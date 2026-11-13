"""AI output in the frontend's shapes (frontend/src/calls.ts Recap and Brief, types.ts ReviewItem), for the
portfolio build. Everything here is empty while the AI is off, and the screens keep their "not extracted" states.

Dates and sources come from each item's ref (what the prompt showed), never from the model. Call briefs are
presented by services/callprep/present.py.
"""
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select

from backend.models.db import ActionCandidate, AiRun, SourceRecord, SourceVersion
from backend.services.ai.context import day


def evidence_id(record_id) -> str:
    return "kb-" + UUID(str(record_id)).hex[:12] if record_id else ""


def _src(refs: dict, ref: str | None) -> dict:
    target = refs.get(ref or "", {})
    return {"date": target.get("date", ""), "sourceId": evidence_id(target.get("record_id"))}


def recap(run: AiRun, record: SourceRecord, version: SourceVersion, client_id: str) -> dict:
    o = run.output
    return {
        "id": "r-" + run.id.hex[:12], "clientId": client_id, "date": day(record.occurred_at),
        "title": version.attributes.get("title") or "Meeting", "type": o.get("call_type_guess", "other"),
        "transcript": True, "sourceId": evidence_id(record.id),
        "decisions": [d["text"] for d in o.get("decisions", [])],
        "commitments": [{"text": c["text"], "who": c.get("owner_name") or c["owner_side"],
                         "when": c.get("due_date") or c.get("due_phrase") or "No date agreed",
                         "status": "In register" if c.get("matches_action") else "Proposed"}
                        for c in o.get("commitments", [])],
        "answered": [f"{a['question']} (answered: {a['answer']})" for a in o.get("answered", [])],
        "covered": o.get("covered", []), "email": o.get("recap_email", ""),
    }


def moments(run: AiRun, client_id: str) -> list[dict]:
    """History moments: date and lane from the first ref, sources from all of them (never from the model)."""
    out = []
    for i, m in enumerate(run.output.get("moments", [])):
        targets = [run.refs[r] for r in m["refs"] if r in run.refs]
        if not targets:
            continue
        sources = [t.get("evidence") or evidence_id(t.get("record_id")) for t in targets]
        out.append({"id": f"mo-{run.id.hex[:8]}-{i}", "clientId": client_id, "date": targets[0].get("date", ""),
                    "lane": targets[0].get("lane", "Communication"), "kind": m["kind"], "title": m["title"], "why": m["why"],
                    "sourceIds": [x for x in dict.fromkeys(sources) if x]})
    return out


def review_item(c: ActionCandidate, run: AiRun, client_id: str) -> dict:
    origin = "Gmail" if run.subject_kind == "email_batch" else "Meeting"
    return {
        # The full id: an admin's decision is posted back with it.
        "id": "ai-" + c.id.hex, "reason": "AI proposal", "clientId": client_id, "origin": origin,
        "explanation": f"Proposed by the KB from {'an email' if origin == 'Gmail' else 'a meeting'} on {day(c.created_at)}."
                       + ("" if c.verified else " The quote wasn't found word for word in the source: check it."),
        "title": c.title, "author": c.owner_name or "", "date": day(c.created_at), "quote": c.quote,
        "suggestedOwner": c.owner_name or "", "suggestedDue": c.due_date.isoformat() if c.due_date else "",
        "side": c.owner_side or "WIA",
    }


def approved_action(c: ActionCandidate, run: AiRun, client_id: str) -> dict:
    """An approved proposal, as an Action Hub action (frontend types.ts Action). Same id as its review item."""
    origin = "Gmail" if run.subject_kind == "email_batch" else "Meeting"
    approved = day(c.decided_at)
    return {
        "id": "ai-" + c.id.hex, "clientId": client_id, "title": c.title, "owner": c.owner_name or "",
        "due": c.due_date.isoformat() if c.due_date else "", "status": "Open", "side": c.owner_side or "WIA",
        "acknowledged": False, "sourceId": evidence_id(c.source_record_id), "origin": origin, "quote": c.quote,
        "note": f"Proposed by the KB from {'an email' if origin == 'Gmail' else 'a meeting'}; approved by {c.decided_by}.",
        "assignedOn": approved if c.owner_name else None, "lastActivity": approved, "verifyRequired": False,
        "history": [{"date": day(c.created_at), "text": f"Proposed by the KB from {'an email' if origin == 'Gmail' else 'a meeting'}"},
                    {"date": approved, "text": f"Approved by {c.decided_by}"}],
    }


def load(s, slugs: dict) -> dict:
    """Everything AI for the build, by business id: {"recaps": [...], "review": [...], "moments": [...], "actions": [approved proposals]}. Three queries plus one per current digest, whatever the number of clients."""
    out = defaultdict(lambda: {"recaps": [], "review": [], "moments": [], "actions": []})
    runs = s.execute(select(AiRun).where(AiRun.is_current, AiRun.state == "succeeded")).scalars().all()
    for run in runs:
        if run.business_id not in slugs:
            continue
        if run.skill == "meeting_digest":
            record = s.get(SourceRecord, UUID(run.subject_id))
            version = s.get(SourceVersion, record.current_version_id)
            out[run.business_id]["recaps"].append(recap(run, record, version, slugs[run.business_id]))
        elif run.skill == "history_moments":
            out[run.business_id]["moments"] += moments(run, slugs[run.business_id])
    for c, run in s.execute(select(ActionCandidate, AiRun).join(AiRun, AiRun.id == ActionCandidate.run_id)
                            .where(ActionCandidate.kind == "new", ActionCandidate.status.in_(("proposed", "approved")))
                            .order_by(ActionCandidate.created_at)).all():
        if c.business_id in slugs:  # proposed: waits in the admins' review; approved: an Action Hub action
            if c.status == "proposed":
                out[c.business_id]["review"].append(review_item(c, run, slugs[c.business_id]))
            else:
                out[c.business_id]["actions"].append(approved_action(c, run, slugs[c.business_id]))
    return out
