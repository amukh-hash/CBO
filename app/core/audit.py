from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_event_hash(prev_hash: str, event_without_hash: dict[str, Any]) -> str:
    canonical = canonical_json(event_without_hash)
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def write_audit_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_user_id: int | None,
    payload: dict[str, Any],
) -> AuditEvent:
    pending = [obj for obj in db.new if isinstance(obj, AuditEvent)]
    if pending:
        prev_hash = pending[-1].event_hash
    else:
        prev_hash = db.scalar(select(AuditEvent.event_hash).order_by(AuditEvent.id.desc()).limit(1)) or "0" * 64
    created_at = datetime.now(UTC).replace(tzinfo=None)
    event_without_hash = {
        "timestamp": created_at.isoformat(),
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor_user_id": actor_user_id,
        "payload": payload,
    }
    event_hash = compute_event_hash(prev_hash, event_without_hash)
    event = AuditEvent(
        created_at=created_at,
        actor_user_id=actor_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=canonical_json(payload),
        prev_hash=prev_hash,
        event_hash=event_hash,
    )
    db.add(event)
    return event
