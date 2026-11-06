"""E.B25 (f) offline: the committed central points of WIA's published log, and the verifier's same-point check."""
from __future__ import annotations

from datetime import date

import pytest

from backend_pipeline.cycle import verification as v
from backend_pipeline.knowledge import published_points, seed

UVP = {"content_id": "published_uvp", "published_on": "2026-09-15", "channel": "Email",
       "title": '"What I taught my clients this week" (UVP training)',
       "key_message": "Advertising starts before the ads: define your unique value proposition before you write an ad or build a landing page."}
QUESTION = {"content_id": "published_question", "published_on": "2026-06-10", "channel": "Email",
            "title": '"The question we ask every new client" / preview "I\'m always surprised by the answer"',
            "key_message": "Ask your clients why they actually booked: WIA asks every new client whether they have surveyed past clients on why they chose them, and almost none have."}


def card(title, perspective):
    return {"title": title, "core_perspective": perspective, "why_it_matters": "x", "wia_in_action": "WIA view (knowledge base): x",
            "evidence_points": [], "moment_ids": []}


# Clear positive pairs: the same point in other words; clear negatives: the same topic, another point.
REPEATS = [
    (card("Why your ads start before the ad account", "Before you write a single ad or build a landing page, define your unique value proposition."), UVP),
    (card("The survey nobody runs", "Ask your past clients why they actually booked you: almost no wedding business has surveyed them on why they chose it."), QUESTION),
]
DISTINCT = [
    (card("Why your landing page needs one job", "A landing page converts when it asks for one action, not five."), UVP),
    (card("Why we ask about follow-up first", "Follow-up shapes lead quality."), QUESTION),
    (card("Reviews are not research", "A five-star review tells you the client was happy, not why they chose you over the venue down the road."), QUESTION),
]


@pytest.mark.parametrize("repeat, piece", REPEATS)
def test_a_card_repeating_a_published_central_point_is_flagged_with_the_piece(repeat, piece):
    ledger = v.verify_card(repeat, {}, [], [], published=[piece, *(p for _, p in DISTINCT if p is not piece)])
    flags = [f for f in ledger["flags"] if f["kind"] == "published_point"]
    assert len(flags) == 1 and flags[0]["severity"] == v.CHECK, "flagged for a look, never blocked"
    assert flags[0]["published"]["content_id"] == piece["content_id"] and piece["published_on"] in flags[0]["message"]
    assert flags[0]["field"] == "core_perspective" and flags[0]["published"]["overlap"] >= v.SAME_POINT_MIN
    assert ledger["readiness"] != "research_required"


@pytest.mark.parametrize("other, piece", DISTINCT)
def test_a_card_on_the_same_topic_with_another_point_is_not_flagged(other, piece):
    score, shared = v.point_overlap(other["core_perspective"], piece["key_message"])
    assert not (score >= v.SAME_POINT_MIN and len(shared) >= v.SAME_POINT_SHARED), (score, shared)
    assert not v.same_point(other, [piece])


def test_the_words_every_point_shares_do_not_make_a_repeat():
    # Wedding, pros, business and ads appear in nearly every WIA point; alone they never count.
    assert v.point_words("Ads for wedding pros: a business owner's marketing") == set()
    assert v.point_words("Couples booked tours from inquiries") == {"couple", "book", "tour", "inquiry"}
    assert v.same_point(card("x", "x"), None) == []


def test_the_committed_central_points_cover_the_published_log():
    entries = published_points.load()
    assert len(entries) == 56 and all(e["source_ref"].startswith(seed.DRAFTS.as_posix() + "/published-content-log.md#") for e in entries)
    by_date = {e["published_on"]: e for e in entries}
    # The plan names the 10 June email and the September UVP campaign.
    assert "surveyed past clients" in by_date["2026-06-10"]["key_message"]
    assert "unique value proposition" in by_date["2026-09-15"]["key_message"] and by_date["2026-09-15"]["date_precision"] == "approximate"
    assert {e["date_precision"] for e in entries} == {"day", "month", "approximate"}
    assert not any("—" in e["key_message"] for e in entries)
    in_window = [e for e in entries if date(2025, 10, 20) <= date.fromisoformat(e["published_on"]) <= date(2026, 10, 20)]
    assert len(in_window) == 45


@pytest.mark.skipif(not (seed.REPOSITORY_ROOT / seed.DRAFTS).is_dir(), reason="The export analysis drafts are not checked out")
def test_each_central_point_names_a_row_the_context_seed_records():
    rows = [e for e in seed.entries(seed.REPOSITORY_ROOT / seed.DRAFTS / "published-content-log.md")
            if e.shape == "row" and not seed.screen(e.text)]
    refs = {f"{seed.DRAFTS.as_posix()}/{e.anchor}": seed.clean(e.cells.get("Item and hook") or e.text)[:2000] for e in rows}
    entries = published_points.load()
    assert {e["source_ref"] for e in entries} == set(refs) and all(e["title"] == refs[e["source_ref"]] for e in entries)
