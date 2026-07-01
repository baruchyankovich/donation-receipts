"""Donation receipts — a local, offline desktop app for nonprofits.

Manage in-kind (goods) donation receipts: record donors and donations,
store them locally (SQLite), export to Excel, back up / restore, and print
a receipt that can be saved as PDF.

The package is organized into small, single-responsibility modules:

* :mod:`receipts.hebrew_numbers` – convert amounts to Hebrew words (pure).
* :mod:`receipts.formatting`     – parsing/formatting helpers (pure).
* :mod:`receipts.models`         – ``Receipt`` and ``OrganizationSettings``.
* :mod:`receipts.database`       – SQLite persistence (parameterized queries).
* :mod:`receipts.backup`         – backup and restore services.
* :mod:`receipts.documents`      – HTML rendering for receipts/summaries.
* :mod:`receipts.excel_export`   – spreadsheet export.
* :mod:`receipts.ui`             – the Tkinter user interface.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
