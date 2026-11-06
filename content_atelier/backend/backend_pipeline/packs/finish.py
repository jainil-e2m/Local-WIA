"""The finisher (NP.B7; the content-packs plan, section 5.4): Opus 5.5 edits the approved brief's copy to WIA's house style
and writes a missing Reel kind, inside the fidelity loop that follows it (fidelity.py).

- **Inputs** are hand-off view v2 only (R56): each piece's copy, the anchor, the message spine, the CTA decision, the
  strategy, the checked claims, the before-publishing items with their answers, the call's words with consent and call
  dates, the attested facts and the offer descriptors; and the lines a person wrote, shown as LOCKED.
- **The packet holds no identifiers that differ between copies of the data** (brief, claim, run or pack ids, timestamps,
  authors), so the same approved brief gives the same request in any database, and a saved response replays (NP-6).
- **After the call** every locked line is put back (`restore`) and recorded; a carousel the model re-split or renumbered
  around a locked slide keeps the brief's carousel, recorded, instead of failing the job.
- **Modes**: `finish` edits every piece; `missing_only` keeps every existing piece verbatim and takes only the missing
  Reels from the answer; `assemble` makes no call (the stage passes the draft through).
- **Round 2 (finisher v3, `draft["premises"]`)**: two calls in the step. The plan (pack-plan.v1) sets each Reel's premise,
  how it is made, its takeaway, why it differs and its times, and weighs two to four openings for every piece; the writing
  call then writes the pack to that plan (the writing answer is at the provider's grammar limit, so it stays v2's size).
  The Reels come back as the central story and two premises of their own; the openings weighed are kept on the pack
  (`creative_choices`).
"""
from __future__ import annotations

import copy

from ..briefs import paths
from . import contracts_v2 as c2
from . import text as T

TASK = {"finish": "Finish every piece (mode finish): refine, don't replace; write any missing Reel kind.",
        "missing_only": "Copy every existing piece exactly; write only the pieces marked missing (mode missing_only).",
        "refinish": "Finish every piece again with the granted items as evidence (mode refinish): use each one where it makes "
                    "the copy stronger, keep every locked line, change nothing else that does not need it."}
CLAIM_STATUSES = ("supported", "bound", "kept_by_person", "attested")


def _at(ms) -> str | None:
    if ms is None:
        return None
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}"


def packet(draft: dict, handoff: dict, mode: str, *, granted: list[dict] | None = None) -> dict:
    """The finisher's user message (deterministic for the same approved brief and pack). `granted` (NP.B15's refinish) adds
    the granted items; a finish without them sends exactly what it sent before."""
    strategy = handoff.get("strategy") or {}
    pieces = {}
    premises = bool(draft.get("premises"))
    for key in c2.PIECE_KEYS:
        p = draft["pieces"][key]
        if p["content"] is None:
            pieces[key] = {"missing": True, "kind": (c2.KEY_PREMISE if premises else c2.KEY_KIND).get(key), "label": c2.LABELS[key]}
        else:
            # A Reel's working title, cover alternates and no-offer ending are the finisher's to write; the carousel's
            # title is copy and stays.
            extras = ("cover_alternates", "no_offer_ending", "title") if p["channel"] == "reel" else ("no_offer_ending",)
            pieces[key] = {"label": c2.LABELS[key], **{k: v for k, v in p["content"].items() if k not in extras}}
    by_brief = {p["key"]: p for p in handoff.get("pieces") or []}
    # A source is a brief Reel's key, or (finishing an earlier pack again under finisher v3) the copy of a Reel that retold the
    # central story, which the finisher replaces with a premise of its own.
    source_material = {target: [k["retold"] if isinstance(k, dict) else by_brief[k]["copy"] for k in keys
                                if isinstance(k, dict) or k in by_brief] for target, keys in draft["sources"].items()}
    locked = [{"piece": key, "path": lock["path"], "value": (draft["pieces"][key]["content"] if lock["path"] == "*"
                                                             else paths.get(draft["pieces"][key]["content"], lock["path"]))}
              for key in c2.PIECE_KEYS for lock in draft["pieces"][key]["locks"]
              if draft["pieces"][key]["content"] is not None and (lock["path"] == "*" or paths.exists(draft["pieces"][key]["content"], lock["path"]))]
    places = {"email": "email", "carousel": "carousel"}
    places.update({bk: pk for bk, pk in draft["brief_map"].items()})
    claims = [{"text": c["text"], "status": c["status"], "piece": places.get(c.get("piece")) if c.get("piece") else None,
               "where": c.get("leaf") or c.get("path") or c.get("field"), "quote": c.get("quote")}
              for c in handoff.get("claims") or [] if c.get("status") in CLAIM_STATUSES]
    evidence = [{"speaker": e.get("speaker"), "at": _at(e.get("start_ms")), "call_date": (e.get("call_date") or "")[:10] or None,
                 "quote": e.get("quote"), "consent": e.get("client_consent"), "quotable": bool(e.get("quotable", True))}
                for e in handoff.get("evidence") or []]
    attested = [i["text"] for i in handoff.get("context") or [] if i.get("kind") == "attested_fact"] + list(draft.get("attested") or [])
    return {"mode": mode, "task": TASK[mode],
            "brief": {"title": handoff.get("title"), "central_point": strategy.get("central_point"),
                      "message_spine": (handoff.get("message_spine") or {}).get("text"),
                      "wia_perspective": strategy.get("wia_perspective"), "audience": strategy.get("audience"),
                      "strategic_purpose": strategy.get("strategic_purpose"), "intended_shift": strategy.get("intended_shift"),
                      "supporting_example": strategy.get("supporting_example"), "narrative_outline": strategy.get("narrative_outline"),
                      "point_of_view": strategy.get("point_of_view"), "cta": {k: v for k, v in (handoff.get("cta") or {}).items()
                                                                              if k != "chosen_by"},
                      "cta_why": strategy.get("cta_why"), "anchor": draft["anchor"]},
            "pieces": pieces, "source_material": source_material, "locked": locked, "claims": claims, "evidence": evidence,
            "attested": attested,
            "before_publishing": [{"id": n["id"], "text": n["text"], "kind": n["kind"], "answer": n.get("answer")}
                                  for n in draft["body"]["before_publishing"]],
            "offer_descriptors": handoff.get("offer_descriptors") or [], **({"granted": granted} if granted is not None else {})}


def _reel(base: dict | None, r, planned=None) -> dict:
    out = copy.deepcopy(base) if base else {"source": "new_script"}
    if planned is not None:
        # How it is made follows what was written (a script, or screens); the premise and the rest come from the plan.
        production = "on_screen_text" if r.screens and not (r.script or "").strip() else "face_to_camera"
        out.update({"production": production, "premise": planned.premise, "takeaway": planned.takeaway,
                    "distinct_because": planned.distinct_because, "timestamps": list(planned.timestamps)})
        text = production == "on_screen_text"
    else:
        text = r.kind == "broll_text"
    out.update({"kind": r.kind, "job": r.job, "register": "on_screen" if text else "spoken", "title": r.title,
                "cover_text": r.cover_text, "cover_alternates": list(r.cover_alternates), "on_screen_hook": r.on_screen_hook,
                "spoken_opening": None if text else r.spoken_opening,
                "script": None if text else r.script,
                "screens": list(r.screens or []) if text else None, "beats": list(r.beats),
                "personal_lines": list(r.personal_lines), "read_time_seconds": r.read_time_seconds,
                "caption": r.caption.model_dump(), "offer_descriptor": r.offer_descriptor, "cta": r.cta,
                "no_offer_ending": r.no_offer_ending if r.cta == "offer" else None})
    out.setdefault("source", "new_script")
    return out


def _carousel(base: dict, c: c2.FinishCarousel) -> dict:
    jobs = {s["number"]: s.get("job") or "" for s in base.get("slides") or []}
    out = copy.deepcopy(base)
    out.update({"title": c.title, "slides": [{"number": s.number, "job": jobs.get(s.number, ""), "text": s.text} for s in c.slides],
                "caption": c.caption.model_dump(), "offer_descriptor": c.offer_descriptor, "cta": c.cta,
                "no_offer_ending": c.no_offer_ending if c.cta == "offer" else None})
    return out


def _email(base: dict, e: c2.FinishEmail) -> dict:
    out = copy.deepcopy(base)
    out.update({"subject_options": list(e.subject_options), "preview": e.preview, "opening": e.opening, "body": e.body,
                "ending": e.ending, "offer_descriptor": e.offer_descriptor, "cta": e.cta})
    return out


def restore(base: dict | None, new: dict, locks: list[dict], channel: str) -> tuple[dict, list[dict]]:
    """`new` with every locked line put back from `base`, and a record of each line the model had changed. A lock on the
    whole piece ("*") keeps `base` whole. A carousel the model re-split or renumbered around a locked slide keeps `base`'s
    carousel whole, recorded (section 5.4)."""
    if base is None or not locks:
        return new, []
    keep = [lock["path"] for lock in locks]
    if "*" in keep:
        return copy.deepcopy(base), ([{"path": "*", "kind": "restored_lock", "note": "The whole piece was written by a person"}]
                                     if new != base else [])
    if channel == "carousel" and any(p.startswith("slides[") for p in keep):
        try:
            paths.restore(base, new, [p for p in keep if p.startswith("slides[")])
        except ValueError:
            return copy.deepcopy(base), [{"path": "slides", "kind": "kept_brief_carousel",
                                          "note": "The model re-split or renumbered a carousel with a locked slide; the "
                                                  "approved carousel is kept"}]
    out, changes = new, []
    for p in sorted(set(keep)):
        if not paths.exists(base, p):
            continue
        if not paths.exists(out, p):
            if channel == "carousel":
                return copy.deepcopy(base), [{"path": "slides", "kind": "kept_brief_carousel",
                                              "note": f"The model removed the locked line {p}; the approved carousel is kept"}]
            continue
        if paths.get(out, p) != paths.get(base, p):
            changes.append({"path": p, "kind": "restored_lock", "before": _str(paths.get(out, p)), "after": _str(paths.get(base, p))})
            out = paths.put(out, p, paths.get(base, p))
    return out, changes


def _str(value) -> str | None:
    return value if isinstance(value, str) or value is None else str(value)


def leaf_changes(channel: str, before: dict | None, after: dict, kind: str) -> list[dict]:
    old, new = T.leaves(channel, before), T.leaves(channel, after)
    return [{"path": p, "kind": kind, "before": old.get(p), "after": v} for p, v in new.items() if old.get(p) != v] + [
        {"path": p, "kind": kind, "before": v, "after": None} for p, v in old.items() if p not in new]


def quotes(output: c2.FinishOutput, handoff: dict) -> list[dict]:
    """The client quotes the finisher used, each tied to its evidence item where the words match, for the client's okay."""
    evidence = [(e["evidence_id"], T.norm_quote(e.get("quote") or "")) for e in handoff.get("evidence") or []]
    out, seen = [], set()
    for q in output.client_quotes:
        key = (q.piece, T.norm_quote(q.quote))
        if key in seen:
            continue
        seen.add(key)
        found = next((eid for eid, text in evidence if key[1] and (key[1] in text or text and text in key[1])), None)
        out.append({"quote_id": f"Q{len(out) + 1}", "piece": q.piece, "quote": q.quote, "speaker": q.speaker,
                    "evidence_id": found, "cleared": None})
    return out


def choices(plan: c2.PlanOutput) -> list[dict]:
    """The openings the plan weighed for each piece, as the pack keeps them (`creative_choices`)."""
    out = [{"piece": o.piece, "considered": list(o.openings), "chosen": o.opening, "why": o.why} for o in plan.openings]
    out += [{"piece": c2.KIND_KEY[r.kind], "considered": list(r.openings), "chosen": r.opening, "why": r.why} for r in plan.reels]
    order = {k: i for i, k in enumerate(c2.PIECE_KEYS)}
    return sorted(out, key=lambda c: order[c["piece"]])


def apply(draft: dict, output: c2.FinishOutput, mode: str, handoff: dict, plan: c2.PlanOutput | None = None,
          found: dict | None = None) -> dict:
    """The finished pack: {"pieces", "body"} from the draft and the finisher's answer, locks restored, changes recorded.
    `plan` (finisher v3) gives each Reel its premise, takeaway, why it differs and its times, and the openings weighed."""
    pieces = copy.deepcopy(draft["pieces"])
    reels = {c2.KIND_KEY[r.kind]: r for r in output.reels}
    planned = {c2.KIND_KEY[r.kind]: r for r in plan.reels} if plan else {}
    proposed = {"email": lambda base: _email(base, output.email), "carousel": lambda base: _carousel(base, output.carousel)}
    for key in c2.PIECE_KEYS:
        p = pieces[key]
        base = p["content"]
        verbatim = key in draft.get("keep_verbatim", []) or (mode == "missing_only" and base is not None)
        if verbatim:
            continue
        if key.startswith("reel_"):
            new = _reel(base, reels[key], planned.get(key) if plan else None)
        elif base is None:
            continue  # a brief without a carousel or an email: nothing to finish (composition blocks Ready)
        else:
            new = proposed[key](base)
        new, restored = restore(base, new, p["locks"], p["channel"])
        if base is None:
            reason = (f"the earlier {c2.LABELS[key]} retold the central story, so it has a premise of its own"
                      if "retells" in (p.get("not_written_reason") or "") or "retold" in (p.get("not_written_reason") or "")
                      else f"the brief had no {c2.KIND_LABELS.get(new['kind'], new['kind'])} Reel")
            p.update(origin="written", content=new, not_written_reason=None,
                     changes=[{"path": "*", "kind": "written", "note": f"Written by the finisher: {reason}"}])
        else:
            changes = leaf_changes(p["channel"], p["brief_copy"] or base, new, "finished")
            # A Reel the finisher wrote stays "written" when finished again: no one approved it at Gate 2 (NP.X3).
            finished = "finished" if changes and p["origin"] != "written" else p["origin"]
            p.update(content=new, origin=finished, changes=restored + changes)
    body = copy.deepcopy(draft["body"])
    body.update(client_quotes=quotes(output, handoff) or body.get("client_quotes") or [],
                stronger_with_permission=list(output.stronger_with_permission),
                pack_notes=list(output.pack_notes), change_notes=list(output.change_notes))
    if plan is not None:
        body["creative_choices"] = choices(plan)
    if found:
        body["premise_material"] = found
    return {"pieces": pieces, "body": body}


def run(worker, job, run_row, draft: dict, handoff: dict, *, stage: str = "pack_finish") -> dict:
    """The pack_finish stage: one call (with its one repair) in finish or missing_only mode; none in assemble mode.
    `pack_refinish` (NP.B15) is the same call in finish mode with the granted items as evidence."""
    from .runtime_v2 import call
    mode = draft["finish_mode"]
    if stage == "pack_refinish":
        from .passes import granted_items
        sent = packet(draft, handoff, "refinish", granted=granted_items(draft["body"]))
        plan = _plan(worker, job, run_row, draft, sent)
        found = _material(draft, plan)
        output = call(worker, job, run_row, stage, _with_plan(sent, plan, found))
        return {**apply(draft, output, "finish", handoff, plan, found), "called": True, "extra_evidence": _evidence(found)}
    if mode == "assemble" or (mode == "missing_only" and not draft["missing"]):
        return {"pieces": draft["pieces"], "body": draft["body"], "called": False}
    sent = packet(draft, handoff, mode)
    plan = _plan(worker, job, run_row, draft, sent)
    found = _material(draft, plan)
    output = call(worker, job, run_row, "pack_finish", _with_plan(sent, plan, found))
    return {**apply(draft, output, mode, handoff, plan, found), "called": True, "extra_evidence": _evidence(found)}


def _plan(worker, job, run_row, draft: dict, sent: dict):
    """Finisher v3's first call (Round 2): the plan, from the same packet the writing call reads; None before v3."""
    if not draft.get("premises"):
        return None
    from .runtime_v2 import call, profiles
    planner = profiles(worker.storage).get("pack_plan") or c2.PLAN_PROFILE
    if draft.get("call"):
        # Finisher v4's plan reads the card's whole call (packs/call.py), one line a turn, in place of the brief's claims and
        # evidence, which the call contains; the request stays inside briefs.max_characters.
        from .call import lines
        sent = {**{k: v for k, v in sent.items() if k not in ("claims", "evidence")}, "call": lines(draft["call"])}
    return call(worker, job, run_row, "pack_finish", sent, profile=planner)


def _material(draft: dict, plan) -> dict:
    """The call's turns behind Reels 2 and 3 (finisher v4), or {}."""
    if plan is None or not draft.get("call"):
        return {}
    from .call import material
    return material(draft["call"], plan)


def _evidence(found: dict) -> list[dict]:
    from .call import as_evidence
    return as_evidence(found) if found else []


def _with_plan(sent: dict, plan, found: dict | None = None) -> dict:
    if plan is None:
        return sent
    return {**sent, "plan": plan.model_dump(mode="json"), **({"premise_material": found} if found else {})}
