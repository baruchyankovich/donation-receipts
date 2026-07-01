"""Tests for in-memory filtering and summarizing."""

from datetime import date

from receipts.filters import Period, filter_receipts, summarize

from .conftest import make_receipt

TODAY = date(2026, 7, 15)
RECEIPTS = [
    make_receipt(1, name="דוד", value="1200", when="05/03/2025", product="עוף"),
    make_receipt(2, name="דוד", value="90", when="10/07/2026", product="חלות"),
    make_receipt(3, name="רות", value="45", when="01/07/2026", product="שמן"),
]


def test_search_matches_product():
    result = filter_receipts(RECEIPTS, search="חלות")
    assert [r.receipt_no for r in result] == [2]


def test_this_month():
    result = filter_receipts(RECEIPTS, period=Period.THIS_MONTH, today=TODAY)
    assert {r.receipt_no for r in result} == {2, 3}


def test_this_year():
    result = filter_receipts(RECEIPTS, period=Period.THIS_YEAR, today=TODAY)
    assert {r.receipt_no for r in result} == {2, 3}


def test_custom_range():
    result = filter_receipts(
        RECEIPTS,
        period=Period.CUSTOM,
        date_from=date(2026, 6, 1),
        date_to=date(2026, 6, 30),
        today=TODAY,
    )
    assert result == []


def test_summarize():
    count, total = summarize(RECEIPTS)
    assert count == 3
    assert total == 1335.0
