"""6.F2's cycle summary, 3.B11's next run and 6.B4's alerts through the API on a real database: what Home reads.

Synthetic rows only (R48)."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline.settings_store import set_value
from backend_pipeline.storage_api import router
from backend_pipeline.summary import summary
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)


@pytest.fixture
def repo(platform_setup):  # noqa: F811
    repo, _, _ = platform_setup
    with repo.connection() as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_s','2026-10-25','2026-10-31')")
        conn.execute("""INSERT INTO pipeline_runs(run_id,week_id,run_scope,status,trigger_type,triggered_by,input_refs)
            VALUES ('run_s','week_s','weekly_angles','waiting_for_review','scheduled',%s,'{"selected_by":"window","started_from":"schedule"}')""",
                     (APPROVER,))
        for n in range(1, 4):
            conn.execute("""INSERT INTO content_angles(angle_id,week_id,run_id,content_body,content_hash,first_generated_at)
                VALUES (%s,'week_s','run_s',%s,%s,now())""", (f"card_{n}", json.dumps({"card": {"rank": n}, "title": f"Card {n}"}), f"h{n}"))
        conn.execute("""INSERT INTO decisions(decision_id,item_kind,item_id,week_id,action,disposition,hold_until,actor,author)
            VALUES ('d_hold','angle','card_3','week_s','decide','hold',%s,%s,%s)""", (date.today() - timedelta(days=1), APPROVER, APPROVER))
    return repo


def test_the_summary_says_what_waits_for_whom_the_latest_cycle_and_the_held_card_due_back(repo):
    with repo.connection() as conn:
        result = summary(conn, datetime.now(UTC))
    waiting = result["waiting"]
    assert waiting["cards_at_gate_1"]["count"] == 2 and waiting["cards_at_gate_1"]["who"] == "an approver"
    assert [c["angle_id"] for c in waiting["held_cards_due_back"]["cards"]] == ["card_3"]
    assert result["latest_cycle"]["run_id"] == "run_s" and result["latest_cycle"]["started_from"] == "schedule"
    assert result["sources"]["collector"].startswith("not active") and result["alerts"]["open"] >= 1  # the silent scheduler
    assert result["next_cycle"]["enabled"] is False
    assert result["spend"]["limits_reached"] == [] and isinstance(result["spend"]["limits_close"], list)
    # What Home reads is the published model (the app's generated type), field for field.
    from backend_pipeline.api_models import CycleOverview
    CycleOverview.model_validate(json.loads(json.dumps(result, default=str)))


def test_home_reads_the_summary_the_schedule_and_the_alerts_through_the_api(repo):
    with repo.connection() as conn:
        set_value(conn, "cycle.schedule.enabled", True, APPROVER)
        set_value(conn, "cycle.schedule.first_day", "2026-11-01", APPROVER)
    app = FastAPI()
    app.include_router(router(repo.settings))
    http = TestClient(app)
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": EDITOR, "X-Atelier-Email": EDITOR}
    assert http.get("/storage/summary", headers=headers).json()["waiting"]["cards_at_gate_1"]["count"] == 2
    schedule = http.get("/storage/schedule", headers=headers).json()
    assert schedule["enabled"] is True and schedule["text"] == "Sunday 04:00 America/Chicago"
    alerts = http.get("/storage/alerts", headers=headers).json()
    assert alerts["email"] == "off" and alerts["alerts"][0]["kind"] == "scheduler_silent"
    from backend_pipeline.api_models import AlertList, CycleOverview, CycleSchedule
    CycleOverview.model_validate(http.get("/storage/summary", headers=headers).json())
    CycleSchedule.model_validate(schedule)
    AlertList.model_validate(alerts)
    assert schedule["at"] and schedule["window"]["end"] == schedule["at"]
    assert http.get("/storage/summary").status_code in (401, 403), "the backend secret is required"


def test_an_archived_week_leaves_the_lists_and_the_summary_but_stays_as_the_record(repo):
    from backend_pipeline import week_archive
    with repo.connection() as conn:
        with pytest.raises(ValueError, match="Say why"):
            week_archive.archive(conn, "week_s", reason=" ", actor=APPROVER)
        assert week_archive.archive(conn, "week_s", reason="Superseded by the regenerated week", actor=APPROVER)["changed"]
        assert not week_archive.archive(conn, "week_s", reason="again", actor=APPROVER)["changed"]
        assert summary(conn)["waiting"]["cards_at_gate_1"]["count"] == 0
        assert conn.execute("SELECT count(*) n FROM content_angles WHERE week_id='week_s'").fetchone()["n"] == 3, "nothing deleted"
    app = FastAPI()
    app.include_router(router(repo.settings))
    http = TestClient(app)
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": EDITOR, "X-Atelier-Email": EDITOR}
    assert "week_s" not in [w["week_id"] for w in http.get("/storage/weeks", headers=headers).json()]
    assert "week_s" in [w["week_id"] for w in http.get("/storage/weeks?include_archived=true", headers=headers).json()]
    with repo.connection() as conn:
        assert week_archive.restore(conn, "week_s", actor=APPROVER)["status"] == "pending", "back to what it was"


def test_an_open_alert_is_dismissed_through_the_api_and_the_live_one_cannot_be(repo):
    """6.F5's Dismiss: a stored open alert is acknowledged by the person the email names; an unknown or already resolved one
    is a 404, and the scheduler's silence (no alert_id) is never offered."""
    from backend_pipeline import alerts
    from backend_pipeline.api_models import AlertDismissed, AlertList
    now = datetime.now(UTC)
    with repo.connection() as conn:
        conn.execute("""INSERT INTO alerts(alert_id,kind,subject,severity,message,details,first_seen_at,last_seen_at,notified)
            VALUES ('alert_t','budget_refused','briefs','warning','Two jobs wait for the briefs budget','{}',%s,%s,'{"email":"off"}')""",
                     (now, now))
    app = FastAPI()
    app.include_router(router(repo.settings))
    http = TestClient(app)
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": EDITOR, "X-Atelier-Email": EDITOR}
    listed = AlertList.model_validate(http.get("/storage/alerts", headers=headers).json())
    assert [a.alert_id for a in listed.alerts if a.kind != "scheduler_silent"] == ["alert_t"]
    answer = http.post("/storage/alerts/alert_t/dismiss", headers=headers)
    assert answer.status_code == 200 and AlertDismissed.model_validate(answer.json()).alert_id == "alert_t"
    assert http.post("/storage/alerts/alert_t/dismiss", headers=headers).status_code == 404, "already resolved"
    resolved = http.get("/storage/alerts?resolved=true", headers=headers).json()["alerts"]
    assert [(a["resolution"], a["resolved_by"]) for a in resolved if a["alert_id"] == "alert_t"] == [("dismissed", EDITOR)]
    assert [a["alert_id"] for a in resolved if a["kind"] == "scheduler_silent"] == [None], "the live silence has no id to dismiss"
    with repo.connection() as conn:
        assert alerts.listing(conn)["open"] == 1, "only the live silence is open"


def test_the_spend_line_names_the_weekly_limits_reached_and_close(repo, monkeypatch):
    """Home's one line to an approver (6.F2): which weekly limit is reached or close, by its label, never a figure."""
    from backend_pipeline import summary as module
    from backend_pipeline.llm import standing
    budgets = [{"label": "briefs", "enabled": True, "cap_usd": 1.0, "spent_usd": 1.0, "left_usd": 0.0},
               {"label": "content packs", "enabled": True, "cap_usd": 2.0, "spent_usd": 1.7, "left_usd": 0.3},
               {"label": "weekly cycle", "enabled": True, "cap_usd": 1.2, "spent_usd": 0.1, "left_usd": 1.1},
               {"label": "context mining", "enabled": False, "cap_usd": 0.0, "spent_usd": 0.0, "left_usd": 0.0},
               {"label": "embedding", "enabled": True, "cap_usd": None, "spent_usd": 0.0, "left_usd": 0.0}]
    monkeypatch.setattr(standing, "status", lambda conn: {"budgets": budgets})
    with repo.connection() as conn:
        spend = module.summary(conn)["spend"]
    assert spend["limits_reached"] == ["briefs"] and spend["limits_close"] == ["content packs"]
    assert spend["caps_usd"] == 4.2 and spend["this_week_usd"] == 2.8
