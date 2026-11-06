"""The week's review document (plan 5.B14, Markdown): one export of a cycle's cards and briefs with all asset copy, in the
layout WIA reviews.

The layout is the 13 October review document's (its header: "Content Atelier Review", the angles, briefs and packs, "Wedding
Industry Ads") as the 20 October v2 packs refined it: for each developed card, a pack with the content angle in Whitney's own
fields, the content brief, then every asset's finished copy (the email with its send header, each Reel, the carousel slide by
slide, the caption) and what to settle before publishing; the week's other cards follow as the content bank. The headings
are the ones `research/v2-reassessment-2026-10-20/tools/packs2docx.py` reads ("# Pack N", "## Content angle", "## Content
brief", "## Email", "## Reel", "## Carousel", "# Content bank"); `review_docx.py` renders this Markdown as the .docx on the
template shipped in the image (`GET /weeks/{id}/review.docx`).

Everything is rendered from the stored structure (the card's fields, the brief document of contract v1 to v4), never by
parsing Markdown, and every field comes from a table below: contract v4's fields (E.B33) and strategist v7's card fields
(E.B30) are rows of those tables. Output is labelled by its maker (R58): the system, and the person who
edited a version at a gate. A card or brief built on material removed at a client's request says so first (6.B12).
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from . import turns
from .contracts_v4 import format_words

Getter = str | Callable[[dict], Any]


def get(data: dict | None, path: Getter):
    """A value by dotted path (`format_plan.email.preview`, `slides[0].text`) or by function; None when any step is missing."""
    if data is None:
        return None
    if callable(path):
        return path(data)
    value: Any = data
    for part in path.replace("]", "").replace("[", ".").split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return None
        if value is None:
            return None
    return value


def words(text: str | None) -> str:
    return (text or "").replace("_", " ")


def sentences(*parts) -> str | None:
    """Parts joined as sentences: a part without closing punctuation gets a full stop."""
    kept = [str(p).strip() for p in parts if present(p)]
    return " ".join(p if p[-1] in ".!?:" else p + "." for p in kept) or None


def present(value) -> bool:
    return value not in (None, "", [], {})


def timestamp(ms: int | None) -> str:
    if ms is None:
        return ""
    seconds = ms // 1000
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}" if seconds >= 3600 else f"{seconds // 60}:{seconds % 60:02d}"


# ---- the tables -------------------------------------------------------------------------------------------------------------

# Strategist v7's choices (E.B30), in the reviewer's words, as Gate 1 shows them (frontend cardFields.ts).
POINT_IS_ABOUT = {"wia_belief": "a WIA belief", "wia_standard": "a WIA standard", "client_experience": "a client's experience",
                  "platform_or_tactic": "a platform or tactic (not for public content)"}
BUYERS = {"elevate": "an ELEVATE buyer", "accelerators": "an Ads Accelerators buyer", "leadlock": "a LeadLock buyer",
          "established_owner": "an established owner who already runs ads"}
CTA_SLOTS = {"offer_cta": "the week's offer CTA", "soft_invitation": "a soft invitation", "none": "no CTA"}


def _point(c):
    """The card's point: strategist v7's `point`, with what it is about; v3 to v6's core perspective."""
    point = c.get("point") if "point" in c else c.get("core_perspective")
    about = POINT_IS_ABOUT.get(c.get("point_is_about"))
    return f"{point} ({about})" if point and about else point


def _surprise(c):
    s = c.get("surprise_for_experienced_advertiser")
    return sentences("Yes" if s["surprising"] else "No", s.get("reason")) if s else None


def _reader(c):
    fit = c.get("reader_fit")
    lines = [c.get("reader_takeaway") and f"Comes away thinking: {c['reader_takeaway']}"]
    if fit:
        lines += [sentences(f"Buyer: {BUYERS.get(fit.get('buyer'), words(fit.get('buyer')))}", fit.get("buyer_statement")), fit.get("why")]
    return [x for x in lines if x]


def _next_step(c):
    """Guardrail and next step: v7's guardrail and its offer and CTA, then what to verify before publishing (v3 to v6 too)."""
    offer = c.get("offer_fit") or {}
    step = sentences("Next step: " + (f"{offer['offer']}, " if offer.get("offer") else "") + CTA_SLOTS.get(offer.get("cta_slot"),
                     words(offer.get("cta_slot"))), offer.get("calendar_note")) if offer else None
    return [x for x in [c.get("guardrail"), step, *(c.get("verify_before_publishing") or [])] if x]


# Whitney's angle fields, in her angle card's order (section 4.2): pillar and type; audience; the point (with strategist v7's
# tests); why this matters; WIA's expertise or process; evidence; guardrail and next step. A field a card does not carry is
# left out, so v3 to v7 cards all render.
CARD_FIELDS: list[tuple[str, Getter]] = [
    ("Content pillar / type", lambda c: f"{c['pillar']} · {words(c.get('content_type'))}" if c.get("pillar") else None),
    ("Audience", "audience"),
    ("Central point", _point),
    ("Would it surprise an owner who already runs ads", _surprise),
    ("The reader", _reader),
    ("The belief it proves", "belief_ref"),
    ("Why this matters", "why_it_matters"),
    ("WIA's expertise or process", "wia_in_action"),
    ("Evidence in the referenced call", "evidence_points"),
    ("How often it came up", "recurrence"),
    ("Offer connection", "offer_connection"),
    ("Editorial guardrail / next step", _next_step),
    ("Series", "series"),
]


def _shift(b):
    shift = b.get("intended_shift") or {}
    return [f"{label}: {shift[key]}" for label, key in (("Understand", "understand"), ("Believe", "believe"), ("Do", "do"))
            if shift.get(key)]


def _example(b):
    example = b.get("supporting_example") or {}
    lines = [example.get("scene")]
    if example.get("wia_move"):
        lines.append("What we did: " + example["wia_move"])
    if example.get("client_contribution"):
        lines.append("What the client contributed: " + example["client_contribution"])
    # Contract v4 (E.B33): the moment's call times, its one or two details and who did what.
    lines += list(example.get("timestamps") or [])
    if example.get("details"):
        lines.append("Details the copy uses: " + "; ".join(example["details"]))
    if example.get("credits"):
        lines.append("Who did what: " + "; ".join(f"{c['actor']}: {c['did']}" for c in example["credits"]))
    return [x for x in lines if x]


def _evidence(b):
    return [f"{e.get('speaker') or 'Unknown speaker'}" + (f" at {timestamp(e['start_ms'])}" if e.get("start_ms") is not None else "")
            + f': "{turns.words(e["quote"], e.get("speaker"))}"' for e in b.get("evidence") or []]


def _outline(b):
    o = b.get("narrative_outline") or {}
    lines = [f"Hook ({words(h.get('style'))}): {h['text']}" for h in o.get("hooks") or []]
    if o.get("problems_desires_symptoms"):
        lines.append("Problems, desires and symptoms: " + "; ".join(o["problems_desires_symptoms"]))
    lines += [f"{label}: {o[key]}" for label, key in (("Main point", "main_point"), ("Transformation", "transformation"), ("CTA", "cta"))
              if o.get(key)]
    return lines


def _formats(b):
    plan = b.get("format_plan") or {}
    lines = []
    if plan.get("email"):
        lines.append("Email: " + (plan["email"].get("job") or "tells the whole story"))
    lines += [f"Reel {i}: {r['job']}" for i, r in enumerate(plan.get("reels") or [], 1)]
    if plan.get("carousel"):
        lines.append("Carousel: " + plan["carousel"]["job"])
    if plan.get("caption") and plan["caption"].get("job"):
        lines.append("Caption: " + plan["caption"]["job"])
    return lines


def _cta(b):
    cta = b.get("cta") or {}
    who = "confirmed by a person" if cta.get("chosen_by") == "person" else "proposed by the writer; confirm it at Gate 2"
    action = cta.get("action") or ("No explicit ask" if cta.get("choice") == "no_explicit_ask" else "To decide in development")
    return sentences(f"{action} ({who})", b.get("cta_why"))


# The brief's sections for contracts v2 and v3 (the 13 October structure, section 4.3).
BRIEF_SECTIONS: list[tuple[str, Getter]] = [
    ("Central point", lambda b: b.get("central_point") or get(b, "approved_angle.core_perspective")),
    ("Sharper point (proposed)", lambda b: (b.get("sharpened_point") or {}).get("text")),
    ("Strategic purpose", lambda b: f"{b['strategic_purpose']['pillar']} · {words(b['strategic_purpose']['content_type'])}. "
                                    f"{b['strategic_purpose']['why_now']}" if b.get("strategic_purpose") else None),
    ("Desired response", lambda b: [x for x in [get(b, "strategic_purpose.desired_response")] if x] + _shift(b)),
    ("Audience and reason to care", lambda b: sentences(get(b, "audience.who"), get(b, "audience.reason_to_care"))),
    ("WIA perspective", "wia_perspective"),
    ("Supporting example", _example),
    ("From the call", _evidence),
    ("Narrative outline", _outline),
    ("Format and creative approach", _formats),
    ("CTA and essential boundaries", _cta),
]

# Contract v1 has directions, not copy.
BRIEF_SECTIONS_V1: list[tuple[str, Getter]] = [
    ("Central point", "angle_statement"), ("Core insight", "core_insight"), ("Audience", "audience"),
    ("Audience pain", "audience_pain"), ("Why now", "why_now"), ("Message spine", "message_spine"), ("Narrative", "narrative"),
    ("Format and creative approach", lambda d: [f"Email: {d['email']['reader_job']} {d['email']['direction']}"]
     + [f"Reel {i}: {r['reader_job']} {r['direction']}" for i, r in enumerate(d.get("reels") or [], 1)]
     + [f"Carousel: {d['carousel_reader_job']}"] + [f"Slide {s['number']}: {s['direction']}" for s in d.get("carousel") or []]),
    ("CTA and essential boundaries", lambda d: [(d.get("cta") or {}).get("text") or "To decide in development"]
     + list(d.get("evidence_boundaries") or [])),
]

# The email's send header (contract v4 adds the date, send time and recipients; WIA confirms them, scheduling is downstream).
EMAIL_HEADER: list[tuple[str, Getter]] = [
    ("DATE", lambda e: get(e, "send_header.date") or e.get("send_date")),
    ("SEND TIME", lambda e: get(e, "send_header.send_time") or e.get("send_time")),
    ("RECIPIENTS", lambda e: get(e, "send_header.recipients") or e.get("recipients")),
    ("SUBJECT", lambda e: (e.get("subject_options") or [None])[0]),
    ("OTHER SUBJECT OPTIONS", lambda e: " | ".join(e["subject_options"][1:]) if len(e.get("subject_options") or []) > 1 else None),
    ("PREVIEW TEXT", "preview"),
]
# Contract v4's direction for the email (its job and register), after the header (E.B33).
EMAIL_FIELDS: list[tuple[str, Getter]] = [("Job", "job"), ("Register", "register")]
EMAIL_BODY: list[Getter] = ["opening", "body", "argument", "transformation", "ending",
                            lambda e: f"Offer descriptor: {e['offer_descriptor']}" if e.get("offer_descriptor") else None]
REEL_FIELDS: list[tuple[str, Getter]] = [
    ("Format", lambda r: r.get("format") or format_words(r) or ("existing clip" if r.get("source") == "existing_clip" else None)),
    # Writer v5.3 (Round 2): each Reel's own premise, its takeaway and why it differs from the other two.
    ("Premise", "premise"), ("Takeaway", "takeaway"), ("Why it differs", "distinct_because"),
    ("Job", "job"), ("Cover", "cover_text"), ("On-screen hook", "on_screen_hook"), ("Spoken opening", "spoken_opening"),
    ("Read time", lambda r: f"about {r['read_time_seconds']} seconds" if r.get("read_time_seconds") else None),
    ("Register", lambda r: words(r.get("register")) or None), ("Offer descriptor", "offer_descriptor"),
]
REEL_BLOCKS: list[tuple[str, Getter]] = [("On-screen text", "screens"), ("Script", "script"), ("Beats", lambda r: None if r.get("script") else r.get("beats")),
                                         ("Personal lines for Whitney to keep or cut", "personal_lines"), ("Caption", "caption")]

CAROUSEL_FIELDS: list[tuple[str, Getter]] = [("Title", "title"), ("Job", "job"), ("Register", "register"),
                                             ("Offer descriptor", "offer_descriptor")]
CAROUSEL_BLOCKS: list[tuple[str, Getter]] = [("Caption", "caption")]

CAPTION_BLOCKS: list[Getter] = ["hook", "body", "adds", "ending"]


# ---- writing --------------------------------------------------------------------------------------------------------------

class Writer:
    def __init__(self):
        self.lines: list[str] = []

    def add(self, *lines: str):
        self.lines.extend(lines)

    def gap(self):
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    def field(self, label: str, value, *, period: bool = False):
        """`**Label:** text`, or the label and a list. `period` writes the brief's `**Label.** text` form."""
        if not present(value):
            return
        mark = f"**{label}.**" if period else f"**{label}:**"
        if isinstance(value, list):
            self.add(mark)
            self.gap()
            self.add(*[f"- {flatten(v)}" for v in value if present(v)])
        else:
            self.add(f"{mark} {flatten(value)}")
        self.gap()

    def block(self, label: str, value):
        """A label on its own line, then the text as paragraphs (a script, a caption)."""
        if not present(value):
            return
        self.add(f"**{label}:**")
        self.gap()
        if isinstance(value, list):
            self.add(*[f"- {flatten(v)}" for v in value if present(v)])
        elif isinstance(value, dict):
            self.add(*[flatten(v) for v in value.values() if present(v)])
        else:
            self.add(str(value).strip())
        self.gap()

    def text(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"


def flatten(value) -> str:
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values() if present(v))
    if isinstance(value, list):
        return "; ".join(flatten(v) for v in value if present(v))
    return " ".join(str(value).split()) if "\n" not in str(value) else str(value).strip()


def public_stance(card: dict, angle: dict) -> str | None:
    """A v7 card's public stance (D31): confirmed by whom and when, or waiting for an approver's confirmation."""
    stance = card.get("public_stance") or {}
    if not stance.get("takes_stance"):
        return None
    confirmed = (angle.get("content_body") or {}).get("stance_confirmation")
    said = stance.get("stance") or _point(card)
    if confirmed:
        return f"{said} (confirmed by {confirmed['by']} on {str(confirmed['at'])[:10]})"
    return f"{said} (not confirmed yet: an approver confirms it before the card is developed)"


REMOVED = "Built on removed material"


def card_section(w: Writer, card: dict, angle: dict):
    # 6.B12: a card built on material removed at a client's request says so first; it is never developed.
    w.field(REMOVED, (angle.get("removed_material") or {}).get("note"))
    for label, path in CARD_FIELDS:
        w.field(label, get(card, path))
    w.field("Public stance", public_stance(card, angle))
    status = angle.get("approval_status")
    if status == "approved":
        w.field("Gate 1", f"developed by {angle.get('approved_by') or 'a reviewer'}")
    elif status:
        w.field("Gate 1", words(status))


def brief_section(w: Writer, body: dict, sections):
    for label, path in sections:
        w.field(label, get(body, path), period=True)


def assets(w: Writer, body: dict):
    plan = body.get("format_plan") or {}
    email = plan.get("email")
    if email:
        w.add("## Email")
        w.gap()
        w.add(*[f"**{label}:** {flatten(v)}" for label, path in EMAIL_HEADER if present(v := get(email, path))])
        w.gap()
        for label, path in EMAIL_FIELDS:
            w.field(label, get(email, path))
        for path in EMAIL_BODY:
            if present(v := get(email, path)):
                w.add(str(v).strip())
                w.gap()
    for i, reel in enumerate(plan.get("reels") or [], 1):
        w.add(f"## Reel {i}: {reel.get('cover_text') or reel.get('job')}")
        w.gap()
        for label, path in REEL_FIELDS:
            w.field(label, get(reel, path))
        for label, path in REEL_BLOCKS:
            w.block(label, get(reel, path))
    carousel = plan.get("carousel")
    if carousel:
        w.add(f"## Carousel: {carousel.get('title') or carousel.get('job')}")
        w.gap()
        for label, path in CAROUSEL_FIELDS:
            w.field(label, get(carousel, path))
        for slide in carousel.get("slides") or []:
            w.add(f"**Slide {slide['number']}**")
            w.add(*[line for line in str(slide.get("text") or slide.get("direction") or "").strip().splitlines()])
            # A v3 or v4 slide's job is direction for the designer, under its copy.
            if slide.get("text") and slide.get("job"):
                w.add(f"*Job: {slide['job']}*")
            w.gap()
        for label, path in CAROUSEL_BLOCKS:
            w.block(label, get(carousel, path))
    caption = plan.get("caption")
    if caption:
        w.add("## Caption")
        w.gap()
        for path in CAPTION_BLOCKS:
            if present(v := get(caption, path)):
                w.add(str(v).strip())
                w.gap()
    if plan.get("stories"):
        w.add("## Stories")
        w.gap()
        w.add(*[f"- {frame}" for frame in plan["stories"]["frames"]])
        w.gap()


def before_publishing(w: Writer, body: dict, number: int):
    items = body.get("before_publishing") or body.get("open_questions") or []
    if not items:
        return
    w.add(f"## Before you publish Pack {number}")
    w.gap()
    for item in items:
        answer = item.get("answer")
        w.add(f"- {item['text']}" + (" (required)" if item.get("required") else "") + (f" Answer: {answer}" if answer else " Unanswered."))
    w.gap()


# ---- the week ----------------------------------------------------------------------------------------------------------------

def week_material(conn, week_id: str) -> dict:
    """The week, its current cards in rank order with their current brief, and who made what."""
    week = conn.execute("SELECT * FROM weeks WHERE week_id=%s", (week_id,)).fetchone()
    if not week:
        raise LookupError("Week not found")
    angles = conn.execute("""SELECT a.* FROM content_angles a WHERE a.week_id=%s AND NOT EXISTS
        (SELECT 1 FROM content_angles n WHERE n.supersedes_id=a.angle_id) ORDER BY a.created_at,a.angle_id""", (week_id,)).fetchall()
    cards = [a for a in angles if (a["content_body"] or {}).get("card")]
    cards.sort(key=lambda a: (a["content_body"]["card"].get("rank") or 10**6, a["angle_id"]))
    briefs = {}
    for a in cards:
        row = conn.execute("""SELECT b.* FROM content_briefs b WHERE b.angle_id=%s AND NOT EXISTS
            (SELECT 1 FROM content_briefs n WHERE n.supersedes_id=b.brief_id) ORDER BY b.created_at DESC,b.brief_id LIMIT 1""",
                           (a["angle_id"],)).fetchone()
        if row:
            depth = conn.execute("""WITH RECURSIVE chain AS (SELECT brief_id,supersedes_id FROM content_briefs WHERE brief_id=%s
                UNION ALL SELECT b.brief_id,b.supersedes_id FROM content_briefs b JOIN chain c ON b.brief_id=c.supersedes_id)
                SELECT count(*) AS n FROM chain""", (row["brief_id"],)).fetchone()["n"]
            row["version_number"] = depth
            briefs[a["angle_id"]] = row
    # Built on material removed at a client's request (6.B12): named on the card and the brief.
    from ..removal import marks
    removed = marks(conn, "angle", [a["angle_id"] for a in cards])
    for a in cards:
        a["removed_material"] = removed.get(a["angle_id"])
    removed = marks(conn, "brief", [b["brief_id"] for b in briefs.values()])
    for b in briefs.values():
        b["removed_material"] = removed.get(b["brief_id"])
    run = conn.execute("""SELECT run_id,input_refs FROM pipeline_runs WHERE week_id=%s AND run_scope='weekly_angles'
        AND status NOT IN ('failed','cancelled') ORDER BY created_at DESC LIMIT 1""", (week_id,)).fetchone()
    return {"week": week, "cards": cards, "briefs": briefs, "run_refs": (run or {}).get("input_refs") or {},
            "founder_notes": founder_notes(conn, (run or {}).get("run_id"), cards)}


def founder_notes(conn, run_id: str | None, cards: list[dict]) -> list[dict]:
    """Whitney's "what stood out" notes the week's cycle read (L.B13, D29), each with what the strategist paired it with and
    the cards that used those scenes; a note paired with no scene is unanswered."""
    if not run_id:
        return []
    job = conn.execute("""SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation' AND status='completed'
        ORDER BY finished_at DESC NULLS LAST LIMIT 1""", (run_id,)).fetchone()
    pairings = [p for p in ((job or {}).get("result_refs") or {}).get("seed_pairings") or [] if p.get("seed_kind") == "founder_note"]
    by_card = {}
    for r in conn.execute("SELECT angle_id,moment_id FROM angle_moments WHERE angle_id=ANY(%s)", ([c["angle_id"] for c in cards],)):
        by_card.setdefault(r["angle_id"], set()).add(r["moment_id"])

    def cited(card):
        return by_card.get(card["angle_id"], set())
    notes = []
    for p in pairings:
        used = [c for c in cards if set(p.get("moment_ids") or []) & cited(c)]
        notes.append({"text": p.get("seed_text"), "author": p.get("seed_author"), "call": p.get("call"),
                      "paired": bool(p.get("moment_ids")), "unanswered": not p.get("moment_ids"),
                      "cards": [c["content_body"]["card"]["title"] for c in used], "note": p.get("note")})
    return notes


def brief_maker(brief: dict) -> str:
    """Who made this version (R58): the system's writer, and a person when a version was edited or revised at Gate 2."""
    document = (brief["content_body"] or {}).get("document") or {}
    version = get(document, "header.schema_version") or "brief_document_v1"
    made = f"Written by the Content Atelier system (brief contract {version.rsplit('_', 1)[-1]})"
    if brief.get("version_number", 1) > 1:
        made += f"; version {brief['version_number']}, last changed at Gate 2 by {brief.get('updated_by') or 'a reviewer'}"
    status = brief.get("approval_status")
    return made + (f". Gate 2: {words(status)}" + (f" by {brief['approved_by']}" if brief.get("approved_by") else "") if status else "")


# The 13 October review document's header: the Markdown's first lines, and the title block of the .docx template
# (`templates/review-template.docx`, review_docx.py), which carries it instead.
HEADER = ("Content Atelier Review", "Content Angles, Briefs and Packs", "Wedding Industry Ads")


def header_lines() -> list[str]:
    return [f"# {HEADER[0]}", "", HEADER[1], "", HEADER[2], ""]


def render(material: dict, *, exported: datetime | None = None) -> str:
    week, cards, briefs, refs = material["week"], material["cards"], material["briefs"], material["run_refs"]
    exported = exported or datetime.now(UTC)
    developed = [a for a in cards if a["angle_id"] in briefs]
    bank = [a for a in cards if a["angle_id"] not in briefs]
    w = Writer()
    w.add(*header_lines())
    w.add(f"**Week:** {week['week_start']:%d %B %Y} to {week['week_end']:%d %B %Y}")
    window = refs.get("window")
    if window:
        w.add(f"**Calls from:** {window['start'][:10]} to {window['end'][:10]} ({len(refs.get('transcripts') or [])} calls)")
    profile = refs.get("angle_prompt_profile")
    w.add("**Made by:** the Content Atelier system" + (f" (cards: strategist profile {profile})" if profile else "")
          + ". Edits a person made at a gate are named on each brief.")
    w.add(f"**Exported:** {exported:%d %B %Y, %H:%M} UTC")
    w.add(f"**In this document:** {len(developed)} developed {'idea' if len(developed) == 1 else 'ideas'} with "
          f"{'its brief' if len(developed) == 1 else 'their briefs'} and finished copy; {len(bank)} more in the content bank")
    w.gap()
    if material.get("founder_notes"):
        # L.B13 (D29): the founder's one line per notable call, paired with the scenes behind it or shown as unanswered.
        w.add("## What stood out (founder notes)")
        w.gap()
        for note in material["founder_notes"]:
            where = (f"in {', '.join(repr(t) for t in note['cards'])}" if note["cards"] else
                     "paired with that call's scenes; no card this week was built on them") if note["paired"] else                 "unanswered: no scene from that call carries it"
            w.add(f"- “{note['text']}” ({note['author'] or 'the team'}, about {note['call'] or 'a call'}): {where}.")
        w.gap()
    for number, angle in enumerate(developed, 1):
        card, brief = angle["content_body"]["card"], briefs[angle["angle_id"]]
        document = (brief["content_body"] or {}).get("document") or {}
        version = get(document, "header.schema_version") or "brief_document_v1"
        w.add("---", "", f"# Pack {number} · {card.get('pillar') or 'IDEA'}", "", "## Content angle", "", f"### {card['title']}", "")
        card_section(w, card, angle)
        w.add("## Content brief")
        w.gap()
        w.add(f"*{brief_maker(brief)}.*")
        w.gap()
        w.field(REMOVED, (brief.get("removed_material") or {}).get("note"))
        if version == "brief_document_v1":
            brief_section(w, document, BRIEF_SECTIONS_V1)
            before_publishing(w, document, number)
        else:
            body = document.get("body") or {}
            brief_section(w, body, BRIEF_SECTIONS)
            assets(w, body)
            before_publishing(w, body, number)
    w.add("---", "", "# Content bank", "")
    if not cards:
        w.add("No ideas for this week yet: no cycle has made cards for it.")
    elif not bank:
        w.add("Every idea this week was developed.")
        w.gap()
    for angle in bank:
        card = angle["content_body"]["card"]
        w.add(f"## {card['title']}")
        w.gap()
        if card.get("rank"):
            w.field("Rank", card["rank"])
        card_section(w, card, angle)
    return w.text()


def render_week(repo, week_id: str, *, exported: datetime | None = None) -> str:
    with repo.connection() as conn:
        return render(week_material(conn, week_id), exported=exported)
