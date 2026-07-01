"""In-memory filtering and summarizing of receipts for the list view."""

from __future__ import annotations

from datetime import date
from enum import Enum

from .formatting import parse_date
from .models import Receipt

_SEARCHABLE = ("receipt_no", "donor_name", "product", "address", "phone", "purpose")


class Period(str, Enum):
    """Date-range presets offered in the UI."""

    ALL = "all"
    THIS_MONTH = "month"
    THIS_YEAR = "year"
    CUSTOM = "range"


def _matches_search(receipt: Receipt, needle: str) -> bool:
    haystack = " ".join(str(getattr(receipt, f) or "") for f in _SEARCHABLE).lower()
    return needle in haystack


def _matches_period(
    receipt: Receipt,
    period: Period,
    date_from: date | None,
    date_to: date | None,
    today: date,
) -> bool:
    if period is Period.ALL:
        return True
    receipt_date = parse_date(receipt.date)
    if receipt_date is None:
        return False
    if period is Period.THIS_MONTH:
        return (receipt_date.month, receipt_date.year) == (today.month, today.year)
    if period is Period.THIS_YEAR:
        return receipt_date.year == today.year
    # Period.CUSTOM
    if date_from and receipt_date < date_from:
        return False
    return not (date_to and receipt_date > date_to)


def filter_receipts(
    receipts: list[Receipt],
    search: str = "",
    period: Period = Period.ALL,
    date_from: date | None = None,
    date_to: date | None = None,
    *,
    today: date | None = None,
) -> list[Receipt]:
    """Return the subset of ``receipts`` matching the search text and period."""
    today = today or date.today()
    needle = (search or "").strip().lower()
    return [
        receipt
        for receipt in receipts
        if (not needle or _matches_search(receipt, needle))
        and _matches_period(receipt, period, date_from, date_to, today)
    ]


def summarize(receipts: list[Receipt]) -> tuple[int, float]:
    """Return ``(count, total_amount)`` for a list of receipts."""
    return len(receipts), sum(receipt.amount for receipt in receipts)
