from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.api.schemas import ExpenseCreate, ExpenseOut
from app.core.audit import write_audit_event
from app.db.models import ExpenseLineItem
from app.services.sync.dedupe import make_idempotency_key

router = APIRouter(prefix="/expenses", tags=["expenses"])


def register_templates(templates: Jinja2Templates) -> None:
    @router.get("", response_class=HTMLResponse)
    def list_expenses(request: Request, user=Depends(current_user), db: Session = Depends(get_db)) -> HTMLResponse:
        expenses = db.scalars(select(ExpenseLineItem).order_by(ExpenseLineItem.id.desc()).limit(100)).all()
        return templates.TemplateResponse("expenses.html", {"request": request, "expenses": expenses})

    @router.post("/add")
    def add_expense(
        amount_cents: int = Form(...),
        incurred_at: str = Form(...),
        category: str = Form("medical"),
        memo: str = Form(""),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        idem = make_idempotency_key(incurred_at, str(amount_cents), category, memo)
        exists = db.scalar(select(ExpenseLineItem).where(ExpenseLineItem.idempotency_key == idem))
        if not exists:
            expense = ExpenseLineItem(
                amount_cents=amount_cents,
                incurred_at=datetime.strptime(incurred_at, "%Y-%m-%d").date(),
                category=category,
                idempotency_key=idem,
            )
            db.add(expense)
            write_audit_event(db, "create", "expense", idem, user.id, {"amount_cents": amount_cents})
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
