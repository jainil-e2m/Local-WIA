"""What the AI should run next. Only the AI worker (the `analysis` lane) sweeps, and only while AI_MODE=live.

- meeting_digest: a recent Fathom meeting with a transcript, linked to an active client, with no digest of its
  current version, unless that version's transcript is word for word the one already digested.
- team_meeting_digest: the same for an internal meeting (no client) whose title matches
  INTERNAL_MEETING_TITLE_PATTERN.
- call_brief: services/callprep/schedule.py (first build within AI_BRIEF_LEAD_HOURS; a rebuild in the last 2 hours
  only when the brief's inputs changed; a rebuild when its call-type skill was edited).
- email_actions: each active client, once per AI_EMAIL_BATCH_HOURS window that holds client email, looking back
  EMAIL_CATCH_UP windows so one missed while the worker was down is still read.
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
EMAIL_CATCH_UP = 7  # email batch windows looked back on (7 days at the default 24-hour window)


def _same_transcript(s, record_id, version_id) -> bool:
    """The current digest already covers these words: the new version only changed what isn't the transcript."""
    from backend.services.ai.context import transcript_fingerprint
    current = s.execute(select(AiRun.checks).where(AiRun.skill == "meeting_digest", AiRun.subject_id == str(record_id),
                                                   AiRun.is_current, AiRun.state == "succeeded")).scalar_one_or_none()
    return bool(current and current.get("transcript") == transcript_fingerprint(s, version_id))


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
        if not _same_transcript(s, rid, vid):
            out.append(("meeting_digest", str(rid), str(vid)))
    if settings.internal_meeting_title_pattern:
        pattern = re.compile(settings.internal_meeting_title_pattern, re.IGNORECASE)
        for rid, vid, attrs in s.execute(meetings.where(~SourceRecord.id.in_(linked),
                                                        _no_run("team_meeting_digest", SourceRecord.id, SourceVersion.id))).all():
            if pattern.search(attrs.get("title") or ""):
                out.append(("team_meeting_digest", str(rid), str(vid)))

    from backend.services.callprep import schedule
    for record_id, trigger, fingerprint in schedule.due(s, now):
        out.append(("call_brief", record_id, f"{trigger}:{fingerprint[:12]}"))

    hours = settings.ai_email_batch_hours
    latest = datetime.fromtimestamp((now.timestamp() // (hours * 3600)) * hours * 3600, UTC)
    # The last EMAIL_CATCH_UP windows, not just the latest: a window that closed while the AI worker was down (a
    # redeploy, an outage) is still read. A window whose job failed for good waits for `kb ai retry`.
    for back in range(EMAIL_CATCH_UP):
        end = latest - timedelta(hours=hours * back)
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
        payload = {"skill": skill, "subject_id": subject}
        if skill == "call_brief":
            payload["options"] = {"trigger": marker.split(":")[0], "built_by": "auto"}
        queue.enqueue(s, runner.JOB, "analysis", f"ai:{skill}:{subject}:{marker}"[:300], payload)
    return len(items)
