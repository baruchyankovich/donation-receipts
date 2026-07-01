"""Tests for the SQLite persistence layer."""

import sqlite3

import pytest

from receipts.database import Database
from receipts.models import OrganizationSettings

from .conftest import make_receipt


def test_insert_and_get_roundtrip(db):
    db.insert(make_receipt(1, name="רות", value="250"))
    stored = db.get(1)
    assert stored is not None
    assert stored.donor_name == "רות"
    assert stored.amount == 250.0


def test_numbering_starts_at_configured_value(db):
    settings = db.load_settings()
    settings.starting_receipt_number = 1151
    db.save_settings(settings)
    assert db.next_receipt_number() == 1151
    db.insert(make_receipt(1151))
    assert db.next_receipt_number() == 1152


def test_update_and_delete(db):
    db.insert(make_receipt(5, name="לפני"))
    receipt = db.get(5)
    receipt.donor_name = "אחרי"
    db.update(receipt)
    assert db.get(5).donor_name == "אחרי"
    db.delete(5)
    assert db.get(5) is None


def test_donor_autocomplete_and_contact(db):
    db.insert(make_receipt(1, name="דוד לוי", value="10"))
    db.insert(make_receipt(2, name="דוד לוי", value="20"))
    db.insert(make_receipt(3, name="מרים"))
    assert db.donor_names("דוד") == ["דוד לוי"]
    address, phone, email = db.latest_donor_contact("דוד לוי")
    assert phone == "050-1234567"
    assert email == "donor@example.com"


def test_donor_names_treats_like_wildcards_literally(db):
    db.insert(make_receipt(1, name="דוד"))
    db.insert(make_receipt(2, name="רחל"))
    # "%" and "_" are LIKE wildcards; used as a literal prefix they match nothing.
    assert db.donor_names("%") == []
    assert db.donor_names("_") == []
    assert db.donor_names("ד") == ["דוד"]


def test_insert_many_is_atomic(db):
    good = make_receipt(1)
    duplicate = make_receipt(1)  # same receipt_no -> UNIQUE violation mid-batch
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_many([good, duplicate])
    assert db.all_receipts() == []  # whole batch rolled back, nothing committed


def test_settings_persist(db):
    db.save_settings(OrganizationSettings(org_name="עמותת בדיקה", starting_receipt_number=500))
    reloaded = db.load_settings()
    assert reloaded.org_name == "עמותת בדיקה"
    assert reloaded.starting_receipt_number == 500


def test_migration_adds_email_column(tmp_path):
    """A legacy DB without an ``email`` column is upgraded, not wiped."""
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE receipts (id INTEGER PRIMARY KEY, receipt_no INTEGER UNIQUE, "
        "donor_name TEXT, value_num TEXT);"
        "INSERT INTO receipts (receipt_no, donor_name) VALUES (7, 'ותיק');"
    )
    conn.commit()
    conn.close()

    db = Database(path)
    columns = {row[1] for row in sqlite3.connect(path).execute("PRAGMA table_info(receipts)")}
    assert "email" in columns
    assert db.get(7).donor_name == "ותיק"
