from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import compute_event_hash
from app.db.models import AuditEvent, Document


def verify_document_hashes(db: Session, docs_root: Path) -> list[str]:
    failures: list[str] = []
    docs = db.scalars(select(Document)).all()
    for doc in docs:
        path = docs_root / doc.storage_path
        if not path.exists():
            failures.append(f"missing:{doc.id}")
            continue
        ciphertext = path.read_bytes()
        digest = hashlib.sha256(ciphertext).hexdigest()
        if digest != doc.sha256_ciphertext:
            failures.append(f"cipher_mismatch:{doc.id}")
    return failures


def verify_audit_chain(db: Session) -> list[str]:
    failures: list[str] = []
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.id.asc())).all()
    prev = "0" * 64
    for event in events:
        payload = json.loads(event.payload_json)
        event_without_hash = {
            "timestamp": event.created_at.isoformat(),
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "actor_user_id": event.actor_user_id,
            "payload": payload,
        }
        expected = compute_event_hash(prev, event_without_hash)
        if event.prev_hash != prev or expected != event.event_hash:
            failures.append(f"audit_mismatch:{event.id}")
        prev = event.event_hash
    return failures
