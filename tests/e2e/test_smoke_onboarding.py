from __future__ import annotations

import pytest


@pytest.mark.optional
def test_dashboard_calendar_and_expense_visible(client) -> None:
    client.get("/auth/login")
    csrf_headers = {"x-csrf-token": client.cookies.get("cb_csrf", "")}
    client.post("/auth/login", data={"pin": "1224"}, headers=csrf_headers)

    csrf_headers = {"x-csrf-token": client.cookies.get("cb_csrf", "")}
    client.post(
        "/providers/add",
        data={
            "name": "Acme Wellness",
            "specialty": "Dermatology",
            "selector_color": "#8E24AA",
            "estimated_copay_cents": 3000,
            "notes": "Bring prior lab reports",
            "adapter_key": "aggregator_stub",
        },
        headers=csrf_headers,
    )

    csrf_headers = {"x-csrf-token": client.cookies.get("cb_csrf", "")}
    client.post(
        "/appointments/add",
        data={
            "provider_id": 1,
            "appointment_date": "2025-01-10",
            "appointment_time": "09:30",
            "estimated_invoice_cents": 3000,
            "location_name": "Acme Clinic",
            "facility_address": "123 Main St, Austin, TX",
            "prep_notes": "Discuss rash persistence",
            "notes": "Annual checkup",
        },
        headers=csrf_headers,
    )

    csrf_headers = {"x-csrf-token": client.cookies.get("cb_csrf", "")}
    client.post(
        "/expenses/add",
        data={"amount_cents": 2222, "incurred_at": "2025-01-05", "category": "rx", "memo": "pharmacy"},
        headers=csrf_headers,
    )
    csrf_headers = {"x-csrf-token": client.cookies.get("cb_csrf", "")}
    client.post(
        "/policies/documents/upload",
        files={"file": ("rx.pdf", b"fake-pdf-3", "application/pdf")},
        data={"doc_type": "receipt"},
        headers=csrf_headers,
    )
    dashboard = client.get("/")
    assert "$22.22" in dashboard.text
    assert "Appointments Calendar" in dashboard.text
