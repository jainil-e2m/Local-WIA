"""Archiving a week (Phase N10, the owner's direction of 25 October 2026: the app shows only content that meets WIA's standard).

A week whose cards, briefs and packs were superseded (the same calls run again under a newer configuration) or were early
diagnostics that do not meet the standard is archived, never deleted: its rows stay as the record, what cites them still
resolves, and `GET /weeks` leaves it out of the app's week lists unless asked (`?include_archived=true`). Who archived it,
when and why are kept on the week (`coverage_notes.archived`). Archiving again is a no-op; `restore` brings a week back.

    python -m backend_pipeline.storage_cli weeks archive --week-id <id> --reason "<why>" --actor <approver>
    python -m backend_pipeline.storage_cli weeks restore --week-id <id> --actor <approver>
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

ARCHIVED = "archived"


def archive(conn, week_id: str, *, reason: str, actor: str) -> dict:
    if not (reason or "").strip():
        raise ValueError("Say why the week is archived")
    row = conn.execute("SELECT week_id,status,coverage_notes FROM weeks WHERE week_id=%s FOR UPDATE", (week_id,)).fetchone()
    if row is None:
        raise LookupError(f"Week not found: {week_id}")
    if row["status"] == ARCHIVED:
        return {"week_id": week_id, "status": ARCHIVED, "changed": False}
    notes = dict(row["coverage_notes"] or {})
    notes["archived"] = {"by": actor, "at": datetime.now(UTC).isoformat(), "reason": reason.strip(), "status_before": row["status"]}
    conn.execute("UPDATE weeks SET status=%s,coverage_notes=%s WHERE week_id=%s", (ARCHIVED, json.dumps(notes), week_id))
    return {"week_id": week_id, "status": ARCHIVED, "changed": True, "status_before": row["status"]}


def restore(conn, week_id: str, *, actor: str) -> dict:
    row = conn.execute("SELECT status,coverage_notes FROM weeks WHERE week_id=%s FOR UPDATE", (week_id,)).fetchone()
    if row is None:
        raise LookupError(f"Week not found: {week_id}")
    if row["status"] != ARCHIVED:
        return {"week_id": week_id, "status": row["status"], "changed": False}
    notes = dict(row["coverage_notes"] or {})
    before = (notes.get("archived") or {}).get("status_before") or "review"
    notes["restored"] = {"by": actor, "at": datetime.now(UTC).isoformat()}
    conn.execute("UPDATE weeks SET status=%s,coverage_notes=%s WHERE week_id=%s", (before, json.dumps(notes), week_id))
    return {"week_id": week_id, "status": before, "changed": True}
