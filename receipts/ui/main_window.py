"""The application's main window."""

from __future__ import annotations

import contextlib
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import backup, constants, documents, excel_export, system
from ..database import Database
from ..filters import Period, filter_receipts, summarize
from ..formatting import parse_date, today_string
from ..hebrew_numbers import amount_in_shekels
from ..models import Receipt
from ..paths import user_data_dir
from .dialogs import DonorHistoryDialog, SettingsDialog
from .widgets import AutocompleteEntry, FlatButton

_BG = "#f4f4f4"
_PAD = 6
_PERIOD_LABELS = {
    "הכל": Period.ALL,
    "החודש": Period.THIS_MONTH,
    "השנה": Period.THIS_YEAR,
    "טווח תאריכים": Period.CUSTOM,
}
_FORM_FIELDS = (
    "receipt_no",
    "date",
    "donor_name",
    "address",
    "phone",
    "email",
    "purpose",
    "product",
    "value_num",
    "value_words",
    "notes",
)


class MainWindow(tk.Tk):
    """Top-level window wiring the form, the list view and all actions."""

    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db
        self._settings = db.load_settings()
        self._all_receipts: list[Receipt] = []
        self._editing = False

        self.title(constants.APP_TITLE)
        self.geometry("900x800")
        self.minsize(820, 720)
        self.configure(bg=_BG)
        with contextlib.suppress(tk.TclError):
            self.option_add("*Font", "Arial 11")

        self._vars = {name: tk.StringVar() for name in _FORM_FIELDS}
        self._search = tk.StringVar()
        self._period = tk.StringVar(value="הכל")
        self._from = tk.StringVar()
        self._to = tk.StringVar()
        self._totals = tk.StringVar()

        self._build_header()
        self._build_form()
        self._build_actions()
        self._build_list()

        for var in (self._search, self._period, self._from, self._to):
            var.trace_add("write", lambda *_: self._refresh_list())

        self.new_receipt()
        self.reload()

    # -- construction -------------------------------------------------------
    def _build_header(self) -> None:
        bar = tk.Frame(self, bg="#111")
        bar.pack(fill="x")
        tk.Label(
            bar, text=constants.APP_TITLE, bg="#111", fg="white", font=("Arial", 16, "bold")
        ).pack(side="right", padx=14, pady=8)
        FlatButton(bar, "⚙ הגדרות", self.open_settings, background="#444444", padx=10, pady=5).pack(
            side="left", padx=12, pady=6
        )

    def _text_row(self, parent: tk.Misc, label: str, key: str, row: int) -> tk.Entry:
        tk.Label(parent, text=label, anchor="e", bg=_BG, font=("Arial", 11, "bold")).grid(
            row=row, column=1, sticky="e", padx=_PAD, pady=4
        )
        entry = tk.Entry(
            parent, textvariable=self._vars[key], width=40, justify="right", font=("Arial", 11)
        )
        entry.grid(row=row, column=0, sticky="we", padx=_PAD, pady=4)
        return entry

    def _build_form(self) -> None:
        frame = tk.LabelFrame(
            self, text=" פרטי הקבלה ", bg=_BG, font=("Arial", 11, "bold"), padx=10, pady=8
        )
        frame.pack(fill="x", padx=12, pady=8)
        frame.columnconfigure(0, weight=1)

        header = tk.Frame(frame, bg=_BG)
        header.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 4))
        tk.Label(header, text="תאריך:", bg=_BG, font=("Arial", 11, "bold")).pack(side="right")
        tk.Entry(header, textvariable=self._vars["date"], width=14, justify="right").pack(
            side="right", padx=(4, 18)
        )
        tk.Label(header, text="מספר קבלה:", bg=_BG, font=("Arial", 11, "bold")).pack(side="right")
        self._number_entry = tk.Entry(
            header,
            textvariable=self._vars["receipt_no"],
            width=10,
            justify="right",
            font=("Arial", 12, "bold"),
        )
        self._number_entry.pack(side="right", padx=4)

        tk.Label(
            frame, text="נתקבל מאת (שם התורם):", anchor="e", bg=_BG, font=("Arial", 11, "bold")
        ).grid(row=1, column=1, sticky="e", padx=_PAD, pady=4)
        self._donor_entry = AutocompleteEntry(
            frame,
            suggestions=self._db.donor_names,
            on_select=self._on_donor_selected,
            textvariable=self._vars["donor_name"],
            width=40,
            justify="right",
            font=("Arial", 11),
        )
        self._donor_entry.grid(row=1, column=0, sticky="we", padx=_PAD, pady=4)

        self._text_row(frame, "כתובת:", "address", 2)
        self._text_row(frame, "טלפון:", "phone", 3)
        self._text_row(frame, "אימייל (לשליחת קבלה):", "email", 4)
        self._text_row(frame, "עבור (מטרה):", "purpose", 5)
        self._text_row(frame, "פרט מוצר:", "product", 6)

        tk.Label(frame, text="סך שווי (₪):", anchor="e", bg=_BG, font=("Arial", 11, "bold")).grid(
            row=7, column=1, sticky="e", padx=_PAD, pady=4
        )
        value_frame = tk.Frame(frame, bg=_BG)
        value_frame.grid(row=7, column=0, sticky="we", padx=_PAD, pady=4)
        tk.Entry(
            value_frame,
            textvariable=self._vars["value_num"],
            width=14,
            justify="right",
            font=("Arial", 11),
        ).pack(side="right")
        tk.Button(value_frame, text="המר למילים ◄", command=self._fill_amount_words).pack(
            side="right", padx=6
        )

        self._text_row(frame, "שווי במילים:", "value_words", 8)
        self._text_row(frame, "הערות:", "notes", 9)

    def _build_actions(self) -> None:
        row1 = tk.Frame(self, bg=_BG)
        row1.pack(fill="x", padx=12, pady=(0, 2))
        row2 = tk.Frame(self, bg=_BG)
        row2.pack(fill="x", padx=12, pady=(0, 6))

        def button(parent: tk.Misc, text: str, command, color: str) -> None:
            FlatButton(parent, text, command, background=color, padx=10, pady=7).pack(
                side="right", padx=3
            )

        button(row1, "💾 שמירה", self.save, "#2e7d32")
        button(row1, "📄 קבלה חדשה", self.new_receipt, "#1565c0")
        button(row1, "🖨️ הדפס / PDF", self.print_receipt, "#6a1b9a")
        button(row1, "🟢 וואטסאפ", self.share_whatsapp, "#25D366")
        button(row1, "📧 מייל", self.share_email, "#1565c0")

        button(row2, "🗑️ מחק קבלה", self.delete_selected, "#c62828")
        button(row2, "👤 היסטוריית תורם", self.show_donor_history, "#00838f")
        button(row2, "📊 ייצוא לאקסל", self.export_excel, "#ef6c00")
        button(row2, "☁ גיבוי", self.backup_data, "#455a64")
        button(row2, "♻ שחזור מגיבוי", self.restore_data, "#5d4037")

    def _build_list(self) -> None:
        wrap = tk.LabelFrame(self, text=" קבלות שמורות ", bg=_BG, font=("Arial", 11, "bold"))
        wrap.pack(fill="both", expand=True, padx=12, pady=(4, 4))

        controls = tk.Frame(wrap, bg=_BG)
        controls.pack(fill="x", padx=6, pady=4)
        tk.Label(controls, text="חיפוש:", bg=_BG, font=("Arial", 11, "bold")).pack(side="right")
        tk.Entry(controls, textvariable=self._search, width=24, justify="right").pack(
            side="right", padx=6
        )
        tk.Label(controls, text="תקופה:", bg=_BG, font=("Arial", 11, "bold")).pack(
            side="right", padx=(12, 2)
        )
        ttk.Combobox(
            controls,
            textvariable=self._period,
            width=12,
            state="readonly",
            values=list(_PERIOD_LABELS),
        ).pack(side="right")
        range_frame = tk.Frame(controls, bg=_BG)
        range_frame.pack(side="right", padx=6)
        tk.Label(range_frame, text="מ-", bg=_BG).pack(side="right")
        tk.Entry(range_frame, textvariable=self._from, width=11, justify="right").pack(
            side="right", padx=2
        )
        tk.Label(range_frame, text="עד", bg=_BG).pack(side="right")
        tk.Entry(range_frame, textvariable=self._to, width=11, justify="right").pack(
            side="right", padx=2
        )
        tk.Label(
            controls, text="(לחיצה כפולה לפתיחת קבלה)", bg=_BG, fg="#666", font=("Arial", 9)
        ).pack(side="left")

        self._tree = ttk.Treeview(
            wrap, columns=("no", "date", "donor", "product", "value"), show="headings", height=11
        )
        for column, heading, width, anchor in (
            ("no", "מס׳", 60, "center"),
            ("date", "תאריך", 100, "center"),
            ("donor", "תורם", 200, "e"),
            ("product", "פרט מוצר", 250, "e"),
            ("value", "שווי ₪", 90, "center"),
        ):
            self._tree.heading(column, text=heading)
            self._tree.column(column, width=width, anchor=anchor)
        self._tree.pack(fill="both", expand=True, side="left", padx=(6, 0), pady=6)
        scrollbar = ttk.Scrollbar(wrap, orient="vertical", command=self._tree.yview)
        scrollbar.pack(side="right", fill="y", pady=6)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.bind("<Double-1>", self._open_selected_receipt)

        tk.Label(
            self,
            textvariable=self._totals,
            bg="#e8e8e8",
            anchor="e",
            font=("Arial", 12, "bold"),
            padx=14,
            pady=6,
        ).pack(fill="x", padx=12, pady=(0, 10))

    # -- form helpers -------------------------------------------------------
    def _collect(self) -> Receipt:
        values = {name: var.get().strip() for name, var in self._vars.items()}
        number = values.pop("receipt_no")
        return Receipt(receipt_no=int(number) if number.isdigit() else 0, **values)

    def _fill_form(self, receipt: Receipt | None) -> None:
        data = receipt.as_dict() if receipt else {}
        for name, var in self._vars.items():
            var.set("" if data.get(name) in (None, 0) else str(data.get(name, "")))

    def _on_donor_selected(self, name: str) -> None:
        address, phone, email = self._db.latest_donor_contact(name)
        if address and not self._vars["address"].get().strip():
            self._vars["address"].set(address)
        if phone and not self._vars["phone"].get().strip():
            self._vars["phone"].set(phone)
        if email and not self._vars["email"].get().strip():
            self._vars["email"].set(email)

    def _fill_amount_words(self) -> None:
        raw = self._vars["value_num"].get().strip()
        if not raw:
            messagebox.showinfo("המרה למילים", 'נא להזין סכום מספרי בשדה "סך שווי".')
            return
        from ..formatting import parse_amount

        self._vars["value_words"].set(amount_in_shekels(parse_amount(raw)))

    # -- actions ------------------------------------------------------------
    def new_receipt(self) -> None:
        self._editing = False
        self._fill_form(None)
        self._vars["receipt_no"].set(str(self._db.next_receipt_number()))
        self._vars["date"].set(today_string())
        self._number_entry.configure(state="normal")
        self._donor_entry.focus_set()

    def save(self) -> None:
        receipt = self._collect()
        if receipt.receipt_no <= 0:
            messagebox.showwarning("שגיאה", "מספר קבלה חייב להיות מספר.")
            return
        if (
            not receipt.donor_name
            and not receipt.product
            and not messagebox.askyesno("שמירה", "שם תורם ופרט מוצר ריקים. לשמור בכל זאת?")
        ):
            return
        if self._editing and self._db.exists(receipt.receipt_no):
            self._db.update(receipt)
            message = "הקבלה עודכנה."
        elif self._db.exists(receipt.receipt_no):
            messagebox.showwarning(
                "שגיאה", f"קבלה מספר {receipt.receipt_no} כבר קיימת.\nלחץ 'קבלה חדשה' למספר חדש."
            )
            return
        else:
            self._db.insert(receipt)
            message = "הקבלה נשמרה."
        self._editing = True
        self.reload()
        if messagebox.askyesno("נשמר", message + "\nלהפיק קבלה להדפסה?"):
            self.print_receipt()

    def print_receipt(self) -> None:
        receipt = self._collect()
        if receipt.receipt_no <= 0:
            messagebox.showwarning("שגיאה", "אין מספר קבלה.")
            return
        html = documents.render_receipt(receipt, self._settings)
        path = user_data_dir() / f"receipt_{receipt.receipt_no}.html"
        path.write_text(html, encoding="utf-8")
        system.open_in_browser(path)

    def share_whatsapp(self) -> None:
        system.open_url(documents.whatsapp_url(self._collect(), self._settings))
        messagebox.showinfo(
            "וואטסאפ",
            'וואטסאפ נפתח עם הודעה מוכנה.\n\nלצירוף הקבלה: "הדפס / PDF", שמור כ-PDF וצרף בשיחה.',
        )

    def share_email(self) -> None:
        system.open_url(documents.mailto_url(self._collect(), self._settings))
        messagebox.showinfo(
            "מייל",
            "תוכנת המייל נפתחה עם הודעה מוכנה.\n\n"
            'לצירוף הקבלה: "הדפס / PDF", שמור כ-PDF וצרף למייל.',
        )

    def delete_selected(self) -> None:
        selection = self._tree.selection()
        if not selection:
            messagebox.showinfo("מחיקה", "בחר קבלה ברשימה למחיקה.")
            return
        values = self._tree.item(selection[0])["values"]
        number = values[0]
        if messagebox.askyesno(
            "מחיקת קבלה", f"למחוק לצמיתות את קבלה מספר {number}\n({values[2]})?\nלא ניתן לשחזר."
        ):
            self._db.delete(int(number))
            self.reload()
            if self._vars["receipt_no"].get() == str(number):
                self.new_receipt()

    def export_excel(self) -> None:
        receipts = self._filtered()
        if len(receipts) != len(self._all_receipts):
            choice = messagebox.askyesnocancel(
                "ייצוא לאקסל",
                f"מוצגות {len(receipts)} קבלות (מסונן) מתוך {len(self._all_receipts)}.\n\n"
                "כן = ייצוא המסונן בלבד\nלא = ייצוא כל הקבלות\nביטול = חזרה",
            )
            if choice is None:
                return
            if not choice:
                receipts = self._all_receipts
        try:
            path = excel_export.export(receipts, user_data_dir() / "receipts.xlsx")
        except Exception as error:  # noqa: BLE001 - surfaced to the user
            messagebox.showerror("שגיאה בייצוא", str(error))
            return
        if messagebox.askyesno("ייצוא הושלם", f"הקובץ נשמר:\n{path}\n\nלפתוח אותו עכשיו?"):
            system.open_path(path)

    def backup_data(self) -> None:
        destination = self._settings.backup_dir
        if not destination or not Path(destination).exists():
            messagebox.showinfo(
                "גיבוי",
                "בחר תיקיית יעד לגיבוי.\n\n"
                'טיפ: בחר את תיקיית "Google Drive" שבמחשב – '
                "כך הגיבוי יסתנכרן אוטומטית לדרייב.",
            )
            destination = filedialog.askdirectory(title="בחר תיקיית גיבוי")
            if not destination:
                return
            self._db.set_setting("backup_dir", destination)
            self._settings = self._db.load_settings()
        try:
            folder = backup.create_backup(self._db, destination)
        except Exception as error:  # noqa: BLE001
            messagebox.showerror("שגיאת גיבוי", f"הגיבוי נכשל:\n{error}")
            return
        messagebox.showinfo(
            "גיבוי הושלם", f"{len(self._all_receipts)} קבלות גובו בהצלחה אל:\n{folder}"
        )

    def restore_data(self) -> None:
        initial = self._settings.backup_dir or str(user_data_dir())
        path = filedialog.askopenfilename(
            title="בחר קובץ גיבוי (receipts.db)",
            initialdir=initial,
            filetypes=[("קובץ גיבוי", "*.db"), ("כל הקבצים", "*.*")],
        )
        if not path:
            return
        receipts = backup.read_receipts(path)
        if receipts is None:
            messagebox.showerror("שחזור", "הקובץ שנבחר אינו גיבוי תקין.")
            return
        mode = messagebox.askyesnocancel(
            "שחזור מגיבוי",
            f"הגיבוי מכיל {len(receipts)} קבלות.\n\n"
            "כן  = מיזוג (הוספת קבלות חסרות בלבד – לא מוחק כלום)\n"
            "לא  = החלפה מלאה (מוחק את כל הנתונים הנוכחיים!)\n"
            "ביטול = יציאה",
        )
        if mode is None:
            return
        if mode:
            added, skipped = backup.merge_missing(self._db, receipts)
            self.reload()
            messagebox.showinfo(
                "שחזור הושלם", f"נוספו {added} קבלות חדשות.\n{skipped} כבר היו קיימות (לא שונו)."
            )
            return
        if not messagebox.askyesno(
            "אזהרה",
            "פעולה זו תמחק את כל הנתונים הנוכחיים ותחליף אותם בגיבוי.\n\n"
            "לפני ההחלפה תישמר גיבוי-בטיחות של המצב הנוכחי. להמשיך?",
        ):
            return
        try:
            backup.snapshot_before_restore(self._db)
            backup.replace_database(self._db, path)
        except Exception as error:  # noqa: BLE001
            messagebox.showerror("שגיאת שחזור", str(error))
            return
        self._settings = self._db.load_settings()
        self.new_receipt()
        self.reload()
        messagebox.showinfo("שחזור הושלם", "כל הנתונים שוחזרו מהגיבוי בהצלחה.")

    def open_settings(self) -> None:
        SettingsDialog(self, self._db, on_saved=self._on_settings_saved)

    def show_donor_history(self) -> None:
        name = self._vars["donor_name"].get().strip()
        selection = self._tree.selection()
        if not name and selection:
            name = self._tree.item(selection[0])["values"][2]
        if not name:
            messagebox.showinfo("היסטוריית תורם", "בחר תורם: הקלד שם בטופס או סמן קבלה ברשימה.")
            return
        receipts = self._db.receipts_for_donor(name)
        if not receipts:
            messagebox.showinfo("היסטוריית תורם", f'לא נמצאו תרומות עבור "{name}".')
            return
        DonorHistoryDialog(self, name, receipts, on_generate_summary=self._generate_summary)

    # -- list / state -------------------------------------------------------
    def reload(self) -> None:
        self._all_receipts = self._db.all_receipts()
        self._refresh_list()

    def _filtered(self) -> list[Receipt]:
        period = _PERIOD_LABELS.get(self._period.get(), Period.ALL)
        return filter_receipts(
            self._all_receipts,
            self._search.get(),
            period,
            parse_date(self._from.get()),
            parse_date(self._to.get()),
        )

    def _refresh_list(self) -> None:
        receipts = self._filtered()
        self._tree.delete(*self._tree.get_children())
        for receipt in receipts:
            self._tree.insert(
                "",
                "end",
                values=(
                    receipt.receipt_no,
                    receipt.date,
                    receipt.donor_name,
                    receipt.product,
                    receipt.value_num,
                ),
            )
        count, total = summarize(receipts)
        self._totals.set(f"סה״כ מוצג:  {count} קבלות   |   שווי כולל:  {int(round(total)):,} ₪")

    def _open_selected_receipt(self, _event: tk.Event) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        number = int(self._tree.item(selection[0])["values"][0])
        receipt = self._db.get(number)
        if receipt:
            self._fill_form(receipt)
            self._editing = True
            self._number_entry.configure(state="normal")

    def _generate_summary(self, donor: str, year: int) -> None:
        receipts = [
            r
            for r in self._db.receipts_for_donor(donor)
            if (parse_date(r.date) or date.min).year == year
        ]
        if not receipts:
            messagebox.showinfo("אישור שנתי", f"אין תרומות מ-{donor} בשנת {year}.")
            return
        html = documents.render_annual_summary(donor, year, receipts, self._settings)
        safe = "".join(ch for ch in donor if ch.isalnum() or ch in " _-").strip() or "donor"
        path = user_data_dir() / f"annual_{safe}_{year}.html"
        path.write_text(html, encoding="utf-8")
        system.open_in_browser(path)

    def _on_settings_saved(self) -> None:
        self._settings = self._db.load_settings()
        if not self._editing:
            self._vars["receipt_no"].set(str(self._db.next_receipt_number()))
