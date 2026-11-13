"""BF-2: Gmail is stored as a pointer. No email text reaches the database; it is read from Gmail on demand."""
import base64
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import cast, func, select, String

from backend.db import transaction
from backend.models.db import (
    Business,
    ConnectorAccount,
    Contact,
    ContentUnit,
    RecordAssociation,
    SourceRecord,
    SourceScope,
    SourceVersion,
)
from backend.services.intake import pipeline
from backend.services.intake.adapters.gmail import GmailAdapter
from backend.services.intake.persist import version_key
from backend.services.shared.errors import NotFoundError
from backend.services.shared.http import ProviderClient
from backend.workers import runner

MAILBOX = "hello@agency-example.com"
CLIENT = "alina@venue-example.com"
BODY = "Approved, go ahead with the spring campaign."
QUOTED_HEADER = "On Mon, Oct 13, 2026 at 9:00 AM Hello <hello@agency-example.com> wrote:"
QUOTED = "> Can you review the draft?"


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _message(mid: str, sender: str, body: str = BODY, full: bool = True) -> dict:
    headers = [{"name": "From", "value": f"Someone <{sender}>"}, {"name": "To", "value": MAILBOX},
               {"name": "Subject", "value": "Re: spring campaign"},
               {"name": "Date", "value": "Tue, 14 Oct 2026 09:00:00 -0500"},
               {"name": "Message-ID", "value": f"<{mid}@mail-example.com>"}]
    payload = {"mimeType": "multipart/mixed", "headers": headers}
    if full:
        payload["parts"] = [
            {"partId": "0", "mimeType": "text/plain", "body": {"data": _b64(f"{body}\n\n{QUOTED_HEADER}\n{QUOTED}")}},
            {"partId": "1", "mimeType": "application/pdf", "filename": "brief.pdf",
             "body": {"size": 2048, "attachmentId": "ANGj-x"}}]
    return {"id": mid, "threadId": "t-" + mid, "internalDate": "1792000000000", "historyId": "9",
            "labelIds": ["INBOX"], "payload": payload}


class FakeGmail:
    """Answers the Gmail API calls the reader and fetch_body make."""

    def __init__(self, messages: dict[str, str]):
        self.messages = messages  # message id -> sender
        self.deleted: set[str] = set()
        self.labels: dict[str, list[str]] = {}  # message id -> labels, when not just INBOX
        self.listed: list[dict] = []  # the params of every messages.list call

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/me/", 1)[1]
        if path == "profile":
            return httpx.Response(200, json={"emailAddress": MAILBOX, "historyId": "9"})
        if path == "messages":
            self.listed.append(dict(request.url.params))
            return httpx.Response(200, json={"messages": [{"id": m} for m in self.messages]})
        mid = path.split("/")[1]
        if mid in self.deleted or mid not in self.messages:
            return httpx.Response(404, json={"error": {"code": 404}})
        full = request.url.params.get("format") == "full"
        return httpx.Response(200, json={**_message(mid, self.messages[mid], full=full),
                                         "labelIds": self.labels.get(mid, ["INBOX"])})


def _adapter(fake: FakeGmail) -> GmailAdapter:
    adapter = GmailAdapter.__new__(GmailAdapter)  # no Google credentials needed
    adapter.http = ProviderClient("gmail", "https://gmail.example.test/gmail/v1/users/me/")
    adapter.http._client = httpx.Client(base_url="https://gmail.example.test/gmail/v1/users/me/",
                                        transport=httpx.MockTransport(fake))
    adapter._refresh = lambda: None
    return adapter


def test_normalised_message_keeps_pointer_fields_and_no_text():
    rec = GmailAdapter.__new__(GmailAdapter)._normalise(_message("m1", CLIENT))
    assert rec.units == [] and rec.content_state == "metadata_only"
    a = rec.attributes
    assert a["thread_id"] == "t-m1" and a["rfc_message_id"] == "<m1@mail-example.com>"
    assert a["subject"] == "Re: spring campaign" and a["from"] == CLIENT and a["to"] == [MAILBOX]
    assert a["attachments"] == [{"filename": "brief.pdf", "mime_type": "application/pdf", "size": 2048, "part_id": "1"}]
    assert len(a["body_sha256"]) == 64
    assert rec.source_url.endswith("/m1")
    assert "Approved" not in repr(rec) and "review the draft" not in repr(rec)


def test_a_changed_body_is_a_new_version_without_storing_it():
    adapter = GmailAdapter.__new__(GmailAdapter)
    first = adapter._normalise(_message("m1", CLIENT))
    same = adapter._normalise(_message("m1", CLIENT))
    edited = adapter._normalise(_message("m1", CLIENT, body="Actually, hold the campaign."))
    assert version_key(first) == version_key(same)
    assert version_key(first) != version_key(edited)


def test_fetch_body_reads_the_text_on_demand():
    fake = FakeGmail({"m1": CLIENT})
    body = _adapter(fake).fetch_body("m1")
    assert body["authored"] == BODY and body["quoted"].startswith("On Mon")
    assert body["thread_id"] == "t-m1" and body["body_format"] == "text/plain"
    assert body["body_sha256"] == GmailAdapter.__new__(GmailAdapter)._normalise(_message("m1", CLIENT)).attributes["body_sha256"]
    fake.deleted.add("m1")
    with pytest.raises(NotFoundError):
        _adapter(fake).fetch_body("m1")


@pytest.fixture
def mailbox(monkeypatch):
    fake = FakeGmail({"m-client": CLIENT, "m-other": "news@unrelated-example.com"})
    monkeypatch.setattr(pipeline, "get_adapter", lambda provider: _adapter(fake))
    with transaction() as s:
        b = Business(id=uuid4(), name="Venue", slug="venue")
        a = ConnectorAccount(id=uuid4(), provider="gmail", provider_account_id=MAILBOX, expected_identity=MAILBOX,
                             credential_ref="GOOGLE_REFRESH_TOKEN")
        s.add_all([b, a])
        s.flush()
        s.add(Contact(id=uuid4(), business_id=b.id, email=CLIENT, status="approved"))
        sc = SourceScope(id=uuid4(), connector_account_id=a.id, kind="mailbox", external_id=MAILBOX, name=MAILBOX,
                         state="approved", default_domain="communications", association_mode="per_record")
        s.add(sc)
    return sc.id


def test_backfill_stores_pointers_and_no_email_text(mailbox):
    with transaction() as s:
        pipeline.start_backfill(s, [mailbox], None)
    while runner.run_one(["bulk"]):
        pass
    with transaction() as s:
        records = {r.external_id: r for r in s.execute(select(SourceRecord)).scalars()}
        assert set(records) == {"m-client", "m-other"}
        client = records["m-client"]
        assert client.admitted_at is not None and records["m-other"].admitted_at is None
        assert s.execute(select(RecordAssociation.record_id)).scalars().all() == [client.id]
        pointer = s.get(SourceVersion, client.current_version_id)
        assert pointer.attributes["subject"] == "Re: spring campaign" and pointer.attributes["body_sha256"]
        assert pointer.unit_count == 0 and pointer.content_state == "metadata_only"
        assert s.execute(select(func.count()).select_from(ContentUnit)).scalar_one() == 0
        # No trace of the text anywhere in the stored versions
        hits = s.execute(select(func.count()).select_from(SourceVersion).where(
            cast(SourceVersion.attributes, String).contains("spring campaign."))).scalar_one()
        assert hits == 0


def test_a_windowed_copy_asks_gmail_for_that_window_and_never_for_spam_or_trash(mailbox, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from backend.services.intake import sync
    fake = FakeGmail({"m-client": CLIENT, "m-spam": CLIENT})
    fake.labels["m-spam"] = ["SPAM"]  # what the change feed can report; a listing never returns spam
    monkeypatch.setattr(pipeline, "get_adapter", lambda provider: _adapter(fake))
    with transaction() as s:
        run = sync.request_run(s, mailbox, "backfill", days=365)[0]
        start = run.window_start
    while runner.run_one(["bulk"]):
        pass
    first = fake.listed[0]
    assert "includeSpamTrash" not in first and first["q"] == f"after:{int(start.timestamp())}"
    assert datetime.now(UTC) - timedelta(days=366) < start
    with transaction() as s:
        assert set(s.execute(select(SourceRecord.external_id)).scalars()) == {"m-client"}
