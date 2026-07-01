"""Application composition root: build dependencies and run the UI."""

from __future__ import annotations

from .database import Database
from .paths import user_data_dir
from .ui.main_window import MainWindow


def create_window() -> MainWindow:
    """Create the main window wired to the on-disk database."""
    database = Database(user_data_dir() / "receipts.db")
    return MainWindow(database)


def main() -> None:
    """Entry point: open the database and start the Tkinter event loop."""
    create_window().mainloop()


if __name__ == "__main__":
    main()
