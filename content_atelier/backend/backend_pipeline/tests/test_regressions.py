"""E.B3's regression cases offline: each is a deterministic check that catches its error and passes a correct card or
revision; the evaluation command reports the card cases on every configuration's samples."""
from __future__ import annotations

from backend_pipeline.cycle.verification import verify_card
from evaluation import regressions

ROSTER = [{"name": "Whitney Hodges", "role": "Co-founder", "status": "current", "aliases": ["Whitney Hodges", "Whitney"]},
          {"name": "Carmen Cruickshank", "role": "Google Ads lead", "status": "current", "aliases": ["Carmen Cruickshank", "Carmen"]}]


def span(who, said, at=0):
    """A synthetic span as verify_card reads it (no transcript text: R48)."""
    return dict(text=said, speaker=who, start_seconds=at)


SCENES = {
    "m1": [span("Carmen", "Keep the term under review until the inquiries show what it brings.", 10),
           span("Whitney", "That makes sense to me.", 20)],
    "m2": [span("Carmen", "We're going to launch the new retargeting campaign next week.", 5)],
    "m3": [span("Prospect", "Honestly it's too expensive for us right now, the monthly fee is a lot.", 3),
           span("Whitney", "I hear you; let's look at what a booking is worth to you.", 9)],
    "m4": [span("Carmen", "We haven't seen the numbers from the show yet.", 1)],
}


def card(**fields):
    return {"title": "A card", "core_perspective": "A view", "why_it_matters": "It matters", "wia_in_action": "",
            "offer_connection": "", "evidence_points": [], "moment_ids": ["m1"], **fields}


def findings(c):
    ledger = verify_card(c, SCENES, ROSTER, [])
    return {case: found for case, found in regressions.card_findings(c, ledger, SCENES, ROSTER).items() if found}


def test_the_seven_cases_are_the_plans():
    assert list(regressions.CASES.values()) == [
        "a team member's quote is not turned into Whitney's anecdote", "a planned capability is not stated as current",
        'one recommendation is not called "a WIA practice"', "price objections stay internal",
        "an unknown result is not stated as zero", "a local edit keeps untouched text",
        "an approved line survives a later revision word for word"]
    assert regressions.CARD_CASES + regressions.BRIEF_CASES == tuple(regressions.CASES)


def test_a_team_members_quote_is_not_turned_into_whitneys_anecdote():
    stolen = card(wia_in_action='Whitney told the client: "keep the term under review until the inquiries show"')
    assert list(findings(stolen)) == ["team_quote_as_whitney_anecdote"]
    assert "Carmen Cruickshank's" in findings(stolen)["team_quote_as_whitney_anecdote"][0]
    absent = card(moment_ids=["m2"], wia_in_action="Whitney explained the retargeting plan to the client")
    assert "team_quote_as_whitney_anecdote" in findings(absent), "credited, and she does not speak in the scene"
    right = card(wia_in_action='Carmen told the client: "keep the term under review until the inquiries show"')
    assert findings(right) == {}


def test_a_planned_capability_is_not_stated_as_current():
    assert "planned_capability_as_current" in findings(card(moment_ids=["m2"], core_perspective="We launched the new retargeting campaign"))
    assert findings(card(moment_ids=["m2"], core_perspective="We plan a new retargeting campaign")) == {}


def test_one_recommendation_is_not_called_a_wia_practice():
    assert "one_recommendation_as_wia_practice" in findings(card(core_perspective="Reviewing terms with the client is a WIA practice"))
    assert findings(card(core_perspective="Carmen suggested reviewing the term with the client")) == {}


def test_price_objections_stay_internal():
    assert "price_objection_public" in findings(card(title="Why owners balk at the monthly fee"))
    cited = card(moment_ids=["m3"], why_it_matters="What a booking is worth shapes the investment in ads")
    assert "cites a price objection by Prospect" in findings(cited)["price_objection_public"][0]
    assert findings(card(moment_ids=["m3"], why_it_matters="What a booking is worth to a venue")) == {}
    # Week 2's audit prospect: "too much information" on a page is not a price objection.
    scenes = {**SCENES, "m5": [span("Prospect", "I want to know if it's too much information before the quote form.")]}
    framed = card(moment_ids=["m5"], why_it_matters="Where the quote form sits shapes the investment")
    assert regressions.price_objection(framed, scenes, ROSTER) == []


def test_an_unknown_result_is_not_stated_as_zero():
    assert "unknown_result_as_zero" in findings(card(moment_ids=["m4"], core_perspective="The show brought no leads"))
    assert findings(card(moment_ids=["m4"], core_perspective="The show's results are not in yet")) == {}


def test_a_local_edit_keeps_untouched_text():
    before = {"header": {"title": "T"}, "body": {"narrative": "First.", "cta": "Book a call", "claims": [{"text": "A"}]}}
    edited = {**before, "body": {**before["body"], "narrative": "First, sharper."}}
    assert regressions.local_edit_findings(before, edited, ["body.narrative"]) == []
    spilled = {**edited, "body": {**edited["body"], "cta": "Book now"}}
    assert regressions.local_edit_findings(before, spilled, ["body.narrative"]) == ["body.cta: changed outside the edit"]
    dropped = {**edited, "body": {**edited["body"], "claims": []}}
    assert regressions.local_edit_findings(before, dropped, ["body.narrative"]) == ["body.claims[0].text: changed outside the edit"]


def test_an_approved_line_survives_a_later_revision_word_for_word():
    approved = ["We work with your market, not against it."]
    kept = {"body": {"narrative": "Opening.  We work with your market,\nnot against it. Closing."}}
    assert regressions.approved_line_findings(approved, kept) == []
    reworded = {"body": {"narrative": "We work with your market rather than against it."}}
    assert regressions.approved_line_findings(approved, reworded) == ["lost: 'We work with your market, not against it.'"]
    found = regressions.brief_findings({"body": {"narrative": "x"}}, reworded, edited=["body.narrative"], approved=approved)
    assert found["local_edit_changes_untouched_text"] == [] and found["approved_line_lost_in_revision"]


def test_the_counts_cover_every_card_case():
    cards = [card(title="Why owners balk at the monthly fee"), card()]
    ledgers = [verify_card(c, SCENES, ROSTER, []) for c in cards]
    counts = regressions.card_counts(cards, ledgers, SCENES, ROSTER)
    assert set(counts) == set(regressions.CARD_CASES) and counts["price_objection_public"] == 1 and sum(counts.values()) == 1
