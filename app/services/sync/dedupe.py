from __future__ import annotations

import hashlib
from typing import Iterable


def make_idempotency_key(*parts: str) -> str:
    raw = "|".join(part.strip().lower() for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dedupe_keys(keys: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out
