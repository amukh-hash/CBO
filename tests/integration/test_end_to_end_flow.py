from __future__ import annotations

import io
import zipfile
from datetime import date

from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import Appointment, Document, ExpenseLineItem, InsuranceProvider, Policy


def _csrf_headers(client) -> dict[str, str]:
    return {"x-csrf-token": client.cookies.get("cb_csrf", "")}


def _login(client) -> None:
    client.get("/auth/login")
    resp = client.post(
        "/auth/login",
        data={"pin": "1224"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code in (200, 303)


def _provider_id_by_name(name: str) -> int:
    with SessionLocal() as db:
        provider = db.scalar(select(InsuranceProvider).where(InsuranceProvider.name == name))
        assert provider is not None
        return provider.id


def _policy_id_for_provider(provider_id: int) -> int:
    with SessionLocal() as db:
        policy = db.scalar(select(Policy).where(Policy.provider_id == provider_id).order_by(Policy.id.desc()))
        assert policy is not None
        return policy.id


def _appointment_id_for(provider_id: int, notes: str) -> int:
    with SessionLocal() as db:
        appt = db.scalar(
            select(Appointment)
            .where(Appointment.provider_id == provider_id, Appointment.notes == notes)
            .order_by(Appointment.id.desc())
        )
        assert appt is not None
        return appt.id


def _expense_id_for(category: str, amount_cents: int, incurred_at: date) -> int:
    with SessionLocal() as db:
        expense = db.scalar(
            select(ExpenseLineItem)
            .where(
                ExpenseLineItem.category == category,
                ExpenseLineItem.amount_cents == amount_cents,
                ExpenseLineItem.incurred_at == incurred_at,
            )
            .order_by(ExpenseLineItem.id.desc())
        )
        assert expense is not None
        return expense.id


def _receipt_doc_id_for_expense(expense_id: int) -> int:
    with SessionLocal() as db:
        doc = db.scalar(
            select(Document)
            .where(Document.expense_id == expense_id)
            .order_by(Document.id.desc())
        )
        assert doc is not None
        return doc.id


def test_policy_expense_document_export_zip(client) -> None:
    _login(client)
    provider_name = "Acme Export"
    client.post(
        "/providers/add",
        data={
            "name": provider_name,
            "specialty": "Primary Care",
            "selector_color": "#C2185B",
            "estimated_copay_cents": 2500,
            "notes": "Front desk asks for insurance card",
            "adapter_key": "aggregator_stub",
        },
        headers=_csrf_headers(client),
    )
    provider_id = _provider_id_by_name(provider_name)
    providers_page = client.get("/providers")
    assert provider_name in providers_page.text

    client.post(
        "/policies/add",
        data={
            "provider_id": provider_id,
            "plan_type": "ppo",
            "policy_number": "ABC123",
            "monthly_premium_cents": 44000,
            "deductible_cents": 100000,
            "oop_max_cents": 250000,
        },
        headers=_csrf_headers(client),
    )
    policy_id = _policy_id_for_provider(provider_id)
    client.post(
        "/expenses/add",
        data={"amount_cents": 1234, "incurred_at": "2025-01-01", "category": "copay", "memo": "visit"},
        headers=_csrf_headers(client),
    )
    client.post(
        "/policies/documents/upload",
        files={"file": ("receipt.pdf", b"fake-pdf", "application/pdf")},
        data={"doc_type": "receipt", "policy_id": str(policy_id)},
        headers=_csrf_headers(client),
    )

    export = client.get("/exports/archive.zip")
    assert export.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(export.content))
    assert "data.json" in zf.namelist()
    assert any(name.startswith("documents/") for name in zf.namelist())


def test_update_appointment_from_calendar_flow(client) -> None:
    _login(client)
    provider_name = "Acme Update"
    client.post(
        "/providers/add",
        data={
            "name": provider_name,
            "specialty": "Primary Care",
            "selector_color": "#C2185B",
            "estimated_copay_cents": 2500,
            "notes": "Front desk asks for insurance card",
            "adapter_key": "aggregator_stub",
        },
        headers=_csrf_headers(client),
    )
    provider_id = _provider_id_by_name(provider_name)

    client.post(
        "/appointments/add",
        data={
            "provider_id": provider_id,
            "appointment_date": "2025-01-10",
            "appointment_time": "09:30",
            "estimated_invoice_cents": 3000,
            "location_name": "Acme Clinic",
            "facility_address": "123 Main St, Austin, TX",
            "prep_notes": "Discuss symptoms",
            "notes": "Initial notes",
        },
        headers=_csrf_headers(client),
    )
    appointment_id = _appointment_id_for(provider_id, "Initial notes")

    resp = client.post(
        "/appointments/update",
        data={
            "appointment_id": appointment_id,
            "provider_id": provider_id,
            "appointment_date": "2025-01-10",
            "appointment_time": "11:15",
            "estimated_invoice_cents": 4500,
            "location_name": "Northside Clinic",
            "facility_address": "44 New Address, Austin, TX",
            "prep_notes": "Bring lab report",
            "notes": "Updated notes",
        },
        headers=_csrf_headers(client),
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/?year=2025&month=1"

    dashboard = client.get("/?year=2025&month=1")
    assert f"11:15 AM {provider_name}" in dashboard.text
    assert "Updated notes" in dashboard.text
    assert "Northside Clinic" in dashboard.text


def test_delete_appointment_from_calendar_flow(client) -> None:
    _login(client)
    provider_name = "Acme Delete"
    client.post(
        "/providers/add",
        data={
            "name": provider_name,
            "specialty": "Primary Care",
            "selector_color": "#C2185B",
            "estimated_copay_cents": 2500,
            "notes": "Front desk asks for insurance card",
            "adapter_key": "aggregator_stub",
        },
        headers=_csrf_headers(client),
    )
    provider_id = _provider_id_by_name(provider_name)
    client.post(
        "/appointments/add",
        data={
            "provider_id": provider_id,
            "appointment_date": "2025-01-10",
            "appointment_time": "09:30",
            "estimated_invoice_cents": 3000,
            "location_name": "Acme Clinic",
            "facility_address": "123 Main St, Austin, TX",
            "prep_notes": "Discuss symptoms",
            "notes": "Initial notes",
        },
        headers=_csrf_headers(client),
    )
    appointment_id = _appointment_id_for(provider_id, "Initial notes")

    resp = client.post(
        "/appointments/delete",
        data={"appointment_id": appointment_id},
        headers=_csrf_headers(client),
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/?year=2025&month=1"

    dashboard = client.get("/?year=2025&month=1")
    assert f"09:30 AM {provider_name}" not in dashboard.text


def test_provider_update_and_delete_flow(client) -> None:
    _login(client)
    provider_name = "Acme Provider Flow"
    client.post(
        "/providers/add",
        data={
            "name": provider_name,
            "specialty": "Primary Care",
            "selector_color": "#C2185B",
            "estimated_copay_usd": "25.00",
            "notes": "Initial notes",
            "provider_addresses": "123 Main St, Austin, TX",
        },
        headers=_csrf_headers(client),
    )
    provider_id = _provider_id_by_name(provider_name)

    update_resp = client.post(
        "/providers/update",
        data={
            "provider_id": provider_id,
            "name": "Acme Updated",
            "specialty": "Dermatology",
            "selector_color": "#8E24AA",
            "estimated_copay_usd": "35.00",
            "notes": "Updated notes",
            "provider_addresses": "777 New St, Austin, TX",
        },
        headers=_csrf_headers(client),
        follow_redirects=False,
    )
    assert update_resp.status_code == 303
    assert update_resp.headers["location"] == "/providers"

    providers_page = client.get("/providers")
    assert "Acme Updated" in providers_page.text
    assert "35.00" in providers_page.text

    delete_resp = client.post(
        "/providers/delete",
        data={"provider_id": provider_id},
        headers=_csrf_headers(client),
        follow_redirects=False,
    )
    assert delete_resp.status_code == 303
    assert delete_resp.headers["location"] == "/providers"

    providers_page_after = client.get("/providers")
    assert "Acme Updated" not in providers_page_after.text


def test_expense_receipt_upload_and_summary_cards(client) -> None:
    _login(client)
    provider_name = "Acme Expense Attachments"
    client.post(
        "/providers/add",
        data={
            "name": provider_name,
            "specialty": "Primary Care",
            "selector_color": "#C2185B",
            "estimated_copay_usd": "20.00",
            "notes": "Provider for expense summary test",
        },
        headers=_csrf_headers(client),
    )
    provider_id = _provider_id_by_name(provider_name)
    today = date.today()
    today_str = today.isoformat()

    client.post(
        "/policies/add",
        data={
            "provider_id": provider_id,
            "plan_type": "ppo",
            "policy_number": "PREM100",
            "monthly_premium_usd": "100.00",
            "deductible_usd": "1000.00",
            "oop_max_usd": "2000.00",
        },
        headers=_csrf_headers(client),
    )
    client.post(
        "/appointments/add",
        data={
            "provider_id": provider_id,
            "appointment_date": today_str,
            "appointment_time": "10:30",
            "estimated_invoice_usd": "80.00",
            "location_name": "Clinic A",
            "facility_address": "11 Main St",
            "prep_notes": "Discuss updates",
            "notes": "Summary stats appointment",
        },
        headers=_csrf_headers(client),
    )
    add_resp = client.post(
        "/expenses/add",
        data={
            "amount_usd": "45.67",
            "incurred_at": today_str,
            "category": "rx",
            "memo": "pharmacy",
        },
        files={"receipt_file": ("rx.pdf", b"%PDF-1.4 fake-content", "application/pdf")},
        headers=_csrf_headers(client),
        follow_redirects=False,
    )
    assert add_resp.status_code == 303
    assert add_resp.headers["location"] == "/expenses"

    expense_id = _expense_id_for("rx", 4567, today)
    receipt_doc_id = _receipt_doc_id_for_expense(expense_id)

    expenses_page = client.get("/expenses")
    assert "Open PDF" in expenses_page.text
    assert "Monthly Expenses So Far" in expenses_page.text
    assert "Yearly Expenses So Far" in expenses_page.text
    assert "Estimated Total Yearly Expenses" in expenses_page.text

    receipt_resp = client.get(f"/policies/documents/{receipt_doc_id}/view")
    assert receipt_resp.status_code == 200
    assert receipt_resp.headers.get("content-type", "").startswith("application/pdf")
