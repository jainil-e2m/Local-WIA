"""L.B6, L.B7 and L.B8 on a migrated database, over a synthetic week of WIA's own work.

L.B6's "done when" asks for a live week with at least five Gate decisions and three edited briefs; this week is
synthetic (two cycles, Gate 1 decisions written by the same service the card screen uses, and three edited,
approved v2 briefs), and the queue must hold candidates each citing its decisions, briefs or diffs."""
from __future__ import annotations

import copy
import json
from datetime import UTC, date, datetime, timedelta

import pytest
from psycopg.types.json import Jsonb

from backend_pipeline.angle_profiles import STRATEGIST_V5_PROFILE
from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.gates.decisions import record
from backend_pipeline.knowledge import items, mining, performance, review, staleness
from backend_pipeline.knowledge.assembly import assemble
from backend_pipeline.repository import insert
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.tests.brief_v2_fixtures import v2_body
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import W1, W2
from backend_pipeline.tests.test_seeds_db import SeedProvider
from backend_pipeline.tests.test_sql_storage import drain

ROOT = BACKEND_ROOT / "knowledge_base"
TODAY = date.today()
PACKET = {"approved_angle": {"title": "Why we ask about follow-up first", "core_perspective": "Follow-up shapes lead quality."},
          "evidence": [{"evidence_id": "ev_a", "speaker": "Carmen Cruickshank", "start_ms": 4000, "role": "anchor",
                        "excerpt": "Carmen Cruickshank: How do you reply to a new inquiry today?"}]}


def brief_row(brief_id, angle, week, body, *, supersedes=None, approved=False):
    envelope = {"schema_version": "brief_document_v2", "document": {"header": {"purpose": "WARM", "channels": ["email"]}, "body": body}}
    digest = "hash_" + brief_id
    return {"brief_id": brief_id, "week_id": week, "angle_id": angle, "angle_input_hash": "a", "supersedes_id": supersedes,
            "content_body": envelope, "selected_evidence": [], "prior_content_context": [], "content_hash": digest,
            "approval_status": "approved" if approved else "pending", "approved_hash": digest if approved else None,
            "approved_by": APPROVER if approved else None, "approved_at": datetime.now(UTC) if approved else None,
            "updated_by": "gisselle@example.invalid"}


@pytest.fixture
def week(platform_setup):  # noqa: F811
    repo, _, _ = platform_setup
    v5 = Settings(llm_payload_format="compact_weekly", extraction_profile="2026-10-13.weekly.v3", angle_prompt_profile=STRATEGIST_V5_PROFILE, knowledge_base_root=ROOT,
                  data_root=repo.settings.artifact_root / "legacy")
    worker = SQLWorker(repo.settings, v5, provider=SeedProvider())
    for w in (W1, W2):
        repo.submit(w, "synthetic", models=v5)
        drain(worker)
    with repo.connection() as conn:
        cards = conn.execute("SELECT angle_id,week_id FROM content_angles WHERE content_body ? 'card' ORDER BY week_id,angle_id").fetchall()
        assert len(cards) == 4
        a1, a2, a3, a4 = cards
        confirmed = items.add_item(conn, kind="process_step", key="process:accelerator-support",
                                   body={"process": "Accelerator", "what": "Support lasts 10 weeks after launch"},
                                   status="confirmed", source_kind="approver_entry", source_ref="p1", author="Whitney",
                                   created_by=APPROVER, reviewed_by=APPROVER)[0]
        common = {"actor": APPROVER, "author": "Whitney Hodges"}
        decisions = [
            record(conn, item_kind="angle", item_id=a1["angle_id"], week_id=a1["week_id"], disposition="develop", action="gate_one_develop", **common),
            record(conn, item_kind="angle", item_id=a2["angle_id"], week_id=a2["week_id"], disposition="hold", action="gate_one_hold",
                   reason_code="accuracy", note="It was 12 weeks, not 10 weeks of support", hold_until=TODAY + timedelta(days=7), **common),
            record(conn, item_kind="angle", item_id=a3["angle_id"], week_id=a3["week_id"], disposition="skip", action="gate_one_skip",
                   reason_code="voice", note="Sounds like AI: a chain of punchy one-liners", **common),
            record(conn, item_kind="angle", item_id=a4["angle_id"], week_id=a4["week_id"], disposition="skip", action="gate_one_skip",
                   reason_code="voice", note="Too many punchy one-liners again; it sounds like AI", actor=APPROVER, author="Gisselle Jiménez"),
            record(conn, item_kind="angle", item_id=a1["angle_id"], week_id=a1["week_id"], disposition="skip", action="gate_one_skip",
                   reason_code="timing", note="Robin Vale joined the team, and the ELEVATE retainer is now $1,597/month", **common),
        ]
        # Three edited briefs: two lose their em dashes (voice), one corrects a number (accuracy).
        for i, (angle, edit) in enumerate([(a1, "voice"), (a3, "voice"), (a4, "accuracy")]):
            first = v2_body(PACKET)
            first["wia_perspective"] = "We look at the follow-up first — always — before we change an ad."
            final = copy.deepcopy(first)
            if edit == "voice":
                final["wia_perspective"] = "We look at the follow-up first, before we change a single ad."
            else:
                final["claims"][0]["text"] = final["claims"][0].get("text", "x") + " in 45 days"
                final["wia_perspective"] = first["wia_perspective"]
            insert(conn, "content_briefs", brief_row(f"brief_{i}a", angle["angle_id"], angle["week_id"], first))
            insert(conn, "content_briefs", brief_row(f"brief_{i}b", angle["angle_id"], angle["week_id"], final, supersedes=f"brief_{i}a", approved=True))
        conn.execute("UPDATE content_briefs SET content_body=jsonb_set(content_body,'{document,body,wia_perspective}',%s) WHERE brief_id='brief_2b'",
                     (Jsonb("We look at the follow-up first — always — before we change an ad. Results came in 45 days."),))
        insert(conn, "published_content", {"content_id": "pc_final", "published_on": TODAY - timedelta(days=2), "channel": "email",
                                           "title": "Follow-up first", "text": "We look at the follow-up first.", "status": "confirmed",
                                           "source_kind": "approved_brief", "source_ref": "pc_final", "brief_id": "brief_0b",
                                           "created_by": APPROVER})
        insert(conn, "seeds", {"seed_id": "seed_always", "kind": "thought", "text": "Ads amplify what already works.",
                               "always_true": True, "author": "Whitney Hodges", "created_by": APPROVER})
    return repo, decisions, confirmed


def test_a_week_of_approved_work_fills_the_queue_with_cited_candidates(week):
    repo, decisions, confirmed = week
    with repo.connection() as conn:
        result = mining.run(conn, actor="context_mining")
        # Four reasons carry a code; timing says nothing about how WIA writes, so three are grouped.
        assert result["reasons_read"] == 3 and result["edits_read"] >= 3
        rows = conn.execute("SELECT * FROM brand_kit_items WHERE status='candidate' ORDER BY kind,key").fetchall()
    by_kind = {}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(r)
    assert all(r["source_kind"] in ("approved_card", "approved_brief", "published_piece", "gate_decision", "brief_edit", "seed")
               and r["source_detail"] for r in rows), "every candidate cites its source"

    # A recurring Gate 1 reason from two independent cards becomes one rule, citing both decisions and authors.
    learned = [r for r in by_kind["rule"] if r["source_kind"] == "gate_decision"]
    assert len(learned) == 1 and set(learned[0]["source_detail"]["decisions"]) == {decisions[2], decisions[3]}
    assert set(learned[0]["source_detail"]["authors"]) == {"Whitney Hodges", "Gisselle Jiménez"}
    assert learned[0]["model_written"] is False and learned[0]["body"]["level"] == "flag"
    # Edits at Gate 2 recurring across two briefs become a rule with example diffs; the single accuracy edit does not.
    edited = [r for r in by_kind["rule"] if r["source_kind"] == "brief_edit"]
    assert len(edited) == 1 and edited[0]["source_detail"]["category"] == "voice"
    assert set(edited[0]["source_detail"]["briefs"]) == {"brief_0b", "brief_1b"} and edited[0]["source_detail"]["diffs"]

    # The one-off correction corrects the fact it names (same key, so accepting it supersedes it); it is no rule.
    corrections = [r for r in rows if (r["source_detail"] or {}).get("corrects") == confirmed]
    assert len(corrections) == 1 and corrections[0]["key"] == "process:accelerator-support"
    assert "12 weeks" in corrections[0]["text"] and decisions[1] in corrections[0]["source_detail"]["decisions"]
    assert not any(decisions[1] in (r["source_detail"].get("decisions") or []) for r in by_kind["rule"])
    # New facts from decision notes: a price (internal) and a team member, each a candidate citing its decision.
    price = by_kind["price"][0]
    assert price["visibility"] == "internal" and price["body"]["amount"] == "$1,597/month"
    assert by_kind["roster_member"][0]["body"]["name"] == "Robin Vale"
    # Exemplars from the approved card, the approved briefs' sections and the published final; a belief from the seed.
    labels = {r["body"]["label"] for r in by_kind["exemplar"]}
    # A card or brief section the model drafted and WIA approved is model-written (R52); a published final is WIA's.
    drafted = [r for r in by_kind["exemplar"] if r["source_kind"] in ("approved_card", "approved_brief")]
    assert drafted and all(r["model_written"] and r["author"].startswith("model draft") for r in drafted)
    assert not any(r["model_written"] for r in by_kind["exemplar"] if r["source_kind"] == "published_piece")
    assert {"approved_card", "approved_brief_wia_perspective", "published_final"} <= labels
    assert by_kind["belief"][0]["source_detail"]["seed_id"] == "seed_always"
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM brand_kit_items WHERE source_kind<>'approver_entry' AND status<>'candidate'").fetchone()["n"] == 0, \
            "nothing confirms itself"
        before = conn.execute("SELECT count(*) n FROM brand_kit_items").fetchone()["n"]
        again = mining.run(conn, actor="context_mining")
        assert sum(again["candidates"].values()) == 0
        assert conn.execute("SELECT count(*) n FROM brand_kit_items").fetchone()["n"] == before


class Categoriser:
    def __init__(self):
        self.calls = []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls.append(stage)
        edits = json.loads(user)
        return {"edits": [{"index": e["index"], "category": "format"} for e in edits]}, {}


def test_a_different_family_model_categorises_edits(week):
    repo, _, _ = week
    provider = Categoriser()
    with repo.connection() as conn:
        with pytest.raises(ValueError, match="different family"):
            mining.run(conn, provider=provider, model="openai/gpt-6-luna", writer_model="openai/gpt-6.1-sol")
        conn.rollback()
    with repo.connection() as conn:
        result = mining.run(conn, provider=provider, model="anthropic/claude-sonnet-5.5", writer_model="openai/gpt-6.1-sol")
        assert provider.calls == ["context_mining"] and result["categorised_by"] == "anthropic/claude-sonnet-5.5"
        edited = conn.execute("SELECT source_detail FROM brand_kit_items WHERE source_kind='brief_edit'").fetchall()
        assert edited and all(r["source_detail"]["category"] == "format" for r in edited)


def test_performance_entry_import_and_the_situational_block(week):
    repo, _, _ = week
    settings = repo.settings
    with repo.connection() as conn:
        piece = performance.add_piece(conn, settings, APPROVER, published_on=TODAY - timedelta(days=5), channel="Instagram",
                                      title="The 59-lead carousel", brief_id="brief_0b")
        assert piece["angle_id"], "a piece linked to an approved brief also links its card"
        with pytest.raises(ValueError, match="approved brief"):
            performance.add_piece(conn, settings, APPROVER, published_on=TODAY, channel="email", title="x", brief_id="brief_0a")
        with pytest.raises(PermissionError):
            performance.enter(conn, settings, "viewer@example.invalid", piece["content_id"], on=TODAY, metric="saves", value="10")
        performance.enter(conn, settings, APPROVER, piece["content_id"], on=TODAY - timedelta(days=5), metric="saves", value="120")
        csv = ("date,channel,piece,metric,value\n"
               f"{(TODAY - timedelta(days=5)).isoformat()},Instagram,The 59-lead carousel,saves,120\n"
               f"{(TODAY - timedelta(days=3)).isoformat()},Instagram,A quiet Reel,saves,4\n")
        imported = performance.import_csv(conn, settings, APPROVER, csv)
        assert imported == {"entries_added": 1, "pieces_created": 1}, "a repeated row adds nothing; an unknown piece is recorded"
    kb = assemble("strategist", root=ROOT, connection=repo.connection)
    strong = kb.situational.split("### Strongest recent pieces")[1].split("###")[0]
    weak = kb.situational.split("### Weakest recent pieces")[1]
    assert "The 59-lead carousel" in strong and "A quiet Reel" in weak


def test_staleness_retires_expired_offers_and_warns_on_an_overdue_roster(week):
    repo, _, _ = week
    with repo.connection() as conn:
        offer = items.add_item(conn, kind="offer", key="offer:summer-promo", body={"name": "Summer promo", "description": "Three spots"},
                               status="confirmed", source_kind="approver_entry", source_ref="o1", author="Whitney", created_by=APPROVER,
                               reviewed_by=APPROVER, valid_to=TODAY - timedelta(days=1))[0]
        member = items.add_item(conn, kind="roster_member", key="roster:carmen", body={"name": "Carmen Cruickshank", "role": "Google Ads lead",
                                "state": "current"}, status="confirmed", source_kind="approver_entry", source_ref="r1",
                                author="Whitney", created_by=APPROVER, reviewed_by=APPROVER)[0]
        conn.execute("UPDATE brand_kit_items SET reviewed_at=now()-interval '45 days' WHERE item_id=%s", (member,))
    assert "Summer promo" not in assemble("strategist", root=ROOT, connection=repo.connection).document("offer_sheet").text
    with repo.connection() as conn:
        result = staleness.run(conn)
        assert result["retired"] == 1 and items.get_item(conn, offer)["status"] == "retired"
        assert conn.execute("SELECT action FROM decisions WHERE item_id=%s", (offer,)).fetchone()["action"] == "context_retire"
        assert any(w["kind"] == "roster_member" for w in result["warnings"])
    review_view = repo.review(W1, APPROVER)
    assert any("roster member" in w for w in review_view["context_warnings"]), "the cycle shows the warning"
    kb = assemble("strategist", root=ROOT, connection=repo.connection)
    assert any("roster member" in w for w in kb.refs()["context"]["warnings"]), "the run records it"
    assert "Summer promo" not in kb.document("offer_sheet").text


def test_review_of_a_mined_candidate_confirms_it(week):
    repo, _, _ = week
    settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,)})
    with repo.connection() as conn:
        mining.run(conn)
        roster = conn.execute("SELECT * FROM brand_kit_items WHERE kind='roster_member' AND status='candidate'").fetchone()
        done = review.decide(conn, settings, roster["item_id"], roster["hash"], "edit", APPROVER, reason="Robin joined in October",
                             changes={"body": {"name": "Robin Vale", "role": "Ads coordinator", "state": "current"}})
        assert done["status"] == "confirmed"
    assert any(r["name"] == "Robin Vale" for r in assemble("verifier", root=ROOT, connection=repo.connection).roster)


def test_the_scheduler_runs_staleness_daily_and_mining_weekly_once_each(week, monkeypatch):
    from backend_pipeline.knowledge import scheduler
    repo, _, _ = week
    monkeypatch.setenv("ATELIER_CONTEXT_NIGHTLY_HOUR", "3")
    # The next Monday after today: the fixture stamps its edits with the real clock, and mining reads the week before the
    # Monday, so a fixed date stops covering them once the calendar passes it (it did on 19 October 2026).
    today = datetime.now(UTC).date()
    monday = datetime.combine(today + timedelta(days=7 - today.weekday()), datetime.min.time(), UTC).replace(hour=4)
    first = scheduler.tick(repo.settings, Settings(), now=monday)
    assert set(first) == {"staleness", "mining"} and first["mining"]["categorised_by"] == "rules"
    assert scheduler.tick(repo.settings, Settings(), now=monday + timedelta(hours=1)) == {}, "a second pass the same day does nothing"
    tuesday = scheduler.tick(repo.settings, Settings(), now=monday + timedelta(days=1))
    assert set(tuesday) == {"staleness"}, "the learning loop runs once a week"
    assert scheduler.tick(repo.settings, Settings(), now=datetime(2026, 10, 21, 1, 0, tzinfo=UTC)) == {}, "nothing before the nightly hour"


def test_a_failed_scheduled_job_is_retried_and_a_refused_categoriser_falls_back_to_rules(week, monkeypatch):
    """L.B6, L.B8: a job that raises is recorded as failed and runs again on a later pass (at most three attempts);
    a live categoriser refused by its plan or route still mines the week, categorised by rules, and says why."""
    from backend_pipeline.knowledge import scheduler
    from backend_pipeline.llm.run_plans import RunPlanError
    repo, _, _ = week
    monkeypatch.setenv("ATELIER_CONTEXT_NIGHTLY_HOUR", "3")
    # The next Monday after today: the fixture stamps its edits with the real clock, and mining reads the week before the
    # Monday, so a fixed date stops covering them once the calendar passes it (it did on 19 October 2026).
    today = datetime.now(UTC).date()
    monday = datetime.combine(today + timedelta(days=7 - today.weekday()), datetime.min.time(), UTC).replace(hour=4)
    calls = []
    real = scheduler.staleness_now

    def flaky(storage, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database restarted")
        return real(storage, **kw)
    monkeypatch.setattr(scheduler, "staleness_now", flaky)
    monkeypatch.setenv("ATELIER_CONTEXT_MINING_LIVE", "true")
    models = Settings(openrouter_context_mining_model="anthropic/claude-sonnet-5.5")

    def refused(*a, **k):
        raise RunPlanError("A real-data model call needs an active run plan")
    monkeypatch.setattr(scheduler, "_provider", lambda m, s=None: type("P", (), {"json_call": refused})())
    first = scheduler.tick(repo.settings, models, now=monday)
    assert "staleness" in first["failed"] and first["mining"]["categorised_by"] == "rules"
    assert "active run plan" in first["mining"]["categoriser_unavailable"]
    with repo.connection() as conn:
        state = conn.execute("SELECT value FROM settings WHERE key=%s", (f"context.staleness.ran.{monday.date().isoformat()}",)).fetchone()["value"]
    assert state["state"] == "failed" and state["attempts"] == 1 and "database restarted" in state["error"]
    with repo.connection() as conn:
        # A failed job waits before its next attempt (jobs/periodic.RETRY_AFTER); the claim is aged past it.
        conn.execute("UPDATE settings SET updated_at=now()-interval '1 hour' WHERE key=%s",
                     (f"context.staleness.ran.{monday.date().isoformat()}",))
        conn.commit()
    again = scheduler.tick(repo.settings, models, now=monday + timedelta(hours=1))
    assert set(again) == {"staleness"}, "the failed job runs again; the finished one does not"
    assert scheduler.tick(repo.settings, models, now=monday + timedelta(hours=2)) == {}


def test_the_context_routes_for_versions_published_warnings_and_mining(week):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend_pipeline.storage_api import router
    repo, _, _ = week
    app = FastAPI()
    app.include_router(router(repo.settings.model_copy(update={"brief_approvers": (APPROVER,), "context_enabled": True})))
    client = TestClient(app)

    def call(method, path, body=None, email=APPROVER):
        headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}
        return client.request(method, "/storage" + path, json=body, headers=headers)
    piece = call("POST", "/context/published", {"published_on": TODAY.isoformat(), "channel": "email", "title": "Follow-up first",
                                                "brief_id": "brief_1b"})
    assert piece.status_code == 201, piece.text
    content_id = piece.json()["content_id"]
    assert call("POST", f"/context/published/{content_id}/performance", {"on": TODAY.isoformat(), "metric": "replies", "value": "14"}).json()["added"]
    assert call("POST", f"/context/published/{content_id}/link", {"brief_id": "brief_2b"}).json()["brief_id"] == "brief_2b"
    assert call("POST", "/context/published/import", {"csv": "date,channel\n"}).status_code == 409
    assert call("POST", "/context/mining", {}, email="viewer@example.invalid").status_code == 403
    mined = call("POST", "/context/mining", {})
    assert mined.status_code == 200 and mined.json()["candidates"]["rule"] >= 1
    assert call("GET", "/context/mining").json()["last"]["window"]["until"] == TODAY.isoformat()
    assert "warnings" in call("GET", "/context/warnings").json()
    compiled = call("POST", "/context/versions", {})
    assert compiled.status_code == 201 and compiled.json()["status"] in ("compiled", "unchanged")
    if compiled.json()["status"] == "compiled":
        version = compiled.json()["version"]
        assert call("GET", f"/context/versions/{version}/diff").json()["documents"]
        assert call("POST", f"/context/versions/{version}/approve", {"note": "ok"}).json()["state"] in ("active", "approved_pending_benchmark")
    assert call("GET", "/context/versions").status_code == 200
