"""Round 2's second pass: three checks that misfired on the re-test's packs read the copy as a person would. Invented text
only (R48)."""
from __future__ import annotations

import pytest

from backend_pipeline.briefs.first_touch import pairs
from backend_pipeline.cycle.verification import ZERO_CLAIM


@pytest.mark.parametrize("text", ["Others want us to launch their campaigns, then guide them while they run them.",
                                  "Some owners want a team to manage their ads. Others want us to launch their campaigns, "
                                  "then guide them while they run them."])
def test_the_offers_close_is_not_a_beat_even_after_then(text):
    assert pairs(text, copy=True) == []


def test_a_person_inside_a_relative_clause_is_not_the_one_who_acted():
    assert pairs("The team member I was talking with had set them up and helps part-time.", copy=True) == []
    assert pairs("We set up the campaigns, then she ran them.", copy=True) == [
        ("wia", "set_up", "We set up the campaigns,"), ("client", "run", "she ran them")], "real beats are still read"


@pytest.mark.parametrize("text,zero", [("No inquiry form could tell you that.", False), ("There's no tours page yet.", False),
                                       ("She had no inquiries yet.", True), ("No leads came in that week.", True)])
def test_a_noun_used_as_a_modifier_is_not_a_zero_claim(text, zero):
    assert bool(ZERO_CLAIM.search(text)) is zero
