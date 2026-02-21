from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.audit import write_audit_event
from app.db.models import Appointment, Document, InsuranceProvider, Policy, PolicyCoverageTerm, ProviderAddress
from app.domain.money import parse_money_to_cents
from app.domain.enums import ProviderAdapterType

router = APIRouter(prefix="/providers", tags=["providers"])
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _coerce_cents(usd_value: str | None, cents_value: int | None, default_cents: int = 0) -> int:
    if usd_value and usd_value.strip():
        try:
            return max(0, parse_money_to_cents(usd_value))
        except ValueError:
            return max(0, default_cents)
    if cents_value is not None:
        return max(0, cents_value)
    return max(0, default_cents)


def _clean_addresses(addresses: list[str] | None) -> list[str]:
    if not addresses:
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in addresses:
        value = raw.strip()
        if not value or value in seen:
            continue
        cleaned.append(value)
        seen.add(value)
    return cleaned


def _adapter_from_key(adapter_key: str) -> ProviderAdapterType:
    lowered = adapter_key.strip().lower()
    if "portal" in lowered:
        return ProviderAdapterType.PORTAL_AUTOMATION
    if "aggregator" in lowered:
        return ProviderAdapterType.AGGREGATOR
    return ProviderAdapterType.MANUAL


def register_templates(templates: Jinja2Templates) -> None:
    @router.get("", response_class=HTMLResponse)
    def list_providers(request: Request, user=Depends(current_user), db: Session = Depends(get_db)) -> HTMLResponse:
        providers = db.scalars(select(InsuranceProvider).order_by(InsuranceProvider.name.asc())).all()
        address_rows = db.scalars(select(ProviderAddress).order_by(ProviderAddress.provider_id.asc(), ProviderAddress.id.asc())).all()
        provider_addresses_by_id: dict[int, list[str]] = {}
        for row in address_rows:
            provider_addresses_by_id.setdefault(row.provider_id, []).append(row.address_text)
        return templates.TemplateResponse(
            "providers.html",
            {
                "request": request,
                "providers": providers,
                "provider_addresses_by_id": provider_addresses_by_id,
                "error": request.query_params.get("error"),
            },
        )

    @router.post("/add")
    def add_provider(
        name: str = Form(...),
        specialty: str = Form(""),
        selector_color: str = Form("#C2185B"),
        estimated_copay_usd: str = Form(""),
        estimated_copay_cents: int | None = Form(None),
        notes: str = Form(""),
        provider_addresses: list[str] | None = Form(None),
        adapter_key: str = Form("manual"),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        cleaned_color = selector_color.strip()
        if not COLOR_RE.fullmatch(cleaned_color):
            cleaned_color = "#C2185B"

        adapter_type = _adapter_from_key(adapter_key)
        estimated_copay = _coerce_cents(estimated_copay_usd, estimated_copay_cents)
        address_values = _clean_addresses(provider_addresses)
        provider = InsuranceProvider(
            name=name.strip(),
            specialty=specialty.strip() or None,
            selector_color=cleaned_color,
            estimated_copay_cents=estimated_copay,
            notes=notes.strip() or None,
            adapter_type=adapter_type,
        )
        db.add(provider)
        try:
            db.flush()
            for address_text in address_values:
                db.add(ProviderAddress(provider_id=provider.id, label=None, address_text=address_text))
            write_audit_event(
                db,
                "create",
                "provider",
                str(provider.id),
                user.id,
                {
                    "adapter": adapter_type.value,
                    "specialty": bool(provider.specialty),
                    "estimated_copay_cents": provider.estimated_copay_cents,
                    "address_count": len(address_values),
                },
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            return RedirectResponse("/providers?error=exists", status_code=303)
        return RedirectResponse("/providers", status_code=303)

    @router.post("/update")
    def update_provider(
        provider_id: int = Form(...),
        name: str = Form(...),
        specialty: str = Form(""),
        selector_color: str = Form("#C2185B"),
        estimated_copay_usd: str = Form(""),
        estimated_copay_cents: int | None = Form(None),
        notes: str = Form(""),
        provider_addresses: list[str] | None = Form(None),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        provider = db.get(InsuranceProvider, provider_id)
        if not provider:
            return RedirectResponse("/providers", status_code=303)

        cleaned_color = selector_color.strip()
        if not COLOR_RE.fullmatch(cleaned_color):
            cleaned_color = "#C2185B"

        provider.name = name.strip()
        provider.specialty = specialty.strip() or None
        provider.selector_color = cleaned_color
        provider.estimated_copay_cents = _coerce_cents(
            estimated_copay_usd, estimated_copay_cents, provider.estimated_copay_cents
        )
        provider.notes = notes.strip() or None
        address_values = _clean_addresses(provider_addresses)
        db.execute(delete(ProviderAddress).where(ProviderAddress.provider_id == provider.id))
        for address_text in address_values:
            db.add(ProviderAddress(provider_id=provider.id, label=None, address_text=address_text))
        write_audit_event(
            db,
            "update",
            "provider",
            str(provider.id),
            user.id,
            {
                "specialty": bool(provider.specialty),
                "estimated_copay_cents": provider.estimated_copay_cents,
                "address_count": len(address_values),
            },
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return RedirectResponse("/providers?error=exists", status_code=303)
        return RedirectResponse("/providers", status_code=303)

    @router.post("/delete")
    def delete_provider(
        provider_id: int = Form(...),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        provider = db.get(InsuranceProvider, provider_id)
        if not provider:
            return RedirectResponse("/providers", status_code=303)

        policy_ids = db.scalars(select(Policy.id).where(Policy.provider_id == provider.id)).all()
        if policy_ids:
            db.execute(update(Document).where(Document.policy_id.in_(policy_ids)).values(policy_id=None))
            db.execute(delete(PolicyCoverageTerm).where(PolicyCoverageTerm.policy_id.in_(policy_ids)))
            db.execute(delete(Policy).where(Policy.id.in_(policy_ids)))

        deleted_appointments = db.execute(delete(Appointment).where(Appointment.provider_id == provider.id)).rowcount or 0
        deleted_addresses = db.execute(delete(ProviderAddress).where(ProviderAddress.provider_id == provider.id)).rowcount or 0
        provider_name = provider.name
        db.delete(provider)
        write_audit_event(
            db,
            "delete",
            "provider",
            str(provider_id),
            user.id,
            {
                "name": provider_name,
                "deleted_policy_count": len(policy_ids),
                "deleted_appointment_count": deleted_appointments,
                "deleted_address_count": deleted_addresses,
            },
        )
        db.commit()
        return RedirectResponse("/providers", status_code=303)
