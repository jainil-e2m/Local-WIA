"""An admin's decision on an AI-proposed action: approve it (as proposed, or with the admin's edits) or reject it.
Only approved proposals reach the Action Hub; a proposal is decided once. Nothing is written to ClickUp.

shortcut: the server trusts the admin name the app sends (the shared team login can't tell people apart),
so anyone with the team password could call this. Check the signed-in person's role here once named sign-in exists."""
from datetime import date
from uuid import UUID

from backend.models.db import ActionCandidate, AuditEvent
from backend.models.db.base import utcnow
from backend.services.read_models import portfolio

EDITABLE = ("title", "owner", "due", "side")
MAX_TITLE, MAX_OWNER = 300, 200


class DecisionError(ValueError):
    """The request can't be applied; the message says why, in words the UI can show."""


def clean_edits(edits: dict) -> dict:
    out = {}
    if "title" in edits:
        title = " ".join((edits["title"] or "").split())
        if not title or len(title) > MAX_TITLE:
            raise DecisionError(f"give the action a title (up to {MAX_TITLE} characters)")
        out["title"] = title
    if "owner" in edits:
        owner = (edits["owner"] or "").strip()
        if len(owner) > MAX_OWNER:
            raise DecisionError("that owner name is too long")
        out["owner_name"] = owner or None
    if "due" in edits:
        try:
            out["due_date"] = date.fromisoformat(edits["due"]) if edits["due"] else None
        except (TypeError, ValueError):
            raise DecisionError("give the due date as YYYY-MM-DD") from None
    if "side" in edits:
        if edits["side"] not in ("WIA", "Client"):
            raise DecisionError("the action is either WIA's or the client's")
        out["owner_side"] = edits["side"]
    return out


def decide(s, ref: str, approve: bool, edits: dict, *, actor: str, reason: str = "") -> dict:
    """Approve (applying `edits` first) or reject one proposed new action. Returns what the UI needs."""
    if unknown := set(edits) - set(EDITABLE):
        raise DecisionError(f"these can't be edited: {', '.join(sorted(unknown))}")
    candidate = find(s, ref)
    if candidate.kind != "new":
        raise DecisionError("only proposed new actions are decided here")
    if candidate.status != "proposed":
        raise DecisionError(f"this proposal was already {candidate.status}"
                            + (f" by {candidate.decided_by}" if candidate.decided_by else ""))
    changes = clean_edits(edits) if approve else {}
    before = {k: _plain(getattr(candidate, k)) for k in changes}
    changes = {k: v for k, v in changes.items() if before[k] != _plain(v)}
    for k, v in changes.items():
        setattr(candidate, k, v)
    candidate.status = "approved" if approve else "rejected"
    candidate.decided_by, candidate.decided_at = actor, utcnow()
    s.add(AuditEvent(actor=actor, action=f"action_candidate.{candidate.status}", target_type="action_candidate",
                     target_id=str(candidate.id),
                     details={"edited": {k: {"from": before[k], "to": _plain(v)} for k, v in changes.items()},
                              **({"reason": reason[:200]} if reason else {})}))
    portfolio.request_refresh(s)
    return {"id": ref, "status": candidate.status, "edited": sorted(changes)}


def find(s, ref: str) -> ActionCandidate:
    """By the review item id: "ai-" + the candidate id's hex. Locked, so two admins can't decide it at once."""
    try:
        candidate = s.get(ActionCandidate, UUID(hex=ref.removeprefix("ai-")), with_for_update=True)
    except ValueError:
        candidate = None
    if candidate is None:
        raise DecisionError("unknown proposal")
    return candidate


def _plain(value):
    return value.isoformat() if isinstance(value, date) else value
