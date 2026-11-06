"""The one `Citation` shape (plan 2.B6; shared by search now, the weekly cycle in Phase 3 and briefs in Phase 4).

A citation says exactly where a piece of evidence is: the document, the passages, the character range in the immutable
original text, the timestamp when the source has one, who spoke and in what role, the client, the consent status the
backend computed, when it happened, where the recording is, and the quote itself. Consent is computed by the backend and
only displayed by the frontend: the browser never decides whether a quote is usable.

For a moment hit, `passage_ids` are the passages the extractor anchored the scene on, `start` and `end` bound the verified
quote inside the original text (so `original_text[start:end] == quote`), and the timestamp is the anchor passage's. For a
chunk hit they are the chunk's passage range and `quote` is the original text of that range. A citation that cannot be
located in the original text is never built (`CitationError`): search withholds the hit rather than cite what it cannot
find.
"""
from __future__ import annotations

import re
from datetime import datetime

from .models import Answer

URL_LIMIT = 2000
_SLACK_ID = re.compile(r"^[A-Z0-9]{6,20}$")
_THREAD_TS = re.compile(r"^\d{9,12}\.\d{1,9}$")


class CitationError(ValueError):
    """The evidence cannot be located in the original text."""


class Citation(Answer):
    document_id: str
    document_title: str
    source_type: str
    call_type: str | None
    passage_ids: list[str]
    start: int
    end: int
    start_ms: int | None
    end_ms: int | None
    speaker_label: str | None
    speaker_id: str | None
    speaker_role: str
    client_id: str | None
    client_name: str | None
    consent_status: str
    occurred_at: datetime | None
    recording_url: str | None
    quote: str


def _http_url(value) -> str | None:
    if not isinstance(value, str) or len(value) > URL_LIMIT or not value.startswith(("https://", "http://")):
        return None
    return None if any(ch.isspace() or ord(ch) < 32 for ch in value) else value


def recording_url(source_type: str | None, source_url, source_metadata) -> str | None:
    """Where to listen to or read the source, from what the document already holds, or None.

    The document's own link first (a Fathom share link, a Slack permalink); then the provider's metadata; then, for a Slack
    thread, a link built from the workspace, channel and thread the export recorded. Only http(s) links are ever returned.
    A Zoom or file transcript carries none, so it has none."""
    meta = source_metadata if isinstance(source_metadata, dict) else {}
    provider = meta.get("provider_metadata") if isinstance(meta.get("provider_metadata"), dict) else {}
    for candidate in (source_url, provider.get("share_url"), provider.get("url")):
        if (url := _http_url(candidate)):
            return url
    slack = meta.get("slack") if isinstance(meta.get("slack"), dict) else {}
    workspace, channel, thread = slack.get("workspace"), slack.get("channel"), slack.get("thread_ts")
    if (source_type == "slack" and isinstance(workspace, str) and _SLACK_ID.match(workspace) and isinstance(channel, str)
            and _SLACK_ID.match(channel) and isinstance(thread, str) and _THREAD_TS.match(thread)):
        return f"https://app.slack.com/client/{workspace}/{channel}/thread/{channel}-{thread}"
    return None


def locate_quote(anchors: list[dict], quote: str) -> tuple[dict, int, int]:
    """The anchor passage that holds the quote, and the quote's character range in the original text."""
    for anchor in anchors:
        at = anchor["text"].find(quote) if quote else -1
        if at >= 0:
            return anchor, anchor["start"] + at, anchor["start"] + at + len(quote)
    raise CitationError("The quote is not in its anchor passages")


def moment_citation(row: dict, anchors: list[dict]) -> Citation:
    """`row` is a moment joined to its document and client (rows.MOMENT_SQL); `anchors` are its anchor passages with their text."""
    quote = (row["moment_body"] or {}).get("quote")
    if not row["document_id"] or not anchors or not isinstance(quote, str):
        raise CitationError("The moment has no anchor passages in a document")
    anchor, start, end = locate_quote(anchors, quote)
    return Citation(
        document_id=row["document_id"], document_title=row["document_title"], source_type=row["source_type"],
        call_type=row["call_type"], passage_ids=[a["passage_id"] for a in anchors], start=start, end=end,
        start_ms=anchor.get("start_ms"), end_ms=anchor.get("end_ms"), speaker_label=row["speaker_label"],
        speaker_id=row["speaker_id"], speaker_role=row["speaker_role"], client_id=row["client_id"],
        client_name=row["client_name"], consent_status=row["consent_status"],
        occurred_at=row["occurred_at"] or row["document_occurred_at"],
        recording_url=recording_url(row["source_type"], row["source_url"], row["source_metadata"]), quote=quote)


def chunk_citation(row: dict, passages: list[dict], text: str) -> Citation:
    """`row` is a chunk joined to its document and client (rows.CHUNK_SQL); `passages` are the chunk's passages in the order of
    its references, from the document's passage map; `text` is the original text of the chunk's character range."""
    refs = row["passage_refs"] or []
    if not refs or len(passages) != len(refs) or not text:
        raise CitationError("The chunk has no passages in the original text")
    first = next((p for ref, p in zip(refs, passages, strict=True) if not ref.get("overlap")), passages[0])
    label = first.get("speaker")
    assigned = (row["speaker_map"] or {}).get(label or "") or {}
    timed = [p for p in passages if p.get("start_ms") is not None]
    ends = [p["end_ms"] if p.get("end_ms") is not None else p["start_ms"] for p in timed]
    # Document chunks do not carry a consent judgement: a client who must not be used is do_not_use, everyone else is the
    # conservative default (anonymise), never cleared.
    consent = "do_not_use" if row["client_consent"] == "no_use" else "anonymise"
    return Citation(
        document_id=row["transcript_id"], document_title=row["document_title"], source_type=row["source_type"],
        call_type=row["call_type"], passage_ids=[ref["passage_id"] for ref in refs], start=min(r["start"] for r in refs),
        end=max(r["end"] for r in refs), start_ms=min(p["start_ms"] for p in timed) if timed else None,
        end_ms=max(ends) if ends else None, speaker_label=label, speaker_id=assigned.get("person_id"),
        speaker_role=assigned.get("role") or "unknown", client_id=row["client_id"], client_name=row["client_name"],
        consent_status=consent, occurred_at=row["occurred_at"] or row["document_occurred_at"],
        recording_url=recording_url(row["source_type"], row["source_url"], row["source_metadata"]), quote=text)
