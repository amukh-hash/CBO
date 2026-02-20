from __future__ import annotations

from typing import Dict, Type

from app.services.providers.base import ProviderAdapter


class ProviderRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, Type[ProviderAdapter]] = {}

    def register(self, key: str, adapter: Type[ProviderAdapter]) -> None:
        self._adapters[key] = adapter

    def create(self, key: str) -> ProviderAdapter:
        if key not in self._adapters:
            raise KeyError(f"Unknown provider adapter: {key}")
        return self._adapters[key]()

    def list_adapters(self) -> list[str]:
        return sorted(self._adapters.keys())


registry = ProviderRegistry()

SUPPORTED_PROVIDER_CATALOG = [
    "Aetna",
    "Anthem Blue Cross",
    "Cigna",
    "UnitedHealthcare",
    "Kaiser Permanente",
    "Humana",
    "Molina Healthcare",
    "Centene",
    "Health Care Service Corporation",
    "Oscar Health",
    "CVS/Aetna",
    "Elevance Health",
]
