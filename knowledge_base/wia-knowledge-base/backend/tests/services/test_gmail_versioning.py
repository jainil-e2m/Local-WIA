"""Regression: re-fetching an unchanged Gmail message must not create a new version.

Found in the 27 Oct test run: Gmail returns a new attachmentId on every fetch, and label
changes (read/archive) are not content edits.
"""
import base64

from backend.services.intake.adapters.gmail import GmailAdapter
from backend.services.intake.persist import version_key


def _msg(attachment_id: str, labels: list[str]) -> dict:
    body = base64.urlsafe_b64encode(b"Approved, go ahead.").decode().rstrip("=")
    return {"id": "m1", "threadId": "t1", "internalDate": "1790000000000", "labelIds": labels, "payload": {
        "mimeType": "multipart/mixed", "headers": [
            {"name": "From", "value": "Alina <alina@venue.com>"}, {"name": "To", "value": "hello@weddingindustryads.com"},
            {"name": "Subject", "value": "Re: ads"}, {"name": "Date", "value": "Tue, 14 Oct 2026 09:00:00 -0500"}],
        "parts": [{"partId": "0", "mimeType": "text/plain", "body": {"data": body}},
                  {"partId": "1", "mimeType": "image/png", "filename": "a.png",
                   "body": {"size": 10, "attachmentId": attachment_id}}]}}


def test_refetch_with_new_attachment_id_and_labels_is_same_version():
    adapter = GmailAdapter.__new__(GmailAdapter)  # no network/credentials needed for _normalise
    first = adapter._normalise(_msg("ANGj-first", ["INBOX", "UNREAD"]))
    second = adapter._normalise(_msg("ANGj-second", ["IMPORTANT"]))
    assert version_key(first)[0] == version_key(second)[0]
    assert "attachment_id" not in first.attributes["attachments"][0]
