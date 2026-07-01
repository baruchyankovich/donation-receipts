"""Render printable HTML documents (receipt and annual donation summary).

Every value that originates from user input is passed through
:func:`~receipts.formatting.escape_html`, and every URL parameter through
:func:`urllib.parse.quote`, so the generated documents are injection-safe.
"""

from __future__ import annotations

import urllib.parse
from datetime import date

from . import constants
from .formatting import escape_html, normalize_phone_e164_il
from .hebrew_numbers import amount_in_shekels
from .models import OrganizationSettings, Receipt

_COMMON_CSS = """
  @page { size: A5 portrait; margin: 8mm; }
  * { box-sizing: border-box; }
  body { font-family: "Arial Hebrew","Arial","Segoe UI",sans-serif; margin:0;
         background:#f0f0f0; color:#000; direction:rtl; }
  .sheet { width:148mm; min-height:200mm; margin:8px auto; background:#fff; padding:6mm 7mm; }
  .topbar { display:flex; align-items:center; justify-content:space-between; }
  .topbar .banner { background:#000; color:#fff; font-weight:bold; font-size:20px;
                    padding:6px 16px; letter-spacing:1px; flex:1; text-align:center; margin-left:10px; }
  .topbar img { height:64px; }
  .orgline { text-align:center; font-weight:bold; font-size:12px; margin:4px 0 2px; }
  .footer { margin-top:10px; }
  .footer .banner { background:#000; color:#fff; text-align:center; font-weight:bold;
                    font-size:12.5px; padding:6px 8px; }
  .footer .addr { text-align:center; font-size:12px; margin-top:4px; font-weight:bold; }
  .toolbar { text-align:center; margin:10px; }
  .toolbar button, .toolbar a { font-size:15px; padding:8px 20px; cursor:pointer;
        text-decoration:none; border:1px solid #999; border-radius:6px;
        background:#f7f7f7; color:#000; display:inline-block; margin:2px; }
  .toolbar a.wa { background:#25D366; color:#fff; border-color:#1da851; }
  .toolbar a.mail { background:#1565c0; color:#fff; border-color:#104a91; }
  .toolbar .hint { display:block; font-size:11px; color:#666; margin-top:6px; }
  @media print { body { background:#fff; } .toolbar { display:none; }
                 .sheet { margin:0; width:auto; } }
"""


def share_message(receipt: Receipt, settings: OrganizationSettings) -> str:
    """Build a plain-text acknowledgement suitable for WhatsApp or email."""
    org = settings.org_name.split("(")[0].strip()
    lines = [f"קבלה מס' {receipt.receipt_no} – {org}"]
    if receipt.donor_name:
        lines.append(f"נתקבל מאת: {receipt.donor_name}")
    if receipt.product:
        lines.append(f"פרט מוצר: {receipt.product}")
    if receipt.value_num:
        lines.append(f"שווי התרומה: {receipt.value_num} ₪")
    if receipt.date:
        lines.append(f"תאריך: {receipt.date}")
    lines.append("תודה רבה על תרומתכם! 🙏")
    return "\n".join(lines)


def whatsapp_url(receipt: Receipt, settings: OrganizationSettings) -> str:
    phone = normalize_phone_e164_il(receipt.phone)
    base = f"https://wa.me/{phone}" if phone else "https://wa.me/"
    return f"{base}?text=" + urllib.parse.quote(share_message(receipt, settings))


def mailto_url(receipt: Receipt, settings: OrganizationSettings) -> str:
    subject = urllib.parse.quote(f"קבלה מס' {receipt.receipt_no}")
    to = urllib.parse.quote(receipt.email or "")
    body = urllib.parse.quote(share_message(receipt, settings))
    return f"mailto:{to}?subject={subject}&body={body}"


def _field(
    label_he: str, value: str = "", label_en: str = "&nbsp;", *, value_html: str | None = None
) -> str:
    """Render one labelled receipt field.

    ``value`` is HTML-escaped; pass ``value_html`` only for trusted markup
    that has already been escaped/composed by the caller.
    """
    inner = value_html if value_html is not None else escape_html(value)
    return (
        f'<div class="field"><span class="he">{label_he}</span>'
        f'<span class="val">{inner}</span>'
        f'<span class="en">{label_en}</span></div>'
    )


def render_receipt(receipt: Receipt, settings: OrganizationSettings) -> str:
    """Return the full HTML for a single printable/shareable receipt."""
    value_line = escape_html(receipt.value_num) + (" ₪" if receipt.value_num else "")
    amount_display = f"{value_line} &nbsp;&nbsp; {escape_html(receipt.value_words)}"
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<title>קבלה {escape_html(receipt.receipt_no)}</title>
<style>{_COMMON_CSS}
  .frame {{ border:3px double #000; border-radius:14px; padding:14px 18px; margin-top:8px; position:relative; }}
  .source {{ position:absolute; top:8px; left:16px; font-size:12px; }}
  .titlerow {{ text-align:center; }}
  .titlerow .t1 {{ font-size:26px; font-weight:bold; }}
  .titlerow .t1 .en {{ font-size:16px; letter-spacing:1px; margin:0 10px; }}
  .titlerow .t2 {{ font-size:20px; font-weight:bold; margin-top:2px; }}
  .fields {{ margin-top:14px; }}
  .field {{ display:flex; align-items:flex-end; gap:8px; margin:10px 2px; }}
  .field .he {{ font-weight:bold; font-size:15px; white-space:nowrap; }}
  .field .val {{ flex:1; border-bottom:1px solid #000; min-height:20px; padding:0 8px 2px; font-size:15px; }}
  .field .en {{ font-size:11px; color:#222; white-space:nowrap; min-width:74px; text-align:left; }}
  .thanks {{ text-align:center; font-size:13px; line-height:1.7; margin-top:14px; }}
  .sign {{ display:flex; justify-content:space-between; margin-top:22px; font-size:14px; }}
  .sign .slot {{ display:flex; align-items:flex-end; gap:6px; }}
  .sign .line {{ border-bottom:1px solid #000; min-width:120px; display:inline-block; min-height:18px; }}
</style></head><body>
  <div class="toolbar">
    <button onclick="window.print()">🖨️ הדפס / שמור כ-PDF</button>
    <a class="wa" href="{whatsapp_url(receipt, settings)}" target="_blank" rel="noopener">🟢 שלח בוואטסאפ</a>
    <a class="mail" href="{mailto_url(receipt, settings)}">📧 שלח במייל</a>
    <span class="hint">לצירוף הקבלה: שמרו כ-PDF (כפתור ההדפסה) וצרפו בוואטסאפ/מייל</span>
  </div>
  <div class="sheet">
    <div class="topbar"><div class="banner">{constants.RECEIPT_BANNER}</div>
      <img src="{settings.logo_data_uri()}" alt="logo"></div>
    <div class="orgline">{escape_html(settings.org_name)}</div>
    <div class="frame">
      <div class="source">מקור</div>
      <div class="titlerow">
        <div class="t1">{constants.RECEIPT_HEADING} <span class="en">RECEIPT</span> {escape_html(receipt.receipt_no)}</div>
        <div class="t2">{constants.RECEIPT_SUBHEADING}</div>
      </div>
      <div class="fields">
        {_field("נתקבל מאת", receipt.donor_name, "Received from")}
        {_field("כתובת", receipt.address, "Address")}
        {_field("עבור", receipt.purpose, "for")}
        {_field("סך שווי תרומה", label_en="The sum of", value_html=amount_display)}
        {_field("פרט מוצר", receipt.product)}
      </div>
      <div class="thanks">{escape_html(constants.DEFAULT_THANK_YOU)}</div>
      <div class="sign">
        <div class="slot"><span class="he">תאריך</span><span class="line">{escape_html(receipt.date)}</span></div>
        <div class="slot"><span class="he">חתימה</span><span class="line">&nbsp;</span></div>
      </div>
    </div>
    <div class="footer"><div class="banner">{escape_html(settings.services_line)}</div>
      <div class="addr">{escape_html(settings.address_line)}</div></div>
  </div>
</body></html>"""


def render_annual_summary(
    donor: str, year: int, receipts: list[Receipt], settings: OrganizationSettings
) -> str:
    """Return HTML summarizing one donor's donations across a calendar year."""
    from .formatting import parse_date  # local import avoids a cycle at top level

    ordered = sorted(receipts, key=lambda r: parse_date(r.date) or date.min)
    total = sum(r.amount for r in ordered)
    body_rows = "".join(
        f"<tr><td>{escape_html(r.receipt_no)}</td><td>{escape_html(r.date)}</td>"
        f"<td>{escape_html(r.product)}</td>"
        f"<td class='num'>{escape_html(r.value_num)} ₪</td></tr>"
        for r in ordered
    )
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<title>ריכוז תרומות {year} - {escape_html(donor)}</title>
<style>{_COMMON_CSS}
  .frame {{ border:3px double #000; border-radius:14px; padding:16px 18px; margin-top:8px; }}
  h1 {{ text-align:center; font-size:22px; margin:6px 0; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:13px; }}
  th, td {{ border:1px solid #000; padding:5px 8px; text-align:right; }}
  th {{ background:#000; color:#fff; }}
  td.num, th.num {{ text-align:center; white-space:nowrap; }}
  tfoot td {{ font-weight:bold; font-size:14px; }}
  .words {{ margin-top:8px; font-size:13px; font-weight:bold; }}
  .sign {{ display:flex; justify-content:space-between; margin-top:26px; font-size:14px; }}
  .sign .line {{ border-bottom:1px solid #000; min-width:140px; display:inline-block; }}
</style></head><body>
  <div class="toolbar"><button onclick="window.print()">🖨️ הדפס / שמור כ-PDF</button></div>
  <div class="sheet">
    <div class="topbar"><div class="banner">{constants.RECEIPT_BANNER}</div>
      <img src="{settings.logo_data_uri()}" alt="logo"></div>
    <div class="orgline">{escape_html(settings.org_name)}</div>
    <div class="frame">
      <h1>ריכוז תרומות שנתי – שנת {year}</h1>
      <div><b>לכבוד:</b> {escape_html(donor)}</div>
      <table>
        <thead><tr><th>מס׳ קבלה</th><th>תאריך</th><th>פרט מוצר</th><th class="num">שווי</th></tr></thead>
        <tbody>{body_rows}</tbody>
        <tfoot><tr><td colspan="3">סה״כ ({len(ordered)} תרומות)</td>
          <td class="num">{int(round(total)):,} ₪</td></tr></tfoot>
      </table>
      <div class="words">סה״כ במילים: {escape_html(amount_in_shekels(total))}</div>
      <div class="sign"><div>תאריך __________</div>
        <div><span>חתימה וחותמת</span> <span class="line">&nbsp;</span></div></div>
    </div>
    <div class="footer"><div class="banner">{escape_html(settings.services_line)}</div>
      <div class="addr">{escape_html(settings.address_line)}</div></div>
  </div>
</body></html>"""
