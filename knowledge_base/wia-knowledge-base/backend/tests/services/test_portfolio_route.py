"""The production portfolio: built by the refresh job, served whole with an ETag; logos only from the build."""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db import transaction
from backend.models.db import WorkItem
from backend.services.clients import mapping
from backend.services.read_models import portfolio


def client():
    from backend.app import app
    return TestClient(app)


def test_not_built_yet_says_so():
    r = client().get("/api/v1/portfolio")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "not_built"


def test_refresh_then_serve_with_etag_and_304():
    with transaction() as s:
        mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
    portfolio.refresh()
    c = client()
    r = c.get("/api/v1/portfolio")
    assert r.status_code == 200 and [x["id"] for x in r.json()["clients"]] == ["venue-one"]
    assert c.get("/api/v1/portfolio", headers={"If-None-Match": r.headers["etag"]}).status_code == 304


def test_a_mapping_decision_queues_one_coalesced_rebuild():
    with transaction() as s:
        mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
        mapping.create_client(s, name="Venue Two", slug="venue-two", actor="t", discover=False)
    with transaction() as s:
        rows = s.execute(select(WorkItem.lane, WorkItem.next_run_at).where(WorkItem.kind == portfolio.JOB)).all()
    assert len(rows) == 1 and rows[0].lane == "maintenance"


def test_logo_route_serves_only_logos_the_build_chose():
    portfolio.refresh()
    assert client().get(f"/api/v1/portfolio/logos/{uuid4()}").status_code == 404


def test_the_build_lists_client_email_as_this_weeks_communication_and_last_contact():
    from datetime import UTC, datetime, timedelta

    from backend.models.db import (
        ConnectorAccount,
        Contact,
        ProviderIdentity,
        RecordAssociation,
        SourceRecord,
        SourceScope,
        SourceVersion,
    )
    with transaction() as s:
        b = mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
        s.add(Contact(id=uuid4(), business_id=b.id, email="dana@venue.example", status="approved"))
        gmail = ConnectorAccount(id=uuid4(), provider="gmail", provider_account_id="hello@agency.example",
                                 expected_identity="hello@agency.example", credential_ref="GOOGLE_REFRESH_TOKEN")
        s.add(gmail)
        s.flush()
        s.add(ProviderIdentity(id=uuid4(), connector_account_id=gmail.id, external_key="dana@venue.example",
                               email="dana@venue.example", display_name="Dana Venue", party="client"))
        scope = SourceScope(id=uuid4(), connector_account_id=gmail.id, kind="mailbox", external_id="hello@agency.example",
                            name="hello@", state="approved", default_domain="communications", association_mode="per_record")
        s.add(scope)
        s.flush()
        at = datetime.now(UTC) - timedelta(days=1)
        r = SourceRecord(id=uuid4(), connector_account_id=gmail.id, scope_id=scope.id, record_kind="gmail_message",
                         external_id="m1", occurred_at=at, admitted_at=at, qualification="metadata_only")
        s.add(r)
        s.flush()
        v = SourceVersion(id=uuid4(), record_id=r.id, version_key="v1", content_sha256="0" * 64, parser_version="gmail-v3",
                          content_state="metadata_only", attributes={"from": "dana@venue.example", "subject": "Spring dates"})
        s.add(v)
        s.flush()
        r.current_version_id = v.id
        s.add(RecordAssociation(id=uuid4(), record_id=r.id, business_id=b.id, basis="verified_contact"))
    out = portfolio.build()
    [item] = out["comms"]["venue-one"]
    assert (item["from"], item["who"], item["text"]) == ("Client", "Dana Venue", "Spring dates")
    assert out["records"]["venue-one"]["lastContact"]["channel"] == "Gmail"
    assert out["clients"][0]["lastTouch"] == item["date"]


def _client_meeting(slug="venue-one"):
    from datetime import UTC, datetime

    from backend.models.db import (
        ConnectorAccount,
        RecordAssociation,
        SourceRecord,
        SourceScope,
    )
    with transaction() as s:
        b = mapping.create_client(s, name=slug.replace("-", " ").title(), slug=slug, actor="t", discover=False)
        acc = s.execute(select(ConnectorAccount).where(ConnectorAccount.provider == "calendar")).scalar_one_or_none()
        if acc is None:
            acc = ConnectorAccount(id=uuid4(), provider="calendar", provider_account_id="hello@agency.example",
                                   expected_identity="hello@agency.example", credential_ref="GOOGLE_REFRESH_TOKEN")
            s.add(acc)
            s.flush()
            s.add(SourceScope(id=uuid4(), connector_account_id=acc.id, kind="calendar", external_id="primary", name="primary",
                              state="approved", default_domain="meetings", association_mode="per_record"))
            s.flush()
        r = SourceRecord(id=uuid4(), connector_account_id=acc.id, record_kind="calendar_event", external_id=str(uuid4()),
                         occurred_at=datetime(2026, 9, 2, 15, tzinfo=UTC), qualification="metadata_only")
        s.add(r)
        s.flush()
        s.add(RecordAssociation(id=uuid4(), record_id=r.id, business_id=b.id, basis="verified_contact"))
        return r.id


def test_a_team_member_can_add_and_remove_a_meeting_link():
    from backend.models.db import AuditEvent, MeetingLink
    rid = _client_meeting()
    c = client()
    r = c.put(f"/api/v1/clients/venue-one/meetings/{rid}/link", json={"url": " https://zoom.us/rec/share/abc "})
    assert r.status_code == 200 and r.json()["link"] == "https://zoom.us/rec/share/abc"
    with transaction() as s:
        assert s.get(MeetingLink, rid).url == "https://zoom.us/rec/share/abc"
        assert s.execute(select(AuditEvent.action).where(AuditEvent.action == "meeting.link_set")).first()
    assert c.delete(f"/api/v1/clients/venue-one/meetings/{rid}/link").status_code == 200
    with transaction() as s:
        assert s.get(MeetingLink, rid) is None


def test_links_must_be_web_links_on_that_clients_own_meetings():
    rid = _client_meeting()
    _client_meeting("venue-two")
    c = client()
    for bad in ("zoom.us/rec/abc", "javascript:alert(1)", "https://", "ftp://files/x", "https://a b.com", "https://x.com/" + "a" * 1000):
        r = c.put(f"/api/v1/clients/venue-one/meetings/{rid}/link", json={"url": bad})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "refused", bad
    r = c.put(f"/api/v1/clients/venue-two/meetings/{rid}/link", json={"url": "https://zoom.us/rec/abc"})
    assert r.status_code == 400 and "isn't one of this client's" in r.json()["detail"]["message"]
    assert c.put(f"/api/v1/clients/venue-one/meetings/{uuid4()}/link", json={"url": "https://zoom.us/rec/abc"}).status_code == 400


# --- scale: what the build loads, how it is served, one build at a time ------------------------------------------

def _version_with_units(units):
    """A Fathom-like stored version with the given (unit_kind, is_quoted, provider_generated, domain) units."""
    from backend.models.db import ConnectorAccount, ContentUnit, SourceRecord, SourceVersion
    with transaction() as s:
        acc = ConnectorAccount(id=uuid4(), provider="fathom", provider_account_id=str(uuid4()), expected_identity="x",
                               credential_ref="FATHOM_API_KEY")
        s.add(acc)
        s.flush()
        r = SourceRecord(id=uuid4(), connector_account_id=acc.id, record_kind="fathom_recording",
                         external_id=str(uuid4()), qualification="content")
        s.add(r)
        s.flush()
        v = SourceVersion(id=uuid4(), record_id=r.id, version_key="v", content_sha256="0" * 64, parser_version="t",
                          content_state="content", attributes={})
        s.add(v)
        s.flush()
        for n, (kind, quoted, generated, domain) in enumerate(units):
            s.add(ContentUnit(id=uuid4(), version_id=v.id, ordinal=n, unit_kind=kind, locator={}, text=f"u{n}",
                              text_sha256="0" * 64, is_quoted=quoted, provider_generated=generated, domain=domain,
                              retention_category="t", retention_state="retained"))
        return v.id


def test_the_build_keeps_only_the_units_it_reads_and_gets_the_same_answers():
    from backend.models.db import ContentUnit, SourceVersion
    seg = ("transcript_segment", False, False, "meetings")
    mixed = _version_with_units([("message", True, False, "finance"), ("provider_action_item", False, True, "finance"),
                                 ("transcript_segment", False, False, "finance"), ("provider_summary", False, True, "meetings"),
                                 *[seg] * 200])
    finance = _version_with_units([("doc_paragraph", False, False, "finance")] * 50)
    whole = _version_with_units([seg] * 30)
    ids = [mixed, finance, whole]
    with transaction() as s:
        full = {v: s.scalars(select(ContentUnit).where(ContentUnit.version_id == v).order_by(ContentUnit.ordinal)).all()
                for v in ids}
        kept = portfolio.needed_units(s, select(SourceVersion.id).where(SourceVersion.id.in_(ids)), {whole})

    def answers(us):  # every question build() asks of a version's units
        return (us[0].id, next((u.id for u in us if not u.is_quoted), None),
                next((u.id for u in us if not u.is_quoted and not u.provider_generated), None),
                next((u.id for u in us if u.unit_kind == "provider_summary"), None),
                all(u.domain == "finance" for u in us))

    for v in ids:
        assert answers(kept[v]) == answers(full[v])
    assert len(kept[mixed]) <= 5 and len(kept[finance]) == 1 and len(kept[whole]) == 30


def test_call_prep_failing_leaves_the_rest_of_the_portfolio_built(monkeypatch):
    from backend.services.callprep import present as call_prep
    with transaction() as s:
        mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
    monkeypatch.setattr(call_prep, "calls", lambda *a, **k: 1 / 0)
    out = portfolio.build()
    assert [c["id"] for c in out["clients"]] == ["venue-one"] and out["calls"] == []


def test_the_portfolio_is_gzipped_once_per_build_and_still_served_plain_on_request():
    from backend.routes import portfolio as route
    with transaction() as s:
        mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
    portfolio.refresh()
    c = client()
    r = c.get("/api/v1/portfolio")
    assert r.headers["content-encoding"] == "gzip" and r.json()["clients"][0]["id"] == "venue-one"
    assert list(route._gzipped) == [r.headers["etag"]]
    cached = route._gzipped[r.headers["etag"]]
    assert c.get("/api/v1/portfolio").content == r.content and route._gzipped[r.headers["etag"]] is cached
    plain = c.get("/api/v1/portfolio", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in plain.headers and plain.json() == r.json()
    portfolio.refresh()  # a new build replaces the cached one
    newer = c.get("/api/v1/portfolio")
    assert newer.headers["etag"] != r.headers["etag"] and list(route._gzipped) == [newer.headers["etag"]]


def test_only_one_portfolio_build_runs_and_a_busy_one_queues_the_next():
    from sqlalchemy import text

    from backend.db import engine
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as other:
        other.execute(text("SELECT pg_advisory_lock(:k)"), {"k": portfolio.BUILD_LOCK})
        try:
            assert portfolio.refresh() is None
        finally:
            other.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": portfolio.BUILD_LOCK})
    with transaction() as s:
        assert s.execute(select(WorkItem).where(WorkItem.kind == portfolio.JOB)).first() is not None
    assert portfolio.refresh() is not None  # the lock is free again
