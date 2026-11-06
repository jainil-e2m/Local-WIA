"""E.B3's regression cases, checked on every configuration (plan E.B3, "Regression cases on every configuration").

Deterministic, with no model call. The card cases read E.B10's ledger for each generated card (the verifier already
finds tense and status overclaims, a recommendation generalised into a practice and a zero stated without support) and
add what the ledger does not decide: whether the person credited is Whitney, and whether a price objection reached a
public card. The brief cases compare a revision with the version before it. `run.sample_metrics` reports the card cases
for every sample; the brief cases apply wherever a configuration produces brief revisions, and run on the product's
own Gate 2 section edit and revision in test_regressions_db.py.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from backend_pipeline.cycle.verification import normalise, speaker_entry

FOUNDER = "Whitney Hodges"
CASES = {
    "team_quote_as_whitney_anecdote": "a team member's quote is not turned into Whitney's anecdote",
    "planned_capability_as_current": "a planned capability is not stated as current",
    "one_recommendation_as_wia_practice": 'one recommendation is not called "a WIA practice"',
    "price_objection_public": "price objections stay internal",
    "unknown_result_as_zero": "an unknown result is not stated as zero",
    "local_edit_changes_untouched_text": "a local edit keeps untouched text",
    "approved_line_lost_in_revision": "an approved line survives a later revision word for word",
}
CARD_CASES = tuple(list(CASES)[:5])
BRIEF_CASES = tuple(list(CASES)[5:])
# The ledger flag kinds (E.B10, cycle/verification.py) that decide a card case.
LEDGER_KINDS = {"planned_capability_as_current": ("tense", "status"),
                "one_recommendation_as_wia_practice": ("generalised_practice",),
                "unknown_result_as_zero": ("zero_claim",)}
FRAMING = ("title", "core_perspective", "why_it_matters", "wia_in_action", "offer_connection")
PRICE = r"(?:price|prices|pricing|priced|cost|costs|fee|fees|investment|budget|expensive|afford|rate|rates)"
OBJECTION = re.compile(rf"\b(?:too expensive|too much (?:money|to spend|for (?:us|me|our budget))|can(?:no|')?t afford|out of (?:my|our) budget|not in (?:my|our|the) budget|"
                       rf"(?:objection|objected|push(?:ed|ing)? back|hesitat\w*|balk\w*|pricey|sticker shock)\b[^.?!]{{0,60}}\b{PRICE}|"
                       rf"{PRICE}\b[^.?!]{{0,60}}\b(?:objection|too high|too steep|a lot|is steep|worth it))", re.I)
QUOTED = re.compile(r'"([^"]{8,})"|“([^”]{8,})”')


def _spans(card: dict, scenes: dict[str, list[dict]]) -> list[dict]:
    return [s for mid in card.get("moment_ids", []) for s in scenes.get(mid, [])]


def _founder(roster: list[dict]) -> dict | None:
    return next((r for r in roster if r["name"] == FOUNDER), None)


def team_quote_as_founder(card: dict, scenes: dict[str, list[dict]], roster: list[dict], ledger: dict | None = None) -> list[str]:
    """Whitney credited with words another team member spoke in the cited scenes, or credited at all when she does not
    speak in them (the ledger's misattribution for her)."""
    founder = _founder(roster)
    if not founder:
        return []
    found = [f"{a['field']}: credits {FOUNDER}, who does not speak in the cited scenes"
             for a in (ledger or {}).get("attribution", []) if a["name"] == FOUNDER and not a["speaks_in_scenes"]]
    aliases = [a for a in founder["aliases"] if len(a) >= 3]
    spans = _spans(card, scenes)
    for field in FRAMING:
        text = card.get(field) or ""
        if not any(re.search(rf"\b{re.escape(a)}\b", text) for a in aliases):
            continue
        for quote in (q for pair in QUOTED.findall(text) for q in pair if q):
            for span in spans:
                entry = speaker_entry(span.get("speaker"), roster)
                if entry and entry["name"] != FOUNDER and normalise(quote) in normalise(span["text"]):
                    found.append(f'{field}: "{quote[:60]}" is {entry["name"]}\'s, not {FOUNDER}\'s')
    return found


def price_objection(card: dict, scenes: dict[str, list[dict]], roster: list[dict]) -> list[str]:
    """A public card framed on a price objection, or on a client's or prospect's objection to price in its scenes."""
    framing = " ".join(card.get(f) or "" for f in FRAMING)
    found = [f"framing: {m.group(0)!r}" for m in OBJECTION.finditer(framing)]
    if not found and re.search(rf"\b{PRICE}\b", framing, re.I):
        for span in _spans(card, scenes):
            entry = speaker_entry(span.get("speaker"), roster)
            if (entry is None or entry["status"] not in ("current", "former")) and OBJECTION.search(span["text"]):
                found.append(f"cites a price objection by {span.get('speaker') or 'a client'}: {span['text'][:80]!r}")
    return found


def card_findings(card: dict, ledger: dict, scenes: dict[str, list[dict]], roster: list[dict]) -> dict[str, list[str]]:
    """Each card case's findings for one public card (internal insights are where a price objection belongs)."""
    out = {"team_quote_as_whitney_anecdote": team_quote_as_founder(card, scenes, roster, ledger),
           "price_objection_public": price_objection(card, scenes, roster)}
    for case, kinds in LEDGER_KINDS.items():
        out[case] = [f"{f['field']}: {f['message']}" for f in ledger.get("flags", []) if f["kind"] in kinds]
    return {case: out[case] for case in CARD_CASES}


def card_counts(cards: list[dict], ledgers: list[dict], scenes: dict[str, list[dict]], roster: list[dict]) -> dict[str, int]:
    """Per card case, how many of a sample's public cards fail it."""
    counts = dict.fromkeys(CARD_CASES, 0)
    for card, ledger in zip(cards, ledgers):
        for case, findings in card_findings(card, ledger, scenes, roster).items():
            counts[case] += bool(findings)
    return counts


def _flatten(value, path: str = "") -> dict[str, str]:
    if isinstance(value, dict):
        return {k: v for key, item in value.items() for k, v in _flatten(item, f"{path}.{key}" if path else str(key)).items()}
    if isinstance(value, list):
        return {k: v for i, item in enumerate(value) for k, v in _flatten(item, f"{path}[{i}]").items()}
    return {path: "" if value is None else str(value)}


def _within(path: str, edited: Iterable[str]) -> bool:
    return any(path == e or path.startswith(e + ".") or path.startswith(e + "[") for e in edited)


def local_edit_findings(before: dict, after: dict, edited: Iterable[str]) -> list[str]:
    """A local edit keeps untouched text: every value outside the edited fields (dotted paths, such as
    "body.narrative") is the same after the edit, byte for byte."""
    edited = list(edited)
    old, new = _flatten(before), _flatten(after)
    return [f"{path}: changed outside the edit" for path in sorted(set(old) | set(new))
            if not _within(path, edited) and old.get(path) != new.get(path)]


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("“", '"').replace("”", '"')).strip()


def approved_line_findings(approved: Iterable[str], after: dict | str) -> list[str]:
    """An approved line survives a later revision word for word (spacing and typographic quotes aside)."""
    text = _plain(after if isinstance(after, str) else "\n".join(_flatten(after).values()))
    return [f"lost: {line[:80]!r}" for line in approved if _plain(line) and _plain(line) not in text]


def brief_findings(before: dict, after: dict, *, edited: Iterable[str] = (), approved: Iterable[str] = ()) -> dict[str, list[str]]:
    return {"local_edit_changes_untouched_text": local_edit_findings(before, after, edited),
            "approved_line_lost_in_revision": approved_line_findings(approved, after)}
