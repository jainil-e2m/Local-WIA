"""X.2 and NP.X4 end to end on the migrated database: the weekly tone loop. A tone request Whitney enters in the app, and a
correction given twice (the learning loop's candidate, as `knowledge/mining.py` writes it from Gate 2 or pack edits, L.B14,
NP.B13) reach one compiled knowledge-base version. It is an identity change, so it is approved pending its benchmark, and it
becomes active only when the result behind it is recorded: the release record, naming the agent's reading of the change
on the last live week (recorded as delegated) when no benchmark run is funded (plan M5, X.2). Synthetic data only (R48)."""
from __future__ import annotations

from backend_pipeline.knowledge import compiler, items, review
from backend_pipeline.knowledge_base import load_published
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_context_compile_db import ON, OWNER, ROOT, SETTINGS, WHITNEY, conn  # noqa: F401 (fixture)

REQUEST = "Never open an email subject line with a question about the reader's numbers."
REPEATED = "Lead a carousel's first slide with the reader's problem, not with what the client did."
READING = "research/n5-2026-10/tone-releases/example.md"


def test_a_tone_request_and_a_repeated_correction_reach_an_active_version_with_its_release_record(conn):  # noqa: F811
    base = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    compiler.approve(conn, SETTINGS, base, WHITNEY, note="The version in force")
    compiler.record_benchmark(conn, SETTINGS, base, WHITNEY, passed=True, result_ref="baseline", note="")

    # 1. Whitney's tone request, entered in the app: confirmed on entry, with its reason and author.
    request = review.enter(conn, SETTINGS, WHITNEY, kind="rule", name="Subject lines without number questions",
                           body={"statement": REQUEST, "level": "flag", "scope": "brief", "category": "voice"},
                           reason="Tone request, week of 26 October")
    assert request["status"] == "confirmed" and request["decision_id"]

    # 2. A correction given twice: the learning loop's candidate, which a reviewer accepts with its category.
    candidate, _ = items.add_item(conn, kind="rule", key=items.key_for("rule", "Carousel slide one leads with the problem"),
                                  body={"statement": REPEATED, "level": "flag", "scope": "brief", "category": "voice"},
                                  status="candidate", source_kind="brief_edit", source_ref="edits:voice:synthetic", author="model",
                                  created_by="context_mining", model_written=True,
                                  source_detail={"edits": ["pack_a:carousel", "pack_b:carousel"], "briefs": ["brief_a", "brief_b"]})
    shown = items.get_item(conn, candidate)
    accepted = review.decide(conn, SETTINGS, candidate, shown["hash"], "accept", WHITNEY, reason="She corrected this twice")
    assert accepted["status"] == "confirmed"

    # 3. One compiled version carries both; an identity change waits for the result behind it.
    compiled = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)
    assert compiled["changes"]["rejection_rules"] == "identity"
    version = compiled["version"]
    approved = compiler.approve(conn, SETTINGS, version, WHITNEY, note="The week's tone requests and repeated corrections")
    assert approved["state"] == "approved_pending_benchmark" and compiler.active_version(conn) == base

    # 4. The release: the agent's reading, named, makes it active; the version's record keeps it.
    released = compiler.record_benchmark(conn, SETTINGS, version, WHITNEY, passed=True, result_ref=READING,
                                         note="The agent's reading of the change on the last live week, replayed from saved "
                                              "inputs; delegated (D12). No benchmark run was funded")
    assert released["state"] == "active" and compiler.active_version(conn) == version
    text = load_published(conn, version).document("rejection_rules").text
    assert REQUEST in text and REPEATED in text
    listed = {v["version"]: v for v in compiler.versions(conn)}
    assert listed[version]["state"] == "active" and listed[version]["benchmark"]["result"] == READING, "the release record"
    assert listed[version]["benchmark"]["recorded_by"] == WHITNEY and "delegated" in listed[version]["benchmark"]["note"]
    actions = [r["action"] for r in conn.execute("SELECT action FROM decisions WHERE item_kind='brand_kit_version' AND item_id=%s "
                                                 "ORDER BY created_at", (version,)).fetchall()]
    assert actions == ["kb_approve", "kb_benchmark"], "the approval and the release are decision rows"


def test_with_the_benchmark_switched_off_the_approvers_approval_releases_the_tone_change(conn):  # noqa: F811
    """Production (the owner, 25 October 2026): no paid benchmark and no developer in the weekly loop. WIA's approver
    approves the week's tone change and it is in force at once, its record saying it was released without a benchmark."""
    from backend_pipeline.settings_store import set_value
    base = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)["version"]
    compiler.approve(conn, SETTINGS, base, WHITNEY, note="The version in force")
    compiler.record_benchmark(conn, SETTINGS, base, WHITNEY, passed=True, result_ref="baseline", note="")
    set_value(conn, "context.release.benchmark_required", False, OWNER)
    request = review.enter(conn, SETTINGS, WHITNEY, kind="rule", name="Subject lines without number questions",
                           body={"statement": REQUEST, "level": "flag", "scope": "brief", "category": "voice"},
                           reason="Tone request, week of 1 November")
    assert request["status"] == "confirmed"
    compiled = compiler.compile_version(conn, on=ON, actor=OWNER, root=ROOT)
    assert compiled["changes"]["rejection_rules"] == "identity"
    approved = compiler.approve(conn, SETTINGS, compiled["version"], WHITNEY, note="The week's tone request")
    assert approved["state"] == "active" and approved["pending_benchmark"] == []
    assert compiler.active_version(conn) == compiled["version"]
    assert REQUEST in load_published(conn, compiled["version"]).document("rejection_rules").text
    listed = {v["version"]: v for v in compiler.versions(conn)}
    assert listed[compiled["version"]]["state"] == "active"
