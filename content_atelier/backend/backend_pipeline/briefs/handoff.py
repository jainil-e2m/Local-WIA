"""The production hand-off of a brief (E.B23; plan section 1.9.7, finding A1; architecture sections 4.6 and 4.7).

One view of a brief that does not depend on its contract version (v1, v2 or v3), so the production stage reads this and
never the contract-specific document. When packs come into scope they read `GET /storage/briefs/{id}/handoff` and act only
when its `can_consume` is true; until then `packs/workflow.py` still accepts v1 briefs only.

- **Pieces and their keys.** Every format-plan piece has a key derived from the plan alone: `reel_1`, `reel_2`, ... in
  the plan's order, then `carousel`, `email`, `caption`, `stories`. The key depends only on the piece's kind and position,
  so the same plan gives the same keys on every read. The names are the pack slots' (`packs/contracts.py` SLOTS), so one
  vocabulary of format keys serves both (R53 will make the formats data).
- **The anchor.** Exactly one piece, when the plan has any, is the one production writes first. The rule: the first Reel;
  else the carousel; else the email; else the caption; else the stories. A person chooses another piece at Gate 2 through
  the brief's edit route (`PATCH /briefs/{id}` with `changes: {"anchor": "<key>"}`, or `null` to return to the rule). The
  choice is kept in `review.anchor`, outside the reviewed document, so it needs no new check of the claims; a choice whose
  piece has left the plan is ignored, the rule applies and the view says so.
- **The message spine.** The one central message every sibling piece keeps: for v2 and v3, the brief's sharpened point
  when the writer proposed one (it was approved with the brief, and a person may edit or clear it at Gate 2), else the
  approved card's core perspective; the WIA perspective and the narrative's main point are its supporting lines. For v1,
  the core insight, with the v1 spine's lines.
- **Consent per evidence item.** From `key_moments.consent_status` and the client's level (`clients.consent`) where the
  evidence links to moments, the most restrictive when it links to several; the client's level from the call's client
  when no moment names one; "unknown" where neither is known, "not_applicable" for external framing.

Everything here is derived when it is read, with no model call: the writer's request is unchanged, and nothing here is
stored except a person's anchor choice.
"""
from __future__ import annotations

from datetime import UTC, datetime

from .contracts_v2 import SCHEMA_V2
from .contracts_v3 import SCHEMA_V3
from .contracts_v4 import SCHEMA_V4

LEDGER = (SCHEMA_V2, SCHEMA_V3, SCHEMA_V4)

HANDOFF_VERSION = "brief_handoff_v1"
ANCHOR_RULE = "The first Reel; else the carousel; else the email; else the caption; else the stories"
ANCHOR_ORDER = ("reel", "carousel", "email", "caption", "stories")
# Where each channel is published. The calendar publishes to Instagram (R-10, R-11); the email is WIA's newsletter.
PLATFORMS = {"reel": "instagram", "carousel": "instagram", "caption": "instagram", "stories": "instagram", "email": "email",
             "threads": "threads"}
LABELS = {"carousel": "Carousel", "email": "Email", "caption": "Caption", "stories": "Stories"}
# Most restrictive first.
CONSENT_ORDER = ("do_not_use", "internal_only", "anonymise", "cleared")
CLIENT_ORDER = ("no_use", "anonymise_only", "may_name")
KEEP = object()


def version_of(row: dict) -> str:
    return (row.get("content_body") or {}).get("schema_version") or "brief_document_v1"


def _pick(value: dict, names) -> dict:
    return {n: value[n] for n in names if n in value}


def _slides(slides, field):
    return [{"number": s["number"], field: s[field]} for s in slides]


def _ids(*groups) -> list[str]:
    return list(dict.fromkeys(i for group in groups for i in group or []))


# Which fields of each piece are copy (finished words the audience reads or hears) and which are direction (a note to the
# person who makes the asset). Version 3 marks them in its field descriptions (contracts_v3 COPY and DIRECTION, checked by
# a test); a field with no mark (a read time, a source, the stories' frames) is direction.
# Version 4 (E.B33): each Reel and the carousel carry their own caption, b-roll its screens, the email its send header.
REEL = {SCHEMA_V4: (("cover_text", "on_screen_hook", "spoken_opening", "script", "screens", "caption"),
                    ("kind", "job", "register", "beats", "personal_lines", "read_time_seconds", "source", "offer_descriptor",
                     # Writer v5.3 (Round 2): how the Reel is made, its own premise, takeaway, why it differs, its times.
                     "production", "premise", "takeaway", "distinct_because", "timestamps")),
        SCHEMA_V3: (("cover_text", "spoken_opening", "script"), ("job", "beats", "read_time_seconds", "source")),
        SCHEMA_V2: (("cover_text", "spoken_opening"), ("job", "beats", "read_time_seconds", "source"))}
EMAIL = {SCHEMA_V4: (("subject_options", "preview", "opening", "body", "ending"), ("job", "register", "send_header", "offer_descriptor")),
         SCHEMA_V3: (("subject_options", "preview", "opening", "body", "ending"), ()),
         SCHEMA_V2: (("subject_options", "preview", "opening", "ending"), ("argument", "transformation"))}
CAPTION = {SCHEMA_V3: (("hook", "body", "ending"), ()), SCHEMA_V2: (("hook", "ending"), ("adds",))}


def _piece(key, channel, label, copy, direction, evidence_ids):
    return {"key": key, "channel": channel, "platform": PLATFORMS[channel], "label": label, "copy": copy,
            "direction": direction, "evidence_ids": evidence_ids}


def pieces(row: dict) -> list[dict]:
    """The brief's pieces in plan order, each with its key, channel, platform, copy and direction (no anchor flag)."""
    version = version_of(row)
    document = row["content_body"]["document"]
    result = []
    if version in LEDGER:
        plan = document["body"]["format_plan"]
        copy_of, direction_of = REEL[version]
        for n, reel in enumerate(plan.get("reels") or [], 1):
            result.append(_piece(f"reel_{n}", "reel", f"Reel {n}", _pick(reel, copy_of), _pick(reel, direction_of),
                                 reel.get("evidence_ids") or []))
        if carousel := plan.get("carousel"):
            slides = carousel["slides"]
            copy, direction = {"slides": _slides(slides, "text")}, {"job": carousel["job"], "slides": _slides(slides, "job")}
            if version == SCHEMA_V4:
                copy = {"title": carousel["title"], **copy, "caption": carousel.get("caption")}
                direction = {**direction, "register": carousel["register"], "offer_descriptor": carousel.get("offer_descriptor")}
            result.append(_piece("carousel", "carousel", LABELS["carousel"], copy, direction, _ids(*(s.get("evidence_ids") for s in slides))))
        if email := plan.get("email"):
            copy_of, direction_of = EMAIL[version]
            result.append(_piece("email", "email", LABELS["email"], _pick(email, copy_of), _pick(email, direction_of),
                                 email.get("evidence_ids") or []))
        if caption := plan.get("caption"):
            copy_of, direction_of = CAPTION[version]
            result.append(_piece("caption", "caption", LABELS["caption"], _pick(caption, copy_of), _pick(caption, direction_of), []))
        if stories := plan.get("stories"):
            result.append(_piece("stories", "stories", LABELS["stories"], {}, {"frames": stories["frames"]}, []))
        return result
    # Version 1: directions only (its pieces were never written as copy); no caption or stories.
    for n, reel in enumerate(document.get("reels") or [], 1):
        result.append(_piece(f"reel_{n}", "reel", f"Reel {n}", {}, _pick(reel, ("reader_job", "direction", "outline")),
                             reel.get("evidence_ids") or []))
    if slides := document.get("carousel"):
        result.append(_piece("carousel", "carousel", LABELS["carousel"], {},
                             {"reader_job": document.get("carousel_reader_job"), "slides": _slides(slides, "direction")},
                             _ids(*(s.get("evidence_ids") for s in slides))))
    if email := document.get("email"):
        result.append(_piece("email", "email", LABELS["email"], {}, _pick(email, ("reader_job", "direction", "outline")),
                             email.get("evidence_ids") or []))
    return result


def default_anchor(keys: list[str]) -> str | None:
    """The anchor rule (ANCHOR_RULE) over a plan's piece keys."""
    for channel in ANCHOR_ORDER:
        found = next((k for k in keys if k == channel or k.startswith(channel + "_")), None)
        if found:
            return found
    return None


def anchor_of(row: dict, plan_pieces: list[dict] | None = None) -> dict:
    """The anchor: the person's choice when its piece is still in the plan, else the rule's; with the pieces to choose from."""
    plan_pieces = pieces(row) if plan_pieces is None else plan_pieces
    keys = [p["key"] for p in plan_pieces]
    chosen = (row["content_body"].get("review") or {}).get("anchor") or {}
    options = [{"key": p["key"], "label": p["label"]} for p in plan_pieces]
    if chosen.get("key") in keys:
        return {"key": chosen["key"], "chosen_by": "person", "actor": chosen.get("actor"), "at": chosen.get("at"),
                "rule": ANCHOR_RULE, "note": None, "options": options}
    note = (f"The piece a person chose as the anchor ({chosen['key']}) is no longer in the format plan; the rule applies"
            if chosen.get("key") else None)
    return {"key": default_anchor(keys), "chosen_by": "rule", "actor": None, "at": None, "rule": ANCHOR_RULE, "note": note,
            "options": options}


def choose_anchor(row: dict, value=KEEP, actor: str | None = None) -> None:
    """A person's anchor choice at Gate 2, set on the row's review block. KEEP drops a choice whose piece left the plan."""
    review = row["content_body"]["review"]
    keys = [p["key"] for p in pieces(row)]
    if value is KEEP:
        if (review.get("anchor") or {}).get("key") not in keys:
            review.pop("anchor", None)
        return
    if value is None:
        review.pop("anchor", None)
        return
    if not isinstance(value, str) or value not in keys:
        raise ValueError("The anchor must be one of this brief's pieces: " + (", ".join(keys) or "the plan has none"))
    review["anchor"] = {"key": value, "actor": actor, "at": datetime.now(UTC).isoformat()}


def parent_anchor(parent: dict | None) -> dict:
    """The anchor choice a revision inherits from the version it revises, as review fields."""
    chosen = (((parent or {}).get("content_body") or {}).get("review") or {}).get("anchor")
    return {"anchor": dict(chosen)} if chosen else {}


def _unique(lines) -> list[str]:
    seen, result = set(), []
    for line in lines:
        text = (line or "").strip()
        if text and " ".join(text.lower().split()) not in seen:
            seen.add(" ".join(text.lower().split()))
            result.append(text)
    return result


def message_spine(row: dict) -> dict:
    """The one central message every piece keeps, and the lines that support it."""
    document = row["content_body"]["document"]
    if version_of(row) in LEDGER:
        body = document["body"]
        sharpened = (body.get("sharpened_point") or {}).get("text")
        text = sharpened or body["approved_angle"]["core_perspective"]
        return {"text": text, "source": "sharpened_point" if sharpened else "approved_angle",
                "supporting": [x for x in _unique([text, body.get("central_point"), body["wia_perspective"],
                                                   body["narrative_outline"]["main_point"]]) if x != text.strip()]}
    text = document["core_insight"]
    return {"text": text, "source": "core_insight",
            "supporting": [x for x in _unique([text, *document.get("message_spine", [])]) if x != text.strip()]}


def _cta(row: dict) -> dict:
    document = row["content_body"]["document"]
    if version_of(row) in LEDGER:
        return dict(document["header"]["cta"])
    cta = document.get("cta") or {}
    text = (cta.get("text") or "").strip() or None
    # A v1 brief's CTA is the one a person selected at Gate 1, or deferred to development.
    choice = cta.get("choice") or ("explicit" if text else "decide_in_development")
    return {"choice": choice, "track": None, "action": text, "offer_connection": None, "chosen_by": "person" if text else None}


def claims(row: dict) -> list[dict]:
    """Every claim with what supports it, in one shape: kind is the claim class (v2, v3) or kind (v1); status the ledger's
    status (v3) or the source status (v1)."""
    document = row["content_body"]["document"]
    if version_of(row) in LEDGER:
        return [{"claim_id": c["claim_id"], "text": c["text"], "kind": c["claim_class"], "status": c.get("status"),
                 "evidence_ids": c.get("evidence_ids") or [], "quote": c.get("quote"), "public_quote": c.get("public_quote", False),
                 "numeric_facts": c.get("numeric_facts") or [], "notes": _unique([(c.get("flag") or {}).get("message"), c.get("note")])}
                for c in document["body"]["claims"]]
    return [{"claim_id": c["claim_id"], "text": c["text"], "kind": c["kind"], "status": c["source_status"],
             "evidence_ids": c["evidence_ids"], "quote": c["quote"], "public_quote": c["public_quote"],
             "numeric_facts": c["numeric_facts"], "notes": c["qualifications"]} for c in document["claims"]]


def before_publishing(row: dict) -> list[dict]:
    """What must be settled before publishing: v2 and v3's items (P1, P2, ... as the answers route names them); v1's open
    questions and the claims it lists as needing consent."""
    document = row["content_body"]["document"]
    if version_of(row) in LEDGER:
        return [{"id": f"P{i}", "text": x["text"], "kind": x["kind"], "required": x["required"], "answer": x.get("answer")}
                for i, x in enumerate(document["body"]["before_publishing"], 1)]
    return ([{"id": q["question_id"], "text": q["text"], "kind": "question", "required": q["required"], "answer": q.get("answer")}
             for q in document.get("open_questions", [])]
            + [{"id": f"C{i}", "text": text, "kind": "permission", "required": True, "answer": None}
               for i, text in enumerate(document.get("claims_requiring_consent", []), 1)])


def _most_restrictive(values, order) -> str | None:
    known = [v for v in values if v in order]
    return min(known, key=order.index) if known else None


def evidence_consent(conn, row: dict, cited: set[str]) -> list[dict]:
    items = row.get("selected_evidence") or []
    review = row["content_body"].get("review") or {}
    clearances = review.get("clearances") or {}
    quotes = {}
    if version_of(row) in LEDGER:
        quotes = {e["evidence_id"]: e["quote"] for e in row["content_body"]["document"]["body"].get("evidence") or []}
    moment_ids = sorted({m for e in items for m in e.get("moment_ids") or []})
    transcript_ids = sorted({e["transcript_id"] for e in items if e.get("transcript_id")})
    moments = {r["moment_id"]: r for r in conn.execute(
        "SELECT m.moment_id, m.consent_status, c.consent AS client_consent FROM key_moments m "
        "LEFT JOIN clients c ON c.client_id = m.client_id WHERE m.moment_id = ANY(%s)", (moment_ids,))} if moment_ids else {}
    callers = {r["transcript_id"]: r["consent"] for r in conn.execute(
        "SELECT t.transcript_id, c.consent FROM transcripts t JOIN clients c ON c.client_id = t.client_id "
        "WHERE t.transcript_id = ANY(%s)", (transcript_ids,))} if transcript_ids else {}
    result = []
    for e in items:
        linked = [moments[m] for m in e.get("moment_ids") or [] if m in moments]
        if e.get("role") == "external_framing":
            status = client = "not_applicable"
            basis = "external source"
        else:
            status = _most_restrictive([m["consent_status"] for m in linked], CONSENT_ORDER) or "unknown"
            client = (_most_restrictive([m["client_consent"] for m in linked], CLIENT_ORDER)
                      or callers.get(e.get("transcript_id")) or "unknown")
            basis = "moments" if linked else "no linked moment"
        clearance = clearances.get(e["evidence_id"])
        result.append({"evidence_id": e["evidence_id"], "cited": e["evidence_id"] in cited, "role": e.get("role"),
                       "title": e.get("title"), "speaker": e.get("speaker"), "start_ms": e.get("start_ms"),
                       "quote": quotes.get(e["evidence_id"]) or e.get("excerpt"), "moment_ids": e.get("moment_ids") or [],
                       "consent_status": status, "client_consent": client, "consent_basis": basis,
                       "sensitivity": e.get("sensitivity"), "public_use": bool(e.get("public_use")),
                       "attribution_verified": bool(e.get("attribution_verified")),
                       "permission_recorded": bool(clearance),
                       "attribution_reference": (clearance or {}).get("attribution_reference")})
    return result


def topics(conn, angle_id: str) -> list[dict]:
    """The registry's active topics of the card's moments, the most shared first."""
    return [dict(r) for r in conn.execute(
        "SELECT t.topic_id, t.name, count(*)::int AS moments FROM angle_moments am JOIN moment_topics mt ON mt.moment_id = am.moment_id "
        "JOIN topics t ON t.topic_id = mt.topic_id WHERE am.angle_id = %s AND t.status = 'active' "
        "GROUP BY t.topic_id, t.name ORDER BY count(*) DESC, t.name", (angle_id,))]


def publishing(conn, row: dict) -> dict:
    """The card's series and its place in the strategist's publishing order for its week (strategist v5, E.B21)."""
    card = (((row["content_body"].get("provenance") or {}).get("angle") or {}).get("body") or {}).get("card") or {}
    rank = card.get("rank")
    angle = conn.execute("SELECT run_id FROM content_angles WHERE angle_id=%s", (row["angle_id"],)).fetchone()
    refs = conn.execute(
        "SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation' AND status='completed' "
        "ORDER BY finished_at DESC NULLS LAST, job_id DESC LIMIT 1", (angle["run_id"],)).fetchone() if angle else None
    order = ((refs or {}).get("result_refs") or {}).get("publishing_order")
    known = isinstance(order, list) and isinstance(rank, int)
    return {"series": card.get("series"),
            "publishing_order": {"rank": rank if isinstance(rank, int) else None,
                                 "position": order.index(rank) + 1 if known and rank in order else None,
                                 "of": len(order) if isinstance(order, list) else None, "held": bool(known and rank not in order),
                                 "known": isinstance(order, list)}}


def view(conn, row: dict) -> dict:
    """The hand-off view of a brief row as gate_two.get returns it (with its blockers and can_consume)."""
    version = version_of(row)
    document = row["content_body"]["document"]
    plan_pieces = pieces(row)
    anchor = anchor_of(row, plan_pieces)
    for p in plan_pieces:
        p["anchor"] = p["key"] == anchor["key"]
    if version in LEDGER:
        header, body = document["header"], document["body"]
        meta = {"title": body["approved_angle"]["title"], "core_perspective": body["approved_angle"]["core_perspective"],
                "audience": header["audience"], "purpose": header["purpose"], "content_type": header["content_type"],
                "point_of_view": header["point_of_view"], "wia_perspective": body["wia_perspective"]}
        channels = list(header.get("channels") or [])
        cited = set(_ids([e["evidence_id"] for e in body.get("evidence") or []], *(c.get("evidence_ids") for c in body["claims"])))
    else:
        card = ((((row["content_body"].get("provenance") or {}).get("angle") or {}).get("body") or {}).get("card") or {})
        meta = {"title": document["title"], "core_perspective": document["angle_statement"], "audience": document["audience"],
                "purpose": card.get("pillar"), "content_type": card.get("content_type"), "point_of_view": None,
                "wia_perspective": None}
        channels = ["reel", "carousel", "email"]
        cited = set(_ids(*(c["evidence_ids"] for c in document["claims"]), *(p["evidence_ids"] for p in plan_pieces)))
    present = {p["channel"] for p in plan_pieces}
    # A v4 brief's captions travel with their Reels and carousel (E.B33): the caption channel has its pieces there.
    if any((p["copy"] or {}).get("caption") for p in plan_pieces):
        present.add("caption")
    found = topics(conn, row["angle_id"])
    return {"handoff_version": HANDOFF_VERSION, "brief_id": row["brief_id"], "schema_version": version,
            "content_hash": row["content_hash"], "approval_status": row["approval_status"],
            "approved_hash": row.get("approved_hash"), "approved_by": row.get("approved_by"),
            "approved_at": row["approved_at"].isoformat() if hasattr(row.get("approved_at"), "isoformat") else row.get("approved_at"),
            "can_consume": row["can_consume"], "blockers": row["blockers"],
            "week_id": row["week_id"], "angle_id": row["angle_id"], **meta, "cta": _cta(row),
            "message_spine": message_spine(row), "anchor": {k: anchor[k] for k in ("key", "chosen_by", "actor", "at", "rule", "note")},
            "pieces": plan_pieces, "channels": channels, "channels_without_piece": [c for c in channels if c not in present],
            **publishing(conn, row), "topic": found[0] if found else None, "topics": found,
            "claims": claims(row), "before_publishing": before_publishing(row),
            "evidence": evidence_consent(conn, row, cited)}


# ---- version 2 (Phase NP, NP.B1; the content-packs plan, section 5.2) ------------------------------------------------------
# What the content pack's finisher and its fidelity loop need beyond version 1: the brief's strategy, each evidence item's
# call date, each claim's field as a piece and leaf, and the lines a person wrote at Gate 2 (locks) with who wrote them.
# The pack reads only this view (R56). Version 1 stays what GET /briefs/{id}/handoff answers, so its consumers keep working.

HANDOFF_VERSION_V2 = "brief_handoff_v2"
STRATEGY_FIELDS = ("central_point", "wia_perspective", "audience", "supporting_example", "narrative_outline",
                   "strategic_purpose", "intended_shift", "cta_why", "sharpened_point", "point_of_view")


def strategy(row: dict) -> dict | None:
    """The brief's strategy sections (v2 to v4), for the finisher: the supporting example with its details and who did what,
    the narrative outline, the strategic purpose, the intended shift and why the CTA."""
    if version_of(row) not in LEDGER:
        return None
    body = row["content_body"]["document"]["body"]
    return {k: body.get(k) for k in STRATEGY_FIELDS if k in body}


def claim_places(row: dict) -> list[dict]:
    """Each ledger claim with its field as a path (0-based, briefs/paths.py) and, when it is copy of a piece, the hand-off
    piece key and the leaf inside it."""
    if version_of(row) not in LEDGER:
        return []
    from ..packs.contracts_v2 import translate_lock
    from .ledger_v3 import field_path
    body = row["content_body"]["document"]["body"]
    out = []
    for c in body.get("claims") or []:
        try:
            path = field_path(c.get("field") or "", body) if c.get("field") else None
        except (ValueError, TypeError):
            path = None
        place = translate_lock(path) if path else None
        out.append({"claim_id": c["claim_id"], "field": c.get("field"), "path": path,
                    "piece": place[0] if place and place[0] != "*" else None, "leaf": place[1] if place else None})
    return out


def lock_authors(conn, row: dict) -> dict[str, dict]:
    """Who last wrote each locked line, from the change records of the brief's versions (newest first): a path locked by an
    edit names that edit's person and time."""
    from . import paths
    found: dict[str, dict] = {}
    seen = set()
    current = row
    while current and current["brief_id"] not in seen:
        seen.add(current["brief_id"])
        change = (current["content_body"] or {}).get("change") or {}
        if change.get("kind") == "edit":
            for p in change.get("fields") or []:
                try:
                    key = paths.canonical(p)
                except ValueError:
                    continue
                found.setdefault(key, {"by": change.get("by"), "at": change.get("at")})
        parent = current.get("supersedes_id")
        current = conn.execute("SELECT brief_id,supersedes_id,content_body FROM content_briefs WHERE brief_id=%s",
                               (parent,)).fetchone() if parent and conn is not None else None
    return found


def locks(conn, row: dict, settings=None) -> list[dict]:
    """The lines a person wrote at Gate 2 (review.locked_fields), each with its place in the pack's terms (the hand-off piece
    key and the leaf; a None leaf is the whole piece; piece "*" the whole format plan), its value, its author and whether the
    author acted under D12's delegation (R55)."""
    from ..gates.decisions import wia_review
    from ..packs.contracts_v2 import translate_lock
    from . import paths
    if version_of(row) not in LEDGER:
        return []
    body = row["content_body"]["document"]["body"]
    authors = lock_authors(conn, row)
    out = []
    for raw in row["content_body"].get("review", {}).get("locked_fields") or []:
        try:
            path = paths.canonical(raw)
        except ValueError:
            continue
        place = translate_lock(path)
        if place is None or not paths.exists(body, path):
            continue
        who = authors.get(path) or next((a for p, a in authors.items() if paths.overlaps(p, path)), None) or {}
        author = who.get("by") or row.get("updated_by") or "unknown"
        out.append({"piece": place[0], "leaf": place[1], "path": path, "value": paths.get(body, path), "author": author,
                    "at": who.get("at"), "delegated": not wia_review(settings, author, author)})
    return out


def call_dates(conn, items: list[dict]) -> dict[str, str | None]:
    """Each evidence item's call date (the transcript's occurred_at), by evidence id."""
    ids = sorted({e["transcript_id"] for e in items if e.get("transcript_id")})
    dated = {r["transcript_id"]: r["occurred_at"] for r in conn.execute(
        "SELECT transcript_id,occurred_at FROM transcripts WHERE transcript_id=ANY(%s)", (ids,))} if ids else {}
    return {e["evidence_id"]: (dated[e["transcript_id"]].isoformat() if hasattr(dated.get(e.get("transcript_id")), "isoformat")
                               else None) for e in items}


def quotable(item: dict, roster: list[dict]) -> bool:
    """Whether copy may quote this evidence word for word: a client's words always (their okay is a before-publishing
    note, never a gate; the owner, 24 October); the team's words only when the source allows public use or a person
    recorded a clearance at Gate 2. Anything else is told in reported speech."""
    from ..packs.checks import speaker_class
    if speaker_class(item.get("speaker"), roster) != "wia":
        return True
    return bool(item.get("public_use") or item.get("permission_recorded"))


def view_v2(conn, row: dict, settings=None) -> dict:
    """Hand-off version 2: version 1's view plus the strategy, call dates, claim places, locks and the attested facts and
    context a person gave at the gates (5.B7). A row as gate_two.get returns it."""
    base = view(conn, row)
    dates = call_dates(conn, row.get("selected_evidence") or [])
    places = {p["claim_id"]: p for p in claim_places(row)}
    context = [{"kind": i.get("kind"), "text": i.get("text"), "author": i.get("author"), "on": str(i.get("created_at") or "")[:10]}
               for i in (row.get("context_items") or []) if i.get("in_brief", True)]
    provenance = row["content_body"].get("provenance") or {}
    beliefs = provenance.get("beliefs")
    # The offer descriptors pinned with the brief (E.B34): the only wording a piece may describe an offer with.
    offers = [{"offer": o.get("offer"), "descriptors": o.get("descriptors"), "who_does_what": o.get("who_does_what")}
              for o in (provenance.get("offer_descriptors") or {}).get("offers") or []]
    return {**base, "handoff_version": HANDOFF_VERSION_V2, "strategy": strategy(row), "offer_descriptors": offers,
            "evidence": [{**e, "call_date": dates.get(e["evidence_id"]), "quotable": quotable(e, provenance.get("roster") or [])}
                         for e in base["evidence"]],
            "claims": [{**c, **{k: v for k, v in (places.get(c["claim_id"]) or {}).items() if k != "claim_id"}} for c in base["claims"]],
            "locks": locks(conn, row, settings), "context": context, "beliefs": beliefs}
