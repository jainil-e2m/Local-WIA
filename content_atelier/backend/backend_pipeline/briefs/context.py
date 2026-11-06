"""Context and attested facts at either gate (5.B7, R57; interface 2).

A reviewer adds free text to a card at Gate 1 (`POST /angles/{id}/context`) or to a brief at Gate 2
(`POST /briefs/{id}/context`), as one of three kinds:

- `context`: guidance about the piece. It reaches the writer; it is never evidence.
- `attested_fact`: a fact an approver states as true. It is evidence: it enters the brief's claims ledger as `attested`
  with the person and the date, may appear in copy, and is shown as attested at Gate 2 (ledger_v3.attest). Only an
  approver may attest.
- `paraphrase`: a client's words in the reviewer's words. It supports a statement as an attested fact does, and is never
  quoted (validation_v3.paraphrase_checks blocks copy that puts it in quotation marks).

Storage needs no migration. Every item is an event on the card's or brief's run (`pipeline_events`, event type
`gate_context`): the audit record, with the text, kind, author and actor. A card's items carry across its versions and
into its brief's writer input when the brief is queued (workflow._queue freezes them on the run). An item added at Gate 2
also makes a new brief version whose `content_body.context_items` holds it, so the ledger and the approval bind to it.
"""
from __future__ import annotations

from datetime import UTC, datetime

from ..repository import identifier

KINDS = ("context", "attested_fact", "paraphrase")
EVENT = "gate_context"
MAX_TEXT = 4000


def _clean(kind: str, text: str, author: str | None, actor: str) -> tuple[str, str]:
    if kind not in KINDS:
        raise ValueError("Context kind must be one of: " + ", ".join(KINDS))
    text = (text or "").strip()
    if not text or len(text) > MAX_TEXT:
        raise ValueError(f"Context needs text of 1 to {MAX_TEXT} characters")
    author = (author or "").strip() or actor
    if len(author) > 200:
        raise ValueError("Author is too long")
    return text, author


def item(kind: str, text: str, author: str, gate: str) -> dict:
    return {"id": identifier("context"), "kind": kind, "text": text, "author": author, "gate": gate,
            "created_at": datetime.now(UTC).isoformat()}


def lineage(conn, angle_id: str) -> list[str]:
    """The card version and every version it supersedes: context given on an earlier version stays with the card."""
    ids, seen, current = [], set(), angle_id
    while current and current not in seen:
        seen.add(current)
        ids.append(current)
        row = conn.execute("SELECT supersedes_id FROM content_angles WHERE angle_id=%s", (current,)).fetchone()
        current = row.get("supersedes_id") if row else None
    return ids


def card_items(conn, angle_id: str) -> list[dict]:
    """The context given on a card at Gate 1, oldest first."""
    rows = conn.execute("""SELECT details FROM pipeline_events WHERE event_type=%s AND details->>'gate'='gate_one'
        AND details->>'angle_id'=ANY(%s) ORDER BY created_at,event_id""", (EVENT, lineage(conn, angle_id))).fetchall()
    return [{k: r["details"][k] for k in ("id", "kind", "text", "author", "gate", "created_at")} for r in rows]


def for_writer(conn, angle_id: str, carried=()) -> list[dict]:
    """The items a brief run is queued with: those already in the brief (a refresh), then the card's not yet in it."""
    out = list(carried)
    ids = {i["id"] for i in out}
    return out + [i for i in card_items(conn, angle_id) if i["id"] not in ids]


def view(conn, row: dict) -> list[dict]:
    """A brief's context items for the screen: those in this version (`in_brief`), then the card's given since, which the
    next refresh will carry."""
    own = [{**i, "in_brief": True} for i in row["content_body"].get("context_items") or []]
    ids = {i["id"] for i in own}
    return own + [{**i, "in_brief": False} for i in card_items(conn, row["angle_id"]) if i["id"] not in ids]


def writer_view(items) -> list[dict]:
    """The items as the writer reads them (`reviewer_context`): what each kind allows, who gave it and when."""
    use = {"context": "Guidance from the reviewer; not evidence",
           "attested_fact": "A fact the approver states as true: you may state it in copy; it overrides the call where they differ",
           "paraphrase": "The client's words in the reviewer's words: use what it says, never in quotation marks"}
    return [{"kind": i["kind"], "text": i["text"], "given_by": i["author"], "on": str(i["created_at"])[:10], "use": use[i["kind"]]}
            for i in items]


def add_to_angle(repo, angle_id: str, kind: str, text: str, actor, author: str | None = None) -> dict:
    """Gate 1: context on a card. An editor adds context or a paraphrase; only an approver attests a fact."""
    from .. import gate_one
    gate_one.require(repo, actor, "decide" if kind == "attested_fact" else "edit")
    text, author = _clean(kind, text, author, str(actor))
    with repo.connection() as conn:
        angle = conn.execute("SELECT angle_id,run_id FROM content_angles WHERE angle_id=%s", (angle_id,)).fetchone()
        if not angle:
            raise ValueError("Angle not found")
        value = item(kind, text, author, "gate_one")
        repo.event(conn, angle["run_id"], EVENT, "Context added at Gate 1",
                   details={**value, "angle_id": angle_id, "actor": str(actor)})
        return {**value, "angle_id": angle_id, "context_items": card_items(conn, angle_id)}


def add_to_brief(repo, brief_id: str, kind: str, text: str, actor, author: str | None = None) -> dict:
    """Gate 2: context on a brief, as a new brief version. An attested fact or a paraphrase settles the statements of the
    copy that say what it says, at once, with no model call (validation_v3.rebuild); a plain note waits for a refresh."""
    from . import gate_two
    gate_two.authorize(repo, actor, "approve" if kind == "attested_fact" else "edit")
    text, author = _clean(kind, text, author, str(actor))
    with repo.connection() as conn:
        current = conn.execute("SELECT content_hash FROM content_briefs WHERE brief_id=%s", (brief_id,)).fetchone()
        if not current:
            raise ValueError("Brief not found")
        row = gate_two.locked(conn, brief_id, current["content_hash"])
        if not gate_two.is_v2(row):
            raise ValueError("Context at Gate 2 applies to version 2 and 3 briefs; add it to the card for a version 1 brief")
        value = item(kind, text, author, "gate_two")
        body = row["content_body"]
        body["context_items"] = [*(body.get("context_items") or []), value]
        if gate_two.is_v3(row):
            from .validation_v3 import rebuild
            body["document"]["body"] = rebuild(row, {}, person_fields=())
        body["review"]["findings"] = gate_two.findings_v2(row, conn=conn)
        result = gate_two.replace(repo, conn, row, actor, change={"kind": "context", "context_kind": kind, "text": text,
                                                                  "author": author})
        repo.event(conn, body["provenance"]["run_id"], EVENT, "Context added at Gate 2",
                   details={**value, "angle_id": row["angle_id"], "brief_id": brief_id,
                            "resulting_brief_id": result["brief_id"], "actor": str(actor)})
        return {**result, "context_id": value["id"]}
