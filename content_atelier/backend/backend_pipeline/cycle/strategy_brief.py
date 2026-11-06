"""The window's strategy brief, as beliefs to prove (E.B28, go-live subset; the v2 method's step 1).

A deterministic assembler: no model call. From the knowledge base it builds, for one cycle:

- **beliefs_to_prove**, four to six: chosen from the belief bank (`knowledge_base/beliefs-to-prove.json`), whose every
  belief rests on statements quoted word for word from documents 16 (belief statements) and 01 (Savannah's content
  strategy). A quote that no longer appears in its document leaves its belief out, with a warning. Each belief carries
  its offer (only an offer on sale in the window), its stage, and its do-not-repeat pieces: what WIA published in the last
  twelve months that already made the same point, the newest first (the published register). The mix follows the content
  plan's (document 14: mostly WARM, ATTRACT for reach, about one CONVERT). Within a stage a belief proved in the last 30
  days waits (D23: 30 days for a fresh angle on the same point); the season, Savannah's priority series (document 01) and
  the longest wait since a belief was last proved come first; ties rotate by the window, so a stable bank still varies.
- **live_offers**: the offer calendar (`knowledge_base/offer-calendar.json`) in force over the publishing window, each
  offer checked against the offer sheet (document 05), with its status and the points a card must not make while it runs
  (`do_not_undercut`).
- **recent_central_points** (the last 90 days of the register), **priority_series** with when each was last published,
  the **content_plan** lines and the **season**.

The brief and its hash are frozen with the cycle's run (`input_refs.strategy_brief`), shown at Gate 1 (the week review)
and passed to strategist profile v7, which pairs every card with one belief (`belief_ref`). `undercut_flags` is the
check behind the calendar: a card whose point, title, why-it-matters or takeaway makes a do-not-undercut point is held
until the offer's window ends, with the offer named (sql_pipeline, gates).
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from ..store import canonical_hash

VERSION = "strategy-brief.v1"
MADE_BY = "system: deterministic assembler from the knowledge base (no model call)"
BELIEFS_FILE = "beliefs-to-prove.json"
CALENDAR_FILE = "offer-calendar.json"
STAGES = ("ATTRACT", "WARM", "CONVERT")
# Section 4.2 and the content plan: mostly WARM, ATTRACT for reach, about one CONVERT. Four to six beliefs in all.
DEFAULT_MIX = {"ATTRACT": 1, "WARM": 3, "CONVERT": 1}
MIN_BELIEFS, MAX_BELIEFS = 4, 6
FRESH_ANGLE_DAYS = 30  # D23: a point published this recently waits, even for a fresh angle
REGISTER_DAYS = 365
RECENT_DAYS = 90
PUBLISHING_DAYS = 14
SELLABLE = ("open", "waitlist")
STATUSES = ("open", "waitlist", "delivering", "closed")
# A belief and a published point make the same point when their content words overlap this much (the same-point rule of
# cycle.verification, a little looser: a belief is broader than one piece).
REPEAT_MIN, REPEAT_SHARED = 0.5, 3
SERIES_SHARED = 2  # a series name is a few words
UNDERCUT_MIN, UNDERCUT_SHARED = 0.6, 3
UNDERCUT_FIELDS = ("title", "point", "core_perspective", "why_it_matters", "reader_takeaway")
PRIORITY_SERIES = re.compile(r"^###\s*Series\s*#\d+:\s*(.+?)\s*$", re.M)


# The season, from the window's first day (WIA's year: engagements peak from December to February).

def season(on: date) -> dict:
    m = on.month
    if m in (12, 1, 2):
        return {"name": "engagement", "label": "Engagement season: couples are getting engaged and starting to book; "
                "wedding pros feel the inquiry rush, or its absence"}
    if m in (10, 11):
        start = date(on.year, 12, 1)
        weeks = max(0, (start - on).days // 7)
        return {"name": "engagement_lead_up", "weeks_to_engagement_season": weeks,
                "label": f"Engagement season starts in about {weeks} weeks (December to February): wedding pros are "
                         "planning their ads and budgets for it now"}
    if m in (3, 4, 5):
        return {"name": "spring_booking", "label": "Spring: couples engaged over the winter are booking their vendors"}
    return {"name": "wedding_season", "label": "Wedding season: owners are busy delivering weddings and inquiries for "
            "next year are arriving"}


def _words(text: str) -> set[str]:
    from .verification import point_words
    return point_words(text)


def _overlap(a: str, b: str) -> tuple[float, set[str]]:
    from .verification import point_overlap
    return point_overlap(a, b)


def _normal(text: str) -> str:
    from .verification import normalise
    return normalise(text)


def _document_text(kb, key: str) -> str | None:
    document = kb.document(key) if kb is not None and hasattr(kb, "document") else None
    return document.text if document is not None else None


def load_json(root: Path, name: str) -> tuple[dict | None, str | None]:
    path = Path(root) / name
    if not path.is_file():
        return None, None
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), canonical_hash(raw.decode("utf-8").replace("\r\n", "\n"))


# The published register: the last twelve months of WIA's central points.

def register(conn, root: Path, on: date) -> list[dict]:
    """Published central points of the twelve months before `on`, newest first: the database's confirmed rows when it has
    any, else the committed file the database is seeded from (knowledge.published_points.FILE)."""
    from ..knowledge import held_out, published_points
    if conn is not None:
        rows = published_points.recent(conn, on, REGISTER_DAYS)
        if rows:
            return rows
    path = Path(root) / published_points.FILE.name
    if not path.is_file():
        return []
    entries = [e for e in published_points.load(path)
               if on - timedelta(days=REGISTER_DAYS) <= date.fromisoformat(e["published_on"]) <= on]
    kept = held_out.keep([{**e, "text": e["key_message"]} for e in entries])
    rows = [{"content_id": e["source_ref"], "published_on": e["published_on"], "channel": e["channel"], "title": e["title"],
             "key_message": e["key_message"]} for e in kept]
    return sorted(rows, key=lambda r: (r["published_on"], r["content_id"]), reverse=True)


def _same_point(texts: list[str], piece: dict, shared_min: int = REPEAT_SHARED) -> bool:
    for text in texts:
        for other in (piece["key_message"], piece.get("title") or ""):
            score, shared = _overlap(text, other)
            if len(shared) >= shared_min and score >= REPEAT_MIN:
                return True
    return False


# The offer calendar, with the changes made in the app (`offers.status`, Phase N10): an offer that opens, closes or moves to a
# waitlist is a settings line an approver writes, not a file a developer edits and deploys.

def status_changes(lines) -> tuple[dict[str, dict], list[str]]:
    """{offer (lower case): {status, ends}} from lines such as "ELEVATE: open" or "Google Search Accelerator: closed until
    2026-12-01"; a line that does not parse is a warning, never a stop."""
    found, warnings = {}, []
    for line in lines or ():
        m = re.fullmatch(r"\s*(.+?)\s*:\s*(open|waitlist|delivering|closed)(?:\s+until\s+(\d{4}-\d{2}-\d{2}))?\s*", line or "", re.I)
        if not m:
            warnings.append(f"An offer status line was not understood and was left out: {line!r}")
            continue
        found[m.group(1).lower()] = {"status": m.group(2).lower(), "ends": m.group(3)}
    return found, warnings


def with_changes(calendar: dict | None, lines) -> tuple[dict | None, list[str]]:
    """The calendar with the app's status changes applied; an offer the calendar does not name is added with its status."""
    changes, warnings = status_changes(lines)
    if not changes:
        return calendar, warnings
    entries = [dict(e) for e in (calendar or {}).get("entries", [])]
    named = {e["offer"].lower(): e for e in entries}
    for offer, change in changes.items():
        entry = named.get(offer)
        if entry is None:
            entry = {"offer": next(line.split(":", 1)[0].strip() for line in lines if line.split(":", 1)[0].strip().lower() == offer),
                     "do_not_undercut": [], "terms": []}
            entries.append(entry)
        entry.update(status=change["status"], ends=change["ends"] or entry.get("ends"), source="offers.status (set in the app)")
        if change["ends"] is None and change["status"] != "delivering":
            entry.pop("ends", None)
        if change["status"] == "closed":
            entry.update(do_not_undercut=[], terms=[])  # nothing on sale or being delivered: nothing a card could undercut
    return {**(calendar or {}), "entries": entries}, warnings


# The offer calendar.

def offer_calendar(calendar: dict | None, offer_sheet: str | None, window: tuple[date, date]) -> tuple[list[dict], list[str]]:
    """The calendar entries in force over the window, each checked against the offer sheet; and warnings."""
    warnings, offers = [], []
    if calendar is None:
        return [], [f"No offer calendar ({CALENDAR_FILE}): offers have no status and nothing is checked for undercutting"]
    start, end = window
    sheet = _normal(offer_sheet or "")
    for entry in calendar.get("entries", []):
        if entry.get("status") not in STATUSES:
            raise ValueError(f"{CALENDAR_FILE}: {entry.get('offer')} has an unknown status {entry.get('status')!r}")
        starts = date.fromisoformat(entry["starts"]) if entry.get("starts") else None
        ends = date.fromisoformat(entry["ends"]) if entry.get("ends") else None
        if (starts and starts > end) or (ends and ends < start):
            continue
        if offer_sheet is not None and _normal(entry["offer"]) not in sheet:
            warnings.append(f"The offer calendar names {entry['offer']}, which the offer sheet (document 05) does not")
        offers.append({"offer": entry["offer"], "status": entry["status"], "sellable": entry["status"] in SELLABLE,
                       "starts": entry.get("starts"), "ends": entry.get("ends"),
                       "do_not_undercut": list(entry.get("do_not_undercut") or []), "terms": list(entry.get("terms") or []),
                       **({"note": entry["note"]} if entry.get("note") else {}), "source": entry.get("source")})
    return offers, warnings


# The content plan's mix.

def plan_mix(plan_text: str | None) -> dict:
    """The stage mix the content plan asks for, read from its 'Mix:' line; the documented default otherwise."""
    line = next((ln for ln in (plan_text or "").splitlines() if re.search(r"\bmix\b", ln, re.I)), "")
    mix = dict(DEFAULT_MIX)
    if re.search(r"mostly\s+attract", line, re.I):
        mix.update(ATTRACT=3, WARM=1)
    if re.search(r"(?:about|one)\s+(?:one\s+)?convert", line, re.I) or re.search(r"\bconvert\b", line, re.I):
        mix["CONVERT"] = 1
    if re.search(r"\bno\s+convert\b", line, re.I):
        mix["CONVERT"] = 0
    return mix


def _rotation(on: date, belief_id: str) -> str:
    year, week, _ = on.isocalendar()
    return canonical_hash([year, week, belief_id])


def _verified_quotes(entry: dict, kb) -> tuple[list[dict], list[str]]:
    quotes, missing = [], []
    for quote in entry.get("quotes", []):
        text = _document_text(kb, quote["document"])
        if text is None:
            missing.append(f"{quote['document']} is not loaded")
        elif _normal(quote["text"]) not in _normal(text):
            missing.append(f"\"{quote['text'][:60]}\" is no longer in {quote['document']}")
        else:
            quotes.append({"document": quote["document"], "text": quote["text"]})
    return quotes, missing


def assemble(kb, *, root: Path, on: date, conn=None, publishing_days: int = PUBLISHING_DAYS) -> dict:
    """The strategy brief for a cycle assembled on `on`. `kb` is the strategist's knowledge base (assembly service)."""
    window = (on, on + timedelta(days=publishing_days - 1))
    bank, bank_hash = load_json(root, BELIEFS_FILE)
    calendar, calendar_hash = load_json(root, CALENDAR_FILE)
    warnings = []
    if conn is not None:
        from ..settings_store import value
        calendar, change_warnings = with_changes(calendar, value("offers.status", conn))
        warnings += change_warnings
    offers, offer_warnings = offer_calendar(calendar, _document_text(kb, "offer_sheet"), window)
    warnings += offer_warnings
    sellable = {o["offer"] for o in offers if o["sellable"]}
    published = register(conn, root, on)
    plan_text = _document_text(kb, "content_plan")
    mix = plan_mix(plan_text)
    now = season(on)
    strategy = _document_text(kb, "content_strategy") or ""
    series = PRIORITY_SERIES.findall(strategy.split("Highest Priority Series", 1)[-1]) if "Highest Priority Series" in strategy else []

    candidates = []
    if bank is None:
        warnings.append(f"No belief bank ({BELIEFS_FILE}): the brief lists no beliefs to prove")
    for entry in (bank or {}).get("entries", []):
        if entry.get("stage") not in STAGES:
            raise ValueError(f"{BELIEFS_FILE}: {entry.get('id')} has an unknown stage {entry.get('stage')!r}")
        quotes, missing = _verified_quotes(entry, kb)
        if missing or not quotes:
            warnings.append(f"Belief {entry['id']} left out: " + "; ".join(missing or ["no quote"]))
            continue
        # An offer counts only when the calendar has it on sale in the window; with no calendar, the bank's offer stands.
        live = [o for o in entry.get("offers", []) if o in sellable] if calendar is not None else list(entry.get("offers", []))
        if entry.get("offers") and not live:
            warnings.append(f"Belief {entry['id']} left out: none of its offers ({', '.join(entry['offers'])}) is on sale "
                            "in this window")
            continue
        repeats = [p for p in published if _same_point([entry["belief"], *(q["text"] for q in quotes)], p)]
        last = repeats[0]["published_on"] if repeats else None
        candidates.append({"entry": entry, "quotes": quotes, "offers": live, "repeats": repeats, "last_proved": last})

    def recent(c) -> bool:
        return bool(c["last_proved"]) and (on - date.fromisoformat(c["last_proved"])).days < FRESH_ANGLE_DAYS

    def order(c):
        e = c["entry"]
        waited = (on - date.fromisoformat(c["last_proved"])).days if c["last_proved"] else 10 ** 6
        return (recent(c), now["name"] not in (e.get("seasons") or []), not e.get("priority_series"), -waited,
                _rotation(on, e["id"]))

    chosen = []
    for stage in STAGES:
        pool = sorted((c for c in candidates if c["entry"]["stage"] == stage and not recent(c)), key=order)
        chosen += pool[:mix.get(stage, 0)]
    # Four to six: fill from WARM, then any stage, from the beliefs not yet chosen and not proved too recently.
    rest = sorted((c for c in candidates if c not in chosen and not recent(c)),
                  key=lambda c: (c["entry"]["stage"] != "WARM", *order(c)))
    while len(chosen) < MIN_BELIEFS and rest:
        chosen.append(rest.pop(0))
    chosen = chosen[:MAX_BELIEFS]
    if len(chosen) < MIN_BELIEFS:
        warnings.append(f"Only {len(chosen)} beliefs could be chosen (four to six expected); check the belief bank and the "
                        "offer calendar")

    beliefs = []
    for i, c in enumerate(chosen, 1):
        e = c["entry"]
        beliefs.append({"ref": f"B{i}", "id": e["id"], "belief": e["belief"], "stage": e["stage"], "offer": c["offers"][0] if c["offers"] else None,
                        "offers": c["offers"], "priority_series": e.get("priority_series"), "quotes": c["quotes"],
                        "last_proved": c["last_proved"],
                        "do_not_repeat": [{k: p[k] for k in ("published_on", "channel", "title", "key_message")}
                                          for p in c["repeats"][:5]]})
    series_rows = []
    for name in series:
        hits = [p for p in published if _same_point([name], p, SERIES_SHARED)]
        series_rows.append({"name": name, "last_published": hits[0]["published_on"] if hits else None})
    body = {
        "version": VERSION, "made_by": MADE_BY, "on": on.isoformat(),
        "publishing_window": {"from": window[0].isoformat(), "to": window[1].isoformat()},
        "season": now, "mix": mix, "beliefs_to_prove": beliefs, "live_offers": offers,
        "recent_central_points": [{k: p[k] for k in ("published_on", "channel", "title", "key_message")} for p in published
                                  if (on - date.fromisoformat(p["published_on"])).days <= RECENT_DAYS][:12],
        "priority_series": series_rows,
        "content_plan": [ln[2:].strip() for ln in (plan_text or "").splitlines() if ln.startswith("- ")],
        "warnings": warnings,
        "inputs": {"knowledge_base_version": getattr(kb, "version", None),
                   "documents": {key: d.sha256 for key in ("content_plan", "belief_statements", "content_strategy", "offer_sheet")
                                 if kb is not None and (d := kb.document(key)) is not None},
                   "belief_bank_sha256": bank_hash, "offer_calendar_sha256": calendar_hash,
                   "published_points": len(published)},
    }
    return {**body, "brief_hash": canonical_hash(body)}


def check_hash(brief: dict) -> bool:
    return brief.get("brief_hash") == canonical_hash({k: v for k, v in brief.items() if k != "brief_hash"})


# For the strategist (profile v7): the brief as a section of the user message.

def render(brief: dict) -> str:
    lines = [f"## This window's strategy brief ({brief['publishing_window']['from']} to {brief['publishing_window']['to']}; "
             "WIA's plan, not call evidence)", "", f"Season: {brief['season']['label']}.", "",
             "### Beliefs to prove (pair every public card with one; cite it in `belief_ref`)"]
    for b in brief["beliefs_to_prove"]:
        offer = f"; offer: {', '.join(b['offers'])}" if b["offers"] else "; no offer"
        series = f"; Savannah's priority series: {b['priority_series']}" if b.get("priority_series") else ""
        lines.append(f"- {b['ref']} ({b['stage']}{offer}{series}): {b['belief']}")
        lines += [f"  - In WIA's words: \"{q['text']}\"" for q in b["quotes"]]
        if b["do_not_repeat"]:
            lines.append("  - Already published (prove it with a new moment; never repeat these): "
                         + "; ".join(f"{p['published_on']} {p['channel']}: {p['key_message']}" for p in b["do_not_repeat"]))
    if not brief["beliefs_to_prove"]:
        lines.append("- None this window: use `belief_ref` \"none\" and say which WIA belief the card proves.")
    lines += ["", "### Offers in this window (a card never undercuts one)"]
    for o in brief["live_offers"]:
        window = f" from {o['starts']}" if o.get("starts") else ""
        window += f" to {o['ends']}" if o.get("ends") else ""
        note = f" {o['note']}" if o.get("note") else ""
        lines.append(f"- {o['offer']}: {o['status']}{window}.{note}")
        lines += [f"  - Do not make this point while it runs: {p}" for p in o["do_not_undercut"]]
    if brief["recent_central_points"]:
        lines += ["", "### Central points published in the last 90 days (do not repeat one)"]
        lines += [f"- {p['published_on']} {p['channel']}: {p['key_message']}" for p in brief["recent_central_points"]]
    return "\n".join(lines)


# The check behind the calendar.

def undercut_flags(card: dict, brief: dict | None) -> list[dict]:
    """A blocking flag for each do-not-undercut point of an offer in force that the card makes, naming the offer.

    A point counts when a listed term appears in the card's framing fields, or when a field and the point share enough
    content words (cycle.verification's same-point rule)."""
    from .verification import BLOCK, _flag
    from ..knowledge.items import contains_term
    flags = []
    for offer in (brief or {}).get("live_offers", []):
        until = offer.get("ends") or (brief.get("publishing_window") or {}).get("to")
        for field in UNDERCUT_FIELDS:
            text = card.get(field)
            if not isinstance(text, str) or not text.strip():
                continue
            hit = next((t for t in offer.get("terms", []) if contains_term(text, t)), None)
            point = None
            for statement in offer.get("do_not_undercut", []):
                score, shared = _overlap(text, statement)
                if len(shared) >= UNDERCUT_SHARED and score >= UNDERCUT_MIN:
                    point = statement
                    break
            if hit or point:
                said = f'"{hit}"' if hit else f'the point "{point}"'
                flag = _flag("offer_undercut", BLOCK, field, text,
                             f"Undercuts {offer['offer']} ({offer['status']}" + (f" until {offer['ends']}" if offer.get("ends") else "")
                             + f"): the card makes {said}. Held until {until}; reframe it, or develop it after that date")
                flags.append({**flag, "offer": offer["offer"], "hold_until": until})
                break
    return flags


def hold_for(flags: list[dict]) -> dict | None:
    """The Gate 1 hold an undercutting card gets: until the latest window end among the offers it undercuts."""
    undercut = [f for f in flags if f.get("kind") == "offer_undercut"]
    if not undercut:
        return None
    until = max(f["hold_until"] for f in undercut)
    offers = sorted({f["offer"] for f in undercut})
    return {"until": (date.fromisoformat(until) + timedelta(days=1)).isoformat(), "reason_code": "timing",
            "note": f"Held by the strategy brief: the card undercuts {', '.join(offers)} while it runs",
            "author": "system: strategy brief", "offers": offers}


def for_run(conn, run_id: str | None) -> dict | None:
    """The brief frozen with a cycle's run, or None for a run made before E.B28."""
    if not run_id:
        return None
    row = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (run_id,)).fetchone()
    return ((row or {}).get("input_refs") or {}).get("strategy_brief")


def assemble_for(models, connection, on: date, mode: str) -> dict:
    """The brief from the strategist's knowledge base (the assembly service), for submit and the preview route."""
    from ..knowledge.assembly import assemble as context
    kb = context("strategist", root=models.knowledge_base_root, connection=connection, on=on,
                 allow_placeholders=mode in ("synthetic", "fake"))
    if connection is None:
        return assemble(kb, root=models.knowledge_base_root, on=on)
    with connection() as conn:
        return assemble(kb, root=models.knowledge_base_root, on=on, conn=conn)
