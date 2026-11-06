"""Offline rendering/transport and real PostgreSQL delivery mechanics; no live Slack calls."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from backend_pipeline import settings_store
from backend_pipeline.database import connect
from backend_pipeline.repository import ContentRepository, insert
from backend_pipeline.slack_schedule_messages import message, public_origin, title
from backend_pipeline import slack_schedule_notifications as notify
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import platform_url, empty  # noqa: F401

NOW = datetime(2026, 11, 5, 8, tzinfo=UTC)
EMAIL, SOCIAL = "C0BQ6RW7C84", "C063XKRCJ0M"
ENV = {"ATELIER_SLACK_BOT_TOKEN": "fake-test-token"}
ORIGIN = "https://atelier.example.test"
KEYS = ("email", "carousel", "reel_1", "reel_2", "reel_3")


def piece(key="email", **changes):
    return {"slot_key": key, "title": "A useful next step", "scheduled_for": (NOW+timedelta(days=2)).isoformat(),
            "previous_time": None, "asset_id": "a_"+key, "entry_id": "ce_"+key, **changes}


def test_piece_links_titles_timezone_and_accessible_fallback():
    body = message({"pack_id": "p one/2", "destination": "email"}, [piece()], ORIGIN, "Asia/Kolkata")
    assert "scheduled for publishing" in body["text"] and "ready to publish" not in body["text"]
    assert "/studio/packs/p%20one%2F2?piece=email" in body["text"]
    assert "13:30 IST (UTC+05:30)" in body["text"]
    assert body["blocks"][1]["text"]["verbatim"]
    assert not body["unfurl_links"] and not body["unfurl_media"] and not body["mrkdwn"]
    assert title({"asset_type": "email", "slot_key": "email", "content_body": {
        "content": {"subject_options": ["Best subject", "Other subject"], "title": "Not the email title"}}}) == "Best subject"


def test_social_group_has_every_piece_link_and_escapes_mentions():
    items = [piece(k, title="A <@U123> & <!channel> | *title*") for k in KEYS[1:]]
    body = message({"pack_id": "p", "destination": "social"}, items, ORIGIN, "America/Chicago")
    assert "4 new social content pieces" in body["text"]
    for key in KEYS[1:]:
        assert f"?piece={key}" in body["text"]
    rendered = body["blocks"][1]["text"]["text"]
    assert "<@U123>" not in rendered and "&lt;@U123&gt;" in rendered and "｜" in rendered
    assert "CST (UTC-06:00)" in body["text"]


def test_reschedule_and_mixed_messages_use_saved_instants():
    changed = piece("reel_1", previous_time=(NOW+timedelta(days=1)).isoformat())
    body = message({"pack_id": "p", "destination": "social"}, [changed], ORIGIN, "UTC")
    assert "updated the publishing schedule" in body["text"] and "→" in body["text"]
    mixed = message({"pack_id": "p", "destination": "social"}, [changed, piece("carousel")], ORIGIN, "UTC")
    assert "schedule updates" in mixed["text"] and "new social" not in mixed["text"]


@pytest.mark.parametrize("url", ["", "http://atelier.example.test", "https://a:b@atelier.example.test",
    "https://atelier.example.test/path", "https://atelier.example.test?x=1", "https://127.0.0.1",
    "https://api.railway.internal", "https://example.test\\evil", "https://example.test:bad"])
def test_links_require_a_public_https_origin(url):
    with pytest.raises(ValueError, match="invalid_public_app_url"):
        public_origin(url)


def test_explicit_loopback_origin_is_local_only_and_still_rejects_external_http():
    assert public_origin("http://localhost:3000", allow_loopback=True) == "http://localhost:3000"
    assert public_origin("http://127.0.0.1:3000/", allow_loopback=True) == "http://127.0.0.1:3000"
    for url in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        with pytest.raises(ValueError):
            public_origin(url)
    for url in ["http://example.com", "http://localhost.evil.test", "http://localhost:3000/x", "http://u:p@localhost:3000"]:
        with pytest.raises(ValueError):
            public_origin(url, allow_loopback=True)


@pytest.mark.parametrize("answer,expected", [
    (httpx.Response(200, json={"ok": True, "channel": EMAIL, "ts": "123.456"}), {"ts": "123.456"}),
    (httpx.Response(200, json={"ok": False, "error": "missing_scope"}), {"error": "missing_scope", "transient": False}),
    (httpx.Response(200, json={"ok": True, "channel": SOCIAL, "ts": "123"}), {"error": "slack_rejected", "transient": False}),
    (httpx.Response(200, json={"ok": False, "error": {"unexpected": "value"}}), {"error": "slack_rejected", "transient": False}),
    (httpx.Response(429, headers={"Retry-After": "125"}), {"error": "rate_limited", "transient": True, "delay": 125}),
    (httpx.Response(503), {"error": "slack_server_error", "transient": True}),
    (httpx.Response(403, text="secret-text-must-not-be-logged"), {"error": "invalid_slack_response", "transient": False}),
])
def test_transport_checks_slack_acknowledgement_and_sanitizes_errors(answer, expected):
    def transport(request):
        assert str(request.url) == notify.SLACK_URL
        assert request.headers["Authorization"] == "Bearer fake-test-token"
        return answer
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        assert notify.send(client, ENV["ATELIER_SLACK_BOT_TOKEN"], EMAIL, {"text": "test"}) == expected


def test_transport_timeout_has_no_token_in_the_error():
    def transport(request):
        raise httpx.ReadTimeout("sensitive exception string", request=request)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        assert notify.send(client, "credential", EMAIL, {}) == {"error": "transport_error", "transient": True}


def test_unconfigured_sender_does_not_open_database_or_http():
    assert notify.tick(SimpleNamespace(database_url="not-a-database"), NOW, environ={})["enabled"] is False
    assert notify.tick(StorageSettings(synthetic=True), NOW, environ=ENV)["reason"] == "synthetic_requires_transport"


def test_slack_failure_in_scheduler_does_not_stop_heartbeat_or_other_parts(monkeypatch):
    from backend_pipeline.jobs import scheduler
    seen = []
    monkeypatch.setattr(scheduler, "reconcile", lambda *a: seen.append("reconcile") or {})
    monkeypatch.setattr(scheduler.periodic, "run_due", lambda *a: {})
    monkeypatch.setattr(scheduler, "review_documents", lambda *a: {})
    monkeypatch.setattr(scheduler, "scan_alerts", lambda *a: {})
    monkeypatch.setattr(scheduler, "beat", lambda *a: seen.append("heartbeat"))
    def broken(*args, **kwargs):
        raise RuntimeError("mock Slack part unavailable")
    monkeypatch.setattr(notify, "tick", broken)
    storage = StorageSettings(context_enabled=False)
    result = scheduler.tick(storage, object(), repo=object(), now=NOW, tasks=[])
    assert result["slack_schedules"] == {"error": True}
    assert seen == ["reconcile", "heartbeat"]


def test_mapping_profile_targets_the_shared_testing_channel():
    import json
    from pathlib import Path
    profile = json.loads((Path(__file__).resolve().parents[2]/"deploy/slack-schedule-notifications.settings.json").read_text())
    typed = settings_store.validate_profile(profile)
    assert typed[notify.EMAIL] == typed[notify.SOCIAL] == "C0C3FT6DZAS"
    assert public_origin(typed[notify.ORIGIN]) == "https://content-atelier.up.railway.app"


@pytest.fixture
def db(platform_url):  # noqa: F811
    empty(platform_url)
    storage = StorageSettings(database_url=platform_url, synthetic=True)
    repo = ContentRepository(storage)
    with connect(platform_url, vectors=False) as conn:
        for key, value in [(notify.EMAIL, EMAIL), (notify.SOCIAL, SOCIAL), (notify.ORIGIN, ORIGIN), ("display.timezone", "Asia/Kolkata")]:
            settings_store.set_value(conn, key, value, actor="tester")
        insert(conn, "weeks", {"week_id": "w", "week_start": "2026-11-02", "week_end": "2026-11-08"})
        insert(conn, "pipeline_runs", {"run_id": "r", "week_id": "w", "run_scope": "scheduling",
                                     "trigger_type": "manual", "status": "completed", "input_refs": {}})
        insert(conn, "content_angles", {"angle_id": "angle", "week_id": "w", "run_id": "r",
            "content_body": {}, "content_hash": "h", "first_generated_at": NOW})
        insert(conn, "content_briefs", {"brief_id": "brief", "week_id": "w", "angle_id": "angle",
            "angle_input_hash": "h", "content_body": {}, "selected_evidence": [], "prior_content_context": [], "content_hash": "h"})
        insert(conn, "content_packs", {"pack_id": "pack", "week_id": "w", "title": "Pack",
            "source_brief_id": "brief", "manifest_hash": "m"})
        for i, key in enumerate(KEYS, 1):
            kind = "email" if key == "email" else "carousel" if key == "carousel" else "reel"
            insert(conn, "content_assets", {"asset_id": "a_"+key, "pack_id": "pack", "brief_id": "brief",
                "brief_input_hash": "h", "slot_key": key, "ordinal": i, "asset_type": kind, "reader_contribution": "test",
                "content_body": {"content": {"title": f"Title {key}", "subject_options": ["An email subject"]}}, "content_hash": "h"})
            insert(conn, "calendar_entries", {"calendar_entry_id": "ce_"+key, "asset_id": "a_"+key,
                "asset_content_hash": "h", "pack_manifest_hash": "m", "channel": "email" if key == "email" else "instagram",
                "scheduled_for": NOW+timedelta(days=2+i), "display_timezone": "UTC", "status": "scheduled"})
    calls = []
    def transport(request):
        import json
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "channel": calls[-1]["channel"], "ts": f"123.{len(calls)}"})
    client = httpx.Client(transport=httpx.MockTransport(transport))
    yield repo, client, calls
    client.close()


def event(repo, event_id="event", keys=KEYS, previous=None, at=NOW):
    with repo.connection() as conn:
        changes = [{"asset_id": "a_"+k, "entry_id": "ce_"+k,
                    "scheduled_for": (NOW+timedelta(days=3+KEYS.index(k))).isoformat(), "previous_time": previous, "revision": 1}
                   for k in keys]
        insert(conn, "pipeline_events", {"event_id": event_id, "run_id": "r", "event_type": "schedule_saved",
            "message": "schedule saved", "created_at": at, "details": {"pack_id": "pack", "request_id": event_id, "changes": changes}})


def run(db, at=NOW, client=None):
    repo, default_client, _ = db
    return notify.tick(repo.settings, at, environ=ENV, client=client or default_client)


def rows(db):
    with db[0].connection() as conn:
        return conn.execute("SELECT * FROM slack_schedule_notifications ORDER BY destination,source_event_id").fetchall()


def test_activation_skips_existing_events_and_restart_does_not_send_them(db):
    event(db[0], "history")
    assert run(db)["sent"] == 0
    assert {r["last_error"] for r in rows(db)} == {"before_activation"}
    assert run(db, NOW+timedelta(seconds=31))["sent"] == 0
    assert db[2] == []


def test_new_five_piece_save_routes_two_messages_with_piece_urls_and_no_repeat(db):
    run(db)
    event(db[0])
    assert run(db, NOW+timedelta(seconds=31))["sent"] == 2
    calls = {r["channel"]: r for r in db[2]}
    assert set(calls) == {EMAIL, SOCIAL}
    assert calls[EMAIL]["text"].count("?piece=") == 1
    assert calls[SOCIAL]["text"].count("?piece=") == 4
    assert "An email subject" in calls[EMAIL]["text"]
    assert "ready to publish" not in calls[SOCIAL]["text"]
    assert run(db, NOW+timedelta(seconds=62))["sent"] == 0
    assert all(r["status"] == "sent" and r["attempt_count"] == 1 for r in rows(db))


def test_partial_noop_expired_and_rolled_back_events(db):
    run(db)
    event(db[0], "noop", keys=("email",), previous=(NOW+timedelta(days=3)).isoformat())
    event(db[0], "old", keys=("email",), at=NOW-timedelta(days=2))
    with pytest.raises(RuntimeError):
        with db[0].connection() as conn:
            insert(conn, "pipeline_events", {"event_id": "rollback", "run_id": "r", "event_type": "schedule_saved",
                "message": "not committed", "details": {}})
            raise RuntimeError("rollback")
    assert run(db, NOW+timedelta(seconds=31))["sent"] == 0
    assert all(r["status"] == "skipped" for r in rows(db))
    assert not any(r["source_event_id"] == "rollback" for r in rows(db))


@pytest.mark.parametrize("change", ["cancel", "published", "rescheduled", "asset_edit", "new_pack"])
def test_stale_schedule_is_not_announced(db, change):
    run(db)
    event(db[0], keys=("email",))
    with db[0].connection() as conn:
        if change == "cancel":
            conn.execute("UPDATE calendar_entries SET status='cancelled' WHERE asset_id='a_email'")
        elif change == "published":
            insert(conn, "published_content", {"content_id": "pub", "source_kind": "approved_brief", "source_ref": "pack:brief:email",
                "channel": "email", "title": "published", "text": "text", "status": "confirmed", "created_by": "tester"})
        elif change == "rescheduled":
            conn.execute("UPDATE calendar_entries SET scheduled_for=scheduled_for+interval '1 hour' WHERE asset_id='a_email'")
        elif change == "asset_edit":
            conn.execute("UPDATE content_assets SET content_hash='other' WHERE asset_id='a_email'")
        else:
            insert(conn, "content_packs", {"pack_id": "new", "week_id": "w", "title": "new", "supersedes_id": "pack"})
    assert run(db, NOW+timedelta(seconds=31))["sent"] == 0
    assert db[2] == []


def test_retry_honors_rate_limit_survives_restart_and_other_channel_sends(db):
    run(db)
    event(db[0])
    def transport(request):
        import json
        channel = json.loads(request.content)["channel"]
        return httpx.Response(429, headers={"Retry-After": "120"}) if channel == EMAIL else httpx.Response(
            200, json={"ok": True, "channel": channel, "ts": "123.1"})
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        result = run(db, NOW+timedelta(seconds=31), client=client)
    assert result["sent"] == 1 and result["retried"] == 1
    assert run(db, NOW+timedelta(seconds=60))["sent"] == 0
    assert run(db, NOW+timedelta(seconds=152))["sent"] == 1
    assert next(r for r in rows(db) if r["destination"] == "email")["attempt_count"] == 2


def test_missing_permission_is_terminal_and_does_not_leak_token(db, caplog):
    run(db)
    event(db[0], keys=("email",))
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": False, "error": "missing_scope"}))) as client:
        assert run(db, NOW+timedelta(seconds=31), client=client)["failed"] == 1
    assert run(db, NOW+timedelta(minutes=2))["sent"] == 0
    assert ENV["ATELIER_SLACK_BOT_TOKEN"] not in caplog.text
    assert next(r for r in rows(db) if r["destination"] == "email")["last_error"] == "missing_scope"


def test_concurrent_schedulers_and_lost_claim_recovery(db):
    run(db)
    event(db[0], keys=("email",))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(db, NOW+timedelta(seconds=31)), range(2)))
    assert sum(r["sent"] for r in results) == 1 and len(db[2]) == 1
    event(db[0], "second", keys=("email",))
    with db[0].connection() as conn:
        notify.discover(conn, "email", EMAIL, NOW+timedelta(minutes=2))
        claimed = notify.claim(conn, EMAIL, NOW+timedelta(minutes=2))
    assert claimed
    assert run(db, NOW+timedelta(minutes=2, seconds=30))["sent"] == 0
    assert run(db, NOW+timedelta(minutes=3, seconds=1))["sent"] == 1


def test_invalid_url_and_missing_token_pause_without_initializing(db):
    repo, client, _ = db
    assert notify.tick(repo.settings, NOW, environ={}, client=client)["enabled"] is False
    with repo.connection() as conn:
        settings_store.set_value(conn, notify.ORIGIN, "", actor="tester")
    assert run(db)["reason"] == "invalid_public_app_url"
    assert rows(db) == []


def test_local_delivery_is_explicit_and_restricted_to_one_test_channel(db):
    repo, client, calls = db
    with repo.connection() as conn:
        settings_store.set_value(conn, notify.ORIGIN, "http://localhost:3000", actor="tester")
    assert notify.tick(repo.settings, NOW, client=client, environ=ENV, local_test_channel=EMAIL)["reason"] == "invalid_local_test_configuration"
    with repo.connection() as conn:
        settings_store.set_value(conn, notify.SOCIAL, EMAIL, actor="tester")
    assert run(db)["reason"] == "invalid_public_app_url"
    notify.tick(repo.settings, NOW, client=client, environ=ENV, local_test_channel=EMAIL)
    event(repo)
    for seconds in (31, 62):
        notify.tick(repo.settings, NOW+timedelta(seconds=seconds), client=client, environ=ENV, local_test_channel=EMAIL)
    assert len(calls) == 2 and {c["channel"] for c in calls} == {EMAIL}
    assert all(c["text"].startswith("[Local test]") and "http://localhost:3000/studio/packs/" in c["text"] for c in calls)
    repo.settings.synthetic = False
    assert notify.tick(repo.settings, NOW, client=client, environ=ENV, local_test_channel=EMAIL)["reason"] == "invalid_local_test_configuration"


def test_transient_failures_stop_after_five_attempts(db):
    run(db)
    event(db[0], keys=("email",))
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503))) as client:
        for minutes in (1, 2, 5, 16, 47):
            run(db, NOW+timedelta(minutes=minutes), client=client)
    email = next(r for r in rows(db) if r["destination"] == "email")
    assert email["status"] == "failed" and email["attempt_count"] == 5
    assert run(db, NOW+timedelta(hours=2))["sent"] == 0


def test_discovery_sees_a_late_commit_with_an_older_timestamp(db):
    run(db)
    event(db[0], "newer", keys=("email",), at=NOW+timedelta(seconds=10))
    assert run(db, NOW+timedelta(seconds=31))["sent"] == 1
    event(db[0], "late_commit", keys=("email",), at=NOW-timedelta(seconds=10))
    assert run(db, NOW+timedelta(seconds=62))["sent"] == 1


def test_missing_destination_only_pauses_that_route(db):
    with db[0].connection() as conn:
        settings_store.set_value(conn, notify.SOCIAL, None, actor="tester")
    run(db)
    event(db[0])
    assert run(db, NOW+timedelta(seconds=31))["sent"] == 1
    assert [c["channel"] for c in db[2]] == [EMAIL]
    with db[0].connection() as conn:
        settings_store.set_value(conn, notify.SOCIAL, SOCIAL, actor="tester")
    # First activation of social baselines existing events, not a historical replay.
    assert run(db, NOW+timedelta(seconds=62))["sent"] == 0


def test_real_schedule_save_receipt_and_rollback_drive_notifications(db, monkeypatch):
    """Real calendar transaction, audit and receipt; unrelated pack validation is covered by calendar suites."""
    from uuid import uuid4
    from backend_pipeline.calendar import service as calendar
    from backend_pipeline.calendar.contracts import Schedule, ScheduleItem
    from backend_pipeline.production_common import ProductionError
    repo, _, calls = db
    repo.settings.calendar_enabled = True
    repo.settings.calendar_schedulers = ("scheduler@example.invalid",)
    def locked(_repo, conn, pack_id):
        return (conn.execute("SELECT * FROM content_packs WHERE pack_id=%s FOR UPDATE", (pack_id,)).fetchone(),
                conn.execute("SELECT * FROM content_assets WHERE pack_id=%s ORDER BY ordinal", (pack_id,)).fetchall())
    monkeypatch.setattr(calendar.packs, "locked", locked)
    monkeypatch.setattr(calendar.packs, "blockers", lambda *a, **k: [])
    run(db)
    future = datetime.now(UTC)+timedelta(days=10)
    request = Schedule(request_id=str(uuid4()), expected_pack_manifest_hash="m", whole_pack=True,
        items=[ScheduleItem(asset_id="a_"+key, expected_asset_hash="h", entry_id="ce_"+key, expected_revision=1,
                            scheduled_for=future+timedelta(days=i), display_timezone="UTC") for i, key in enumerate(KEYS)])
    saved = calendar.schedule(repo, "pack", request, "scheduler@example.invalid")
    assert calendar.schedule(repo, "pack", request, "scheduler@example.invalid") == saved
    delivered = run(db, datetime.now(UTC)+timedelta(seconds=1))
    assert delivered["sent"] == 2 and len(calls) == 2
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM pipeline_events WHERE event_type='schedule_saved'").fetchone()["n"] == 1
    bad = request.model_copy(deep=True)
    bad.request_id = str(uuid4())
    for item in bad.items:
        item.expected_revision = 2
        item.scheduled_for += timedelta(days=1)
    bad.items[-1].expected_asset_hash = "stale"
    with pytest.raises(ProductionError, match="Selected asset changed"):
        calendar.schedule(repo, "pack", bad, "scheduler@example.invalid")
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM pipeline_events WHERE event_type='schedule_saved'").fetchone()["n"] == 1
        current = conn.execute("SELECT scheduled_for FROM calendar_entries WHERE asset_id='a_email'").fetchone()
        assert current["scheduled_for"] == future
