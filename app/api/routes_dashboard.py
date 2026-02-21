from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.audit import write_audit_event
from app.db.models import Appointment, Document, ExpenseLineItem, InsuranceProvider, Policy, ProviderAddress
from app.domain.money import parse_money_to_cents

router = APIRouter(tags=["dashboard"])


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _safe_month_year(year_raw: str | None, month_raw: str | None) -> tuple[int, int]:
    today = date.today()
    year = today.year
    month = today.month
    if year_raw:
        try:
            parsed_year = int(year_raw)
            if 1900 <= parsed_year <= 2100:
                year = parsed_year
        except ValueError:
            pass
    if month_raw:
        try:
            parsed_month = int(month_raw)
            if 1 <= parsed_month <= 12:
                month = parsed_month
        except ValueError:
            pass
    return year, month


def _coerce_cents(usd_value: str | None, cents_value: int | None, default_cents: int) -> int:
    if usd_value and usd_value.strip():
        try:
            return max(0, parse_money_to_cents(usd_value))
        except ValueError:
            return max(0, default_cents)
    if cents_value is not None and cents_value >= 0:
        return cents_value
    return max(0, default_cents)


def register_templates(templates: Jinja2Templates) -> None:
    @router.get("/dev/cats/duo", response_class=HTMLResponse)
    def dev_duo_cats(request: Request, user=Depends(current_user)) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "dev_cats_duo.html",
            {
                "user": user,
            },
        )

    @router.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, user=Depends(current_user), db: Session = Depends(get_db)) -> HTMLResponse:
        year, month = _safe_month_year(request.query_params.get("year"), request.query_params.get("month"))
        month_start, month_end = _month_bounds(year, month)

        provider_count = db.scalar(select(func.count()).select_from(InsuranceProvider)) or 0
        docs_count = db.scalar(select(func.count()).select_from(Document)) or 0
        monthly_expense = db.scalar(
            select(func.coalesce(func.sum(ExpenseLineItem.amount_cents), 0)).where(
                ExpenseLineItem.incurred_at >= month_start,
                ExpenseLineItem.incurred_at < month_end,
            )
        ) or 0
        monthly_premium = db.scalar(select(func.coalesce(func.sum(Policy.monthly_premium_cents), 0))) or 0
        month_appointment_count = db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.scheduled_at >= datetime.combine(month_start, time.min),
                Appointment.scheduled_at < datetime.combine(month_end, time.min),
            )
        ) or 0

        first_weekday = month_start.weekday()
        month_last_day = monthrange(year, month)[1]
        last_date = date(year, month, month_last_day)
        grid_start = month_start - timedelta(days=first_weekday)
        grid_end = last_date + timedelta(days=6 - last_date.weekday())
        grid_end_exclusive = grid_end + timedelta(days=1)

        rows = db.execute(
            select(Appointment, InsuranceProvider)
            .join(InsuranceProvider, Appointment.provider_id == InsuranceProvider.id)
            .where(
                Appointment.scheduled_at >= datetime.combine(grid_start, time.min),
                Appointment.scheduled_at < datetime.combine(grid_end_exclusive, time.min),
            )
            .order_by(Appointment.scheduled_at.asc())
        ).all()

        by_day: dict[date, list[dict[str, object]]] = {}
        for appt, provider in rows:
            appt_day = appt.scheduled_at.date()
            by_day.setdefault(appt_day, []).append(
                {
                    "id": appt.id,
                    "provider_id": provider.id,
                    "provider_name": provider.name,
                    "provider_specialty": provider.specialty or "",
                    "provider_color": provider.selector_color,
                    "time": appt.scheduled_at.strftime("%I:%M %p").lstrip("0"),
                    "scheduled_at_iso": appt.scheduled_at.isoformat(timespec="minutes"),
                    "scheduled_date": appt.scheduled_at.strftime("%Y-%m-%d"),
                    "scheduled_time": appt.scheduled_at.strftime("%H:%M"),
                    "estimated_invoice_cents": appt.estimated_invoice_cents,
                    "estimated_invoice_usd": f"{appt.estimated_invoice_cents / 100:.2f}",
                    "location_name": appt.location_name or "",
                    "facility_address": appt.facility_address or "",
                    "prep_notes": appt.prep_notes or "",
                    "notes": appt.notes or "",
                }
            )

        weeks: list[list[dict[str, object]]] = []
        cursor = grid_start
        while cursor <= grid_end:
            week: list[dict[str, object]] = []
            for _ in range(7):
                week.append(
                    {
                        "date": cursor,
                        "day_num": cursor.day,
                        "in_month": cursor.month == month,
                        "appointments": by_day.get(cursor, []),
                    }
                )
                cursor += timedelta(days=1)
            weeks.append(week)

        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        providers = db.scalars(select(InsuranceProvider).order_by(InsuranceProvider.name.asc())).all()
        address_rows = db.scalars(select(ProviderAddress).order_by(ProviderAddress.provider_id.asc(), ProviderAddress.id.asc())).all()
        provider_addresses_by_id: dict[int, list[str]] = {}
        for row in address_rows:
            provider_addresses_by_id.setdefault(row.provider_id, []).append(row.address_text)
        recent = db.scalars(select(ExpenseLineItem).order_by(ExpenseLineItem.id.desc()).limit(8)).all()

        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "user": user,
                "provider_count": provider_count,
                "docs_count": docs_count,
                "monthly_expense": monthly_expense,
                "monthly_premium": monthly_premium,
                "monthly_total": monthly_expense + monthly_premium,
                "month_appointment_count": month_appointment_count,
                "current_month_label": month_start.strftime("%B %Y"),
                "current_year": year,
                "current_month": month,
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_year": next_year,
                "next_month": next_month,
                "weeks": weeks,
                "providers": providers,
                "provider_addresses_by_id": provider_addresses_by_id,
                "recent": recent,
            },
        )

    @router.post("/appointments/add")
    def add_appointment(
        provider_id: int = Form(...),
        appointment_date: str = Form(...),
        appointment_time: str = Form(...),
        estimated_invoice_usd: str = Form(""),
        estimated_invoice_cents: int | None = Form(None),
        location_name: str = Form(""),
        facility_address: str = Form(""),
        prep_notes: str = Form(""),
        notes: str = Form(""),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        provider = db.get(InsuranceProvider, provider_id)
        if not provider:
            return RedirectResponse("/", status_code=303)

        try:
            scheduled_at = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return RedirectResponse("/", status_code=303)

        invoice_cents = _coerce_cents(estimated_invoice_usd, estimated_invoice_cents, provider.estimated_copay_cents)
        appointment = Appointment(
            provider_id=provider.id,
            scheduled_at=scheduled_at,
            estimated_invoice_cents=invoice_cents,
            location_name=location_name.strip() or None,
            facility_address=facility_address.strip() or None,
            prep_notes=prep_notes.strip() or None,
            notes=notes.strip() or None,
        )
        db.add(appointment)
        db.flush()
        write_audit_event(
            db,
            "create",
            "appointment",
            str(appointment.id),
            user.id,
            {"provider_id": provider.id, "scheduled_at": scheduled_at.isoformat(timespec="minutes")},
        )
        db.commit()
        return RedirectResponse(f"/?year={scheduled_at.year}&month={scheduled_at.month}", status_code=303)

    @router.post("/appointments/update")
    def update_appointment(
        appointment_id: int = Form(...),
        provider_id: int = Form(...),
        appointment_date: str = Form(...),
        appointment_time: str = Form(...),
        estimated_invoice_usd: str = Form(""),
        estimated_invoice_cents: int | None = Form(None),
        location_name: str = Form(""),
        facility_address: str = Form(""),
        prep_notes: str = Form(""),
        notes: str = Form(""),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        appointment = db.get(Appointment, appointment_id)
        provider = db.get(InsuranceProvider, provider_id)
        if not appointment or not provider:
            return RedirectResponse("/", status_code=303)

        try:
            scheduled_at = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return RedirectResponse("/", status_code=303)

        invoice_cents = _coerce_cents(estimated_invoice_usd, estimated_invoice_cents, provider.estimated_copay_cents)
        appointment.provider_id = provider.id
        appointment.scheduled_at = scheduled_at
        appointment.estimated_invoice_cents = invoice_cents
        appointment.location_name = location_name.strip() or None
        appointment.facility_address = facility_address.strip() or None
        appointment.prep_notes = prep_notes.strip() or None
        appointment.notes = notes.strip() or None
        db.flush()
        write_audit_event(
            db,
            "update",
            "appointment",
            str(appointment.id),
            user.id,
            {"provider_id": provider.id, "scheduled_at": scheduled_at.isoformat(timespec="minutes")},
        )
        db.commit()
        return RedirectResponse(f"/?year={scheduled_at.year}&month={scheduled_at.month}", status_code=303)

    @router.post("/appointments/delete")
    def delete_appointment(
        appointment_id: int = Form(...),
        user=Depends(current_user),
        db: Session = Depends(get_db),
    ):
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return RedirectResponse("/", status_code=303)
        scheduled_at = appointment.scheduled_at
        db.delete(appointment)
        write_audit_event(
            db,
            "delete",
            "appointment",
            str(appointment_id),
            user.id,
            {"scheduled_at": scheduled_at.isoformat(timespec="minutes")},
        )
        db.commit()
        return RedirectResponse(f"/?year={scheduled_at.year}&month={scheduled_at.month}", status_code=303)
