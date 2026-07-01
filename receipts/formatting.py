"""Small, pure parsing and formatting helpers shared across the app."""

from __future__ import annotations

import datetime
import html
from datetime import date

# Date formats accepted when parsing user-entered dates.
_DATE_FORMATS = ("%d/%m/%Y", "%d/%m/%y")
DISPLAY_DATE_FORMAT = "%d/%m/%Y"


def parse_amount(text: str | float | None) -> float:
    """Parse a monetary value from arbitrary text.

    Non-numeric characters (currency signs, thousands separators, spaces) are
    ignored. Returns ``0.0`` when nothing numeric is found.

    >>> parse_amount("1,200 ₪")
    1200.0
    """
    if text is None:
        return 0.0
    digits = "".join(ch for ch in str(text) if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


def parse_date(text: str | None) -> date | None:
    """Parse a ``DD/MM/YYYY`` (or ``DD/MM/YY``) date, tolerating ``.``/``-``.

    Returns ``None`` when the text cannot be parsed.
    """
    if not text:
        return None
    normalized = str(text).strip().replace("-", "/").replace(".", "/")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    return None


def today_string() -> str:
    """Return today's date formatted for display."""
    return date.today().strftime(DISPLAY_DATE_FORMAT)


def normalize_phone_e164_il(phone: str | None) -> str:
    """Normalize an Israeli phone number to international digits (``972…``).

    Used to build WhatsApp deep links. Returns an empty string when the input
    contains no digits.

    >>> normalize_phone_e164_il("050-1234567")
    '972501234567'
    """
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith("972"):
        return digits
    if digits.startswith("0"):
        return "972" + digits[1:]
    return digits


def escape_html(value: object) -> str:
    """Escape a value for safe inclusion in HTML text, keeping line breaks."""
    return html.escape("" if value is None else str(value)).replace("\n", "<br>")
