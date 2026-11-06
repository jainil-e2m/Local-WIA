"""Gate 1 dispositions for strategist cards and considered ideas (E.B20, R45; the first slice of 3.B7 and 3.B9).

A disposition is what Whitney decides about an item she was shown: develop, reframe, hold, internal or skip.
Every disposition writes one `decisions` row and one `calibration_labels` row (migration 005) in the same
transaction as its effect, with the verified actor and the author whose judgement it records (Whitney, or a
named team member relaying her). These rows are the benchmark (E.B2).

- develop is approval: gate_one.decide's path, with verify acknowledgements and the CTA or "decide in development".
- reframe writes a new card version from the reframed title or point; the brief uses that version once it is
  reassessed and developed.
- hold keeps the card pending until a date, stored in content_body until migration 008 adds the column.
- internal and skip close the card for public content (approval_status 'rejected'); the label says which.
- revive turns a considered idea into a proposed card, which matching must assess before it can be developed.

A card's disposition may carry the reviewer's ratings on rubric 2.3a (E.X7, gates/rubric.py): every criterion, 1 to 5,
stored on the label with the rubric's version and text hash.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from psycopg.types.json import Jsonb

from .. import gate_one
from . import rubric
from ..card_contracts import AngleCard, AngleCardV5, AngleCardV7, card_point, is_v7
from ..matching import is_card
from ..repository import identifier, insert
from ..store import canonical_hash

DISPOSITIONS = ("develop", "reframe", "hold", "internal", "skip")
CONSIDERED_DISPOSITIONS = ("hold", "internal", "skip")
# Whitney's own categories (research/chatgpt-export-2026-10-18/synthesis.md), then the strategist's ranking terms.
REASON_CODES = ("positioning", "audience", "accuracy", "voice", "format", "edit_scope", "strategic_fit",
                "distinctiveness", "duplicate", "evidence", "timing", "internal_use", "strong", "other")
# A reframe changes the idea's framing, never its grounding or rank.
# A strategist v7 card's point is `point`, or `core_perspective` from a screen built for earlier cards (gate_one maps it).
REFRAME_FIELDS = ("title", "core_perspective", "point", "why_it_matters", "audience")
NEXT_STEP = "The new version's comparison check is queued (see its check); develop it once the check completes"


def _author(author, actor):
    author = (author or "").strip() or actor
    if len(author) > 200:
        raise ValueError("Author is too long")
    return author


def _reason(disposition, reason_code):
    if reason_code is None:
        if disposition == "develop":
            return None
        raise ValueError(f"A {disposition} disposition needs a reason code: " + ", ".join(REASON_CODES))
    if reason_code not in REASON_CODES:
        raise ValueError("Unknown reason code; use one of: " + ", ".join(REASON_CODES))
    return reason_code


def wia_review(settings, actor, author) -> bool:
    """Whether a decision records WIA's own judgement: its actor, or the author it names (a team member relaying
    Whitney), is one of WIA's reviewers (ATELIER_WIA_REVIEWERS). Section 2.3: success is measured by WIA, so a decision
    recorded under D12's delegation is kept but is not WIA's label. With no list configured, none is."""
    from .roles import key, listed
    reviewers = listed(settings, "wia_reviewers") if settings is not None else frozenset()
    return bool(reviewers) and (key(actor) in reviewers or key(author) in reviewers)


def record(conn, *, item_kind, item_id, week_id, disposition, action, actor, author, reason_code=None, note=None,
           reframe=None, central_point_kept=None, hold_until=None, expected_hash=None, resulting_item_id=None,
           details=None, settings=None, rubric_ratings=None):
    """One decision and the label that points to it; returns the decision ID.

    The label is WIA's (source gate) only for a WIA reviewer's decision (wia_review); any other is a proxy from source
    gate_delegated, readable but never ground truth (evaluation.benchmark.ground_truth)."""
    own = wia_review(settings, actor, author)
    decision_id = identifier("decision")
    insert(conn, "decisions", {
        "decision_id": decision_id, "item_kind": item_kind, "item_id": item_id, "week_id": week_id, "action": action,
        "disposition": disposition, "reason_code": reason_code, "note": note, "reframe": reframe,
        "central_point_kept": central_point_kept, "hold_until": hold_until, "actor": actor, "author": author,
        "expected_hash": expected_hash, "resulting_item_id": resulting_item_id,
        "details": {**(details or {}), "wia_review": own,
                    **({"rubric_version": rubric_ratings["version"]} if rubric_ratings else {})}})
    insert(conn, "calibration_labels", {
        "label_id": identifier("label"), "item_kind": item_kind, "item_id": item_id, "decision_id": decision_id,
        "week_id": week_id, "disposition": disposition, "reason_code": reason_code, "reframe": reframe,
        "central_point_kept": central_point_kept, "rubric_ratings": rubric_ratings, "rater": actor, "author": author,
        "source": "gate" if own else "gate_delegated", "proxy": not own,
        "details": {**(details or {}), **({"note": note} if note else {}), **({} if own else {"delegated": True})}})
    return decision_id


def _card_row(a):
    if not is_card(a["content_body"]):
        raise ValueError("Dispositions apply to strategist cards; use approve or reject for earlier angles")
    if a["approval_status"] == "approved":
        raise ValueError("Angle has already been approved")
    return a


def dispose(repo, angle_id, expected_hash, disposition, actor, *, reason_code=None, note=None, author=None,
            reframe=None, central_point_kept=None, hold_until=None, cta=None, overlap_ack=False, verified=None,
            rubric_ratings=None, rubric_version=None):
    if disposition not in DISPOSITIONS:
        raise ValueError("Unknown disposition; use one of: " + ", ".join(DISPOSITIONS))
    gate_one.require(repo, actor, "decide")
    author, reason_code = _author(author, actor), _reason(disposition, reason_code)
    rated = rubric.ratings(rubric_ratings, rubric_version)
    note = (note or "").strip() or None

    def rows(conn, a, **extra):
        # Called inside the effect's transaction; a non-card angle rolls the effect back.
        if not is_card(a["content_body"]):
            raise ValueError("Dispositions apply to strategist cards; use approve or reject for earlier angles")
        return record(conn, item_kind="angle", item_id=angle_id, week_id=a["week_id"], disposition=disposition,
                      action="gate_one_" + disposition, actor=actor, author=author, reason_code=reason_code, note=note,
                      expected_hash=expected_hash, details={"run_id": a["run_id"]}, settings=repo.settings,
                      rubric_ratings=rated, **extra)

    if disposition == "develop":
        result = gate_one.decide(repo, angle_id, expected_hash, "approved", cta, overlap_ack, note, actor,
                                 verified=verified, record=rows)
        return {**result, "disposition": disposition}
    if disposition in ("internal", "skip"):
        if reframe or hold_until or central_point_kept is not None:
            raise ValueError(f"A {disposition} disposition takes a reason code and a note only")
        result = gate_one.decide(repo, angle_id, expected_hash, "rejected", None, False, note, actor, record=rows)
        return {**result, "disposition": disposition}
    with repo.connection() as conn:
        a = _card_row(gate_one.locked(conn, angle_id, expected_hash))
        if disposition == "hold":
            if not isinstance(hold_until, date) or hold_until <= date.today():
                raise ValueError("A hold needs a date after today")
            hold = {"until": hold_until.isoformat(), "reason_code": reason_code, "note": note, "author": author}
            # Until migration 008 adds hold_until to content_angles. The hold is review state, not card text, so
            # the content hash (and the matching bound to it) is unchanged.
            conn.execute("UPDATE content_angles SET content_body=%s,updated_by=%s,updated_at=now() WHERE angle_id=%s",
                         (Jsonb({**a["content_body"], "gate_one_hold": hold}), actor, angle_id))
            decision_id = rows(conn, a, hold_until=hold_until)
            repo.event(conn, a["run_id"], "gate_one_hold", "Card held", details={"angle_id": angle_id, "actor": actor})
            return {"angle_id": angle_id, "disposition": disposition, "hold_until": hold["until"],
                    "decision_id": decision_id}
        # Reframe: a new card version from the reframed title or point.
        if not isinstance(reframe, dict) or not reframe or set(reframe) - set(REFRAME_FIELDS):
            raise ValueError("A reframe changes only: " + ", ".join(REFRAME_FIELDS))
        if "point" in reframe and not is_v7(a["content_body"]["card"]):
            raise ValueError("Only a strategist v7 card has a point field; reframe core_perspective on this card")
        if not ({"title", "core_perspective", "point"} & set(reframe)):
            raise ValueError("A reframe needs the reframed title or central point")
        if not isinstance(central_point_kept, bool):
            raise ValueError('A reframe records whether the central point was kept (true or false)')
        saved = gate_one.save_card_edit(repo, conn, a, reframe, actor, note, decided=True)
        decision_id = rows(conn, a, reframe=reframe, central_point_kept=central_point_kept,
                           resulting_item_id=saved["angle_id"])
        return {**saved, "supersedes_id": angle_id, "disposition": disposition, "decision_id": decision_id,
                "next": NEXT_STEP}


def selection_hash(run_id, refs):
    """Binds a considered-idea action to the selection block the reviewer saw."""
    return canonical_hash({"run_id": run_id, "considered_not_selected": refs.get("considered_not_selected", [])})


def _considered(conn, week_id, index, expected_hash):
    latest = conn.execute("""SELECT run_id,result_refs FROM pipeline_jobs WHERE week_id=%s AND stage='angle_generation'
        AND status='completed' AND result_refs ? 'week_summary' ORDER BY finished_at DESC,job_id DESC LIMIT 1""",
                          (week_id,)).fetchone()
    if not latest:
        raise ValueError("This week has no strategist selection")
    refs = latest["result_refs"]
    if selection_hash(latest["run_id"], refs) != expected_hash:
        raise ValueError("Selection changed; refresh before saving")
    ideas = refs.get("considered_not_selected", [])
    if not 0 <= index < len(ideas):
        raise ValueError("No considered idea at that index")
    item_id = f"{latest['run_id']}:{index}"
    # Serialise actions on one idea, so two reviewers cannot both revive it.
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (item_id,))
    return latest["run_id"], refs, ideas[index], item_id


def considered_decision(repo, week_id, index, expected_hash, disposition, actor, *, reason_code=None, note=None,
                        author=None, hold_until=None):
    """Hold, internal or skip on a considered idea: a label only, since the idea is not a card."""
    if disposition not in CONSIDERED_DISPOSITIONS:
        raise ValueError("A considered idea takes hold, internal or skip here; revive it to develop or reframe it")
    gate_one.require(repo, actor, "decide")
    author, reason_code = _author(author, actor), _reason(disposition, reason_code)
    if disposition == "hold" and (not isinstance(hold_until, date) or hold_until <= date.today()):
        raise ValueError("A hold needs a date after today")
    with repo.connection() as conn:
        run_id, _, idea, item_id = _considered(conn, week_id, index, expected_hash)
        decision_id = record(conn, item_kind="considered_idea", item_id=item_id, week_id=week_id,
                             disposition=disposition, action="considered_" + disposition, actor=actor, author=author,
                             reason_code=reason_code, note=(note or "").strip() or None,
                             hold_until=hold_until if disposition == "hold" else None, expected_hash=expected_hash,
                             details={"run_id": run_id, "idea": idea["idea"]}, settings=repo.settings)
        return {"item_id": item_id, "disposition": disposition, "decision_id": decision_id}


def _revived_v7(fields, idea, moment_ids, quotes, reason, note, rank) -> dict:
    """A revived idea in a strategist v7 week is a v7 card, so it passes the same gates as its siblings and a refresh rewrites
    it whole. The reviewer's form names what the idea lacks; the point's tests start plain and unclaimed until a person edits
    the card or asks for a refreshed version."""
    point = fields.get("point") or fields.get("core_perspective") or idea["idea"]
    return AngleCardV7.model_validate({
        "rank": rank, "title": fields.get("title") or idea["idea"], "pillar": fields.get("pillar"),
        "content_type": fields.get("content_type"), "series": fields.get("series"), "audience": fields.get("audience"),
        "why_it_matters": fields.get("why_it_matters"), "wia_in_action": fields.get("wia_in_action") or idea["idea"],
        "evidence_points": ([q for q in quotes if q] or [idea["idea"]])[:3],
        "guardrail": "Revived by a person from the ideas not chosen: check each line against the call before stating it as fact.",
        "point": point, "point_is_about": "wia_belief",
        "surprise_for_experienced_advertiser": {"surprising": False, "reason": "Not assessed yet; a person revived this idea."},
        "reader_takeaway": "I want a team that thinks like this.",
        "reader_fit": {"buyer": "established_owner", "buyer_statement": "Established owners who already invest in their marketing.",
                       "why": fields.get("audience")},
        "belief_ref": "Not set yet",
        "offer_fit": {"offer": fields.get("offer_connection"), "cta_slot": "none", "calendar_note": "Not set yet; decided when it is developed."},
        "public_stance": {"takes_stance": False, "stance": None}, "recurrence": None, "moment_ids": moment_ids,
        "verify_before_publishing": [], "why_selected": reason + (f". {note.strip()}" if note and note.strip() else ""),
    }).model_dump(mode="json")


def revive(repo, week_id, index, expected_hash, card_fields, actor, *, reason_code=None, note=None, author=None):
    """A proposed card from a considered idea. card_fields supplies what the idea lacks (pillar, type, audience,
    why it matters) and may replace the title or central point, which default to the idea itself."""
    gate_one.require(repo, actor, "decide")
    author = _author(author, actor)
    if reason_code is not None and reason_code not in REASON_CODES:
        raise ValueError("Unknown reason code; use one of: " + ", ".join(REASON_CODES))
    allowed = {"title", "pillar", "content_type", "audience", "core_perspective", "why_it_matters", "wia_in_action",
               "offer_connection", "series", "point"}
    if set(card_fields) - allowed:
        raise ValueError("A revived card takes only: " + ", ".join(sorted(allowed)))
    with repo.connection() as conn:
        run_id, refs, idea, item_id = _considered(conn, week_id, index, expected_hash)
        if conn.execute("SELECT 1 FROM decisions WHERE item_kind='considered_idea' AND item_id=%s AND disposition='revive'",
                        (item_id,)).fetchone():
            raise ValueError("This idea has already been revived")
        moment_ids = list(idea["moment_ids"])
        # By id, not by week: a cycle over a date window reads scenes that belong to documents, with no week of their own (3.B2).
        # The idea comes from this week's selection, whose hash was just checked.
        moments = {r["moment_id"]: r for r in conn.execute(
            "SELECT moment_id,moment_body FROM key_moments WHERE moment_id=ANY(%s)", (moment_ids,))}
        if not moment_ids or set(moment_ids) - set(moments):
            raise ValueError("The idea's scenes are not saved for this week")
        siblings = [r["content_body"]["card"] for r in conn.execute(
            "SELECT content_body FROM content_angles WHERE run_id=%s AND content_body ? 'card'", (run_id,))]
        v5 = any("series" in card for card in siblings)
        contract = AngleCardV5 if v5 else AngleCard
        reason = f"Revived from the considered ideas by {author}; first dropped because: {idea['reason']}"
        quotes = [moments[m]["moment_body"].get("quote") for m in moment_ids]
        if any(is_v7(c) for c in siblings):
            card = _revived_v7(card_fields, idea, moment_ids, quotes, reason, note, 1 + max(c["rank"] for c in siblings))
        else:
            card = contract.model_validate({
                "rank": 1 + max((c["rank"] for c in siblings), default=0),
                "title": card_fields.get("title") or idea["idea"],
                "pillar": card_fields.get("pillar"), "content_type": card_fields.get("content_type"),
                "audience": card_fields.get("audience"),
                "core_perspective": card_fields.get("core_perspective") or idea["idea"],
                "why_it_matters": card_fields.get("why_it_matters"),
                "wia_in_action": card_fields.get("wia_in_action"), "offer_connection": card_fields.get("offer_connection"),
                "moment_ids": moment_ids, "evidence_points": [q for q in quotes if q] or [idea["idea"]],
                "verify_before_publishing": [], "why_selected": reason + (f". {note.strip()}" if note and note.strip() else ""),
                **({"series": card_fields.get("series")} if v5 else {})}).model_dump(mode="json")
        point = card_point(card)
        qualifiers = list(dict.fromkeys(q for m in moment_ids for q in moments[m]["moment_body"].get("qualifications", [])))
        risks = list(dict.fromkeys(f"handling: {moments[m]['moment_body'].get('sensitivity')}; public reuse needs review"
                                   for m in moment_ids))
        sources = conn.execute("""SELECT DISTINCT ref->>'transcript_id' AS source FROM key_moments,
            jsonb_array_elements(evidence_refs) ref WHERE moment_id=ANY(%s)""", (moment_ids,)).fetchall()
        body = {"title": card["title"], "argument": point, "audience": card["audience"], "tension": "",
                "take": point, "mechanism": card["wia_in_action"] or point,
                "reader_decision": None, "source_assertions": [], "inference": None, "qualifiers": qualifiers,
                "risks": risks, "card": card, "revived_from": item_id,
                "source_family_id": "source_family_" + canonical_hash(sorted(r["source"] for r in sources))[:24]}
        # Verified like a generated card (E.B10): without a ledger its approval would check no blocking flag.
        from ..cycle.verification import ledger_from_database
        body["ledger"] = ledger_from_database(conn, card)
        angle_id = identifier("angle")
        digest = canonical_hash({"body": body, "moments": sorted(moment_ids)})
        insert(conn, "content_angles", {"angle_id": angle_id, "week_id": week_id, "run_id": run_id, "content_body": body,
                                        "content_hash": digest, "updated_by": actor,
                                        "first_generated_at": datetime.now(UTC)})
        for moment_id in moment_ids:
            insert(conn, "angle_moments", {"angle_id": angle_id, "moment_id": moment_id,
                                           "evidence_role": "supports_argument"})
        decision_id = record(conn, item_kind="considered_idea", item_id=item_id, week_id=week_id, disposition="revive",
                             action="considered_revive", actor=actor, author=author, reason_code=reason_code,
                             note=(note or "").strip() or None, expected_hash=expected_hash,
                             resulting_item_id=angle_id, details={"run_id": run_id, "idea": idea["idea"]}, settings=repo.settings)
        repo.event(conn, run_id, "considered_idea_revived", "Considered idea revived as a proposed card",
                   details={"angle_id": angle_id, "item_id": item_id, "actor": actor})
        # Its comparison check (embedding, matching, duplicates) is queued with it (E.B16, E.B20).
        check = gate_one.queue_card_check(repo, conn, week_id, actor)
        return {"angle_id": angle_id, "content_hash": digest, "decision_id": decision_id, "next": NEXT_STEP, "check": check}


def latest_dispositions(conn, week_id):
    """The latest decision per item for a week, for the review view; empty before migration 005."""
    if not conn.execute("SELECT to_regclass('public.decisions') AS t").fetchone()["t"]:
        return {}
    # With the label's rubric ratings, when the reviewer rated the card (E.X7).
    rows = conn.execute("""SELECT DISTINCT ON (d.item_kind,d.item_id) d.item_kind,d.item_id,d.disposition,d.reason_code,
        d.note,d.author,d.actor,d.hold_until,d.resulting_item_id,d.central_point_kept,d.created_at,l.rubric_ratings
        FROM decisions d LEFT JOIN calibration_labels l ON l.decision_id=d.decision_id WHERE d.week_id=%s
        AND d.item_kind IN ('angle','considered_idea') ORDER BY d.item_kind,d.item_id,d.created_at DESC,d.decision_id DESC""",
                        (week_id,)).fetchall()
    return {(r["item_kind"], r["item_id"]): r for r in rows}


__all__ = ["CONSIDERED_DISPOSITIONS", "DISPOSITIONS", "REASON_CODES", "REFRAME_FIELDS", "considered_decision", "dispose", "latest_dispositions", "record", "revive", "selection_hash"]
