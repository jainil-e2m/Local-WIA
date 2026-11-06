"""The week's success measures (7.X2): the main plan's section 4.5 and the content-packs plan's section 4.6, read from the
database only, for one week (`storage_cli week-measures --week <week_id> [--json]`).

Every count is split into WIA's own rows and delegated ones (plan 2.3, R55), and only WIA's count toward the bar:
- a Gate 1, Gate 2 or pack decision is WIA's when it was recorded as WIA's (`decisions.details.wia_review`, the label's
  source `gate` rather than `gate_delegated`): the record at the time, never today's `ATELIER_WIA_REVIEWERS`;
- a person's pack edit is WIA's when its change record says it was not delegated (`change.delegated`, as NP.B13 reads it);
- a brief edit at Gate 2 and a published piece carry no such record, so they are WIA's when the person who made them is on
  today's `ATELIER_WIA_REVIEWERS` (`gates.decisions.wia_review`).

What counts, in the words the report prints:
- the slate is the week's current strategist cards (the newest version of each, a reframe being the same card), without a
  duplicate matching suppressed and without a considered idea revived at Gate 1; the top five are the five best ranked;
- a card is developed, or reframed keeping the point, when any version of it has a develop decision (an approval) or a
  reframe with `central_point_kept`; a card is skipped when any version has a skip (or a plain reject);
- rubric 2.3a ratings (`rubric-2.3a.v1`) are the labels' ratings of the week's cards and, when Gate 2 records them, briefs;
- a brief is approved without rewriting its central point when the approved version's central point (contract v1's angle
  statement) is word for word the writer's first version's; "on cards WIA chose" means WIA developed the card;
- Gate 2 edits are the learning loop's field diffs of the week's approved briefs (L.B6, `knowledge/mining.edit_diffs`) in
  its deterministic categories; they are not categorised by the kinds a check covers (first touch, insider term, fidelity);
- a pack is the newest version of each content pack v2 of the week; it is ready when that version is marked ready to
  publish, with light edits or none when at most `LIGHT_EDITS` distinct lines (piece and path) were edited or put back by a
  person across its versions; a piece is published when a final is recorded from the pack; its cost is every model call of
  every run that made one of its versions (`llm_runs.details.run_id`).

A threshold of the "Done" column holds on two consecutive live weeks: it is checked on this week and the week before it.
Read only (one read-only transaction); no model call.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from statistics import mean

from fastapi import Depends

from .gates import rubric
from .gates.decisions import wia_review

LIGHT_EDITS = 3
LIGHT_RULE = (f"light edits or none: at most {LIGHT_EDITS} distinct lines (a piece and a path) edited or put back by a person "
              "across the pack's versions, whoever made them")
SIDES = ("wia", "delegated")
SKIPS = ("skip", "reject")
COST_BAR_USD = 0.85
NOT_IN_DATABASE = "not in the database: judged by reading the week"


def _counts() -> dict:
    return {"wia": 0, "delegated": 0, "all": 0}


def _side(own) -> str:
    return "wia" if own else "delegated"


def _roots(rows: list[dict], key: str) -> dict[str, str]:
    """Each row's first version (its lineage), walking `supersedes_id` within the rows given."""
    parent = {r[key]: r["supersedes_id"] for r in rows}
    out = {}
    for start in parent:
        current, seen = start, set()
        while parent.get(current) and parent[current] in parent and current not in seen:
            seen.add(current)
            current = parent[current]
        out[start] = current
    return out


def _current(rows: list[dict], key: str) -> list[dict]:
    replaced = {r["supersedes_id"] for r in rows if r["supersedes_id"]}
    return [r for r in rows if r[key] not in replaced]


# ---- cards (section 4.5, row 1) -------------------------------------------------------------------------------------------

def cards(conn, week_id: str) -> tuple[dict, dict]:
    rows = conn.execute("""SELECT angle_id,supersedes_id,content_body,selection_status FROM content_angles
        WHERE week_id=%s AND content_body ? 'card'""", (week_id,)).fetchall()
    roots = _roots(rows, "angle_id")
    slate = [r for r in _current(rows, "angle_id") if r["selection_status"] != "suppressed" and "revived_from" not in r["content_body"]]
    slate.sort(key=lambda r: (r["content_body"]["card"].get("rank") or 10**6, r["angle_id"]))
    decisions = conn.execute("""SELECT item_id,disposition,central_point_kept,details FROM decisions WHERE item_kind='angle'
        AND item_id = ANY(%s)""", ([r["angle_id"] for r in rows],)).fetchall()
    chose, skipped = {s: set() for s in SIDES}, {s: set() for s in SIDES}
    for d in decisions:
        side, root = _side((d["details"] or {}).get("wia_review")), roots[d["item_id"]]
        if d["disposition"] == "develop" or (d["disposition"] == "reframe" and d["central_point_kept"]):
            chose[side].add(root)
        if d["disposition"] in SKIPS:
            skipped[side].add(root)
    roots_of = [roots[r["angle_id"]] for r in slate]

    def count(within, found):
        out = _counts()
        for root in within:
            for s in SIDES:
                out[s] += root in found[s]
            out["all"] += any(root in found[s] for s in SIDES)
        return out

    top_three = roots_of[:3]
    result = {"slate": len(slate), "top_five": len(roots_of[:5]),
              "developed_or_reframed_keeping_the_point": count(roots_of, chose),
              "top_five_developed_or_reframed_keeping_the_point": count(roots_of[:5], chose),
              "top_three_skipped": {**{s: any(r in skipped[s] for r in top_three) for s in SIDES},
                                    "all": any(r in skipped[s] for r in top_three for s in SIDES)}}
    # Which lineages WIA developed (the cards WIA chose), for the briefs' measure.
    developed = {roots[d["item_id"]] for d in decisions if d["disposition"] == "develop" and (d["details"] or {}).get("wia_review")}
    return result, {"roots": roots, "wia_developed": developed}


# ---- rubric 2.3a (row 2) ---------------------------------------------------------------------------------------------------

def _summary(ratings: list[dict]) -> dict:
    if not ratings:
        return {"count": 0, "overall": None, "criteria": {k: None for k in rubric.KEYS}}
    return {"count": len(ratings), "overall": round(mean(float(r["overall"]) for r in ratings), 2),
            "criteria": {k: round(mean(r["criteria"][k] for r in ratings), 2) for k in rubric.KEYS}}


def ratings(conn, week_id: str) -> dict:
    rows = conn.execute("""SELECT item_kind,source,rubric_ratings FROM calibration_labels WHERE week_id=%s
        AND rubric_ratings IS NOT NULL AND rubric_ratings->>'version'=%s AND item_kind IN ('angle','brief')""",
                        (week_id, rubric.VERSION)).fetchall()
    out = {"version": rubric.VERSION}
    for name, kinds in (("cards", ("angle",)), ("briefs", ("brief",)), ("cards_and_briefs", ("angle", "brief"))):
        picked = [r for r in rows if r["item_kind"] in kinds]
        out[name] = {**{s: _summary([r["rubric_ratings"] for r in picked if _side(r["source"] == "gate") == s]) for s in SIDES},
                     "all": _summary([r["rubric_ratings"] for r in picked])}
    return out


# ---- briefs and Gate 2 edits (rows 3 and 4) --------------------------------------------------------------------------------

def _point(content_body: dict) -> str | None:
    document = (content_body or {}).get("document") or {}
    body = document.get("body") or document
    point = body.get("central_point") or body.get("angle_statement") or (body.get("approved_angle") or {}).get("core_perspective")
    return " ".join(str(point).split()) if point else None


def briefs(conn, week_id: str, card_lineage: dict) -> tuple[dict, set[str]]:
    rows = conn.execute("SELECT brief_id,supersedes_id,angle_id,content_body FROM content_briefs WHERE week_id=%s", (week_id,)).fetchall()
    by_id, roots = {r["brief_id"]: r for r in rows}, _roots(rows, "brief_id")
    approvals = conn.execute("""SELECT item_id,details FROM decisions WHERE item_kind='brief' AND disposition='approve'
        AND week_id=%s""", (week_id,)).fetchall()
    approved, kept, chosen = {s: set() for s in SIDES}, {s: set() for s in SIDES}, set()
    for d in approvals:
        brief = by_id.get(d["item_id"])
        if not brief:
            continue
        side, card = _side((d["details"] or {}).get("wia_review")), card_lineage["roots"].get(brief["angle_id"], brief["angle_id"])
        approved[side].add(card)
        if _point(brief["content_body"]) is not None and _point(brief["content_body"]) == _point(by_id[roots[brief["brief_id"]]]["content_body"]):
            kept[side].add(card)
            if side == "wia" and card in card_lineage["wia_developed"]:
                chosen.add(card)

    def count(found):
        return {**{s: len(found[s]) for s in SIDES}, "all": len(set().union(*found.values()))}
    return ({"approved": count(approved), "approved_without_rewriting_the_central_point": count(kept),
             "approved_without_rewriting_the_central_point_on_cards_wia_chose": len(chosen)}, set(by_id))


def gate_two_edits(conn, settings, week_briefs: set[str]) -> dict:
    from .knowledge import mining
    out = {"categorised_by": "the learning loop's deterministic categories (L.B6, knowledge/mining.py)",
           "check_kinds": "not categorised: no stored edit says first touch, insider term or fidelity", "edits": _counts(),
           "by_category": {s: {c: 0 for c in mining.CATEGORIES} for s in SIDES}}
    for edit in mining.edit_diffs(conn, date(2000, 1, 1), date(9999, 12, 31)):
        if edit["brief_id"] not in week_briefs or edit.get("pack") or edit.get("published"):
            continue
        side = _side(wia_review(settings, edit["editor"], edit["editor"]))
        category = mining.categorise(edit)
        out["by_category"][side][category] = out["by_category"][side].get(category, 0) + 1
        out["edits"][side] += 1
        out["edits"]["all"] += 1
    return out


# ---- packs (section 4.6) ---------------------------------------------------------------------------------------------------

def packs(conn, settings, week_id: str) -> dict:
    from .packs import contracts_v2 as c2
    rows = conn.execute("""SELECT pack_id,supersedes_id,source_brief_id,production_run_id,content_body,approval_status,approved_by,
        approved_hash,manifest_hash FROM content_packs WHERE week_id=%s AND contract_version=%s""", (week_id, c2.VERSION)).fetchall()
    roots = _roots(rows, "pack_id")
    current = _current(rows, "pack_id")
    marks = {r["item_id"]: r["details"] or {} for r in conn.execute("""SELECT DISTINCT ON (item_id) item_id,details FROM decisions
        WHERE item_kind='pack' AND action='pack_ready_to_publish' AND item_id = ANY(%s)
        ORDER BY item_id,created_at DESC,decision_id DESC""", ([p["pack_id"] for p in current],)).fetchall()}
    ready, light, edited = _counts(), _counts(), _counts()
    for pack in current:
        lineage = [r for r in rows if roots[r["pack_id"]] == roots[pack["pack_id"]]]
        lines, by_side = set(), {s: set() for s in SIDES}
        for version in lineage:
            change = (version["content_body"] or {}).get("change") or {}
            if change.get("kind") not in ("edit", "revert"):
                continue
            pieces = ",".join(sorted(change.get("pieces") or []))
            for path in change.get("paths") or []:
                lines.add((pieces, path))
                by_side["delegated" if change.get("delegated", True) else "wia"].add((pieces, path))
        for s in SIDES:
            edited[s] += len(by_side[s])
        edited["all"] += len(lines)
        if not (pack["content_body"] is not None and pack["approval_status"] == "approved" and pack["approved_hash"]
                and pack["approved_hash"] == pack["manifest_hash"]):
            continue
        mark = marks.get(pack["pack_id"])
        side = _side(mark.get("wia_review") if mark is not None else wia_review(settings, pack["approved_by"], pack["approved_by"]))
        for counts in ([ready, light] if len(lines) <= LIGHT_EDITS else [ready]):
            counts[side] += 1
            counts["all"] += 1
    briefs_of = sorted({r["source_brief_id"] for r in rows if r["source_brief_id"]})
    published = _counts()
    for piece in conn.execute("""SELECT created_by FROM published_content WHERE source_kind='approved_brief'
            AND source_ref LIKE 'pack:%%' AND brief_id = ANY(%s)""", (briefs_of,)).fetchall():
        published[_side(wia_review(settings, piece["created_by"], piece["created_by"]))] += 1
        published["all"] += 1
    runs = sorted({r["production_run_id"] for r in rows if r["production_run_id"]})
    cost = conn.execute("""SELECT count(*) AS calls,coalesce(sum(cost_usd),0) AS usd FROM llm_runs
        WHERE details->>'run_id' = ANY(%s)""", (runs,)).fetchone()
    finished = [p for p in current if p["content_body"] is not None]
    total = float(cost["usd"])
    return {"packs": len(current), "finished": len(finished), "ready": ready, "ready_with_light_edits_or_none": light,
            "light_edits_rule": LIGHT_RULE, "lines_edited_by_a_person": edited, "pieces_published": published,
            "cost": {"model_calls": cost["calls"], "total_usd": round(total, 6),
                     "per_pack_usd": round(total / len(finished), 4) if finished and cost["calls"] else None}}


# ---- the thresholds --------------------------------------------------------------------------------------------------------

def _at_least(value, bar) -> bool:
    return value is not None and value >= bar


def _rubric_first(m) -> bool:
    wia = m["rubric"]["cards_and_briefs"]["wia"]
    return _at_least(wia["overall"], 3) and _at_least(wia["criteria"]["wia_is_the_subject"], 3)


def _rubric_done(m) -> bool:
    wia = m["rubric"]["cards_and_briefs"]["wia"]
    return _at_least(wia["overall"], 3.5) and all(_at_least(v, 3) for v in wia["criteria"].values())


def _cards_first(m) -> bool:
    c = m["cards"]
    return c["slate"] >= 4 and 2 * c["developed_or_reframed_keeping_the_point"]["wia"] >= c["slate"]


def _cards_done(m) -> bool:
    c = m["cards"]
    return c["top_five_developed_or_reframed_keeping_the_point"]["wia"] >= 3 and not c["top_three_skipped"]["wia"]


def _ready_share(m, share) -> bool:
    p = m["packs"]
    return p["packs"] > 0 and p["ready_with_light_edits_or_none"]["wia"] >= share * p["packs"]


def _cost_done(m) -> bool:
    per = m["packs"]["cost"]["per_pack_usd"]
    return per is not None and per <= COST_BAR_USD


# (plan, measure, column, threshold text, check on one week's measures or None when it cannot be read from the database,
# whether the column needs two consecutive live weeks)
THRESHOLDS = [
    ("4.5", "Cards Whitney develops, or reframes keeping the point", "first live round",
     "At least half of a slate of at least four public cards", _cards_first, False),
    ("4.5", "Cards Whitney develops, or reframes keeping the point", "done",
     "At least three of the top five on two consecutive live weeks, and no skip in the top three", _cards_done, True),
    ("4.5", "Rubric 2.3a (rubric-2.3a.v1), rated in the app", "first live round", "3 or more overall and on criterion 1",
     _rubric_first, False),
    ("4.5", "Rubric 2.3a (rubric-2.3a.v1), rated in the app", "done",
     "3.5 or more overall and 3 or more on every criterion, on two consecutive live weeks", _rubric_done, True),
    ("4.5", "Briefs approved without rewriting the central point", "first live round", "At least one in the first live week",
     lambda m: m["briefs"]["approved_without_rewriting_the_central_point"]["wia"] >= 1, False),
    ("4.5", "Briefs approved without rewriting the central point", "done", "At least three, on cards WIA chose",
     lambda m: m["briefs"]["approved_without_rewriting_the_central_point_on_cards_wia_chose"] >= 3, False),
    ("4.5", "First-touch, insider-term and fidelity edits WIA makes at Gate 2", "first live round", "Recorded by kind", None, False),
    ("4.5", "First-touch, insider-term and fidelity edits WIA makes at Gate 2", "done", "None of a kind a check exists for", None, True),
    ("4.5", "Factual problems WIA finds", "first live round", "Recorded", None, False),
    ("4.5", "Factual problems WIA finds", "done", "None the ledger did not flag", None, True),
    ("4.5", "Repeats of published or prior content at Gate 1", "first live round", "Recorded", None, False),
    ("4.5", "Repeats of published or prior content at Gate 1", "done", "None unflagged", None, True),
    ("4.6", "Packs WIA marks ready with light edits or none", "first live week", "At least half", lambda m: _ready_share(m, 0.5), False),
    ("4.6", "Packs WIA marks ready with light edits or none", "done", "At least 80%", lambda m: _ready_share(m, 0.8), True),
    ("4.6", "Edits of a kind a pack check covers (first touch, insider term, who did what, quote, name)", "first live week",
     "Recorded by kind", None, False),
    ("4.6", "Edits of a kind a pack check covers (first touch, insider term, who did what, quote, name)", "done",
     "None of a checked kind", None, True),
    ("4.6", "Factual problems WIA finds in a pack", "first live week", "Recorded", None, False),
    ("4.6", "Factual problems WIA finds in a pack", "done", "None the fidelity loop did not flag", None, True),
    ("4.6", "Pieces published from packs", "first live week", "Recorded", lambda m: True, False),
    ("4.6", "Pieces published from packs", "done", "WIA publishes from the packs each week (RQ7)",
     lambda m: m["packs"]["pieces_published"]["wia"] >= 1, True),
    ("4.6", "Cost per pack", "first live week", "Recorded", lambda m: m["packs"]["cost"]["model_calls"] > 0, False),
    ("4.6", "Cost per pack", "done", f"At most USD {COST_BAR_USD:.2f} on average", _cost_done, True),
]
NOTES = {"First-touch, insider-term and fidelity edits WIA makes at Gate 2": "Gate 2 edits are categorised by the learning loop "
         "(voice, accuracy, positioning, scope, format), not by the kinds a check covers",
         "Edits of a kind a pack check covers (first touch, insider term, who did what, quote, name)": "pack edits are counted "
         "by line, not categorised by the kinds a pack check covers"}


def thresholds(this: dict, previous: dict | None) -> list[dict]:
    out = []
    for plan, measure, column, text, check, consecutive in THRESHOLDS:
        row = {"plan": plan, "measure": measure, "column": column, "threshold": text, "met": None}
        if check is None:
            row["note"] = NOTES.get(measure) or NOT_IN_DATABASE
        elif consecutive:
            row["this_week"] = check(this)
            row["previous_week"] = check(previous) if previous else None
            row["met"] = bool(row["this_week"] and row["previous_week"])
            if previous is None:
                row["note"] = "no week before this one in the database"
        else:
            row["met"] = bool(check(this))
        out.append(row)
    return out


# ---- the week ----------------------------------------------------------------------------------------------------------------

def _week(conn, settings, week: dict) -> dict:
    card_result, lineage = cards(conn, week["week_id"])
    brief_result, week_briefs = briefs(conn, week["week_id"], lineage)
    return {"week_id": week["week_id"], "week_start": week["week_start"].isoformat(), "week_end": week["week_end"].isoformat(),
            "cards": card_result, "rubric": ratings(conn, week["week_id"]), "briefs": brief_result,
            "gate_two_edits": gate_two_edits(conn, settings, week_briefs), "packs": packs(conn, settings, week["week_id"])}


def measures(repo, week_id: str) -> dict:
    """The week's measures and thresholds; the week before it is read for the two-consecutive-weeks thresholds."""
    settings = repo.settings
    with repo.connection() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        week = conn.execute("SELECT week_id,week_start,week_end FROM weeks WHERE week_id=%s", (week_id,)).fetchone()
        if not week:
            raise LookupError(f"Week not found: {week_id}")
        before = conn.execute("SELECT week_id,week_start,week_end FROM weeks WHERE week_start=%s",
                              (week["week_start"] - timedelta(days=7),)).fetchone()
        this = _week(conn, settings, week)
        previous = _week(conn, settings, before) if before else None
    return {**this, "wia_reviewers_configured": bool(getattr(settings, "wia_reviewers", ())),
            "previous_week_id": previous["week_id"] if previous else None, "thresholds": thresholds(this, previous)}


# ---- the report in words -------------------------------------------------------------------------------------------------------

def _split(counts: dict) -> str:
    return f"{counts['wia']} WIA's own, {counts['delegated']} delegated ({counts['all']} in all)"


def _rated(summary: dict) -> str:
    if not summary["count"]:
        return "none"
    criteria = ", ".join(f"{k} {v}" for k, v in summary["criteria"].items())
    return f"{summary['count']} rated, overall {summary['overall']}; {criteria}"


def text(m: dict) -> str:
    c, r, b, e, p = m["cards"], m["rubric"], m["briefs"], m["gate_two_edits"], m["packs"]
    lines = [f"Week measures for {m['week_id']} ({m['week_start']} to {m['week_end']}): main plan 4.5, content-packs plan 4.6",
             "Only WIA's own rows count toward the bar; delegated rows are shown beside them.", ""]
    if not m["wia_reviewers_configured"]:
        lines += ["Note: ATELIER_WIA_REVIEWERS is blank, so brief edits and published pieces count as delegated "
                  "(decisions keep the label they were recorded with).", ""]
    lines += ["Cards",
              f"- Public cards in the slate: {c['slate']}",
              f"- Developed, or reframed keeping the point: {_split(c['developed_or_reframed_keeping_the_point'])}",
              f"- Of the top five ({c['top_five']}): {_split(c['top_five_developed_or_reframed_keeping_the_point'])}",
              f"- A skip in the top three: WIA's own {'yes' if c['top_three_skipped']['wia'] else 'no'}, "
              f"delegated {'yes' if c['top_three_skipped']['delegated'] else 'no'}", "",
              f"Rubric 2.3a ({r['version']})"]
    for name, label in (("cards", "Cards"), ("briefs", "Briefs")):
        lines += [f"- {label}, WIA's own: {_rated(r[name]['wia'])}", f"- {label}, delegated: {_rated(r[name]['delegated'])}"]
    lines += ["", "Briefs",
              f"- Approved: {_split(b['approved'])}",
              f"- Approved without rewriting the central point: {_split(b['approved_without_rewriting_the_central_point'])}",
              f"- Of those, WIA's own on cards WIA chose: {b['approved_without_rewriting_the_central_point_on_cards_wia_chose']}", "",
              f"Gate 2 edits, by {e['categorised_by']}",
              f"- Edits: {_split(e['edits'])}"]
    for side, label in (("wia", "WIA's own"), ("delegated", "Delegated")):
        kinds = ", ".join(f"{k} {v}" for k, v in e["by_category"][side].items() if v) or "none"
        lines.append(f"- {label}: {kinds}")
    lines += [f"- First touch, insider term, fidelity: {e['check_kinds']}", "",
              "Packs",
              f"- Packs in the week: {p['packs']} ({p['finished']} finished)",
              f"- Marked ready: {_split(p['ready'])}",
              f"- Ready with light edits or none: {_split(p['ready_with_light_edits_or_none'])}",
              f"  Rule: {p['light_edits_rule']}",
              f"- Lines edited by a person: {_split(p['lines_edited_by_a_person'])}",
              f"- Pieces published: {_split(p['pieces_published'])}",
              "- Cost: " + (f"USD {p['cost']['total_usd']:.4f} over {p['cost']['model_calls']} model calls"
                            + (f", USD {p['cost']['per_pack_usd']:.4f} per finished pack" if p["cost"]["per_pack_usd"] is not None else "")
                            if p["cost"]["model_calls"] else "no model call recorded for the week's packs"), "",
              "Thresholds (WIA's own rows only)" + (f"; the Done column also reads {m['previous_week_id']}" if m["previous_week_id"] else "")]
    for row in m["thresholds"]:
        verdict = "not judged" if row["met"] is None else "met" if row["met"] else "not met"
        detail = ""
        if "this_week" in row:
            detail = f" (this week {'yes' if row['this_week'] else 'no'}, the week before " + (
                "none" if row["previous_week"] is None else "yes" if row["previous_week"] else "no") + ")"
        lines.append(f"- [{row['plan']}] {row['measure']}, {row['column']}: \"{row['threshold']}\": {verdict}{detail}"
                     + (f"; {row['note']}" if row.get("note") else ""))
    return "\n".join(lines) + "\n"


def run_cli(repo, week_id: str, as_json: bool) -> str:
    result = measures(repo, week_id)
    return json.dumps(result, indent=2, default=str) + "\n" if as_json else text(result)


# ---- editorial monitoring (6.B13) ---------------------------------------------------------------------------------------------

ACCEPTED_SHARE_BAR = 0.5  # section 4.5, row 1 (O28): at least half of a slate of at least four public cards
DECIDED_AT_LEAST = 4


def cards_decided(conn, week_id: str) -> int:
    """How many of the week's cards have a Gate 1 decision, whoever made it: Gate 1 counts as done from DECIDED_AT_LEAST."""
    return conn.execute("""SELECT count(DISTINCT d.item_id) n FROM decisions d JOIN content_angles a ON a.angle_id=d.item_id
        WHERE d.item_kind='angle' AND a.week_id=%s AND d.disposition IS NOT NULL""", (week_id,)).fetchone()["n"]


def accepted_share_condition(conn) -> dict | None:
    """The alert 6.B13 asks for: the accepted share (cards developed, or reframed keeping the point, over the slate) under
    the bar on the two latest weeks whose Gate 1 is done (at least DECIDED_AT_LEAST cards decided, whoever decided them), so
    a week still waiting for its decisions never counts as a low one. None when it holds or fewer than two weeks are judged."""
    weeks = conn.execute("""SELECT a.week_id,max(a.created_at) made FROM content_angles a JOIN weeks w USING (week_id)
        WHERE a.content_body ? 'card' AND w.status<>'archived' GROUP BY a.week_id ORDER BY made DESC LIMIT 6""").fetchall()
    judged = []
    for w in weeks:
        if cards_decided(conn, w["week_id"]) < DECIDED_AT_LEAST:
            continue
        result, _ = cards(conn, w["week_id"])
        if result["slate"]:
            judged.append((w["week_id"], result["developed_or_reframed_keeping_the_point"]["all"] / result["slate"], result["slate"]))
        if len(judged) == 2:
            break
    if len(judged) < 2 or any(share >= ACCEPTED_SHARE_BAR for _, share, _ in judged):
        return None
    words = " and ".join(f"{week} ({share:.0%} of {slate})" for week, share, slate in judged)
    return {"subject": judged[0][0], "details": {"weeks": [{"week_id": w, "share": round(s, 2), "slate": n} for w, s, n in judged],
                                               "bar": ACCEPTED_SHARE_BAR},
            "message": f"Fewer than half of the cards were developed or reframed keeping their point two weeks running: {words}. "
                       "Read the skip reasons at Gate 1 before the next cycle"}


def monitoring(repo, week_id: str) -> dict:
    """Editorial monitoring per cycle (6.B13), for the app: the week's measures with the accepted share, the reasons cards
    were skipped, the cards whose evidence check raised a flag, the knowledge-base version and the strategist profile the
    cycle ran on, and what the cycle cost. Read only; no model call."""
    result = measures(repo, week_id)
    with repo.connection() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        skips = [dict(r) for r in conn.execute("""SELECT d.reason_code,d.note,a.content_body->>'title' AS title FROM decisions d
            JOIN content_angles a ON a.angle_id=d.item_id WHERE d.item_kind='angle' AND a.week_id=%s AND d.disposition IN ('skip','reject')
            ORDER BY d.created_at""", (week_id,)).fetchall()]
        flagged = conn.execute("""SELECT count(*) n FROM content_angles WHERE week_id=%s AND content_body ? 'card'
            AND jsonb_typeof(content_body->'card'->'verification'->'findings')='array'
            AND jsonb_array_length(content_body->'card'->'verification'->'findings')>0""", (week_id,)).fetchone()["n"]
        run = conn.execute("""SELECT run_id,input_refs->'settings_snapshot'->>'knowledge_base_version' AS kb,
            input_refs->>'angle_prompt_profile' AS profile,input_refs->>'started_from' AS started_from FROM pipeline_runs
            WHERE week_id=%s AND run_scope='weekly_angles' ORDER BY created_at DESC LIMIT 1""", (week_id,)).fetchone()
        cost = conn.execute("""SELECT coalesce(sum(cost_usd),0) usd,count(*) calls FROM llm_runs WHERE details->>'run_id'=%s""",
                            (run["run_id"] if run else None,)).fetchone()
        decided = cards_decided(conn, week_id)
    slate = result["cards"]["slate"]
    chose = result["cards"]["developed_or_reframed_keeping_the_point"]["all"]
    # The share is shown against the bar once Gate 1 is done, by the rule the low-share alert uses (accepted_share_condition).
    result["monitoring"] = {"accepted_share": round(chose / slate, 2) if slate else None, "bar": ACCEPTED_SHARE_BAR,
                            "cards_decided": decided, "decided_at_least": DECIDED_AT_LEAST,
                            "gate_1_done": bool(slate) and decided >= DECIDED_AT_LEAST,
                            "skip_reasons": skips, "cards_with_evidence_flags": flagged,
                            "cycle": {"run_id": run["run_id"] if run else None, "knowledge_base_version": run["kb"] if run else None,
                                      "strategist_profile": run["profile"] if run else None,
                                      "started_from": (run["started_from"] if run else None) or "app",
                                      "cost_usd": round(float(cost["usd"]), 4), "model_calls": cost["calls"]}}
    return result


def install(routes, repo, reader, action):
    from .api_models import WeekMeasures, returns

    @routes.get("/weeks/{week_id}/measures", responses=returns(WeekMeasures))
    def week_monitoring(week_id: str, subject: str = Depends(reader)):
        return action(monitoring, repo, week_id)
