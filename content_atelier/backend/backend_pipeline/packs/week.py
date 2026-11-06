"""The week's pack plan (NP.B11; the content-packs plan, section 4.4; KB 14, rulings R-10 and R-11; the offer calendar).

WIA's week is one Tuesday list email and three Instagram pieces, two without an offer ask and one with, the formats
alternating. Three packs make three emails and fifteen Instagram pieces, so most pieces wait in the bank. When read, the plan
proposes for the publishing week after the packs' approval week:

| Slot | Rule |
| --- | --- |
| Tuesday email | the highest-ranked pack's email (the card's rank); the other emails wait for the following Tuesdays |
| Instagram 1 (Monday) | the story Reel of a WARM or ATTRACT pack, ending without the offer ask (its no-offer ending) |
| Instagram 2 (Wednesday) | the carousel of a different pack, with no offer ask |
| Instagram 3 (Friday) | the week's one offer post: a piece of the CONVERT pack if there is one (else of the strongest pack), with the brief's CTA, when the offer calendar allows an ask that week |
| The bank | every other unpublished piece, with a suggested later week |

A piece marked published leaves the plan. The dates are suggestions, computed on read and never stored on a pack's copy; the
system neither schedules into any tool nor publishes (D43e). The week's findings are the pack checks' week checks
(packs/checks.py, `week_findings`), and the plan's own (an offer ask the calendar holds this week).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from ..production_common import ProductionError
from . import checks, model, views
from . import contracts_v2 as c2

SLOTS = (("tuesday_email", "Tuesday email", 1), ("instagram_1", "Instagram 1", 0), ("instagram_2", "Instagram 2", 2),
         ("instagram_3", "Instagram 3", 4))
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
# The offer post prefers a Reel, so the week alternates Reel, carousel, Reel (section 4.4: formats alternate).
OFFER_ORDER = ("reel_2", "reel_3", "reel_1", "carousel")
INSTAGRAM = ("reel_1", "reel_2", "reel_3", "carousel")
NO_RANK = 10 ** 6


def _day(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None


def publishing_week(week: dict, approvals: list) -> tuple[date, date]:
    """Monday to Sunday of the week after the packs' approval week (the latest approval), else after the cycle's week."""
    days = [d for d in (_day(a) for a in approvals) if d]
    base = max(days) if days else _day(week["week_end"]) or _day(week["week_start"])
    start = base + timedelta(days=7 - base.weekday())
    return start, start + timedelta(days=6)


def calendar_holds(text: str, window: tuple[date, date]) -> tuple[bool, str | None]:
    """Whether the offer calendar allows an offer ask in this window for this copy: (allowed, why not in words)."""
    from ..briefs.first_touch import load_data
    from ..cycle.strategy_brief import CALENDAR_FILE, offer_calendar
    from ..cycle.verification import knowledge_root
    offers, _ = offer_calendar(load_data(CALENDAR_FILE, knowledge_root()) or None, None, window)
    if not offers:
        return True, None
    low = (text or "").lower()
    for offer in offers:
        if not offer["sellable"] and any(t.lower() in low for t in offer["terms"]):
            return False, f"the offer calendar has {offer['offer']} {offer['status']} that week ({offer.get('note') or 'no ask for it'})"
    if not any(o["sellable"] for o in offers):
        return False, "the offer calendar has no offer on sale that week"
    return True, None


def _entries(conn, week_id: str) -> list[dict]:
    rows = conn.execute("""SELECT * FROM content_packs p WHERE p.week_id=%s AND p.contract_version=%s
        AND NOT EXISTS (SELECT 1 FROM content_packs n WHERE n.supersedes_id=p.pack_id) ORDER BY p.created_at,p.pack_id""",
                        (week_id, c2.VERSION)).fetchall()
    out = []
    for pack in rows:
        state, _ = model.state_of(conn, pack)
        body = pack.get("content_body") or {}
        brief = conn.execute("SELECT approved_at FROM content_briefs WHERE brief_id=%s", (pack["source_brief_id"],)).fetchone()
        published = set(views.published_marks(conn, pack["source_brief_id"]))
        bodies = checks.bodies_of(model.pieces(conn, pack["pack_id"])) if body else {}
        out.append({"pack": pack, "state": state, "body": body, "bodies": bodies, "published": published,
                    "approved_at": (brief or {}).get("approved_at"), "rank": body.get("rank") if isinstance(body.get("rank"), int) else NO_RANK,
                    "pillar": body.get("pillar")})
    out.sort(key=lambda e: (e["rank"], e["pack"]["created_at"], e["pack"]["pack_id"]))
    return out


def _usable(entry: dict, key: str, used: set) -> bool:
    piece = entry["bodies"].get(key) or {}
    return bool(piece.get("content")) and key not in entry["published"] and (entry["pack"]["pack_id"], key) not in used


def _slot(slot: str, label: str, day: date, entry: dict | None = None, key: str | None = None, cta=None, note=None) -> dict:
    out = {"slot": slot, "label": label, "date": day.isoformat(), "weekday": WEEKDAYS[day.weekday()], "pack_id": None, "piece": None,
           "piece_label": None, "title": None, "cta": cta, "note": note}
    if entry:
        notes = [note] if note else []
        out.update(pack_id=entry["pack"]["pack_id"], piece=key, piece_label=c2.LABELS[key], title=entry["pack"]["title"],
                   note=". ".join(notes) or None)
    return out


def _no_offer(entry: dict, key: str) -> str:
    ending = ((entry["bodies"].get(key) or {}).get("content") or {}).get("no_offer_ending")
    return f"Ends without the offer ask: {ending}" if ending else "Ends on its caption's last line, with no offer ask"


def plan(repo, week_id: str, actor=None) -> dict:
    """GET /weeks/{id}/pack-plan -> WeekPackPlanV2, computed on read."""
    with repo.connection() as conn:
        week = conn.execute("SELECT * FROM weeks WHERE week_id=%s", (week_id,)).fetchone()
        if not week:
            raise ProductionError("Week not found", "not_found", 404)
        entries = _entries(conn, week_id)
        ready = [e for e in entries if e["body"]]
        start, end = publishing_week(week, [e["approved_at"] for e in ready])
        day = {name: start + timedelta(days=offset) for name, _, offset in SLOTS}
        used: set = set()
        slots, findings = [], []

        def take(entry, key):
            used.add((entry["pack"]["pack_id"], key))

        email = next((e for e in ready if _usable(e, "email", used)), None)
        if email:
            take(email, "email")
            slots.append(_slot("tuesday_email", "Tuesday email", day["tuesday_email"], email, "email",
                               cta=(email["bodies"]["email"]["content"] or {}).get("cta") or "none"))
        else:
            slots.append(_slot("tuesday_email", "Tuesday email", day["tuesday_email"], note="No pack has an email waiting this week"))

        story = next((e for e in ready if e["pillar"] in ("WARM", "ATTRACT") and _usable(e, "reel_1", used)), None)
        fallback = None if story else next((e for e in ready if _usable(e, "reel_1", used)), None)
        first = story or fallback
        if first:
            take(first, "reel_1")
            note = _no_offer(first, "reel_1") + ("" if story else "; no WARM or ATTRACT pack has a story Reel waiting, so the "
                                                                   "strongest pack's goes first")
            slots.append(_slot("instagram_1", "Instagram 1", day["instagram_1"], first, "reel_1", cta="no_offer", note=note))
        else:
            slots.append(_slot("instagram_1", "Instagram 1", day["instagram_1"], note="No story Reel is waiting this week"))

        others = [e for e in ready if not first or e["pack"]["pack_id"] != first["pack"]["pack_id"]]
        carousel = next((e for e in others if _usable(e, "carousel", used)), None)
        same = None if carousel else next((e for e in ready if _usable(e, "carousel", used)), None)
        second = carousel or same
        if second:
            take(second, "carousel")
            note = _no_offer(second, "carousel") + ("" if carousel else "; only one pack has a carousel waiting this week")
            slots.append(_slot("instagram_2", "Instagram 2", day["instagram_2"], second, "carousel", cta="no_offer", note=note))
        else:
            slots.append(_slot("instagram_2", "Instagram 2", day["instagram_2"], note="No carousel is waiting this week"))

        convert = [e for e in ready if e["pillar"] == "CONVERT"]
        offer = None
        for group in (convert, ready[:1], ready):
            for e in group:
                keys = [k for k in OFFER_ORDER if _usable(e, k, used)]
                asks = [k for k in keys if ((e["bodies"][k].get("content") or {}).get("cta") == "offer")]
                if keys:
                    offer = (e, (asks or keys)[0])
                    break
            if offer:
                break
        if offer:
            entry, key = offer
            take(entry, key)
            allowed, why = calendar_holds(checks.piece_text(key, entry["bodies"][key]["content"]), (start, end))
            if allowed:
                note = None if entry["pillar"] == "CONVERT" else "No CONVERT pack this week: the strongest pack carries the offer post"
                slots.append(_slot("instagram_3", "Instagram 3", day["instagram_3"], entry, key, cta="offer", note=note))
            else:
                slots.append(_slot("instagram_3", "Instagram 3", day["instagram_3"], entry, key, cta="no_offer",
                                   note=f"No offer ask this week: {why}; it goes out with its no-offer ending"))
                findings.append({"severity": "warning", "message": f"The week has no offer post: {why}",
                                 "pieces": [f"{c2.LABELS[key]} of {entry['pack']['title']}"]})
        else:
            slots.append(_slot("instagram_3", "Instagram 3", day["instagram_3"], note="No piece is waiting for the offer post"))

        bank = []
        emails, instagram = 0, 0
        for e in ready:
            for key in c2.EXPORT_ORDER:
                if not _usable(e, key, used):
                    continue
                if key == "email":
                    emails += 1
                    week_n, reason = emails, "Waits for a later Tuesday: one list email a week"
                else:
                    instagram += 1
                    week_n, reason = 1 + (instagram - 1) // 3, "Waits for a later week: three Instagram pieces a week"
                bank.append({"pack_id": e["pack"]["pack_id"], "piece": key, "piece_label": c2.LABELS[key], "title": e["pack"]["title"],
                             "suggested_week": week_n, "reason": reason})

        seen = {}
        for e in ready:
            siblings = [{"pack_id": o["pack"]["pack_id"], "title": o["pack"]["title"], "brief_id": o["pack"]["source_brief_id"],
                         "body": o["body"], "pieces": o["bodies"], "created_at": o["pack"]["created_at"]}
                        for o in ready if o is not e]
            for f in checks.week_findings(conn, e["pack"], e["bodies"], siblings):
                where = f"{c2.LABELS[f['piece']]} of {e['pack']['title']}" if f.get("piece") else e["pack"]["title"]
                item = seen.setdefault(f["message"], {"severity": f["severity"], "message": f["message"], "pieces": []})
                if where not in item["pieces"]:
                    item["pieces"].append(where)
        findings += list(seen.values())
    slots.sort(key=lambda s: s["date"])  # in the week's order: Monday, Tuesday, Wednesday, Friday
    return {"week_id": week_id, "publishing_week_start": start.isoformat(), "publishing_week_end": end.isoformat(), "slots": slots,
            "bank": bank, "findings": findings,
            "packs": [{"pack_id": e["pack"]["pack_id"], "title": e["pack"]["title"], "state": e["state"], "pillar": e["pillar"],
                       "rank": None if e["rank"] == NO_RANK else e["rank"]} for e in entries]}
