"""Tests for HTML document rendering, including injection safety."""

from receipts import documents
from receipts.models import OrganizationSettings, Receipt


def _receipt(**overrides):
    base = {
        "receipt_no": 1,
        "date": "01/07/2026",
        "donor_name": "דוד",
        "phone": "050-1234567",
        "email": "d@example.com",
        "product": "מזון",
        "value_num": "100",
        "value_words": "מאה שקלים",
    }
    base.update(overrides)
    return Receipt(**base)


def test_receipt_contains_key_content():
    html = documents.render_receipt(_receipt(), OrganizationSettings())
    assert "data:image/png;base64," in html  # default logo embedded
    assert "דוד" in html
    assert "RECEIPT" in html


def test_user_input_is_escaped():
    malicious = '<script>alert("x")</script>'
    html = documents.render_receipt(_receipt(donor_name=malicious), OrganizationSettings())
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_whatsapp_url_uses_international_phone():
    url = documents.whatsapp_url(_receipt(phone="050-1234567"), OrganizationSettings())
    assert url.startswith("https://wa.me/972501234567?text=")


def test_mailto_url_targets_donor_email():
    url = documents.mailto_url(_receipt(email="d@example.com"), OrganizationSettings())
    assert url.startswith("mailto:d%40example.com?")


def test_annual_summary_totals(tmp_path):
    receipts = [_receipt(receipt_no=1, value_num="100"), _receipt(receipt_no=2, value_num="250")]
    html = documents.render_annual_summary("דוד", 2026, receipts, OrganizationSettings())
    assert "350 ₪" in html
    assert "שנת 2026" in html
