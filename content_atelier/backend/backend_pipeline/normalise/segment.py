"""Segmentation v2 (plan 1.B6): chunks that say what they are.

Each chunk starts with a header naming the call, its date, its type, the client and the speakers with their roles, so a
chunk found out of context still says whose words they are and when they were said. Consecutive whole turns fill a chunk
up to a size and a pause limit, and the last turn of one chunk opens the next (a one-turn overlap), so a question and its
answer are never split across a boundary without either appearing on both sides. A quotation is never cut: an unusually
large turn stays a single chunk.

A chunk's `content_hash` covers its text and its passage references exactly as before, so the encoding pipeline's integrity
checks apply unchanged. A chunk carries the date, the speaker roles and (after encoding) the embedding model.
"""
from __future__ import annotations

from ..store import canonical_hash

SEGMENTATION_VERSION = "v2"
CALL_LABELS = {"client_1to1": "Client call", "office_hours": "Office hours", "workshop": "Workshop", "prospect": "Prospect call",
               "internal": "Internal call", "vendor": "Vendor call", "fragment": "Fragment", "slack_thread": "Slack thread",
               "other": "Call"}
ROLE_LABELS = {"staff": "WIA", "client": "client", "prospect": "prospect", "vendor": "vendor", "outside": "outside",
               "ai_agent": "AI agent", "unknown": "role unknown"}
# The conservative embedding input bound the encoder enforces (chunk_encoding.chunk_view), less room for the header.
BYTE_LIMIT = 7600


def header_lines(document: dict, context: dict, speakers: list[dict]) -> list[str]:
    """The header: call, date, type, client, speakers with roles. `context` carries call_type, client_name and the date source."""
    when = document.get("occurred_at")
    lines = [f"Call: {document['title']}",
             "Date: " + (when.date().isoformat() if when else "unknown"),
             "Type: " + CALL_LABELS.get(context.get("call_type") or "other", "Call")]
    if context.get("client_name"):
        lines.append(f"Client: {context['client_name']}")
    if speakers:
        lines.append("Speakers: " + ", ".join(f"{s['name']} ({ROLE_LABELS.get(s['role'], s['role'])})" for s in speakers))
    return lines


def chunk_document(document: dict, context: dict, mapping: dict | None = None, *, max_characters: int = 2400,
                   gap_ms: int = 90_000) -> list[dict]:
    """v2 chunks for one document: id, text, passage references, hash, header, date, speaker roles and version.

    `mapping` is the document's speaker map (label -> assignment); without one every speaker's role is unknown."""
    mapping = mapping or {}
    text = document["original_text"]
    turns = [(p, text[p["start"]:p["end"]]) for p in document["passage_map"]]
    groups, group, size, last = [], [], 0, None
    for p, value in turns:
        gap = last is not None and p.get("start_ms") is not None and p["start_ms"] - last > gap_ms
        if group and (size + len(value) > max_characters or gap):
            groups.append(group)
            group, size = [], 0
        group.append((p, value))
        size += len(value)
        last = p["end_ms"] if p.get("end_ms") is not None else p.get("start_ms", last)
    if group:
        groups.append(group)
    previous: tuple | None = None
    result = []
    for index, members in enumerate(groups):
        # One-turn overlap: the previous chunk's last turn opens this one (unless the pause was a topic break or it would
        # push the chunk past the encoder's bound).
        overlap = previous if previous is not None and index > 0 and not _paused(previous[0], members[0][0], gap_ms) else None
        speakers = _speakers([m for m in ([overlap] if overlap else []) + members], mapping)
        header = "\n".join(header_lines(document, context, speakers))
        turns_in = ([overlap] if overlap else []) + members
        body = "\n".join(v for _, v in turns_in)
        if overlap and len((header + "\n\n" + body).encode("utf-8")) > BYTE_LIMIT:
            turns_in, overlap = members, None
            speakers = _speakers(members, mapping)
            header = "\n".join(header_lines(document, context, speakers))
            body = "\n".join(v for _, v in members)
        contextual = header + "\n\n" + body
        refs = [{"passage_id": p["passage_id"], "start": p["start"], "end": p["end"]} for p, _ in turns_in]
        if overlap:
            refs[0]["overlap"] = True
        digest = canonical_hash({"text": contextual, "passages": refs})
        result.append({"chunk_id": "chunk_" + canonical_hash([document["transcript_id"], digest, SEGMENTATION_VERSION])[:24],
                       "chunk_text": contextual, "passage_refs": refs, "content_hash": digest, "header": header,
                       "occurred_at": document.get("occurred_at"), "speaker_roles": speakers,
                       "segmentation_version": SEGMENTATION_VERSION})
        previous = members[-1]
    return result


def _paused(a: dict, b: dict, gap_ms: int) -> bool:
    end = a.get("end_ms") if a.get("end_ms") is not None else a.get("start_ms")
    return end is not None and b.get("start_ms") is not None and b["start_ms"] - end > gap_ms


def _speakers(members, mapping: dict) -> list[dict]:
    seen: dict[str, dict] = {}
    for p, _ in members:
        label = p.get("speaker")
        if label and label not in seen:
            assigned = mapping.get(label, {})
            seen[label] = {"name": label, "role": assigned.get("role", "unknown"), "inferred": bool(assigned.get("inferred", False))}
    return list(seen.values())


def retire_and_store(conn, document: dict, chunks: list[dict], *, search_text=lambda text: text) -> dict:
    """Make `chunks` the document's current chunks: insert the new ones, retire the others (they stay readable).

    Idempotent: chunks already stored stay; nothing is deleted and no vector is touched."""
    from psycopg.types.json import Jsonb
    wanted = {c["chunk_id"] for c in chunks}
    existing = {r["chunk_id"]: r for r in conn.execute(
        "SELECT chunk_id,is_current FROM transcript_chunks WHERE transcript_id=%s", (document["transcript_id"],))}
    added = 0
    for chunk in chunks:
        searchable = search_text(chunk["chunk_text"])
        if chunk["chunk_id"] not in existing:
            conn.execute("""INSERT INTO transcript_chunks(chunk_id,transcript_id,chunk_text,passage_refs,content_hash,header,occurred_at,
                speaker_roles,segmentation_version,is_current,search_text) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,true,%s)""",
                         (chunk["chunk_id"], document["transcript_id"], chunk["chunk_text"], Jsonb(chunk["passage_refs"]),
                          chunk["content_hash"], chunk["header"], chunk["occurred_at"], Jsonb(chunk["speaker_roles"]),
                          chunk["segmentation_version"], None if searchable == chunk["chunk_text"] else searchable))
            added += 1
        elif not existing[chunk["chunk_id"]]["is_current"]:
            conn.execute("UPDATE transcript_chunks SET is_current=true WHERE chunk_id=%s", (chunk["chunk_id"],))
    retired = conn.execute("UPDATE transcript_chunks SET is_current=false WHERE transcript_id=%s AND is_current AND chunk_id<>ALL(%s)",
                           (document["transcript_id"], list(wanted))).rowcount
    return {"added": added, "retired": retired, "current": len(wanted)}
