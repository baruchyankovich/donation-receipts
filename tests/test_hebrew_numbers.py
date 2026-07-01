"""Tests for Hebrew number-to-words conversion."""

import pytest

from receipts.hebrew_numbers import amount_in_shekels, number_to_words


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "אפס"),
        (3, "שלושה"),
        (10, "עשרה"),
        (13, "שלושה עשר"),
        (21, "עשרים ואחד"),
        (100, "מאה"),
        (103, "מאה ושלושה"),
        (123, "מאה עשרים ושלושה"),
        (200, "מאתיים"),
        (999, "תשע מאות תשעים ותשעה"),
        (1000, "אלף"),
        (1005, "אלף וחמישה"),
        (1234, "אלף מאתיים שלושים וארבעה"),
        (10000, "עשרת אלפים"),
    ],
)
def test_number_to_words(value, expected):
    assert number_to_words(value) == expected


def test_negative_is_empty():
    assert number_to_words(-5) == ""


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "אפס שקלים"),
        (1, "שקל אחד"),
        (2, "שני שקלים"),
        (250, "מאתיים וחמישים שקלים"),
        (1200.4, "אלף ומאתיים שקלים"),  # rounds to nearest shekel
    ],
)
def test_amount_in_shekels(amount, expected):
    assert amount_in_shekels(amount) == expected
