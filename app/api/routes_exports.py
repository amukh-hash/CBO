from __future__ import annotations

import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.audit import write_audit_event
from app.core.config import get_settings
from app.db.models import Appointment, Document, ExpenseLineItem, InsuranceProvider, Policy

router = APIRouter(prefix="/exports", tags=["exports"])
settings = get_settings()


def _stable_json(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


@router.get("/archive.zip")
def export_archive(user=Depends(current_user), db: Session = Depends(get_db)) -> Response:
    providers = db.scalars(select(InsuranceProvider).order_by(InsuranceProvider.id.asc())).all()
    policies = db.scalars(select(Policy).order_by(Policy.id.asc())).all()
    appointments = db.scalars(select(Appointment).order_by(Appointment.id.asc())).all()
    expenses = db.scalars(select(ExpenseLineItem).order_by(ExpenseLineItem.id.asc())).all()
    docs = db.scalars(select(Document).order_by(Document.id.asc())).all()

    payload = {
        "providers": [
            {
                "id": p.id,
                "name": p.name,
                "specialty": p.specialty,
                "selector_color": p.selector_color,
                "estimated_copay_cents": p.estimated_copay_cents,
                "adapter_type": p.adapter_type.value,
            }
            for p in providers
        ],
        "policies": [
            {
                "id": p.id,
                "provider_id": p.provider_id,
                "plan_type": p.plan_type.value,
                "monthly_premium_cents": p.monthly_premium_cents,
            }
            for p in policies
        ],
        "expenses": [{"id": e.id, "amount_cents": e.amount_cents, "incurred_at": e.incurred_at.isoformat()} for e in expenses],
        "appointments": [
            {
                "id": a.id,
                "provider_id": a.provider_id,
                "scheduled_at": a.scheduled_at.isoformat(timespec="minutes"),
                "estimated_invoice_cents": a.estimated_invoice_cents,
            }
            for a in appointments
        ],
    }

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("data.json", _stable_json(payload))
        for doc in docs:
            path = settings.docs_dir / doc.storage_path
            if path.exists():
                zf.write(path, arcname=str(Path("documents") / f"{doc.id}-{doc.filename}.bin"))

    write_audit_event(db, "export", "archive", "zip", user.id, {"items": len(docs)})
    db.commit()
    return Response(buffer.getvalue(), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=cb-archive.zip"})


@router.post("/reimbursement.pdf")
def reimbursement_packet(service_ids: str = Form(""), user=Depends(current_user), db: Session = Depends(get_db)) -> Response:
    selected = [x for x in service_ids.split(",") if x.strip()]
    packet = io.BytesIO()
    pdf = canvas.Canvas(packet, pagesize=letter)
    pdf.setTitle("Reimbursement Packet")
    pdf.drawString(72, 740, "Reimbursement Packet")
    pdf.drawString(72, 720, f"Selected service IDs: {', '.join(selected) if selected else 'None'}")
    pdf.drawString(72, 700, "Generated locally by CB Organizer")
    pdf.showPage()
    pdf.save()
    write_audit_event(db, "export", "reimbursement_packet", "pdf", user.id, {"service_ids": selected})
    db.commit()
    return Response(packet.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=reimbursement-packet.pdf"})
