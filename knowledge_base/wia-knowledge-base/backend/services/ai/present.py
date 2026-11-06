"""AI output in the frontend's shapes (frontend/src/calls.ts Recap and Brief, types.ts ReviewItem), for the
portfolio build. Everything here is empty while the AI is off, and the screens keep their "not extracted" states.

Dates and sources come from each item's ref (what the prompt showed), never from the model. A brief is Stale when
the client's email, Slack or tasks changed after it was built; the "owed" list is the Action Hub's own.
"""
from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select

from backend.models.db import ActionCandidate, AiRun, RecordAssociation, SourceRecord, SourceVersion
from backend.services.ai.context import day

LABELS = {"T": "Fathom transcript", "E": "Gmail", "S": "Slack", "V": "Viktor (attributed)", "A": "Action Hub",
          "C": "Calendar"}
CHANGES = ("gmail_message", "slack_message", "clickup_task")


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


def brief(run: AiRun) -> dict:
    o, refs = run.output, run.refs
    used = sorted({r[0] for r in refs})
    limits = ["Sources: " + ", ".join(LABELS[p] for p in used if p in LABELS)] if used else []
    limits += [f"Clipped to fit: {name.replace('_', ' ')} ({n} older items not shown)"
               for name, n in (run.checks.get("clipped") or {}).items()]
    return {
        "thirty": o.get("thirty", []),
        "since": [{"text": i["text"], **_src(refs, i["ref"])} for i in o.get("since", [])],
        "asks": [{"quote": a["quote"], "who": a["who"], **_src(refs, a["ref"])} for a in o.get("asks", [])],
        "agenda": o.get("agenda", []), "questions": o.get("questions", []), "watch": o.get("watch", []),
        **({"opportunity": {"text": o["opportunity"]["text"], "why": o["opportunity"]["why"],
                            "sourceId": _src(refs, o["opportunity"]["ref"])["sourceId"]}} if o.get("opportunity") else {}),
        "typeBlock": [{"label": t["label"], "value": t["value"]} for t in o.get("type_block", [])],
        "limits": limits, "more": {},
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
        "id": "ai-" + c.id.hex[:12], "reason": "AI proposal", "clientId": client_id, "origin": origin,
        "explanation": f"Proposed by the KB from {'an email' if origin == 'Gmail' else 'a meeting'} on {day(c.created_at)}."
                       + ("" if c.verified else " The quote wasn't found word for word in the source: check it."),
        "title": c.title, "author": c.owner_name or "", "date": day(c.created_at), "quote": c.quote,
        "suggestedOwner": c.owner_name or "", "suggestedDue": c.due_date.isoformat() if c.due_date else "",
        "side": c.owner_side or "WIA",
    }


def load(s, slugs: dict) -> dict:
    """Everything AI for the build, by business id: {"recaps": [...], "briefs": {event record id: (...)},
    "review": [...]}. Three queries plus one per current digest, whatever the number of clients."""
    out = defaultdict(lambda: {"recaps": [], "briefs": {}, "review": [], "moments": []})
    runs = s.execute(select(AiRun).where(AiRun.is_current, AiRun.state == "succeeded")).scalars().all()
    changed = dict(s.execute(select(RecordAssociation.business_id, func.max(SourceRecord.last_observed_at))
                             .join(SourceRecord, SourceRecord.id == RecordAssociation.record_id)
                             .where(RecordAssociation.status == "associated", SourceRecord.record_kind.in_(CHANGES))
                             .group_by(RecordAssociation.business_id)).all())
    for run in runs:
        if run.business_id not in slugs:
            continue
        if run.skill == "meeting_digest":
            record = s.get(SourceRecord, UUID(run.subject_id))
            version = s.get(SourceVersion, record.current_version_id)
            out[run.business_id]["recaps"].append(recap(run, record, version, slugs[run.business_id]))
        elif run.skill == "history_moments":
            out[run.business_id]["moments"] += moments(run, slugs[run.business_id])
        elif run.skill == "call_brief":
            last = changed.get(run.business_id)
            stale = bool(last and last > run.created_at)
            out[run.business_id]["briefs"][UUID(run.subject_id)] = (
                brief(run), run.created_at, "Stale" if stale else "Ready",
                f"Built {day(run.created_at)}. Since then: new email, Slack or task activity." if stale else None)
    for c, run in s.execute(select(ActionCandidate, AiRun).join(AiRun, AiRun.id == ActionCandidate.run_id)
                            .where(ActionCandidate.kind == "new", ActionCandidate.status == "proposed")).all():
        if c.business_id in slugs:
            out[c.business_id]["review"].append(review_item(c, run, slugs[c.business_id]))
    return out
