"""6 Nov: Calendar and Fathom keep a pointer for every item; P-02 attaches pointers when a contact is approved."""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from backend.db import transaction
from backend.models.db import (Business, ConnectorAccount, RecordAssociation, SourceRecord, SourceScope,
                               SourceVersion, SyncRun, WorkItem)
from backend.models.domain.intake import IntakeContext
from backend.services.clients import mapping
from backend.services.intake.adapters import readers
from backend.services.intake.adapters.calendar import CalendarAdapter
from backend.services.intake.adapters.fathom import FathomAdapter
from backend.workers import runner

CLIENT = "dana@venue-example.com"
OTHER = "someone@unrelated-example.com"


def _ctx(contacts=()):
    return IntakeContext(None, datetime.now(UTC), "hello@agency-example.com", "calendar", list(contacts))


class FakeCalendar(CalendarAdapter):
    def __init__(self, items):
        self.items = items

    def _get(self, path, params=None):
        return {"items": self.items}


def test_calendar_keeps_a_pointer_without_description_for_a_non_client_event():
    ev = {"id": "e1", "status": "confirmed", "summary": "Coffee", "description": "Private notes",
          "start": {"dateTime": "2026-11-10T15:00:00Z"}, "end": {"dateTime": "2026-11-10T16:00:00Z"},
          "attendees": [{"email": OTHER}], "organizer": {"email": "hello@agency-example.com"}}
    batch = readers.read_calendar(FakeCalendar([ev]), _ctx(), {})
    [rec] = batch.records
    assert batch.excluded == 1
    assert rec.admitted is False and rec.units == [] and rec.content_state == "metadata_only"
    assert rec.attributes["attendees"][0]["email"] == OTHER and rec.attributes["summary"] == "Coffee"
    assert "Private notes" not in repr(rec)


class FakeFathomHttp:
    def get_json(self, path, params=None):
        assert path == "meetings", "a pointer must not fetch the transcript or summary"
        return {"items": [{"recording_id": 42, "title": "Internal sync", "url": "https://fathom.example/42",
                           "created_at": "2026-11-05T10:00:00Z", "recording_start_time": "2026-11-05T10:00:00Z",
                           "calendar_invitees": [{"email": OTHER, "name": "Someone"}]}], "next_cursor": None}


def test_fathom_keeps_a_metadata_only_pointer_for_a_non_client_meeting():
    adapter = FathomAdapter.__new__(FathomAdapter)
    adapter.http = FakeFathomHttp()
    batch = readers.read_fathom(adapter, _ctx(), {})
    [rec] = batch.records
    assert batch.excluded == 1
    assert rec.admitted is False and rec.units == [] and rec.content_state == "metadata_only"
    assert rec.attributes["invitees"] == [{"email": OTHER, "name": "Someone"}] and rec.participants[0].email == OTHER


def _pointer(s, account, scope, kind, external_id, attributes):
    r = SourceRecord(id=uuid4(), connector_account_id=account.id, scope_id=scope.id, record_kind=kind,
                     external_id=external_id, qualification="metadata_only", occurred_at=datetime.now(UTC))
    s.add(r)
    s.flush()
    v = SourceVersion(id=uuid4(), record_id=r.id, version_key="v1", content_sha256="0" * 64, parser_version="t",
                      content_state="metadata_only", attributes=attributes)
    s.add(v)
    s.flush()
    r.current_version_id = v.id
    return r.id


def test_approving_a_contact_attaches_mail_and_refreshes_calendar_items():
    with transaction() as s:
        b = Business(id=uuid4(), name="Venue", slug="venue")
        gmail = ConnectorAccount(id=uuid4(), provider="gmail", provider_account_id="hello@agency-example.com",
                                 expected_identity="hello@agency-example.com", credential_ref="GOOGLE_REFRESH_TOKEN")
        cal = ConnectorAccount(id=uuid4(), provider="calendar", provider_account_id="hello@agency-example.com",
                               expected_identity="hello@agency-example.com", credential_ref="GOOGLE_REFRESH_TOKEN")
        s.add_all([b, gmail, cal])
        s.flush()
        mailbox = SourceScope(id=uuid4(), connector_account_id=gmail.id, kind="mailbox", external_id="hello@agency-example.com",
                              name="hello@", state="approved", default_domain="communications", association_mode="per_record")
        calendar = SourceScope(id=uuid4(), connector_account_id=cal.id, kind="calendar", external_id="primary",
                               name="primary", state="approved", default_domain="meetings", association_mode="per_record")
        s.add_all([mailbox, calendar])
        s.flush()
        mail = _pointer(s, gmail, mailbox, "gmail_message", "m1", {"from": CLIENT, "to": ["hello@agency-example.com"]})
        other = _pointer(s, gmail, mailbox, "gmail_message", "m2", {"from": OTHER, "to": ["hello@agency-example.com"]})
        _pointer(s, cal, calendar, "calendar_event", "primary:e1", {"attendees": [{"email": CLIENT}]})
        business_id = b.id
    with transaction() as s:
        mapping.add_contact(s, business_id, actor="test", email=CLIENT)
    while runner.run_one(["maintenance"]):
        pass
    with transaction() as s:
        assert s.get(SourceRecord, mail).admitted_at is not None
        assert s.get(SourceRecord, other).admitted_at is None
        assert s.execute(select(RecordAssociation.record_id, RecordAssociation.business_id,
                                RecordAssociation.basis)).all() == [(mail, business_id, "verified_contact")]
        [run] = s.execute(select(SyncRun)).scalars().all()
        assert run.mode == "refresh" and run.target_external_id == "primary:e1"
        assert s.execute(select(WorkItem.state).where(WorkItem.kind == "qualify.recheck")).scalars().all() == ["succeeded"]
