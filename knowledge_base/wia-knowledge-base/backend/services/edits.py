"""Shared edits: what people change in the app (Action Hub, client details), saved for everyone.

The KB builds actions and client records from the sources (the portfolio). A person's change is stored here as
only the fields they changed, and the app layers them over the build when it loads, so everyone sees the same
thing. A save happens only when someone presses a button that commits it; nothing is kept in one browser.

- One row per action (`kind="action"`, the action's id) or client (`kind="client"`, its slug).
- `changes` merge into the row field by field; a field set to null goes back to following the KB.
- Every save names the revision it was based on. If someone saved in between, it is refused (409) with the
  current copy, so nobody silently overwrites a colleague.
- An action added in the app is a row with `created: true` and the whole action.
- Edits stay in the KB: nothing is written to ClickUp or Slack (that is the outbound guard's job). An action edit
  of a field ClickUp also sets (status, owner, due, title, side) records what ClickUp said then (`_base`); when
  ClickUp later says something else, the app shows ClickUp's newer value (frontend App.tsx withEdits).

shortcut: the editor's name is the one the app sends (no named sign-in yet), the same limit as AI approvals.
"""
import json
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.models.db import AuditEvent, Business, SharedEdit

ACTION_FIELDS = frozenset({
    "id", "clientId", "title", "owner", "suggestedOwner", "suggestedWhy", "due", "status", "side", "acknowledged",
    "sourceId", "note", "origin", "assignedOn", "ackMethod", "lastActivity", "verifyRequired", "actionType",
    "conflict", "quote", "clickupUrl", "completionBasis", "reportedDone", "verification", "history", "notes",
    "snoozedUntil", "snoozeReason", "priority", "completedOn", "deadlineRequest", "slackPingedAt", "slackChannel",
    "kind", "programme", "recurring", "created",
    "_base"})  # what the source said for each source field when it was edited: a later source change wins again
CLIENT_FIELDS = frozenset({
    "name", "aliases", "category", "location", "owner", "lifecycle", "engagements", "logo", "logoRemoved",
    "logoScale", "logoTint", "editedBy", "editedAt", "coverId", "archived"})
FIELDS = {"action": ACTION_FIELDS, "client": CLIENT_FIELDS}
# A client row can hold an uploaded logo (the app caps it at 2 MB before base64); an action is small.
MAX_BYTES = {"action": 200_000, "client": 3_500_000}
KEY = re.compile(r"^[\w:.\-]{1,100}$")  # 100: the audit log's target id
STATUSES = {"Open", "In progress", "Blocked", "Done", "Verified"}
DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})?$")


class EditError(ValueError):
    """The save is not allowed as sent (unknown field, bad value, too large)."""


class Conflict(Exception):
    """Someone saved this since it was loaded. Carries the current copy."""

    def __init__(self, current: dict):
        super().__init__("changed since it was loaded")
        self.current = current


def present(row: SharedEdit) -> dict:
    return {"kind": row.kind, "key": row.key, "data": row.data, "revision": row.revision,
            "by": row.updated_by, "at": row.updated_at.isoformat()}


def load(s) -> dict:
    """Everything, for the app to layer over the portfolio at start: {"actions": {id: row}, "clients": {slug: row}}."""
    out = {"actions": {}, "clients": {}}
    for row in s.execute(select(SharedEdit)).scalars():
        out[row.kind + "s"][row.key] = present(row)
    return out


def _check(kind: str, key: str, changes: dict, s) -> None:
    if kind not in FIELDS:
        raise EditError("unknown kind")
    if not KEY.match(key):
        raise EditError("bad key")
    if not isinstance(changes, dict) or not changes:
        raise EditError("nothing to save")
    unknown = sorted(set(changes) - FIELDS[kind])
    if unknown:
        raise EditError(f"unknown field: {unknown[0]}")
    if kind == "client" and s.scalar(select(Business.id).where(Business.slug == key)) is None:
        raise EditError("unknown client")
    if kind == "action":
        if "status" in changes and changes["status"] not in STATUSES:
            raise EditError("bad status")
        if "due" in changes and not (isinstance(changes["due"], str) and DATE.match(changes["due"])):
            raise EditError("due must be YYYY-MM-DD or empty")
        if "side" in changes and changes["side"] not in ("WIA", "Client"):
            raise EditError("bad side")
        if changes.get("_base") is not None and not isinstance(changes["_base"], dict):
            raise EditError("_base must be an object")
        client = changes.get("clientId")
        if client is not None and s.scalar(select(Business.id).where(Business.slug == client)) is None:
            raise EditError("unknown client")


def save(s, kind: str, key: str, changes: dict, *, expected_revision: int | None, actor: str) -> dict:
    """Merge `changes` into the row (null removes a field), based on `expected_revision` (None: "I saw no row")."""
    _check(kind, key, changes, s)
    row = s.execute(select(SharedEdit).where(SharedEdit.kind == kind, SharedEdit.key == key)
                    .with_for_update()).scalar_one_or_none()
    if (row.revision if row else None) != expected_revision:
        raise Conflict(present(row) if row else {"kind": kind, "key": key, "data": {}, "revision": None})
    data = {**(row.data if row else {}), **changes}
    data = {k: v for k, v in data.items() if v is not None}
    if len(json.dumps(data)) > MAX_BYTES[kind]:
        raise EditError("too large")
    if row is None:
        row = SharedEdit(kind=kind, key=key, data=data, revision=1, updated_by=actor)
        try:
            with s.begin_nested():  # two first saves at once: the second loses on the unique key, as a conflict
                s.add(row)
                s.flush()
        except IntegrityError:
            current = s.execute(select(SharedEdit).where(SharedEdit.kind == kind, SharedEdit.key == key)).scalar_one()
            raise Conflict(present(current)) from None
    else:
        row.data, row.revision, row.updated_by = data, row.revision + 1, actor
        s.flush()
    # Which fields, never their values: an audit line must not copy client text around.
    s.add(AuditEvent(actor=actor, action=f"edit.{kind}", target_type=kind, target_id=key,
                     details={"fields": sorted(changes), "revision": row.revision}))
    return present(row)
