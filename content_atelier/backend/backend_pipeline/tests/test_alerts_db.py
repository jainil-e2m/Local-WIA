"""6.B4 on a real database: each simulated failure produces exactly one alert, a condition that persists is counted on the
same alert, one that clears is resolved, and a dismissed one stays quiet until it has cleared once (Phase N6's exit)."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from backend_pipeline import alerts
from backend_pipeline.database import connect
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401 (fixture)

NOW = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def url(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_x','2026-10-25','2026-10-31')")
        conn.execute("""INSERT INTO pipeline_runs(run_id,week_id,run_scope,status,trigger_type,triggered_by,input_refs)
            VALUES ('run_x','week_x','brief_generation','running','manual','t','{}')""")
        # The first scan sets the watch start; set it before the simulated failures, as a deployment would.
        conn.execute("INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'t')",
                     (alerts.WATCH_SINCE_KEY, json.dumps({"at": (NOW - timedelta(days=1)).isoformat()})))
        conn.commit()
    return platform_url


def job(url, job_id, *, status, stage="brief_research", queue="interactive", created=NOW, updated=NOW, details=None,
        lease=None, error=None):
    with connect(url, vectors=False) as conn:
        conn.execute("""INSERT INTO pipeline_jobs(job_id,run_id,week_id,stage,status,idempotency_key,progress_details,queue,
            executor,created_at,updated_at,lease_expires_at,lease_token,heartbeat_at,error_summary)
            VALUES (%s,'run_x','week_x',%s,%s,%s,%s,%s,'rq',%s,%s,%s,%s,%s,%s)""",
                     (job_id, stage, status, f"run_x:{job_id}", json.dumps(details or {"dependencies": []}), queue, created,
                      updated, lease, "lease" if lease else None, updated if lease else None, error))
        conn.commit()


def scan(url, now=NOW):
    with connect(url, vectors=False) as conn:
        result = alerts.scan(conn, now)
        conn.commit()
    return result


def rows(url):
    with connect(url, vectors=False) as conn:
        return conn.execute("SELECT kind,subject,occurrences,resolution,notified FROM alerts ORDER BY first_seen_at,kind").fetchall()


def test_a_failed_job_is_one_alert_counted_while_it_stays_failed_and_cleared_when_retried(url):
    job(url, "job_a", status="failed", error="Provider refused the request")
    assert scan(url) == {"opened": 1, "still_open": 0, "cleared": 0}
    assert scan(url, NOW + timedelta(seconds=30)) == {"opened": 0, "still_open": 1, "cleared": 0}
    (row,) = rows(url)
    assert (row["kind"], row["subject"], row["occurrences"], row["resolution"]) == ("job_failed", "job_a", 2, None)
    assert row["notified"]["email"] == "off"  # the owner's ruling: the app is the channel, nothing is emailed
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE pipeline_jobs SET status='queued' WHERE job_id='job_a'")
        conn.commit()
    assert scan(url, NOW + timedelta(minutes=1))["cleared"] == 1
    assert rows(url)[0]["resolution"] == "cleared"


def test_a_failure_from_before_the_watch_start_raises_nothing(url):
    job(url, "job_old", status="failed", updated=NOW - timedelta(days=3))
    assert scan(url)["opened"] == 0


def test_a_stuck_queue_is_one_alert_but_a_busy_one_is_not(url):
    job(url, "job_q1", status="queued", created=NOW - timedelta(minutes=40))
    job(url, "job_q2", status="queued", created=NOW - timedelta(minutes=35))
    assert scan(url)["opened"] == 1
    (row,) = rows(url)
    assert (row["kind"], row["subject"]) == ("job_stuck", "interactive")
    # A job on the queue finished a minute ago: the queue is moving, so it clears.
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE pipeline_jobs SET status='completed',started_at=%s,finished_at=%s WHERE job_id='job_q1'",
                     (NOW - timedelta(minutes=2), NOW - timedelta(minutes=1)))
        conn.commit()
    assert scan(url, NOW + timedelta(seconds=30))["cleared"] == 1


def test_a_job_behind_an_unfinished_dependency_is_not_stuck(url):
    job(url, "job_head", status="running", lease=NOW + timedelta(minutes=10), created=NOW - timedelta(hours=2))
    job(url, "job_next", status="queued", created=NOW - timedelta(hours=2), details={"dependencies": ["job_head"]})
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE pipeline_jobs SET started_at=%s WHERE job_id='job_head'", (NOW - timedelta(minutes=5),))
        conn.commit()
    assert scan(url)["opened"] == 0


def test_a_lost_worker_is_a_stuck_queue(url):
    job(url, "job_lost", status="running", lease=NOW - timedelta(minutes=20))
    scan(url)
    assert [(r["kind"], r["subject"]) for r in rows(url)] == [("job_stuck", "interactive")]


def test_a_stopped_intake_connection_is_one_alert(url):
    with connect(url, vectors=False) as conn:
        conn.execute("""INSERT INTO intake_connections(connection_id,provider,activated_at,checkpoint,health,config)
            VALUES ('fathom','fathom',%s,%s,'healthy','{}')""", (NOW - timedelta(hours=5), NOW - timedelta(hours=5)))
        conn.commit()
    scan(url)
    assert [(r["kind"], r["subject"]) for r in rows(url)] == [("intake_stopped", "fathom")]
    # A collection runs: the checkpoint moves to the end of the window it listed.
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE intake_connections SET checkpoint=%s WHERE connection_id='fathom'", (NOW - timedelta(minutes=5),))
        conn.commit()
    assert scan(url, NOW + timedelta(seconds=30))["cleared"] == 1


def test_a_connection_not_yet_active_is_not_watched(url):
    with connect(url, vectors=False) as conn:
        conn.execute("""INSERT INTO intake_connections(connection_id,provider,activated_at,checkpoint,health,config)
            VALUES ('fathom','fathom',%s,%s,'healthy','{}')""", (NOW + timedelta(days=1), NOW + timedelta(days=1)))
        conn.commit()
    assert scan(url)["opened"] == 0


def test_a_budget_refusal_is_one_alert_per_purpose_and_a_dismissal_holds_until_it_clears(url):
    waiting = {"waiting_for": "budget", "budget_purpose": "briefs", "budget_reason": "this week's USD 4.00 is spent",
               "dependencies": []}
    job(url, "job_b1", status="waiting", details=waiting)
    job(url, "job_b2", status="waiting", details=waiting)
    assert scan(url)["opened"] == 1
    with connect(url, vectors=False) as conn:
        (open_alert,) = conn.execute("SELECT alert_id,message FROM alerts WHERE resolved_at IS NULL").fetchall()
        assert "2 job(s) are waiting for this week's briefs budget" in open_alert["message"]
        alerts.dismiss(conn, open_alert["alert_id"], "approver@example.invalid")
        conn.commit()
    assert scan(url, NOW + timedelta(seconds=30))["opened"] == 0  # acknowledged: quiet while it persists
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE pipeline_jobs SET status='queued' WHERE status='waiting'")
        conn.commit()
    scan(url, NOW + timedelta(minutes=1))  # cleared once
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE pipeline_jobs SET status='waiting' WHERE job_id='job_b1'")
        conn.commit()
    assert scan(url, NOW + timedelta(minutes=2))["opened"] == 1  # the same condition again: a new alert


def test_a_scheduled_task_out_of_attempts_is_a_missed_schedule(url):
    with connect(url, vectors=False) as conn:
        conn.execute("INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'scheduler')",
                     ("schedule.weekly_cycle.2026-11-01", json.dumps({"state": "failed", "attempts": 3, "error": "no approver"})))
        conn.commit()
    scan(url)
    with connect(url, vectors=False) as conn:
        (row,) = conn.execute("SELECT kind,message FROM alerts").fetchall()
    # The weekly run is tried eight times (cycle/schedule.ATTEMPTS): from the third failure it is an alert that says so.
    assert row["kind"] == "schedule_missed" and "weekly cycle failed 3 times and is tried again by itself" in row["message"]
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE settings SET value=%s WHERE key='schedule.weekly_cycle.2026-11-01'",
                     (json.dumps({"state": "failed", "attempts": 8, "error": "no approver"}),))
        conn.commit()
    scan(url)
    with connect(url, vectors=False) as conn:
        (row,) = conn.execute("SELECT kind,message FROM alerts").fetchall()
    assert "weekly cycle did not run: no approver" in row["message"]


def test_a_missed_hour_clears_when_a_later_hour_of_the_task_runs(url):
    with connect(url, vectors=False) as conn:
        conn.execute("INSERT INTO settings(key,value,updated_by,updated_at) VALUES (%s,%s,'scheduler',now() - interval '1 hour')",
                     ("schedule.upkeep.2026-10-25T18", json.dumps({"state": "failed", "attempts": 3, "error": "budget"})))
        conn.commit()
    assert scan(url)["opened"] == 1
    with connect(url, vectors=False) as conn:
        conn.execute("INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'scheduler')",
                     ("schedule.upkeep.2026-10-25T19", json.dumps({"state": "done", "attempts": 1})))
        conn.commit()
    scan(url)
    with connect(url, vectors=False) as conn:
        row = conn.execute("SELECT resolution FROM alerts WHERE subject='schedule.upkeep.2026-10-25T18'").fetchone()
    assert row["resolution"] == "cleared", "the next hour picked up what the missed one left"


def test_a_missed_backup_and_a_failed_restore_check_are_alerts(url):
    with connect(url, vectors=False) as conn:
        conn.execute("INSERT INTO settings(key,value,updated_by,updated_at) VALUES (%s,%s,'db-backup',%s)",
                     (alerts.BACKUP_KEY, json.dumps({"key": "k"}), NOW - timedelta(hours=40)))
        conn.execute("INSERT INTO settings(key,value,updated_by,updated_at) VALUES (%s,%s,'db-backup',%s)",
                     (alerts.RESTORE_KEY, json.dumps({"ok": False, "problem": "settings: expected 9, restored 8"}), NOW - timedelta(days=1)))
        conn.commit()
    scan(url)
    assert sorted(r["kind"] for r in rows(url)) == ["backup_missing", "restore_check_failed"]


def test_listing_adds_a_silent_scheduler_live(url):
    with connect(url, vectors=False) as conn:
        listed = alerts.listing(conn, now=NOW)
    assert listed["alerts"][0]["kind"] == "scheduler_silent" and listed["email"] == "off"


def test_low_accepted_share_two_judged_weeks_running_is_an_alert(url):
    with connect(url, vectors=False) as conn:
        for week, start in (("week_a", "2026-10-12"), ("week_b", "2026-10-19")):
            conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES (%s,%s,%s::date+6)", (week, start, start))
            for i in range(4):
                angle = f"angle_{week}_{i}"
                conn.execute("""INSERT INTO content_angles(angle_id,week_id,run_id,content_body,content_hash,created_at,
                    first_generated_at) VALUES (%s,%s,'run_x',%s,%s,%s,%s)""",
                             (angle, week, json.dumps({"card": {"rank": i + 1}, "title": angle}), f"h{angle}",
                              f"{start}T12:00:00Z", f"{start}T12:00:00Z"))
                disposition = "develop" if i == 0 else "skip"
                conn.execute("""INSERT INTO decisions(decision_id,item_kind,item_id,week_id,action,disposition,actor,author)
                    VALUES (%s,'angle',%s,%s,'decide',%s,'t','t')""", (f"d_{angle}", angle, week, disposition))
        conn.commit()
    scan(url)
    with connect(url, vectors=False) as conn:
        (row,) = conn.execute("SELECT kind,subject,message FROM alerts").fetchall()
    assert (row["kind"], row["subject"]) == ("accepted_share_low", "week_b")
    assert "25% of 4" in row["message"]


def test_a_queue_behind_one_long_running_job_with_a_live_lease_is_not_stuck(url):
    job(url, "job_long", status="running", lease=NOW + timedelta(minutes=5), created=NOW - timedelta(minutes=40))
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE pipeline_jobs SET started_at=%s WHERE job_id='job_long'", (NOW - timedelta(minutes=30),))
        conn.commit()
    job(url, "job_behind", status="queued", created=NOW - timedelta(minutes=35))
    assert scan(url)["opened"] == 0, "the brief's long claim check is running; its queue is not stuck"
