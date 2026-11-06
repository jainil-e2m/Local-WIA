"""3.B5 extension: same-point recency as a ranking penalty inside the repetition window (D23: 60 days, 30 for a fresh angle on
the same point), on top of the same-point flag Gate 1 already shows."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from backend_pipeline.cycle import recency
from backend_pipeline.cycle import verification as v
from backend_pipeline.knowledge import published_points


class Card(BaseModel):
    rank: int
    title: str
    core_perspective: str


class Angle(BaseModel):
    angle_id: str
    card: Card


def pieces(on: date) -> list[dict]:
    """The committed register as the verifier receives it: every piece of the last twelve months, the giveaway's included."""
    rows = [e for e in published_points.flat(published_points.load()) if date.fromisoformat(e["published_on"]) <= on]
    return [{"content_id": e["source_ref"], "published_on": e["published_on"], "channel": e["channel"], "title": e["title"],
             "key_message": e["key_message"]} for e in rows if (on - date.fromisoformat(e["published_on"])).days <= 365]


REPS = Card(rank=1, title="Google reps work for Google, not for your business",
            core_perspective="Google reps push you to spend more and try new features, but they don't know your business or your client journey.")
FRESH = Card(rank=2, title="What we check before we trust an account's numbers",
             core_perspective="Google's own recommendations serve Google's goals and aren't always what's best for a wedding business.")
NEW = Card(rank=3, title="How we decide a new client's first month of ad spend",
           core_perspective="A smaller first budget on a sound account teaches us more than a big one on a guess.")


def slate(on: date):
    published = pieces(on)
    angles = [Angle(angle_id=f"a{c.rank}", card=c) for c in (REPS, FRESH, NEW)]
    ledgers = {a.angle_id: {"flags": v.same_point(a.card.model_dump(), published)} for a in angles}
    return angles, ledgers


def test_a_card_repeating_a_giveaway_piece_drops_below_the_new_points_with_the_piece_and_date_shown():
    on = date(2026, 10, 20)
    angles, ledgers = slate(on)
    assert ledgers["a1"]["flags"] and ledgers["a2"]["flags"] and not ledgers["a3"]["flags"], "the same-point flag already shows"
    output = {"angles": [], "publishing_order": [1, 3, 2]}
    reranked, out, applied = recency.apply(angles, ledgers, output, on, 60, 30)
    assert [a.angle_id for a in sorted(reranked, key=lambda a: a.card.rank)] == ["a3", "a1", "a2"]
    assert out["publishing_order"] == [2, 1, 3] and output["publishing_order"] == [1, 3, 2], "renumbered, the input untouched"
    reps = ledgers["a1"]["recency"]
    assert reps["published_on"] == "2026-10-08" and reps["angle"] == "same" and reps["window_days"] == 60
    assert reps["hold_until"] == "2026-12-07" and reps["rank_before"] == 1 and reps["rank_after"] == 2
    assert "Ranked lower until 2026-12-07" in next(f["message"] for f in ledgers["a1"]["flags"] if f["kind"] == "published_point")
    # Only the point repeats: a fresh angle on the same point, with the shorter window.
    assert ledgers["a2"]["recency"]["angle"] == "fresh" and ledgers["a2"]["recency"]["window_days"] == 30
    assert {p["rank"] for p in applied} == {1, 2}


def test_outside_the_window_the_flag_stays_and_the_rank_does_not_move():
    on = date(2026, 11, 20)  # 43 days after the giveaway's pieces: past the fresh-angle window, inside the full one
    angles, ledgers = slate(on)
    reranked, _, applied = recency.apply(angles, ledgers, {"angles": []}, on, 60, 30)
    assert [p["rank"] for p in applied] == [1]
    assert [a.angle_id for a in sorted(reranked, key=lambda a: a.card.rank)] == ["a2", "a3", "a1"]
    later = date(2027, 1, 20)
    angles, ledgers = slate(later)
    reranked, _, applied = recency.apply(angles, ledgers, {"angles": []}, later, 60, 30)
    assert applied == [] and [a.card.rank for a in reranked] == [1, 2, 3] and ledgers["a1"]["flags"]


def test_the_june_email_repeated_on_week_2_ranks_last_and_the_window_comes_from_settings():
    on = date(2026, 6, 14)
    card = Card(rank=1, title="Why reviews aren't market research",
                core_perspective="Ask past clients why they actually booked: almost no wedding business has surveyed them, and reviews are not that.")
    flags = v.same_point(card.model_dump(), pieces(on))
    assert flags and flags[0]["published"]["published_on"] == "2026-06-10"
    ranks, applied = recency.rerank([card.model_dump(), {**NEW.model_dump(), "rank": 2}], [{"flags": flags}, {"flags": []}], on, 60, 30)
    assert ranks == {1: 2, 2: 1} and applied[0]["age_days"] == 4
    assert recency.windows() == (60, 30)
    # A window of zero days turns the penalty off; an undated piece never moves a card.
    assert recency.rerank([card.model_dump()], [{"flags": flags}], on, 0, 0)[1] == []
    undated = [{**flags[0], "published": {**flags[0]["published"], "published_on": None}}]
    assert recency.assess(card.model_dump(), undated, on, 60, 30) is None
