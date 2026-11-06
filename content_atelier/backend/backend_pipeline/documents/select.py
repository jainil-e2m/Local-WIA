"""Documents chosen by date window or explicit set, never by `week_id` (plan 1.B13).

A document is selectable when it is included, normalised, and not a duplicate of another. A window takes the dated ones
whose occurrence falls in it (`window_start <= occurred_at < window_end`); an explicit set takes exactly the named ones
(including undated ones, which no window can reach). The week a document was once admitted in plays no part.

`submit_window` turns a selection into a cycle run: the run freezes the chosen documents (id, hash and view hash), queues
extraction, and marks each document's extraction status. The cycle container (`weeks` row) is named by the window.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

# A live document is read only as its source's current, undeleted revision: an edited Slack message or a re-published
# Fathom transcript is a new revision of one source (a version, not a copy, so no canonical link), and a message deleted at
# the source is never read again. Documents that came from no intake source (files, the backfill, the Slack export) pass.
CURRENT_REVISION = """NOT EXISTS (SELECT 1 FROM intake_revisions r JOIN intake_sources s USING (source_id)
    WHERE r.transcript_id = transcripts.transcript_id AND (s.latest_revision_id IS DISTINCT FROM r.revision_id OR s.status = 'deleted'))"""
SELECTABLE = "included AND normalised_at IS NOT NULL AND canonical_document_id IS NULL AND " + CURRENT_REVISION


def by_window(conn, window_start: datetime, window_end: datetime, *, pending_only: bool = False) -> list[dict]:
    """Included, normalised, non-duplicate documents that occurred in [window_start, window_end), oldest first."""
    if window_end <= window_start:
        raise ValueError("A window ends after it starts")
    for value in (window_start, window_end):
        if value.tzinfo is None:
            raise ValueError("A window needs explicit time zones")
    return conn.execute(f"""SELECT * FROM transcripts WHERE {SELECTABLE} AND occurred_at >= %s AND occurred_at < %s
        {"AND extraction_status IN ('pending','failed')" if pending_only else ""} ORDER BY occurred_at, transcript_id""",
                        (window_start, window_end)).fetchall()


def by_set(conn, transcript_ids: list[str]) -> list[dict]:
    """Exactly the named documents; one that is not selectable is an error that says why (never silently dropped)."""
    if not transcript_ids:
        raise ValueError("Name at least one document")
    rows = {r["transcript_id"]: r for r in conn.execute("SELECT * FROM transcripts WHERE transcript_id=ANY(%s)", (list(transcript_ids),))}
    stale = {r["transcript_id"] for r in conn.execute(
        f"SELECT transcript_id FROM transcripts WHERE transcript_id=ANY(%s) AND NOT ({CURRENT_REVISION})", (list(transcript_ids),))}
    for transcript_id in transcript_ids:
        row = rows.get(transcript_id)
        if row is None:
            raise ValueError(f"Document {transcript_id} does not exist")
        if row["normalised_at"] is None:
            raise ValueError(f"Document {transcript_id} has not been normalised yet")
        if row["canonical_document_id"]:
            raise ValueError(f"Document {transcript_id} is a copy of {row['canonical_document_id']}; select that one")
        if not row["included"]:
            raise ValueError(f"Document {transcript_id} is excluded: {row['exclusion_reason']}")
        if transcript_id in stale:
            raise ValueError(f"Document {transcript_id} is a superseded or deleted revision of a live source; select its current revision")
    return sorted(rows.values(), key=lambda r: (r["occurred_at"] or datetime.max.replace(tzinfo=UTC), r["transcript_id"]))


def container_week(documents: list[dict], window_start: datetime | None = None) -> tuple[str, date]:
    """The cycle container a selection runs in: the seven days from the window's start (a set uses its latest document's day)."""
    if window_start is not None:
        start = window_start.astimezone(UTC).date()
    else:
        dated = [d["occurred_at"] for d in documents if d.get("occurred_at")]
        start = (max(dated) if dated else datetime.now(UTC)).astimezone(UTC).date()
    return "week_" + start.isoformat(), start


def submit_window(repo, models=None, *, window_start: datetime | None = None, window_end: datetime | None = None,
                  transcript_ids: list[str] | None = None, mode: str = "replay", actor: str = "local-cli", **options) -> dict:
    """Select documents by window (or set) and queue their extraction and the rest of the cycle."""
    from ..repository import insert
    if (window_start is None) == (transcript_ids is None):
        raise ValueError("Select by a date window or by an explicit set of documents, not both and not neither")
    with repo.connection() as conn:
        if transcript_ids is None:
            if window_end is None:
                window_end = window_start + timedelta(days=7)
            documents = by_window(conn, window_start, window_end)
            kind = "window"
        else:
            documents, kind = by_set(conn, transcript_ids), "set"
        if not documents:
            raise ValueError("No included, normalised documents fall in that window")
        week_id, start = container_week(documents, window_start)
        insert(conn, "weeks", {"week_id": week_id, "week_start": start, "week_end": start + timedelta(days=6)}, conflict=True)
    if kind == "window":
        # The window is recorded with the run, so a call that arrives after this cycle is listed for the next window (O25).
        options.setdefault("extra_refs", {"window": {"start": window_start.astimezone(UTC).isoformat(),
                                                     "end": window_end.astimezone(UTC).isoformat()}})
    result = repo.submit(week_id, mode, actor=actor, models=models, documents=documents, selected_by=kind, **options)
    return {**result, "week_id": week_id, "selected_by": kind, "documents": [d["transcript_id"] for d in documents]}


def mark_extraction(conn, run_id: str, status: str, job: dict | None = None) -> None:
    """Keep each selected document's extraction status in step with its run's extraction job. A job that names its document
    (a document's own extraction, 2.B2) moves only that document; a weekly run's job moves every document the run read, except
    that a failure leaves the documents it already extracted as completed."""
    if job is not None and job.get("transcript_id"):
        conn.execute("UPDATE transcripts SET extraction_status=%s WHERE transcript_id=%s AND included", (status, job["transcript_id"]))
        return
    run = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (run_id,)).fetchone()
    ids = [t["id"] for t in (run["input_refs"] or {}).get("transcripts", [])] if run else []
    if ids:
        # A weekly run that fails keeps the documents it did extract as extracted: only the rest are failed (N8).
        keep = " AND extraction_status<>'completed'" if status == "failed" else ""
        conn.execute(f"UPDATE transcripts SET extraction_status=%s WHERE transcript_id=ANY(%s) AND included{keep}", (status, ids))
