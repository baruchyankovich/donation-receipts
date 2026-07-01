"""Backup and restore of the local database.

A *backup* copies the SQLite file (and an Excel snapshot) into a timestamped
folder under a destination the user chooses — pointing it at a synced folder
(e.g. Google Drive / OneDrive) effectively backs up to the cloud.

*Restore* supports two strategies:

* **merge** – add only receipts whose numbers are missing locally; never
  deletes or overwrites existing data.
* **replace** – swap the whole database file for the backup (used when moving
  to a new machine). Callers should snapshot the current DB first.
"""

from __future__ import annotations

import datetime
import shutil
import sqlite3
from pathlib import Path

from . import excel_export
from .database import Database
from .models import Receipt


def create_backup(db: Database, destination: str | Path) -> Path:
    """Copy the database and an Excel export into a timestamped subfolder.

    Returns the created folder path.
    """
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    folder = Path(destination) / f"backup_{stamp}"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db.path, folder / "receipts.db")
    excel_export.export(db.all_receipts(), folder / "receipts.xlsx")
    return folder


def read_receipts(backup_db_path: str | Path) -> list[Receipt] | None:
    """Read receipts from an external backup DB, or ``None`` if it is invalid."""
    try:
        conn = sqlite3.connect(str(backup_db_path))
        conn.row_factory = sqlite3.Row
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(receipts)")}
            if "receipt_no" not in columns:
                return None
            rows = conn.execute("SELECT * FROM receipts").fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return [Receipt.from_mapping(dict(row)) for row in rows]


def merge_missing(db: Database, receipts: list[Receipt]) -> tuple[int, int]:
    """Insert receipts whose numbers are absent locally.

    Returns ``(added, skipped)``.
    """
    missing = [receipt for receipt in receipts if not db.exists(receipt.receipt_no)]
    db.insert_many(missing)  # single transaction — all-or-nothing
    return len(missing), len(receipts) - len(missing)


def replace_database(db: Database, backup_db_path: str | Path) -> None:
    """Overwrite the live database with a backup file, then re-open the schema."""
    shutil.copy2(str(backup_db_path), str(db.path))
    db.reopen()  # re-run additive migration on the restored file


def snapshot_before_restore(db: Database) -> Path | None:
    """Save a safety copy of the current DB next to it before a destructive op."""
    if not db.path.exists():
        return None
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    safety = db.path.with_name(f"before_restore_{stamp}.db")
    shutil.copy2(db.path, safety)
    return safety
