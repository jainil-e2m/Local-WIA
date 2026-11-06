"""Native Fathom admission. Raw JSON remains the immutable source of evidence."""

import hashlib
import json
import re
from datetime import datetime

from .store import canonical_hash


def timestamp_ms(value):
    match = re.fullmatch(r"(\d+):([0-5]\d):([0-5]\d)(?:\.(\d{1,3}))?", value or "")
    if not match:
        raise ValueError("Invalid Fathom segment timestamp")
    h, m, s, fraction = match.groups()
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int((fraction or "0").ljust(3, "0"))


def capture_fathom(path, week_index, ordinal):
    raw = path.read_bytes()
    metadata_raw = path.with_name("metadata.json").read_bytes()
    envelope = json.loads(metadata_raw)
    if (
        envelope.get("source_type") != "fathom"
        or envelope.get("classification") != "additional"
        or envelope.get("selected_as_additional_source") is not True
    ):
        raise ValueError("Fathom source is not selected for admission")
    if envelope.get("week") != week_index:
        raise ValueError("Fathom folder week differs from its selection metadata")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != envelope.get("transcript_sha256"):
        raise ValueError("Fathom raw transcript hash differs from its verified metadata")
    source_metadata = envelope["source_metadata"]
    rid = envelope["recording_id"]
    if type(rid) is not int or source_metadata.get("recording_id") != rid:
        raise ValueError("Fathom recording identity mismatch")
    occurred = datetime.fromisoformat(source_metadata["recording_start_time"])
    if occurred.tzinfo is None:
        raise ValueError("Fathom occurrence requires an explicit timezone")
    segments = json.loads(raw).get("transcript")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Fathom transcript is empty")
    source_id = f"fathom:{rid}"
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
        passages.append(
            {
                "passage_id": f"{source_id}:span:{i}",
                "ordinal": i,
                "start": cursor,
                "end": cursor + len(body),
                "kind": "timestamped",
                "start_ms": start_ms,
                "end_ms": None,
                "speaker": speaker,
                "cue_settings": None,
                "source_segment_index": i,
                "source_timestamp": segment["timestamp"],
                "speaker_email": speaker_data.get("matched_calendar_invitee_email"),
            }
        )
        cursor += len(body) + 1
        previous = start_ms
    normalized = "\n".join(parts)
    title = source_metadata.get("meeting_title") or source_metadata.get("title") or f"Fathom {rid}"
    return {
        "transcript_id": "transcript_" + canonical_hash({"source": source_id, "raw": digest})[:24],
        "source_type": "fathom",
        "upstream_id": source_id,
        "title": title,
        "source_url": source_metadata.get("url"),
        "occurred_at": occurred,
        "original_text": normalized,
        "content_hash": digest,
        "passage_map": passages,
        "source_metadata": {
            "legacy_source_id": source_id,
            "file_order": ordinal,
            "week_index": week_index,
            "normalized_sha256": hashlib.sha256(normalized.encode()).hexdigest(),
            "admission_metadata_sha256": hashlib.sha256(metadata_raw).hexdigest(),
            "provider_metadata": source_metadata,
            "packet_metadata": {
                "filename_label": path.name,
                "name": title,
                "date": envelope["occurrence_ist"][:10],
                "timezone": "Asia/Kolkata",
                "status": "verified_fathom_metadata",
            },
        },
    }
