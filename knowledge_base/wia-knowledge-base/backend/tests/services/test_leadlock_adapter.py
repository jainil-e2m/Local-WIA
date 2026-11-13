"""LeadLock adapter: phases, pagination, privacy rules, gaps, discovery and an end-to-end backfill."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from backend.db import transaction
from backend.models.db import (ConnectorAccount, ContentUnit, LeadLockLocation, RecordAssociation, SourceRecord,
                               SourceScope, SourceVersion, WorkItem)
from backend.models.domain.intake import BusinessHint, IntakeContext
from backend.services.clients import mapping
from backend.services.intake import leadlock_app, pipeline
from backend.services.intake.adapters import leadlock as ll
from backend.services.shared.errors import NotFoundError, ScopeDeniedError

LOC = "loc-venue"
PII = ("Jane", "Doe", "jane@couple.example", "+15550100", "1 Main St", "Our dream wedding")
_NOW_MS = int(datetime.now(UTC).timestamp() * 1000)
EVENTS = [{"id": f"e{n}", "title": "Tour with Jane Doe", "contactId": "c0", "calendarId": "cal1",
           "appointmentStatus": status, "startTime": _NOW_MS + days * 86_400_000, "endTime": _NOW_MS + days * 86_400_000 + 3_600_000}
          for n, (days, status) in enumerate([(-10, "showed"), (20, "confirmed")])]


class FakeAPI:
    """Stands in for ProviderClient: answers by path; a handler is a dict, a function of params, or an error."""

    def __init__(self, routes):
        self.routes, self.calls, self.headers = routes, [], {}

    def set_header(self, name, value):
        self.headers[name] = value

    def get_json(self, path, params=None, auth_retry=None):
        self.calls.append((path, dict(params or {})))
        handler = self.routes[path]
        if isinstance(handler, Exception):
            raise handler
        return handler(params or {}) if callable(handler) else handler


def contact(i, **kw):
    return {"id": f"c{i}", "firstName": "Jane", "lastName": "Doe", "contactName": "Jane Doe", "email": "jane@couple.example",
            "phone": "+15550100", "address1": "1 Main St", "type": "lead", "source": "Website form",
            "tags": ["tour-booked", "fall"], "dateAdded": "2026-10-01T12:00:00.000Z", "dateUpdated": "2026-10-02T12:00:00.000Z",
            "attributions": [{"medium": "facebook", "utmCampaign": "fall-promo", "isFirst": True}],
            "customFields": [{"id": "f-date", "value": int(datetime(2027, 6, 12, tzinfo=UTC).timestamp() * 1000)},
                             {"id": "f-guests", "value": 120},
                             {"id": "f-notes", "value": "Our dream wedding"}, {"id": "f-partner", "value": "Doe"}], **kw}


def routes(contacts=2, page=ll.PAGE):
    def contacts_page(p):
        start = 0 if "startAfterId" not in p else page
        rows = [contact(i) for i in range(start, min(contacts, start + page))]
        return {"contacts": rows, "meta": {"startAfterId": rows[-1]["id"] if rows else None, "startAfter": 1}}
    return {
        "contacts/": contacts_page,
        f"locations/{LOC}/customFields": {"customFields": [
            {"id": "f-date", "name": "Wedding date", "dataType": "DATE"},
            {"id": "f-guests", "name": "Guest count", "dataType": "NUMERICAL"},
            {"id": "f-notes", "name": "Tell us about your day", "dataType": "LARGE_TEXT"},
            {"id": "f-partner", "name": "Partner name", "dataType": "TEXT"}]},
        "opportunities/search": {"opportunities": [{"id": "o1", "name": "Jane & John Doe", "contactId": "c0",
                                                    "pipelineId": "p1", "pipelineStageId": "s2", "status": "open",
                                                    "monetaryValue": 12000, "source": "Website form",
                                                    "createdAt": "2026-10-01T12:00:00Z", "updatedAt": "2026-10-03T12:00:00Z",
                                                    "contact": {"name": "Jane Doe", "email": "jane@couple.example"}}],
                                 "meta": {}},
        "opportunities/pipelines": {"pipelines": [{"id": "p1", "name": "Venue sales",
                                                   "stages": [{"id": "s1", "name": "New inquiry"}, {"id": "s2", "name": "Tour booked"}]}]},
        "conversations/search": {"conversations": [{"id": "v1", "contactId": "c0", "type": "TYPE_SMS",
                                                    "lastMessageBody": "Our dream wedding", "fullName": "Jane Doe",
                                                    "lastMessageDirection": "inbound", "lastMessageDate": 1793000000000,
                                                    "unreadCount": 1, "dateAdded": 1792000000000}], "total": 1},
        "forms/submissions": {"submissions": [{"id": "fs1", "contactId": "c0", "formId": "form1", "name": "Jane Doe",
                                               "email": "jane@couple.example", "others": {"notes": "Our dream wedding"},
                                               "createdAt": "2026-10-01T12:00:00Z"}], "meta": {"nextPage": None}},
        "forms/": {"forms": [{"id": "form1", "name": "Venue inquiry"}]},
        "calendars/": {"calendars": [{"id": "cal1", "name": "Tours"}, {"id": "cal2", "name": "Calls"}]},
        f"locations/{LOC}": {"location": {"id": LOC, "dateAdded": "2026-08-01T00:00:00.000Z"}},
        "calendars/events": lambda p: {"events": [e for e in EVENTS if p["startTime"] <= e["startTime"] < p["endTime"]]},
        "invoices/": {"invoices": [{"_id": "inv1", "invoiceNumber": "1001", "title": "Wedding package", "status": "paid",
                                    "total": 5000, "amountPaid": 5000, "amountDue": 0, "currency": "USD",
                                    "contactDetails": {"id": "c0", "name": "Jane Doe", "email": "jane@couple.example"}}]},
        "payments/transactions": {"data": [{"_id": "t1", "amount": 5000, "currency": "USD", "status": "succeeded",
                                            "entityType": "invoice", "entityId": "inv1", "contactId": "c0",
                                            "contactName": "Jane Doe"}]},
    }


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setattr(leadlock_app, "location_token", lambda location_id, http=None: "loc-token")
    monkeypatch.setattr(leadlock_app, "mint_location_token", lambda location_id, http=None: "loc-token-2")
    a = ll.LeadLockAdapter()
    a.http = FakeAPI(routes())
    return a


def ctx(days=30):
    end = datetime.now(UTC)
    return IntakeContext(window_start=end - timedelta(days=days), window_end=end, scope_external_id=LOC,
                         scope_kind="location", contacts=[])


def read_all(adapter, context):
    records, gaps, state, pages = [], [], {}, 0
    while True:
        batch = adapter.read_page(context, state)
        records += batch.records
        gaps += batch.gaps
        pages += 1
        assert all(k in ("phase", "cursor") for k in batch.checkpoint)  # checkpoints never hold data
        if batch.terminal:
            return records, gaps, pages
        state = batch.checkpoint


def test_reads_every_phase_once_and_ends_terminal(adapter):
    records, gaps, _ = read_all(adapter, ctx())
    kinds = {r.record_kind for r in records}
    assert kinds == {"leadlock_pipeline", "leadlock_contact", "leadlock_opportunity", "leadlock_conversation",
                     "leadlock_form_submission", "leadlock_appointment", "leadlock_invoice", "leadlock_transaction"}
    pipeline = next(r for r in records if r.record_kind == "leadlock_pipeline")
    assert [s["name"] for s in pipeline.attributes["stages"]] == ["New inquiry", "Tour booked"]
    assert not gaps and adapter.http.headers["Authorization"] == "Bearer loc-token"
    assert all(r.content_state == "metadata_only" and not r.units for r in records)  # nothing goes to AI extraction
    assert {r.record_kind for r in records if r.domain == "finance"} == {"leadlock_invoice", "leadlock_transaction"}


def test_no_couple_personal_data_is_kept(adapter):
    records, _, _ = read_all(adapter, ctx())
    for r in records:
        blob = repr(r.attributes)
        for value in PII:
            assert value not in blob, (r.record_kind, value)


def test_contacts_keep_structured_fields_and_attribution(adapter):
    records, _, _ = read_all(adapter, ctx())
    c = next(r for r in records if r.record_kind == "leadlock_contact")
    assert c.attributes["custom_fields"] == {"Wedding date": "2027-06-12", "Guest count": 120}
    assert c.attributes["attributions"] == [{"medium": "facebook", "utmCampaign": "fall-promo", "isFirst": True}]
    assert c.attributes["source"] == "Website form" and c.attributes["tags"] == ["fall", "tour-booked"]


def test_opportunities_carry_pipeline_and_stage_names(adapter):
    records, _, _ = read_all(adapter, ctx())
    o = next(r for r in records if r.record_kind == "leadlock_opportunity")
    assert (o.attributes["pipeline"], o.attributes["stage"], o.attributes["status"]) == ("Venue sales", "Tour booked", "open")
    assert o.attributes["monetary_value"] == 12000 and o.attributes["contact_id"] == "c0"


def test_contacts_page_through_with_the_providers_cursor(adapter):
    adapter.http = FakeAPI(routes(contacts=150))
    records, _, _ = read_all(adapter, ctx())
    assert sum(r.record_kind == "leadlock_contact" for r in records) == 150
    contact_calls = [p for path, p in adapter.http.calls if path == "contacts/"]
    assert len(contact_calls) == 2 and contact_calls[1]["startAfterId"] == "c99"


def test_a_refused_feature_is_a_gap_for_that_phase_only(adapter):
    r = routes()
    r["forms/submissions"] = ScopeDeniedError("leadlock: HTTP 403")
    adapter.http = FakeAPI(r)
    records, gaps, _ = read_all(adapter, ctx())
    assert [g.external_id for g in gaps] == [f"{LOC}:form_submissions"]
    assert "leadlock_appointment" in {x.record_kind for x in records}  # later phases still ran


def test_a_paused_sub_account_is_scope_denied_not_a_blocked_connector(monkeypatch):
    def refused(location_id, http=None):
        raise leadlock_app.LeadLockAppError("Location is not active")
    monkeypatch.setattr(leadlock_app, "location_token", refused)
    monkeypatch.setattr(leadlock_app, "mint_location_token", refused)
    with pytest.raises(ScopeDeniedError):
        ll.LeadLockAdapter().read_page(ctx(), {})


def test_appointments_cover_the_window_to_a_year_ahead_in_90_day_steps(adapter):
    read_all(adapter, ctx(days=30))
    windows = [p for path, p in adapter.http.calls if path == "calendars/events"]
    first, last = windows[0], windows[-1]
    assert first["startTime"] <= int((datetime.now(UTC) - timedelta(days=29)).timestamp() * 1000)
    assert last["endTime"] >= int((datetime.now(UTC) + ll.APPOINTMENT_HORIZON).timestamp() * 1000)
    assert all(w["endTime"] - w["startTime"] == int(ll.APPOINTMENT_CHUNK.total_seconds() * 1000) for w in windows)
    assert {w["calendarId"] for w in windows} == {"cal1", "cal2"}
    assert sum(w["calendarId"] == "cal2" and w["startTime"] == first["startTime"] for w in windows) == 1  # each calendar restarts


def test_full_history_appointments_start_when_the_sub_account_was_created(adapter):
    read_all(adapter, ctx(days=3650))  # a window far older than the sub-account
    first = next(p for path, p in adapter.http.calls if path == "calendars/events")
    assert first["startTime"] == int(datetime(2026, 8, 1, tzinfo=UTC).timestamp() * 1000)


def test_discovery_lists_installed_sub_accounts_and_suggests_matching_clients():
    business = uuid4()
    with transaction() as s:
        s.add_all([LeadLockLocation(location_id="loc-1", name="Venue One Weddings", state="active", scopes=[]),
                   LeadLockLocation(location_id="loc-2", name="Unrelated Co", state="failed", scopes=[],
                                    last_error="Location is not active"),
                   LeadLockLocation(location_id="loc-3", name="Gone Venue", state="uninstalled", scopes=[])])
    result = ll.LeadLockAdapter().discover([BusinessHint(business, "Venue One", ("Venue One",))], None, datetime.now(UTC))
    by_id = {c.external_id: c for c in result.scopes}
    assert set(by_id) == {"loc-1", "loc-2"}
    assert by_id["loc-1"].suggested_business_id == business and by_id["loc-1"].association_mode == "dedicated"
    assert by_id["loc-2"].suggested_business_id is None and "Location is not active" in by_id["loc-2"].reason
    with pytest.raises(NotFoundError):
        ll.LeadLockAdapter().describe_scope("location", "loc-3")


def test_backfill_stores_associated_metadata_and_a_rerun_changes_nothing(adapter, monkeypatch):
    with transaction() as s:
        venue = mapping.create_client(s, name="Venue One", slug="venue-one", aliases=["V1"], actor="t").id
        account = ConnectorAccount(id=uuid4(), provider="leadlock", provider_account_id="company-example",
                                   expected_identity="company-example", credential_ref="leadlock_installations")
        s.add(account)
        s.flush()
        scope = SourceScope(id=uuid4(), connector_account_id=account.id, kind="location", external_id=LOC, name="Venue One",
                            state="approved", default_domain="leads", association_mode="dedicated", business_id=venue)
        s.add(scope)
        s.flush()
        scope_id = scope.id
        s.query(WorkItem).delete()  # client creation queued discovery; only the backfill should run here
    monkeypatch.setattr(pipeline, "get_adapter", lambda provider: adapter)
    from backend.workers import runner

    def run_once():
        with transaction() as s:
            pipeline.start_backfill(s, [scope_id], days=30)
        while runner.run_one(["bulk"]):
            pass

    run_once()
    with transaction() as s:
        records = s.execute(select(SourceRecord)).scalars().all()
        assert {r.record_kind for r in records} >= {"leadlock_contact", "leadlock_opportunity", "leadlock_invoice"}
        assert all(r.qualification == "metadata_only" for r in records)
        assert s.scalar(select(func.count()).select_from(ContentUnit)) == 0
        linked = s.execute(select(RecordAssociation.business_id).distinct()).scalars().all()
        assert linked == [venue]
        assert s.scalar(select(func.count()).select_from(WorkItem).where(WorkItem.kind == "record.extract")) == 0
        versions = s.scalar(select(func.count()).select_from(SourceVersion))
    run_once()
    with transaction() as s:
        assert s.scalar(select(func.count()).select_from(SourceVersion)) == versions  # idempotent re-run


def test_form_submissions_ask_for_the_whole_window_not_highlevels_30_day_default(adapter):
    read_all(adapter, ctx(days=3650))
    call = next(p for path, p in adapter.http.calls if path == "forms/submissions")
    assert call["startAt"] == "2020-01-01"  # the history floor, since the window starts before it
    assert call["endAt"] == (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
