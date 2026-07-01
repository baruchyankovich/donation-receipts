"""Cross-platform helpers for opening files and URLs.

Uses :mod:`subprocess` with argument lists (never a shell string), so paths
containing spaces or shell metacharacters cannot lead to command injection.
"""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def open_path(path: str | Path) -> None:
    """Open a file or folder with the OS default application."""
    path = str(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: PTH123 (Windows API)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def open_url(url: str) -> None:
    """Open a URL (http/https/mailto) in the default handler."""
    webbrowser.open(url)


def open_in_browser(path: str | Path) -> None:
    """Open a local HTML file in the default web browser."""
    webbrowser.open(Path(path).as_uri())
