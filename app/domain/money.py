from __future__ import annotations

import re

_MONEY_RE = re.compile(r"^\s*\$?\s*([-+]?[0-9][0-9,]*)(?:\.([0-9]{1,2}))?\s*$")


def parse_money_to_cents(value: str) -> int:
    match = _MONEY_RE.match(value)
    if not match:
        raise ValueError(f"Invalid money amount: {value!r}")
    dollars = int(match.group(1).replace(",", ""))
    cents = match.group(2) or "0"
    cents = int(cents.ljust(2, "0"))
    sign = -1 if dollars < 0 else 1
    return dollars * 100 + sign * cents


def cents_to_money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    abs_cents = abs(cents)
    dollars, rem = divmod(abs_cents, 100)
    return f"{sign}${dollars:,}.{rem:02d}"
