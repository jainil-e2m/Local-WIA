"""The fidelity loop around the finisher (NP.B8; the content-packs plan, section 5.5): check, repair, re-check.

- **Check** (`pack_check`, Sonnet 5.5): every statement about the real event, the client, WIA's actions, a person's words, a
  result or a commitment, supported or not, and whether each quote sits in its own moment. Its sources are the brief's
  supported claims, the supporting example, the before-publishing items with their answers, the call's words, the attested
  facts, the offer descriptors and WIA's beliefs. Lines a person wrote and Whitney's personal lines are skipped.
- **Repair** (`pack_repair`, Opus 5.5): patches for the flagged sentences only, never a locked one. A patch whose old text
  is not found is dropped and recorded; locked lines are put back after.
- **Re-check** (`pack_recheck`): the changed statements only, plus the caption of a Reel whose script changed.

A model check is a net, not the gate: what survives goes to finalize (finalize.py), which puts the brief's sentence back in
a piece the brief had and leaves an open finding on a Reel the finisher wrote (R57).

**Round 2 (check v4, repair v2).** The check also reads the pack as an editor (WIA, 26 October: "a fact can be
source-grounded and still be the wrong fact to foreground"): what a prospect would infer, work WIA inherited, lead quality,
causation and generalisations, slogans and agency comparisons, repetition, premises that overlap, weak hooks and broad
lessons (`contracts_v2.EDITORIAL_ISSUES`), and how strong each piece is. Each note is a flag with the verdict `editorial`
and its issue; the repair works on them with the fidelity flags, and what survives becomes an editorial finding.
"""
from __future__ import annotations

import copy
import re

from ..briefs import paths
from . import contracts_v2 as c2
from . import text as T
from .finish import CLAIM_STATUSES, _at, restore

LIST_ITEM = re.compile(r"^(cover_alternates|screens|subject_options)\[(\d+)\]$")


def sources(handoff: dict, attested: list[str] | None = None, *, perspective: bool = False, said: dict | None = None) -> dict:
    """What a check or repair may rest on. `perspective` (pack-check.v3) adds the approved brief's WIA perspective and
    central point; `said` (the post-recording pass) the recorded take, {piece: words}. Without them the sources are exactly
    what an earlier profile sent, so its saved answers replay."""
    strategy = handoff.get("strategy") or {}
    extra = {}
    if perspective:
        extra["approved_perspective"] = {"wia_perspective": strategy.get("wia_perspective"),
                                         "central_point": strategy.get("central_point")}
    if said:
        extra["recorded_take"] = said
    return {**extra, "supported_claims": [c["text"] for c in handoff.get("claims") or [] if c.get("status") in CLAIM_STATUSES],
            "supporting_example": strategy.get("supporting_example"),
            "before_publishing": [{"text": n["text"], "kind": n.get("kind"), "answer": n.get("answer")}
                                  for n in handoff.get("before_publishing") or []],
            "evidence": [{"evidence_id": e["evidence_id"], "speaker": e.get("speaker"), "at": _at(e.get("start_ms")),
                          "call_date": (e.get("call_date") or "")[:10] or None, "quote": e.get("quote")}
                         for e in handoff.get("evidence") or []],
            "attested": [i["text"] for i in handoff.get("context") or [] if i.get("kind") == "attested_fact"] + list(attested or []),
            "offer_descriptors": handoff.get("offer_descriptors") or [], "beliefs": handoff.get("beliefs")}


def locked_leaf(p: dict, path: str) -> bool:
    return any(lock["path"] == "*" or paths.overlaps(lock["path"], path) for lock in p.get("locks") or [])


def view(pieces: dict, *, only: dict[str, set[str]] | None = None, keys=None) -> tuple[dict, list[dict]]:
    """The pack as the check reads it ({piece: {path: text}}), and what it must skip: lines a person wrote and personal
    lines. `only` limits it to some leaves (the re-check); `keys` to some pieces (missing_only checks written Reels)."""
    pack, skip = {}, []
    for key in keys or c2.PIECE_KEYS:
        p = pieces[key]
        if p["content"] is None:
            continue
        found = {}
        for path, text in T.leaves(p["channel"], p["content"]).items():
            if only is not None and path not in only.get(key, set()):
                continue
            if locked_leaf(p, path):
                skip.append({"piece": key, "text": text, "why": "written by a person"})
                continue
            found[path] = text
        for line in p["content"].get("personal_lines") or []:
            skip.append({"piece": key, "text": line, "why": "a personal line for Whitney to keep or cut"})
        if found:
            pack[key] = found
    return pack, skip


def premises_of(pieces: dict) -> dict:
    """Each Reel's premise, takeaway and why it differs (finisher v3), for the editorial reading of overlap."""
    out = {}
    for key in ("reel_1", "reel_2", "reel_3"):
        content = (pieces.get(key) or {}).get("content") or {}
        if content.get("premise"):
            out[key] = {k: content.get(k) for k in ("premise", "takeaway", "distinct_because", "production")}
    return out


def editorial_flags(notes: list[dict], pieces: dict, skip: list[dict]) -> list[dict]:
    """The editorial notes as flags (verdict `editorial`, with the issue and its severity), each placed in its leaf where its
    text is found there. A note on a person's line (or a personal line) is kept for the person as a warning: their line is
    theirs to change, and the repair never touches a locked line."""
    skipped = [T.norm(s["text"]) for s in skip]
    out = []
    for n in notes:
        target = T.norm(n["text"])
        theirs = any(target and (target in k or k in target) for k in skipped if k)
        p = pieces.get(n["piece"])
        if not p or p["content"] is None:
            continue
        path = T.locate(T.leaves(p["channel"], p["content"]), n["text"])
        out.append({"piece": n["piece"], "path": path, "text": n["text"], "verdict": "editorial", "issue": n["issue"],
                    "severity": "warning" if theirs else c2.EDITORIAL_ISSUES.get(n["issue"], "warning"),
                    "why": (n.get("why") or "") + (" (a line a person wrote: theirs to change)" if theirs else ""), "source": ""})
    return out


REPEAT_SPAN = 8


def repetition_flags(pieces: dict, skip: list[dict]) -> list[dict]:
    """Wording one piece repeats from a piece before it (eight or more words in a row, as the sibling-overlap check reads it),
    as editorial flags on the later piece's sentence, so the repair rewords it (Round 2, second pass: the pieces were
    retelling the story's facts in the same words). A person's line, a quotation, a sign-off and an offer's CTA are left."""
    from ..briefs.asset_checks import OFFER_CTA, SIGN_OFF, _spans
    skipped = {T.norm(s["text"]) for s in skip}
    seen: list[tuple[str, set]] = []
    out, done = [], set()
    for key in c2.PIECE_KEYS:
        p = pieces.get(key) or {}
        if p.get("content") is None:
            continue
        mine = []
        for path, text in T.leaves(p["channel"], p["content"]).items():
            if OFFER_CTA.search(text) or SIGN_OFF.search(text.strip()):
                continue
            for sentence in T.sentences(text):
                spans = _spans(sentence, REPEAT_SPAN)
                mine.append((path, sentence, spans))
                # A person's line is never flagged, but a later piece must not repeat it either (found on the re-test).
                if locked_leaf(p, path) or T.norm(sentence) in skipped:
                    continue
                for earlier, theirs in seen:
                    if spans & theirs and (key, path, sentence) not in done:
                        done.add((key, path, sentence))
                        out.append({"piece": key, "path": path, "text": sentence, "verdict": "editorial", "issue": "repetition",
                                    "severity": "warning", "source": "",
                                    "why": f"repeats a run of words from {c2.LABELS[earlier]}: say it in this piece's own words"})
                        break
        seen.append((key, set().union(*[s for _, _, s in mine]) if mine else set()))
    return out


def flagged(statements: list[dict], pieces: dict, skip: list[dict]) -> list[dict]:
    """The statements judged unsupported or guardrail, each placed in its leaf, with a quote moved out of its moment counted
    as unsupported; a statement inside a skipped line (a person's or a personal line) is dropped."""
    skipped = [T.norm(s["text"]) for s in skip]
    out = []
    for s in statements:
        verdict = s["verdict"]
        if verdict == "supported" and s.get("in_moment") is False:
            verdict = "unsupported"
        if verdict == "supported":
            continue
        target = T.norm(s["text"])
        if any(target and (target in k or k in target) for k in skipped if k):
            continue
        p = pieces.get(s["piece"])
        if not p or p["content"] is None:
            continue
        path = T.locate(T.leaves(p["channel"], p["content"]), s["text"])
        out.append({"piece": s["piece"], "path": path, "text": s["text"], "verdict": verdict,
                    "why": s.get("why") or ("A quote moved out of its moment" if s.get("in_moment") is False else ""),
                    "source": s.get("source") or ""})
    return out


def check(worker, job, run_row, pieces: dict, handoff: dict, *, stage: str = "pack_check", only=None, keys=None,
          attested=None, said: dict | None = None) -> dict:
    """One check call; {"statements", "flags", "skipped"} (no call when there is nothing to check)."""
    from .runtime_v2 import call, profiles
    pack, skip = view(pieces, only=only, keys=keys)
    if not pack:
        return {"statements": [], "flags": [], "skipped": len(skip), "called": False}
    profile = profiles(worker.storage)[stage]
    perspective = profile in c2.PERSPECTIVE_CHECKS
    packet = {"sources": sources(handoff, attested, perspective=perspective, said=said), "pack": pack, "skip": skip}
    if profile in c2.EDITORIAL_CHECKS:
        packet["premises"] = premises_of(pieces)
    output = call(worker, job, run_row, stage, packet)
    statements = [s.model_dump() for s in output.statements]
    flags = flagged(statements, pieces, skip)
    readings = []
    if hasattr(output, "editorial"):
        flags += editorial_flags([n.model_dump() for n in output.editorial], pieces, skip)
        readings = [r.model_dump() for r in output.pieces]
        if only is None:
            # A whole-pack check (not the re-check of patched lines) also hands the repair the wording pieces repeat.
            known = {(f["piece"], T.norm(f["text"])) for f in flags}
            flags += [f for f in repetition_flags(pieces, skip) if (f["piece"], T.norm(f["text"])) not in known]
    return {"statements": statements, "flags": flags, "readings": readings, "skipped": len(skip), "called": True}


def apply_patches(pieces: dict, patches: list[dict], flags: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    """The pieces with each patch applied to the leaf holding its old text (never a locked leaf, never a leaf no flag
    named); (pieces, applied, missed)."""
    out = copy.deepcopy(pieces)
    flagged_leaves = {(f["piece"], f["path"]) for f in flags}
    applied, missed = [], []
    for patch in patches:
        p = out.get(patch["piece"])
        done = False
        if p and p["content"] is not None:
            for path, text in T.leaves(p["channel"], p["content"]).items():
                if locked_leaf(p, path) or (patch["piece"], path) not in flagged_leaves and (patch["piece"], None) not in flagged_leaves:
                    continue
                new = T.replace_once(text, patch["old"], patch["new"])
                if new is None:
                    continue
                new = T.tidy(new)
                if not new:
                    # A patch that cuts a whole line of a list (a cover alternate, a b-roll screen, a subject option) removes
                    # it: an empty string left in the list failed the piece's contract at finalize (NP-7's shakedown). A
                    # required leaf is never emptied, and a screen or subject list keeps at least one line.
                    item = LIST_ITEM.match(path)
                    if not item:
                        continue
                    items = list(paths.get(p["content"], item.group(1)))
                    if len(items) <= 1 and item.group(1) != "cover_alternates":
                        continue
                    items.pop(int(item.group(2)))
                    p["content"] = paths.put(p["content"], item.group(1), items)
                    p["changes"].append({"path": path, "kind": "repaired", "before": text, "after": None,
                                         "note": "The repair cut this line; it is removed"})
                    applied.append({**patch, "path": path})
                    done = True
                    break
                p["content"] = paths.put(p["content"], path, new)
                p["changes"].append({"path": path, "kind": "repaired", "before": text, "after": new})
                applied.append({**patch, "path": path})
                done = True
                break
        if not done:
            missed.append(patch)
            if p is not None:
                p["changes"].append({"path": "*", "kind": "missed_patch", "before": patch["old"], "after": patch["new"],
                                     "note": "The repair's old text was not found in an unlocked flagged line; nothing changed"})
    for key in c2.PIECE_KEYS:
        p, base = out[key], pieces[key]
        if p["content"] is not None and base["content"] is not None:
            p["content"], restored = restore(base["content"], p["content"], p["locks"], p["channel"])
            p["changes"] += restored
    return out, applied, missed


def repair(worker, job, run_row, pieces: dict, handoff: dict, flags: list[dict], *, attested=None, said: dict | None = None) -> dict:
    """One repair call for the flagged, unlocked statements; {"pieces", "applied", "missed", "called"}."""
    from .runtime_v2 import call
    open_flags = [f for f in flags if not (f["path"] and locked_leaf(pieces[f["piece"]], f["path"]))]
    if not open_flags:
        return {"pieces": pieces, "applied": [], "missed": [], "called": False}
    pack, _ = view(pieces)
    locked = [{"piece": k, "text": t} for k in c2.PIECE_KEYS if pieces[k]["content"] is not None
              for path, t in T.leaves(pieces[k]["channel"], pieces[k]["content"]).items() if locked_leaf(pieces[k], path)]
    from .runtime_v2 import profiles
    packet = {"flagged": [{k: f[k] for k in ("piece", "text", "verdict", "why")} for f in open_flags],
              "sources": sources(handoff, attested, said=said), "pack": pack, "locked": locked}
    if profiles(worker.storage)["pack_repair"] in c2.EDITORIAL_REPAIRS:
        # Repair v2 (Round 2) sees each editorial note's issue, and the Reels' premises it may need to keep apart.
        packet["flagged"] = [{k: f[k] for k in ("piece", "text", "verdict", "why")} | ({"issue": f["issue"]} if f.get("issue") else {})
                             for f in open_flags]
        packet["premises"] = premises_of(pieces)
    output = call(worker, job, run_row, "pack_repair", packet)
    patched, applied, missed = apply_patches(pieces, [p.model_dump() for p in output.patches], open_flags)
    return {"pieces": patched, "applied": applied, "missed": missed, "called": True}


def changed_leaves(applied: list[dict], pieces: dict) -> dict[str, set[str]]:
    """What the re-check reads: each patched leaf, and the caption of a Reel whose script changed."""
    out: dict[str, set[str]] = {}
    for a in applied:
        out.setdefault(a["piece"], set()).add(a["path"])
        if a["path"] == "script" and pieces[a["piece"]]["content"].get("caption"):
            out[a["piece"]] |= {"caption.hook", "caption.body", "caption.ending"}
    return out
