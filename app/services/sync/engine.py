from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from app.services.providers.registry import registry


@dataclass(slots=True)
class ProviderCircuit:
    failures: int = 0
    opened_until: float = 0.0


@dataclass(slots=True)
class SyncEngine:
    max_failures: int = 3
    cooldown_seconds: int = 120
    circuits: dict[str, ProviderCircuit] = field(default_factory=dict)

    def run_once(self, adapter_key: str, sink: Callable[[dict], None]) -> int:
        circuit = self.circuits.setdefault(adapter_key, ProviderCircuit())
        now = time.time()
        if now < circuit.opened_until:
            return 0

        adapter = registry.create(adapter_key)
        for attempt in range(1, 4):
            try:
                records = adapter.refresh()
                for record in records:
                    sink({"adapter": adapter_key, "external_id": record.external_id, "payload": record.payload})
                circuit.failures = 0
                return len(records)
            except Exception:
                time.sleep(0.2 * (2**attempt))

        circuit.failures += 1
        if circuit.failures >= self.max_failures:
            circuit.opened_until = now + self.cooldown_seconds
        return 0
