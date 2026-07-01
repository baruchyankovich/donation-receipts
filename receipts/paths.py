"""Resolve the per-user data directory where the database and exports live."""

from __future__ import annotations

from pathlib import Path

_APP_FOLDER_NAME = "DonationReceipts"


def user_data_dir() -> Path:
    """Return (creating if needed) the directory that holds all app data.

    Kept in the user's *Documents* folder so it is easy to find and back up,
    and so it survives replacing the executable with a newer version.
    """
    directory = Path.home() / "Documents" / _APP_FOLDER_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory
