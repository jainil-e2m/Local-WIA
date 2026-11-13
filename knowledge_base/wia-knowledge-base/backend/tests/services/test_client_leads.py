"""Leads read model and endpoint: period counts, the won-tracking rule, funnel order, local-only access."""
from collections import namedtuple
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import (ConnectorAccount, RecordAssociation, SourceRecord, SourceScope, SourceVersion, SyncRun)
from backend.services.clients import mapping
from backend.services.read_models import leads

NOW = datetime(2026, 11, 4, 12, tzinfo=UTC)


def ago(days):
    return NOW - timedelta(days=days)


@pytest.fixture
def venue():
    with transaction() as s:
        business = mapping.create_client(s, name="Venue One", slug="venue-one", aliases=["V1"], actor="t")
        account = ConnectorAccount(id=uuid4(), provider="leadlock", provider_account_id="co", expected_identity="co",
                                   credential_ref="leadlock_installations")
        s.add(account)
        s.flush()
        scope = SourceScope(id=uuid4(), connector_account_id=account.id, kind="location", external_id="loc-1",
                            name="Venue One", state="approved", default_domain="leads", association_mode="dedicated",
                            business_id=business.id)
        s.add(scope)
        s.flush()
        s.add(SyncRun(id=uuid4(), connector_account_id=account.id, scope_id=scope.id, mode="backfill",
                      state="succeeded", window_end=ago(0.1), finished_at=ago(0.1), checkpoint={}))
        return Ids(business.id, account.id, scope.id)


Ids = namedtuple("Ids", "business_id account_id scope_id")


def add(ids, kind, occurred, **attributes):
    with transaction() as s:
        record = SourceRecord(id=uuid4(), connector_account_id=ids.account_id, scope_id=ids.scope_id,
                              record_kind=f"leadlock_{kind}", external_id=str(uuid4()), occurred_at=occurred,
                              admitted_at=NOW, qualification="metadata_only", provider_state={})
        s.add(record)
        s.flush()
        version = SourceVersion(id=uuid4(), record_id=record.id, version_key=str(uuid4()), content_sha256="0" * 64,
                                parser_version="leadlock-v2", content_state="metadata_only", attributes=attributes)
        s.add(version)
        s.flush()
        record.current_version_id = version.id
        s.add(RecordAssociation(id=uuid4(), record_id=record.id, business_id=ids.business_id, basis="scope_mapping"))


def leads_for(period="90d"):
    with transaction() as s:
        return leads.client_leads(s, "venue-one", period, now=NOW)


def test_inquiries_and_tours_count_in_the_period_and_compare_with_the_one_before(venue):
    for days in (5, 40, 100, 150):
        add(venue, "opportunity", ago(days), status="open", pipeline="Sales", stage="New")
    add(venue, "appointment", ago(10), status="confirmed", start_at=ago(5).isoformat())
    add(venue, "appointment", ago(12), status="cancelled", start_at=ago(2).isoformat())
    add(venue, "appointment", ago(1), status="confirmed", start_at=(NOW + timedelta(days=7)).isoformat())
    out = leads_for("90d")
    assert out["kpis"]["inquiries"] == {"value": 2, "previous": 2}
    assert out["kpis"]["tours_booked"]["value"] == 2  # the cancelled one doesn't count
    assert out["kpis"]["upcoming_tours"]["value"] == 1
    assert leads_for("all")["kpis"]["inquiries"] == {"value": 4, "previous": None}


def test_won_is_hidden_when_the_venue_leaves_everything_open(venue):
    for days in range(20):
        add(venue, "opportunity", ago(days), status="open", pipeline="Sales", stage="New")
    add(venue, "opportunity", ago(3), status="won", last_status_change_at=ago(1).isoformat(), pipeline="Sales", stage="Won")
    won = leads_for()["kpis"]["won"]
    assert won == {"tracked": False, "value": None, "previous": None}  # 1 of 21 closed: under 10%


def test_won_counts_by_status_change_when_the_venue_closes_opportunities(venue):
    for days, status in ((3, "won"), (4, "lost"), (5, "open"), (6, "open")):
        add(venue, "opportunity", ago(days + 100), status=status, last_status_change_at=ago(days).isoformat(),
            pipeline="Sales", stage="X")
    out = leads_for("30d")
    assert out["kpis"]["won"]["tracked"] is True and out["kpis"]["won"]["value"] == 1
    assert out["outcomes"]["all_time"] == {"won": 1, "lost": 1, "open": 2}


def test_funnel_follows_the_pipelines_stage_order(venue):
    add(venue, "pipeline", None, name="Sales", stages=[{"name": "New", "position": 0}, {"name": "Tour", "position": 1},
                                                        {"name": "Won", "position": 2}])
    for stage in ("Tour", "New", "New", "Won"):
        add(venue, "opportunity", ago(2), status="open", pipeline="Sales", stage=stage)
    funnel = leads_for()["pipelines"][0]
    assert funnel["ordered"] and [(s["stage"], s["count"]) for s in funnel["stages"]] == [("New", 2), ("Tour", 1), ("Won", 1)]


def test_awaiting_reply_and_channels(venue):
    add(venue, "conversation", ago(30), channel="TYPE_PHONE", last_message_direction="inbound", unread_count=2,
        last_message_at=ago(4).isoformat())
    add(venue, "conversation", ago(30), channel="TYPE_EMAIL", last_message_direction="outbound", unread_count=0,
        last_message_at=ago(1).isoformat())
    add(venue, "conversation", ago(400), channel="TYPE_PHONE", last_message_direction="inbound", unread_count=1,
        last_message_at=ago(300).isoformat())  # stale: never opened in LeadLock
    out = leads_for()
    assert out["kpis"]["awaiting_reply"] == {"value": 1, "oldest_days": 4, "older_unread": 1}
    assert {c["label"]: (c["count"], c["awaiting"]) for c in out["channels"]} == {"SMS / phone": (1, 1), "Email": (1, 0)}


def test_sources_are_tidied_and_all_returned(venue):
    for source in ("Website Inquiry Form", "Website Inquiry Form", "website inquiry form ", ",", None, "Ads",
                   *[f"Source {i}" for i in range(8)]):
        add(venue, "contact", ago(2), source=source)
    sources = leads_for()["sources"]
    assert sources[0] == {"label": "Website Inquiry Form", "count": 3}  # spelling variants merged
    assert {"label": "Not recorded", "count": 2} in sources  # blank and "," alike
    assert len(sources) == 11 and "Other" not in {s["label"] for s in sources}  # nothing folded server-side


def test_new_presets_cover_one_and_two_weeks_and_six_months(venue):
    for days in (3, 10, 100, 170, 200):
        add(venue, "opportunity", ago(days), status="open", pipeline="Sales", stage="New")
    assert leads_for("7d")["kpis"]["inquiries"]["value"] == 1
    assert leads_for("14d")["kpis"]["inquiries"] == {"value": 2, "previous": 0}
    assert leads_for("180d")["kpis"]["inquiries"]["value"] == 4


def test_custom_range_is_inclusive_by_day_and_compares_with_the_same_length_before(venue):
    from datetime import date
    for when in (datetime(2026, 10, 1, 0, 5, tzinfo=UTC), datetime(2026, 10, 10, 23, 59, tzinfo=UTC),
                 datetime(2026, 10, 11, 0, 1, tzinfo=UTC), datetime(2026, 9, 25, tzinfo=UTC)):
        add(venue, "opportunity", when, status="open", pipeline="Sales", stage="New")
    with transaction() as s:
        out = leads.client_leads(s, "venue-one", now=NOW, start_date=date(2026, 10, 1), end_date=date(2026, 10, 10))
    assert out["period"]["key"] == "custom" and out["period"]["days"] == 10
    assert out["period"]["start"].startswith("2026-10-01") and out["period"]["end"].startswith("2026-10-10T23:59:59")
    # 1 Oct 00:05 and 10 Oct 23:59 are in; 11 Oct isn't; 25 Sep falls in the 10 days before (21-30 Sep)
    assert out["kpis"]["inquiries"] == {"value": 2, "previous": 1}


def test_custom_range_is_validated(venue):
    from backend.app import app
    client = TestClient(app)
    ok = client.get("/api/v1/clients/venue-one/leads", params={"start": "2026-10-01", "end": "2026-10-31"})
    assert ok.status_code == 200 and ok.json()["period"]["key"] == "custom"
    for params in ({"start": "2026-10-31", "end": "2026-10-01"}, {"start": "2026-10-01"}, {"end": "2026-10-01"}):
        r = client.get("/api/v1/clients/venue-one/leads", params=params)
        assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_range", params
    assert client.get("/api/v1/clients/venue-one/leads", params={"start": "1 Oct", "end": "2026-10-02"}).status_code == 422


def test_endpoint_is_local_only_and_404s_unknown_clients(venue, monkeypatch):
    from backend.app import app
    client = TestClient(app)
    assert client.get("/api/v1/clients/venue-one/leads").status_code == 200
    assert client.get("/api/v1/clients/nobody/leads").status_code == 404
    assert client.get("/api/v1/clients/venue-one/leads", params={"period": "5y"}).status_code == 400
    monkeypatch.setattr(get_settings(), "environment", "production")
    assert client.get("/api/v1/clients/venue-one/leads").status_code == 404


def test_endpoint_says_when_the_database_is_down(venue, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from backend.app import app

    def down(*a, **k):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
    monkeypatch.setattr(leads, "client_leads", down)
    r = TestClient(app).get("/api/v1/clients/venue-one/leads")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "database_unavailable"


def test_same_named_pipelines_in_two_sub_accounts_stay_apart(venue):
    for loc in ("loc-1", "loc-2"):
        add(venue, "pipeline", None, location_id=loc, name="Inquiry", stages=[{"name": "New"}, {"name": "Won"}])
    add(venue, "opportunity", ago(2), location_id="loc-1", status="open", pipeline="Inquiry", stage="New")
    add(venue, "opportunity", ago(2), location_id="loc-2", status="won", pipeline="Inquiry", stage="Won")
    funnels = leads_for()["pipelines"]
    assert len(funnels) == 2 and {f["pipeline"] for f in funnels} == {"Inquiry"}
    assert {f["sub_account"] for f in funnels} == {"Venue One", None}  # loc-1 is the fixture's mapped sub-account
    assert all(f["ordered"] for f in funnels)


def test_an_unlinked_sub_account_keeps_its_history_and_says_since_when(venue):
    add(venue, "opportunity", ago(5), status="open", pipeline="Sales", stage="New")
    assert leads_for()["collecting"] is True
    with transaction() as s:
        mapping.unassign_scope(s, venue.scope_id, expected_revision=None, actor="t")
    out = leads_for()
    assert out["sub_accounts"] == [] and out["collecting"] is False
    assert out["kpis"]["inquiries"]["value"] == 1  # history stays with the client
    assert out["synced_at"] == ago(0.1).isoformat()  # last copy of the old sub-account
