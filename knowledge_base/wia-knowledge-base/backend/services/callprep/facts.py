"""Facts layer: every count, date, owner and status in a brief, computed by code (never by the model).

Reads the portfolio payload being built (its actions, History events and recaps, so the brief agrees with the
rest of the app) plus a few queries: unanswered asks from the KB's own digests, client email threads waiting on
WIA's reply, lead outcomes and ad figures. Each part fails alone: an error makes that part "unavailable".
"""
import re
from datetime import UTC, date, datetime, timedelta
from email.utils import parseaddr

from sqlalchemy import select

from backend.models.db import AiRun, Contact, RecordAssociation, SourceRecord, SourceVersion
from backend.services.ai.context import WIA_TZ
from backend.services.ai.present import evidence_id
from backend.services.callprep.registry import Call

AWAITING_HOURS = 24  # a client email unanswered this long is "awaiting our reply"
# Not a message anyone answers: calendar responses and automatic replies.
NO_REPLY_NEEDED = re.compile(r"^(accepted|declined|tentative|tentatively accepted|updated invitation|invitation|canceled|"
                             r"cancelled)( event)?:|out of office|automatic reply|auto-?reply|maternity leave|on vacation|"
                             r"delivery status notification|undeliverable", re.IGNORECASE)
SETTLE_MAX = 6


def wia_day(dt: datetime | None) -> str:
    return dt.astimezone(WIA_TZ).date().isoformat() if dt else ""


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days if a and b else 0


def _ago(day: str, today: str) -> str:
    d = _days(day, today)
    return "today" if d <= 0 else "1 day ago" if d == 1 else f"{d} days ago"


def window(call: Call) -> dict:
    since = call.previous or call.starts_at - timedelta(days=30)
    return {"since": wia_day(since), "basis": "last call" if call.previous else "30 days", "until": wia_day(call.starts_at)}


def owed(actions: list[dict], cid: str, call_day: str, today: str) -> dict:
    mine = [a for a in actions if a["clientId"] == cid and a.get("status") not in ("Done", "Cancelled")]
    overdue = lambda a: bool(a.get("due")) and a["due"] < today  # noqa: E731
    key = lambda a: (not overdue(a), a.get("due") or "9999")  # noqa: E731
    we = sorted((a for a in mine if a.get("side") != "Client"), key=key)
    they = sorted((a for a in mine if a.get("side") == "Client"), key=key)
    return {"we": [_action(a, today) for a in we], "they": [_action(a, today) for a in they],
            "overdue": sum(1 for a in we if overdue(a)),
            "due_before_call": sum(1 for a in we if a.get("due") and today <= a["due"] <= call_day)}


def _action(a: dict, today: str) -> dict:
    late = bool(a.get("due")) and a["due"] < today
    return {"id": a["id"], "title": a["title"], "owner": a.get("owner") or "", "due": a.get("due") or "",
            "status": a.get("status") or "Open", "late": late, "lateDays": _days(a["due"], today) if late else 0,
            "sourceId": a.get("sourceId") or ""}


def asks(s, call: Call, since: str) -> list[dict]:
    """Quoted client asks still open in the KB's digests and email reads since the window opened (AI output; empty
    while the AI is off)."""
    out = []
    runs = s.execute(select(AiRun).where(AiRun.business_id == call.business.id, AiRun.is_current,
                                         AiRun.state == "succeeded", AiRun.skill.in_(("meeting_digest", "email_actions")))).scalars()
    for run in runs:
        for a in (run.output or {}).get("open_asks", []):
            target = run.refs.get(a.get("ref") or "", {})
            when = target.get("date") or (run.checks.get("meeting_date") or "")[:10]
            if when and when >= since:
                out.append({"quote": a["quote"], "who": a.get("who") or "Client", "date": when,
                            "sourceId": evidence_id(target.get("record_id"))})
    return sorted(out, key=lambda x: x["date"])


def awaiting_reply(s, call: Call, now: datetime) -> list[dict]:
    """Client email threads whose latest message is from the client and older than AWAITING_HOURS."""
    contacts = s.execute(select(Contact.email, Contact.domain).where(Contact.business_id == call.business.id,
                                                                     Contact.status == "approved")).all()
    emails = {e.lower() for e, _ in contacts if e}
    domains = {d.lower() for _, d in contacts if d}
    rows = s.execute(select(SourceRecord, SourceVersion.attributes)
                     .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
                     .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                     .where(RecordAssociation.business_id == call.business.id, RecordAssociation.status == "associated",
                            SourceRecord.record_kind == "gmail_message", SourceRecord.occurred_at > now - timedelta(days=45))
                     .order_by(SourceRecord.occurred_at)).all()
    last = {}
    for r, a in rows:
        last[a.get("thread_id") or r.external_id] = (r, a)
    out = []
    for r, a in last.values():
        sender = parseaddr(a.get("from") or "")[1].lower()
        if NO_REPLY_NEEDED.search(a.get("subject") or ""):
            continue
        if (sender in emails or sender.split("@")[-1] in domains) and r.occurred_at < now - timedelta(hours=AWAITING_HOURS):
            out.append({"subject": a.get("subject") or "(no subject)", "from": sender, "date": wia_day(r.occurred_at),
                        "hours": int((now - r.occurred_at).total_seconds() // 3600), "sourceId": evidence_id(r.id)})
    return sorted(out, key=lambda x: x["date"])


def promised(payload: dict, call: Call, actions: list[dict]) -> dict:
    """The last recorded meeting's commitments, each with where it stands now (via the Action Hub)."""
    cid = call.business.slug
    recaps = sorted((r for r in payload.get("recaps", []) if r["clientId"] == cid and r["date"] < wia_day(call.starts_at)),
                    key=lambda r: r["date"])
    if not recaps:
        return {"recap": None, "items": []}
    last = recaps[-1]
    by_title = {a["title"].strip().lower(): a for a in actions if a["clientId"] == cid}
    items = []
    for c in last.get("commitments", []):
        a = by_title.get(c["text"].strip().lower())
        items.append({**c, "now": (a.get("status") if a else "not tracked"), "actionId": a["id"] if a else None})
    return {"recap": {"id": last["id"], "date": last["date"], "title": last["title"], "decisions": last.get("decisions", []),
                      "covered": last.get("covered", []), "sourceId": last.get("sourceId")}, "items": items}


def bot_threads(s, call: Call, since: str) -> set[str]:
    """Evidence ids of Slack messages written by a bot (Viktor and other agents): call prep never reads them."""
    from backend.models.db import ContentUnit, ProviderIdentity
    rows = s.execute(select(SourceRecord.id).join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                     .join(ContentUnit, ContentUnit.version_id == SourceRecord.current_version_id)
                     .join(ProviderIdentity, ProviderIdentity.id == ContentUnit.author_identity_id)
                     .where(RecordAssociation.business_id == call.business.id, SourceRecord.record_kind == "slack_message",
                            SourceRecord.occurred_at >= datetime.fromisoformat(since).replace(tzinfo=WIA_TZ),
                            ProviderIdentity.party.in_(("bot", "automated")))).scalars()
    return {evidence_id(r) for r in rows}


def changed(events: list[dict], cid: str, since: str, until: str, skip: set[str] = frozenset()) -> list[dict]:
    out = []
    for e in events:
        if e.get("sourceId") in skip:
            continue
        if e["clientId"] == cid and since <= e["date"] < until:
            side = "Client" if e.get("from") in ("Client", "Both") else "Internal"
            out.append({"id": e["id"], "text": e["title"], "detail": e.get("detail", ""), "date": e["date"],
                        "lane": e["lane"], "from": side, "sourceId": e.get("sourceId", ""), "state": e.get("state")})
    return sorted(out, key=lambda x: x["date"], reverse=True)


def leads(s, call: Call) -> dict | None:
    from backend.services.read_models import leads as lead_model
    try:
        out = lead_model.client_leads(s, call.business.slug, "30d")
    except Exception:  # noqa: BLE001 — not a LeadLock client, or no data
        return None
    if not out["sub_accounts"] and not any(out["coverage"]["records"].values()):
        return None
    k = out["kpis"]
    return {"inquiries": [k["inquiries"]["value"], k["inquiries"]["previous"]],
            "tours": [k["tours_booked"]["value"], k["tours_booked"]["previous"]],
            "won": [k["won"]["value"], k["won"]["previous"]] if k["won"].get("tracked") else None,
            "awaiting": k["awaiting_reply"]["value"], "collecting": out["collecting"]}


def ads(s, call: Call, today: date) -> dict:
    from backend.services import ads as ad_figures
    return ad_figures.summary(s, call.business.id, today)


def _pct(now, before) -> int | None:
    return round(100 * (now - before) / before) if before else None


def pulse(o: dict, l: dict | None, ad: dict, ask_list: list, waiting: list, last_contact: dict | None, today: str) -> dict:
    connected = [p for p in ad["platforms"] if p["state"] == "connected"]
    if connected:
        spend = sum(p["current"]["spend"] for p in connected)
        conv = sum(p["current"]["leads"] for p in connected)
        prev = [p["previous"] for p in connected if p.get("previous")]
        prev_conv = sum(p["leads"] for p in prev) if len(prev) == len(connected) else None
        delta = _pct(conv, prev_conv) if prev_conv is not None else None
        ads_chip = {"value": f"${spend:,.0f} spend", "note": f"{conv:g} leads in 30 days"
                    + (f" · {'+' if delta >= 0 else ''}{delta}% vs prior 30" if delta is not None else ""),
                    "tone": "watch" if delta is not None and delta <= -20 else "ok"}
    else:
        state = {p["state"] for p in ad["platforms"]}
        ads_chip = {"value": "No account mapped" if "not_mapped" in state else "Not connected",
                    "note": "Map this client's ad accounts" if "not_mapped" in state else "Ad platforms aren't connected",
                    "tone": "none"}
    if l:
        d = _pct(l["inquiries"][0], l["inquiries"][1]) if l["inquiries"][1] is not None else None
        leads_chip = {"value": f"{l['inquiries'][0]} inquiries", "note": f"{l['tours'][0]} tours"
                      + (f" · {'+' if d >= 0 else ''}{d}% inquiries vs prior 30" if d is not None else "")
                      + (f" · {l['awaiting']} awaiting a reply" if l["awaiting"] else ""),
                      "tone": "watch" if (d is not None and d <= -20) or l["awaiting"] else "ok"}
    else:
        leads_chip = {"value": "Unavailable", "note": "Not a LeadLock client, or not linked", "tone": "none"}
    delivery = {"value": f"{o['overdue']} overdue" if o["overdue"] else "On time",
                "note": f"{len(o['we'])} open on our side", "tone": "bad" if o["overdue"] else "ok"}
    open_items = len(ask_list) + len(waiting)
    contact = f"Last contact {_ago(last_contact['date'], today)} · {last_contact['channel']}" if last_contact and last_contact.get("date") else "No contact on record"
    client = {"value": (f"{len(waiting)} awaiting our reply" if waiting else f"{len(ask_list)} ask{'s' if len(ask_list) != 1 else ''} unanswered")
              if open_items else "Nothing waiting", "note": contact, "tone": "watch" if open_items else "ok"}
    return {"ads": ads_chip, "leads": leads_chip, "delivery": delivery, "client": client}


def settle(o: dict, ask_list: list, waiting: list, call_day: str, today: str) -> list[dict]:
    """Late items we owe, then quoted asks and emails awaiting our reply, then what they owe before the call and
    anything blocked."""
    items = [{"who": f"We owe · {a['owner'] or 'no owner'}", "text": a["title"], "age": f"{a['lateDays']} day{'s' if a['lateDays'] != 1 else ''} late",
              "tone": "late", "sourceId": a["sourceId"]} for a in o["we"] if a["late"]]
    items += [{"who": f"{q['who']} asked", "text": f"“{q['quote']}”", "age": _ago(q["date"], today), "tone": "ask",
               "sourceId": q["sourceId"]} for q in ask_list]
    items += [{"who": "Awaiting our reply", "text": w["subject"], "age": _ago(w["date"], today), "tone": "ask",
               "sourceId": w["sourceId"]} for w in waiting]
    items += [{"who": f"Waiting on {a['owner'] or 'the client'}", "text": a["title"], "age": f"due {a['due']}", "tone": "wait",
               "sourceId": a["sourceId"]} for a in o["they"] if a["due"] and a["due"] <= call_day]
    items += [{"who": f"Blocked · {a['owner'] or 'no owner'}", "text": a["title"], "age": "", "tone": "wait",
               "sourceId": a["sourceId"]} for a in o["we"] if a["status"] == "Blocked"]
    return items[:SETTLE_MAX]


def limits(call: Call, record: dict | None, l: dict | None, ad: dict, prom: dict) -> list[str]:
    out = []
    if call.previous and not prom["recap"]:
        out.append(f"No transcript of the last call ({wia_day(call.previous)}): what was agreed there isn't known, which doesn't mean nothing was")
    elif not call.previous:
        out.append("No earlier meeting with this client on record: changes cover the last 30 days")
    for p in ad["platforms"]:
        if p["state"] == "not_connected":
            out.append(f"{p['label']}: not connected, so no ad figures")
        elif p["state"] == "not_mapped":
            out.append(f"{p['label']}: no ad account mapped to this client")
        elif any(a.get("error") for a in p.get("accounts", [])):
            out.append(f"{p['label']}: the last pull failed for an account, figures may be out of date")
    if l is None:
        out.append("LeadLock: not linked for this client, so no inquiry or tour figures")
    elif not l["collecting"]:
        out.append("LeadLock: no longer collecting; figures are from the last sync")
    for row in (record or {}).get("sources", []):
        if row.get("state") == "Not linked" and row["source"] in ("Gmail", "Slack", "ClickUp", "Fathom"):
            out.append(f"{row['source']}: not linked for this client")
    out.append("Calendar: only the connected calendars are read; calls booked elsewhere don't appear")
    return out


def compute(s, call: Call, payload: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    today = wia_day(now)
    cid, call_day = call.business.slug, wia_day(call.starts_at)
    w = window(call)
    actions = payload.get("actions", [])
    record = payload.get("records", {}).get(cid)
    o = owed(actions, cid, call_day, today)
    ask_list = asks(s, call, w["since"])
    waiting = awaiting_reply(s, call, now)
    l = leads(s, call)
    ad = ads(s, call, now.astimezone(WIA_TZ).date())
    prom = promised(payload, call, actions)
    return {
        "window": w, "pulse": pulse(o, l, ad, ask_list, waiting, (record or {}).get("lastContact"), today),
        "settle": settle(o, ask_list, waiting, call_day, today), "owed": o, "asks": ask_list, "awaiting": waiting,
        "promised": prom,
        "changed": changed(payload.get("events", []), cid, w["since"], w["until"] or today, bot_threads(s, call, w["since"])),
        "leads": l, "ads": ad, "attendance": call.attendance_risk, "limits": limits(call, record, l, ad, prom),
    }
