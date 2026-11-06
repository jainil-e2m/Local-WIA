"""NP-7's two person-started passes on a finished pack (the content-packs plan, section 4.5 and NP-7). Each is a new run that
supersedes the pack, with its own writer step in the finisher's place and the same fidelity loop after it.

- **The post-recording pass** (NP.B14, `pack_caption`; RQ18). A person pastes what Whitney said on a face-to-camera Reel's
  recorded take. It becomes the Reel's script word for word, locked as that person's line, and its first sentence the
  spoken opening; then Opus 5.5 writes the Reel's caption and three cover options from what was said and the brief's
  claims. The check reads the caption and covers only (the take is a person's line), with the take among its sources, and
  a flag that survives the repair stays an open finding on its sentence: the brief's caption was written for another script,
  so it is never put back.
- **Finishing again with a permission** (NP.B15, `pack_refinish`). A person grants a "stronger with permission" item or
  states a fact. The finisher runs again with each one as evidence, attested with the person and date (R57), every
  person's line kept; the check counts them as supported. The grants are kept on the pack (`granted`), so a later Finish
  again keeps them.

Neither is feedback refresh: each takes a person's own words, never a new instruction (section 4.5).
"""
from __future__ import annotations

import copy
import re

from ..briefs import paths
from . import contracts_v2 as c2
from .finish import CLAIM_STATUSES, _at

# The leaves the post-recording pass writes, and so the only ones its check reads.
CAPTION_LEAVES = ("cover_text", "cover_alternates[0]", "cover_alternates[1]", "caption.hook", "caption.body", "caption.ending",
                  "no_offer_ending")
SPOKEN = ("reel_1", "reel_2")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def first_sentence(text: str) -> str:
    return _SENTENCE.split(text.strip(), maxsplit=1)[0].strip()


def _lock(path: str, pass_: dict) -> dict:
    return c2.Lock(path=path, author=pass_["by"], delegated=bool(pass_.get("delegated")), at=pass_.get("at"),
                   origin="pack").model_dump(mode="json")


def prepare(draft: dict, pass_: dict) -> dict:
    """The draft a pass starts from (Finish again's draft of the current pack), with the pass's own input applied."""
    out = copy.deepcopy(draft)
    if pass_["kind"] == "caption":
        key = pass_["piece"]
        p = out["pieces"][key]
        if p["content"] is None or key not in SPOKEN:
            raise ValueError("The post-recording pass works on a face-to-camera Reel with copy")
        said = pass_["said"].strip()
        before = {"script": p["content"].get("script"), "spoken_opening": p["content"].get("spoken_opening")}
        p["content"] = {**p["content"], "script": said, "spoken_opening": first_sentence(said)}
        keep = [lock for lock in p["locks"] if lock["path"] not in ("script", "spoken_opening")]
        p["locks"] = keep + [_lock("script", pass_), _lock("spoken_opening", pass_)]
        p["changes"] = [{"path": path, "kind": "recorded", "before": before[path], "after": p["content"][path],
                         "note": "What Whitney said on the recorded take, word for word"} for path in ("script", "spoken_opening")
                        if before[path] != p["content"][path]]
        # Kept on the pack, so a later run's check reads the caption against what was said (found by NP-7's shakedown).
        out["body"] = {**out["body"], "recorded_takes": {**(out["body"].get("recorded_takes") or {}), key: said}}
    else:
        grants = list(pass_.get("grants") or [])
        out["attested"] = list(out.get("attested") or []) + [g["statement"] for g in grants]
        out["body"] = {**out["body"], "granted": [*(out["body"].get("granted") or []), *grants]}
    return out


def granted_items(body: dict) -> list[dict]:
    """The grants as the finisher reads them: the item granted (when one was) and the person's words."""
    return [{"item": g.get("item"), "statement": g["statement"]} for g in body.get("granted") or []]


def caption_packet(draft: dict, handoff: dict, key: str) -> dict:
    """The post-recording pass's user message (deterministic for the same pack and take)."""
    strategy = handoff.get("strategy") or {}
    reel = draft["pieces"][key]["content"]
    locked = [lock["path"] for lock in draft["pieces"][key]["locks"] if lock["path"] in CAPTION_LEAVES or lock["path"] == "caption"]
    return {"task": "Write this Reel's caption and three cover options from what Whitney said on the recorded take.",
            "reel": {"kind": reel.get("kind"), "label": c2.LABELS[key], "job": reel.get("job"), "said": reel.get("script"),
                     "on_screen_hook": reel.get("on_screen_hook"), "current_cover": reel.get("cover_text"),
                     "current_caption": reel.get("caption"), "cta": reel.get("cta"), "offer_descriptor": reel.get("offer_descriptor"),
                     "locked": [{"path": p, "value": paths.get(reel, p)} for p in locked if paths.exists(reel, p)]},
            "brief": {"title": handoff.get("title"), "central_point": strategy.get("central_point"),
                      "message_spine": (handoff.get("message_spine") or {}).get("text"),
                      "wia_perspective": strategy.get("wia_perspective"), "audience": strategy.get("audience"),
                      "supporting_example": strategy.get("supporting_example"),
                      "cta": {k: v for k, v in (handoff.get("cta") or {}).items() if k != "chosen_by"}},
            "claims": [c["text"] for c in handoff.get("claims") or [] if c.get("status") in CLAIM_STATUSES],
            "evidence": [{"speaker": e.get("speaker"), "at": _at(e.get("start_ms")), "quote": e.get("quote"),
                          "consent": e.get("client_consent")} for e in handoff.get("evidence") or []],
            "attested": [i["text"] for i in handoff.get("context") or [] if i.get("kind") == "attested_fact"] + list(draft.get("attested") or []),
            "before_publishing": [{"id": n["id"], "text": n["text"], "kind": n["kind"], "answer": n.get("answer")}
                                  for n in draft["body"]["before_publishing"]],
            "offer_descriptors": handoff.get("offer_descriptors") or []}


def apply_caption(draft: dict, output: c2.CaptionOutput, key: str) -> dict:
    """The pieces with the Reel's caption and covers written, every locked line kept, each change recorded."""
    from .finish import restore
    pieces = copy.deepcopy(draft["pieces"])
    p = pieces[key]
    base = p["content"]
    new = {**base, "cover_text": output.cover_text, "cover_alternates": list(output.cover_alternates),
           "caption": output.caption.model_dump(), "no_offer_ending": output.no_offer_ending if base.get("cta") == "offer" else None}
    new, restored = restore(base, new, p["locks"], p["channel"])
    changes = [{"path": path, "kind": "captioned", "before": _text(paths.get(base, path) if paths.exists(base, path) else None),
                "after": _text(paths.get(new, path) if paths.exists(new, path) else None),
                "note": "Written from what was said on the recorded take"}
               for path in CAPTION_LEAVES
               if (paths.get(base, path) if paths.exists(base, path) else None) != (paths.get(new, path) if paths.exists(new, path) else None)]
    p.update(content=new, changes=[*p["changes"], *restored, *changes])
    return pieces


def _text(value) -> str | None:
    return value if isinstance(value, str) or value is None else str(value)


def check_only(key: str) -> dict[str, list[str]]:
    """What the post-recording pass's check reads: the leaves it wrote."""
    return {key: list(CAPTION_LEAVES)}


def run_caption(worker, job, run_row, draft: dict, handoff: dict, key: str) -> dict:
    """The pack_caption stage: one call (with its one repair)."""
    from .runtime_v2 import call
    output = call(worker, job, run_row, "pack_caption", caption_packet(draft, handoff, key))
    body = copy.deepcopy(draft["body"])
    body["pack_notes"] = [*(body.get("pack_notes") or []), *(f"{c2.LABELS[key]}: {n}" for n in output.notes)]
    return {"pieces": apply_caption(draft, output, key), "body": body, "called": True}


def change_record(pass_: dict) -> dict:
    """The version's change record for a pass: started by the person, made by the content-pack step."""
    if pass_["kind"] == "caption":
        return {"kind": "recorded_take", "by": pass_["by"], "at": pass_["at"], "delegated": bool(pass_.get("delegated")),
                "pieces": [pass_["piece"]], "paths": ["script", "spoken_opening", *CAPTION_LEAVES],
                "note": f"{c2.LABELS[pass_['piece']]}: the recorded take became the script; caption and covers written from it"}
    n = len(pass_.get("grants") or [])
    return {"kind": "refinish", "by": pass_["by"], "at": pass_["at"], "delegated": bool(pass_.get("delegated")), "pieces": [],
            "paths": [], "note": f"Finished again with {n} granted item{'s' if n != 1 else ''} as evidence"}
