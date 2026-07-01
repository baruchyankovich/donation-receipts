"""SQLite persistence for receipts and organization settings.

Every query is parameterized; no user input is ever interpolated into SQL.
The :class:`Database` owns a file path and opens a short-lived connection per
operation, which keeps the app safe to use from a single-threaded UI and makes
file-level backup/restore trivial (no long-lived locks).
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

from .models import OrganizationSettings, Receipt

_SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_no  INTEGER UNIQUE,
    date        TEXT,
    donor_name  TEXT,
    address     TEXT,
    phone       TEXT,
    email       TEXT,
    purpose     TEXT,
    product     TEXT,
    value_num   TEXT,
    value_words TEXT,
    notes       TEXT,
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""


class Database:
    """Thin, well-typed wrapper around the SQLite schema."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._create_schema()

    # -- connection helpers -------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path))
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            self._migrate(conn)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Additively bring older databases up to date (never destructive)."""
        columns = {row[1] for row in conn.execute("PRAGMA table_info(receipts)")}
        if "email" not in columns:
            conn.execute("ALTER TABLE receipts ADD COLUMN email TEXT")

    # -- settings (key/value) ----------------------------------------------
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def load_settings(self) -> OrganizationSettings:
        defaults = OrganizationSettings()
        raw = {
            "org_name": self.get_setting("org_name", defaults.org_name),
            "address_line": self.get_setting("address_line", defaults.address_line),
            "services_line": self.get_setting("services_line", defaults.services_line),
            "backup_dir": self.get_setting("backup_dir", "") or "",
            "custom_logo_base64": self.get_setting("logo_base64", "") or "",
            "custom_logo_mime": self.get_setting("logo_mime", "") or "",
        }
        start = self.get_setting("starting_receipt_number", str(defaults.starting_receipt_number))
        raw["starting_receipt_number"] = (
            int(start) if start and start.isdigit() else defaults.starting_receipt_number
        )
        return OrganizationSettings(**raw)

    def save_settings(self, settings: OrganizationSettings) -> None:
        for key in OrganizationSettings.TEXT_KEYS:
            self.set_setting(key, str(getattr(settings, key)))
        self.set_setting("logo_base64", settings.custom_logo_base64)
        self.set_setting("logo_mime", settings.custom_logo_mime)

    # -- receipts -----------------------------------------------------------
    def next_receipt_number(self) -> int:
        with self._connect() as conn:
            highest = conn.execute("SELECT MAX(receipt_no) FROM receipts").fetchone()[0]
        start = self.load_settings().starting_receipt_number
        return start if highest is None else max(highest + 1, start)

    def exists(self, receipt_no: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM receipts WHERE receipt_no = ?", (receipt_no,)
            ).fetchone()
        return row is not None

    def insert(self, receipt: Receipt) -> None:
        data = receipt.as_dict()
        data["created_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        columns = (*Receipt.COLUMNS, "created_at")
        placeholders = ", ".join("?" for _ in columns)
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO receipts ({', '.join(columns)}) VALUES ({placeholders})",
                tuple(data[col] for col in columns),
            )

    def update(self, receipt: Receipt) -> None:
        editable = [c for c in Receipt.COLUMNS if c != "receipt_no"]
        assignments = ", ".join(f"{col} = ?" for col in editable)
        data = receipt.as_dict()
        with self._connect() as conn:
            conn.execute(
                f"UPDATE receipts SET {assignments} WHERE receipt_no = ?",
                (*[data[col] for col in editable], receipt.receipt_no),
            )

    def delete(self, receipt_no: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM receipts WHERE receipt_no = ?", (receipt_no,))

    def get(self, receipt_no: int) -> Receipt | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM receipts WHERE receipt_no = ?", (receipt_no,)
            ).fetchone()
        return Receipt.from_mapping(dict(row)) if row else None

    def all_receipts(self) -> list[Receipt]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM receipts ORDER BY receipt_no DESC").fetchall()
        return [Receipt.from_mapping(dict(row)) for row in rows]

    def donor_names(self, prefix: str = "", limit: int = 8) -> list[str]:
        """Return distinct donor names starting with ``prefix``, most recent first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT donor_name, MAX(receipt_no) AS recent FROM receipts "
                "WHERE donor_name LIKE ? AND TRIM(donor_name) <> '' "
                "GROUP BY donor_name ORDER BY recent DESC LIMIT ?",
                (f"{prefix}%", limit),
            ).fetchall()
        return [row["donor_name"] for row in rows]

    def latest_donor_contact(self, name: str) -> tuple[str, str, str]:
        """Return ``(address, phone, email)`` from the donor's most recent receipt."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT address, phone, email FROM receipts WHERE donor_name = ? "
                "ORDER BY receipt_no DESC LIMIT 1",
                (name,),
            ).fetchone()
        if not row:
            return "", "", ""
        return row["address"] or "", row["phone"] or "", row["email"] or ""

    def receipts_for_donor(self, name: str) -> list[Receipt]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM receipts WHERE donor_name = ? ORDER BY receipt_no DESC",
                (name,),
            ).fetchall()
        return [Receipt.from_mapping(dict(row)) for row in rows]
