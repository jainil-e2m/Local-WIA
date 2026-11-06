"""Connections > LeadLock: sub-account states, name suggestions, and the mapping commands behind them.

Mapping is what starts collection (FR-INT-01): an unmapped sub-account is never read, a mapped one queues its
full-history copy, a remap moves what was already collected, and LeadLock never runs in shared mode."""
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import (Business, ConnectorAccount, LeadLockLocation, RecordAssociation, SourceRecord,
                               SourceScope, SyncRun)
from backend.models.db.base import utcnow
from backend.services.clients import connections, mapping
from backend.services.read_models import leads


def _business(b_list, name):
    return next(b for b in b_list if b.name == name)


@pytest.fixture
def agency():
    """A LeadLock agency with sub-accounts of every kind, and clients (one archived)."""
    with transaction() as s:
        s.add(ConnectorAccount(id=uuid4(), provider="leadlock", provider_account_id="co", expected_identity="co",
                               credential_ref="leadlock_installations"))
        mapping.create_client(s, name="The Weinberg", slug="the-weinberg", actor="t", discover=False)
        mapping.create_client(s, name="Dogwood Reserve", slug="dogwood-reserve", actor="t", discover=False)
        archived = mapping.create_client(s, name="The Penny", slug="the-penny", actor="t", discover=False)
        mapping.set_client_status(s, archived.id, "inactive", expected_revision=None, actor="t")
        for location_id, name, state in (("loc-weinberg", "The Weinberg at Wixon Valley", "active"),
                                         ("loc-dogwood", "Dogwood Reserve", "active"),
                                         ("loc-penny", "The Penny", "active"),
                                         ("loc-demo", "Venue Demo Subaccount", "active"),
                                         ("loc-other", "Mangieri Electric", "active"),
                                         ("loc-broken", "One Eleven East", "failed")):
            s.add(LeadLockLocation(id=uuid4(), location_id=location_id, name=name, state=state, installed_at=utcnow(),
                                   last_error="token refused" if state == "failed" else None))


def rows(client=None):
    with transaction() as s:
        return {r["location_id"]: r for r in connections.leadlock_rows(s, client)["rows"]}


def map_(location_id, slug, **kw):
    """As the route does it: the mapping commits, then collection starts in its own transaction."""
    with transaction() as s:
        out = connections.map_location(s, location_id, slug, expected_revision=kw.pop("rev", None), actor="t", **kw)
    with transaction() as s:
        out["collection"] = connections.start_collection(s, UUID(out.pop("scope_id")))
    return out


def test_suggestions_match_distinctive_words_and_stay_quiet_when_unsure():
    clients = [(Business(id=uuid4(), name=n, slug=n.lower(), status="active", revision=1), aliases) for n, aliases in (
        ("The Weinberg", []), ("SK Designs & Events", []), ("Evergreen Venues", []),
        ("Ridgefield Weddings and Events", []), ("Dos Palomas Ranch", ["Dos Palomas"]))]
    hit = lambda name: (connections.suggest_client(name, clients) or (None,))[0]
    assert hit("The Weinberg at Wixon Valley").name == "The Weinberg"
    assert hit("SK Events & Design LLC").name == "SK Designs & Events"  # plural and word order
    assert hit("Evergreen Venue").name == "Evergreen Venues"
    assert hit("Ridgefield ").name == "Ridgefield Weddings and Events"  # the shorter name inside the longer
    assert hit("Mangieri Electric") is None
    assert hit("Weddings & Events") is None  # only generic words: never a match
    assert connections.suggest_client(None, clients) is None


def test_every_installed_sub_account_is_listed_in_one_state(agency):
    r = rows()
    assert r["loc-weinberg"]["state"] == "suggested" and r["loc-weinberg"]["suggestion"]["client"]["slug"] == "the-weinberg"
    assert r["loc-demo"]["state"] == "suggested" and r["loc-demo"]["suggestion"]["kind"] == "not_a_client"
    assert r["loc-other"]["state"] == "needs_client" and r["loc-other"]["suggestion"] is None
    assert r["loc-broken"]["state"] == "access_failed" and r["loc-broken"]["access_error"] == "token refused"
    assert not any(x["is_new"] for x in r.values())  # the initial batch isn't "new"
    with transaction() as s:
        s.add(LeadLockLocation(id=uuid4(), location_id="loc-later", name="Brand New Venue", state="active",
                               installed_at=utcnow() + timedelta(days=2)))
    assert rows()["loc-later"]["is_new"]  # auto-installed after the first batch
    # Archived clients still get suggested: mapping them is how production gets all clients in.
    assert r["loc-penny"]["suggestion"]["client"]["status"] == "inactive"


def test_mapping_starts_the_full_history_copy(agency):
    out = map_("loc-dogwood", "dogwood-reserve")
    assert out == {"collection": "started", "moved_records": 0, "revision": out["revision"]}
    with transaction() as s:
        scope = s.execute(select(SourceScope).where(SourceScope.external_id == "loc-dogwood")).scalar_one()
        assert (scope.state, scope.association_mode) == ("approved", "dedicated")
        run = s.execute(select(SyncRun).where(SyncRun.scope_id == scope.id)).scalar_one()
        assert run.mode == "backfill" and run.window_start is None  # full obtainable history
    r = rows()["loc-dogwood"]
    assert r["state"] == "mapped" and r["collection"] == "collecting" and r["client"]["slug"] == "dogwood-reserve"
    assert map_("loc-dogwood", "dogwood-reserve")["collection"] == "already_running"


def test_mapping_to_an_archived_client_waits_unless_reactivated(agency):
    assert map_("loc-penny", "the-penny")["collection"] == "waiting_client_archived"
    assert rows()["loc-penny"]["collection"] == "paused_client_archived"
    with transaction() as s:
        assert not s.execute(select(SyncRun)).first()  # nothing is read for an archived client
    assert map_("loc-penny", "the-penny", reactivate=True)["collection"] == "started"
    with transaction() as s:
        assert mapping.business_by_slug(s, "the-penny").status == "active"


def test_no_access_means_mapped_but_not_read(agency):
    assert map_("loc-broken", "dogwood-reserve")["collection"] == "waiting_access"
    with transaction() as s:
        assert not s.execute(select(SyncRun)).first()


def test_leadlock_is_never_shared(agency):
    map_("loc-dogwood", "dogwood-reserve")
    with transaction() as s:
        scope = s.execute(select(SourceScope).where(SourceScope.external_id == "loc-dogwood")).scalar_one()
        with pytest.raises(mapping.MappingError, match="exactly one client"):
            mapping.assign_scope(s, scope.id, business_id=None, expected_revision=None, actor="t")


def _collected_lead(location_id, slug):
    """One stored LeadLock record attached by the scope mapping, as a backfill would leave it."""
    with transaction() as s:
        scope = s.execute(select(SourceScope).where(SourceScope.external_id == location_id)).scalar_one()
        business = mapping.business_by_slug(s, slug)
        record = SourceRecord(id=uuid4(), connector_account_id=scope.connector_account_id, scope_id=scope.id,
                              record_kind="leadlock_opportunity", external_id=str(uuid4()), occurred_at=utcnow(),
                              admitted_at=utcnow(), qualification="metadata_only", provider_state={})
        s.add(record)
        s.flush()
        s.add(RecordAssociation(id=uuid4(), record_id=record.id, business_id=business.id, basis="scope_mapping"))
        return record.id


def test_remapping_moves_what_was_already_collected(agency):
    map_("loc-weinberg", "dogwood-reserve")  # the wrong client, by mistake
    record_id = _collected_lead("loc-weinberg", "dogwood-reserve")
    with transaction() as s:
        s.execute(SyncRun.__table__.update().values(state="succeeded"))  # let the copy finish
    out = map_("loc-weinberg", "the-weinberg")
    assert out["moved_records"] == 1
    with transaction() as s:
        links = {(mapping.business_by_slug(s, slug).id, status) for slug, status in
                 (("dogwood-reserve", "rejected"), ("the-weinberg", "associated"))}
        found = {(a.business_id, a.status) for a in s.execute(
            select(RecordAssociation).where(RecordAssociation.record_id == record_id)).scalars()}
        assert found == links  # the old link stays, marked rejected; the new one is live


def test_unmap_stops_reading_and_keeps_history(agency):
    map_("loc-dogwood", "dogwood-reserve")
    record_id = _collected_lead("loc-dogwood", "dogwood-reserve")
    revision = rows()["loc-dogwood"]["revision"]
    with transaction() as s:
        connections.unmap_location(s, "loc-dogwood", expected_revision=revision, actor="t")
        assert s.execute(select(RecordAssociation.status).where(RecordAssociation.record_id == record_id)).scalar_one() == "associated"
    assert rows()["loc-dogwood"]["state"] == "suggested"


def test_not_a_client_is_remembered_and_can_be_undone(agency):
    with transaction() as s:
        connections.mark_not_a_client(s, "loc-demo", expected_revision=None, actor="t", reason="demo account")
    assert rows()["loc-demo"]["state"] == "not_a_client"
    with pytest.raises(mapping.MappingError, match="restore it first"):
        map_("loc-demo", "dogwood-reserve")
    with transaction() as s:
        connections.restore_location(s, "loc-demo", expected_revision=None, actor="t")
    assert rows()["loc-demo"]["state"] == "suggested"
    map_("loc-dogwood", "dogwood-reserve")
    with pytest.raises(mapping.MappingError, match="unmap"), transaction() as s:
        connections.mark_not_a_client(s, "loc-dogwood", expected_revision=None, actor="t")


def test_client_side_view_shows_its_own_and_suggested_sub_accounts(agency):
    map_("loc-dogwood", "dogwood-reserve")
    assert set(rows("dogwood-reserve")) == {"loc-dogwood"}
    assert set(rows("the-weinberg")) == {"loc-weinberg"}  # suggested for it, not mapped yet


def test_endpoints_are_local_only_and_refuse_stale_edits(agency, monkeypatch):
    from backend.app import app
    client = TestClient(app)
    assert client.get("/api/v1/connections/leadlock").json()["counts"]["needs_client"] == 1
    r = client.post("/api/v1/connections/leadlock/loc-weinberg/map", json={"client": "the-weinberg"})
    assert r.status_code == 200 and r.json()["collection"] == "started"
    stale = client.post("/api/v1/connections/leadlock/loc-weinberg/unmap", json={"expected_revision": 1})
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "changed_elsewhere"
    assert client.post("/api/v1/connections/leadlock/loc-nope/map", json={"client": "the-weinberg"}).status_code == 400
    created = client.post("/api/v1/clients", json={"name": "Mangieri  Electric"})
    assert created.status_code == 201 and created.json()["slug"] == "mangieri-electric"
    assert client.post("/api/v1/clients", json={"name": "Mangieri Electric"}).status_code == 400  # slug taken
    monkeypatch.setattr(get_settings(), "environment", "production")
    assert client.get("/api/v1/connections/leadlock").status_code == 404
    assert client.post("/api/v1/clients", json={"name": "X Y"}).status_code == 404


def _cells(slug):
    from backend.services.clients import client_connections
    with transaction() as s:
        out = client_connections.overview(s)
    return next(c for c in out["clients"] if c["slug"] == slug)["cells"], out


def test_client_view_has_one_state_per_channel(agency):
    from backend.services.clients import client_connections
    map_("loc-dogwood", "dogwood-reserve")
    cells, out = _cells("dogwood-reserve")
    assert [c["id"] for c in out["channels"]] == ["leadlock", "slack", "clickup", "drive", "contacts"]
    assert cells["leadlock"]["state"] == "linked" and cells["leadlock"]["linked"][0]["ref"] == {"kind": "location", "id": "loc-dogwood"}
    assert cells["slack"]["state"] == "not_connected"  # no Slack account in this fixture
    assert cells["contacts"]["state"] == "not_connected"
    weinberg, _ = _cells("the-weinberg")
    assert weinberg["leadlock"]["state"] == "suggested"
    penny, _ = _cells("the-penny")
    assert penny["leadlock"]["state"] == "suggested"  # archived clients still get their suggestion
    # Sub-accounts with no client stay out of the client rows: demo, electrician, broken access.
    assert out["unassigned_leadlock"]["count"] == 3
    with transaction() as s:
        client_connections.set_applicable(s, client="the-weinberg", channel="leadlock", applicable=False,
                                          reason="no LeadLock", actor="t")
    assert _cells("the-weinberg")[0]["leadlock"]["state"] == "not_applicable"


def test_linking_a_dedicated_source_starts_collection_and_contacts_attach_shared_ones(agency):
    from backend.services.clients import client_connections
    with transaction() as s:
        slack = ConnectorAccount(id=uuid4(), provider="slack", provider_account_id="T1", expected_identity="T1",
                                 credential_ref="env")
        gmail = ConnectorAccount(id=uuid4(), provider="gmail", provider_account_id="hello@", expected_identity="hello@",
                                 credential_ref="env")
        s.add_all([slack, gmail])
        s.flush()
        channel = SourceScope(id=uuid4(), connector_account_id=slack.id, kind="channel", external_id="C1",
                              name="c_dogwood", state="candidate", default_domain="communications", association_mode="dedicated",
                              suggested_business_id=mapping.business_by_slug(s, "dogwood-reserve").id, revision=1)
        s.add(channel)
    cells, out = _cells("dogwood-reserve")
    assert cells["slack"]["state"] == "suggested" and out["options"]["slack"][0]["name"] == "c_dogwood"
    with transaction() as s:
        res = client_connections.link(s, client="dogwood-reserve", channel="slack",
                                      ref={"kind": "scope", "id": str(channel.id)}, expected_revision=1, actor="t")
    with transaction() as s:
        assert connections.start_collection(s, UUID(res["scope_id"])) == "started"
    assert _cells("dogwood-reserve")[0]["slack"]["state"] == "linked"
    with transaction() as s:
        client_connections.add_contact(s, client="dogwood-reserve", value="@DogwoodReserve.com", actor="t")
    contacts = _cells("dogwood-reserve")[0]["contacts"]
    assert contacts["state"] == "linked" and contacts["linked"][0]["name"] == "anyone @dogwoodreserve.com"
    with transaction() as s:
        client_connections.unlink(s, channel="contacts", ref=contacts["linked"][0]["ref"],
                                  expected_revision=contacts["linked"][0]["revision"], actor="t")
    assert _cells("dogwood-reserve")[0]["contacts"]["state"] == "missing"
    with pytest.raises(mapping.MappingError), transaction() as s:
        client_connections.link(s, client="dogwood-reserve", channel="clickup",
                                ref={"kind": "scope", "id": str(channel.id)}, expected_revision=None, actor="t")


def test_a_mapped_venue_shows_up_on_its_leads_tab(agency):
    map_("loc-dogwood", "dogwood-reserve")
    _collected_lead("loc-dogwood", "dogwood-reserve")
    with transaction() as s:
        assert leads.client_leads(s, "dogwood-reserve", "all")["sub_accounts"][0]["location_id"] == "loc-dogwood"
