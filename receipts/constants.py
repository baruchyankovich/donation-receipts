"""User-facing default strings and generic organization placeholders.

None of these values reference a specific organization; every field is a
neutral placeholder that each nonprofit overrides from the Settings screen.
"""

from __future__ import annotations

APP_TITLE = "מערכת קבלות תרומות"
RECEIPT_HEADING = "קבלה"
RECEIPT_SUBHEADING = "קבלת מוצרים שווה כסף"
RECEIPT_BANNER = "מפעלי צדקה וחסד"

# Generic placeholders — replaced per-organization via the Settings dialog.
DEFAULT_ORG_NAME = 'שם העמותה (ע"ר ________)'
DEFAULT_ADDRESS_LINE = "כתובת העמותה  |  טלפון: ___-_______"
DEFAULT_SERVICES_LINE = "עמותת צדקה וחסד"
DEFAULT_STARTING_RECEIPT_NUMBER = 1

# A short, neutral acknowledgement printed on every receipt. Editable in code
# by adopters who want their own wording.
DEFAULT_THANK_YOU = (
    "תודה רבה על תרומתכם ועל השותפות בחסד. יהי רצון שתזכו לברכה והצלחה בכל מעשה ידיכם."
)
