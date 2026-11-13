"""Call preparation: skill files, the call registry, the facts layer, the evidence pack, the checks, versions and
the scheduler, the runner end to end (OpenRouter mocked), the routes, and the ad-platform scripts (HTTP mocked).
All names are invented."""
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import (AdAccount, AdDaily, AiRun, CallBrief, ConnectorAccount, Contact, Person, PersonAddress,
                               RecordAssociation, SourceRecord, SourceScope, SourceVersion)
from backend.services import ads
from backend.services.ads import google_ads, meta
from backend.services.ai import runner
from backend.services.callprep import briefs, checks, facts, pack, registry, schedule, skill_files
from backend.services.clients import mapping
from backend.services.read_models import portfolio

NOW = datetime.now(UTC)
CLIENT, STAFF, OTHER = "owner@venue-one.example", "ana@wia.example", "pat@wia.example"


# ---- skill files ---------------------------------------------------------------------------------------------

def test_every_seed_skill_parses_and_detects_real_title_shapes():
    skills = skill_files.load_all()
    assert set(skills) >= {"strategy", "creative", "checkin", "ads-kickoff", "leadlock-kickoff", "messaging",
                           "office-hours", "other"}
    assert skill_files.detect(skills, "Venue One Monthly Meeting").key == "strategy"
    assert skill_files.detect(skills, "Monthly Strategy | Venue One").key == "strategy"
    assert skill_files.detect(skills, "Creative Review | Venue One").key == "creative"
    assert skill_files.detect(skills, "Ads Kickoff - Venue One").key == "ads-kickoff"
    assert skill_files.detect(skills, "LeadLock Kickoff").key == "leadlock-kickoff"
    assert skill_files.detect(skills, "Check-in with Pat").key == "checkin"
    assert skill_files.detect(skills, "Something else").key == "other"
    for sales in ("Ads Consultation with Pat", "LeadLock Demo", "Coffee Chat", "Discovery call"):
        assert skill_files.excluded(skills, sales)
    assert not skill_files.excluded(skills, "Monthly Strategy | Venue One")


def test_a_bad_skill_file_names_the_problem():
    good = skill_files.seed_files()["checkin"]
    with pytest.raises(skill_files.SkillError, match="blocks"):
        skill_files.parse(good.replace("  leads: true", "  website: true"))
    with pytest.raises(skill_files.SkillError, match="Guidance"):
        skill_files.parse(good.replace("## Guidance", "## Notes"))
    with pytest.raises(skill_files.SkillError, match="bad pattern"):
        skill_files.parse(good.replace("detect: ['check[- ]?in'", "detect: ['check[- in'"))


def test_edits_are_versions_that_a_reseed_never_overwrites():
    with transaction() as s:
        assert len(skill_files.seed(s)) == len(skill_files.seed_files())
        assert skill_files.seed(s) == []  # unchanged repo files: nothing to do
        text = skill_files.seed_files()["checkin"].replace("Be warm and specific", "Be brief and warm")
        row = skill_files.save(s, "checkin", text, by="Ana")
        assert row.version == 2 and skill_files.load_all(s)["checkin"].ref == "db:checkin:2"
        assert skill_files.load_all(s)["checkin"].edited["by"] == "Ana"
        assert skill_files.seed(s) == []  # the edit stays
        clash = text.replace("detect: ['check[- ]?in'", "detect: ['strategy'")
        with pytest.raises(skill_files.SkillError, match="already belongs"):
            skill_files.save(s, "checkin", clash, by="Ana")
        assert skill_files.revert(s, "checkin", 1, by="Ana").version == 3
        assert "Be warm and specific" in skill_files.load_all(s)["checkin"].body["Guidance"]
        assert [v["version"] for v in skill_files.versions(s, "checkin")] == [3, 2, 1]


# ---- fixture: one client, a staff host, an upcoming call, an email awaiting our reply ---------------------------

def _account(s, provider):
    a = ConnectorAccount(id=uuid4(), provider=provider, provider_account_id=provider, expected_identity=provider,
                         credential_ref="X")
    s.add(a)
    s.flush()
    sc = SourceScope(id=uuid4(), connector_account_id=a.id, kind="mailbox", external_id=provider, name=provider,
                     state="approved", default_domain="communications", association_mode="per_record")
    s.add(sc)
    s.flush()
    return a, sc


def _record(s, account, scope, kind, at, attrs, business):
    r = SourceRecord(id=uuid4(), connector_account_id=account.id, scope_id=scope.id, record_kind=kind,
                     external_id=str(uuid4()), occurred_at=at, admitted_at=at)
    s.add(r)
    s.flush()
    v = SourceVersion(id=uuid4(), record_id=r.id, version_key="v1", content_sha256="0" * 64, parser_version="t",
                      content_state="metadata_only", attributes=attrs)
    s.add(v)
    s.flush()
    r.current_version_id = v.id
    s.add(RecordAssociation(id=uuid4(), record_id=r.id, business_id=business.id, basis="verified_contact"))
    s.flush()
    return r


def event(start, title="Venue One Monthly Meeting", client_response="needsAction", status="confirmed"):
    return {"summary": title, "status": status, "organizer": STAFF, "ical_uid": str(uuid4()),
            "end": {"date_time": (start + timedelta(minutes=30)).isoformat()},
            "attendees": [{"email": CLIENT, "response": client_response}, {"email": STAFF, "response": "accepted"},
                          {"email": OTHER, "response": "accepted"}]}


@pytest.fixture
def world():
    with transaction() as s:
        b = mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
        s.add(Contact(id=uuid4(), business_id=b.id, email=CLIENT, status="approved"))
        ana = Person(id=uuid4(), name="Ana Reyes", kind="staff")
        s.add(ana)
        s.flush()
        s.add(PersonAddress(id=uuid4(), person_id=ana.id, kind="email", value=STAFF))
        cal, cal_scope = _account(s, "calendar")
        gmail, gmail_scope = _account(s, "gmail")
        start = NOW + timedelta(hours=20)
        call = _record(s, cal, cal_scope, "calendar_event", start, event(start), b)
        past = NOW - timedelta(days=10)
        _record(s, cal, cal_scope, "calendar_event", past, event(past, client_response="accepted"), b)
        _record(s, gmail, gmail_scope, "gmail_message", NOW - timedelta(days=3),
                {"from": f"Owner <{CLIENT}>", "subject": "Question about the new page", "thread_id": "t1"}, b)
        _record(s, gmail, gmail_scope, "gmail_message", NOW - timedelta(days=2),
                {"from": CLIENT, "subject": "Automatic reply: out of office", "thread_id": "t2"}, b)
        return {"business": b.id, "call": call.id, "call_id": "cal-" + call.id.hex, "start": start, "gmail": (gmail, gmail_scope)}


ACTIONS = [
    {"id": "cu-1", "clientId": "venue-one", "title": "Send the revised page", "owner": "Ana", "due": (NOW - timedelta(days=4)).date().isoformat(),
     "status": "Open", "side": "WIA", "sourceId": "kb-1"},
    {"id": "cu-2", "clientId": "venue-one", "title": "Approve the gallery", "owner": "Owner", "due": NOW.date().isoformat(),
     "status": "Open", "side": "Client", "sourceId": "kb-2"},
    {"id": "cu-3", "clientId": "venue-one", "title": "Archive old campaign", "owner": "", "due": "", "status": "Done",
     "side": "WIA", "sourceId": "kb-3"},
]


def data():
    return {"actions": ACTIONS, "events": [
        {"id": "ev-1", "clientId": "venue-one", "date": (NOW - timedelta(days=3)).date().isoformat(), "lane": "Communication",
         "title": "Question about the new page", "detail": "Gmail", "from": "Client", "sourceId": "kb-9"}],
        "records": {"venue-one": {"lastContact": {"date": (NOW - timedelta(days=3)).date().isoformat(), "channel": "Gmail"},
                                  "profile": [{"section": "Goals", "facts": [{"label": "What success means", "value": "40 tours a month", "sourceId": "kb-p"}]}],
                                  "sources": []}}, "recaps": []}


# ---- registry and facts ----------------------------------------------------------------------------------------

def test_a_calendar_event_becomes_a_call_with_type_host_and_rsvp_risk(world):
    with transaction() as s:
        [call] = registry.calls(s, NOW, NOW + timedelta(days=2))
        assert (call.skill.key, call.type_source, call.host, call.host_source) == ("strategy", "Calendar title", "Ana Reyes", "Organiser")
        assert call.attendance_risk == "The client hasn't accepted the invite yet"
        assert call.previous is not None and call.excluded is None
        registry.set_override(s, world["call"], actor="t", call_type="creative", host="Pat Lee")
    with transaction() as s:
        call = registry.get(s, world["call"])
        assert (call.skill.key, call.type_source, call.host) == ("creative", "Set by the team", "Pat Lee")
        registry.set_override(s, world["call"], actor="t", excluded=True)
    with transaction() as s:
        assert registry.get(s, world["call"]).excluded == "Set aside by the team"


def test_facts_are_computed_by_code_and_skip_auto_replies(world):
    with transaction() as s:
        call = registry.get(s, world["call"])
        f = facts.compute(s, call, data(), NOW)
    assert [a["id"] for a in f["owed"]["we"]] == ["cu-1"] and f["owed"]["overdue"] == 1
    assert [a["id"] for a in f["owed"]["they"]] == ["cu-2"]
    assert [w["subject"] for w in f["awaiting"]] == ["Question about the new page"]  # the auto-reply is not waiting
    assert [x["tone"] for x in f["settle"]] == ["late", "ask", "wait"]
    assert f["pulse"]["delivery"]["value"] == "1 overdue" and f["pulse"]["client"]["value"] == "1 awaiting our reply"
    assert f["pulse"]["ads"]["value"] == "Not connected" and any("not connected" in x for x in f["limits"])
    assert f["window"]["basis"] == "last call" and f["changed"][0]["from"] == "Client"


def test_the_pack_cites_facts_and_its_fingerprint_ignores_ages(world):
    with transaction() as s:
        call = registry.get(s, world["call"])
        p = pack.build(s, call, data=data(), now=NOW, fetch=lambda mid: {"authored": "Can we see the page this week?"})
        system, user = pack.render(p)
        later = pack.build(s, call, data=data(), now=NOW + timedelta(hours=3), read_bodies=False)
    assert "[A1] Send the revised page" in user and "[W1]" in user and "40 tours a month" in user
    assert "Monthly strategy" in system
    assert "Google Ads: not connected" in user
    assert p.fingerprint == later.fingerprint  # three hours later, nothing changed


# ---- checks ----------------------------------------------------------------------------------------------------

def test_checks_drop_invented_figures_leave_out_topics_and_missing_refs():
    skill = skill_files.load_all()["strategy"]
    texts = ["[L1] LeadLock, last 30 days: inquiries 95 (previous 30 days 88)", "[A1] Send the revised page"]
    c = checks.BriefChecks(skill, {"L1": {}, "A1": {}}, texts)
    out, core = c.run({
        "goal": "Agree next month's plan from 95 inquiries", "standing": "Inquiries are up on the previous 30 days.",
        "risk": "Inquiries fell 40% last week", "talking_points": [
            {"text": "Inquiries rose to 95 from 88", "why": "results", "refs": ["L1"]},
            {"text": "Inquiries are up 8%", "why": "results", "refs": ["L1"]},   # 8% isn't in the sources
            {"text": "Revisit the onboarding checklist", "why": "x", "refs": ["A1"]},  # a leave-out term
            {"text": "Something with no source", "why": "x", "refs": ["Z9"]}],
        "questions": [], "watch_outs": [], "opportunity": None, "type_block": [{"label": "Leads", "value": "95", "ref": "L1"}],
        "changed_highlights": ["H1", "L1"], "declined": None})
    assert core == [] and out["risk"] is None
    assert [p["text"] for p in out["talking_points"]] == ["Inquiries rose to 95 from 88"]
    assert {d["why"].split(":")[0] for d in c.dropped} >= {"figure not in the sources", "leave-out topic", "no ref from the sources"}
    _, core = checks.BriefChecks(skill, {}, texts).run({"goal": "Plan for 120 inquiries", "standing": "Fine.",
                                                         "risk": None, "talking_points": [], "questions": [], "watch_outs": [],
                                                         "opportunity": None, "type_block": [], "changed_highlights": []})
    assert core == ["goal"]


# ---- runner end to end, versions, scheduler ------------------------------------------------------------------

BRIEF = {"goal": "Agree when the revised page gets approved", "standing": "The client is waiting on the revised page.",
         "risk": "We are 4 days late on the page", "talking_points": [
             {"text": "Answer the question about the new page", "why": "awaiting our reply", "refs": ["W1"]},
             {"text": "Send the revised page and agree an approval date", "why": "late", "refs": ["A1"]}],
         "questions": [], "watch_outs": [{"text": "Acknowledge the late page first", "audience": "internal", "refs": ["A1"]}],
         "opportunity": None, "type_block": [], "changed_highlights": ["H1"], "declined": None}


def answer(payload, cost=0.03):
    return {"choices": [{"message": {"content": json.dumps(payload)}}], "model": "anthropic/claude-sonnet-5.5",
            "usage": {"prompt_tokens": 9000, "completion_tokens": 700, "cost": cost}}


@pytest.fixture
def live(monkeypatch):
    for k, v in (("ai_mode", "live"), ("openrouter_api_key", "k"), ("ai_monthly_budget_usd", 5.0)):
        monkeypatch.setattr(get_settings(), k, v)


def _snapshot():
    with transaction() as s:
        from backend.models.db import ReadModelSnapshot
        s.merge(ReadModelSnapshot(name="portfolio", built_at=NOW, payload=data()))


def test_a_brief_is_built_checked_and_stored_as_a_version(world, live):
    portfolio.refresh()  # the brief reads the stored build; this one has no ClickUp tasks
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=answer(BRIEF))
    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetch = lambda mid: {"authored": "Can we see the page this week?"}  # noqa: E731
    run = runner.run("call_brief", str(world["call"]), client=client, fetch=fetch, options={"trigger": "first", "built_by": "auto"})
    assert run.state == "succeeded" and len(sent) == 1
    assert "Monthly strategy" in sent[0]["messages"][0]["content"][0]["text"]
    with transaction() as s:
        [row] = briefs.history(s, world["call"])
        assert (row.version, row.is_current, row.outcome, row.skill_key) == (1, True, "ready", "strategy")
        assert row.output["risk"] is None  # no task is late in this build, so "4 days" is in no source
        assert [p["refs"] for p in row.output["talking_points"]] == [["W1"]]  # A1 isn't in this pack
    assert runner.run("call_brief", str(world["call"]), client=client, fetch=fetch).id == run.id
    assert len(sent) == 1  # same inputs: never paid for twice
    built = portfolio.build()
    [m] = built["callMeta"]
    assert m["state"] == "Ready" and m["brief"]["thirty"][0].startswith("The client is waiting")
    assert m["host"] == "Ana Reyes" and m["facts"]["owed"]["overdue"] == 0 and m["versions"][0]["by"] == "Automatic"


def test_a_brief_that_fails_its_core_checks_is_repaired_once_then_rejected(world, live):
    _snapshot()
    bad = {**BRIEF, "goal": "Hit 300 inquiries next month"}
    sent = []
    client = httpx.Client(transport=httpx.MockTransport(lambda r: sent.append(1) or httpx.Response(200, json=answer(bad))))
    runner.run("call_brief", str(world["call"]), client=client, fetch=lambda m: {"authored": ""})
    assert len(sent) == 2  # the answer and one repair
    with transaction() as s:
        [row] = briefs.history(s, world["call"])
        assert (row.outcome, row.is_current, row.output) == ("rejected", False, None)
        assert row.checks["core_failed"] == ["goal"] and row.checks["content_repaired"]
        assert float(s.scalar(select(func.sum(AiRun.cost_usd)))) == pytest.approx(0.06)


def test_the_scheduler_builds_once_and_rebuilds_only_on_changes(world):
    _snapshot()
    with transaction() as s:
        [(rid, trigger, fp)] = schedule.due(s, NOW)
        assert (rid, trigger) == (str(world["call"]), "first")
        assert schedule.due(s, world["start"] - timedelta(hours=30)) == []  # outside the 24 h lead
        call = registry.get(s, world["call"])
        p = pack.build(s, call, data=data(), now=NOW, read_bodies=False)
        briefs.save(s, p, output=BRIEF, checks={}, ai_run_id=None, trigger="first", built_by="auto")
        s.execute(CallBrief.__table__.update().values(built_at=NOW - timedelta(days=1)))
        near = world["start"] - timedelta(minutes=90)
        assert schedule.due(s, near) == []  # nothing changed
        gmail, scope = world["gmail"]
    with transaction() as s:
        from backend.models.db import Business
        _record(s, gmail, scope, "gmail_message", NOW - timedelta(hours=1),
                {"from": CLIENT, "subject": "One more thing", "thread_id": "t3"}, s.get(Business, world["business"]))
    with transaction() as s:
        [(_, trigger, _)] = schedule.due(s, world["start"] - timedelta(minutes=90))
        assert trigger == "final"
        assert "1 new client email" in briefs.reasons(briefs.current(s, world["call"]).inputs,
                                                     pack.build(s, registry.get(s, world["call"]), data=data(), read_bodies=False).inputs)


# ---- routes --------------------------------------------------------------------------------------------------

def test_routes_correct_a_call_and_edit_a_skill(world):
    from backend.app import app
    api = TestClient(app)
    assert api.put(f"/api/v1/calls/{world['call_id']}/override", json={"call_type": "creative", "viewer": "Ana"}).status_code == 200
    assert api.put(f"/api/v1/calls/{world['call_id']}/override", json={"call_type": "nope"}).status_code == 400
    assert api.put("/api/v1/calls/cal-zz/override", json={}).status_code == 404
    assert api.post(f"/api/v1/calls/{world['call_id']}/briefs", json={"instructions": "focus on leads"}).status_code == 409  # AI off
    text = skill_files.seed_files()["creative"].replace("List exactly", "Show exactly")
    assert api.post("/api/v1/call-skills/creative", json={"text": text, "viewer": "Ana"}).json()["version"] == 2
    assert api.post("/api/v1/call-skills/creative", json={"text": text.replace("## Guidance", "## X")}).status_code == 422
    assert [v["version"] for v in api.get("/api/v1/call-skills/creative/versions").json()["versions"]] == [2, 1]


# ---- ad platforms --------------------------------------------------------------------------------------------

def test_google_ads_lists_client_accounts_and_reads_daily_campaigns(monkeypatch):
    monkeypatch.setattr(google_ads, "_access_token", lambda force=False: "tok")
    for k, v in (("google_ads_developer_token", "dev"), ("google_ads_login_customer_id", "1112223333")):
        monkeypatch.setattr(get_settings(), k, v)
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append((request.url.path, request.headers.get("login-customer-id"), request.method))
        if "customer_client" in body["query"]:
            return httpx.Response(200, json={"results": [
                {"customerClient": {"id": "1112223333", "manager": True}},
                {"customerClient": {"id": "4445556666", "descriptiveName": "Venue One Ads", "currencyCode": "USD", "status": "ENABLED"}}]})
        return httpx.Response(200, json={"results": [{"campaign": {"id": "9", "name": "Search", "advertisingChannelType": "SEARCH"},
                                                      "segments": {"date": "2026-11-10"},
                                                      "metrics": {"costMicros": "12500000", "impressions": "400", "clicks": "20",
                                                                  "conversions": 2.0, "searchBudgetLostImpressionShare": 0.42}}]})
    g = google_ads.GoogleAds(transport=httpx.MockTransport(handler))
    assert [a["account_id"] for a in g.accounts()] == ["4445556666"]
    [row] = g.daily("4445556666", date(2026, 11, 1), date(2026, 11, 11))
    assert (row["spend"], row["conversions"], row["channel"], row["extra"]["budget_lost_is"]) == (12.5, 2.0, "Google Search", 0.42)
    assert all(m == "POST" and h == "1112223333" and p.endswith("googleAds:search") for p, h, m in seen)  # search only


def test_meta_counts_leads_once_and_pages_by_cursor():
    assert meta.leads_from([{"action_type": "lead", "value": "3"}, {"action_type": "onsite_conversion.lead_grouped", "value": "3"}]) == 3
    assert meta.leads_from([{"action_type": "onsite_conversion.lead_grouped", "value": "2"},
                            {"action_type": "offsite_conversion.fb_pixel_lead", "value": "1"}]) == 3
    pages = iter([{"data": [{"account_id": "1", "name": "A", "account_status": 1}], "paging": {"next": "x", "cursors": {"after": "c1"}}},
                  {"data": [{"account_id": "2", "name": "B", "account_status": 2}], "paging": {}},
                  {"data": [], "paging": {}}])
    m = meta.Meta("tok", "WIA", transport=httpx.MockTransport(lambda r: httpx.Response(200, json=next(pages))))
    assert [(a["account_id"], a["status"]) for a in m.accounts("biz")] == [("1", "ACTIVE"), ("2", "DISABLED")]


def test_mapped_accounts_feed_the_ads_summary_and_unmapping_deletes_figures(world):
    today = NOW.date()
    with transaction() as s:
        acct = AdAccount(provider="google_ads", account_id="4445556666", name="Venue One Ads", currency="USD")
        s.add(acct)
        s.flush()
        assert ads.suggest_client(s, "Venue One - Google Ads") == "venue-one"
        ads.map_account(s, "google_ads", "4445556666", "venue-one", actor="t")
        acct.pulled_from = today - timedelta(days=90)
        for d, spend, conv in ((5, 100, 4), (40, 80, 2)):
            s.add(AdDaily(ad_account_id=acct.id, campaign_id="9", day=today - timedelta(days=d), campaign_name="Search",
                          channel="Google Search", spend=Decimal(spend), impressions=1000, clicks=50,
                          conversions=Decimal(conv), extra={}))
    with transaction() as s:
        summ = ads.summary(s, world["business"], today)
        google = next(p for p in summ["platforms"] if p["provider"] == "google_ads")
        assert google["state"] == "connected" and google["current"]["spend"] == 100 and google["current"]["cpl"] == 25
        assert google["previous"]["leads"] == 2
        call = registry.get(s, world["call"])
        f = facts.compute(s, call, data(), NOW)
        assert f["pulse"]["ads"]["value"] == "$100 spend" and "+100% vs prior 30" in f["pulse"]["ads"]["note"]
        ads.map_account(s, "google_ads", "4445556666", None, actor="t")
    with transaction() as s:
        assert s.scalar(select(func.count()).select_from(AdDaily)) == 0
