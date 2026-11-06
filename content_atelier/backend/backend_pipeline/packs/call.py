"""The card's call for finisher v4 (Round 2, second pass: premise Reels on thin evidence).

The brief's selected evidence was chosen for the central story, so Reels 2 and 3 had little of their own to stand on and
the writer filled the gap with invented steps and methods. Finisher v4's plan reads the card's whole call, turn by turn
with its times (`turns`), to find premises of their own; the turns each premise's times point to (`material`) then go to
the writing call and, as evidence, to the check and the repair, so a premise Reel is written and judged against what was
actually said there. Only the card's own call (the transcripts its anchor evidence comes from) is read, and only when its
source allows research; nothing identifies a database (no ids), so the same call gives the same request in any copy.
"""
from __future__ import annotations

import re

from ..briefs import turns as T
from ..briefs.inputs import source_allowed
from ..store import canonical_hash

# The call's text the plan reads, in characters: about an hour of conversation. A longer call is read from its start.
CAP = 40000
# Around a premise's times: a little before the first, a minute after the last, so a turn's answer comes with its question.
BEFORE_MS, AFTER_MS = 15000, 60000
_TIME = re.compile(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})")


def _at(ms) -> str | None:
    if ms is None:
        return None
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}"


def turns(conn, brief_id: str) -> list[dict]:
    """The card's call as turns ({at, start_ms, speaker, said, call_date}), up to CAP characters; [] when there is none."""
    row = conn.execute("SELECT selected_evidence FROM content_briefs WHERE brief_id=%s", (brief_id,)).fetchone()
    items = (row or {}).get("selected_evidence") or []
    ids = sorted({e["transcript_id"] for e in items if e.get("transcript_id") and e.get("role") == "anchor"}) or \
        sorted({e["transcript_id"] for e in items if e.get("transcript_id") and e.get("role") != "external_framing"})[:1]
    out, size = [], 0
    for tid in ids:
        source = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (tid,)).fetchone()
        if not source or not source_allowed(source):
            continue
        date = source.get("occurred_at")
        date = date.date().isoformat() if hasattr(date, "date") else (str(date)[:10] if date else None)
        for p in source.get("passage_map") or []:
            said = T.words(source["original_text"][p["start"]:p["end"]], p.get("speaker")).strip()
            if not said:
                continue
            size += len(said) + 40
            if size > CAP:
                return out
            out.append({"at": _at(p.get("start_ms")), "start_ms": p.get("start_ms"), "speaker": p.get("speaker"),
                        "said": said, "call_date": date})
    return out


def lines(call: list[dict]) -> list[str]:
    """The call as the plan reads it: one line a turn, "m:ss Speaker: words"."""
    return [f"{t['at']} {t.get('speaker') or 'Speaker'}: {t['said']}" for t in call]


def _windows(timestamps: list[str]) -> list[tuple[int, int]]:
    out = []
    for stamp in timestamps or []:
        times = [((int(h or 0) * 60 + int(m)) * 60 + int(s)) * 1000 for h, m, s in _TIME.findall(stamp)[:2]]
        if times:
            out.append((min(times) - BEFORE_MS, max(times) + AFTER_MS))
    return out


def material(call: list[dict], plan) -> dict[str, list[dict]]:
    """The call's turns behind Reels 2 and 3, by piece key, from the plan's times for each."""
    from . import contracts_v2 as c2
    out = {}
    for reel in plan.reels:
        key = c2.KIND_KEY[reel.kind]
        if key == "reel_1":
            continue
        spans = _windows(list(reel.timestamps))
        found = [t for t in call if t.get("start_ms") is not None and any(a <= t["start_ms"] <= b for a, b in spans)]
        if found:
            out[key] = [{k: t[k] for k in ("at", "speaker", "said", "call_date")} for t in found]
    return out


def as_evidence(found: dict[str, list[dict]]) -> list[dict]:
    """The premise material as evidence items for the check and the repair: told, never quoted (`quotable` false), since no
    one has cleared these turns for quotation."""
    seen, out = set(), []
    for turns_ in found.values():
        for t in turns_:
            key = (t["at"], t["speaker"], t["said"])
            if key in seen:
                continue
            seen.add(key)
            ms = None
            if m := _TIME.fullmatch(t["at"] or ""):
                ms = ((int(m.group(1) or 0) * 60 + int(m.group(2))) * 60 + int(m.group(3))) * 1000
            out.append({"evidence_id": "call_" + canonical_hash(list(key))[:16], "speaker": t["speaker"], "start_ms": ms,
                        "call_date": t.get("call_date"), "quote": t["said"], "client_consent": "anonymise", "quotable": False,
                        "role": "premise_material"})
    return out
