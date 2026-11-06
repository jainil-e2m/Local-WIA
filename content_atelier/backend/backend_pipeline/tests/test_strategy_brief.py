"""E.B28 (go-live subset): the window's strategy brief as beliefs to prove, offline. The committed knowledge base, and a
constructed one with an invented offer calendar; no model call, no client text beyond the committed knowledge base."""
from __future__ import annotations

import json
from datetime import date

import pytest

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.cycle import strategy_brief as sb
from backend_pipeline.cycle import verification as v
from backend_pipeline.knowledge.assembly import assemble
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.tests.test_strategist_profile import DOCS, write_kb
from backend_pipeline.tests.test_strategist_v7 import ROSTER, SCENES, v7_card

KB = BACKEND_ROOT / "knowledge_base"
ON = date(2026, 10, 27)


def committed():
    return sb.assemble(assemble("strategist", root=KB), root=KB, on=ON)


def test_the_committed_brief_lists_four_to_six_beliefs_each_with_its_offer_and_quotes_that_are_in_the_knowledge_base():
    brief = committed()
    beliefs = brief["beliefs_to_prove"]
    assert 4 <= len(beliefs) <= 6 and [b["ref"] for b in beliefs] == [f"B{i}" for i in range(1, len(beliefs) + 1)]
    assert {b["stage"] for b in beliefs} == {"ATTRACT", "WARM", "CONVERT"}
    assert sum(b["stage"] == "WARM" for b in beliefs) >= 2, "mostly WARM, as the content plan asks"
    assert all(b["offer"] and b["quotes"] for b in beliefs)
    kb = load_knowledge_base(KB)
    for b in beliefs:
        for q in b["quotes"]:
            assert v.normalise(q["text"]) in v.normalise(kb.document(q["document"]).text)
    # Every belief in the bank still rests on quotes the knowledge base holds: none is left out.
    assert not [w for w in brief["warnings"] if w.startswith("Belief")], brief["warnings"]
    assert brief["season"]["name"] == "engagement_lead_up" and brief["mix"] == {"ATTRACT": 1, "WARM": 3, "CONVERT": 1}
    offers = {o["offer"]: o for o in brief["live_offers"]}
    assert offers["Google Ads Audit Giveaway"]["status"] == "delivering" and not offers["Google Ads Audit Giveaway"]["sellable"]
    assert offers["ELEVATE"]["sellable"] and len(brief["priority_series"]) == 6
    assert brief["made_by"].startswith("system") and sb.check_hash(brief)
    assert committed() == brief, "deterministic: the same inputs and date make the same brief and hash"
    # After the giveaway's audits end, its calendar entry is no longer in force.
    later = sb.assemble(assemble("strategist", root=KB), root=KB, on=date(2026, 12, 1))
    assert "Google Ads Audit Giveaway" not in {o["offer"] for o in later["live_offers"]}


def test_the_rendered_brief_names_beliefs_offers_and_what_not_to_repeat():
    text = sb.render(committed())
    assert "B1 (" in text and "Do not make this point while it runs: A one-off ads audit is not enough to fix your ads" in text
    assert "delivering from 2026-10-19 to 2026-11-08" in text


# A constructed knowledge base with an invented offer calendar ----------------------------------------------------------------

def constructed(tmp_path, *, calendar=None, bank=None, published=None):
    docs = {**DOCS,
            "content_strategy": ("01-strategy.md", "Strategy", "Pillars.\n- We measure bookings, not clicks.\n- Stop chasing reach."),
            "offer_sheet": ("05-offers.md", "Offers", "- Retainer Offer: done for you.\n- Audit Offer: a free audit, closed."),
            "belief_statements": ("16-beliefs.md", "Beliefs", '- "A slow month is a system problem, not a season."'),
            "content_plan": ("14-plan.md", "Plan", "- Mix: mostly WARM, ATTRACT for reach, about one CONVERT.")}
    root = write_kb(tmp_path / "kb", docs)
    entries = bank or [
        {"id": "bookings", "stage": "WARM", "offers": ["Retainer Offer"], "belief": "We judge ads by bookings.",
         "quotes": [{"document": "content_strategy", "text": "We measure bookings, not clicks."}]},
        {"id": "reach", "stage": "ATTRACT", "offers": ["Retainer Offer"], "belief": "Reach is not the goal.",
         "quotes": [{"document": "content_strategy", "text": "Stop chasing reach."}]},
        {"id": "season", "stage": "CONVERT", "offers": ["Retainer Offer"], "belief": "A slow month is a system problem.",
         "quotes": [{"document": "belief_statements", "text": "A slow month is a system problem, not a season."}]},
        {"id": "audits", "stage": "WARM", "offers": ["Audit Offer"], "belief": "An audit shows the gaps.",
         "quotes": [{"document": "content_strategy", "text": "We measure bookings, not clicks."}]},
        {"id": "gone", "stage": "WARM", "offers": ["Retainer Offer"], "belief": "A line nobody wrote.",
         "quotes": [{"document": "belief_statements", "text": "This sentence is in no document."}]},
    ]
    (root / sb.BELIEFS_FILE).write_text(json.dumps({"entries": entries}), encoding="utf-8")
    (root / sb.CALENDAR_FILE).write_text(json.dumps({"entries": calendar if calendar is not None else [
        {"offer": "Retainer Offer", "status": "waitlist", "do_not_undercut": ["Hiring an agency is a waste of money"]},
        {"offer": "Audit Offer", "status": "delivering", "starts": "2026-10-20", "ends": "2026-11-08",
         "do_not_undercut": ["A one-off audit is not enough to fix your ads"], "terms": ["one-off audit"]}]}), encoding="utf-8")
    if published is not None:
        (root / "published-central-points.json").write_text(json.dumps({"entries": published}), encoding="utf-8")
    return root


def brief_of(root, on=ON):
    return sb.assemble(load_knowledge_base(root, stage="strategist"), root=root, on=on)


def test_beliefs_need_their_quotes_and_an_offer_on_sale(tmp_path):
    brief = brief_of(constructed(tmp_path))
    ids = [b["id"] for b in brief["beliefs_to_prove"]]
    assert set(ids) == {"bookings", "reach", "season"}
    assert any("gone left out" in w and "no longer in belief_statements" in w for w in brief["warnings"])
    assert any("audits left out" in w and "on sale" in w for w in brief["warnings"])
    assert any("Only 3 beliefs" in w for w in brief["warnings"]), "fewer than four is said, never padded"


def test_a_belief_proved_in_the_last_30_days_waits_and_an_older_proof_is_listed_as_do_not_repeat(tmp_path):
    published = [{"source_ref": "log#1", "published_on": "2026-10-10", "date_precision": "day", "channel": "Email",
                  "title": "Bookings, not clicks", "key_message": "We measure ads by bookings, not by clicks."},
                 {"source_ref": "log#2", "published_on": "2026-06-01", "date_precision": "day", "channel": "Reel",
                  "title": "Reach", "key_message": "Chasing reach is not a strategy; stop chasing reach."}]
    brief = brief_of(constructed(tmp_path, published=published))
    ids = [b["id"] for b in brief["beliefs_to_prove"]]
    assert "bookings" not in ids, "proved 17 days before the window: it waits (D23)"
    reach = next(b for b in brief["beliefs_to_prove"] if b["id"] == "reach")
    assert reach["last_proved"] == "2026-06-01" and reach["do_not_repeat"][0]["title"] == "Reach"


def test_on_a_constructed_offer_calendar_a_card_that_undercuts_a_live_offer_is_held_with_the_offer_named(tmp_path):
    brief = brief_of(constructed(tmp_path))
    undercut = {**v7_card(point="We tell owners a one-off audit is not enough, and here is what we do instead."),
                "moment_ids": ["moment_a"]}
    ledger = v.verify_card(undercut, SCENES, ROSTER, [], strategy_brief=brief)
    flags = [f for f in ledger["flags"] if f["kind"] == "offer_undercut"]
    assert len(flags) == 1 and flags[0]["severity"] == v.BLOCK and flags[0]["offer"] == "Audit Offer"
    assert "Undercuts Audit Offer (delivering until 2026-11-08)" in flags[0]["message"]
    hold = sb.hold_for(ledger["flags"])
    assert hold == {"until": "2026-11-09", "reason_code": "timing", "offers": ["Audit Offer"], "author": "system: strategy brief",
                    "note": "Held by the strategy brief: the card undercuts Audit Offer while it runs"}
    # The same point by shared words, without the listed term, on another field.
    by_words = {**v7_card(why_it_matters="Hiring an agency is a waste of money, owners say."), "moment_ids": ["moment_a"]}
    assert [f["offer"] for f in v.verify_card(by_words, SCENES, ROSTER, [], strategy_brief=brief)["flags"]
            if f["kind"] == "offer_undercut"] == ["Retainer Offer"]
    # A card that undercuts nothing raises nothing, and without a brief nothing is checked.
    clean = {**v7_card(), "moment_ids": ["moment_a"]}
    assert not [f for f in v.verify_card(clean, SCENES, ROSTER, [], strategy_brief=brief)["flags"] if f["kind"] == "offer_undercut"]
    assert sb.hold_for(v.verify_card(undercut, SCENES, ROSTER, [])["flags"]) is None
    # After the window, the audit point is no longer held.
    after = brief_of(constructed(tmp_path / "later"), on=date(2026, 11, 20))
    assert not [f for f in v.verify_card(undercut, SCENES, ROSTER, [], strategy_brief=after)["flags"] if f["kind"] == "offer_undercut"]


def test_the_calendar_and_the_bank_are_checked(tmp_path):
    root = constructed(tmp_path, calendar=[{"offer": "Unknown Offer", "status": "open", "do_not_undercut": []}])
    brief = brief_of(root)
    assert any("Unknown Offer" in w and "offer sheet" in w for w in brief["warnings"])
    bad = constructed(tmp_path / "bad", calendar=[{"offer": "Retainer Offer", "status": "half open"}])
    with pytest.raises(ValueError, match="unknown status"):
        brief_of(bad)
    (root / sb.BELIEFS_FILE).unlink()
    (root / sb.CALENDAR_FILE).unlink()
    empty = brief_of(root)
    assert empty["beliefs_to_prove"] == [] and empty["live_offers"] == [] and len(empty["warnings"]) >= 2


def test_an_offer_status_changed_in_the_app_overrides_the_calendar_file():
    """Phase N10: an offer that opens, closes or moves to a waitlist is a settings line, not a file edit and a deployment."""
    from backend_pipeline.cycle.strategy_brief import with_changes
    calendar = {"entries": [{"offer": "ELEVATE", "status": "waitlist", "do_not_undercut": ["Agencies are a waste"], "terms": []},
                            {"offer": "Audit Giveaway", "status": "delivering", "ends": "2026-11-08",
                             "do_not_undercut": ["An audit is not enough"], "terms": ["one-off audit"]}]}
    changed, warnings = with_changes(calendar, ["ELEVATE: open", "Audit Giveaway: closed", "Holiday Workshop: open until 2026-12-01",
                                                "not a line"])
    by = {e["offer"]: e for e in changed["entries"]}
    assert by["ELEVATE"]["status"] == "open" and by["ELEVATE"]["do_not_undercut"] == ["Agencies are a waste"]
    assert by["Audit Giveaway"]["status"] == "closed" and by["Audit Giveaway"]["do_not_undercut"] == [] and "ends" not in by["Audit Giveaway"]
    assert by["Holiday Workshop"]["ends"] == "2026-12-01" and by["Holiday Workshop"]["source"].startswith("offers.status")
    assert warnings == ["An offer status line was not understood and was left out: 'not a line'"]
    assert with_changes(calendar, ())[0] is calendar, "no change, the file as it is"
