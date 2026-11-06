"""Duplicate documents: a stored canonical link (plan 1.B10).

The same call can arrive twice: a live Fathom document and its backfilled copy (same recording, bytes that differ in
whitespace or key order), or one file imported from two places. Copies are documents with the same text (equal once
whitespace and case are collapsed). Revisions of one live source (an edited Slack message, a re-published recording) are
versions of a single source, not copies, however alike their text: the intake already tracks which is current.

A second recording of one meeting is a copy too (Phase N7: the live collector brings every note-taker's recording, and in
October 11 of 39 meetings had two): its text differs, so it is found as the backfill finds it (fathom_backfill.same_call),
a document from another source that started within minutes and shares most of its wording.

One document in each group is canonical; the others point to it (`canonical_document_id`), are excluded with the reason
"Duplicate of ..." (or "Another recording of ..."), and need no extraction, so the strategist never sees one call twice. The canonical choice prefers what
other work already cites: a document admitted into a week, then one whose scenes were extracted, then the earliest.
Nothing is deleted; a copy can still be read and the link can be undone by a person.
"""
from __future__ import annotations

import hashlib
import re


def text_key(original_text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", original_text).strip().lower().encode()).hexdigest()


def _rank(row: dict):
    """Lower sorts first: admitted into a week, extracted, then earliest ingested."""
    return (0 if row["week_id"] else 1, 0 if row["extraction_status"] == "completed" else 1, row["ingested_at"], row["transcript_id"])


def group_of(conn, transcript_id: str) -> list[dict]:
    """Every document that is the same document as this one (including itself), canonical candidates first."""
    row = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (transcript_id,)).fetchone()
    if row is None:
        raise LookupError("Document not found")
    members = {r["transcript_id"]: r for r in conn.execute(
        """SELECT transcript_id,week_id,source_type,upstream_id,original_text,extraction_status,ingested_at,canonical_document_id,
                  title,included,exclusion_reason,classification,source_metadata->'intake'->>'source_id' AS intake_source
           FROM transcripts WHERE transcript_id=%s OR length(original_text) BETWEEN %s AND %s""",
        (transcript_id, max(0, len(row["original_text"]) - 64), len(row["original_text"]) + 64)).fetchall()}
    key = text_key(row["original_text"])
    mine = members[transcript_id]["intake_source"]
    same = [r for r in members.values() if r["transcript_id"] == transcript_id or (
        text_key(r["original_text"]) == key and not (mine and r["intake_source"] == mine))]
    known = {r["transcript_id"] for r in same}
    same += [r for r in recordings_of_the_same_meeting(conn, row, mine) if r["transcript_id"] not in known]
    return sorted(same, key=_rank)


def recordings_of_the_same_meeting(conn, row: dict, intake_source: str | None) -> list[dict]:
    """Other documents of this meeting from another source: started within SAME_CALL_START, sharing most of the wording."""
    from .fathom_backfill import SAME_CALL_SHARE, SAME_CALL_START, same_call
    if not row["occurred_at"]:
        return []
    found = []
    for r in conn.execute("""SELECT transcript_id,week_id,source_type,upstream_id,original_text,extraction_status,ingested_at,
            canonical_document_id,title,included,exclusion_reason,classification,source_metadata->'intake'->>'source_id' AS intake_source
            FROM transcripts WHERE transcript_id<>%s AND occurred_at BETWEEN %s AND %s
              AND (canonical_document_id IS NULL OR canonical_document_id=%s)""",
                          (row["transcript_id"], row["occurred_at"] - SAME_CALL_START, row["occurred_at"] + SAME_CALL_START,
                           row["transcript_id"])).fetchall():
        if (intake_source and r["intake_source"] == intake_source) or r["upstream_id"] == row["upstream_id"]:
            continue  # a revision of one source is a version, not a copy
        if same_call(row["original_text"], r["original_text"]) >= SAME_CALL_SHARE:
            found.append({**r, "second_recording": True})
    return found


def link(conn, transcript_id: str) -> str | None:
    """Make the group's canonical document the target of every other member's link. Returns this document's canonical id
    when it is a copy, else None. A person's earlier choice (a document they excluded or included) is respected."""
    group = group_of(conn, transcript_id)
    if len(group) < 2:
        return None
    canonical = group[0]
    for member in group[1:]:
        if (member.get("classification") or {}).get("unlinked_by"):
            continue
        person = (member.get("classification") or {}).get("method") == "person"
        keep_inclusion = person and member["included"]
        second = member.get("second_recording") or canonical.get("second_recording")
        reason = (f"Another recording of the same meeting as {canonical['title']} ({canonical['transcript_id']})." if second
                  else f"Duplicate of {canonical['title']} ({canonical['transcript_id']}).")
        conn.execute("""UPDATE transcripts SET canonical_document_id=%s,
            included=CASE WHEN %s THEN included ELSE false END,
            exclusion_reason=CASE WHEN %s THEN exclusion_reason ELSE %s END,
            extraction_status=CASE WHEN %s THEN extraction_status ELSE 'not_applicable' END
            WHERE transcript_id=%s""",
                     (canonical["transcript_id"], keep_inclusion, keep_inclusion, reason, keep_inclusion, member["transcript_id"]))
    if canonical["canonical_document_id"]:
        conn.execute("UPDATE transcripts SET canonical_document_id=NULL WHERE transcript_id=%s", (canonical["transcript_id"],))
    return canonical["transcript_id"] if canonical["transcript_id"] != transcript_id else None


def unlink(conn, transcript_id: str, *, actor: str) -> None:
    """A person says this is not a copy: remove the link and include it again (its type decides inclusion on the next
    normalisation)."""
    row = conn.execute("SELECT canonical_document_id FROM transcripts WHERE transcript_id=%s FOR UPDATE", (transcript_id,)).fetchone()
    if row is None or not row["canonical_document_id"]:
        raise ValueError("This document is not linked to a canonical copy")
    conn.execute("""UPDATE transcripts SET canonical_document_id=NULL,included=true,exclusion_reason=NULL,
        extraction_status='pending',classification=COALESCE(classification,'{}'::jsonb)||jsonb_build_object('unlinked_by',%s::text)
        WHERE transcript_id=%s""", (actor, transcript_id))
