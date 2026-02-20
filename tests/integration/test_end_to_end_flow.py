from __future__ import annotations

import io
import zipfile


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


def test_policy_expense_document_export_zip(client) -> None:
    _login(client)
    client.post(
        "/providers/add",
        data={
            "name": "Acme",
            "specialty": "Primary Care",
            "selector_color": "#C2185B",
            "estimated_copay_cents": 2500,
            "notes": "Front desk asks for insurance card",
            "adapter_key": "aggregator_stub",
        },
        headers=_csrf_headers(client),
    )
    providers_page = client.get("/providers")
    assert "Acme" in providers_page.text

    client.post(
        "/policies/add",
        data={
            "provider_id": 1,
            "plan_type": "ppo",
            "policy_number": "ABC123",
            "monthly_premium_cents": 44000,
            "deductible_cents": 100000,
            "oop_max_cents": 250000,
        },
        headers=_csrf_headers(client),
    )
    client.post(
        "/expenses/add",
        data={"amount_cents": 1234, "incurred_at": "2025-01-01", "category": "copay", "memo": "visit"},
        headers=_csrf_headers(client),
    )
    client.post(
        "/policies/documents/upload",
        files={"file": ("receipt.pdf", b"fake-pdf", "application/pdf")},
        data={"doc_type": "receipt", "policy_id": "1"},
        headers=_csrf_headers(client),
    )

    export = client.get("/exports/archive.zip")
    assert export.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(export.content))
    assert "data.json" in zf.namelist()
    assert any(name.startswith("documents/") for name in zf.namelist())
