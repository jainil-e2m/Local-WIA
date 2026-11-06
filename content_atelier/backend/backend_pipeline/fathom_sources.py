"""Native Fathom admission. Raw JSON remains the immutable source of evidence.

The document itself is built by the one Fathom normaliser (normalise/sources.py), the same function the live intake uses
(plan 1.B14); this module only verifies the admission folder around it.
"""

import hashlib
import json

from .normalise.sources import fathom_document, timestamp_ms  # noqa: F401 (timestamp_ms is re-exported)


class NotSelected(ValueError):
    """A Fathom capture the reconciliation did not select for admission (a capture of a call Zoom already has, or an
    alternative): deliberately left out, not a fault in the file."""


def capture_fathom(path, week_index, ordinal):
    """Verify an admission folder and build its document. `week_index=None` is document intake: the folder's own week is
    recorded as a hint but is not checked against anything, and the document belongs to no week."""
    raw = path.read_bytes()
    metadata_raw = path.with_name("metadata.json").read_bytes()
    envelope = json.loads(metadata_raw)
    if (
        envelope.get("source_type") != "fathom"
        or envelope.get("classification") != "additional"
        or envelope.get("selected_as_additional_source") is not True
    ):
        raise NotSelected("Fathom source is not selected for admission (classification "
                          f"{envelope.get('classification')!r}, selected_as_additional_source {envelope.get('selected_as_additional_source')!r})")
    if week_index is not None and envelope.get("week") != week_index:
        raise ValueError("Fathom folder week differs from its selection metadata")
    if week_index is None:
        week_index = envelope.get("week") or 0
    digest = hashlib.sha256(raw).hexdigest()
    if digest != envelope.get("transcript_sha256"):
        raise ValueError("Fathom raw transcript hash differs from its verified metadata")
    source_metadata = envelope["source_metadata"]
    rid = envelope["recording_id"]
    if type(rid) is not int or source_metadata.get("recording_id") != rid:
        raise ValueError("Fathom recording identity mismatch")
    if not source_metadata.get("recording_start_time"):
        raise ValueError("Fathom occurrence requires an explicit timezone")
    segments = json.loads(raw).get("transcript")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Fathom transcript is empty")
    record = fathom_document(
        source_metadata, {"transcript": segments}, digest, filename_label=path.name,
        extra_metadata={"file_order": ordinal, "week_index": week_index,
                        "admission_metadata_sha256": hashlib.sha256(metadata_raw).hexdigest()})
    record["source_metadata"]["packet_metadata"]["date"] = envelope["occurrence_ist"][:10]
    return record
