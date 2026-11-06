"""E.B26's report on saved benchmark samples: do Whitney's stance and the strategist's checkpoint survive, correctly
credited and with no blocking flag, and does the slate keep the content plan's pillar mix with few template titles?

Offline and free: it reads saved samples only (research/benchmark-v1/runs), never generates one.

- The two Week 2 golden scenes E.B26 names (g07 buying research, g09 clicks without conversions) are mapped to the
  packet's moment IDs by their anchor quote: the benchmark packet carries excerpts, not the golden file's transcript IDs,
  so the scene whose turns hold the anchor is the one, and the golden file's `source` must agree.
- For each card citing such a scene: its title and pillar; whether the scene's key claim survives (a deterministic proxy:
  the claim's words appear in the card's framing) and is credited to the right person (the framing names the WIA
  speaker of the anchor turn, or "our team"); and its blocking flags from the deterministic ledger.
- Per sample: ATTRACT cards, and titles that open "Why/What/How we" or "We" (the template section 1.9.2 counts).
"""
from __future__ import annotations

import json
import re

from backend_pipeline.cycle import verification
from backend_pipeline.knowledge.assembly import assemble

from . import run
from .benchmark import RESEARCH

GOLDEN = RESEARCH / "golden-scenes" / "benchmark-v1-scenes.json"
# The scenes E.B26's "done when" names, and the claim each must keep. Every group must appear in the card's framing (any
# phrase of a group will do); the words are the scene's own.
STANCES = {
    "g07": {"stance": "Whitney's stance: reviews are not market research",
            "claim": [("market research",), ("review",)]},
    "g09": {"stance": "the strategist's checkpoint: judge the campaign at about 100 clicks",
            "claim": [("100 clicks", "100 click", "hundred clicks"),]},
}
FRAMING = ("title", "core_perspective", "why_it_matters", "wia_in_action")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").replace("’", "'").lower()).strip()


def golden_scenes(week: str, ids=tuple(STANCES)) -> dict[str, dict]:
    """Golden ID -> the packet moment holding its anchor, and the speaker of the anchor turn."""
    scenes = {s["id"]: s for s in json.loads(GOLDEN.read_text(encoding="utf-8"))["scenes"] if s["id"] in ids}
    found = {}
    for gid, scene in scenes.items():
        anchor = _norm(scene["anchor"])
        for moment in run.packet(week):
            turn = next((t for t in moment["source_evidence"] if anchor in _norm(t["text"])), None)
            if turn:
                if scene.get("source") and scene["source"] != moment["moment_id"]:
                    raise ValueError(f"Golden scene {gid}'s anchor is in {moment['moment_id']}, not its source {scene['source']}")
                found[gid] = {"moment_id": moment["moment_id"], "speaker": turn["speaker"], "anchor": scene["anchor"],
                              "note": scene.get("note")}
                break
    return found


def stance_of(card: dict, golden: dict, stance: dict, roster: list[dict]) -> dict:
    framing = " ".join(str(card.get(f) or "") for f in FRAMING)
    text = _norm(framing)
    claim = all(any(_norm(p) in text for p in group) for group in stance["claim"])
    entry = verification.speaker_entry(golden["speaker"], roster)
    names = [a for a in (entry or {}).get("aliases", []) if len(a) >= 3] if entry and entry["status"] == "current" else []
    credited = bool(re.search(r"\bour team\b", framing, re.I)) or any(re.search(rf"\b{re.escape(a)}\b", framing) for a in names)
    return {"claim_present": claim, "credited": credited, "speaker": (entry or {}).get("name") or golden["speaker"]}


def sample_report(config_name: str, week: str, record: dict) -> dict:
    cards, _ = run.cards_of(config_name, week, record["output"])
    kb = assemble("verifier", root=run.KB)
    document = getattr(kb, "document", None)
    beliefs = verification.belief_index(document(verification.BELIEF_DOCUMENT)) if document else None
    scenes = {m["moment_id"]: m["source_evidence"] for m in run.packet(week)}
    rules = verification.load_rules(run.KB)
    goldens = golden_scenes(week)
    out = {"sample": record.get("sample"), "cards": len(cards),
           "attract_cards": sum(c["pillar"] == "ATTRACT" for c in cards),
           "template_titles": sum(bool(run.TEMPLATE_TITLE.match(c["title"])) for c in cards),
           "pillars": [c["pillar"] for c in cards], "scenes": {}}
    for gid, golden in goldens.items():
        rows = []
        for card in cards:
            if golden["moment_id"] not in card["moment_ids"]:
                continue
            ledger = verification.verify_card(card, scenes, kb.roster, rules, beliefs=beliefs)
            blocks = [f"{f['kind']}: {f['message']}" for f in verification.blocking(ledger)]
            stance = stance_of(card, golden, STANCES[gid], kb.roster)
            rows.append({"rank": card["rank"], "title": card["title"], "pillar": card["pillar"], **stance,
                         "blocking_flags": blocks,
                         "survives": stance["claim_present"] and stance["credited"] and not blocks})
        out["scenes"][gid] = {"moment_id": golden["moment_id"], "cards": rows, "survives": any(r["survives"] for r in rows)}
    return out


def report(config_names, weeks, samples: int, label: str = "") -> dict:
    """Every saved sample of each configuration and week; a missing sample is listed, never generated."""
    result = {"golden": GOLDEN.relative_to(RESEARCH.parent).as_posix(), "label": label or None, "stances": STANCES,
              "configs": {}}
    for name in config_names:
        weeks_out = {}
        for week in weeks:
            rows, missing = [], []
            for s in range(1, samples + 1):
                path = run.OUT / "runs" / f"{name}-{week}-s{s}{label}.json"
                if not path.is_file():
                    missing.append(path.name)
                    continue
                rows.append(sample_report(name, week, json.loads(path.read_text(encoding="utf-8"))))
            summary = {"samples": len(rows), "samples_with_attract": sum(r["attract_cards"] > 0 for r in rows),
                       "template_titles": f"{sum(r['template_titles'] for r in rows)} of {sum(r['cards'] for r in rows)}"}
            for gid in STANCES:
                if any(gid in r["scenes"] for r in rows):
                    summary[f"{gid}_survives_in_samples"] = sum(r["scenes"].get(gid, {}).get("survives", False) for r in rows)
            weeks_out[week] = {"summary": summary, "samples": rows, "missing": missing}
        result["configs"][name] = weeks_out
    return result
