"""7.X2 on a migrated database: the week's success measures (main plan 4.5, content-packs plan 4.6) for a synthetic week of
cards, Gate 1 and Gate 2 decisions, briefs, packs, published pieces and model calls, with WIA's own rows and delegated rows
counted apart and only WIA's toward the bar; the week before is read for the two-consecutive-weeks thresholds. Rows are
written directly (the services have their own tests); invented text only (R48)."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from backend_pipeline import storage_cli, week_measures
from backend_pipeline.gates import rubric
from backend_pipeline.gates.decisions import record
from backend_pipeline.repository import insert
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)

PREVIOUS, WEEK = "week_2026-06-01", "week_2026-06-08"
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)


def run(conn, week, run_id):
    insert(conn, "pipeline_runs", {"run_id": run_id, "week_id": week, "run_scope": "weekly_angles", "status": "completed",
                                   "trigger_type": "manual", "input_refs": {}})


def card(conn, week, angle_id, rank, *, supersedes=None, status="candidate", **body):
    insert(conn, "content_angles", {"angle_id": angle_id, "week_id": week, "run_id": f"run_{week}", "supersedes_id": supersedes,
                                    "content_body": {"card": {"rank": rank, "title": f"Idea {rank}", "point": f"Point {rank}"}, **body},
                                    "content_hash": "hash_" + angle_id, "first_generated_at": NOW, "selection_status": status})


# Who is WIA's reviewer when a decision is recorded: the approver; the editor acts under delegation.
REVIEWERS = SimpleNamespace(wia_reviewers=(APPROVER,))


def decide(conn, week, item_id, disposition, actor, *, kind="angle", ratings=None, **extra):
    action = {"angle": "gate_one_", "brief": "gate_two_"}[kind] + disposition
    return record(conn, item_kind=kind, item_id=item_id, week_id=week, disposition=disposition, action=action, actor=actor,
                  author=actor, settings=REVIEWERS, rubric_ratings=rubric.ratings(ratings) if ratings else None, **extra)


def brief(conn, week, brief_id, angle_id, point, *, supersedes=None, approved_by=None, editor=None, perspective="We read the reply first."):
    digest = "hash_" + brief_id
    insert(conn, "content_briefs", {
        "brief_id": brief_id, "week_id": week, "angle_id": angle_id, "angle_input_hash": "a", "supersedes_id": supersedes,
        "content_body": {"schema_version": "brief_document_v4", "document": {"header": {}, "body": {"central_point": point, "wia_perspective": perspective}}},
        "selected_evidence": [], "prior_content_context": [], "content_hash": digest,
        "approval_status": "approved" if approved_by else "pending", "approved_hash": digest if approved_by else None,
        "approved_by": approved_by, "approved_at": NOW if approved_by else None, "updated_by": editor or "content-atelier"})


def pack(conn, week, pack_id, brief_id, run_id, *, supersedes=None, change=None, ready_by=None, finished=True):
    body = {"title": pack_id, "change": change or {"kind": "generated", "by": "content-pack step", "delegated": False, "pieces": [], "paths": []}}
    insert(conn, "content_packs", {
        "pack_id": pack_id, "week_id": week, "supersedes_id": supersedes, "title": pack_id, "manifest_hash": "m_" + pack_id,
        "approval_status": "approved" if ready_by else "pending", "approved_hash": "m_" + pack_id if ready_by else None,
        "approved_by": ready_by, "approved_at": NOW if ready_by else None, "contract_version": "content_pack_v2",
        "source_brief_id": brief_id, "production_run_id": run_id, "content_body": body if finished else None,
        "content_hash": "c_" + pack_id if finished else None})
    if ready_by:
        record(conn, item_kind="pack", item_id=pack_id, week_id=week, disposition="approve", action="pack_ready_to_publish",
               actor=ready_by, author=ready_by, details={"brief_id": brief_id}, settings=REVIEWERS)


def edit(by, delegated, piece, *paths):
    return {"kind": "edit", "by": by, "delegated": delegated, "pieces": [piece], "paths": list(paths)}


def published(conn, brief_id, piece, by):
    insert(conn, "published_content", {"content_id": f"published_{brief_id}_{piece}", "published_on": NOW.date(), "channel": "email",
                                       "title": "A published piece", "text": "We read the reply first.", "status": "confirmed",
                                       "source_kind": "approved_brief", "source_ref": f"pack:{brief_id}:{piece}", "brief_id": brief_id,
                                       "created_by": by})


def llm(conn, llm_run_id, run_id, usd):
    insert(conn, "llm_runs", {"llm_run_id": llm_run_id, "stage": "pack_finish", "model": "synthetic", "routing_policy": "synthetic",
                              "request_fingerprint": llm_run_id, "cost_usd": usd, "status": "succeeded", "details": {"run_id": run_id}})


ALL_FOURS = dict.fromkeys(rubric.KEYS, 4)


@pytest.fixture
def week(platform_setup):  # noqa: F811
    """The decisions keep the label they were recorded with; brief edits and published pieces are read against today's
    reviewers, the same approver."""
    repo, _, _ = platform_setup
    repo.settings.wia_reviewers = REVIEWERS.wia_reviewers
    with repo.connection() as conn:
        for w in (PREVIOUS, WEEK):
            run(conn, w, f"run_{w}")
        # The slate: six cards ranked 1 to 6, a revived considered idea and a suppressed duplicate.
        for n in range(1, 7):
            card(conn, WEEK, f"c{n}", n)
        card(conn, WEEK, "c7", 7, revived_from={"run_id": "run_x", "index": 0})
        card(conn, WEEK, "c8", 8, status="suppressed")
        decide(conn, WEEK, "c1", "develop", APPROVER, ratings=ALL_FOURS)
        decide(conn, WEEK, "c2", "skip", EDITOR, reason_code="timing", ratings=dict.fromkeys(rubric.KEYS, 2))
        card(conn, WEEK, "c3b", 3, supersedes="c3")
        decide(conn, WEEK, "c3", "reframe", APPROVER, reason_code="voice", reframe={"title": "Idea 3, reframed"},
               central_point_kept=True, resulting_item_id="c3b")
        decide(conn, WEEK, "c3b", "develop", APPROVER)
        card(conn, WEEK, "c4b", 4, supersedes="c4")
        decide(conn, WEEK, "c4", "reframe", APPROVER, reason_code="positioning", reframe={"point": "Another point"},
               central_point_kept=False, resulting_item_id="c4b")
        decide(conn, WEEK, "c4b", "develop", EDITOR)
        decide(conn, WEEK, "c5", "develop", APPROVER, ratings={**ALL_FOURS, "wia_is_the_subject": 3})
        decide(conn, WEEK, "c6", "skip", APPROVER, reason_code="duplicate")
        decide(conn, WEEK, "c7", "develop", APPROVER)
        # Briefs: b1 edited at Gate 2 by WIA but its point kept; b3 kept; b4 approved under delegation; b5's point rewritten.
        brief(conn, WEEK, "b1a", "c1", "Point 1")
        brief(conn, WEEK, "b1", "c1", "Point 1", supersedes="b1a", approved_by=APPROVER, editor=APPROVER, perspective="We read every reply first.")
        brief(conn, WEEK, "b3", "c3b", "Point 3", approved_by=APPROVER)
        brief(conn, WEEK, "b4", "c4b", "Another point", approved_by=EDITOR)
        brief(conn, WEEK, "b5a", "c5", "Point 5")
        brief(conn, WEEK, "b5", "c5", "Point 5, rewritten at Gate 2", supersedes="b5a", approved_by=APPROVER, editor=EDITOR)
        decide(conn, WEEK, "b1", "approve", APPROVER, kind="brief", ratings=dict.fromkeys(rubric.KEYS, 5))
        decide(conn, WEEK, "b3", "approve", APPROVER, kind="brief")
        decide(conn, WEEK, "b4", "approve", EDITOR, kind="brief")
        decide(conn, WEEK, "b5", "approve", APPROVER, kind="brief")
        # Packs: p1 edited by WIA on two lines and marked ready by WIA (light); p3 edited on four lines under delegation and
        # marked ready by WIA (not light); p4 marked ready under delegation; p5 in review.
        pack(conn, WEEK, "p1a", "b1", "run_p1")
        pack(conn, WEEK, "p1", "b1", "run_p1", supersedes="p1a", change=edit(APPROVER, False, "email", "subject_options[0]", "preview"),
             ready_by=APPROVER)
        pack(conn, WEEK, "p3a", "b3", "run_p3")
        pack(conn, WEEK, "p3", "b3", "run_p3", supersedes="p3a", change=edit(EDITOR, True, "reel_1", "script", "cover_text", "on_screen_hook",
                                                                              "caption.hook"), ready_by=APPROVER)
        pack(conn, WEEK, "p4", "b4", "run_p4", ready_by=EDITOR)
        pack(conn, WEEK, "p5", "b5", "run_p5")
        published(conn, "b1", "email", APPROVER)
        published(conn, "b4", "reel_1", EDITOR)
        llm(conn, "llm_1", "run_p1", 0.30)
        llm(conn, "llm_2", "run_p1", 0.20)
        llm(conn, "llm_3", "run_p3", 0.40)
        llm(conn, "llm_other", "run_elsewhere", 9.99)
        # The week before: one pack, ready by WIA, published by WIA, at USD 0.50.
        card(conn, PREVIOUS, "q1", 1)
        decide(conn, PREVIOUS, "q1", "develop", APPROVER)
        brief(conn, PREVIOUS, "bq1", "q1", "Point q", approved_by=APPROVER)
        decide(conn, PREVIOUS, "bq1", "approve", APPROVER, kind="brief")
        pack(conn, PREVIOUS, "pq1", "bq1", "run_q1", ready_by=APPROVER)
        published(conn, "bq1", "carousel", APPROVER)
        llm(conn, "llm_q", "run_q1", 0.50)
    return repo


def by(result, measure, column):
    return next(r for r in result["thresholds"] if r["measure"].startswith(measure) and r["column"] == column)


def test_the_week_s_measures_count_wia_s_own_rows_apart_from_delegated_ones(week):
    result = week_measures.measures(week, WEEK)
    cards = result["cards"]
    assert cards["slate"] == 6 and cards["top_five"] == 5, "the revived idea and the suppressed duplicate are not in the slate"
    assert cards["developed_or_reframed_keeping_the_point"] == {"wia": 3, "delegated": 1, "all": 4}
    assert cards["top_five_developed_or_reframed_keeping_the_point"] == {"wia": 3, "delegated": 1, "all": 4}
    assert cards["top_three_skipped"] == {"wia": False, "delegated": True, "all": True}
    rated = result["rubric"]
    assert rated["cards"]["wia"]["count"] == 2 and rated["cards"]["wia"]["overall"] == 3.9
    assert rated["cards"]["wia"]["criteria"]["wia_is_the_subject"] == 3.5
    assert rated["cards"]["delegated"]["count"] == 1 and rated["cards"]["delegated"]["overall"] == 2.0
    assert rated["briefs"]["wia"]["count"] == 1 and rated["briefs"]["delegated"]["count"] == 0
    assert rated["cards_and_briefs"]["wia"]["overall"] == round((4 + 3.8 + 5) / 3, 2)
    briefs = result["briefs"]
    assert briefs["approved"] == {"wia": 3, "delegated": 1, "all": 4}
    assert briefs["approved_without_rewriting_the_central_point"] == {"wia": 2, "delegated": 1, "all": 3}
    assert briefs["approved_without_rewriting_the_central_point_on_cards_wia_chose"] == 2
    edits = result["gate_two_edits"]
    assert edits["edits"] == {"wia": 1, "delegated": 1, "all": 2}
    # WIA reworded a line (voice); the delegated rewrite of b5's point added a figure ("Gate 2"), which L.B6 reads as accuracy.
    assert edits["by_category"]["wia"]["voice"] == 1 and edits["by_category"]["delegated"]["accuracy"] == 1
    packs = result["packs"]
    assert packs["packs"] == 4 and packs["finished"] == 4
    assert packs["ready"] == {"wia": 2, "delegated": 1, "all": 3}
    assert packs["ready_with_light_edits_or_none"] == {"wia": 1, "delegated": 1, "all": 2}
    assert packs["lines_edited_by_a_person"] == {"wia": 2, "delegated": 4, "all": 6}
    assert packs["pieces_published"] == {"wia": 1, "delegated": 1, "all": 2}
    assert packs["cost"] == {"model_calls": 3, "total_usd": 0.9, "per_pack_usd": 0.225}
    assert str(week_measures.LIGHT_EDITS) in packs["light_edits_rule"]


def test_each_threshold_is_judged_on_wia_s_rows_and_the_done_column_on_two_consecutive_weeks(week):
    result = week_measures.measures(week, WEEK)
    assert result["previous_week_id"] == PREVIOUS
    assert by(result, "Cards", "first live round")["met"] is True, "three of six, all WIA's"
    done = by(result, "Cards", "done")
    assert done["this_week"] is True and done["previous_week"] is False and done["met"] is False, "the delegated skip does not count"
    assert by(result, "Rubric", "first live round")["met"] is True
    assert by(result, "Rubric", "done")["met"] is False
    assert by(result, "Briefs", "first live round")["met"] is True
    assert by(result, "Briefs", "done")["met"] is False, "two on cards WIA chose; the delegated approval does not count"
    assert by(result, "Packs WIA marks ready", "first live week")["met"] is False, "one light pack of WIA's out of four"
    assert by(result, "Pieces published", "done")["met"] is True, "WIA published from the packs this week and the week before"
    assert by(result, "Cost per pack", "done")["met"] is True and by(result, "Cost per pack", "first live week")["met"] is True
    for row in result["thresholds"]:
        if row["measure"].startswith(("Factual", "Repeats", "First-touch", "Edits of a kind")):
            assert row["met"] is None and row["note"]
    assert len(result["thresholds"]) == len(week_measures.THRESHOLDS) == 22
    texts = {row["threshold"] for row in result["thresholds"]}
    assert "At least three of the top five on two consecutive live weeks, and no skip in the top three" in texts
    # The first week in the database has no week before it, so no Done threshold holds.
    first = week_measures.measures(week, PREVIOUS)
    assert first["previous_week_id"] is None and by(first, "Cost per pack", "done")["note"] == "no week before this one in the database"
    # A week with nothing in it yet reads as zeros, and no threshold is met by an empty week.
    with week.connection() as conn:
        insert(conn, "weeks", {"week_id": "week_2026-06-15", "week_start": datetime(2026, 6, 15).date(), "week_end": datetime(2026, 6, 21).date()})
    empty = week_measures.measures(week, "week_2026-06-15")
    assert empty["cards"]["slate"] == 0 and empty["packs"]["packs"] == 0 and empty["packs"]["cost"]["per_pack_usd"] is None
    assert empty["rubric"]["cards"]["wia"] == {"count": 0, "overall": None, "criteria": dict.fromkeys(rubric.KEYS)}
    assert not any(row["met"] for row in empty["thresholds"] if row["measure"] != "Pieces published from packs")


def test_the_command_prints_the_report_or_json_and_writes_nothing(week, monkeypatch, capsys):
    monkeypatch.setenv("ATELIER_DATABASE_URL", week.settings.database_url)
    monkeypatch.setenv("ATELIER_ARTIFACT_ROOT", str(week.settings.artifact_root))
    monkeypatch.setenv("ATELIER_WIA_REVIEWERS", APPROVER)
    with week.connection() as conn:
        before = {t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] for t in ("decisions", "calibration_labels", "content_packs")}
    storage_cli.main(["week-measures", "--week", WEEK, "--json"])
    printed = json.loads(capsys.readouterr().out)
    assert printed["packs"]["ready"] == {"wia": 2, "delegated": 1, "all": 3} and printed["week_id"] == WEEK
    storage_cli.main(["week-measures", "--week", WEEK])
    report = capsys.readouterr().out
    assert report.startswith(f"Week measures for {WEEK}") and "Only WIA's own rows count toward the bar" in report
    assert "- Developed, or reframed keeping the point: 3 WIA's own, 1 delegated (4 in all)" in report
    assert f"Rule: {week_measures.LIGHT_RULE}" in report
    assert '"At least half of a slate of at least four public cards": met' in report
    with week.connection() as conn:
        after = {t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] for t in ("decisions", "calibration_labels", "content_packs")}
    assert after == before, "read only"
    with pytest.raises(SystemExit, match="Week not found"):
        storage_cli.main(["week-measures", "--week", "week_2030-01-07"])


def test_editorial_monitoring_gives_the_cycle_its_accepted_share_skip_reasons_and_cost(week):
    """6.B13: per cycle, the accepted share against the bar, the reasons cards were skipped and what the cycle cost."""
    from backend_pipeline.week_measures import monitoring
    with week.connection() as conn:
        llm(conn, "llm_cycle", f"run_{WEEK}", 0.81)
    m = monitoring(week, WEEK)["monitoring"]
    assert m["bar"] == 0.5 and m["accepted_share"] == round(4 / 6, 2)  # c1, c3 (kept its point), c4b and c5 of six
    assert sorted(s["reason_code"] for s in m["skip_reasons"]) == ["duplicate", "timing"]
    assert m["cycle"]["run_id"] == f"run_{WEEK}" and m["cycle"]["cost_usd"] == 0.81 and m["cycle"]["started_from"] == "app"
    # The share counts against the bar once Gate 1 is done, by the alert's rule: at least four cards decided.
    assert m["cards_decided"] >= m["decided_at_least"] == week_measures.DECIDED_AT_LEAST and m["gate_1_done"] is True


def test_the_monitoring_answer_is_what_the_app_reads_and_gate_1_waits_for_four_decisions(week):
    """6.B13 in the app: the answer matches its published model (the app's generated type), and a week with fewer than four
    cards decided is not judged against the bar yet."""
    from backend_pipeline.api_models import WeekMeasures
    from backend_pipeline.week_measures import monitoring
    WeekMeasures.model_validate(monitoring(week, WEEK))
    with week.connection() as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-06-15','2026-06-15','2026-06-21')")
        run(conn, "week_2026-06-15", "run_week_2026-06-15")
        for n in range(1, 4):
            card(conn, "week_2026-06-15", f"w3_{n}", n)
        decide(conn, "week_2026-06-15", "w3_1", "develop", APPROVER)
    m = monitoring(week, "week_2026-06-15")["monitoring"]
    assert m["cards_decided"] == 1 and m["gate_1_done"] is False and m["accepted_share"] == round(1 / 3, 2)
