"""Shared pytest fixtures."""

import pytest

from receipts.database import Database
from receipts.hebrew_numbers import amount_in_shekels
from receipts.models import Receipt


@pytest.fixture
def db(tmp_path):
    """A fresh, isolated database backed by a temporary file."""
    return Database(tmp_path / "receipts.db")


def make_receipt(no, name="דוד", value="100", when="01/07/2026", product="מזון"):
    """Helper to build a fully-populated receipt for tests."""
    return Receipt(
        receipt_no=no,
        date=when,
        donor_name=name,
        phone="050-1234567",
        email="donor@example.com",
        product=product,
        value_num=value,
        value_words=amount_in_shekels(float(value)),
    )
