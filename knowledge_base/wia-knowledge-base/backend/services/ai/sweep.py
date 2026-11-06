"""What the AI should run next. Only the AI worker (the `analysis` lane) sweeps, and only while AI_MODE=live.

- meeting_digest: a recent Fathom meeting with a transcript, linked to an active client, with no digest of its
  current version.
- team_meeting_digest: the same for an internal meeting (no client) whose title matches
  INTERNAL_MEETING_TITLE_PATTERN.
- call_brief: a client calendar event starting within AI_BRIEF_LEAD_HOURS, once; rebuilt in its last 2 hours
  only if the client's email, Slack or tasks changed after the brief was built (stale).
- email_actions: each active client, once per AI_EMAIL_BATCH_HOURS window that holds client email.
- history_moments: each active client with activity in the portfolio build, at most once a week (a new meeting
  digest changes its inputs; an unchanged input is never paid for twice).

Each becomes an `ai.run` job; the signature holds a freshness marker, so a sweep never queues the same work twice.
"""
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import String, cast, exists, select

from backend.config import get_settings
from backend.models.db import AiRun, Business, ReadModelSnapshot, RecordAssociation, SourceRecord, SourceVersion
from backend.services.ai import runner
from backend.workers import queue

LOOKBACK = timedelta(days=14)
FINAL = timedelta(hours=2)
CHANGES = ("gmail_message", "slack_message", "clickup_task")


def _no_run(skill, subject, version=None):
    q = select(AiRun.id).where(AiRun.skill == skill, AiRun.subject_id == cast(subject, String), AiRun.state == "succeeded")
    return ~exists(q.where(AiRun.checks["version"].astext == cast(version, String)) if version is not None else q)


def due(s, now: datetime | None = None) -> list[tuple[str, str, str]]:
    """(skill, subject id, freshness marker) for everything that should run now. Reads only."""
    settings, now = get_settings(), now or datetime.now(UTC)
    out = []
    linked = (select(RecordAssociation.record_id).join(Business, Business.id == RecordAssociation.business_id)
              .where(RecordAssociation.status == "associated", Business.status == "active"))
    meetings = (select(SourceRecord.id, SourceVersion.id, SourceVersion.attributes)
                .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
                .where(SourceRecord.record_kind == "fathom_recording", SourceRecord.admitted_at.is_not(None),
                       SourceVersion.content_state == "content", SourceRecord.occurred_at >= now - LOOKBACK))
    for rid, vid, _ in s.execute(meetings.where(SourceRecord.id.in_(linked),
                                                _no_run("meeting_digest", SourceRecord.id, SourceVersion.id))).all():
        out.append(("meeting_digest", str(rid), str(vid)))
    if settings.internal_meeting_title_pattern:
        pattern = re.compile(settings.internal_meeting_title_pattern, re.IGNORECASE)
        for rid, vid, attrs in s.execute(meetings.where(~SourceRecord.id.in_(linked),
                                                        _no_run("team_meeting_digest", SourceRecord.id, SourceVersion.id))).all():
            if pattern.search(attrs.get("title") or ""):
                out.append(("team_meeting_digest", str(rid), str(vid)))

    events = s.execute(select(SourceRecord.id, SourceRecord.occurred_at, RecordAssociation.business_id)
                       .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
                       .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                       .join(Business, Business.id == RecordAssociation.business_id)
                       .where(SourceRecord.record_kind == "calendar_event", SourceRecord.availability == "available",
                              RecordAssociation.status == "associated", Business.status == "active",
                              SourceVersion.attributes["status"].astext != "cancelled",
                              SourceRecord.occurred_at > now,
                              SourceRecord.occurred_at <= now + timedelta(hours=settings.ai_brief_lead_hours))).all()
    for rid, starts, business_id in events:
        built = s.execute(select(AiRun.created_at).where(AiRun.skill == "call_brief", AiRun.subject_id == str(rid),
                                                         AiRun.is_current)).scalar_one_or_none()
        if built is None:
            out.append(("call_brief", str(rid), "first"))
        elif starts - now <= FINAL and built < starts - FINAL and s.execute(
                select(SourceRecord.id).join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                .where(RecordAssociation.business_id == business_id, SourceRecord.record_kind.in_(CHANGES),
                       SourceRecord.last_observed_at > built).limit(1)).first():
            out.append(("call_brief", str(rid), "final"))

    hours = settings.ai_email_batch_hours
    end = datetime.fromtimestamp((now.timestamp() // (hours * 3600)) * hours * 3600, UTC)
    with_mail = (select(RecordAssociation.business_id).join(SourceRecord, SourceRecord.id == RecordAssociation.record_id)
                 .where(RecordAssociation.status == "associated", SourceRecord.record_kind == "gmail_message",
                        SourceRecord.occurred_at > end - timedelta(hours=hours), SourceRecord.occurred_at <= end))
    for slug, in s.execute(select(Business.slug).where(Business.status == "active", Business.id.in_(with_mail))).all():
        subject = f"{slug}:{end.isoformat()}"
        if s.execute(select(AiRun.id).where(AiRun.skill == "email_actions", AiRun.subject_id == subject,
                                            AiRun.state == "succeeded")).first() is None:
            out.append(("email_actions", subject, "batch"))
    week = now.strftime("%G-W%V")
    events = s.execute(select(ReadModelSnapshot.payload["events"]).where(ReadModelSnapshot.name == "portfolio")).scalar_one_or_none() or []
    with_activity = {e.get("clientId") for e in events}
    for slug, in s.execute(select(Business.slug).where(Business.status == "active")).all():
        if slug in with_activity and s.execute(select(AiRun.id).where(
                AiRun.skill == "history_moments", AiRun.subject_id == slug, AiRun.state == "succeeded",
                AiRun.checks["week"].astext == week)).first() is None:
            out.append(("history_moments", slug, week))
    return out


def sweep(s) -> int:
    if get_settings().ai_mode != "live":
        return 0
    items = due(s)
    for skill, subject, marker in items:
        queue.enqueue(s, runner.JOB, "analysis", f"ai:{skill}:{subject}:{marker}"[:300],
                      {"skill": skill, "subject_id": subject})
    return len(items)
