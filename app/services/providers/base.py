from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ProviderRecord:
    external_id: str
    name: str
    payload: dict[str, Any]


class ProviderAdapter(ABC):
    name: str

    @abstractmethod
    def refresh(self) -> list[ProviderRecord]:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> dict[str, Any]:
        raise NotImplementedError
