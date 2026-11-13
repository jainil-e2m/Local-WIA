"""Call prep in the frontend's shapes (frontend/src/calls.ts CallMeta and Brief) for the portfolio build and the
call routes. Facts are live (recomputed every build); the brief text is the current stored version.
"""
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from backend.config import get_settings
from backend.models.db import CallBrief
from backend.services.ai.context import WIA_TZ
from backend.services.callprep import briefs, facts as facts_layer, pack as packs, registry, skill_files

IST = ZoneInfo("Asia/Kolkata")  # the screens render call times in IST and convert with each client's offset
AHEAD_DAYS = 31


def team_name(name: str) -> str:
    from backend.services.read_models.portfolio import team_name as first_name  # portfolio imports this module
    return first_name(name)


def _source(refs: dict, ref: str | None) -> str:
    t = refs.get(ref or "", {})
    return t.get("evidence") or (("kb-" + str(t["record_id"]).replace("-", "")[:12]) if t.get("record_id") else "")


def brief(row: CallBrief, live: dict) -> dict:
    """A stored version as the screen's Brief. Asks, owed and limits are the live facts, not the stored ones."""
    o, refs = row.output or {}, row.refs or {}
    by_ref = {e["sourceId"]: e for e in live.get("changed", [])}
    since = []
    for r in o.get("changed_highlights", []):
        t = refs.get(r, {})
        since.append({"text": next((e["text"] for e in [by_ref.get(t.get("evidence"))] if e), None) or t.get("lane", ""),
                      "date": t.get("date", ""), "sourceId": t.get("evidence") or ""})
    since = [x for x in since if x["text"]]
    return {
        "thirty": [o.get("standing", ""), f"Must achieve: {o.get('goal', '')}", f"Risk: {o['risk']}" if o.get("risk") else ""],
        "since": since,
        "asks": [{"quote": q["quote"], "who": q["who"], "date": q["date"], "sourceId": q["sourceId"]} for q in live.get("asks", [])],
        "agenda": [{"item": p["text"], "why": p["why"], "sourceId": _source(refs, (p.get("refs") or [None])[0])}
                   for p in o.get("talking_points", [])],
        "questions": [q["text"] for q in o.get("questions", [])],
        "watch": [w["text"] + (" (internal)" if w.get("audience") == "internal" else "") for w in o.get("watch_outs", [])],
        **({"opportunity": {"text": o["opportunity"]["text"], "why": o["opportunity"]["why"],
                            "sourceId": _source(refs, (o["opportunity"].get("refs") or [None])[0])}} if o.get("opportunity") else {}),
        "typeBlock": [{"label": t["label"], "value": t["value"]} for t in o.get("type_block", [])],
        "limits": live.get("limits", []), "more": {},
        **({"declined": o["declined"]} if o.get("declined") else {}),
    }


def version_row(row: CallBrief, skills: dict) -> dict:
    return {"n": row.version, "by": "Automatic" if row.built_by == "auto" else row.built_by,
            "at": row.built_at.astimezone(WIA_TZ).strftime("%Y-%m-%d %H:%M"),
            "skill": skills[row.skill_key].name if row.skill_key in skills else row.skill_key,
            "trigger": row.trigger, "outcome": row.outcome, "prompt": row.instructions or "",
            **({"declined": row.output["declined"]} if row.output and row.output.get("declined") else {}),
            **({"rejected": [d["why"] for d in (row.checks or {}).get("dropped_lines", [])
                             if d["where"] in (row.checks or {}).get("core_failed", [])][:3]} if row.outcome == "rejected" else {})}


def meta(s, call: registry.Call, data: dict, skills: dict, now: datetime, *, with_fingerprint=True) -> dict:
    start = call.starts_at.astimezone(IST)
    minutes = int((call.ends_at - call.starts_at).total_seconds() // 60) if call.ends_at else 0
    f = facts_layer.compute(s, call, data, now)
    rows = briefs.history(s, call.record_id)
    current = next((r for r in rows if r.is_current), None)
    out = {
        "id": call.call_id, "recordId": str(call.record_id), "clientId": call.business.slug,
        "date": start.date().isoformat(), "time": start.strftime("%H:%M"), "duration": f"{minutes} min" if minutes else "",
        # Team members by the app's first-name roster, so "My calls" matches the viewer.
        "title": call.title, "host": team_name(call.host), "hostSource": call.host_source,
        "attendees": [team_name(a.name) if a.side == "WIA" else a.name for a in call.attendees],
        "attendeeDetail": [{"name": team_name(a.name) if a.side == "WIA" else a.name, "side": a.side,
                            "response": a.response} for a in call.attendees],
        "type": call.skill.key, "typeSource": call.type_source, "facts": f,
        "versions": [version_row(r, skills) for r in rows],
        "location": call.location if call.location.startswith("http") else "",
    }
    if call.cancelled:
        out.update(state="Cancelled", stateNote="Cancelled in the calendar. Earlier versions stay readable.")
    elif current is not None:
        out["brief"] = brief(current, f)
        out["builtAt"] = current.built_at.astimezone(WIA_TZ).strftime("%Y-%m-%d %H:%M")
        out["state"], reasons = "Ready", []
        if with_fingerprint:
            now_inputs = packs.build(s, call, f=f, data=data, instructions=briefs.latest_instructions(s, call.record_id),
                                     now=now, read_bodies=False).inputs
            reasons = briefs.reasons(current.inputs, now_inputs)
        if reasons:
            out.update(state="Stale", stateNote="Since it was built: " + "; ".join(reasons) + ".", changedReasons=reasons)
    elif call.type_source == "Fallback":
        out.update(state="Needs type", stateNote="The title doesn't say the call type. Set it so the right skill builds the brief.")
    else:
        rejected = next((r for r in reversed(rows) if r.outcome == "rejected"), None)
        out.update(state="Scheduled", stateNote=(
            "The last build failed its checks; the facts below are current." if rejected else
            f"The brief text builds automatically {get_settings().ai_brief_lead_hours} h before the call while the AI is on. "
            "The facts below are live."))
    return out


def calls(s, data: dict, now: datetime | None = None) -> dict:
    """{"callMeta": [...], "calls": [...legacy shape], "excludedCalls": [...], "callSkills": [...]} for the build."""
    now = now or datetime.now(UTC)
    skills = skill_files.load_all(s)
    day_start = now.astimezone(WIA_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    out = {"callMeta": [], "calls": [], "excludedCalls": [],
           "callSkills": [skill_files.present(k) for k in skills.values()]}
    for call in registry.calls(s, day_start, now + timedelta(days=AHEAD_DAYS)):
        if call.excluded:
            out["excludedCalls"].append({"id": call.call_id, "clientId": call.business.slug, "title": call.title,
                                         "date": call.starts_at.astimezone(IST).date().isoformat(),
                                         "time": call.starts_at.astimezone(IST).strftime("%H:%M"), "why": call.excluded})
            continue
        m = meta(s, call, data, skills, now)
        out["callMeta"].append(m)
        b = m.get("brief") or {}

        out["calls"].append({
            "id": m["id"], "clientId": m["clientId"], "date": m["date"], "time": m["time"], "duration": m["duration"],
            "type": call.title, "host": m["host"], "objective": (b.get("thirty") or ["", call.skill.body["This call must decide"]])[1],
            "context": (b.get("thirty") or [""])[0], "needs": [], "agenda": call.skill.agenda,
            "opportunity": (b.get("opportunity") or {}).get("text", ""), "sourceIds": [],
        })
    return out
