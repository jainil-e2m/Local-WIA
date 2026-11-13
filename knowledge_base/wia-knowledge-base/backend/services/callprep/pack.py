"""Evidence pack: what the one model call for a brief reads. Code builds it from the call, its facts and only the
blocks the call type's skill asks for; every line carries a ref the answer must cite.

Refs: [A#] open actions, [Q#] unanswered asks, [W#] email awaiting our reply, [H#] History events, [D#] last
meeting digest, [E#] client email (read live, never stored), [S#] internal Slack, [L#] lead figures, [P#] ad
figures, [F#] profile facts, [X#] items fetched for a person's instructions.

The fingerprint is computed from pointers (record and version ids, action states, the facts), never from email
bodies, so the scheduler can check "did anything change?" every sweep without reading Gmail.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from backend.models.db import (AiRun, ConnectorAccount, ContentUnit, RecordAssociation, ReadModelSnapshot,
                               SourceRecord, SourceScope, SourceVersion)
from backend.services.ai import context
from backend.services.ai.context import Block, People, Refs, clip
from backend.services.callprep import facts as facts_layer
from backend.services.callprep import skill_files
from backend.services.callprep.registry import Call
from backend.services.shared.hashing import canonical_hash


UNDATED_MAX = 10  # open tasks with no due date shown per side; the rest are counted, not listed


@dataclass
class Pack:
    call: Call
    skill: skill_files.Skill
    facts: dict
    blocks: dict[str, Block]
    refs: Refs
    inputs: dict
    instructions: str | None = None
    extra: list = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.inputs)


def payload(s) -> dict:
    return s.execute(select(ReadModelSnapshot.payload).where(ReadModelSnapshot.name == "portfolio")).scalar_one_or_none() or {}


def _lines(title: str, lines: list[str], empty: str) -> Block:
    return Block(title, "\n".join(lines) if lines else empty)


def _money(x: float) -> str:
    return f"${x:,.0f}" if x >= 100 else f"${x:,.2f}"


def ads_lines(ads: dict, refs: Refs) -> list[str]:
    out = []
    for p in ads["platforms"]:
        if p["state"] != "connected":
            out.append(f"{p['label']}: {'not connected' if p['state'] == 'not_connected' else 'no account mapped to this client'}")
            continue
        c, prev = p["current"], p.get("previous")

        def part(t):
            bits = [f"spend {_money(t['spend'])}", f"leads {t['leads']:g}", f"cost per lead {_money(t['cpl']) if t['cpl'] else 'n/a'}",
                    f"clicks {t['clicks']}", f"CTR {t['ctr']}%" if t.get("ctr") is not None else ""]
            if t.get("link_ctr") is not None:
                bits.append(f"link CTR {t['link_ctr']}%")
            if t.get("lpv_rate") is not None:
                bits.append(f"landing page views {t['lpv_rate']}% of link clicks")
            if t.get("budget_lost_is") is not None:
                bits.append(f"search impression share lost to budget {t['budget_lost_is']}%")
            return ", ".join(b for b in bits if b)
        text = f"{p['label']}, last {ads['period_days']} days to {ads['through']}: {part(c)}" + \
               (f". Previous {ads['period_days']} days: {part(prev)}" if prev else ". No figures for the previous period")
        ref = refs.add("P", text, evidence=None, lane="Ads")
        out.append(f"[{ref}] {text}")
        for camp in p.get("campaigns", [])[:5]:
            t = f"{p['label']} campaign “{camp['name']}”: spend {_money(camp['spend'])}, leads {camp['leads']:g}"
            r = refs.add("P", t, evidence=None, lane="Ads")
            out.append(f"[{r}]   {t}")
    return out


def facts_block(f: dict, call: Call, refs: Refs) -> Block:
    lines = [f"Window: since {f['window']['since']} ({f['window']['basis']})"]
    if f["attendance"]:
        lines.append(f"Attendance: {f['attendance']}")
    lines.append("\nWe owe (open, overdue first):")
    owed_cfg = call.skill.blocks.get("owed")
    budget = (owed_cfg.get("max_chars", 6000) if isinstance(owed_cfg, dict) else 6000) // 2
    for side, who in (("we", "no owner"), ("they", "client")):
        if side == "they":
            lines.append("\nThey owe:")
        used, hidden, undated = 0, 0, 0
        for a in f["owed"][side]:  # late first, then by date, undated last (mostly onboarding template tasks)
            line = (f"{a['title']} · {a['owner'] or who} · due {a['due'] or 'no date'}"
                    + (f" · LATE {a['lateDays']} days" if a["late"] else "") + f" · {a['status']}")
            if used + len(line) > budget or (not a["due"] and undated >= UNDATED_MAX):
                hidden += 1
                continue
            used += len(line)
            undated += not a["due"]
            ref = refs.add("A", a["title"], action_ref=a["id"], evidence=a["sourceId"])
            lines.append(f"[{ref}] {line}")
        if hidden:
            lines.append(f"({hidden} more open items with later or no dates are not shown)")
    lines.append("\nClient asks not yet answered (quoted):")
    for q in f["asks"]:
        ref = refs.add("Q", q["quote"], evidence=q["sourceId"], date=q["date"], who=q["who"])
        lines.append(f"[{ref}] {q['date']} · {q['who']}: “{q['quote']}”")
    lines.append("\nClient emails awaiting our reply:")
    for w in f["awaiting"]:
        ref = refs.add("W", w["subject"], evidence=w["sourceId"], date=w["date"])
        lines.append(f"[{ref}] {w['date']} · “{w['subject']}” · waiting {w['hours'] // 24} days")
    prom = f["promised"]
    if prom["recap"]:
        lines.append(f"\nPromised on the last recorded call ({prom['recap']['date']}), and where it stands now:")
        for c in prom["items"]:
            ref = refs.add("D", c["text"], evidence=prom["recap"]["sourceId"], date=prom["recap"]["date"])
            lines.append(f"[{ref}] {c['text']} · {c['who']} · promised {c['when']} · now: {c['now']}")
        for d in prom["recap"]["decisions"]:
            ref = refs.add("D", d, evidence=prom["recap"]["sourceId"], date=prom["recap"]["date"])
            lines.append(f"[{ref}] Decided: {d}")
    if f["leads"]:
        l = f["leads"]
        text = (f"LeadLock, last 30 days: inquiries {l['inquiries'][0]} (previous 30 days {l['inquiries'][1]}), "
                f"tours booked {l['tours'][0]} (previous {l['tours'][1]})"
                + (f", won {l['won'][0]} (previous {l['won'][1]})" if l.get("won") else "")
                + f", inquiries awaiting a reply {l['awaiting']}")
        ref = refs.add("L", text, evidence=None, lane="Leads")
        lines.append(f"\n[{ref}] {text}")
    lines.append("\nLimits (what the KB couldn't see): " + "; ".join(f["limits"]))
    return Block("facts", "\n".join(lines))


def changed_block(f: dict, refs: Refs, max_chars: int) -> Block:
    lines, used, clipped = [], 0, 0
    for e in f["changed"]:  # newest first, so the budget keeps the recent days
        line = f"{e['date']} · {e['from']} · {e['lane']} · {e['text']} ({e['detail']})"
        if used + len(line) > max_chars:
            clipped += 1
            continue
        lines.append((e, line))
        used += len(line)
    out = []
    for e, line in reversed(lines):
        ref = refs.add("H", e["text"], evidence=e["sourceId"], date=e["date"], lane=e["lane"])
        out.append(f"[{ref}] {line}")
    note = f"\n(the {clipped} oldest changes are not shown)" if clipped else ""
    return Block("since_last_call", ("\n".join(out) + note) if out else "(nothing recorded since the last call)", clipped)


def last_call_block(s, call: Call, refs: Refs, n: int) -> Block:
    runs = s.execute(select(AiRun).where(AiRun.skill == "meeting_digest", AiRun.business_id == call.business.id,
                                         AiRun.is_current, AiRun.state == "succeeded",
                                         AiRun.checks["meeting_date"].astext < call.starts_at.isoformat())
                     .order_by(AiRun.checks["meeting_date"].astext.desc()).limit(n)).scalars().all()
    lines = []
    for run in runs:
        when = (run.checks.get("meeting_date") or "")[:10]
        evidence = "kb-" + run.subject_id.replace("-", "")[:12]
        lines.append(f"Meeting on {when}:")
        for x in (run.output or {}).get("summary", []):
            ref = refs.add("D", x, evidence=evidence, date=when)
            lines.append(f"[{ref}] {x}")
    if not lines and call.previous:
        lines.append(f"(the last meeting, {facts_layer.wia_day(call.previous)}, has no transcript in the KB)")
    return Block("last_call", "\n".join(lines) or "(no earlier meeting digest)")


def profile_block(record: dict | None, wanted, refs: Refs) -> Block:
    lines = []
    for section in (record or {}).get("profile", []):
        if wanted != "all" and section["section"] not in wanted:
            continue
        for f in section["facts"]:
            ref = refs.add("F", f["value"], evidence=f.get("sourceId"), lane="Profile")
            lines.append(f"[{ref}] {section['section']} · {f['label']}: {clip(f['value'], 400)}")
        if not section["facts"]:
            lines.append(f"{section['section']}: not answered")
    return Block("profile", "\n".join(lines) or "(no profile facts yet)")


def _pointer_inputs(s, call: Call, since: datetime) -> dict:
    """Record and version ids of the email and Slack the pack may read: what changed, never what it says."""
    rows = s.execute(select(SourceRecord.id, SourceRecord.current_version_id, SourceRecord.record_kind)
                     .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                     .where(RecordAssociation.business_id == call.business.id, RecordAssociation.status == "associated",
                            SourceRecord.record_kind.in_(("gmail_message", "slack_message")),
                            SourceRecord.occurred_at > since)).all()
    scopes = [sc for sc in s.execute(select(SourceScope.id).join(ConnectorAccount).where(
        ConnectorAccount.provider == "slack", SourceScope.business_id == call.business.id,
        SourceScope.state == "approved")).scalars()]
    slack = s.execute(select(SourceRecord.id, SourceRecord.current_version_id).where(
        SourceRecord.scope_id.in_(scopes), SourceRecord.occurred_at > since)).all() if scopes else []
    return {"email": sorted(str(v) for _, v, k in rows if k == "gmail_message"),
            "slack": sorted(str(v) for _, v in slack)}


def build(s, call: Call, *, f: dict | None = None, data: dict | None = None, instructions: str | None = None,
          fetch=None, extra: list | None = None, now: datetime | None = None, read_bodies: bool = True) -> Pack:
    """`read_bodies=False` builds the inputs and fingerprint only (the scheduler's cheap check)."""
    now = now or datetime.now(UTC)
    data = data if data is not None else payload(s)
    f = f if f is not None else facts_layer.compute(s, call, data, now)
    skill, refs, b = call.skill, Refs(), call.skill.blocks
    since = call.previous or call.starts_at - timedelta(days=30)
    blocks = {"facts": facts_block(f, call, refs)}
    people = People(s, call.business.id)
    if "last_call" in b:
        blocks["last_call"] = last_call_block(s, call, refs, int(b["last_call"] or 1))
    if "since_last_call" in b:
        blocks["since_last_call"] = changed_block(f, refs, (b["since_last_call"] or {}).get("max_chars", 6000))
    if "ads" in b:
        blocks["ads"] = _lines("ads", ads_lines(f["ads"], refs), "(no ad figures)")
    if "profile" in b:
        blocks["profile"] = profile_block(data.get("records", {}).get(call.business.slug), b["profile"], refs)
    if read_bodies and "email_since" in b:
        cfg = b["email_since"] or {}
        blocks["email_since"] = context.client_emails(s, call.business, since, now, people, refs, cfg.get("max_chars", 12000),
                                                      fetch=fetch, limit=cfg.get("max_threads", 10))
    if read_bodies and "internal_slack" in b:
        blocks["internal_slack"] = context.slack_posts(s, call.business, since, now, people, refs,
                                                       (b["internal_slack"] or {}).get("max_chars", 6000), viktor=False)
    if extra:
        lines = []
        for item in extra:
            ref = refs.add("X", item["text"], evidence=item.get("sourceId"), date=item.get("date"))
            lines.append(f"[{ref}] {item.get('date', '')} · {item['label']}: {clip(item['text'], 1500)}")
        blocks["fetched"] = Block("fetched", "\n".join(lines))
    # Only what a person would call a change: not ages ("3 days ago"), and not the rolling 30-day lead and ad
    # totals, which move every day and would otherwise rebuild every brief at T-2 h.
    inputs = {"skill": skill.ref, "instructions": instructions or "", "starts": call.starts_at.isoformat(),
              "type": skill.key, "attendance": f["attendance"],
              "actions": sorted([a["id"], a["status"], a["due"]] for side in ("we", "they") for a in f["owed"][side]),
              "asks": sorted([q["date"], q["quote"]] for q in f["asks"]),
              "awaiting": sorted(w["sourceId"] for w in f["awaiting"]),
              "promised": [[c["text"], c["now"]] for c in f["promised"]["items"]],
              "digest": f["promised"]["recap"]["id"] if f["promised"]["recap"] else None,
              "changes": sorted([e["date"], e["sourceId"], e["text"]] for e in f["changed"]),
              **_pointer_inputs(s, call, since)}
    return Pack(call, skill, f, blocks, refs, inputs, instructions, extra or [])


def render(pack: Pack) -> tuple[str, str]:
    """(system, user) prompts: the shared rules, then the skill, then instructions, then the evidence."""
    from backend.services.ai import skills as ai_skills
    sk, c = pack.skill, pack.call
    system = ai_skills.render("call_brief.system.md", {
        "skill_name": sk.name, "purpose": sk.purpose, "decide": sk.body["This call must decide"],
        "agenda": sk.body["Agenda skeleton"], "leave_out": sk.body["Leave out"], "guidance": sk.body["Guidance"],
        "type_block": sk.body["Type-specific block"], "type_block_title": sk.type_block or "none",
        "points": str(sk.length["points"]), "questions": str(sk.length["questions"]), "watch": str(sk.length["watch"]),
        "highlights": str(sk.length["highlights"])})
    wia = [a for a in c.attendees if a.side == "WIA"]
    client = [a for a in c.attendees if a.side == "Client"]
    header = "\n".join([
        f"Client: {c.business.name}", f"Call: {c.title}",
        f"Starts: {c.starts_at.astimezone(context.WIA_TZ).strftime('%Y-%m-%d %H:%M')} WIA time",
        f"Host: {c.host}",
        "WIA attendees: " + (", ".join(f"{a.name} ({a.response})" for a in wia) or "none listed"),
        "Client attendees: " + (", ".join(f"{a.name} ({a.response})" for a in client) or "none listed")])
    order = [("facts", "Facts (computed by code: fixed, cite them, never change them)"),
             ("last_call", "Last meeting (the KB's digest)"), ("since_last_call", "What changed since the last call"),
             ("ads", "Ad figures (from the ad platforms)"), ("profile", "Client profile"),
             ("email_since", "Client email since the last call"),
             ("internal_slack", "Internal Slack since the last call (WIA's team only)"),
             ("fetched", "Fetched for the instructions")]
    parts = [f"## The call\n{header}"]
    if pack.instructions:
        parts.append(f"## Instructions from {c.host if c.host != 'Not set' else 'the team'} for this version\n{pack.instructions}")
    parts += [f"## {title}\n{pack.blocks[k].text}" for k, title in order if k in pack.blocks]
    return system, "\n\n".join(parts)


def all_text(pack: Pack, system: str, user: str) -> list[str]:
    """Every text the answer may take a figure from: the evidence, what the refs point at, and the skill's guidance
    and type block (WIA's playbook thresholds). Not the rest of the system prompt: its list numbers and length caps
    would let any small number through."""
    return [user, *pack.refs.texts.values(), pack.skill.body["Guidance"], pack.skill.body["Type-specific block"]]


def extra_candidates(s, call: Call, *, days: int = 180) -> list[dict]:
    """What regenerate may fetch beyond the pack: older client email subjects, earlier meeting digests and older
    History events for this client only."""
    since = call.starts_at - timedelta(days=days)
    out = []
    for r, v in s.execute(select(SourceRecord, SourceVersion)
                          .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
                          .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                          .where(RecordAssociation.business_id == call.business.id, RecordAssociation.status == "associated",
                                 SourceRecord.record_kind == "gmail_message", SourceRecord.occurred_at > since)
                          .order_by(SourceRecord.occurred_at.desc()).limit(60)).all():
        out.append({"id": f"email:{r.id}", "label": f"Email “{v.attributes.get('subject') or '(no subject)'}” from "
                    f"{v.attributes.get('from') or 'unknown'}", "date": facts_layer.wia_day(r.occurred_at)})
    for run in s.execute(select(AiRun).where(AiRun.skill == "meeting_digest", AiRun.business_id == call.business.id,
                                             AiRun.is_current, AiRun.state == "succeeded")).scalars():
        out.append({"id": f"digest:{run.id}", "label": "Meeting digest", "date": (run.checks.get("meeting_date") or "")[:10]})
    for r in s.execute(select(SourceRecord).join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                       .where(RecordAssociation.business_id == call.business.id, RecordAssociation.status == "associated",
                              SourceRecord.record_kind == "fathom_recording")).scalars():
        out.append({"id": f"transcript:{r.id}", "label": "Meeting transcript", "date": facts_layer.wia_day(r.occurred_at)})
    return out


def fetch_extra(s, call: Call, ids: list[str], fetch=None) -> list[dict]:
    """Read the chosen items. Each id must be one `extra_candidates` offered for this client."""
    allowed = {c["id"]: c for c in extra_candidates(s, call)}
    out = []
    for item_id in ids[:4]:
        c = allowed.get(item_id)
        if c is None:
            continue  # not this client's, or not offered: never read
        kind, _, raw = item_id.partition(":")
        if kind == "email":
            r = s.get(SourceRecord, raw)
            if fetch is None:
                from backend.services.intake.adapters import get_adapter
                fetch = get_adapter("gmail").fetch_body
            text = context.read_email(fetch, r.external_id)
            if text is None:
                continue  # gone from Gmail: skipped; any other failure is raised (services/ai/context.py)
            out.append({**c, "text": text, "sourceId": "kb-" + r.id.hex[:12]})
        elif kind == "digest":
            run = s.get(AiRun, raw)
            o = run.output or {}
            text = " ".join(o.get("summary", []) + [f"Decided: {d['text']}" for d in o.get("decisions", [])])
            out.append({**c, "text": text, "sourceId": "kb-" + run.subject_id.replace("-", "")[:12]})
        elif kind == "transcript":
            r = s.get(SourceRecord, raw)
            units = s.execute(select(ContentUnit.text).where(ContentUnit.version_id == r.current_version_id,
                                                             ContentUnit.retention_state == "retained")
                              .order_by(ContentUnit.ordinal)).scalars().all()
            out.append({**c, "text": clip(" ".join(units), 6000), "sourceId": "kb-" + r.id.hex[:12]})
    return out
