"""The pack's last stage, with no model call (NP.B8; the content-packs plan, section 5.5): what survives the fidelity loop,
the record, the deterministic checks, the version.

- **A flag that survives in a piece the brief had**: the flagged sentence goes back to the brief's corresponding sentence (a
  patch from the pack's sentence to the brief's), falling back to the whole leaf. When the brief's sentence would repeat a
  sentence beside it (the finisher split it in two and only one half was flagged), the brief's paragraph goes back in
  place of the pack's. A line the brief never had (a cover alternate, a no-offer ending) is removed. Recorded as
  `put_back`.
- **A flag that survives in a Reel the finisher wrote** stays an open finding on its sentence. It blocks Ready until a
  person edits that sentence or attests it is true (R57).
- **An editorial note that survives** (check v4, Round 2) stays an open editorial finding wherever it is: one that could
  misrepresent WIA, a client or a result blocks Ready until a person edits the line or keeps it with a reason; a craft
  note is a warning.
- Then every locked line is put back once more, the deterministic checks run (packs/checks.py), and the run's pack row is
  filled (`model.write_version(..., reuse_row=True)`), in review.
"""
from __future__ import annotations

import copy

from ..briefs import paths
from ..store import canonical_hash
from . import contracts_v2 as c2
from . import text as T
from .finish import restore

SYSTEM_ACTOR = "content-pack step"
PUT_BACK_SIMILARITY = 0.35


def put_back(p: dict, flag: dict) -> dict | None:
    """Put the brief's sentence back for one surviving flag in a piece the brief had; the change made, or None."""
    path = flag.get("path")
    if not path or p["content"] is None or not paths.exists(p["content"], path):
        return None
    current = paths.get(p["content"], path)
    brief = p.get("brief_copy") or {}
    if not paths.exists(brief, path):
        # A line the brief never had: an optional line is removed; a required one keeps its piece's own fallback.
        if path.startswith(("cover_alternates", "screens")) or path == "no_offer_ending":
            parent, _, _ = path.rpartition("[") if path.endswith("]") else (None, None, None)
            if parent:
                items = list(paths.get(p["content"], parent))
                items.remove(current)
                p["content"] = paths.put(p["content"], parent, items)
            else:
                p["content"] = paths.put(p["content"], path, None)
            return {"path": path, "kind": "put_back", "before": current, "after": None,
                    "note": "A line the brief never had was flagged by the fidelity check and removed"}
        return None
    original = paths.get(brief, path)
    sentence = T.sentence_in(current, flag["text"])
    replacement, score = T.most_similar(sentence or flag["text"], original)
    if sentence and replacement and score >= PUT_BACK_SIMILARITY and len(T.sentences(current)) > 1:
        new = T.replace_once(current, sentence, replacement)
        if new is not None:
            beside = [s for s in T.sentences(T.paragraph_of(new, replacement) or "") if T.norm(s) != T.norm(replacement)]
            ours, theirs = T.paragraph_of(current, sentence), T.paragraph_of(original, replacement)
            # The paid proof (NP.X3): a brief sentence the finisher had split in two came back beside its other half.
            if T.repeats(replacement, beside) and ours and theirs:
                whole = T.replace_once(current, ours, theirs)
                if whole is not None:
                    p["content"] = paths.put(p["content"], path, whole)
                    return {"path": path, "kind": "put_back", "before": ours, "after": theirs,
                            "note": "The fidelity check's flag survived the repair; the brief's sentence would repeat the "
                                    "one beside it, so the brief's paragraph is put back"}
            p["content"] = paths.put(p["content"], path, new)
            return {"path": path, "kind": "put_back", "before": sentence, "after": replacement,
                    "note": "The fidelity check's flag survived the repair; the brief's sentence is put back"}
    p["content"] = paths.put(p["content"], path, original)
    return {"path": path, "kind": "put_back", "before": current, "after": original,
            "note": "The fidelity check's flag survived the repair; the brief's line is put back"}


def finding(key: str, flag: dict) -> dict:
    if flag["verdict"] == "editorial":
        # Round 2 (check v4): an editorial note the repair did not settle. It is never put back to the brief's line (the
        # brief's line may be where it came from); a person edits it, or keeps it with a reason.
        return {"finding_id": "edi_" + canonical_hash([key, flag.get("path"), flag["text"], flag.get("issue")])[:20],
                "kind": "editorial", "verdict": "editorial", "issue": flag.get("issue"), "path": flag.get("path"),
                "sentence": flag["text"], "why": flag.get("why") or "The editorial reading flagged this line",
                "severity": flag.get("severity") or "warning", "status": "open", "resolution": None}
    return {"finding_id": "fid_" + canonical_hash([key, flag.get("path"), flag["text"]])[:20], "kind": "fidelity",
            "verdict": flag["verdict"], "path": flag.get("path"), "sentence": flag["text"],
            "why": flag.get("why") or "The fidelity check could not find support for this sentence",
            "severity": "blocking", "status": "open", "resolution": None}


def settle(pieces: dict, survivors: list[dict], *, open_keys=()) -> tuple[dict, list[dict]]:
    """The pieces after the surviving flags are settled; (pieces, what was done with each). A flag in one of `open_keys`
    (the Reel of a post-recording pass, whose caption the brief never wrote for this script) stays an open finding."""
    out = copy.deepcopy(pieces)
    _drop_empty_lines(out)
    record = []
    for flag in survivors:
        p = out.get(flag["piece"])
        if not p or p["content"] is None:
            continue
        if p["origin"] == "written" or not p.get("brief_copy") or flag["piece"] in open_keys or flag["verdict"] == "editorial":
            f = finding(flag["piece"], flag)
            if f["finding_id"] not in {x["finding_id"] for x in p["findings"]}:
                p["findings"].append(f)
            record.append({**flag, "outcome": "open_finding"})
            continue
        change = put_back(p, flag)
        if change:
            p["changes"].append(change)
            record.append({**flag, "outcome": "put_back"})
        else:
            p["findings"].append(finding(flag["piece"], flag))
            record.append({**flag, "outcome": "open_finding"})
    for key in c2.PIECE_KEYS:
        p = out[key]
        base = p.get("brief_copy") if p["origin"] != "written" else None
        if p["content"] is not None and base is not None:
            p["content"], restored = restore(_locked_base(pieces[key], base), p["content"], p["locks"], p["channel"])
            p["changes"] += restored
    return out, record


def _drop_empty_lines(pieces: dict) -> None:
    """An empty line in a list (a cover alternate, a b-roll screen, a subject option) is removed, as the repair now does, so
    a run saved before that fix still finalizes on a retry (NP-7's shakedown). A list keeps at least one line."""
    for p in pieces.values():
        content = p.get("content")
        if not content:
            continue
        for leaf in ("cover_alternates", "screens", "subject_options"):
            items = content.get(leaf)
            if isinstance(items, list) and any(not (x or "").strip() for x in items):
                kept = [x for x in items if (x or "").strip()]
                content[leaf] = kept if kept or leaf == "cover_alternates" else items[:1]


def _locked_base(piece_before: dict, brief_copy: dict) -> dict:
    """The values locked lines must hold: the piece as the finisher left it (whose locked lines were already restored)."""
    return piece_before["content"] or brief_copy


def body_for(state: dict, run_row: dict, handoff: dict, worker) -> dict:
    from . import runtime_v2
    refs = run_row["input_refs"]
    contract = refs.get("execution_contract") or {}
    body = copy.deepcopy(state["body"])
    body["fidelity"] = state["fidelity"]
    body["change"] = {"kind": "finish_again" if refs.get("supersedes") else "generated", "by": SYSTEM_ACTOR,
                      "at": run_row["created_at"].isoformat() if hasattr(run_row.get("created_at"), "isoformat") else str(run_row.get("created_at")),
                      "delegated": False, "pieces": [], "paths": [], "note": None}
    if refs.get("pass"):
        from .passes import change_record
        body["change"] = change_record(refs["pass"])
    body["provenance"] = {"brief_id": refs["brief"]["brief_id"], "approved_hash": refs["brief"]["approved_hash"],
                          "brief_schema": refs["brief"].get("schema_version") or "brief_document_v4",
                          "handoff_version": c2.HANDOFF_VERSION, "run_id": run_row["run_id"], "mode": refs["mode"],
                          "finish_mode": state["finish_mode"], "profiles": contract.get("profiles") or runtime_v2.profiles(worker.storage),
                          "models": {"writer": contract.get("writer"), "reviewer": contract.get("reviewer")},
                          "knowledge_base_version": (contract.get("knowledge_base") or {}).get("version"),
                          "approved_by": handoff.get("approved_by"), "approval_delegated": bool(refs.get("approval_delegated"))}
    return body


def deterministic(conn, pack_row: dict, pieces: dict, brief_row: dict) -> dict | None:
    """The deterministic pack checks (NP.B4, packs/checks.py), stored with the version."""
    from . import checks
    found = checks.findings(conn, pack_row, pieces, brief_row)
    return {"findings": found, "blocking": sum(f["severity"] == "blocking" for f in found)}
