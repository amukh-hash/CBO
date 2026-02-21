from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.audit import write_audit_event
from app.core.config import get_settings
from app.core.crypto import FieldEncryptor
from app.db.models import Document, InsuranceProvider, Policy, PolicyCoverageTerm
from app.domain.enums import DocumentType, NetworkTier, PlanType
from app.domain.money import parse_money_to_cents
from app.services.documents.store import DocumentStore

router = APIRouter(prefix="/policies", tags=["policies"])
encryptor = FieldEncryptor()
settings = get_settings()
store = DocumentStore(settings.docs_dir)
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
DOCUMENT_TYPE_VALUES = {item.value for item in DocumentType}


def _is_allowed_file(upload: UploadFile) -> bool:
    filename = (upload.filename or "").lower()
    suffix = Path(filename).suffix
    if suffix not in ALLOWED_EXTENSIONS:
        return False
    if upload.content_type and upload.content_type not in ALLOWED_MIME_TYPES:
        return False
    return True


def _coerce_cents(usd_value: str | None, cents_value: int | None) -> int:
    if usd_value and usd_value.strip():
        try:
            return max(0, parse_money_to_cents(usd_value))
        except ValueError:
            return max(0, cents_value or 0)
    return max(0, cents_value or 0)


def register_templates(templates: Jinja2Templates) -> None:
    @router.get("", response_class=HTMLResponse)
    def list_policies(request: Request, user=Depends(current_user), db: Session = Depends(get_db)) -> HTMLResponse:
        policies = db.scalars(select(Policy).order_by(Policy.id.desc())).all()
        providers = db.scalars(select(InsuranceProvider).order_by(InsuranceProvider.name.asc())).all()
        documents = db.scalars(select(Document).order_by(Document.created_at.desc()).limit(300)).all()
        policy_by_id = {policy.id: policy for policy in policies}
        provider_by_id = {provider.id: provider for provider in providers}

        return templates.TemplateResponse(
            request,
            "policies.html",
            {
                "policies": policies,
                "providers": providers,
                "plan_types": list(PlanType),
                "documents": documents,
                "policy_by_id": policy_by_id,
                "provider_by_id": provider_by_id,
            },
        )

    @router.post("/add")
    def add_policy(
        provider_id: int = Form(...),
        plan_type: str = Form(...),
        policy_number: str = Form(...),
        monthly_premium_usd: str = Form(""),
        monthly_premium_cents: int = Form(0),
        deductible_usd: str = Form(""),
        deductible_cents: int = Form(0),
        oop_max_usd: str = Form(""),
        oop_max_cents: int = Form(0),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        monthly_premium = _coerce_cents(monthly_premium_usd, monthly_premium_cents)
        deductible = _coerce_cents(deductible_usd, deductible_cents)
        oop_max = _coerce_cents(oop_max_usd, oop_max_cents)
        policy = Policy(
            provider_id=provider_id,
            plan_type=PlanType(plan_type),
            policy_number_enc=encryptor.encrypt(policy_number),
            monthly_premium_cents=monthly_premium,
            deductible_cents=deductible,
            oop_max_cents=oop_max,
        )
        db.add(policy)
        db.flush()
        db.add(
            PolicyCoverageTerm(
                policy_id=policy.id,
                network_tier=NetworkTier.IN_NETWORK,
                start_date=date.today(),
                deductible_cents=policy.deductible_cents,
                oop_max_cents=policy.oop_max_cents,
            )
        )
        write_audit_event(db, "create", "policy", str(policy.id), user.id, {"provider_id": provider_id})
        db.commit()
        return RedirectResponse("/policies", status_code=303)

    @router.post("/documents/upload")
    async def upload_doc(
        policy_id: int | None = Form(None),
        doc_type: str = Form("policy"),
        file: UploadFile = File(...),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ) -> Response:
        if not _is_allowed_file(file):
            return RedirectResponse("/policies?upload=invalid_type", status_code=303)

        payload = await file.read()
        safe_name = file.filename or "upload.bin"
        info = store.encrypt_and_store(safe_name, payload)
        linked_policy_id = policy_id if policy_id and policy_id > 0 else None
        doc_enum = DocumentType(doc_type) if doc_type in DOCUMENT_TYPE_VALUES else DocumentType.OTHER
        doc = Document(
            owner_user_id=user.id,
            policy_id=linked_policy_id,
            doc_type=doc_enum,
            filename=safe_name,
            storage_path=str(info["storage_path"]),
            nonce=info["nonce"],
            wrapped_dek=info["wrapped_dek"],
            sha256_plaintext=str(info["sha256_plaintext"]),
            sha256_ciphertext=str(info["sha256_ciphertext"]),
            aad_sha256=str(info["aad_sha256"]),
            encryption_version=int(info["encryption_version"]),
            size_bytes=int(info["size_bytes"]),
            mime_type=file.content_type or "application/octet-stream",
        )
        db.add(doc)
        write_audit_event(
            db,
            "create",
            "document",
            safe_name,
            user.id,
            {"doc_type": doc_type, "policy_id": linked_policy_id},
        )
        db.commit()
        return RedirectResponse("/policies", status_code=303)

    @router.get("/documents/{doc_id}/view")
    def view_document(doc_id: int, user=Depends(current_user), db: Session = Depends(get_db)) -> Response:
        doc = db.get(Document, doc_id)
        if not doc:
            return Response(status_code=404)
        try:
            plaintext = store.decrypt_and_verify(
                storage_path=doc.storage_path,
                nonce=doc.nonce,
                wrapped_dek=doc.wrapped_dek,
                expected_sha256_ciphertext=doc.sha256_ciphertext,
                expected_sha256_plaintext=doc.sha256_plaintext,
                size_bytes=doc.size_bytes,
                encryption_version=doc.encryption_version,
            )
        except ValueError:
            return Response(content="Document integrity verification failed", status_code=409)
        write_audit_event(db, "view", "document", str(doc.id), user.id, {"filename": doc.filename})
        db.commit()
        return Response(
            content=plaintext,
            media_type=doc.mime_type,
            headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
        )
