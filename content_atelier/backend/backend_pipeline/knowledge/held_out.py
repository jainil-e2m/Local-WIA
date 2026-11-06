"""Held-out benchmark weeks (E.B17): no knowledge-base text, exemplar or situational line may derive from them.

A week counts as held out only if no prompt or knowledge-base text derives from it. The context store was seeded
from the ChatGPT export (L.B2), which also holds WIA's published pieces built on held-out calls, and a reviewer
accepting a candidate cannot be expected to know which call a story came from. So the guard is here, in code: every
compiled document, the brief writer's exemplars and the strategist's situational block leave out an item or published
piece that states held-out material, and a compiled version records what it withheld.

What a week withholds is the material itself (the result's figures, the client's words, the pieces built on it), not
every line that cites the same ChatGPT conversation: a general belief Whitney stated in that conversation carries
nothing from the call. Release a week (remove it here) only after it has served as a held-out week and its result is
recorded; the withheld items then compile again with no review needed.
"""
from __future__ import annotations

import json
import re

HELD_OUT: dict[int, dict] = {
    # The clean held-out label week of E.B13 and E.X3. Checked on 19 October against its six documents (backfill week5,
    # 29 June to 5 July 2026): no compiled version, seed input or strategist prompt states its material and no piece was
    # built on it, so it has no keys. The patterns are the week's own stories, not its clients' names: The Elia, Alexis,
    # Lux Travel and the Penny return in later weeks, whose material is not held out.
    5: {
        "what": ("The stories of benchmark Week 5's calls (backfill week5, from 29 June 2026): the venue prospect who pays "
                 "her agency and its setter, booked 15 tours from a wedding show and runs three other businesses; "
                 "The Elia's TikTok leads, all-inclusive switch and falling conversions; Alexis Gaston's progression "
                 "call; and the Penny creative of the internal check-in"),
        "patterns": (r"\b15 tours\b", r"bought (?:the|a|her|their) venue", r"\b(?:three|3) other businesses\b",
                     r"\bauto(?:motive)? industry\b", r"\bsetter\b",
                     r"(?:spending|spend|paying|pays|paid) \$?[\d,]+K? (?:a month |per month )?(?:with|to) Hitched|Hitched is only doing",
                     r"I ?Do Society.{0,60}(?:TikTok|ads|leads|traffic)", r"rental(?: fee)?[^.]{0,40}\$7,000",
                     r"tours[^.]{0,40}conversions (?:are|were) down|conversions (?:are|were) down[^.]{0,80}all-inclusive",
                     r"Broken Bow", r"coming out of my bank account", r"Welcome to the Penny", r"POV:? your camera roll"),
        "keys": (),
    },
    6: {
        "what": ("The Ads Accelerator venue result discussed in benchmark Week 6 (backfill week6, from 6 July 2026) and "
                 "the pieces built on it: Reel 5 (7 July) and the case-study Reel, email, carousel and caption "
                 "(31 July to 4 August)"),
        # The result's figures and its client's words, as WIA's pieces and the export state them.
        "patterns": (r"\$?22,000\b", r"\$22\s?K\b", r"\$?70\s?K\b", r"\$?70,000\b", r"venue marketing director",
                     r"hand-hold her agency", r"venue['’]s total revenue"),
        # Pieces built on the result whose own text carries none of it: the case-study carousel's caption and the
        # case-study email's opening (conversation 2026-08-04_6a721147).
        "keys": ("exemplar:ex01", "exemplar:ex26"),
    },
}
_PATTERNS = {week: re.compile("|".join(spec["patterns"]), re.I) for week, spec in HELD_OUT.items()}


def week_of(row: dict) -> int | None:
    """The held-out week an item or published piece derives from, or None."""
    said = " ".join([str(row.get("text") or ""), str(row.get("title") or ""),
                     json.dumps(row.get("body") or {}, ensure_ascii=False)])
    for week, spec in HELD_OUT.items():
        if row.get("key") in spec["keys"] or _PATTERNS[week].search(said):
            return week
    return None


def keep(rows: list[dict]) -> list[dict]:
    """The rows that derive from no held-out week."""
    return [r for r in rows if week_of(r) is None]


def withheld(rows: list[dict]) -> list[dict]:
    """What a compiled document leaves out, for its record: item or piece, and the week."""
    return [{"id": r.get("item_id") or r.get("content_id"), "key": r.get("key"), "week": week}
            for r in rows if (week := week_of(r)) is not None]


def text_weeks(text: str) -> set[int]:
    """The held-out weeks whose material a text states (the committed knowledge base's guard)."""
    return {week for week, pattern in _PATTERNS.items() if pattern.search(text or "")}


def check_live(text: str) -> None:
    """A live run (real calls on real data) loads only a knowledge base that holds every held-out week out; an
    archived version that predates the guard is for replaying the runs that used it."""
    if weeks := text_weeks(text):
        raise ValueError(f"This knowledge base states material from held-out benchmark week {', '.join(map(str, sorted(weeks)))} "
                         "(E.B17); a live run needs a version that holds it out. Replay saved runs instead.")
