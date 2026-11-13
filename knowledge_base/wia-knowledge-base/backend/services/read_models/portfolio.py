"""The portfolio read model: the KB database in the frontend's data shapes, built whole.

Production: the `portfolio.refresh` maintenance job builds it after a copy stores changes (at most once per
5 minutes) and stores it in `read_model_snapshots`; GET /api/v1/portfolio serves it. Locally,
`python -m backend.scripts.export_frontend_snapshot` writes the same shape to frontend/src/kb-live.local.json.

Reads only the KB database (no provider calls, except the local export's inline logos). Every value is either
copied from an ingested record or derived by a fixed rule stated here. Anything that needs AI extraction or a
human decision (summaries, health, profile story, call briefs) is an explicit "not extracted" state, never
invented.

Scale: it loads active clients' linked records (LeadLock excluded), only the few units per record it reads
(`needed_units`, streamed), and one build runs at a time. shortcut: the snapshot is still one payload holding
every evidence item, so it grows with history (~0.4 KB per record); split it per client once loads get slow.
"""
import base64
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import insert

from backend.db import engine, transaction
from backend.logging.config import get_logger
from backend.models.db import (
    AccountTeamMember,
    Business,
    BusinessAlias,
    ConnectorAccount,
    Contact,
    ContentUnit,
    MeetingLink,
    Person,
    PersonAddress,
    ProviderIdentity,
    ReadModelSnapshot,
    RecordAssociation,
    SourceRecord,
    SourceScope,
    SourceVersion,
    SyncRun,
)
from backend.models.db.base import utcnow
from backend.services.callprep import skill_files
from backend.workers import queue

NAME = "portfolio"
JOB = "portfolio.refresh"
BUCKET_SECONDS = 300
CALL_WINDOW_MAX_DAYS = 90  # "since the last call" never reaches further back (keeps the card and the build small)
BUILD_LOCK = 7_301_126  # pg advisory key: one build at a time across workers (the sync sweep uses 7_301_125)
log = get_logger("portfolio")
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


SLACK_MARKUP = re.compile(r"<([@#!])?([^>|]+)(?:\|([^>]*))?>")


def slack_text(text: str, user_name=lambda uid: None) -> str:
    """Slack's markup as people read it: <@U123> -> @Name, <#C1|general> -> #general, <url|label> -> label."""
    def plain(m):
        kind, ref, label = m.groups()
        if kind == "@":
            return "@" + ((user_name(ref) or "").split(" ")[0] or "someone")
        if kind == "#":
            return "#" + (label or "channel")
        if kind == "!":
            return "@" + (label or ref.split("^")[0])
        return label or ref
    return SLACK_MARKUP.sub(plain, text or "")


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


def meeting_list(recs, provider, ev_id, links, name_of, now):
    """Every past meeting with the client (Meetings tab), newest first, by rule:
    - each calendar meeting with a client contact, not cancelled; copies of one invite on several calendars count once;
    - each Fathom recording, attached to that day's calendar meeting closest in time, or listed on its own;
    - the link: a link a person added (`meeting_links`) wins, else the Fathom recording; with neither the meeting
      says "No link" and the team can add one (most older calls were on Zoom, recorded outside these sources)."""
    calendar, recordings = {}, []
    for r, v in recs:
        p, a = provider(r), v.attributes
        if not r.occurred_at or r.occurred_at > now or a.get("status") == "cancelled":
            continue
        if p == "calendar":
            calendar.setdefault((a.get("ical_uid") or r.external_id, r.occurred_at), (r, v))
        elif p == "fathom":
            recordings.append((r, v))
    meetings = {r.id: {"record": r, "title": v.attributes.get("summary") or "Meeting", "fathom": None,
                       "people": [x.get("email") for x in v.attributes.get("attendees") or [] if x.get("email")]}
                for r, v in calendar.values()}
    for r, v in recordings:
        same_day = [m for m in meetings.values() if m["fathom"] is None and wia_date(m["record"].occurred_at) == wia_date(r.occurred_at)]
        target = min(same_day, key=lambda m: abs(m["record"].occurred_at - r.occurred_at), default=None)
        if target is None:
            target = meetings[r.id] = {"record": r, "title": v.attributes.get("title") or "Meeting", "fathom": None,
                                       "people": [i.get("email") for i in v.attributes.get("invitees") or [] if i.get("email")]}
        target["fathom"] = (r, v)
    out, call_kinds = [], skill_files.load_all()
    for m in sorted(meetings.values(), key=lambda m: m["record"].occurred_at, reverse=True):
        r, fathom = m["record"], m["fathom"]
        transcript = "Available" if fathom and fathom[1].attributes.get("transcript_segments") else None
        added = links.get(r.id) or (links.get(fathom[0].id) if fathom else None)
        link = added or (fathom[0].source_url if fathom else None)
        out.append({
            "id": "mt-" + r.id.hex[:12], "recordId": str(r.id), "date": wia_date(r.occurred_at),
            "type": skill_files.detect(call_kinds, m["title"]).name, "title": m["title"],
            "source": "Fathom" if fathom else "Calendar",
            "transcript": transcript or ("Recording link only" if link else "Not found"),
            **({"link": link, "linkSource": "Added by the team" if added else "Fathom"} if link else {}),
            "attendees": ", ".join(dict.fromkeys(name_of(e) for e in m["people"][:6])),
            "decisions": [], "actionIds": [], "sourceId": ev_id[(fathom[0] if fathom else r).id],
        })
    return out


def client_comms(recs, provider, ev_id, side_of, name_of, slack_author, now, days=30):
    """Communication WITH the client: the Now tab's "Communication since the last call" card, and the record's last
    contact.

    The window starts on the day of the client's most recent call (a calendar invite or Fathom recording, not
    cancelled, not in the future), so the card answers "what has happened since we last spoke". A call today
    starts it today. No call on record: the last `days` days.

    - Email: "Client" when the sender is an approved client contact or domain, "WIA" when it is WIA's own people or
      shared inbox; anyone else (partners, unknown) isn't client communication. The subject is the text: bodies
      are never stored (BF-2).
    - Calls: one per meeting a day, from the calendar invite or the Fathom recording (the invite's title wins).
    - Slack: WIA's workspace is internal-only, so the client's channel is the team working on the client: one
      "Team" item per thread (its first message, who took part, how many messages). A message a client wrote, if
      one ever appears, is "Client". Team posts are never contact with the client, so never the last contact.
    Returns (items in the window, newest first; the latest client contact of all time or None; the window as
    {"since": date, "call": the call's title or None})."""
    items, calls, threads = [], {}, {}
    for r, v in recs:
        p, a = provider(r), v.attributes
        if not r.occurred_at or r.occurred_at > now:
            continue
        day = wia_date(r.occurred_at)
        if p == "gmail":
            sender = (a.get("from") or "").lower()
            side = side_of(sender)
            if side:
                items.append({"id": f"cm-{r.id.hex[:12]}", "date": day, "channel": "Gmail", "from": side,
                              "who": name_of(sender), "text": a.get("subject") or "(no subject)",
                              "sourceId": ev_id[r.id], "_at": r.occurred_at})
        elif p == "slack":
            who, party, text = slack_author(v)
            if party == "client":
                items.append({"id": f"cm-{r.id.hex[:12]}", "date": day, "channel": "Slack", "from": "Client",
                              "who": who, "text": clip(text, 160), "sourceId": ev_id[r.id], "_at": r.occurred_at})
            elif party == "internal":  # bots and automated posts are left out
                key = (a.get("channel"), a.get("thread_ts") or a.get("ts") or str(r.id))
                t = threads.setdefault(key, {"first": None, "people": [], "n": 0, "_at": r.occurred_at})
                if t["first"] is None or r.occurred_at < t["first"][0]:
                    t["first"] = (r.occurred_at, r, text)
                t["people"].append(who)
                t["n"] += 1
                t["_at"] = max(t["_at"], r.occurred_at)
        elif p in ("calendar", "fathom") and a.get("status") != "cancelled":
            people = [x.get("email") for x in a.get("attendees") or a.get("invitees") or [] if x.get("email")]
            call = calls.get(day)
            if call is None or (p == "calendar" and call["channel"] == "Fathom"):
                calls[day] = {"id": f"cm-{r.id.hex[:12]}", "date": day, "channel": "Calendar" if p == "calendar" else "Fathom",
                              "from": "Call", "who": ", ".join(dict.fromkeys(name_of(e) for e in people[:4])) or "Attendees not listed",
                              "text": a.get("summary") or a.get("title") or "Meeting", "sourceId": ev_id[r.id], "_at": r.occurred_at}
    for t in threads.values():
        _, r, text = t["first"]
        people = list(dict.fromkeys(t["people"]))
        items.append({"id": f"cm-{r.id.hex[:12]}", "date": wia_date(t["_at"]), "channel": "Slack", "from": "Team",
                      "who": ", ".join(people[:3]) + (f" +{len(people) - 3}" if len(people) > 3 else ""),
                      "text": clip(text, 160) + (f" · {t['n']} messages" if t["n"] > 1 else ""),
                      "sourceId": ev_id[r.id], "_at": t["_at"]})
    items = sorted([*items, *calls.values()], key=lambda c: c["_at"], reverse=True)
    last = next((c for c in items if c["from"] != "Team"), None)
    last_call = max(calls.values(), key=lambda c: c["_at"], default=None)
    if last_call and now - last_call["_at"] > timedelta(days=CALL_WINDOW_MAX_DAYS):
        last_call = None  # a call that long ago isn't "the last call" worth anchoring on: the last `days` days
    if last_call:  # from the start of that call's day (WIA time), so the call itself and that day's mail count
        since = last_call["date"]
        window = {"since": since, "call": last_call["text"]}
        recent = [c for c in items if c["date"] >= since]
    else:
        cutoff = now - timedelta(days=days)
        window = {"since": wia_date(cutoff), "call": None}
        recent = [c for c in items if c["_at"] >= cutoff]
    return [{k: v for k, v in c.items() if k != "_at"} for c in recent], last, window


RELATIONSHIP = re.compile(r"monthly (consulting|strategy|reporting)|check-?in email|recap email|upload (the )?recording", re.IGNORECASE)
# ClickUp's "Role" field, in WIA's role split (12 Nov): ads = Google and Meta (one person, or Google and Meta split
# between two), LeadLock copy/sequences/page design, technical LeadLock work, creatives. "Assistant" is the shared
# support account, not a person.
ROLE_FIELD = {"ads manager": "ads", "ghl specialist": "Technical LeadLock", "leadlock designer": "LeadLock copy, sequences & page design",
              "marketing assistant": "Creatives"}
OWNER_WEIGHT = {"relationship": 3, "call": 2, "email": 1}


def team_signals(recs, provider, scope_names, person_of, slack_person, now, days=90, ahead=60):
    """Who does the work for one client, from the last `days` (calls also `ahead` days scheduled).
    person_of(kind, value) / slack_person(version) give a staff or contractor name, else None.
    Returns owner signals [(name, kind, at)], ClickUp role tasks Counter[(name, role)], Slack posts Counter[name]."""
    since, until = now - timedelta(days=days), now + timedelta(days=ahead)
    owner, roles, slack, calls = [], Counter(), Counter(), set()
    for r, v in recs:
        at, a, p = r.occurred_at, v.attributes, provider(r)
        if not at or at < since:
            continue
        if p == "calendar" and at <= until and a.get("status") != "cancelled":
            for x in a.get("attendees") or []:
                name = person_of("email", x.get("email"))
                if name and (name, wia_date(at)) not in calls:  # one per person per call day
                    calls.add((name, wia_date(at)))
                    owner.append((name, "call", at))
        if at > now:
            continue
        if p == "clickup":
            people = [n for n in (person_of("clickup_user", str(i)) for i in a.get("assignee_ids") or []) if n]
            if "client management" in scope_names.get(r.scope_id, "").lower() and RELATIONSHIP.search(a.get("name") or ""):
                owner += [(n, "relationship", at) for n in people]
            role = next((f.get("label") for f in a.get("custom_fields") or [] if f.get("name") == "Role"), None)
            if role and role.lower() in ROLE_FIELD:
                roles.update((n, ROLE_FIELD[role.lower()]) for n in people)
        elif p == "gmail" and (name := person_of("email", a.get("from"))):
            owner.append((name, "email", at))
        elif p == "slack" and (name := slack_person(v)):
            slack[name] += 1
    return owner, roles, slack


def suggest_owner(signals, leaders, now, confirmed=None) -> dict:
    """Account owner from the work: relationship tasks x3, client calls x2, direct emails x1. Leadership isn't
    scored; the client-communication lead (leaders[0]) is the fallback when the evidence is thin."""
    score, kinds = Counter(), defaultdict(Counter)
    for name, kind, _ in signals:
        if name not in leaders:
            score[name] += OWNER_WEIGHT[kind]
            kinds[name][kind] += 1
    (top, s1), (_, s2) = (score.most_common(2) + [(None, 0), (None, 0)])[:2]
    k = kinds[top] if top else Counter()
    confidence = ("High" if top and k["relationship"] >= 2 and s1 >= 2 * s2
                  else "Medium" if top and len(k) >= 2 and s1 >= 1.5 * s2 else "Low")
    why = ", ".join(f"{n} {label}{'' if n == 1 else 's'}" for label, n in
                    (("relationship task", k["relationship"]), ("client call", k["call"]), ("email", k["email"])) if n)
    out = {"name": top if confidence != "Low" else (leaders[0] if leaders else ""), "confidence": confidence,
           "why": f"{why} in 90 days" if why else "No relationship tasks, client calls or emails in 90 days"}
    if confidence == "Low" and top:
        out["lead"] = top
    if (confirmed and confidence != "Low" and top != confirmed
            and not any(n == confirmed and at >= now - timedelta(days=60) for n, _, at in signals)):
        out["changed"] = True  # the confirmed owner has gone quiet while someone else clearly runs the account
    return out


def account_team(roles: Counter, slack: Counter, functions: dict) -> list[dict]:
    """On the account = 2+ tasks in a ClickUp role, or 10+ posts in the client's Slack, in the window.
    Ads follow the account: where a Meta specialist is on it, the person who does both handles Google there."""
    def ads(fn) -> str:
        return (" & ".join(x for x, f in (("Google", "ads_google"), ("Meta", "ads_meta")) if f in fn) + " Ads").strip()
    def by_function(fn) -> str:
        if "leadership" in fn:
            return "Leadership"
        if {"ads_google", "ads_meta"} & set(fn):
            return ads(fn)
        labels = {"leadlock_technical": "Technical LeadLock", "leadlock_copy": "LeadLock copy, sequences & page design", "creative": "Creatives",
                  "operations": "Operations", "support": "Operations"}
        return next((labels[f] for f in fn if f in labels), "Team member")
    team = defaultdict(list)
    for (name, role), n in roles.items():
        if n >= 2:
            team[name].append(ads(functions.get(name, [])) if role == "ads" else role)
    for name, n in slack.items():
        if n >= 10 and name not in team:
            team[name].append(by_function(functions.get(name, [])))
    if any("Meta Ads" in rs for rs in team.values()):
        team = {n: ["Google Ads" if r == "Google & Meta Ads" else r for r in rs] for n, rs in team.items()}
    return [{"name": n, "role": " · ".join(dict.fromkeys(rs))} for n, rs in sorted(team.items())]


ROLE_FUNCTION = {"Technical LeadLock": "leadlock_technical", "LeadLock copy, sequences & page design": "leadlock_copy",
                 "Creatives": "creative"}
META = re.compile(r"\b(meta|facebook|fb|instagram|ig)\b", re.IGNORECASE)
GOOGLE = re.compile(r"\b(google|search|pmax|performance max|youtube)\b", re.IGNORECASE)


def suggest_task_owner(role, title, team, functions) -> dict | None:
    """Who should own a task no person holds (assigned to the shared support account, or to no one), from its ClickUp
    Role and WIA's role split: that role's person on this account's team, else whoever does that work at WIA.
    A suggestion only: nothing is written to the KB or ClickUp."""
    want = ROLE_FIELD.get((role or "").lower())
    if not want:
        return None  # Assistant, Client, CEO, All Team Members: the split doesn't name a person
    if want == "ads":
        channel = "Meta" if META.search(title or "") else "Google" if GOOGLE.search(title or "") else None
        label = f"{channel} Ads" if channel else "Ads"
        names = [t["name"] for t in team if "Ads" in t["role"] and (channel is None or channel in t["role"])]
        fallback = [n for n, fn in functions.items() if {"ads_google", "ads_meta"} <= set(fn)]  # does both
    else:
        label = want
        names = [t["name"] for t in team if want in t["role"]]
        fallback = [n for n, fn in functions.items() if ROLE_FUNCTION[want] in fn]
    where = "on this account's team"
    if not names:
        names, where = fallback, "at WIA (not seen on this account yet)"
    if not names:
        return None
    return {"name": " or ".join(n.split()[0] for n in names[:2]), "why": f"ClickUp Role “{role}” → {label} {where}"}


# Dubsado's own notices (WIA's templates), sent from hello@ to the signer. Replies and forwards aren't the signing.
CONTRACT_MAIL = re.compile(r"(contract completed for)|(proposal signed)", re.IGNORECASE)
CONTRACT_FILE = re.compile(r"countersigned (contract|agreement)", re.IGNORECASE)
ENGAGEMENT_LIST = re.compile(r"onboarding|checklist", re.IGNORECASE)


def engagement_type(list_name: str, space: str = "") -> str:
    n = list_name.lower()
    if "leadlock" in n:
        return "LeadLock"
    if "landing page" in n:
        return "Ads landing page"
    return "Google + Meta ads" if "google" in n or "meta" in n else space or "Engagement"


def engagements(recs, provider, list_of, space="", has_leadlock=False) -> list[dict]:
    """One engagement per ClickUp onboarding list. Its start is the agreement behind it, best source first: the signed-
    agreement email, the countersigned contract file, the checklist's "Countersign Contract" task; else estimated from
    the list's first task. Sales calls, intro emails and file dates are never a start."""
    lists, evidence = defaultdict(list), []
    for r, v in recs:
        a, p = v.attributes, provider(r)
        if not r.occurred_at:
            continue
        if p == "clickup" and ENGAGEMENT_LIST.search(name := list_of(r.scope_id)) and "client management" not in name.lower():
            lists[r.scope_id].append((r, a))
        elif p == "gmail" and (m := CONTRACT_MAIL.match(a.get("subject") or "")):
            # the contract is the agreement; a signed proposal comes a few days before it
            evidence.append((1, r.occurred_at, None, "From the signed agreement") if m[1]
                            else (1.5, r.occurred_at, None, "From the signed proposal"))
        elif p == "drive" and CONTRACT_FILE.search(a.get("name") or ""):
            n = a["name"].lower()
            hint = "LeadLock" if "leadlock" in n else "Google + Meta ads" if re.search(r"elevate|ads management|google|meta", n) else None
            evidence.append((2, r.occurred_at, hint, "From the countersigned contract"))
    out = []
    for sid, tasks in lists.items():
        kind = engagement_type(list_of(sid), space)
        begun = min(r.occurred_at for r, _ in tasks)
        signed = min((_ms(a["date_done"]) for _, a in tasks if a.get("date_done")
                      and (a.get("name") or "").strip().lower() == "countersign contract"), default=None)
        wanted = "Google + Meta ads" if kind == "Ads landing page" else kind
        fits = sorted((e for e in evidence if e[2] in (None, wanted) and begun - timedelta(days=60) <= e[1] <= begun + timedelta(days=14)),
                      key=lambda e: (e[0], abs(e[1] - begun)))
        rank, at, _, basis = fits[0] if fits else (3, signed, None, "From the onboarding checklist") if signed else (
            4, begun, None, "Estimated from the onboarding start")
        e = {"type": kind, "start": wia_date(at), "basis": basis}
        if rank < 3:
            e["signed"] = e["start"]
        if signed and rank < 3 and abs(signed - at) > timedelta(days=14):  # e.g. checklists ticked in a batch weeks later
            local = signed.astimezone(WIA_TZ)
            e["note"] = f"The onboarding checklist marks it signed on {local:%b} {local.day}, {local.year}"
        out.append(e)
    if has_leadlock and not any(e["type"] == "LeadLock" for e in out):
        out.append({"type": "LeadLock", "start": "", "basis": "Start not recorded"})
    return sorted(out, key=lambda e: e["start"] or "9999")


UNITS = {"slack": "channel", "gmail": "mailbox", "clickup": "list", "fathom": "recorder", "drive": "folder",
         "leadlock": "sub-account", "calendar": "calendar"}


def scope_copy(runs) -> tuple[str, datetime | None]:
    """How much history one linked account/list holds, from its backfill runs (newest first). One finished
    full-history copy is enough: a later re-check that fails doesn't remove what was copied."""
    full = [r for r in runs if r.window_start is None]
    if any(r.state == "succeeded" for r in full):
        return "complete", None
    if full:
        return ("copying" if full[0].state in ("queued", "running") else "incomplete"), full[0].started_at
    windows = [r.window_start for r in runs if r.state == "succeeded"]
    return ("window", min(windows)) if windows else ("none", None)


def source_copy(copies: list, unit: str, blocked: bool = False) -> tuple[str, str]:
    """Accounts & sources row state and why: Linked only once every linked account holds its whole history."""
    if blocked:
        return "Blocked", "Access lost: reconnect it in Settings → Connections"
    n, notes = len(copies), []
    def part(k: int) -> str:
        return f" for {k} of {n} {unit}s" if n > 1 else ""
    def day(dt) -> str:
        return f"{dt.astimezone(WIA_TZ):%b} {dt.astimezone(WIA_TZ).day}, {dt.astimezone(WIA_TZ).year}"
    for kind, text in (("copying", "Full history still copying{p} (started {d})"), ("incomplete", "Full history copy stopped short{p}"),
                       ("window", "Only copied from {d}{p}"), ("none", "History not copied yet{p}")):
        hit = [at for k, at in copies if k == kind]
        if hit:
            notes.append(text.format(p=part(len(hit)), d=day(min(hit)) if hit[0] else ""))
    return ("Partial", "; ".join(notes)) if notes else ("Linked", "")


def needed_units(s, versions, whole: set) -> dict:
    """Each version's units, cut to the ones the build reads, streamed, so memory holds a few units per record
    instead of every transcript segment and paragraph. `versions` is a subquery (no bind parameter per record:
    Postgres refuses more than 65,535).

    Kept per version, in ordinal order: the first unit, the first not quoted, the first not quoted and not
    provider-generated, the first provider summary, and the first not finance. That answers every question the
    build asks exactly as the full list would: `us[0]`, `next(not quoted ...)`, `next(provider_summary)` and
    `all(finance)`. Versions in `whole` (profile questionnaires) keep every unit."""
    out, filled = defaultdict(list), defaultdict(set)
    q = (select(ContentUnit).where(ContentUnit.version_id.in_(versions))
         .order_by(ContentUnit.version_id, ContentUnit.ordinal).execution_options(yield_per=2000))
    for u in s.scalars(q):
        if u.version_id in whole:
            out[u.version_id].append(u)
            continue
        roles = {"first"}
        if not u.is_quoted:
            roles |= {"plain", "own"} if not u.provider_generated else {"plain"}
        if u.unit_kind == "provider_summary":
            roles.add("summary")
        if u.domain != "finance":
            roles.add("not_finance")
        if roles - filled[u.version_id]:
            filled[u.version_id] |= roles
            out[u.version_id].append(u)
    return out


def build(logos: str = "link") -> dict:
    """`logos`: "link" (production: served by the logo route) or "inline" (the local export: data URIs)."""
    now = datetime.now(UTC)
    today = now.astimezone(WIA_TZ).date().isoformat()
    with transaction() as s:
        # One read of every linked record at full history can outlast the app's 30 s per-statement limit; this is
        # a background job, so give it room instead of failing every rebuild.
        s.execute(sql_text("SET LOCAL statement_timeout = '300s'"))
        businesses = s.execute(select(Business).where(Business.status == "active").order_by(Business.name)).scalars().all()
        aliases = defaultdict(list)
        for a in s.execute(select(BusinessAlias)).scalars():
            aliases[a.business_id].append(a.alias)
        accounts = {a.id: a for a in s.execute(select(ConnectorAccount)).scalars()}
        scopes = s.execute(select(SourceScope).where(SourceScope.state == "approved")).scalars().all()
        identities = {i.id: i for i in s.execute(select(ProviderIdentity)).scalars()}
        people = {p.id: p for p in s.execute(select(Person)).scalars()}
        workers = {pid: p for pid, p in people.items() if p.kind in ("staff", "contractor") and not p.merged_into_id}
        worker_at = {(a.kind, a.value.lower()): workers[a.person_id].name
                     for a in s.execute(select(PersonAddress)).scalars() if a.person_id in workers}
        def slack_name(uid: str) -> str | None:
            return worker_at.get(("slack_user", uid.lower()))
        functions = {p.name: p.functions or [] for p in workers.values()}
        # Fallback owner: leadership, client-communication lead first.
        leaders = sorted((p.name for p in workers.values() if "leadership" in (p.functions or [])),
                         key=lambda n: "client_communication" not in functions[n])
        confirmed_team = defaultdict(list)
        for m in s.execute(select(AccountTeamMember).where(AccountTeamMember.status == "confirmed",
                                                           AccountTeamMember.ended_on.is_(None))).scalars():
            if m.person_id in people:
                confirmed_team[m.business_id].append((people[m.person_id].name, m.role))
        id_by_key = {(i.connector_account_id, i.external_key): i for i in identities.values()}
        contacts = defaultdict(list)
        for c in s.execute(select(Contact).where(Contact.status == "approved")).scalars():
            contacts[c.business_id].append(c)
        runs_by_scope = defaultdict(list)
        for run in s.execute(select(SyncRun).where(SyncRun.mode == "backfill").order_by(SyncRun.started_at.desc())).scalars():
            runs_by_scope[run.scope_id].append(run)
        last_run = max((r for runs in runs_by_scope.values() for r in runs if r.state == "succeeded"),
                       key=lambda r: r.started_at, default=None)
        # Only what a screen shows: links to active clients, from providers with evidence (LeadLock has its own
        # Leads read model). Inactive clients' records stay stored; they just aren't loaded here.
        def shown(*columns):
            return (select(*columns)
                    .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                    .join(Business, Business.id == RecordAssociation.business_id)
                    .join(ConnectorAccount, ConnectorAccount.id == SourceRecord.connector_account_id)
                    .where(RecordAssociation.status == "associated", Business.status == "active",
                           ConnectorAccount.provider.in_(KIND)))
        rows = s.execute(shown(SourceRecord, SourceVersion, RecordAssociation.business_id)
                         .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)).all()
        questionnaires = {v.id for r, v, _ in rows if accounts[r.connector_account_id].provider == "drive"
                          and QUESTIONNAIRE.search(v.attributes.get("name") or "")}
        units = needed_units(s, shown(SourceRecord.current_version_id), questionnaires)
        from backend.services.ai import present
        ai = present.load(s, {b.id: b.slug for b in businesses})  # empty while the AI is off
        links = {m.record_id: m.url for m in s.execute(select(MeetingLink)).scalars()}  # added by the team

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
        out["actions"] += ai[b.id]["actions"]  # AI proposals an admin approved; proposed ones stay in review
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
        unowned = []  # (action, role) for open tasks no person holds; owners are suggested once the team is known
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
            role = next((f.get("label") for f in a.get("custom_fields", []) if f.get("name") == "Role"), None)
            due_ms = a.get("due_date")
            due = wia_date(datetime.fromtimestamp(int(due_ms) / 1000, UTC)) if due_ms else ""
            action = {
                "id": "cu-" + r.external_id, "clientId": cid, "title": a.get("name") or "(untitled task)",
                "owner": names[0] if names else "", "due": due, "status": state,
                "side": "Client" if role == "Client" else "WIA", "acknowledged": False,
                "sourceId": ev_id[r.id], "origin": "ClickUp", "clickupUrl": r.source_url,
                "note": f"ClickUp status “{status.get('status', '')}”"
                        + (f" · also assigned: {', '.join(names[1:])}" if len(names) > 1 else "")
                        + (f" · Role: {role}" if role else ""),
                "lastActivity": wia_date(v.provider_updated_at), "verifyRequired": False,
                "history": [{"date": wia_date(r.occurred_at), "text": "Created in ClickUp"}],
            }
            out["actions"].append(action)
            if state != "Done" and role != "Client" and not any(
                    worker_at.get(("clickup_user", str(k).lower())) for k in a.get("assignee_ids", [])):
                unowned.append((action, role))

        # History: merged events, rule milestones and the meeting rhythm (see history()); moments come from the AI.
        scope_names = {sc.id: f"{sc.parent_name or ''} / {sc.name}" for sc in scopes}
        events, marks, rhythm = history(cid, recs, provider, ev_id, scope_names,
                                        lambda e: e in approved_emails or e.split("@")[-1] in approved_domains, now,
                                        lambda v: slack_text(next((u.text for u in units.get(v.id, []) if not u.is_quoted), ""), slack_name))
        out["events"] += events
        out["milestones"] += marks
        out["moments"] += ai[b.id]["moments"]

        # Now tab: communication WITH the client (client_comms); it also sets the last-contact date and channel.
        def side_of(email):
            if email in approved_emails or email.split("@")[-1] in approved_domains:
                return "Client"
            i = id_by_key.get((gmail_account, email))
            return "WIA" if i and i.party in ("internal", "shared_mailbox") else None

        def name_of(email):
            i = id_by_key.get((gmail_account, email))
            person = people.get(i.person_id) if i and i.person_id else None
            # a shared inbox's roster name describes the inbox, not who wrote
            return (person.name if person and person.kind != "shared_mailbox" else None) or (i.display_name if i else None) or email

        def slack_author(v):
            u = next((u for u in units.get(v.id, []) if not u.is_quoted), None)
            i = identities.get(u.author_identity_id) if u else None
            return ((people[i.person_id].name if i and i.person_id in people else None) or (i.display_name if i else None) or "Unknown",
                    i.party if i else None, slack_text(u.text, slack_name) if u else "")

        comms, last_comm, comms_window = client_comms(recs, provider, ev_id, side_of, name_of, slack_author, now)
        out.setdefault("comms", {})[cid] = comms
        out["clients"][-1]["lastTouch"] = last_comm["date"] if last_comm else ""

        meetings = meeting_list(recs, provider, ev_id, links, name_of, now)

        def person_of(kind, value):
            return worker_at.get((kind, (value or "").lower()))
        def slack_person(v):
            u = units.get(v.id, [None])[0]
            i = identities.get(u.author_identity_id) if u else None
            return workers[i.person_id].name if i and i.person_id in workers else None
        owner_sig, role_tasks, slack_posts = team_signals(recs, provider, scope_names, person_of, slack_person, now)
        owner = next((n for n, role in confirmed_team[b.id] if role == "owner"), "")
        owner_hint = suggest_owner(owner_sig, leaders, now, owner or None)
        ROLE_LABEL = {"ads_google": "Google Ads", "ads_meta": "Meta Ads", "copy": "LeadLock copy", "technical": "LeadLock technical",
                      "creative": "Creative", "operations": "Operations"}
        confirmed = [{"name": n, "role": f"{ROLE_LABEL[r]} (confirmed)"} for n, r in confirmed_team[b.id] if r != "owner"]
        team_rows = confirmed + [t for t in account_team(role_tasks, slack_posts, functions)
                                 if t["name"] not in {c["name"] for c in confirmed}]
        for action, role in unowned:
            if hint := suggest_task_owner(role, action["title"], team_rows, functions):
                action["suggestedOwner"], action["suggestedWhy"] = hint["name"], hint["why"]

        counts = Counter(provider(r) for r, _ in recs)
        first = {}
        for r, _ in recs:
            if r.occurred_at and (provider(r) not in first or r.occurred_at < first[provider(r)]):
                first[provider(r)] = r.occurred_at
        copied = []  # (complete?) per linked account/list, for the record's overall history-copy progress
        def scope_row(p: str, label: str, empty_note: str = "") -> dict:
            mine = [sc for sc in b_scopes if accounts[sc.connector_account_id].provider == p]
            shared = [sc for sc in scopes if sc.business_id is None and accounts[sc.connector_account_id].provider == p]
            linked = mine or shared
            if not linked:
                return {"source": label, "account": "Not linked", "state": "Not linked", "items": 0}
            copies = [scope_copy(runs_by_scope.get(sc.id, [])) for sc in linked]
            copied.extend(k == "complete" for k, _ in copies)
            state, note = source_copy(copies, UNITS[p], any(accounts[sc.connector_account_id].state == "blocked" for sc in linked))
            sync = max((sc.last_successful_sync_at for sc in linked if sc.last_successful_sync_at), default=None)
            account = ", ".join(sc.name for sc in mine) or "Matched by approved client contacts"
            # History from = this client's earliest item the KB holds; with a partial copy, older items may still exist.
            reach = first.get(p) or min((at for k, at in copies if k == "window"), default=None)
            row = {"source": label, "account": account, "state": state, "items": counts.get(p, 0), "from": wia_date(reach) if reach else ""}
            if sync:
                local = sync.astimezone(IST)
                row["lastSync"] = f"{local:%b} {local.day}, " + local.strftime("%I:%M %p").lstrip("0")
            if note or not counts.get(p):
                row["note"] = note or empty_note or "No activity collected yet"
            return row

        sources = [scope_row("slack", "Slack"), scope_row("gmail", "Gmail"), scope_row("clickup", "ClickUp"),
                   scope_row("fathom", "Fathom"),
                   {"source": "Zoom history", "account": "Not ingested yet", "state": "Not linked"},
                   scope_row("drive", "Drive"),
                   scope_row("leadlock", "LeadLock", "Lead figures are on the Leads tab"),
                   scope_row("calendar", "Calendar")]
        drive_scope = next((sc for sc in b_scopes if accounts[sc.connector_account_id].provider == "drive"), None)
        list_names = {sc.id: sc.name for sc in b_scopes}
        programme = "" if space.isupper() else space.removesuffix(" Clients")  # "ONBOARDING CLIENTS" isn't a service
        has_leadlock = any(accounts[sc.connector_account_id].provider == "leadlock" for sc in b_scopes)
        engaged = (engagements(recs, provider, lambda sid: list_names.get(sid, ""), programme, has_leadlock)
                   or [{"type": service, "start": ""}])
        out["clients"][-1]["since"] = next((e["start"] for e in engaged if e["start"]), "")
        out["records"][cid] = {
            "owner": owner, **({"ownerSuggestion": owner_hint} if owner_hint["name"] and (not owner or owner_hint.get("changed")) else {}),
            "lifecycle": "Onboarding" if space.upper() == "ONBOARDING CLIENTS" else "Active",
            "aliases": [x for x in aliases[b.id] if x != b.name and (" " in x or not x.islower())],  # skip search-only spellings
            "engagements": engaged,
            "earliestEvidence": wia_date(dated[0]) if dated else "", "processedThrough": out["meta"]["windowEnd"],
            "lastContact": {"date": last_comm["date"], "channel": last_comm["channel"]} if last_comm else {"date": "", "channel": "Gmail"},
            "commsWindow": comms_window,  # the Now tab card: "since the <date> call", or the last 30 days
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
            "team": team_rows,
            "sources": sources,
            # unprocessed = linked accounts/lists whose whole history isn't copied yet
            "backfill": {"state": "Complete" if copied and all(copied) else "In progress",
                         "percent": round(100 * sum(copied) / len(copied)) if copied else 0, "unprocessed": copied.count(False)},
            "support": [], "supportCoverage": f"{NOT_EXTRACTED}: support issues are read from email and Slack by the KB.",
            "meetings": meetings, "changes": [], "cadence": rhythm, "sensitivities": [],
        }

    # Call preparation: upcoming client calls with live facts and the current brief (services/callprep).
    from backend.services.callprep import present as call_prep
    try:
        with transaction() as s:
            out.update(call_prep.calls(s, out, now))
    except Exception as exc:  # noqa: BLE001 — one odd event or skill must not freeze the whole portfolio
        log.error("call prep left out of the portfolio build", extra={"error_type": type(exc).__name__})

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


def refresh() -> dict | None:
    """Build outside any write transaction, then store it in a short one. One build at a time: when another
    worker is already building, queue one for the next bucket instead (the running one may predate the latest
    copy), so builds never pile up on both bulk workers and an older build never overwrites a newer one."""
    # Session-level lock on its own autocommit connection: held for the whole build, never an open transaction.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as lock:
        if not lock.scalar(select(func.pg_try_advisory_lock(BUILD_LOCK))):
            with transaction() as s:
                request_refresh(s)
            return None
        try:
            payload = build(logos="link")
            with transaction() as s:
                values = {"built_at": utcnow(), "payload": payload}
                s.execute(insert(ReadModelSnapshot).values(name=NAME, **values)
                          .on_conflict_do_update(index_elements=["name"], set_=values))
            return payload
        finally:
            lock.scalar(select(func.pg_advisory_unlock(BUILD_LOCK)))


def current(s) -> ReadModelSnapshot | None:
    return s.get(ReadModelSnapshot, NAME)


def run_job(work_id, lease_token, payload: dict) -> None:
    refresh()
    with transaction() as s:
        queue.complete(s, work_id, lease_token)
