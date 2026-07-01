"""Reusable Tkinter widgets used across the UI.

* :class:`FlatButton` – a colored, flat button that renders identically on
  macOS and Windows (native ``tk.Button`` ignores ``bg`` on macOS Aqua, which
  produces unreadable light-on-light text).
* :class:`AutocompleteEntry` – a text entry with a dropdown of suggestions.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable

_ROW_PIXELS = 22
_MAX_VISIBLE_SUGGESTIONS = 8


def _shade(hex_color: str, factor: float) -> str:
    """Return ``hex_color`` scaled toward black by ``factor`` (0–1).

    Accepts ``#rgb`` and ``#rrggbb``; returns the input unchanged if it is not
    a valid hex color, so callers never crash on unexpected values.
    """
    value = str(hex_color).lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return hex_color
    try:
        channels = [int(value[i : i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return hex_color
    scaled = (max(0, min(255, int(c * factor))) for c in channels)
    return "#{:02x}{:02x}{:02x}".format(*scaled)


class FlatButton(tk.Label):
    """A colored button implemented as a ``Label`` for cross-platform styling."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        background: str,
        foreground: str = "white",
        padx: int = 12,
        pady: int = 8,
    ) -> None:
        super().__init__(
            master,
            text=text,
            bg=background,
            fg=foreground,
            font=("Arial", 11, "bold"),
            padx=padx,
            pady=pady,
            cursor="hand2",
        )
        self._base = background
        self._command = command
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _e: self.configure(bg=_shade(self._base, 0.85)))
        self.bind("<Leave>", lambda _e: self.configure(bg=self._base))

    def _on_click(self, _event: tk.Event) -> None:
        self.configure(bg=_shade(self._base, 0.70))
        self.after(90, lambda: self.configure(bg=self._base))
        self._command()


class AutocompleteEntry(tk.Entry):
    """An entry that shows a right-aligned dropdown of matching suggestions.

    ``suggestions`` is called with the current text and returns candidate
    strings; ``on_select`` is invoked with the chosen value.
    """

    def __init__(
        self,
        master: tk.Misc,
        suggestions: Callable[[str], list[str]],
        on_select: Callable[[str], None] | None = None,
        **entry_options: object,
    ) -> None:
        super().__init__(master, **entry_options)
        self._suggestions = suggestions
        self._on_select = on_select
        self._popup: tk.Toplevel | None = None
        self._listbox: tk.Listbox | None = None
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<FocusOut>", lambda _e: self.after(200, self._close_if_unfocused))
        self.bind("<Escape>", lambda _e: self._close())
        self.bind("<Down>", self._focus_first)

    # -- events -------------------------------------------------------------
    def _on_key_release(self, event: tk.Event) -> None:
        if event.keysym in {"Up", "Down", "Return", "Escape", "Left", "Right", "Tab"}:
            return
        text = self.get().strip()
        if not text:
            self._close()
            return
        try:
            matches = self._suggestions(text)
        except Exception:  # never let a lookup error break typing
            matches = []
        if not matches or (len(matches) == 1 and matches[0] == text):
            self._close()
        else:
            self._show(matches)

    def _focus_first(self, _event: tk.Event) -> str:
        if self._listbox and self._popup and self._popup.winfo_exists():
            self._listbox.focus_set()
            self._listbox.selection_clear(0, "end")
            self._listbox.selection_set(0)
            self._listbox.activate(0)
        return "break"

    def _select(self, _event: tk.Event | None = None) -> None:
        if not (self._listbox and self._popup and self._popup.winfo_exists()):
            return
        selection = self._listbox.curselection()
        if not selection:
            return
        value = self._listbox.get(selection[0])
        self.delete(0, "end")
        self.insert(0, value)
        self._close()
        self.focus_set()
        if self._on_select:
            self._on_select(value)

    # -- popup lifecycle ----------------------------------------------------
    def _show(self, matches: list[str]) -> None:
        height = min(_MAX_VISIBLE_SUGGESTIONS, len(matches))
        if self._popup is None or not self._popup.winfo_exists():
            self._popup = tk.Toplevel(self)
            self._popup.wm_overrideredirect(True)
            self._listbox = tk.Listbox(
                self._popup,
                font=("Arial", 11),
                activestyle="dotbox",
                relief="solid",
                bd=1,
                highlightthickness=1,
            )
            # right-align items (Tk 8.6.5+); silently ignored on older builds
            with contextlib.suppress(tk.TclError):
                self._listbox.configure(justify="right")
            self._listbox.pack(fill="both", expand=True)
            self._listbox.bind("<Return>", self._select)
            self._listbox.bind("<Double-Button-1>", self._select)
            self._listbox.bind("<Button-1>", lambda _e: self.after(10, self._select))

        assert self._listbox is not None
        self._listbox.delete(0, "end")
        for match in matches:
            self._listbox.insert("end", match)
        self._listbox.configure(height=height)
        try:
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height()
            width = max(self.winfo_width(), 180)
            self._popup.wm_geometry(f"{width}x{height * _ROW_PIXELS}+{x}+{y}")
            self._popup.deiconify()
            self._popup.lift()
        except tk.TclError:
            pass

    def _close_if_unfocused(self) -> None:
        try:
            if self.focus_get() is not self._listbox:
                self._close()
        except Exception:
            self._close()

    def _close(self) -> None:
        if self._popup is not None:
            with contextlib.suppress(Exception):
                self._popup.destroy()
            self._popup = None
            self._listbox = None
