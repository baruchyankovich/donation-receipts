"""Tests for backup creation and the two restore strategies."""

from receipts import backup
from receipts.database import Database

from .conftest import make_receipt


def test_create_backup_writes_db_and_excel(db, tmp_path):
    db.insert(make_receipt(1))
    folder = backup.create_backup(db, tmp_path / "drive")
    names = {p.name for p in folder.iterdir()}
    assert names == {"receipts.db", "receipts.xlsx"}


def test_read_receipts_rejects_invalid_file(tmp_path):
    bogus = tmp_path / "not-a-backup.db"
    bogus.write_text("just text")
    assert backup.read_receipts(bogus) is None
    assert backup.read_receipts(tmp_path / "missing.db") is None


def test_merge_only_adds_missing(db, tmp_path):
    db.insert(make_receipt(1, name="קיים"))
    source = Database(tmp_path / "source.db")
    source.insert(make_receipt(1, name="שונה"))  # overlaps -> skipped
    source.insert(make_receipt(2, name="חדש"))  # new -> added

    added, skipped = backup.merge_missing(db, source.all_receipts())
    assert (added, skipped) == (1, 1)
    assert db.get(1).donor_name == "קיים"  # existing left untouched
    assert db.get(2).donor_name == "חדש"


def test_replace_swaps_entire_database(db, tmp_path):
    db.insert(make_receipt(1, name="ישן"))
    source_path = tmp_path / "source.db"
    source = Database(source_path)
    source.insert(make_receipt(9, name="מגיבוי"))

    backup.replace_database(db, source_path)
    assert db.get(1) is None
    assert db.get(9).donor_name == "מגיבוי"
