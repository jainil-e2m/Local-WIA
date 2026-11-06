"""L.B4 on a migrated database: compiling twice gives identical hashes; approval records the approver; an identity
change waits for its benchmark; operating changes take effect on approval."""
from __future__ import annotations

import json
from datetime import date

import pytest

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.database import connect
from backend_pipeline.knowledge import compiler, items, review, seed
from backend_pipeline.knowledge_base import load_knowledge_base, load_published
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401

# The first compile after the seed runs against the file version the seed was taken from (version 2, archived once
# version 3 was compiled and exported from the reviewed store).
ROOT = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.v2"
ON = date(2026, 10, 20)
OWNER, WHITNEY = "gisselle@example.invalid", "whitney@example.invalid"
SETTINGS = StorageSettings(brief_approvers=(OWNER, WHITNEY), identity_approvers=(WHITNEY,))


@pytest.fixture
def conn(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver="owner@example.invalid")
        yield c


def test_compiling_twice_with_no_change_gives_identical_hashes(conn):
    first = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)
    second = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)
    assert first["status"] == "compiled" and second["status"] == "exists"
    assert first["version"] == second["version"] and first["documents"] == second["documents"]
    # The seed's confirmed roster, offer sheet and rules compile; drafts with no confirmed item carry over.
    assert first["changes"]["team_roster"] == "operating" and first["changes"]["rejection_rules"] == "identity"
    assert first["changes"]["content_strategy"] == "unchanged" and first["changes"]["exemplars"] == "unchanged"
    assert first["pending_candidates"]["exemplars"] > 0
    kb = load_published(conn, first["version"], stage="strategist")
    files = load_knowledge_base(ROOT, stage="strategist")
    assert kb.document("content_strategy").sha256 == files.document("content_strategy").sha256
    roster = kb.document("team_roster").text
    assert "Fallon Looney" in roster.split("## Former staff")[1] and "Matt" in roster
    rows = conn.execute("SELECT key,compiled_from,benchmark_state FROM brand_kit_docs WHERE version=%s", (first["version"],)).fetchall()
    compiled = {r["key"]: r for r in rows}
    assert compiled["team_roster"]["compiled_from"]["items"] and compiled["content_strategy"]["compiled_from"] is None
    assert compiled["rejection_rules"]["benchmark_state"] == "pending" and compiled["team_roster"]["benchmark_state"] == "not_required"


def test_internal_prices_never_enter_a_document(conn):
    items.add_item(conn, kind="price", key="price:elevate", body={"offer": "ELEVATE", "amount": "$1,497/month"},
                   status="confirmed", visibility="internal", source_kind="approver_entry", source_ref="p1",
                   author="Whitney", created_by=OWNER, reviewed_by=OWNER)
    items.add_item(conn, kind="price", key="price:audit", body={"offer": "Google Ads Audit", "amount": "normally $297"},
                   status="confirmed", visibility="public", source_kind="approver_entry", source_ref="p2",
                   author="Whitney", created_by=OWNER, reviewed_by=OWNER)
    version = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    sheet = load_published(conn, version).document("offer_sheet").text
    assert "$1,497" not in sheet and "normally $297" in sheet


def test_a_compiled_version_and_the_brief_exemplars_hold_week_6_out(conn):
    """E.B17: items stating the held-out Week 6 result, or the pieces built on it, never compile or reach a stage."""
    from backend_pipeline.knowledge import assembly, held_out

    def entry(kind, key, body, ref):
        return items.add_item(conn, kind=kind, key=key, body=body, status="confirmed", source_kind="approver_entry",
                              source_ref=ref, author="Whitney", created_by=OWNER, reviewed_by=OWNER,
                              **({"permission": "published"} if kind == "result" else {}))[0]
    week6 = entry("result", "result:venue", {"claim": "Venue: more than $22,000 on ad spend, then about $70,000 in bookings"}, "w6")
    caption = entry("exemplar", "exemplar:ex01", {"text": "You can't optimize what you can't measure.", "channel": "caption",
                                                  "published": True}, "w6b")
    other = entry("result", "result:planner", {"claim": "A planner's inquiries doubled in a quarter"}, "ok")
    version = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    kb = load_published(conn, version)
    register = kb.document("results_register").text
    assert "$22,000" not in register and "planner's inquiries doubled" in register
    assert not any(held_out.text_weeks(d.text) for d in kb.documents)
    rows = {r["key"]: r["compiled_from"] for r in conn.execute(
        "SELECT key,compiled_from FROM brand_kit_docs WHERE version=%s AND compiled_from IS NOT NULL", (version,))}
    assert {"id": week6, "key": "result:venue", "week": 6} in rows["results_register"]["withheld"]
    assert other in {i["id"] for i in rows["results_register"]["items"]}
    chosen = assembly._exemplars(conn, ON, ["caption"], None, 5, 4000)
    assert caption not in {r["item_id"] for r in chosen}


def test_approval_records_the_approver_and_identity_waits_for_its_benchmark(conn):
    version = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    with pytest.raises(PermissionError, match="identity approver"):
        compiler.approve(conn, SETTINGS, version, OWNER, note="ok")
    approved = compiler.approve(conn, SETTINGS, version, WHITNEY, note="Reviewed the diff")
    assert approved["state"] == "approved_pending_benchmark" and "rejection_rules" in approved["pending_benchmark"]
    assert compiler.active_version(conn) is None, "an identity change is not the default before its benchmark"
    approvers = {r["approver"] for r in conn.execute("SELECT approver FROM brand_kit_docs WHERE version=%s", (version,))}
    assert approvers == {WHITNEY}
    decision = conn.execute("SELECT * FROM decisions WHERE item_kind='brand_kit_version' AND item_id=%s", (version,)).fetchone()
    assert decision["actor"] == WHITNEY and decision["action"] == "kb_approve"
    listed = {v["version"]: v for v in compiler.versions(conn)}
    assert listed[version]["state"] == "approved_pending_benchmark"
    with pytest.raises(ValueError, match="already approved pending benchmark"):
        compiler.approve(conn, SETTINGS, version, WHITNEY, note="again")
    done = compiler.record_benchmark(conn, SETTINGS, version, WHITNEY, passed=True,
                                     result_ref="research/benchmark-v1/results/example.json", note="Smoke result held")
    assert done["state"] == "active" and compiler.active_version(conn) == version
    assert {r["benchmark_state"] for r in conn.execute("SELECT benchmark_state FROM brand_kit_docs WHERE version=%s AND key='rejection_rules'", (version,))} == {"passed"}
    diff = compiler.diff(conn, version)
    assert any(d["key"] == "team_roster" and d["diff"].startswith("---") for d in diff["documents"])


def test_an_operating_change_takes_effect_on_approval(conn):
    first = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    compiler.approve(conn, SETTINGS, first, WHITNEY, note="first")
    compiler.record_benchmark(conn, SETTINGS, first, WHITNEY, passed=True, result_ref="smoke", note="")
    review.enter(conn, SETTINGS, OWNER, kind="roster_member", name="New Hire", body={"name": "New Hire", "role": "Ads coordinator",
                                                                                   "state": "current"}, reason="Joined in October")
    second = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)
    assert second["changes"]["team_roster"] == "operating"
    assert all(c in ("unchanged", "operating") for c in second["changes"].values())
    assert compiler.approve(conn, SETTINGS, second["version"], OWNER, note="New hire")["state"] == "active"
    assert compiler.active_version(conn) == second["version"]
    assert "New Hire" in load_published(conn, second["version"]).document("team_roster").text
    assert compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["status"] == "unchanged"


def test_a_draft_can_be_discarded_but_an_active_approved_or_used_version_is_kept(conn):
    first = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    with pytest.raises(PermissionError):
        compiler.discard(conn, SETTINGS, first, "viewer@example.invalid")
    # A draft a run recorded is kept, so what that run read can be read again.
    conn.execute("""INSERT INTO pipeline_runs(run_id,run_scope,status,trigger_type,input_refs)
        VALUES ('run_kb_used','weekly_cycle','completed','manual',%s)""", (json.dumps({"knowledge_base": {"version": first}}),))
    with pytest.raises(ValueError, match="A run has used this version"):
        compiler.discard(conn, SETTINGS, first, OWNER)
    conn.execute("DELETE FROM pipeline_runs WHERE run_id='run_kb_used'")
    done = compiler.discard(conn, SETTINGS, first, OWNER)
    assert done["state"] == "discarded"
    assert first not in {v["version"] for v in compiler.versions(conn)}
    assert not conn.execute("SELECT 1 FROM brand_kit_docs WHERE version=%s", (first,)).fetchone()
    decision = conn.execute("SELECT * FROM decisions WHERE item_kind='brand_kit_version' AND item_id=%s", (first,)).fetchone()
    assert decision["action"] == "kb_discard" and decision["actor"] == OWNER
    with pytest.raises(LookupError):
        compiler.discard(conn, SETTINGS, first, OWNER)
    # Compiled again, approved and active: kept. Approved but waiting for its benchmark: kept as well.
    again = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)
    assert again["status"] == "compiled", "a discarded draft can be compiled again"
    compiler.approve(conn, SETTINGS, again["version"], WHITNEY, note="Reviewed")
    with pytest.raises(ValueError, match="approved"):
        compiler.discard(conn, SETTINGS, again["version"], WHITNEY)
    compiler.record_benchmark(conn, SETTINGS, again["version"], WHITNEY, passed=True, result_ref="smoke", note="")
    with pytest.raises(ValueError, match="in use"):
        compiler.discard(conn, SETTINGS, again["version"], WHITNEY)


def test_the_discard_route_answers_409_in_plain_words(platform_url):  # noqa: F811
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend_pipeline.storage_api import router
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver="owner@example.invalid")
        version = compiler.compile_version(c, on=ON, actor=OWNER, root=ROOT)["version"]
        compiler.approve(c, SETTINGS, version, WHITNEY, note="Reviewed")
    settings = SETTINGS.model_copy(update={"database_url": platform_url, "api_secret": "test-secret", "context_enabled": True})
    app = FastAPI()
    app.include_router(router(settings))
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": OWNER, "X-Atelier-Email": OWNER}
    refused = client.post(f"/storage/context/versions/{version}/discard", headers=headers)
    assert refused.status_code == 409 and refused.json()["detail"] == "This version has been approved, so it is kept"
    assert client.post("/storage/context/versions/kb-none/discard", headers=headers).status_code == 404


def test_the_verifier_receives_the_belief_statements(platform_url):  # noqa: F811
    """The card verifier checks the strategist's quotes of Whitney against her belief bank, so a compiled version gives
    the verifier that document even when the base version did not; a change of stages alone is a new version."""
    empty(platform_url)
    committed = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.c-0cb353e4"  # version 4, archived when version 5 replaced it
    assert "verifier" not in load_knowledge_base(committed).document("belief_statements").entry.stages
    with connect(platform_url) as c:
        result = compiler.compile_version(c, on=ON, actor=OWNER, root=committed)
        assert result["status"] == "compiled"
        assert {k for k, v in result["changes"].items() if v != "unchanged"} == {"belief_statements"}
        assert result["changes"]["belief_statements"] == "operating", "only the stages changed, not the text"
        kb = load_published(c, result["version"], stage="verifier")
        assert kb.document("belief_statements") is not None
        assert kb.document("belief_statements").text == load_knowledge_base(committed).document("belief_statements").text
        assert compiler.compile_version(c, on=ON, actor=OWNER, root=committed)["status"] == "exists"


def test_the_benchmark_can_evaluate_a_compiled_version_before_it_is_active(conn, platform_url, monkeypatch):  # noqa: F811
    """L.B4: an identity change's smoke result comes from the evaluation command run on that version."""
    from functools import partial

    from evaluation import run
    version = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    conn.commit()
    try:
        files_body, _ = run.request("strategist_v5", "week1")
    except FileNotFoundError:
        pytest.skip("Benchmark inputs are not checked out")
    monkeypatch.setitem(run.CONTEXT, "version", version)
    monkeypatch.setitem(run.CONTEXT, "connection", partial(connect, platform_url))
    body, _ = run.request("strategist_v5", "week1")
    system = body["messages"][0]["content"]
    assert f"version {version}" in system and system != files_body["messages"][0]["content"]
    assert compiler.active_version(conn) is None, "evaluating a version does not activate it"
