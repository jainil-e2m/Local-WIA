"""One normaliser per source (plan 1.B14, N6): exact passage offsets, stable identifiers, speaker emails where the provider has them.

* `fathom_document`: a Fathom recording. The same function builds the document whether the transcript arrived from the
  Fathom API (intake) or from the native `transcript.raw.json` of an admission folder, so the same call gives identical
  passages, identifiers and speaker emails.
* `slack_threads`: Slack messages grouped by thread, one document per thread; every passage is exactly one original
  message's text, in order.
* `entries_document`: the generic builder for entries that are already text (attachments, extracted files).

Passage offsets are into `original_text`, which is the passages joined by a newline; a passage's text is always
`original_text[start:end]`.
"""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from ..store import canonical_hash
from .classify import UNINFORMATIVE_TITLE

LIVE_RESTRICTIONS = {"research_allowed": True, "public_use": False, "attribution_verified": False}
IST = ZoneInfo("Asia/Kolkata")


def timestamp_ms(value) -> int:
    match = re.fullmatch(r"(\d+):([0-5]\d):([0-5]\d)(?:\.(\d{1,3}))?", value or "")
    if not match:
        raise ValueError("Invalid Fathom segment timestamp")
    h, m, s, fraction = match.groups()
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int((fraction or "0").ljust(3, "0"))


def fathom_title(meeting: dict, recording_id=None) -> str:
    """A Fathom call's title: the calendar event's, unless it names nothing, when the recording's own name says what the call
    was. Zoom calls a meeting started on the spot "Impromptu Zoom Meeting", and WIA names the recording in Fathom ("Ads
    Consultation with <prospect>", N4); the rules read the call's type from the title."""
    calendar = (meeting.get("meeting_title") or "").strip()
    recording = (meeting.get("title") or "").strip()
    if calendar and not (recording and UNINFORMATIVE_TITLE.search(calendar)):
        return calendar
    return recording or calendar or f"Fathom {recording_id}"


def _joined(parts: list[str]) -> str:
    return "\n".join(parts)


def fathom_document(meeting: dict, payload: dict, raw_sha256: str, *, use_restrictions=None, filename_label=None,
                    extra_metadata=None) -> dict:
    """A Fathom recording as a document. `meeting` is the provider's metadata for it; `payload` the transcript JSON."""
    recording_id = meeting.get("recording_id")
    if type(recording_id) is not int:
        raise ValueError("Fathom recording identity mismatch")
    source_id = f"fathom:{recording_id}"
    occurred_text = meeting.get("recording_start_time")
    occurred = datetime.fromisoformat(occurred_text) if occurred_text else None
    if occurred is not None and occurred.tzinfo is None:
        raise ValueError("Fathom occurrence requires an explicit timezone")
    segments = payload.get("transcript") if isinstance(payload, dict) else None
    if not isinstance(segments, list) or not segments:
        raise ValueError("Fathom transcript is not available yet")
    parts, passages, cursor, previous = [], [], 0, None
    for i, segment in enumerate(segments):
        text = segment.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Fathom segment requires its complete source text")
        start_ms = timestamp_ms(segment.get("timestamp"))
        if previous is not None and start_ms < previous:
            raise ValueError("Fathom timestamps are not in source order")
        speaker_data = segment.get("speaker") or {}
        speaker = speaker_data.get("display_name")
        if speaker is not None and not isinstance(speaker, str):
            raise ValueError("Invalid Fathom speaker label")
        body = f"{speaker}: {text}" if speaker else text
        parts.append(body)
        passages.append({"passage_id": f"{source_id}:span:{i}", "ordinal": i, "start": cursor, "end": cursor + len(body),
                         "kind": "timestamped", "start_ms": start_ms, "end_ms": None, "speaker": speaker, "cue_settings": None,
                         "source_segment_index": i, "source_timestamp": segment["timestamp"],
                         "locator": {"segment": i, "timestamp": segment["timestamp"]}, "extraction_method": "provider",
                         "speaker_email": speaker_data.get("matched_calendar_invitee_email")})
        cursor += len(body) + 1
        previous = start_ms
    original = _joined(parts)
    title = fathom_title(meeting, recording_id)
    date_ist = occurred.astimezone(IST).date().isoformat() if occurred else None
    metadata = {"legacy_source_id": source_id, "normalized_sha256": hashlib.sha256(original.encode()).hexdigest(),
                "provider_metadata": meeting,
                "packet_metadata": {"filename_label": filename_label or f"fathom-{recording_id}", "name": title,
                                    "date": date_ist, "timezone": "Asia/Kolkata", "status": "verified_fathom_metadata"},
                **(extra_metadata or {})}
    return {"transcript_id": "transcript_" + canonical_hash({"source": source_id, "raw": raw_sha256})[:24],
            "source_type": "fathom", "upstream_id": source_id, "title": title,
            "source_url": meeting.get("share_url") or meeting.get("url"), "occurred_at": occurred,
            "occurred_at_source": "provider" if occurred else None, "original_text": original, "content_hash": raw_sha256,
            "passage_map": passages, "source_metadata": metadata, "use_restrictions": use_restrictions}


def entries_document(source_id, title, kind, entries, *, url=None, occurred_at=None, content_hash=None, upstream_id=None,
                     source_metadata=None, use_restrictions=LIVE_RESTRICTIONS, transcript_prefix="live_",
                     occurred_at_source="provider") -> dict:
    """A document from entries that already hold their text. Empty entries are skipped; offsets are into the joined text."""
    text, passages, cursor = [], [], 0
    for entry in entries:
        body = entry["text"]
        if not body.strip():
            continue
        ordinal = len(passages)
        passages.append({"passage_id": f"{source_id}:span:{ordinal}", "ordinal": ordinal, "start": cursor,
                         "end": cursor + len(body), "kind": kind, "speaker": entry.get("speaker"),
                         "start_ms": entry.get("start_ms"), "end_ms": entry.get("end_ms"),
                         "locator": entry.get("locator", {}), "extraction_method": entry.get("extraction_method", "provider")})
        text.append(body)
        cursor += len(body) + 1
    original = _joined(text)
    digest = content_hash or canonical_hash(entries)
    return {"transcript_id": transcript_prefix + canonical_hash([source_id, digest])[:32], "week_id": None,
            "source_type": kind, "upstream_id": upstream_id or source_id, "title": title, "source_url": url,
            "occurred_at": occurred_at, "occurred_at_source": occurred_at_source if occurred_at else None,
            "original_text": original, "content_hash": digest, "passage_map": passages,
            "source_metadata": {"normalized_sha256": hashlib.sha256(original.encode()).hexdigest(), **(source_metadata or {})},
            "use_restrictions": use_restrictions, "processing_status": "pending"}


def slack_time(ts: str) -> datetime:
    return datetime.fromtimestamp(float(Decimal(ts)), UTC)


def thread_key(message: dict) -> str:
    """A reply belongs to its thread's root; a message with no thread is its own thread."""
    return message.get("thread_ts") or message["ts"]


def slack_threads(messages: list[dict], channel: str, *, workspace: str = "", channel_name: str | None = None,
                  use_restrictions=LIVE_RESTRICTIONS) -> list[dict]:
    """Group Slack messages by thread and build one document per thread.

    Messages are dicts with `ts`, `text`, optionally `thread_ts`, `user` (or `user_name`), `deleted`, `files`, `edited`.
    A deleted message and an empty one contribute no passage. Every passage is exactly one message's text, so a passage
    resolves to the original message by its locator (channel and ts). A thread whose messages are all empty or deleted
    yields no document. Documents come back in order of their first message.
    """
    threads: dict[str, list[dict]] = {}
    for message in messages:
        threads.setdefault(thread_key(message), []).append(message)
    documents = []
    for root, members in sorted(threads.items(), key=lambda kv: Decimal(kv[0])):
        members = sorted({m["ts"]: m for m in members}.values(), key=lambda m: Decimal(m["ts"]))
        entries = [{"text": m.get("text") or "", "speaker": m.get("user_name") or m.get("user"),
                    "locator": {"channel": channel, "ts": m["ts"], "thread_ts": thread_key(m)},
                    "extraction_method": "provider"} for m in members if not m.get("deleted")]
        if not any(e["text"].strip() for e in entries):
            continue
        upstream = f"slack:{workspace}:{channel}:{root}"
        digest = canonical_hash([[m["ts"], m.get("text") or "", m.get("user"), bool(m.get("deleted"))] for m in members])
        label = channel_name or channel
        first = next(m for m in members if not m.get("deleted") and (m.get("text") or "").strip())
        documents.append(entries_document(
            upstream, f"Slack #{label} · {slack_time(first['ts']).date().isoformat()}", "slack", entries,
            url=next((m.get("permalink") for m in members if m.get("permalink")), None), occurred_at=slack_time(first["ts"]),
            content_hash=digest, upstream_id=upstream, transcript_prefix="transcript_", use_restrictions=use_restrictions,
            source_metadata={"legacy_source_id": upstream, "slack": {"workspace": workspace, "channel": channel,
                                                                    "thread_ts": root, "message_count": len(members)},
                             "packet_metadata": {"filename_label": f"slack-{channel}-{root}", "name": f"Slack #{label}",
                                                 "date": slack_time(first["ts"]).date().isoformat(), "timezone": "UTC",
                                                 "status": "slack_thread"}}))
    return documents
