from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from io import StringIO


@dataclass(slots=True)
class PaymentImportRow:
    date: datetime
    amount_cents: int
    description: str
    idempotency_key: str


def parse_payment_csv(text: str, date_col: str, amount_col: str, desc_col: str) -> list[PaymentImportRow]:
    rows = list(csv.DictReader(StringIO(text)))
    parsed: list[PaymentImportRow] = []
    for row in rows:
        date = datetime.strptime(row[date_col], "%Y-%m-%d")
        amount_cents = int(round(float(row[amount_col]) * 100))
        desc = row.get(desc_col, "")
        idem = f"{date.date().isoformat()}|{amount_cents}|{desc.strip().lower()}"
        parsed.append(PaymentImportRow(date=date, amount_cents=amount_cents, description=desc, idempotency_key=idem))
    return parsed
