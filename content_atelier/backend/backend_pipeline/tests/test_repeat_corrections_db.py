"""L.B14: repeat corrections become rules. Gate feedback, card refresh feedback and brief refresh instructions join the learning
loop's inputs; a correction of the same kind given twice is one rule candidate in the review queue citing both. The 13 and
20 October subject-line notes, entered as feedback (anonymised), produce one candidate. No model call: the sorting is by
fixed patterns, and the loop runs in its rules mode."""
from __future__ import annotations

from datetime import UTC, date, datetime

from psycopg.types.json import Jsonb

from backend_pipeline.database import connect
from backend_pipeline.gates.decisions import record
from backend_pipeline.knowledge import mining, repeats
from backend_pipeline.repository import insert
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401

APPROVER = "approver@example.invalid"
# Her two subject-line notes, anonymised: 13 October on one pack's email, 20 October on another's.
OCT_13 = ("Revise the email subject line: a little bit more enticing, more about the problem than the process, "
          "something like 'When more inquiries aren't enough'")
OCT_20 = "That's probably not a subject line I would use: it narrates what a client did with her AI"


def refresh_run(conn, run_id, *, scope, refs, on):
    insert(conn, "pipeline_runs", {"run_id": run_id, "run_scope": scope, "trigger_type": "manual", "triggered_by": APPROVER,
                                   "input_refs": Jsonb(refs), "status": "completed"})
    conn.execute("UPDATE pipeline_runs SET created_at=%s WHERE run_id=%s", (on, run_id))


def rules(conn):
    return conn.execute("""SELECT key,status,body,source_detail FROM brand_kit_items WHERE kind='rule' AND key LIKE 'rule:repeat.%%'
        ORDER BY key""").fetchall()


def test_the_13_and_20_october_subject_notes_given_as_feedback_make_one_candidate(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as conn:
        # 13 October: a brief refresh's instructions on one pack's brief; 20 October: a Gate 2 note on another's brief.
        refresh_run(conn, "brief_run_oct13", scope="brief", on=datetime(2026, 10, 13, 17, tzinfo=UTC),
                    refs={"revision_of": "brief_pack_a", "instructions": OCT_13, "queued_by": APPROVER})
        decision = record(conn, item_kind="brief", item_id="brief_pack_b", week_id=None, disposition="reject", action="gate_two_reject",
                          note=OCT_20, actor=APPROVER, author="Whitney Hodges")
        conn.execute("UPDATE decisions SET created_at=%s WHERE decision_id=%s", (datetime(2026, 10, 20, 16, tzinfo=UTC), decision))
        # Unrelated feedback given once: no candidate.
        refresh_run(conn, "card_refresh_1", scope="card_refresh", on=datetime(2026, 10, 20, 15, tzinfo=UTC),
                    refs={"angle_id": "angle_x", "feedback": "Lead with the venue owner's decision, not the platform", "author": "Whitney Hodges"})
        result = mining.run(conn, since=date(2026, 10, 18), until=date(2026, 10, 24))
        found = rules(conn)
        assert len(found) == 1 and result["repeat_corrections"]["rules"] == 1 and result["candidates"]["rule"] >= 1
        rule = found[0]
        assert rule["status"] == "candidate" and rule["key"].startswith("rule:repeat.subject_line.")
        assert rule["body"]["category"] == "voice" and "subject lines" in rule["body"]["statement"].lower()
        detail = rule["source_detail"]
        assert detail["feedback"] == sorted([f"decision:{decision}", "revise:brief_run_oct13"])
        assert detail["dates"] == ["2026-10-13", "2026-10-20"] and detail["sources"] == ["brief_revise", "gate_decision"]
        assert OCT_13 not in rule["body"]["statement"], "the rule is stated in general terms, never the reviewer's words"
        # Mined again, or in a later window, nothing is proposed twice.
        assert mining.run(conn, since=date(2026, 10, 18), until=date(2026, 10, 24))["repeat_corrections"]["rules"] == 0
        assert mining.run(conn, since=date(2026, 10, 25), until=date(2026, 10, 31))["repeat_corrections"]["rules"] == 0
        assert len(rules(conn)) == 1


def test_a_correction_given_once_or_outside_the_window_is_not_a_rule(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as conn:
        refresh_run(conn, "card_refresh_a", scope="card_refresh", on=datetime(2026, 10, 20, 15, tzinfo=UTC),
                    refs={"angle_id": "angle_a", "feedback": "Slide one is so ambiguous; tie the title in", "author": "Whitney Hodges"})
        assert mining.run(conn, since=date(2026, 10, 18), until=date(2026, 10, 24))["repeat_corrections"]["rules"] == 0
        # The same kind again, but both before the mined window: the pattern belongs to an earlier pass.
        refresh_run(conn, "card_refresh_b", scope="card_refresh", on=datetime(2026, 10, 21, 15, tzinfo=UTC),
                    refs={"angle_id": "angle_b", "feedback": "Punchier slide 1, please", "author": "Whitney Hodges"})
        assert repeats.run(conn, since=date(2026, 10, 25), until=date(2026, 10, 31), support=date(2026, 10, 4))["rules"] == 0
        made = repeats.run(conn, since=date(2026, 10, 18), until=date(2026, 10, 24), support=date(2026, 9, 27))
        assert made["rules"] == 1 and made["proposed"][0]["kind"] == "slide_one"


def test_the_kinds_are_fixed_patterns():
    assert repeats.kind_of("The subject line sucks") == "subject_line"
    assert repeats.kind_of("slide 1 is so ambiguous") == "slide_one"
    assert repeats.kind_of("Make the cover about ads") == "specific"
    assert repeats.kind_of("An audience not in the program won't know office hours") == "insider_term"
    assert repeats.kind_of("A little more casual, a little less polished") == "register"
    assert repeats.kind_of("It reads like a how-to") == "how_to"
    assert repeats.kind_of("Lovely work") is None
    assert repeats.independent([{"item": "a", "on": date(2026, 10, 13)}, {"item": "a", "on": date(2026, 10, 20)}])
    assert not repeats.independent([{"item": "a", "on": date(2026, 10, 13)}, {"item": "a", "on": date(2026, 10, 13)}])


def test_two_notes_on_one_card_and_its_refreshed_version_the_same_day_are_one_correction(platform_url):  # noqa: F811
    """N1 shakedown: a card was refreshed with feedback, and its refreshed version (a new angle id) was refreshed again the
    same day with similar words; the two were proposed as a correction given twice."""
    empty(platform_url)
    with connect(platform_url) as conn:
        insert(conn, "weeks", {"week_id": "week_2026-10-19", "week_start": date(2026, 10, 19), "week_end": date(2026, 10, 25)})
        refresh_run(conn, "run_cards", scope="weekly_angles", on=datetime(2026, 10, 20, 9, tzinfo=UTC), refs={})
        for angle, before in (("angle_v1", None), ("angle_v2", "angle_v1")):
            insert(conn, "content_angles", {"angle_id": angle, "run_id": "run_cards", "week_id": "week_2026-10-19",
                                            "content_body": Jsonb({"card": {"title": "Landing pages"}}), "supersedes_id": before,
                                            "content_hash": f"hash_{angle}", "first_generated_at": datetime(2026, 10, 20, 9, tzinfo=UTC)})
        for run, angle, text in (("card_refresh_1", "angle_v1", "Make the point about WIA's standard for landing pages"),
                                 ("card_refresh_2", "angle_v2", "Name the landing page standard WIA holds itself to")):
            refresh_run(conn, run, scope="card_refresh", on=datetime(2026, 10, 21, 10, tzinfo=UTC),
                        refs={"angle_id": angle, "feedback": text, "author": "Whitney Hodges"})
        records = repeats.feedback(conn, date(2026, 10, 18), date(2026, 10, 24))
        assert {r["lineage"] for r in records} == {"angle:angle_v1"}
        assert repeats.run(conn, since=date(2026, 10, 18), until=date(2026, 10, 24), support=date(2026, 9, 27))["rules"] == 0
