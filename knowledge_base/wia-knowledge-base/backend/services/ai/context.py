"""Context blocks: deterministic database reads that become the user prompt.

Every line a model may cite carries a short ref ([T12] transcript, [E3] email, [S5] internal Slack, [V2] Viktor,
[A4] open action, [C1] calendar). `Refs` maps each back to its record/unit for citations and checks the quotes
against the text it showed; only ids are stored with the run, never the text (email bodies are never stored).

Each block has a character budget; lists are clipped most-recent-first and the run records what was clipped.
"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select

from backend.models.db import (AccountTeamMember, ActionCandidate, AiRun, Business, BusinessAlias, ConnectorAccount,
                               Contact, ContentUnit, Person, ProviderIdentity, ReadModelSnapshot, RecordAssociation,
                               SourceRecord, SourceScope, SourceVersion)
from backend.services.shared.errors import NotFoundError

WIA_TZ = ZoneInfo("America/Chicago")
VIKTOR = "Viktor"  # the roster's bot account for viktor.com (WIA's Slack agent); its posts are attributed analysis
DONE_TYPES = ("done", "closed")
TRANSCRIPT_KINDS = ("transcript_segment", "transcript_cue")
# Email about money: never a source for text the client reads (the recap email). Senders as the Gmail adapter's.
FINANCE_SUBJECT = re.compile(r"\b(invoice|payment|paid|receipt|refund|billing|overdue|past due|contract|"
                             r"proposal signed|balance due|charge)\b", re.IGNORECASE)


def read_email(fetch, message_id: str) -> str | None:
    """One email's text, live from Gmail. None only when it was deleted since intake. Every other failure (an
    expired credential, a throttle, a 5xx) is raised: running on half the email would be billed as if complete,
    and that window would never be read again."""
    try:
        return fetch(message_id).get("authored") or ""
    except NotFoundError:
        return None


def is_finance_email(sender: str | None, subject: str | None) -> bool:
    from backend.services.intake.adapters.gmail import FINANCE_SENDERS
    return (sender or "").lower() in FINANCE_SENDERS or bool(FINANCE_SUBJECT.search(subject or ""))


def transcript_fingerprint(s, version_id) -> str:
    """The transcript's words, as a hash: a new version with the same words (Fathom added its summary or action
    items, an invitee changed) is not a new meeting to digest."""
    shas = s.execute(select(ContentUnit.text_sha256).where(ContentUnit.version_id == version_id,
                                                           ContentUnit.unit_kind.in_(TRANSCRIPT_KINDS))
                     .order_by(ContentUnit.ordinal)).scalars().all()
    return hashlib.sha256(",".join(shas).encode()).hexdigest()


def day(dt: datetime | None) -> str:
    return dt.astimezone(WIA_TZ).date().isoformat() if dt else ""


def clip(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


@dataclass
class Refs:
    """Short reference -> what it points at. `texts` stays in memory for quote checks only."""
    items: dict = field(default_factory=dict)
    texts: dict = field(default_factory=dict)
    counters: dict = field(default_factory=dict)

    def add(self, prefix: str, text: str, **target) -> str:
        n = self.counters[prefix] = self.counters.get(prefix, 0) + 1
        ref = f"{prefix}{n}"
        self.items[ref] = {k: (str(v) if v is not None and not isinstance(v, (str, int, float, bool)) else v)
                           for k, v in target.items()}
        self.texts[ref] = text
        return ref

    def drop(self, ref: str) -> None:
        """A line clipped from the prompt: the model never saw it, so it can't be cited."""
        self.items.pop(ref, None)
        self.texts.pop(ref, None)


@dataclass
class Block:
    name: str
    text: str
    clipped: int = 0


class People:
    """Names and sides for identities, loaded once per prompt."""

    def __init__(self, s, business_id):
        self.s = s
        self.contacts = {c.email for c in s.execute(select(Contact).where(
            Contact.business_id == business_id, Contact.status == "approved", Contact.email.is_not(None))).scalars()}
        self.domains = {c.domain for c in s.execute(select(Contact).where(
            Contact.business_id == business_id, Contact.status == "approved", Contact.domain.is_not(None))).scalars()}
        self._cache = {}

    def identity(self, identity_id) -> tuple[str, str]:
        """(name, side) for a unit author: side is WIA, Client, Bot or Guest."""
        if identity_id in self._cache:
            return self._cache[identity_id]
        i = self.s.get(ProviderIdentity, identity_id) if identity_id else None
        person = self.s.get(Person, i.person_id) if i and i.person_id else None
        if person is not None and person.kind == "shared_mailbox":
            person = None  # a shared inbox's roster name describes the inbox; the speaker's own name is better
        name = (person.name if person else None) or (i.display_name if i else None) or (i.email if i else None) or "Unknown"
        party = i.party if i else None
        side = {"internal": "WIA", "shared_mailbox": "WIA", "client": "Client", "bot": "Bot", "automated": "Bot"}.get(
            party, self.side_of(i.email if i else None))
        self._cache[identity_id] = (name, side)
        return name, side

    def side_of(self, email: str | None) -> str:
        if not email:
            return "Guest"
        email = email.lower()
        return "Client" if email in self.contacts or email.split("@")[-1] in self.domains else "Guest"


def _units(s, version_id, kinds=None):
    q = select(ContentUnit).where(ContentUnit.version_id == version_id, ContentUnit.retention_state == "retained")
    if kinds:
        q = q.where(ContentUnit.unit_kind.in_(kinds))
    return s.execute(q.order_by(ContentUnit.ordinal)).scalars().all()


def meeting(s, record, version, people: People) -> Block:
    a = version.attributes
    invitees = [f"{i.get('name') or i.get('email')} ({people.side_of(i.get('email'))})" for i in a.get("invitees", [])]
    start, end = a.get("recording_start"), a.get("recording_end")
    minutes = ""
    if start and end:
        minutes = f"{int((datetime.fromisoformat(end.replace('Z', '+00:00')) - datetime.fromisoformat(start.replace('Z', '+00:00'))).total_seconds() // 60)} min"
    return Block("meeting", f"Title: {a.get('title') or 'Meeting'}\nDate: {day(record.occurred_at)} (WIA time)\n"
                            f"Length: {minutes or 'unknown'}\nInvited: {', '.join(invitees) or 'not listed'}")


def transcript(s, version, people: People, refs: Refs, budget: int) -> Block:
    lines, used, clipped = [], 0, 0
    for u in _units(s, version.id, TRANSCRIPT_KINDS):
        name, side = people.identity(u.author_identity_id)
        if u.author_identity_id is None and (u.locator or {}).get("speaker"):
            name = u.locator["speaker"]
        ref = refs.add("T", u.text, record_id=version.record_id, unit_id=u.id, date=day(u.occurred_at), who=name)
        line = f"[{ref}] {(u.locator or {}).get('timestamp') or ''} {name} ({side}): {u.text}"
        if used + len(line) > budget:
            clipped += 1
            refs.drop(ref)
            continue
        lines.append(line)
        used += len(line)
    note = f"\n(transcript clipped: the last {clipped} segments are not shown)" if clipped else ""
    return Block("transcript", "\n".join(lines) + note or "(no transcript text)", clipped)


def client_card(s, business: Business) -> Block:
    team = s.execute(select(Person.name, AccountTeamMember.role).join(Person, Person.id == AccountTeamMember.person_id)
                     .where(AccountTeamMember.business_id == business.id, AccountTeamMember.status == "confirmed")).all()
    contacts = s.execute(select(Contact).where(Contact.business_id == business.id, Contact.status == "approved")).scalars()
    aliases = s.execute(select(BusinessAlias.alias).where(BusinessAlias.business_id == business.id)).scalars().all()
    return Block("client_card", "\n".join([
        f"Client: {business.name} (id {business.slug})",
        f"Also called: {', '.join(a for a in aliases if a != business.name) or 'none'}",
        "WIA account team: " + (", ".join(f"{n} ({r})" for n, r in team) or "not confirmed in the KB"),
        "Client contacts: " + (", ".join(c.display_name or c.email or f"anyone @{c.domain}" for c in contacts) or "none approved"),
    ]))


def task_state(attributes: dict) -> str | None:
    """ClickUp status as the portfolio shows it; None for 'n/a' (not delivery)."""
    status = attributes.get("status") or {}
    raw, stype = (status.get("status") or "").lower(), (status.get("type") or "").lower()
    if raw in ("n/a", "na", "not applicable"):
        return None
    if stype in DONE_TYPES:
        return "Done"
    return "In progress" if "progress" in raw else "Blocked" if ("hold" in raw or "block" in raw) else "Open"


def open_actions(s, business: Business, people: People, refs: Refs, budget: int, *, subject: str = "") -> Block:
    """ClickUp tasks not done, plus the KB's own proposals and approved actions. This subject's own pending
    proposals are left out (a re-run replaces them, so it must not read them as WIA's list), but its approved
    ones stay in: a re-digest then matches them instead of proposing them again."""
    lines, used, clipped = [], 0, 0
    rows = s.execute(select(SourceRecord, SourceVersion).join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
                     .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                     .where(RecordAssociation.business_id == business.id, RecordAssociation.status == "associated",
                            SourceRecord.record_kind == "clickup_task", SourceRecord.availability == "available")
                     .order_by(SourceRecord.occurred_at.desc())).all()
    items = []
    for r, v in rows:
        state = task_state(v.attributes)
        if state in (None, "Done"):
            continue
        due_ms = v.attributes.get("due_date")
        due = day(datetime.fromtimestamp(int(due_ms) / 1000, UTC)) if due_ms else "no date"
        items.append((v.attributes.get("name") or "(untitled task)", due, state, "ClickUp", f"cu-{r.external_id}", r.id))
    for c in s.execute(select(ActionCandidate).join(AiRun, AiRun.id == ActionCandidate.run_id)
                       .where(ActionCandidate.business_id == business.id, ActionCandidate.kind == "new",
                              ActionCandidate.status.in_(("proposed", "approved")),
                              or_(AiRun.subject_id != subject, ActionCandidate.status == "approved"))).scalars():
        items.append((c.title, c.due_date.isoformat() if c.due_date else "no date",
                      "Proposed" if c.status == "proposed" else "Approved", "KB proposal", f"ai-{c.id}", c.source_record_id))
    for title, due, state, origin, action_ref, record_id in items:
        ref = refs.add("A", title, action_ref=action_ref, record_id=record_id)
        line = f"[{ref}] {title} · due {due} · {state} · {origin}"
        if used + len(line) > budget:
            clipped += 1
            refs.drop(ref)
            continue
        lines.append(line)
        used += len(line)
    return Block("open_actions", "\n".join(lines) or "(no open actions)", clipped)


def previous_digest(s, business: Business, before: datetime, *, limit: int = 1) -> Block:
    """The KB's own digests of the client's last meetings (Call 1 output), newest first."""
    runs = s.execute(select(AiRun).where(AiRun.skill == "meeting_digest", AiRun.business_id == business.id,
                                         AiRun.is_current, AiRun.state == "succeeded",
                                         AiRun.checks["meeting_date"].astext < before.isoformat())
                     .order_by(AiRun.checks["meeting_date"].astext.desc()).limit(limit)).scalars().all()
    parts = []
    for run in runs:
        o = run.output or {}
        parts.append(f"Meeting on {run.checks.get('meeting_date', '')[:10]}:")
        parts += [f"- {x}" for x in o.get("summary", [])]
        parts += [f"- Decided: {d['text']}" for d in o.get("decisions", [])]
        parts += [f"- Committed: {c['text']} ({c.get('owner_name') or c['owner_side']}, {c.get('due_phrase') or 'no date'})"
                  for c in o.get("commitments", [])]
        parts += [f"- Still open: {a['who']} asked \"{a['quote']}\"" for a in o.get("open_asks", [])]
    return Block("previous_digest", "\n".join(parts) or "(no earlier meeting digest)")


def _client_slack(s, business: Business):
    return [sc.id for sc in s.execute(select(SourceScope).join(ConnectorAccount).where(
        ConnectorAccount.provider == "slack", SourceScope.business_id == business.id,
        SourceScope.state == "approved")).scalars()]


def slack_posts(s, business: Business, since: datetime, until: datetime, people: People, refs: Refs, budget: int,
                *, viktor: bool) -> Block:
    """Internal Slack in the client's linked channels (WIA's Slack is internal-only), or Viktor's posts there."""
    scopes = _client_slack(s, business)
    name = "viktor_posts" if viktor else "internal_comms"
    if not scopes:
        return Block(name, "(no Slack channel linked to this client)")
    rows = s.execute(select(ContentUnit, SourceRecord.id).join(SourceVersion, SourceVersion.id == ContentUnit.version_id)
                     .join(SourceRecord, SourceRecord.current_version_id == SourceVersion.id)
                     .where(SourceRecord.scope_id.in_(scopes), ContentUnit.unit_kind == "message",
                            ContentUnit.occurred_at > since, ContentUnit.occurred_at <= until,
                            ContentUnit.retention_state == "retained")
                     .order_by(ContentUnit.occurred_at.desc())).all()
    lines, used, clipped = [], 0, 0
    for u, record_id in rows:
        who, side = people.identity(u.author_identity_id)
        is_viktor = side == "Bot" and who.startswith(VIKTOR)
        if viktor != is_viktor or (not viktor and side == "Bot"):
            continue
        ref = refs.add("V" if viktor else "S", u.text, record_id=record_id, unit_id=u.id, date=day(u.occurred_at), who=who)
        line = f"[{ref}] {day(u.occurred_at)} · {who}{' (attributed analysis)' if viktor else f' ({side})'}: {clip(u.text, 1200)}"
        if used + len(line) > budget:
            clipped += 1
            refs.drop(ref)
            continue
        lines.append(line)
        used += len(line)
    empty = "(no posts by Viktor in this period)" if viktor else "(no internal Slack messages in this period)"
    return Block(name, "\n".join(reversed(lines)) or empty, clipped)


def client_emails(s, business: Business, since: datetime, until: datetime, people: People, refs: Refs, budget: int,
                  *, fetch=None, limit: int = 15) -> Block:
    """Admitted client email in the period. The text is read live from Gmail and never stored (BF-2)."""
    rows = s.execute(select(SourceRecord, SourceVersion).join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
                     .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                     .where(RecordAssociation.business_id == business.id, RecordAssociation.status == "associated",
                            SourceRecord.record_kind == "gmail_message", SourceRecord.availability == "available",
                            SourceRecord.occurred_at > since, SourceRecord.occurred_at <= until)
                     .order_by(SourceRecord.occurred_at.desc()).limit(limit + 1)).all()
    clipped = max(0, len(rows) - limit)
    if fetch is None:
        from backend.services.intake.adapters import get_adapter
        fetch = get_adapter("gmail").fetch_body
    lines, used = [], 0
    for r, v in rows[:limit]:
        a = v.attributes
        text = read_email(fetch, r.external_id)
        if text is None:
            clipped += 1  # deleted from Gmail since intake
            continue
        sender = a.get("from") or ""
        ref = refs.add("E", text, record_id=r.id, date=day(r.occurred_at), who=sender,
                       finance=is_finance_email(sender, a.get("subject")), side=people.side_of(sender))
        line = (f"[{ref}] {day(r.occurred_at)} · from {sender} ({people.side_of(sender) if sender else 'unknown'}) · "
                f"subject: {a.get('subject') or '(no subject)'}\n{clip(text, 1500)}")
        if used + len(line) > budget:
            clipped += 1
            refs.drop(ref)
            continue
        lines.append(line)
        used += len(line)
    return Block("client_emails", "\n\n".join(reversed(lines)) or "(no client email in this period)", clipped)


def calendar_event(record, version, people: People, refs: Refs) -> Block:
    a = version.attributes
    ref = refs.add("C", a.get("summary") or "", record_id=record.id, date=day(record.occurred_at), who="Calendar")
    attendees = [f"{x['email']} ({people.side_of(x['email'])})" for x in a.get("attendees", []) if x.get("email")]
    start = record.occurred_at.astimezone(WIA_TZ) if record.occurred_at else None
    return Block("calendar_event", f"[{ref}] {a.get('summary') or 'Call'}\nStarts: "
                                   f"{start.strftime('%Y-%m-%d %H:%M') + ' WIA time' if start else 'unknown'}\n"
                                   f"Attendees: {', '.join(attendees) or 'not listed'}")


def leads_summary(s, business: Business) -> Block:
    """Aggregate lead figures only (never a couple's name, contact or message)."""
    from backend.services.read_models import leads
    try:
        out = leads.client_leads(s, business.slug, "30d")
    except Exception:  # noqa: BLE001 — not a LeadLock client, or no data
        return Block("leads_summary", "(no LeadLock data for this client)")
    if not out["sub_accounts"] and not any(out["coverage"]["records"].values()):
        return Block("leads_summary", "(not a LeadLock client)")
    k = out["kpis"]
    return Block("leads_summary", "Last 30 days: " + ", ".join(
        f"{name.replace('_', ' ')} {v['value']}" + (f" (previous 30 days {v['previous']})" if v.get("previous") is not None else "")
        for name, v in k.items() if isinstance(v, dict) and "value" in v))


def client_list(s) -> Block:
    lines = []
    for b in s.execute(select(Business).where(Business.status == "active").order_by(Business.name)).scalars():
        aliases = s.execute(select(BusinessAlias.alias).where(BusinessAlias.business_id == b.id)).scalars().all()
        lines.append(f"{b.slug}: {b.name}" + (f" (also: {', '.join(a for a in aliases if a != b.name)})" if aliases else ""))
    return Block("client_list", "\n".join(lines) or "(no active clients)")


def activity(s, business: Business, refs: Refs, budget: int) -> Block:
    """The client's merged History events from the current portfolio build (one line per event, oldest first)."""
    events = s.execute(select(ReadModelSnapshot.payload["events"]).where(ReadModelSnapshot.name == "portfolio")).scalar_one_or_none() or []
    mine = sorted((e for e in events if e.get("clientId") == business.slug), key=lambda e: e["date"], reverse=True)
    kept, used, clipped = [], 0, 0
    for e in mine:  # newest first, so the budget keeps the recent past
        line_text = f"{e['date']} · {e['lane']} · {e['title']} ({e.get('detail', '')})"
        if used + len(line_text) > budget:
            clipped += 1
            continue
        kept.append((e, line_text))
        used += len(line_text)
    lines = []
    for e, line_text in reversed(kept):  # refs numbered in reading order, oldest first
        ref = refs.add("H", e["title"], evidence=e.get("sourceId"), date=e["date"], lane=e["lane"])
        lines.append(f"[{ref}] {line_text}")
    note = f"\n(the {clipped} oldest events are not shown)" if clipped else ""
    return Block("activity", "\n".join(lines) + note if lines else "(no activity in the record yet)", clipped)


def meeting_decisions(s, business: Business, refs: Refs, budget: int) -> Block:
    """Decisions and commitments from the KB's own meeting digests (Call 1 output), with their meeting dates."""
    lines, used = [], 0
    runs = s.execute(select(AiRun).where(AiRun.skill == "meeting_digest", AiRun.business_id == business.id,
                                         AiRun.is_current, AiRun.state == "succeeded")
                     .order_by(AiRun.checks["meeting_date"].astext)).scalars().all()
    for run in runs:
        when = (run.checks.get("meeting_date") or "")[:10]
        for kind, items in (("Decided", (run.output or {}).get("decisions", [])), ("Committed", (run.output or {}).get("commitments", []))):
            for item in items:
                text = f"{when} · {kind}: {item['text']}"
                if used + len(text) > budget:
                    break
                ref = refs.add("D", item["text"], record_id=run.subject_id, date=when, lane="Meetings")
                lines.append(f"[{ref}] {text}")
                used += len(text)
    return Block("digests", "\n".join(lines) or "(no meeting digests yet)")


def last_meeting_before(s, business: Business, before: datetime) -> datetime:
    """When the client last met WIA before `before` (a recorded meeting or a past calendar event); 30 days if never."""
    at = s.execute(select(SourceRecord.occurred_at).join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                   .where(RecordAssociation.business_id == business.id, RecordAssociation.status == "associated",
                          SourceRecord.record_kind.in_(("fathom_recording", "calendar_event")),
                          SourceRecord.occurred_at < before - timedelta(hours=1))
                   .order_by(SourceRecord.occurred_at.desc()).limit(1)).scalar_one_or_none()
    return at or before - timedelta(days=30)
