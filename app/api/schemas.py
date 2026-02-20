from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    amount_cents: int = Field(ge=0)
    incurred_at: date
    category: str = "medical"
    memo: str = ""


class ExpenseOut(BaseModel):
    id: int
    amount_cents: int
    incurred_at: date
    category: str


class ProviderOut(BaseModel):
    id: int
    name: str
    specialty: str | None = None
    selector_color: str
    estimated_copay_cents: int = 0
    adapter_type: str
