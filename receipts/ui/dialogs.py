"""Modal dialogs: organization settings and per-donor history."""

from __future__ import annotations

import base64
import tkinter as tk
from collections.abc import Callable
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..database import Database
from ..filters import summarize
from ..formatting import parse_date
from ..models import OrganizationSettings, Receipt
from .widgets import FlatButton

_MAX_LOGO_BYTES = 2_000_000
_LOGO_MIME_BY_EXT = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
}
_BG = "#f4f4f4"


class SettingsDialog(tk.Toplevel):
    """Edit organization details, logo, starting number and backup folder."""

    _FIELDS = (
        ("org_name", "שם הארגון (בקבלה):"),
        ("address_line", "כתובת וטלפון (תחתית):"),
        ("services_line", "שורת שירותים (תחתית):"),
        ("starting_receipt_number", "מספר קבלה התחלתי:"),
    )

    def __init__(self, parent: tk.Misc, db: Database, on_saved: Callable[[], None]) -> None:
        super().__init__(parent)
        self._db = db
        self._on_saved = on_saved
        self._settings = db.load_settings()
        self._pending_logo: tuple[str, str] | None = None  # (base64, mime) or reset("","")

        self.title("הגדרות")
        self.geometry("600x470")
        self.configure(bg=_BG)
        self.transient(parent)
        self.columnconfigure(0, weight=1)

        self._vars: dict[str, tk.StringVar] = {}
        for row, (key, label) in enumerate(self._FIELDS):
            tk.Label(self, text=label, anchor="e", bg=_BG, font=("Arial", 11, "bold")).grid(
                row=row, column=1, sticky="e", padx=8, pady=8
            )
            var = tk.StringVar(value=str(getattr(self._settings, key)))
            self._vars[key] = var
            tk.Entry(self, textvariable=var, width=46, justify="right").grid(
                row=row, column=0, padx=8, pady=8
            )

        self._build_logo_row(len(self._FIELDS))
        self._build_backup_row(len(self._FIELDS) + 1)
        FlatButton(self, "💾 שמירה", self._save, background="#2e7d32", padx=16, pady=8).grid(
            row=len(self._FIELDS) + 2, column=0, pady=16
        )

    def _build_logo_row(self, row: int) -> None:
        tk.Label(self, text="לוגו הקבלה:", anchor="e", bg=_BG, font=("Arial", 11, "bold")).grid(
            row=row, column=1, sticky="e", padx=8, pady=8
        )
        self._logo_state = tk.StringVar(
            value="לוגו מותאם אישית" if self._settings.has_custom_logo() else "לוגו ברירת מחדל"
        )
        frame = tk.Frame(self, bg=_BG)
        frame.grid(row=row, column=0, sticky="we", padx=8, pady=8)
        FlatButton(
            frame, "🖼️ החלף לוגו", self._choose_logo, background="#6a1b9a", padx=8, pady=5
        ).pack(side="right", padx=3)
        FlatButton(
            frame, "↩ ברירת מחדל", self._reset_logo, background="#777777", padx=8, pady=5
        ).pack(side="right", padx=3)
        tk.Label(frame, textvariable=self._logo_state, bg=_BG, fg="#555").pack(side="right", padx=8)

    def _build_backup_row(self, row: int) -> None:
        tk.Label(self, text="תיקיית גיבוי:", anchor="e", bg=_BG, font=("Arial", 11, "bold")).grid(
            row=row, column=1, sticky="e", padx=8, pady=8
        )
        self._backup_var = tk.StringVar(value=self._settings.backup_dir or "(לא נבחרה)")
        frame = tk.Frame(self, bg=_BG)
        frame.grid(row=row, column=0, sticky="we", padx=8, pady=8)
        FlatButton(
            frame, "📁 בחר תיקייה", self._choose_backup, background="#455a64", padx=8, pady=5
        ).pack(side="right", padx=3)
        tk.Label(
            frame, textvariable=self._backup_var, bg=_BG, fg="#555", wraplength=300, justify="right"
        ).pack(side="right", padx=8)

    # -- actions ------------------------------------------------------------
    def _choose_logo(self) -> None:
        path = filedialog.askopenfilename(
            title="בחר קובץ לוגו",
            parent=self,
            filetypes=[("תמונות", "*.png *.jpg *.jpeg *.gif"), ("כל הקבצים", "*.*")],
        )
        if not path:
            return
        data = Path(path).read_bytes()
        if len(data) > _MAX_LOGO_BYTES:
            messagebox.showwarning(
                "לוגו", "הקובץ גדול מדי (מעל 2MB). בחר תמונה קטנה יותר.", parent=self
            )
            return
        mime = _LOGO_MIME_BY_EXT.get(Path(path).suffix.lower().lstrip("."), "image/png")
        self._pending_logo = (base64.b64encode(data).decode(), mime)
        self._logo_state.set("לוגו מותאם אישית (יישמר)")

    def _reset_logo(self) -> None:
        self._pending_logo = ("", "")
        self._logo_state.set("לוגו ברירת מחדל (יישמר)")

    def _choose_backup(self) -> None:
        directory = filedialog.askdirectory(
            title="בחר תיקיית גיבוי (למשל תיקיית Google Drive)", parent=self
        )
        if directory:
            self._backup_var.set(directory)

    def _save(self) -> None:
        start = self._vars["starting_receipt_number"].get().strip()
        if not start.isdigit():
            messagebox.showwarning("שגיאה", "מספר קבלה התחלתי חייב להיות מספר.", parent=self)
            return
        settings = OrganizationSettings(
            org_name=self._vars["org_name"].get().strip(),
            address_line=self._vars["address_line"].get().strip(),
            services_line=self._vars["services_line"].get().strip(),
            starting_receipt_number=int(start),
            backup_dir="" if self._backup_var.get() == "(לא נבחרה)" else self._backup_var.get(),
            custom_logo_base64=self._settings.custom_logo_base64,
            custom_logo_mime=self._settings.custom_logo_mime,
        )
        if self._pending_logo is not None:
            settings.custom_logo_base64, settings.custom_logo_mime = self._pending_logo
        self._db.save_settings(settings)
        self._on_saved()
        messagebox.showinfo("הגדרות", "ההגדרות נשמרו.", parent=self)
        self.destroy()


class DonorHistoryDialog(tk.Toplevel):
    """Show every receipt for one donor, with a yearly-summary generator."""

    def __init__(
        self,
        parent: tk.Misc,
        donor: str,
        receipts: list[Receipt],
        on_generate_summary: Callable[[str, int], None],
    ) -> None:
        super().__init__(parent)
        self.title(f"היסטוריית תורם – {donor}")
        self.geometry("640x460")
        self.configure(bg=_BG)

        tk.Label(self, text=f"תרומות של: {donor}", bg=_BG, font=("Arial", 13, "bold")).pack(pady=8)

        tree = ttk.Treeview(
            self, columns=("no", "date", "product", "value"), show="headings", height=12
        )
        for column, heading, width, anchor in (
            ("no", "מס׳", 60, "center"),
            ("date", "תאריך", 100, "center"),
            ("product", "פרט מוצר", 300, "e"),
            ("value", "שווי ₪", 90, "center"),
        ):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor=anchor)
        tree.pack(fill="both", expand=True, padx=10)
        for receipt in receipts:
            tree.insert(
                "",
                "end",
                values=(receipt.receipt_no, receipt.date, receipt.product, receipt.value_num),
            )

        count, total = summarize(receipts)
        tk.Label(
            self,
            text=f"סה״כ {count} תרומות  |  שווי כולל: {int(round(total)):,} ₪",
            bg="#e8e8e8",
            font=("Arial", 12, "bold"),
            padx=12,
            pady=6,
        ).pack(fill="x", padx=10, pady=6)

        years = sorted(
            {(parse_date(r.date) or date.min).year for r in receipts if parse_date(r.date)},
            reverse=True,
        ) or [date.today().year]
        year_var = tk.StringVar(value=str(years[0]))
        footer = tk.Frame(self, bg=_BG)
        footer.pack(pady=8)
        tk.Label(footer, text="שנה:", bg=_BG, font=("Arial", 11, "bold")).pack(side="right")
        ttk.Combobox(
            footer, textvariable=year_var, width=8, state="readonly", values=[str(y) for y in years]
        ).pack(side="right", padx=6)
        FlatButton(
            footer,
            "📄 הפק אישור תרומה שנתי",
            lambda: on_generate_summary(donor, int(year_var.get())),
            background="#00695c",
            padx=10,
            pady=6,
        ).pack(side="right", padx=8)
