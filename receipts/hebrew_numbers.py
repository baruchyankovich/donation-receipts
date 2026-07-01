"""Convert integer amounts to their Hebrew words representation.

This module is intentionally free of any I/O or UI dependencies so it can be
unit-tested in isolation. The grammar follows standard Hebrew number words
used when counting the (masculine) noun "שקל" (shekel), including the
conjunctive *vav* placed before the final component (e.g. ``123`` →
``"מאה עשרים ושלושה"``).
"""

from __future__ import annotations

_UNITS = ["", "אחד", "שניים", "שלושה", "ארבעה", "חמישה", "שישה", "שבעה", "שמונה", "תשעה"]
_TEENS = [
    "אחד עשר",
    "שנים עשר",
    "שלושה עשר",
    "ארבעה עשר",
    "חמישה עשר",
    "שישה עשר",
    "שבעה עשר",
    "שמונה עשר",
    "תשעה עשר",
]
_TENS = ["", "", "עשרים", "שלושים", "ארבעים", "חמישים", "שישים", "שבעים", "שמונים", "תשעים"]
_HUNDREDS = [
    "",
    "מאה",
    "מאתיים",
    "שלוש מאות",
    "ארבע מאות",
    "חמש מאות",
    "שש מאות",
    "שבע מאות",
    "שמונה מאות",
    "תשע מאות",
]
_THOUSANDS_CONSTRUCT = ["", "", "", "שלושת", "ארבעת", "חמשת", "ששת", "שבעת", "שמונת", "תשעת"]


def _tens_and_units(value: int) -> str:
    """Return the words for a number in the range 1–99."""
    if value < 10:
        return _UNITS[value]
    if value == 10:
        return "עשרה"
    if value < 20:
        return _TEENS[value - 11]
    tens, units = divmod(value, 10)
    if units:
        return f"{_TENS[tens]} ו{_UNITS[units]}"
    return _TENS[tens]


def _under_thousand_parts(value: int) -> list[str]:
    """Split 0–999 into hundreds and tens/units word components."""
    parts: list[str] = []
    hundreds, remainder = divmod(value, 100)
    if hundreds:
        parts.append(_HUNDREDS[hundreds])
    if remainder:
        parts.append(_tens_and_units(remainder))
    return parts


def _join_with_vav(parts: list[str]) -> str:
    """Join word components, prefixing the last with the conjunctive *vav*.

    The *vav* is only added when the last component does not already contain a
    conjoined token (so ``"עשרים ושלושה"`` is not turned into
    ``"ועשרים ושלושה"``).
    """
    parts = [part for part in parts if part]
    if len(parts) > 1 and not any(tok.startswith("ו") for tok in parts[-1].split()):
        parts = parts[:-1] + [f"ו{parts[-1]}"]
    return " ".join(parts)


def _thousands_phrase(thousands: int) -> str:
    """Return the words for the thousands component."""
    if thousands == 1:
        return "אלף"
    if thousands == 2:
        return "אלפיים"
    if 3 <= thousands <= 9:
        return f"{_THOUSANDS_CONSTRUCT[thousands]} אלפים"
    if thousands == 10:
        return "עשרת אלפים"
    return f"{_join_with_vav(_under_thousand_parts(thousands))} אלף"


def number_to_words(value: int) -> str:
    """Return the Hebrew words for a non-negative integer.

    Returns an empty string for negative input.

    >>> number_to_words(0)
    'אפס'
    >>> number_to_words(123)
    'מאה עשרים ושלושה'
    """
    value = int(value)
    if value == 0:
        return "אפס"
    if value < 0:
        return ""
    parts: list[str] = []
    thousands, remainder = divmod(value, 1000)
    if thousands:
        parts.append(_thousands_phrase(thousands))
    parts.extend(_under_thousand_parts(remainder))
    return _join_with_vav(parts)


def amount_in_shekels(amount: float | int) -> str:
    """Return a rounded shekel amount spelled out, suffixed with the currency.

    >>> amount_in_shekels(1)
    'שקל אחד'
    >>> amount_in_shekels(250)
    'מאתיים וחמישים שקלים'
    """
    value = int(round(amount))
    if value < 0:
        return ""
    if value == 0:
        return "אפס שקלים"
    if value == 1:
        return "שקל אחד"
    if value == 2:
        return "שני שקלים"
    return f"{number_to_words(value)} שקלים"
