"""The portfolio read model: the KB database in the frontend's data shapes, built whole.

Production: the `portfolio.refresh` maintenance job builds it after a copy stores changes (at most once per
5 minutes) and stores it in `read_model_snapshots`; GET /api/v1/portfolio serves it. Locally,
`python -m backend.scripts.export_frontend_snapshot` writes the same shape to frontend/src/kb-live.local.json.

Reads only the KB database (no provider calls, except the local export's inline logos). Every value is either
copied from an ingested record or derived by a fixed rule stated here. Anything that needs AI extraction or a
human decision (summaries, health, profile story, call briefs) is an explicit "not extracted" state, never
invented.

shortcut: every rebuild loads all associated records and their units in one read; split it per tab once a
rebuild passes ~30 s.
"""
import base64
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.db import transaction
from backend.models.db import (
    Business,
    BusinessAlias,
    ConnectorAccount,
    Contact,
    ContentUnit,
    ProviderIdentity,
    Person,
    RecordAssociation,
    SourceRecord,
    SourceScope,
    SourceVersion,
    ReadModelSnapshot,
    SyncRun,
)
from backend.models.db.base import utcnow
from backend.services.ai import call_types
from backend.workers import queue

NAME = "portfolio"
JOB = "portfolio.refresh"
BUCKET_SECONDS = 300
WIA_TZ = ZoneInfo("America/Chicago")  # WIA's business timezone: dates for deadlines and "today"
IST = ZoneInfo("Asia/Kolkata")  # the mock renders call times in IST and converts with offsetFromIST
TEAM = ["Whitney", "Gisselle", "Carmen", "Jacqueline", "Danielle", "Ivy"]
NOT_EXTRACTED = "Not extracted yet"
KIND = {"slack": "Slack", "gmail": "Gmail", "drive": "Drive", "clickup": "ClickUp", "calendar": "Calendar",
        "fathom": "Fathom"}


def wia_date(dt: datetime | None) -> str:
    return dt.astimezone(WIA_TZ).date().isoformat() if dt else ""


def team_name(name: str | None) -> str:
    """ClickUp/Slack display name → the preview's first-name team list when it's clearly that person."""
    if not name:
        return ""
    first = name.split()[0]
    return first if first in TEAM else name


def initials(name: str) -> str:
    words = [w for w in name.replace("/", " ").split() if w[0].isalnum()]
    return "".join(w[0] for w in words[:2]).upper()


def clip(text: str, n: int = 600) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


QUESTIONNAIRE = re.compile(r"questionnaire", re.IGNORECASE)  # surveys are feedback about WIA, not profile
LOCATION_Q = re.compile(r"^(city|town|location|where (is|are) (your|the) (business|venue|property) located)\b", re.IGNORECASE)
STATE_Q = re.compile(r"^state\b", re.IGNORECASE)
# Never copied into the profile: identifiers, credentials and banking (google_drive_scope.md §5).
SENSITIVE_Q = re.compile(r"\b(ein|tax|ssn|social security|password|login|username|credential|bank|routing|account number|card)\b", re.IGNORECASE)


def questionnaire_pairs(us: list) -> list[tuple[str, str, str]]:
    """(section, question, answer) copied verbatim from a questionnaire's structure.

    Rule: a paragraph ending in '?' followed by an answer unit (table cell or paragraph that is not
    itself a question or heading). Structural copying only; no interpretation of the answer.
    """
    pairs = []
    for q, a in zip(us, us[1:]):
        if q.unit_kind != "doc_paragraph" or not q.text.rstrip().endswith("?"):
            continue
        if a.unit_kind == "doc_heading" or a.text.rstrip().endswith("?"):
            continue
        section = " › ".join(q.locator.get("heading_path") or []) or "Questionnaire"
        pairs.append((section, q.text.strip(), a.text.strip()))
    return [(sec, q, a) for sec, q, a in pairs if not SENSITIVE_Q.search(q)]


def form_pairs(us: list) -> list[tuple[str, str, str]]:
    """(section, question, answer) from a PDF form export: a line ending in '*' (required-field marker)
    is a question; the lines after it, up to the next question, are the answer. Verbatim copy only."""
    lines = [(u.locator.get("page"), line.strip()) for u in us if u.unit_kind == "pdf_page"
             for line in u.text.splitlines() if line.strip()]
    pairs, question, page, answer = [], None, None, []
    for pg, line in lines + [(None, "*")]:
        if line.endswith("*") or line.endswith("?"):  # required-field marker, or an optional question
            if question and answer:
                pairs.append((f"Form · page {page}", question, " ".join(answer)))
            question, page, answer = line.rstrip("* ").strip(), pg, []
        elif question:
            answer.append(line)
    return [(sec, q, a) for sec, q, a in pairs if q and a and len(a) < 2000 and not SENSITIVE_Q.search(q)]


def pick_logo(recs: list) -> tuple | None:
    """P10: a logo file from the client's Drive brand assets, by a fixed preference order."""
    best = None
    for r, v in recs:
        a = v.attributes
        name, mime = (a.get("name") or ""), a.get("mime_type") or ""
        if "logo" not in name.lower() and not any("logo" in p.lower() for p in a.get("folder_path", [])):
            continue
        if mime not in ("image/png", "image/svg+xml", "text/xml", "image/jpeg") or int(a.get("size") or 0) > 1_500_000:
            continue
        n = name.lower()
        # Card banners are wide, so a landscape/horizontal lockup beats a square one.
        score = (3 * ("full color" in n or "colour" in n) + 2 * ("transparent" in n) + 4 * ("landscape" in n or "horizontal" in n)
                 - 3 * ("white" in n) - ("icon" in n) + (mime == "image/png"))
        if best is None or score > best[0]:
            best = (score, r, v)
    return best


def logo_bytes(record, version) -> tuple[str, bytes]:
    """Read one logo file from Drive. The KB itself stores no image bytes."""
    from backend.services.intake.adapters.drive import COMMON, DriveAdapter
    drive = DriveAdapter()
    try:
        data = drive.http.request("GET", f"drive/v3/files/{record.external_id}", params={"alt": "media", **COMMON},
                                  auth_retry=drive._refresh).content
    finally:
        drive.http.close()
    mime = version.attributes.get("mime_type")
    return ("image/svg+xml" if mime == "text/xml" else mime), data


def download_logo(record, version) -> dict | None:
    """Inline copy for the local export only (production links to GET /api/v1/portfolio/logos/<record id>)."""
    try:
        mime, data = logo_bytes(record, version)
    except Exception as exc:  # noqa: BLE001 — a missing logo must not fail the export
        print(f"  logo download failed for {version.attributes.get('name')}: {type(exc).__name__}")
        return None
    return {"dataUri": f"data:{mime};base64,{base64.b64encode(data).decode()}", "file": version.attributes.get("name"),
            "folder": " / ".join(version.attributes.get("folder_path") or [])}


# ---- Profile: the fixed Client Marketing Profile (frontend records.ts PROFILE_SCHEMA) -----------------------------
# Until the KB's profile reading (AI) fills these, a questionnaire answer is placed under the one field its question
# asks about, by these rules, first match wins. Answers that fit no field stay in the questionnaire (its source link).
PROFILE_RULES = [
    ("Offer", "Packages & pricing", r"\b(package|pricing|price|investment|cost|rate|fee)s?\b"),
    ("Offer", "Minimums & policies", r"\b(minimum|deposit|policy|policies|cancellation|guest count)\b"),
    ("Offer", "Capacity & availability", r"\b(capacity|how many (weddings|events)|availability|available dates|book(ing)? (window|out))\b"),
    ("Ideal client", "Budget", r"\bbudget\b"),
    ("Ideal client", "What couples worry about", r"\b(objection|concern|hesitat|worr|pain point|questions? (do )?(couples|clients) ask)"),
    ("Ideal client", "Who their couples are", r"\b(ideal|target|dream) (client|couple|customer|market|audience)|who (are|is) your (client|couple|customer)"),
    ("Differentiators & proof", "Proof to cite", r"\b(review|testimonial|award|featured|press|publication)s?\b"),
    ("Differentiators & proof", "What sets them apart", r"\b(sets? you apart|different|unique|stand out|competitor|why (do )?(couples|clients) choose)"),
    ("Voice", "Words to avoid", r"\b(avoid|never (say|use)|don.?t (want|like) .*(word|say|use))"),
    ("Voice", "Words to use", r"\b(words?|phrases?) (to use|that describe|you love|you use)"),
    ("Voice", "Tone", r"\b(tone|voice|brand personality|describe your brand|brand (feel|vibe))\b"),
    ("Goals", "What success means", r"\b(goal|success|achieve|hope to|looking to accomplish|expectation)s?\b"),
    ("Business", "Location & service area", r"\b(service area|areas? (do )?you (serve|travel)|travel to|where (do|are) you (based|located))"),
    ("Business", "Category", r"\b(type of (business|venue|vendor)|what (kind|type) of)\b"),
    ("Business", "Who they are", r"\b(tell us about|describe) (you|your (business|company|story))|your story|history of (your|the) business|what do you do\b"),
]
PROFILE_RE = [(sec, label, re.compile(rx, re.IGNORECASE)) for sec, label, rx in PROFILE_RULES]
PROFILE_SECTIONS = ["Business", "Offer", "Ideal client", "Differentiators & proof", "Voice", "Goals"]


def profile_field(question: str) -> tuple[str, str] | None:
    return next(((sec, label) for sec, label, rx in PROFILE_RE if rx.search(question)), None)


# ---- History: one event per thing that happened, never one per record ---------------------------------------------
ONBOARDING = re.compile(r"onboard", re.IGNORECASE)
KICKOFF = re.compile(r"onboarding|kick-?off|welcome", re.IGNORECASE)


def _ms(value) -> datetime | None:
    return datetime.fromtimestamp(int(value) / 1000, UTC) if value else None


def history(cid, recs, provider, ev_id, scope_names, client_side, now, text_of=lambda v: ""):
    """(events, milestones, cadence) for one client, by fixed rules (frontend story.ts explains each lane):
    a conversation (Gmail thread, Slack thread) on one day; one meeting a day (invite + recording + transcript);
    tasks created on one day; tasks finished on one day (onboarding lists go to the Onboarding lane); a returned
    questionnaire. Milestones: the first onboarding or kickoff call, onboarding started, onboarding complete."""
    groups: dict = {}

    def add(key, lane, day, title, record, kind, *, who=None, side=None, transcript=None, missed=False, prefer_title=False):
        g = groups.setdefault(key, {"lane": lane, "date": day, "title": title, "sourceId": ev_id[record.id], "kinds": [],
                                    "count": 0, "who": [], "sides": set(), "transcript": False, "seen_meeting": False, "missed": False})
        g["count"] += 1
        if kind not in g["kinds"]:
            g["kinds"].append(kind)
        if prefer_title:
            g["title"] = title
        if who and who not in g["who"]:
            g["who"].append(who)
        if side:
            g["sides"].add(side)
        g["transcript"] = g["transcript"] or bool(transcript)
        g["missed"] = g["missed"] or missed

    onboarding_open, onboarding_done, onboarding_made, cadence = 0, [], [], Counter()
    for r, v in recs:
        p, a = provider(r), v.attributes
        if not r.occurred_at or r.occurred_at > now:
            continue
        day = wia_date(r.occurred_at)
        if p == "gmail":
            sender = (a.get("from") or "").lower()
            add(("gmail", a.get("thread_id") or r.external_id, day), "Communication", day, a.get("subject") or "(no subject)",
                r, "Gmail", who=sender.split("@")[0] or None, side="Client" if client_side(sender) else "WIA")
        elif p == "slack":
            add(("slack", a.get("channel"), a.get("thread_ts") or a.get("ts"), day), "Communication", day,
                clip(text_of(v) or "Slack thread", 90), r, "Slack", side="WIA")
        elif p in ("calendar", "fathom"):
            if a.get("status") == "cancelled":
                continue
            title = a.get("summary") or a.get("title") or "Meeting"
            add(("meeting", day), "Meetings", day, clip(title, 120), r, "Calendar" if p == "calendar" else "Fathom",
                transcript=p == "fathom" and a.get("transcript_segments"), prefer_title=p == "calendar")
            if p == "calendar" and r.parent_external_id:
                cadence[title] += 1
        elif p == "clickup":
            onboarding = bool(ONBOARDING.search(scope_names.get(r.scope_id, "")))
            done = _ms(a.get("date_done") or a.get("date_closed"))
            due = _ms(a.get("due_date"))
            lane = "Onboarding" if onboarding else "Commitments"
            add(("made", lane, day), lane, day, clip(a.get("name") or "Task", 120), r, "ClickUp",
                missed=not onboarding and not done and bool(due and due < now))
            if onboarding:
                onboarding_made.append(day)
                if done:
                    onboarding_done.append(done)
                else:
                    onboarding_open += 1
            if done and done <= now:
                done_lane = "Onboarding" if onboarding else "Work delivered"
                add(("done", done_lane, wia_date(done)), done_lane, wia_date(done), clip(a.get("name") or "Task", 120), r, "ClickUp")
        elif p == "drive" and QUESTIONNAIRE.search(a.get("name") or ""):
            add(("questionnaire", r.id), "Onboarding", day, "Questionnaire returned", r, "Drive")

    events = []
    for key, g in sorted(groups.items(), key=lambda kv: kv[1]["date"]):
        n, kind = g["count"], key[0]
        title, detail = g["title"], " · ".join(g["kinds"])
        event = {"clientId": cid, "date": g["date"], "lane": g["lane"], "sourceId": g["sourceId"]}
        if kind in ("gmail", "slack"):
            detail += f" · {n} message{'' if n == 1 else 's'}" + (f" · {', '.join(g['who'][:3])}" if g["who"] else "")
            event["from"] = "Both" if len(g["sides"]) > 1 else next(iter(g["sides"]), "WIA")
            event["count"] = n
        elif kind == "meeting":
            detail += " · transcript" if g["transcript"] else " · no transcript"
            if not g["transcript"]:
                event["state"] = "no-transcript"
        elif kind == "made":
            if n > 1:
                title = f"{n} onboarding tasks set up" if g["lane"] == "Onboarding" else f"{n} tasks created"
                event["count"] = n
            if g["missed"]:
                event["state"] = "missed"
        elif kind == "done":
            if n > 1:
                title = f"{n} onboarding steps done" if g["lane"] == "Onboarding" else f"{n} tasks done"
                event["count"] = n
            detail += " · done"
        events.append({"id": f"ev-{cid}-{len(events) + 1}", "title": title, "detail": detail, **event})

    milestones = []
    kickoff = next((e for e in events if e["lane"] == "Meetings" and KICKOFF.search(e["title"])), None)
    if onboarding_made:
        milestones.append({"label": "Onboarding started", "date": min(onboarding_made)})
    if kickoff:
        milestones.append({"label": "Kickoff call" if "kick" in kickoff["title"].lower() else "Onboarding call",
                           "date": kickoff["date"], "sourceId": kickoff["sourceId"]})
    if onboarding_made and not onboarding_open and onboarding_done:
        milestones.append({"label": "Onboarding complete", "date": wia_date(max(onboarding_done))})
    milestones = [{"id": f"ms-{cid}-{i}", "clientId": cid, "basis": "Rule", **m} for i, m in enumerate(milestones, 1)]
    rhythm = [f"{title} · recurring, {n} on record" for title, n in cadence.most_common(4) if n >= 2]
    return events, milestones, rhythm


def build(logos: str = "link") -> dict:
    """`logos`: "link" (production: served by the logo route) or "inline" (the local export: data URIs)."""
    now = datetime.now(UTC)
    today = now.astimezone(WIA_TZ).date().isoformat()
    with transaction() as s:
        businesses = s.execute(select(Business).where(Business.status == "active").order_by(Business.name)).scalars().all()
        aliases = defaultdict(list)
        for a in s.execute(select(BusinessAlias)).scalars():
            aliases[a.business_id].append(a.alias)
        accounts = {a.id: a for a in s.execute(select(ConnectorAccount)).scalars()}
        scopes = s.execute(select(SourceScope).where(SourceScope.state == "approved")).scalars().all()
        identities = {i.id: i for i in s.execute(select(ProviderIdentity)).scalars()}
        people = {p.id: p for p in s.execute(select(Person)).scalars()}
        id_by_key = {(i.connector_account_id, i.external_key): i for i in identities.values()}
        contacts = defaultdict(list)
        for c in s.execute(select(Contact).where(Contact.status == "approved")).scalars():
            contacts[c.business_id].append(c)
        last_run = s.execute(select(SyncRun).where(SyncRun.mode == "backfill", SyncRun.state == "succeeded")
                             .order_by(SyncRun.started_at.desc())).scalars().first()
        rows = s.execute(
            select(SourceRecord, SourceVersion, RecordAssociation.business_id)
            .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
            .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
            .where(RecordAssociation.status == "associated")
        ).all()
        version_ids = [v.id for _, v, _ in rows]
        units = defaultdict(list)
        for u in s.execute(select(ContentUnit).where(ContentUnit.version_id.in_(version_ids))
                           .order_by(ContentUnit.version_id, ContentUnit.ordinal)).scalars():
            units[u.version_id].append(u)
        from backend.services.ai import present
        ai = present.load(s, {b.id: b.slug for b in businesses})  # empty while the AI is off

    def provider(rec: SourceRecord) -> str:
        return accounts[rec.connector_account_id].provider

    def ident_name(account_id, key) -> str | None:
        i = id_by_key.get((account_id, key))
        return ((people[i.person_id].name if i.person_id in people else None) or i.display_name or i.email) if i else None

    by_business = defaultdict(list)
    for rec, ver, bid in rows:
        if provider(rec) not in KIND:
            continue  # e.g. LeadLock leads: aggregate figures only, served by the Leads read model, not evidence
        by_business[bid].append((rec, ver))

    out = {"meta": {"asOf": today, "generatedAt": now.isoformat(),
                    "windowStart": wia_date(last_run.window_start) if last_run and last_run.window_start else None,
                    "windowEnd": wia_date(last_run.window_end) if last_run else today,
                    "note": "Source records from the KB. Nothing is AI-extracted yet."},
           "clients": [], "evidence": [], "actions": [], "calls": [], "callMeta": [], "events": [],
           "records": {}, "slackChannels": {}, "timezones": {}, "connectors": [], "syncStatus": [],
           "recaps": [], "reviewItems": [], "milestones": [], "moments": []}

    for b in businesses:
        cid = b.slug
        recs = by_business.get(b.id, [])
        out["recaps"] += ai[b.id]["recaps"]
        out["reviewItems"] += ai[b.id]["review"]
        b_scopes = [sc for sc in scopes if sc.business_id == b.id]
        clickup_scope = next((sc for sc in b_scopes if accounts[sc.connector_account_id].provider == "clickup"), None)
        space = (clickup_scope.parent_name or "").split(" / ")[0] if clickup_scope else ""
        service = space.title() if space.isupper() else space or NOT_EXTRACTED

        # Primary contact: the approved client address that sent the most of this client's emails.
        approved_emails = {c.email for c in contacts[b.id] if c.email}
        approved_domains = {c.domain for c in contacts[b.id] if c.domain}
        senders = Counter(v.attributes.get("from") for r, v in recs if provider(r) == "gmail")
        client_senders = [(e, n) for e, n in senders.most_common()
                          if e and (e in approved_emails or e.split("@")[-1] in approved_domains)]
        primary = client_senders[0][0] if client_senders else next(iter(sorted(approved_emails)), "")
        gmail_account = next((a.id for a in accounts.values() if a.provider == "gmail"), None)
        contact_name = ident_name(gmail_account, primary) if primary else None

        dated = sorted((r.occurred_at for r, _ in recs if r.occurred_at), reverse=False)
        talk = sorted(((r.occurred_at, provider(r)) for r, _ in recs
                       if r.occurred_at and provider(r) in ("slack", "gmail", "fathom") and r.occurred_at <= now),
                      reverse=True)
        weeks = [0] * 12
        for at, _ in talk:
            w = (now - at).days // 7
            if 0 <= w < 12:
                weeks[11 - w] += 1

        out["clients"].append({
            "id": cid, "name": b.name, "initials": initials(b.name), "contact": contact_name or primary or "Unknown",
            "email": primary, "location": NOT_EXTRACTED, "service": service, "type": "retainer",
            "category": NOT_EXTRACTED, "health": "Settling in", "tone": "neutral", "since": "",
            "summary": f"{NOT_EXTRACTED}. The KB holds source records only; it hasn't summarised them yet.",
            "focus": NOT_EXTRACTED, "sentiment": "Not assessed",
            "lastTouch": wia_date(talk[0][0]) if talk else "", "coverage": 0, "activity": weeks,
            "story": NOT_EXTRACTED, "audience": NOT_EXTRACTED, "differentiator": NOT_EXTRACTED,
            "voice": NOT_EXTRACTED, "goal": NOT_EXTRACTED, "profileSource": "",
        })

        slack_scope = next((sc for sc in b_scopes if accounts[sc.connector_account_id].provider == "slack"), None)
        if slack_scope:
            out["slackChannels"][cid] = {"channel": slack_scope.name, "audience": "client"}
        out["timezones"][cid] = {"label": "WIA time (Chicago, CDT)", "offsetFromIST": -10.5}

        # Evidence: one item per source record, all tagged 'Background' (classification needs extraction).
        ev_id = {}
        for r, v in recs:
            p = provider(r)
            us = units.get(v.id, [])
            first = next((u for u in us if not u.is_quoted and not u.provider_generated), None)
            summary_unit = next((u for u in us if u.unit_kind == "provider_summary"), None)
            a = v.attributes
            title = {"slack": f"{slack_scope.name if slack_scope else 'Slack'} message",
                     "gmail": a.get("subject") or "(no subject)", "drive": a.get("name"),
                     "clickup": a.get("name"), "calendar": a.get("summary") or "Calendar event",
                     "fathom": a.get("title")}.get(p) or p
            if us and all(u.domain == "finance" for u in us):
                excerpt, locator = "Finance document: hidden in this preview (F2, admins only).", "Finance"
            elif p == "fathom" and summary_unit:
                excerpt, locator = clip(summary_unit.text), f"Fathom summary · {a.get('transcript_segments', 0)} transcript segments"
            elif first:
                excerpt = clip(first.text)
                locator = {"slack": "Thread reply" if a.get("thread_ts") and a.get("thread_ts") != a.get("ts") else "Slack message",
                           "gmail": f"Email · {a.get('state', '')}", "drive": " › ".join(first.locator.get("heading_path") or []) or "Document",
                           # Every entry is evaluated: a calendar event's status is a plain string.
                           "clickup": f"Task · status “{(a.get('status') or {}).get('status', '') if p == 'clickup' else ''}”",
                           "calendar": "Event description"}.get(p, p)
            else:
                excerpt = "No readable text: file or event metadata only."
                locator = (v.coverage_notes or ["metadata only"])[0]
            author = None
            if first and first.author_identity_id in identities:
                i = identities[first.author_identity_id]
                author = (people[i.person_id].name if i.person_id in people else None) or i.display_name or i.email
            if p == "gmail":
                author = ident_name(r.connector_account_id, a.get("from")) or a.get("from")
            eid = "kb-" + r.id.hex[:12]
            ev_id[r.id] = eid
            out["evidence"].append({
                "id": eid, "clientId": cid, "kind": KIND[p], "title": clip(title, 140), "date": wia_date(r.occurred_at),
                "author": team_name(author) or "Unknown", "excerpt": excerpt, "locator": locator, "tag": "Background",
            })

        # Profile: the fixed Client Marketing Profile. A questionnaire answer fills the field its question asks
        # about (PROFILE_RULES), word for word and flagged unreviewed, until the KB's profile reading replaces it.
        profile_sections: dict[str, list] = {sec: [] for sec in PROFILE_SECTIONS}
        city = state = None
        source_doc = ""
        for r, v in recs:
            if provider(r) != "drive" or not QUESTIONNAIRE.search(v.attributes.get("name") or ""):
                continue
            us = units.get(v.id, [])
            if any(u.domain == "finance" for u in us):
                continue
            pairs = questionnaire_pairs(us) if any(u.unit_kind.startswith("doc_") for u in us) else form_pairs(us)
            for section, question, answer in pairs:
                field = profile_field(question)
                facts = profile_sections[field[0]] if field else None
                if field and sum(f["label"] == field[1] for f in facts) < 2:
                    facts.append({"label": field[1], "value": clip(answer, 500), "tag": "Documented client fact",
                                  "sourceId": ev_id[r.id], "sourceNote": f"Questionnaire answer, not reviewed: “{clip(question, 90)}”"})
                if city is None and LOCATION_Q.search(question):
                    city = clip(answer, 60)
                if state is None and STATE_Q.search(question):
                    state = clip(answer, 30)
            source_doc = source_doc or ev_id[r.id]
        # Location only from the client's own City/State answers; a street or P.O. box is not a location.
        location = ", ".join(x for x in (city, state) if x)
        out["clients"][-1]["location"] = location or NOT_EXTRACTED
        out["clients"][-1]["profileSource"] = source_doc
        if location:
            profile_sections["Business"].append({"label": "Location & service area", "value": location, "tag": "Documented client fact",
                                                 "sourceId": source_doc, "sourceNote": "Questionnaire City/State answers, not reviewed"})
        profile = [{"section": k, "facts": f} for k, f in profile_sections.items()]

        best = pick_logo(recs)
        if best:
            _, rec, ver = best
            logo = download_logo(rec, ver) if logos == "inline" else {
                "src": f"/api/v1/portfolio/logos/{rec.id}", "recordId": str(rec.id), "file": ver.attributes.get("name"),
                "folder": " / ".join(ver.attributes.get("folder_path") or [])}
            if logo:
                out.setdefault("logos", {})[cid] = {**logo, "extracted": today}

        # Actions: ClickUp tasks only (deterministic fields). Conversation commitments need extraction.
        team = Counter()
        for r, v in recs:
            if provider(r) != "clickup":
                continue
            a = v.attributes
            status = a.get("status") or {}
            raw, stype = (status.get("status") or "").lower(), (status.get("type") or "").lower()
            if raw in ("n/a", "na", "not applicable"):
                continue  # 'n/a' is a done-type status in ClickUp; it is not delivery (clickup_scope §5)
            if stype in ("done", "closed"):
                state = "Done"
            elif "progress" in raw:
                state = "In progress"
            elif "hold" in raw or "block" in raw:
                state = "Blocked"
            else:
                state = "Open"
            names = [ident_name(r.connector_account_id, k) for k in a.get("assignee_ids", [])]
            names = [team_name(n) for n in names if n]
            for n in names:
                team[n] += 1
            role = next((f.get("label") for f in a.get("custom_fields", []) if f.get("name") == "Role"), None)
            due_ms = a.get("due_date")
            due = wia_date(datetime.fromtimestamp(int(due_ms) / 1000, UTC)) if due_ms else ""
            out["actions"].append({
                "id": "cu-" + r.external_id, "clientId": cid, "title": a.get("name") or "(untitled task)",
                "owner": names[0] if names else "", "due": due, "status": state,
                "side": "Client" if role == "Client" else "WIA", "acknowledged": False,
                "sourceId": ev_id[r.id], "origin": "ClickUp", "clickupUrl": r.source_url,
                "note": f"ClickUp status “{status.get('status', '')}”"
                        + (f" · also assigned: {', '.join(names[1:])}" if len(names) > 1 else "")
                        + (f" · Role: {role}" if role else ""),
                "lastActivity": wia_date(v.provider_updated_at), "verifyRequired": False,
                "history": [{"date": wia_date(r.occurred_at), "text": "Created in ClickUp"}],
            })

        # Upcoming calls from Calendar, one per real occurrence (copies on several calendars are merged).
        seen = set()
        cal = sorted(((r, v) for r, v in recs if provider(r) == "calendar" and r.occurred_at and r.occurred_at >= now
                      and v.attributes.get("status") != "cancelled"), key=lambda x: x[0].occurred_at)
        for r, v in cal:
            a = v.attributes
            key = (a.get("ical_uid"), r.occurred_at)
            if key in seen:
                continue
            seen.add(key)
            start = r.occurred_at.astimezone(IST)
            end = a.get("end", {}).get("date_time")
            minutes = int((datetime.fromisoformat(end) - r.occurred_at).total_seconds() // 60) if end else 0
            title = a.get("summary") or "Call"
            call_id = "cal-" + r.id.hex[:12]
            attendees = [x["email"] for x in a.get("attendees", []) if x.get("email")]
            out["calls"].append({
                "id": call_id, "clientId": cid, "date": start.date().isoformat(), "time": start.strftime("%H:%M"),
                "duration": f"{minutes} min" if minutes else "", "type": title, "host": "Not set",
                "objective": "Brief not built: Call Preparation is Stage 2 and needs extraction.",
                "context": "", "needs": [], "agenda": [], "opportunity": "", "sourceIds": [ev_id[r.id]],
            })
            built = ai[b.id]["briefs"].get(r.id)  # (brief, built at, Ready|Stale, note) from the call-prep AI
            out["callMeta"].append({
                "id": call_id, "clientId": cid, "date": start.date().isoformat(), "time": start.strftime("%H:%M"),
                "duration": f"{minutes} min" if minutes else "", "title": title, "host": "Not set",
                "attendees": [team_name(ident_name(r.connector_account_id, e) or e) for e in attendees],
                "type": call_types.detect(title).key, "typeSource": "Calendar title",
                **({"state": built[2], "brief": built[0], "builtAt": built[1].astimezone(WIA_TZ).strftime("%Y-%m-%d %H:%M"),
                    **({"stateNote": built[3]} if built[3] else {})} if built else
                   {"state": "Scheduled", "stateNote": "Brief not built yet: call prep runs when the AI is switched on."}),
            })

        # History: merged events, rule milestones and the meeting rhythm (see history()); moments come from the AI.
        scope_names = {sc.id: f"{sc.parent_name or ''} / {sc.name}" for sc in scopes}
        events, marks, rhythm = history(cid, recs, provider, ev_id, scope_names,
                                        lambda e: e in approved_emails or e.split("@")[-1] in approved_domains, now,
                                        lambda v: next((u.text for u in units.get(v.id, []) if not u.is_quoted), ""))
        out["events"] += events
        out["milestones"] += marks
        out["moments"] += ai[b.id]["moments"]

        meetings = []
        for r, v in recs:
            if provider(r) != "fathom":
                continue
            a = v.attributes
            meetings.append({
                "id": "mt-" + r.id.hex[:12], "date": wia_date(r.occurred_at), "type": "Recorded call",
                "title": a.get("title") or "Meeting", "source": "Fathom",
                "transcript": "Available" if a.get("transcript_segments") else "Not found",
                "attendees": ", ".join(i.get("name") or i.get("email") for i in a.get("invitees", [])),
                "decisions": [], "actionIds": [], "sourceId": ev_id[r.id],
            })

        counts = Counter(provider(r) for r, _ in recs)
        def scope_row(p: str, label: str, empty_note: str = "") -> dict:
            mine = [sc for sc in b_scopes if accounts[sc.connector_account_id].provider == p]
            shared = [sc for sc in scopes if sc.business_id is None and accounts[sc.connector_account_id].provider == p]
            linked = mine or shared
            sync = max((sc.last_successful_sync_at for sc in linked if sc.last_successful_sync_at), default=None)
            account = ", ".join(sc.name for sc in mine) or ("Matched by approved client contacts" if shared else "Not linked")
            row = {"source": label, "account": account, "state": "Linked" if linked else "Not linked",
                   "items": counts.get(p, 0), "from": out["meta"]["windowStart"] or ""}
            if sync:
                row["lastSync"] = sync.astimezone(IST).strftime("%I:%M %p").lstrip("0")
            if linked and not counts.get(p):
                row["note"] = empty_note or "No activity collected yet"
            return row

        sources = [scope_row("slack", "Slack"), scope_row("gmail", "Gmail"), scope_row("clickup", "ClickUp"),
                   scope_row("fathom", "Fathom"),
                   {"source": "Zoom history", "account": "Not ingested yet", "state": "Not linked"},
                   scope_row("drive", "Drive"),
                   scope_row("leadlock", "LeadLock", "Lead figures are on the Leads tab"),
                   scope_row("calendar", "Calendar")]
        drive_scope = next((sc for sc in b_scopes if accounts[sc.connector_account_id].provider == "drive"), None)
        out["records"][cid] = {
            "owner": "", "lifecycle": "Onboarding" if space.upper() == "ONBOARDING CLIENTS" else "Active",
            "aliases": [x for x in aliases[b.id] if x != b.name and (" " in x or not x.islower())],  # skip search-only spellings
            "engagements": [{"type": service, "start": ""}],
            "earliestEvidence": wia_date(dated[0]) if dated else "", "processedThrough": out["meta"]["windowEnd"],
            "lastContact": {"date": wia_date(talk[0][0]), "channel": KIND[talk[0][1]]} if talk else {"date": "", "channel": "Slack"},
            # The record header shows these as labels (the mock's links are names, not URLs).
            "links": {"slack": slack_scope.name if slack_scope else "",
                      "drive": " / ".join(x for x in (drive_scope.parent_name, drive_scope.name) if x) if drive_scope else "",
                      "clickup": " · ".join(x for x in ((clickup_scope.parent_name or "").split(" / ")[-1], clickup_scope.name) if x) if clickup_scope else ""},
            "narrative": {"status": "Stale", "approvedBy": "Nobody yet", "approvedOn": "",
                          "staleReason": "Not generated yet: narratives are drafted after extraction, which isn't built."},
            "profile": profile,
            "contacts": [{"name": ident_name(gmail_account, c.email) or c.email, "role": "Approved contact", "email": c.email}
                         for c in contacts[b.id] if c.email]
                        + [{"name": f"Anyone @{c.domain}", "role": "Approved domain", "email": f"@{c.domain}"}
                           for c in contacts[b.id] if c.domain],
            "team": [{"name": n, "role": "ClickUp assignee"} for n, _ in team.most_common()],
            "sources": sources,
            "backfill": {"state": "Complete", "percent": 100, "unprocessed": 0},
            "support": [], "supportCoverage": f"{NOT_EXTRACTED}: support issues are read from email and Slack by the KB.",
            "meetings": meetings, "changes": [], "cadence": rhythm, "sensitivities": [],
        }

    for a in accounts.values():
        if a.provider not in KIND:
            continue
        sync = max((sc.last_successful_sync_at for sc in scopes
                    if sc.connector_account_id == a.id and sc.last_successful_sync_at), default=None)
        n = sum(1 for r, _, _ in rows if r.connector_account_id == a.id)
        out["connectors"].append({"name": {"gmail": "Gmail", "drive": "Google Drive", "calendar": "Google Calendar"}.get(a.provider, KIND[a.provider]),
                                  "kind": KIND[a.provider], "detail": a.display_identity or "", "records": n,
                                  "state": "Connected" if a.state == "active" else "Blocked",
                                  "note": f"{n} client-linked records" + ("" if a.state == "active" else f" · {a.blocked_reason}")})
        if sync:
            out["syncStatus"].append({"source": KIND[a.provider], "at": sync.astimezone(IST).strftime("%I:%M %p").lstrip("0")})

    return out


def request_refresh(s) -> None:
    """Queue one rebuild for the end of the current 5-minute bucket: a work-item insert, deduplicated, so a
    burst of finished copies costs one rebuild."""
    now = utcnow().timestamp()
    bucket = int(now // BUCKET_SECONDS)
    queue.enqueue(s, JOB, "maintenance", f"portfolio:{bucket}", {}, delay_seconds=(bucket + 1) * BUCKET_SECONDS - now)


def refresh() -> dict:
    """Build outside any write transaction, then store it in a short one. Concurrent builds: last one wins."""
    payload = build(logos="link")
    with transaction() as s:
        values = {"built_at": utcnow(), "payload": payload}
        s.execute(insert(ReadModelSnapshot).values(name=NAME, **values)
                  .on_conflict_do_update(index_elements=["name"], set_=values))
    return payload


def current(s) -> ReadModelSnapshot | None:
    return s.get(ReadModelSnapshot, NAME)


def run_job(work_id, lease_token, payload: dict) -> None:
    refresh()
    with transaction() as s:
        queue.complete(s, work_id, lease_token)
