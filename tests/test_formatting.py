"""Tests for parsing and formatting helpers."""

from datetime import date

import pytest

from receipts.formatting import (
    escape_html,
    normalize_phone_e164_il,
    parse_amount,
    parse_date,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("1,200 ₪", 1200.0), ("50", 50.0), ("", 0.0), ("abc", 0.0), (None, 0.0)],
)
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("05/03/2025", date(2025, 3, 5)),
        ("5.3.2025", date(2025, 3, 5)),
        ("05-03-25", date(2025, 3, 5)),
        ("nonsense", None),
        ("", None),
    ],
)
def test_parse_date(text, expected):
    assert parse_date(text) == expected


@pytest.mark.parametrize(
    ("phone", "expected"),
    [
        ("050-1234567", "972501234567"),
        ("+972 54 222 2222", "972542222222"),
        ("972541111111", "972541111111"),
        ("", ""),
        ("no digits", ""),
    ],
)
def test_normalize_phone(phone, expected):
    assert normalize_phone_e164_il(phone) == expected


def test_escape_html_blocks_injection():
    assert escape_html('<script>"x"</script>') == ("&lt;script&gt;&quot;x&quot;&lt;/script&gt;")
