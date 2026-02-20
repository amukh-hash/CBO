from __future__ import annotations

import argparse
import io
import os
import time
import zipfile

import httpx


def wait_ready(base_url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base_url}/auth/login", timeout=1.5)
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.4)
    raise RuntimeError("Application did not become ready in time")


def csrf_headers(client: httpx.Client) -> dict[str, str]:
    token = client.cookies.get("cb_csrf") or ""
    return {"x-csrf-token": token}


def validate(base_url: str, mode: str) -> None:
    wait_ready(base_url)
    pin = os.getenv("CB_VALIDATE_PIN", "1224")

    with httpx.Client(base_url=base_url, follow_redirects=True, timeout=10.0) as client:
        client.get("/auth/login")

        denied = client.post("/auth/login", data={"pin": pin})
        if denied.status_code != 403:
            raise RuntimeError("Expected CSRF protection to reject missing token")

        client.post("/auth/login", data={"pin": pin}, headers=csrf_headers(client))

        client.post(
            "/providers/add",
            data={
                "name": "Release Health",
                "specialty": "Primary Care",
                "selector_color": "#8E24AA",
                "estimated_copay_cents": 2000,
                "notes": "Release test provider",
                "adapter_key": "aggregator_stub",
            },
            headers=csrf_headers(client),
        )
        client.post(
            "/policies/add",
            data={
                "provider_id": 1,
                "plan_type": "ppo",
                "policy_number": "REL-123",
                "monthly_premium_cents": 32000,
                "deductible_cents": 100000,
                "oop_max_cents": 250000,
            },
            headers=csrf_headers(client),
        )
        client.post(
            "/expenses/add",
            data={"amount_cents": 9900, "incurred_at": "2025-01-01", "category": "medical", "memo": "release-check"},
            headers=csrf_headers(client),
        )
        client.post(
            "/policies/documents/upload",
            files={"file": ("release.pdf", b"fake-pdf", "application/pdf")},
            data={"doc_type": "receipt", "policy_id": "1"},
            headers=csrf_headers(client),
        )
        client.post(
            "/appointments/add",
            data={
                "provider_id": 1,
                "appointment_date": "2025-01-08",
                "appointment_time": "10:45",
                "estimated_invoice_cents": 2000,
                "location_name": "Release Clinic",
                "facility_address": "100 Health Ave",
                "prep_notes": "Review medications",
                "notes": "Release validation visit",
            },
            headers=csrf_headers(client),
        )

        archive = client.get("/exports/archive.zip")
        archive.raise_for_status()
        zf = zipfile.ZipFile(io.BytesIO(archive.content))
        if "data.json" not in zf.namelist():
            raise RuntimeError("Archive is missing data.json")

        if mode == "packaged":
            dashboard = client.get("/")
            dashboard.raise_for_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--mode", choices=["dev", "packaged"], default="dev")
    args = parser.parse_args()
    validate(args.base_url, args.mode)
    print("release validation passed")
