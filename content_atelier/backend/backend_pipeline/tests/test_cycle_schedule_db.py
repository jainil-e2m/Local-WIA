"""3.B11 (Phase N7) on a real database: the weekly cycle starts by itself at the scheduled time, over the seven days before
it, only from its first day and only when switched on; it collects the window, activates the collector once and starts the
cycle under the named approver's standing approval; a window with no call starts nothing; once the cycle has finished, the
week's review document is made and kept with the run. The Fathom API and the paid cycle are stubbed: no network, no model."""
from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime, timedelta

import pytest

from backend_pipeline.cycle import schedule
from backend_pipeline.settings_store import set_value
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixtures)

# Sunday 1 November 2026, 04:00 America/Chicago is 09:00 UTC (CDT ends at 02:00 that morning: CST, UTC-6, so 10:00 UTC).
FIRST = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    with repo.connection() as conn:
        set_value(conn, "cycle.schedule.enabled", True, APPROVER)
        set_value(conn, "cycle.schedule.first_day", "2026-11-01", APPROVER)
        set_value(conn, "cycle.schedule.actor", APPROVER, APPROVER)
    return repo, models, tmp_path


def test_the_scheduled_time_is_sunday_four_in_the_morning_chicago_and_the_window_is_the_week_before():
    s = {"timezone": "America/Chicago", "weekday": 6, "hour": 4}
    assert schedule.scheduled_end(FIRST, s) == FIRST
    assert schedule.scheduled_end(FIRST - timedelta(minutes=1), s) == datetime(2026, 10, 25, 9, 0, tzinfo=UTC)  # CDT a week before
    assert schedule.scheduled_end(FIRST + timedelta(days=3), s) == FIRST


@pytest.mark.parametrize(("now", "expected"), [
    ("2026-11-08T10:00:00+00:00", "2026-11-08T04:00:00-06:00"),
    ("2026-11-15T10:00:00+00:00", "2026-11-15T04:00:00-06:00"),
    ("2026-11-22T10:00:00+00:00", "2026-11-22T04:00:00-06:00"),
    ("2027-03-14T09:00:00+00:00", "2027-03-14T04:00:00-05:00"),
])
def test_later_weeks_keep_the_sunday_four_am_chicago_cutoff(now, expected):
    s = {"timezone": "America/Chicago", "weekday": 6, "hour": 4}
    assert schedule.scheduled_end(datetime.fromisoformat(now), s).isoformat() == expected


def test_it_is_due_only_when_switched_on_and_from_its_first_day(ready):
    repo, _, _ = ready
    assert schedule.due(repo.settings, FIRST - timedelta(hours=1)) is None, "before the first Sunday, nothing"
    assert schedule.due(repo.settings, FIRST) == "2026-11-01"
    assert schedule.due(repo.settings, FIRST + timedelta(days=6)) == "2026-11-01", "a missed tick runs on the next pass"
    assert schedule.due(repo.settings, FIRST + timedelta(days=7)) == "2026-11-08"
    with repo.connection() as conn:
        set_value(conn, "cycle.schedule.enabled", False, APPROVER)
    assert schedule.due(repo.settings, FIRST) is None
    with repo.connection() as conn:
        nxt = schedule.next_run(conn, FIRST - timedelta(days=1))
    assert nxt["enabled"] is False and nxt["at"] is None


def test_the_next_run_is_the_first_sunday_until_it_has_passed(ready):
    repo, _, _ = ready
    with repo.connection() as conn:
        assert schedule.next_run(conn, datetime(2026, 10, 25, 18, 0, tzinfo=UTC))["at"] == FIRST.astimezone(
            schedule.ZoneInfo("America/Chicago")).isoformat()
        assert schedule.next_run(conn, FIRST + timedelta(hours=1))["at"].startswith("2026-11-08T04:00")


def stub(monkeypatch, repo, *, documents):
    calls = {}
    monkeypatch.setattr(type(repo.settings), "generation_enabled", property(lambda self: True), raising=False)
    monkeypatch.setattr(schedule, "collect_window", lambda repo_, models, start, end, tz, actor: calls.setdefault(
        "collect", (start, end, tz, actor)) and {"meetings_listed": 2})
    monkeypatch.setattr(schedule, "activate_collector", lambda actor, now: calls.setdefault("activate", (actor, now)) and {"ok": 1})
    from backend_pipeline.cycle import window
    monkeypatch.setattr(window, "preview", lambda repo_, models, start, end: {
        "document_count": documents, "selection_hash": "hash-of-the-selection"})

    def start(repo_, models, actor, start_, end, *, mode, expected_selection):
        calls["start"] = (actor, start_, end, mode, expected_selection)
        with repo_.connection() as conn:
            conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-10-25','2026-10-25','2026-10-31') "
                         "ON CONFLICT DO NOTHING")
            conn.execute("""INSERT INTO pipeline_runs(run_id,week_id,run_scope,status,trigger_type,triggered_by,input_refs)
                VALUES ('run_sched','week_2026-10-25','weekly_angles','queued','manual',%s,'{"selected_by":"window"}')""", (actor,))
        return {"run_id": "run_sched", "week_id": "week_2026-10-25", "status": "queued", "estimate": {"total_usd": 0.7}}
    monkeypatch.setattr(window, "start", start)
    return calls


def test_the_run_collects_the_window_activates_the_collector_and_starts_the_cycle_under_the_approver(ready, monkeypatch):
    repo, models, _ = ready
    calls = stub(monkeypatch, repo, documents=6)
    result = schedule.run(repo.settings, models, FIRST)
    start, end = FIRST - timedelta(days=7), FIRST
    assert calls["collect"] == (start, end, "America/Chicago", APPROVER)
    assert calls["activate"][0] == APPROVER
    assert calls["start"] == (APPROVER, start, end, "live", "hash-of-the-selection")
    assert result["cycle"]["run_id"] == "run_sched"
    with repo.connection() as conn:
        run = conn.execute("SELECT trigger_type,input_refs FROM pipeline_runs WHERE run_id='run_sched'").fetchone()
    assert run["trigger_type"] == "scheduled" and run["input_refs"]["started_from"] == "schedule"


def test_a_window_without_a_call_starts_nothing(ready, monkeypatch):
    repo, models, _ = ready
    calls = stub(monkeypatch, repo, documents=0)
    result = schedule.run(repo.settings, models, FIRST)
    assert "start" not in calls and result["cycle"] is None and "No included call" in result["note"]


def test_without_an_approver_or_paid_calls_the_run_refuses_and_is_retried_then_alerted(ready):
    repo, models, _ = ready
    with pytest.raises(ValueError, match="ATELIER_ALLOW_GENERATION"):
        schedule.run(repo.settings, models, FIRST)
    with repo.connection() as conn:
        conn.execute("DELETE FROM settings WHERE key='cycle.schedule.actor'")  # back to its default: no one
    with pytest.raises(ValueError, match="names no approver"):
        schedule.run(repo.settings, models, FIRST)


def test_the_weeks_review_document_follows_the_finished_cycle(ready, monkeypatch):
    repo, models, _ = ready
    stub(monkeypatch, repo, documents=3)
    schedule.run(repo.settings, models, FIRST)
    from backend_pipeline.briefs import review_document
    head = "\n".join(review_document.header_lines())
    monkeypatch.setattr(review_document, "render_week", lambda repo_, week_id, exported=None: f"{head}\n## {week_id}\n\nNo cards yet.\n")
    assert schedule.review_documents(repo.settings, FIRST)["made"] == [], "the cycle has not finished"
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_runs SET status='waiting_for_review' WHERE run_id='run_sched'")
    assert schedule.review_documents(repo.settings, FIRST)["made"] == ["run_sched"]
    assert schedule.review_documents(repo.settings, FIRST)["made"] == [], "made once"
    with repo.connection() as conn:
        refs = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id='run_sched'").fetchone()["input_refs"]
    from backend_pipeline.artifacts import store_for
    assert store_for(repo.settings).read_bytes(refs["review_document"]["markdown"]).startswith(head.encode("utf-8"))
    word = store_for(repo.settings).read_bytes(refs["review_document"]["docx"])
    assert word[:2] == b"PK", "the Word file sits beside the Markdown"
    assert "No cards yet." in zipfile.ZipFile(io.BytesIO(word)).read("word/document.xml").decode("utf-8")
