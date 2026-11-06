"""Same-point recency as a ranking penalty (3.B5 extension, D23).

The verifier's same-point check (`verification.same_point`, E.B25 (f)) flags a card whose title or point repeats a central
point WIA published in the last twelve months, naming the piece; until now ranking ignored the flag, so "reviews aren't
market research", published on 10 June, ranked first in every strategist v6 sample on Week 2. Here, after verification and
before the cards are saved, a card that repeats a piece published inside the repetition window ranks below every card that
does not, keeping the strategist's order within each group, and its ledger says why: the piece, its date, the window and
the date the window ends (`hold_until`, shown at Gate 1 beside the flag). Nothing is hidden or held: the person decides.

The window (D23, Whitney on 13 October: "maybe like a month, two months") comes from settings:
`context.same_point.window_days` (60) for a card that repeats the point and its framing (the title repeats the piece too),
and `context.same_point.fresh_angle_days` (30) for a fresh angle on the same point (only the card's point repeats it).
An undated piece makes no adjustment. Deterministic, no model call; the hook into the cycle is one call
(`sql_pipeline.cards`), so the strategist and card verification can change beside it.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta

from .verification import SAME_POINT_MIN, SAME_POINT_SHARED, point_overlap

KIND = "published_point"
WINDOW, FRESH = "context.same_point.window_days", "context.same_point.fresh_angle_days"


def windows(conn=None) -> tuple[int, int]:
    """The repetition window and the fresh-angle window, in days, from settings (the database's when it has a settings
    table, else the environment and the defaults)."""
    from ..settings_store import values
    v = values((WINDOW, FRESH), conn if hasattr(conn, "transaction") else None)
    return int(v[WINDOW]), int(v[FRESH])


def _repeats(text: str, point: str) -> bool:
    score, shared = point_overlap(text or "", point or "")
    return len(shared) >= SAME_POINT_SHARED and score >= SAME_POINT_MIN


def assess(card: dict, flags: list[dict], on: date, window: int, fresh: int) -> dict | None:
    """The recency penalty for one card, or None: the most recent repeated piece still inside its window."""
    found = []
    for flag in flags or []:
        piece = flag.get("published") if flag.get("kind") == KIND else None
        if not piece or not piece.get("published_on"):
            continue
        published = date.fromisoformat(str(piece["published_on"])[:10])
        same_angle = _repeats(card.get("title") or "", piece.get("key_message") or "")
        days = window if same_angle else fresh
        age = (on - published).days
        if 0 <= age < days:
            found.append({"content_id": piece.get("content_id"), "published_on": published.isoformat(),
                          "title": piece.get("title"), "key_message": piece.get("key_message"), "age_days": age,
                          "window_days": days, "angle": "same" if same_angle else "fresh",
                          "hold_until": (published + timedelta(days=days)).isoformat()})
    if not found:
        return None
    piece = max(found, key=lambda p: (p["hold_until"], p["published_on"]))
    return {**piece, "penalty": "ranked_below_new_points",
            "reason": f'Repeats the point WIA published on {piece["published_on"]} ({(piece["title"] or "")[:80]}), '
                      f'{piece["age_days"]} days ago, inside the {piece["window_days"]}-day window '
                      f'({"a fresh angle on the same point" if piece["angle"] == "fresh" else "the same point and framing"}): '
                      f'ranked below the cards with a new point until {piece["hold_until"]}'}


def rerank(cards: list[dict], ledgers: list[dict], on: date, window: int, fresh: int) -> tuple[dict[int, int], list[dict]]:
    """New ranks for a slate (old rank -> new rank) and the penalties applied, rank by rank. Cards without a penalty keep
    their order at the top; penalised cards follow in their own order."""
    penalties = {c["rank"]: assess(c, ledger.get("flags", []), on, window, fresh) for c, ledger in zip(cards, ledgers)}
    order = sorted(cards, key=lambda c: (penalties[c["rank"]] is not None, c["rank"]))
    ranks = {c["rank"]: i for i, c in enumerate(order, 1)}
    applied = [{"rank": r, "new_rank": ranks[r], **p} for r, p in sorted(penalties.items()) if p]
    return ranks, applied


def apply(angles: list, ledgers: dict[str, dict], output: dict, on: date, window: int, fresh: int) -> tuple[list, dict, list[dict]]:
    """The cycle's hook: the angles with their new ranks, the strategist's output with its publishing order renumbered, and
    the penalties. Each penalised card's ledger carries `recency` and its flag says it was ranked lower."""
    positions = [i for i, a in enumerate(angles) if getattr(a, "card", None) is not None]
    cards = [angles[i].card.model_dump(mode="json") for i in positions]
    if not cards:
        return angles, output, []
    ranks, applied = rerank(cards, [ledgers.get(angles[i].angle_id, {}) for i in positions], on, window, fresh)
    if not applied:
        return angles, output, []
    angles = list(angles)
    by_rank = {p["rank"]: p for p in applied}
    for i in positions:
        old = angles[i].card.rank
        angles[i] = angles[i].model_copy(update={"card": angles[i].card.model_copy(update={"rank": ranks[old]})})
        if old in by_rank and angles[i].angle_id in ledgers:
            ledger = ledgers[angles[i].angle_id]
            penalty = {k: v for k, v in by_rank[old].items() if k not in ("rank", "new_rank")}
            ledger["recency"] = {**penalty, "rank_before": old, "rank_after": ranks[old]}
            for flag in ledger.get("flags", []):
                if flag.get("kind") == KIND and (flag.get("published") or {}).get("content_id") == penalty["content_id"]:
                    flag["message"] = flag["message"].rstrip(".") + f". Ranked lower until {penalty['hold_until']} (3.B5)"
    output = copy.deepcopy(output)
    if output.get("publishing_order"):
        output["publishing_order"] = [ranks[r] for r in output["publishing_order"] if r in ranks]
    return angles, output, applied
