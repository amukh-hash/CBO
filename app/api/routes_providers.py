from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.audit import write_audit_event
from app.db.models import InsuranceProvider
from app.domain.enums import ProviderAdapterType
from app.services.providers import aggregator_stub, portal_automation  # noqa: F401
from app.services.providers.registry import registry

router = APIRouter(prefix="/providers", tags=["providers"])
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def register_templates(templates: Jinja2Templates) -> None:
    @router.get("", response_class=HTMLResponse)
    def list_providers(request: Request, user=Depends(current_user), db: Session = Depends(get_db)) -> HTMLResponse:
        providers = db.scalars(select(InsuranceProvider).order_by(InsuranceProvider.name.asc())).all()
        return templates.TemplateResponse(
            "providers.html",
            {"request": request, "providers": providers, "adapters": registry.list_adapters(), "error": request.query_params.get("error")},
        )

    @router.post("/add")
    def add_provider(
        request: Request,
        name: str = Form(...),
        specialty: str = Form(""),
        selector_color: str = Form("#C2185B"),
        estimated_copay_cents: int = Form(0),
        notes: str = Form(""),
        adapter_key: str = Form("aggregator_stub"),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        cleaned_color = selector_color.strip()
        if not COLOR_RE.fullmatch(cleaned_color):
            cleaned_color = "#C2185B"

        adapter_type = ProviderAdapterType.AGGREGATOR if "aggregator" in adapter_key else ProviderAdapterType.MANUAL
        provider = InsuranceProvider(
            name=name.strip(),
            specialty=specialty.strip() or None,
            selector_color=cleaned_color,
            estimated_copay_cents=max(0, estimated_copay_cents),
            notes=notes.strip() or None,
            adapter_type=adapter_type,
        )
        db.add(provider)
        write_audit_event(
            db,
            "create",
            "provider",
            provider.name,
            user.id,
            {
                "adapter": adapter_key,
                "specialty": bool(provider.specialty),
                "estimated_copay_cents": provider.estimated_copay_cents,
            },
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return RedirectResponse("/providers?error=exists", status_code=303)
        return RedirectResponse("/providers", status_code=303)
