from __future__ import annotations

from app.services.providers.base import ProviderAdapter, ProviderRecord
from app.services.providers.registry import registry


class AggregatorStubAdapter(ProviderAdapter):
    name = "aggregator_stub"

    def refresh(self) -> list[ProviderRecord]:
        return [
            ProviderRecord(
                external_id="stub-1",
                name="Acme Health",
                payload={"plans": ["PPO", "HDHP"], "members": 2},
            )
        ]

    def healthcheck(self) -> dict[str, str]:
        return {"status": "ok", "adapter": self.name}


registry.register("aggregator_stub", AggregatorStubAdapter)
