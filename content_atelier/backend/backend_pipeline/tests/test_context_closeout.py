"""The S.B2 review's fixes that need no database: a run in flight tolerates operating facts confirmed mid-run but not
an identity change; an internal figure or an invented name is never cleared by acknowledgement; internal figures are
matched as whole figures over every public part of a v2 brief."""
from __future__ import annotations

import copy

import pytest

from backend_pipeline.briefs.runtime import stable_contract
from backend_pipeline.cycle.verification import BLOCK
from backend_pipeline.gate_one import check_card_approval
from backend_pipeline.knowledge.items import contains_term


def contract(**documents):
    docs = {"content_strategy": "a", "rejection_rules": "b", "cta_catalogue": "c", "offer_sheet": "d", **documents}
    return {"prompt_hashes": {"brief_write": "p"}, "models": {"brief_write": "m"},
            "knowledge_base": {"version": "wia-kb-1", "manifest_sha256": "m1", "context": {"source": "database", "on": "2026-10-18"},
                               "documents": [{"key": k, "sha256": v} for k, v in docs.items()]}}


def test_a_run_in_flight_tolerates_operating_changes_but_not_identity_changes():
    frozen = contract()
    assert stable_contract(contract(cta_catalogue="c2", offer_sheet="d2")) == stable_contract(frozen), \
        "a CTA or price confirmed mid-run is used as it stands"
    assert stable_contract(contract(rejection_rules="b2")) != stable_contract(frozen), "an identity change stops the run"
    other_version = copy.deepcopy(frozen)
    other_version["knowledge_base"]["version"] = "wia-kb-2"
    assert stable_contract(other_version) != stable_contract(frozen)
    prompt = copy.deepcopy(frozen)
    prompt["prompt_hashes"]["brief_write"] = "p2"
    assert stable_contract(prompt) != stable_contract(frozen), "prompts and models stay frozen"
    files = {"prompt_hashes": {}, "knowledge_base": {"version": "files", "documents": [{"key": "cta_catalogue", "sha256": "x"}]}}
    assert stable_contract(files) == files, "a file knowledge base has no live documents; everything stays frozen"


def test_a_raised_output_limit_does_not_stop_a_run_in_flight():
    """N2, 23 October: a brief's claim check was cut off at 16,000 tokens; raising the limit must let the step finish,
    not void the run's research and writing."""
    frozen = {**contract(), "max_tokens": 16000}
    assert stable_contract({**contract(), "max_tokens": 32000}) == stable_contract(frozen)
    files = {"prompt_hashes": {}, "max_tokens": 16000, "knowledge_base": {"version": "files", "documents": []}}
    assert stable_contract({**files, "max_tokens": None}) == stable_contract(files)


@pytest.mark.parametrize("kind", ["internal_item", "invented_person"])
def test_an_internal_figure_or_invented_name_cannot_be_acknowledged(kind):
    card = {"verify_before_publishing": []}
    ledger = {"flags": [{"id": "flag_1", "kind": kind, "severity": BLOCK, "message": "States $1,497/month"}]}
    with pytest.raises(ValueError, match="Reframe this card first"):
        check_card_approval(card, ["flag_1"], {}, ledger, note="Checked against the call")
    other = {"flags": [{"id": "flag_2", "kind": "unsupported_fact", "severity": BLOCK, "message": "Unsupported"}]}
    check_card_approval(card, ["flag_2"], {}, other, note="Checked against the call")


@pytest.mark.parametrize("text,term,found", [
    ("ELEVATE is $1,497/month", "$1,497", True),
    ("Spend $5,000 a month", "$500", False),
    ("We charge $500.", "$500", True),
    ("A $11,497 package", "$1,497", False),
    ("Call it 1,497 dollars", "$1,497", False),
    ("The Launchpad tier", "Launchpad", True),
    ("Two Launchpads", "Launchpad", True),
    ("MyLaunchpad", "Launchpad", False),
    ("$1,4970 total", "$1,497", False),
])
def test_internal_terms_match_whole_figures_and_words(text, term, found):
    # A word term still matches its plural, which discloses the same name; a figure never matches a larger one.
    assert contains_term(text, term) is found


def test_the_compiled_roster_reads_the_same_as_the_file_tables():
    """A compiled version's roster is a list, a file version's a table; the speaker and verification checks read both
    the same (L.B4), so the committed knowledge base keeps WIA's staff after the switch to compiled versions."""
    from backend_pipeline.config import BACKEND_ROOT
    from backend_pipeline.knowledge_base import team_roster
    root = BACKEND_ROOT / "knowledge_base"
    compiled = team_roster(root)
    table = team_roster(root / "archive" / "wia-kb-2026-10-18.v2")

    def key(row):
        return row["name"], row["role"], row["status"], tuple(row["aliases"])
    assert sorted(map(key, compiled)) == sorted(map(key, table))
    carmen = next(r for r in compiled if r["name"] == "Carmen Cruickshank")
    assert carmen["status"] == "current" and "Cruikshank" in carmen["aliases"]
    assert next(r for r in compiled if r["name"] == "Fallon Looney")["aliases"] == ["Fallon Looney", "Fallon"]


def test_gate_two_steps_are_not_edits_and_examples_are_prose():
    """L.B6 on the live week: confirming the writer's CTA and answering the before-publishing items are Gate 2 steps,
    never style lessons; an approved brief's supporting example is learned as prose, not JSON."""
    from backend_pipeline.knowledge.mining import _editorial, _example_text
    writer = {"choice": "no_explicit_ask", "action": None, "chosen_by": "writer", "offer_connection": "Proposed by the writer"}
    assert not _editorial("cta", writer, {**writer, "chosen_by": "person", "offer_connection": None})
    assert _editorial("cta", writer, {**writer, "choice": "explicit", "action": "DM us ADS"})
    items = [{"kind": "permission", "text": "Confirm permission", "answer": None, "required": True}]
    assert not _editorial("before_publishing", items, [{**items[0], "answer": "Confirmed"}])
    assert _editorial("before_publishing", items, [{**items[0], "text": "Confirm permission and attribution"}])
    assert _editorial("wia_perspective", "Before.", "After.")
    text = _example_text("supporting_example", {"scene": "A venue call.", "wia_move": "Whitney suggested a call.",
                                                "client_contribution": "The owner shared her schedule."})
    assert text == "A venue call.\n\nWhat WIA did: Whitney suggested a call.\n\nWhat the client contributed: The owner shared her schedule."
    assert _example_text("wia_perspective", "We looked at the wait.") == "We looked at the wait."


def test_an_internal_item_blocks_its_figures_and_quoted_words_not_only_dollar_amounts():
    """L.B5: an internal result or note with no dollar figure still reaches public copy unless what it states is
    blocked: its measured figures and the words it quotes (a client's private praise, an internal policy line)."""
    from backend_pipeline.knowledge import items
    said = 'Band client (2025): a year with no attributable weddings, then "booking weddings like clockwork"; 45% more, 30 inquiries'
    phrases = items.internal_phrases(said)
    assert {"booking weddings like clockwork", "45%", "30 inquiries"} <= set(phrases)
    assert items.internal_phrases('ELEVATE: "approved pool" of creatives') == [], "two quoted words are too common to block"
    assert contains_term("We were Booking  weddings like clockwork.", "booking weddings like clockwork")
    assert contains_term("we can’t in good conscience run their ads that way", "we can't in good conscience run their ads that way")
    # A dollar figure is the same figure with or without its thousands separator.
    assert contains_term("ELEVATE at $1497 a month", "$1,497") and contains_term("ELEVATE at $1,497", "$1497")
    assert not contains_term("a $11497 package", "$1,497") and not contains_term("$14,970", "$1,497")


def test_the_file_knowledge_base_blocks_its_internal_lines_in_public_copy():
    """Without the store, the committed knowledge base's internal lines are the internal items (L.B5)."""
    from backend_pipeline.config import BACKEND_ROOT
    from backend_pipeline.cycle.verification import BLOCK, verify_card
    from backend_pipeline.knowledge import assembly
    root = BACKEND_ROOT / "knowledge_base"
    for stage in ("verifier", "brief"):
        kb = assembly.assemble(stage, root=root)
        assert any(t["term"] == "booking weddings like clockwork" for t in kb.internal_terms), stage
    assert assembly.assemble("strategist", root=root).internal_terms == [], "the strategist sees them labelled instead"
    kb = assembly.assemble("verifier", root=root)
    card = {"title": "How one band started booking weddings like clockwork", "core_perspective": "x", "why_it_matters": "x",
            "evidence_points": [], "moment_ids": []}
    flags = verify_card(card, {}, kb.roster, [], internal_terms=kb.internal_terms)["flags"]
    assert any(f["kind"] == "internal_item" and f["severity"] == BLOCK for f in flags)


def test_a_one_off_factual_correction_never_becomes_a_rule():
    """L.B6 (architecture 6.5): an edit that only changes a figure corrects a fact; notes that share only a stop word
    are not one pattern; a correction note names its figure with commas and its unit."""
    from backend_pipeline.knowledge import mining
    days = {"field": "claims", "before": "Results came in 45 days.", "after": "Results came in 30 days.", "brief_id": "b1"}
    weeks = {"field": "claims", "before": "Support lasts 10 weeks.", "after": "Support lasts 12 weeks.", "brief_id": "b2"}
    voice = {"field": "wia_perspective", "before": "We look first — always.", "after": "We look first, always.", "brief_id": "b3"}
    reworded = {"field": "claims", "before": "Results came in 45 days.", "after": "Bookings came in 45 days.", "brief_id": "b4"}
    assert mining.factual_correction(days) and mining.factual_correction(weeks)
    assert not mining.factual_correction(voice) and not mining.factual_correction(reworded)
    assert mining._similar("Too long for the format", "Too salesy") == 0
    assert mining._similar("Sounds like AI: punchy one-liners", "Too many punchy one-liners; it sounds like AI") >= mining.SIMILAR
    m = mining.CORRECTION.search("It was $1,697, not $1,497 a month")
    assert m and m.group(1).strip() == "$1,697" and m.group(2).strip().startswith("$1,497")
    assert mining.correction_target("12 weeks", "10") == "10 weeks"
    assert mining.correction_target("$1,697", "$1,497 a month") == "$1,497 a month"

