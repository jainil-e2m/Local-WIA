import base64

from backend.models.domain.intake import ApprovedContact, BusinessHint, IntakeContext
from backend.services.intake.normalise.documents import sheet_units
from backend.services.intake.normalise.email import message_text, split_quoted


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def test_reply_header_splits_quoted_history():
    authored, quoted = split_quoted("Approved, go ahead.\n\nOn Tue, Oct 14, 2026 at 9:00 AM Whitney <w@x.com> wrote:\n> Can you review?")
    assert authored == "Approved, go ahead."
    assert quoted.startswith("On Tue")


def test_trailing_angle_quote_block_is_quoted():
    authored, quoted = split_quoted("Thanks!\n> old line\n> older line")
    assert authored == "Thanks!"
    assert "old line" in quoted


def test_html_only_message_is_converted():
    payload = {"mimeType": "multipart/alternative", "parts": [
        {"mimeType": "text/html", "body": {"data": _b64("<p>Hello&nbsp;there</p><style>x{}</style><div>Line 2</div>")}}]}
    authored, quoted, attachments, fmt = message_text(payload)
    assert fmt == "text/html"
    assert "Hello there" in authored and "Line 2" in authored and "x{}" not in authored


def test_sheet_false_stays_a_string_and_rows_keep_locators():
    units, notes = sheet_units("f1", [("October", [["Date", "Member", "Attended?"], ["10/9", "Ann", "FALSE"]])])
    assert units[0].text == "Date: 10/9; Member: Ann; Attended?: FALSE"
    assert units[0].locator == {"kind": "sheet", "file_id": "f1", "tab": "October", "row": 2}
    assert notes == []


def test_contact_matching_by_email_and_domain():
    from datetime import UTC, datetime
    from uuid import uuid4
    a, b = uuid4(), uuid4()
    ctx = IntakeContext(None, datetime.now(UTC), "x", "mailbox",
                        [ApprovedContact(a, "owner@venue.com", None), ApprovedContact(b, None, "other.com")])
    assert ctx.matches(["Owner@Venue.com"]) == {a}
    assert ctx.matches(["someone@other.com", "owner@venue.com"]) == {a, b}
    assert ctx.matches(["owner@gmail.com"]) == set()


def test_alias_matching_ignores_separators():
    from uuid import uuid4
    hint = BusinessHint(uuid4(), "Luxury Travel Boutique", ("Luxury Travel Boutique",))
    assert hint.matches_text("cfpfu_luxurytravelboutique")
    assert not hint.matches_text("luxury hotels")


def test_nul_bytes_from_pdf_text_are_dropped():
    # Regression (27 Oct run): pypdf emitted \x00, which PostgreSQL text/jsonb reject.
    from backend.services.shared.hashing import normalise_text
    assert normalise_text("Dogwood\x00 Reserve\r\nQ1") == "Dogwood Reserve\nQ1"


def test_profile_documents_bypass_the_activity_window():
    from backend.services.intake.adapters.drive import is_profile_document
    assert is_profile_document("Dogwood Reserve | Messaging & Positioning Questionnaire", [])
    assert is_profile_document("LTB Icon Green.png", ["LTB Logo Icon"])
    assert not is_profile_document("8.png", ["Ad creatives"])
