"""Durable, opt-in Slack delivery from existing scheduling audit events.

The scheduler alone needs credentials. Calendar writes and their latency are unchanged.
Delivery is at least once: a lost Slack acknowledgement can cause a duplicate on retry.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from urllib.parse import urlsplit

import httpx
from psycopg.types.json import Jsonb

from . import settings_store
from .database import connect
from .slack_schedule_messages import DESTINATIONS, instant, message, public_origin, title

log = logging.getLogger(__name__)
TABLE = "slack_schedule_notifications"
EMAIL = "slack.schedule_notifications.email_channel_id"
SOCIAL = "slack.schedule_notifications.social_channel_id"
ORIGIN = "slack.schedule_notifications.public_app_url"
SETTING_KEYS = (EMAIL, SOCIAL, ORIGIN, "display.timezone")
MAX_AGE = timedelta(hours=24)
LEASE = timedelta(seconds=60)
DISCOVERY_LIMIT = 100
BACKOFF = (30, 120, 600, 1800)
MAX_ATTEMPTS = 5
SLACK_URL = "https://slack.com/api/chat.postMessage"
TRANSIENT = {"internal_error", "fatal_error", "service_unavailable", "ratelimited", "rate_limited"}


def state_key(destination):
    return f"slack.schedule_notifications.state.{destination}"


def cooldown_key(channel):
    return f"slack.schedule_notifications.cooldown.{channel}"


def _state(conn, key):
    row = conn.execute("SELECT value FROM settings WHERE key=%s", (key,)).fetchone()
    return row["value"] if row else None


def _put_state(conn, key, value):
    conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'slack-notifications')
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,updated_at=now()""", (key, Jsonb(value)))


def _record(conn, event, destination, channel, status, payload, now, error=None):
    conn.execute("""INSERT INTO slack_schedule_notifications
        (notification_id,source_event_id,destination,channel_id,status,payload,next_attempt_at,created_at,last_error)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (source_event_id,destination) DO NOTHING""",
        ("slack_" + uuid4().hex, event["event_id"], destination, channel, status, Jsonb(payload), now, now, error))


def initialize(conn, destination, channel, now):
    """Baseline exactly the visible historical set, without a lossy timestamp cursor."""
    key = state_key(destination)
    if _state(conn, key):
        return False
    conn.execute("""INSERT INTO slack_schedule_notifications
        (notification_id,source_event_id,destination,channel_id,status,last_error,created_at,next_attempt_at)
        SELECT 'slack_'||md5(event_id||%s),event_id,%s,%s,'skipped','before_activation',%s,%s
        FROM pipeline_events WHERE event_type='schedule_saved'
        ON CONFLICT (source_event_id,destination) DO NOTHING""", (destination, destination, channel, now, now))
    _put_state(conn, key, {"initialized_at": now.isoformat(), "initial_channel_id": channel})
    log.info("Slack schedule destination initialized: %s", destination)
    return True


def event_payload(conn, event, destination):
    details = event["details"] or {}
    changes = details.get("changes")
    pack_id = details.get("pack_id")
    if not isinstance(changes, list) or not isinstance(pack_id, str) or not 1 <= len(changes) <= 5:
        raise ValueError("invalid_schedule_event")
    assets = {r["asset_id"]: r for r in conn.execute(
        "SELECT * FROM content_assets WHERE pack_id=%s", (pack_id,))}
    pieces = []
    for change in changes:
        asset = assets.get(change.get("asset_id")) if isinstance(change, dict) else None
        if not asset or asset["asset_type"] not in DESTINATIONS:
            raise ValueError("missing_or_unknown_asset")
        at = instant(change["scheduled_for"])
        before = instant(change["previous_time"]) if change.get("previous_time") else None
        if DESTINATIONS[asset["asset_type"]] != destination or before == at:
            continue
        pieces.append({"asset_id": asset["asset_id"], "entry_id": change["entry_id"],
                       "slot_key": asset["slot_key"], "title": title(asset),
                       "scheduled_for": at.isoformat(), "previous_time": before.isoformat() if before else None})
    pieces.sort(key=lambda p: ("email", "carousel", "reel_1", "reel_2", "reel_3").index(p["slot_key"]))
    return {"version": 1, "pack_id": pack_id, "request_id": details.get("request_id"),
            "destination": destination, "event_created_at": event["created_at"].isoformat(), "pieces": pieces}


def discover(conn, destination, channel, now):
    if initialize(conn, destination, channel, now):
        return 0
    events = conn.execute("""SELECT e.event_id,e.details,e.created_at FROM pipeline_events e
        WHERE e.event_type='schedule_saved' AND NOT EXISTS (
            SELECT 1 FROM slack_schedule_notifications n WHERE n.source_event_id=e.event_id AND n.destination=%s)
        ORDER BY e.created_at,e.event_id LIMIT %s""", (destination, DISCOVERY_LIMIT)).fetchall()
    for event in events:
        try:
            payload = event_payload(conn, event, destination)
            reason = "expired" if now - event["created_at"] > MAX_AGE else "no_changed_pieces" if not payload["pieces"] else None
            _record(conn, event, destination, channel, "skipped" if reason else "pending", payload, now, reason)
        except (ValueError, KeyError, TypeError, IndexError):
            _record(conn, event, destination, channel, "failed", {}, now, "invalid_schedule_event")
    return len(events)


def claim(conn, channel, now):
    cooldown = _state(conn, cooldown_key(channel))
    if cooldown and instant(cooldown["until"]) > now:
        return None
    # A persisted channel lease also spaces different rows claimed by different schedulers.
    conn.execute("""UPDATE slack_schedule_notifications SET status=CASE WHEN attempt_count>=%s THEN 'failed' ELSE 'pending' END,
        claim_token=NULL,lease_expires_at=NULL,last_error='delivery_lease_expired'
        WHERE status='sending' AND lease_expires_at<=%s AND channel_id=%s""", (MAX_ATTEMPTS, now, channel))
    row = conn.execute("""SELECT * FROM slack_schedule_notifications WHERE channel_id=%s AND status='pending'
        AND next_attempt_at<=%s ORDER BY created_at,notification_id FOR UPDATE SKIP LOCKED LIMIT 1""", (channel, now)).fetchone()
    if not row:
        return None
    token = uuid4().hex
    conn.execute("""UPDATE slack_schedule_notifications SET status='sending',claim_token=%s,lease_expires_at=%s
        WHERE notification_id=%s""", (token, now + LEASE, row["notification_id"]))
    _put_state(conn, cooldown_key(channel), {"until": (now + LEASE).isoformat()})
    row["claim_token"] = token
    return row


def current_pieces(conn, row, now):
    """Filter replaced/cancelled/published content without invoking retired pack approval."""
    payload = row["payload"]
    pack = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s", (payload["pack_id"],)).fetchone()
    if not pack or conn.execute("SELECT 1 FROM content_packs WHERE supersedes_id=%s", (payload["pack_id"],)).fetchone():
        return []
    from .packs.views import published_marks
    from .removal import mark_of
    if mark_of(conn, "pack", payload["pack_id"]) or mark_of(conn, "brief", pack["source_brief_id"]):
        return []
    published = published_marks(conn, pack["source_brief_id"])
    kept = []
    for piece in payload["pieces"]:
        entry = conn.execute("""SELECT ce.*,a.content_hash AS current_hash,a.pack_id FROM calendar_entries ce
            JOIN content_assets a USING(asset_id) WHERE ce.calendar_entry_id=%s""", (piece["entry_id"],)).fetchone()
        if (entry and entry["pack_id"] == payload["pack_id"] and entry["asset_id"] == piece["asset_id"]
                and entry["status"] in ("scheduled", "needs_review") and entry["scheduled_for"] == instant(piece["scheduled_for"])
                and entry["scheduled_for"] > now and entry["asset_content_hash"] == entry["current_hash"]
                and entry["pack_manifest_hash"] == pack["manifest_hash"] and not published.get(piece["slot_key"])):
            kept.append(piece)
    return kept


def _finish(conn, row, *, status, now, error=None, retry_at=None, slack_ts=None, attempted=False):
    return conn.execute("""UPDATE slack_schedule_notifications SET status=%s,last_error=%s,next_attempt_at=%s,
        attempt_count=attempt_count+%s,claim_token=NULL,lease_expires_at=NULL,slack_ts=%s,sent_at=%s
        WHERE notification_id=%s AND status='sending' AND claim_token=%s""",
        (status, error, retry_at or now, int(attempted), slack_ts, now if status == "sent" else None,
         row["notification_id"], row["claim_token"])).rowcount


def send(client, token, channel, body):
    """Only allowlisted diagnostic codes escape; exception strings may contain credentials."""
    try:
        response = client.post(SLACK_URL, headers={"Authorization": f"Bearer {token}"},
                               json={"channel": channel, **body}, timeout=httpx.Timeout(5, connect=2))
    except httpx.HTTPError:
        return {"error": "transport_error", "transient": True}
    if response.status_code == 429:
        try:
            delay = min(86400, max(1, int(response.headers.get("Retry-After", "30"))))
        except ValueError:
            delay = 30
        return {"error": "rate_limited", "transient": True, "delay": delay}
    if response.status_code >= 500:
        return {"error": "slack_server_error", "transient": True}
    try:
        data = response.json()
    except ValueError:
        return {"error": "invalid_slack_response", "transient": False}
    if (response.is_success and isinstance(data, dict) and data.get("ok") is True
            and data.get("channel") == channel and isinstance(data.get("ts"), str) and data["ts"]):
        return {"ts": data["ts"]}
    code = data.get("error") if isinstance(data, dict) else None
    known = TRANSIENT | {"invalid_auth", "token_revoked", "account_inactive", "missing_scope", "not_in_channel",
                         "channel_not_found", "is_archived", "no_permission", "restricted_action", "invalid_arguments"}
    return {"error": code if isinstance(code, str) and code in known else "slack_rejected",
            "transient": isinstance(code, str) and code in TRANSIENT}


def tick(storage, now=None, *, client=None, environ=None, local_test_channel=None):
    now = now or datetime.now(UTC)
    env = os.environ if environ is None else environ
    token = env.get("ATELIER_SLACK_BOT_TOKEN", "").strip()
    if not token:
        return {"enabled": False, "reason": "bot_token_missing"}
    if storage.synthetic and client is None:
        return {"enabled": False, "reason": "synthetic_requires_transport"}
    with connect(storage.database_url, vectors=False) as conn:
        config = settings_store.values(SETTING_KEYS, conn)
    routes = {"email": config[EMAIL], "social": config[SOCIAL]}
    routes = {k: v for k, v in routes.items() if v and re.fullmatch(r"[CG][A-Z0-9]{8,30}", v)}
    if not routes:
        return {"enabled": False, "reason": "destinations_missing"}
    # Explicit local testing can use localhost links only for a synthetic test database
    # and one nominated channel. The production scheduler never supplies this option.
    local = local_test_channel is not None
    if local and not (storage.synthetic and urlsplit(storage.database_url).path.endswith("_test")
                      and set(routes.values()) == {local_test_channel}):
        return {"enabled": False, "reason": "invalid_local_test_configuration"}
    try:
        origin = public_origin(config[ORIGIN], allow_loopback=local)
    except ValueError:
        log.error("Slack schedule notifications paused: invalid_public_app_url")
        return {"enabled": False, "reason": "invalid_public_app_url"}
    result = {"enabled": True, "discovered": 0, "sent": 0, "failed": 0, "skipped": 0, "retried": 0}
    for destination, channel in routes.items():
        with connect(storage.database_url, vectors=False) as conn:
            locked = conn.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) AS held",
                                 (state_key(destination),)).fetchone()["held"]
            if locked:
                result["discovered"] += discover(conn, destination, channel, now)
    owned = client is None
    client = client or httpx.Client(follow_redirects=False, trust_env=False)
    try:
        for channel in dict.fromkeys(routes.values()):
            with connect(storage.database_url, vectors=False) as conn:
                locked = conn.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) AS held",
                                     (cooldown_key(channel),)).fetchone()["held"]
                row = claim(conn, channel, now) if locked else None
            if row is None:
                continue
            with connect(storage.database_url, vectors=False) as conn:
                payload = row["payload"]
                expired = not payload or now - instant(payload["event_created_at"]) > MAX_AGE
                pieces = current_pieces(conn, row, now) if not expired else []
            if routes.get(row["destination"]) != row["channel_id"]:
                outcome = {"error": "channel_configuration_changed", "transient": False}
            elif not pieces:
                outcome = {"skip": "expired_or_schedule_changed"}
            else:
                body = message(payload, pieces, origin, config["display.timezone"], allow_loopback=local)
                if local:
                    body["text"] = "[Local test] " + body["text"]
                    body["blocks"][0]["text"]["text"] = "[Local test] " + body["blocks"][0]["text"]["text"]
                outcome = send(client, token, channel, body)
            attempted = bool(pieces) and "skip" not in outcome and outcome.get("error") != "channel_configuration_changed"
            status, retry_at = "failed", None
            if "ts" in outcome:
                status = "sent"
            elif "skip" in outcome:
                status = "skipped"
            elif outcome.get("transient") and row["attempt_count"] + int(attempted) < MAX_ATTEMPTS:
                status = "pending"
                delay = max(BACKOFF[min(row["attempt_count"], len(BACKOFF)-1)], outcome.get("delay", 0))
                retry_at = now + timedelta(seconds=delay)
            with connect(storage.database_url, vectors=False) as conn:
                updated = _finish(conn, row, status=status, now=now, error=outcome.get("error") or outcome.get("skip"),
                                  retry_at=retry_at, slack_ts=outcome.get("ts"), attempted=attempted)
                if updated:
                    _put_state(conn, cooldown_key(channel), {"until": (retry_at or now + timedelta(seconds=1)).isoformat()})
            if updated:
                result["retried" if status == "pending" else status] += 1
                log.info("Slack schedule notification %s: %s (%s)", row["notification_id"], status, outcome.get("error") or "ok")
    finally:
        if owned:
            client.close()
    return result
