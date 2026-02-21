from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.api.schemas import ExpenseCreate, ExpenseOut
from app.core.audit import write_audit_event
from app.core.config import get_settings
from app.db.models import Appointment, Document, ExpenseLineItem, Policy
from app.domain.enums import DocumentType
from app.domain.money import parse_money_to_cents
from app.services.documents.store import DocumentStore
from app.services.sync.dedupe import make_idempotency_key

router = APIRouter(prefix="/expenses", tags=["expenses"])
settings = get_settings()
store = DocumentStore(settings.docs_dir)
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


def _has_file(upload: UploadFile | None) -> bool:
    return bool(upload and (upload.filename or "").strip())


def _is_allowed_file(upload: UploadFile) -> bool:
    filename = (upload.filename or "").lower()
    suffix = Path(filename).suffix
    if suffix not in ALLOWED_EXTENSIONS:
        return False
    if upload.content_type and upload.content_type not in ALLOWED_MIME_TYPES:
        return False
    return True


def register_templates(templates: Jinja2Templates) -> None:
    @router.get("", response_class=HTMLResponse)
    def list_expenses(request: Request, user=Depends(current_user), db: Session = Depends(get_db)) -> HTMLResponse:
        today = date.today()
        month_start = today.replace(day=1)
        year_start = date(today.year, 1, 1)
        next_year_start = date(today.year + 1, 1, 1)
        months_elapsed = max(1, today.month)

        expenses = db.scalars(select(ExpenseLineItem).order_by(ExpenseLineItem.id.desc()).limit(200)).all()
        expense_ids = [expense.id for expense in expenses]
        documents = (
            db.scalars(
                select(Document)
                .where(Document.expense_id.in_(expense_ids))
                .order_by(Document.created_at.desc())
            ).all()
            if expense_ids
            else []
        )
        receipt_by_expense_id: dict[int, Document] = {}
        for doc in documents:
            if doc.expense_id is None or doc.expense_id in receipt_by_expense_id:
                continue
            receipt_by_expense_id[doc.expense_id] = doc

        monthly_expenses_so_far = db.scalar(
            select(func.coalesce(func.sum(ExpenseLineItem.amount_cents), 0)).where(
                ExpenseLineItem.incurred_at >= month_start,
                ExpenseLineItem.incurred_at <= today,
            )
        ) or 0
        yearly_expenses_so_far = db.scalar(
            select(func.coalesce(func.sum(ExpenseLineItem.amount_cents), 0)).where(
                ExpenseLineItem.incurred_at >= year_start,
                ExpenseLineItem.incurred_at <= today,
            )
        ) or 0
        monthly_premium_cents = db.scalar(select(func.coalesce(func.sum(Policy.monthly_premium_cents), 0))) or 0
        appointments_ytd = db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.scheduled_at >= datetime.combine(year_start, time.min),
                Appointment.scheduled_at < datetime.combine(next_year_start, time.min),
            )
        ) or 0
        appointment_invoice_ytd = db.scalar(
            select(func.coalesce(func.sum(Appointment.estimated_invoice_cents), 0)).where(
                Appointment.scheduled_at >= datetime.combine(year_start, time.min),
                Appointment.scheduled_at < datetime.combine(next_year_start, time.min),
            )
        ) or 0

        avg_monthly_expenses_cents = int(round(yearly_expenses_so_far / months_elapsed))
        avg_monthly_appointments = appointments_ytd / months_elapsed
        avg_invoice_per_appointment_cents = int(round(appointment_invoice_ytd / appointments_ytd)) if appointments_ytd else 0
        projected_appointment_cost_cents = int(round(avg_monthly_appointments * avg_invoice_per_appointment_cents * 12))
        estimated_total_yearly_cents = int(round(monthly_premium_cents * 12 + avg_monthly_expenses_cents * 12 + projected_appointment_cost_cents))

        expense_rows = [
            {
                "expense": expense,
                "receipt": receipt_by_expense_id.get(expense.id),
            }
            for expense in expenses
        ]
        return templates.TemplateResponse(
            "expenses.html",
            {
                "request": request,
                "expense_rows": expense_rows,
                "monthly_expenses_so_far": monthly_expenses_so_far,
                "yearly_expenses_so_far": yearly_expenses_so_far,
                "estimated_total_yearly_cents": estimated_total_yearly_cents,
                "monthly_premium_cents": monthly_premium_cents,
                "avg_monthly_expenses_cents": avg_monthly_expenses_cents,
                "appointments_ytd": appointments_ytd,
                "avg_invoice_per_appointment_cents": avg_invoice_per_appointment_cents,
                "upload_error": request.query_params.get("upload"),
            },
        )

    @router.post("/add")
    async def add_expense(
        amount_usd: str = Form(""),
        amount_cents: int | None = Form(None),
        incurred_at: str = Form(...),
        category: str = Form("medical"),
        memo: str = Form(""),
        receipt_file: UploadFile | None = File(None),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        if _has_file(receipt_file) and receipt_file is not None and not _is_allowed_file(receipt_file):
            return RedirectResponse("/expenses?upload=invalid_type", status_code=303)

        cents = amount_cents if amount_cents is not None else 0
        if amount_usd.strip():
            try:
                cents = parse_money_to_cents(amount_usd)
            except ValueError:
                cents = amount_cents if amount_cents is not None else 0
        cents = max(0, cents)
        idem = make_idempotency_key(incurred_at, str(cents), category, memo)
        expense = db.scalar(select(ExpenseLineItem).where(ExpenseLineItem.idempotency_key == idem))
        if not expense:
            expense = ExpenseLineItem(
                amount_cents=cents,
                incurred_at=datetime.strptime(incurred_at, "%Y-%m-%d").date(),
                category=category,
                idempotency_key=idem,
            )
            db.add(expense)
            db.flush()
            write_audit_event(db, "create", "expense", idem, user.id, {"amount_cents": cents})

        if _has_file(receipt_file) and receipt_file is not None:
            payload = await receipt_file.read()
            safe_name = receipt_file.filename or "expense-receipt.pdf"
            info = store.encrypt_and_store(safe_name, payload)
            doc = Document(
                owner_user_id=user.id,
                policy_id=None,
                expense_id=expense.id,
                doc_type=DocumentType.RECEIPT,
                filename=safe_name,
                storage_path=str(info["storage_path"]),
                nonce=info["nonce"],
                wrapped_dek=info["wrapped_dek"],
                sha256_plaintext=str(info["sha256_plaintext"]),
                sha256_ciphertext=str(info["sha256_ciphertext"]),
                aad_sha256=str(info["aad_sha256"]),
                encryption_version=int(info["encryption_version"]),
                size_bytes=int(info["size_bytes"]),
                mime_type=receipt_file.content_type or "application/pdf",
            )
            db.add(doc)
            write_audit_event(
                db,
                "create",
                "document",
                safe_name,
                user.id,
                {"doc_type": DocumentType.RECEIPT.value, "expense_id": expense.id},
            )

        db.commit()
        return RedirectResponse("/expenses", status_code=303)

    @router.post("/api", response_model=ExpenseOut)
    def add_expense_api(payload: ExpenseCreate, user=Depends(current_user), db: Session = Depends(get_db)) -> ExpenseOut:
        idem = make_idempotency_key(payload.incurred_at.isoformat(), str(payload.amount_cents), payload.category, payload.memo)
        expense = db.scalar(select(ExpenseLineItem).where(ExpenseLineItem.idempotency_key == idem))
        if not expense:
            expense = ExpenseLineItem(
                amount_cents=payload.amount_cents,
                incurred_at=payload.incurred_at,
                category=payload.category,
                idempotency_key=idem,
            )
            db.add(expense)
            write_audit_event(db, "create", "expense", idem, user.id, {"amount_cents": payload.amount_cents})
            db.commit()
            db.refresh(expense)
        return ExpenseOut(id=expense.id, amount_cents=expense.amount_cents, incurred_at=expense.incurred_at, category=expense.category)
