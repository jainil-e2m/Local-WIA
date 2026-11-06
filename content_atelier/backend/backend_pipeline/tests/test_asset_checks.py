"""E.B24's extension: every check that enforces section 4.3 on a v4 brief's assets, each with a failing and a passing case.

The failing lines are the constructions WIA's team rejected (the 20 October diagnosis and the 21 October findings, which
quote them); the passing lines are copy WIA accepted in the 20 October packs or wrote herself. Short lines with no name,
venue or figure (R48). Blocking only where the plan marks it: outcome verbs and hook fidelity."""
from __future__ import annotations

import copy

import pytest

from backend_pipeline.briefs import asset_checks
from backend_pipeline.briefs.asset_checks import asset_findings, week_findings
from backend_pipeline.briefs.first_touch import load_data, offer_descriptors
from backend_pipeline.tests.brief_v4_fixtures import caption, v4_body

def turn(speaker, said, at_ms=None, role=None):
    # A synthetic turn, built here so the file holds no transcript-shaped JSON (R48, test_client_material_guard).
    return {"speaker": speaker, "excerpt": f"{speaker}: {said}", "start_ms": at_ms, **({"role": role} if role else {})}


PACKET = {"approved_angle": {"title": "How we read follow-up", "core_perspective": "Follow-up shapes lead quality."},
          "card": {"pillar": "WARM"}, "evidence": [turn("Strategist", "How do you answer a new inquiry today?", 1000, role="anchor")]}
ROSTER = [{"name": "Our Strategist", "role": "strategist", "status": "current", "aliases": ["Strategist"]}]


def base():
    return v4_body(PACKET)


def run(b, **kw):
    kw.setdefault("pillar", "WARM")
    return asset_findings(b, **kw)


def of(findings, check):
    return [f for f in findings if f["check"] == check]


def test_the_fixture_raises_no_asset_finding():
    assert run(base()) == []


def with_caption(b, i, hook=None, body=None, ending=None):
    c = b["format_plan"]["reels"][i]["caption"]
    b["format_plan"]["reels"][i]["caption"] = {**c, **{k: v for k, v in (("hook", hook), ("body", body), ("ending", ending)) if v}}
    return b


# Outcome verbs against the evidence (blocking) ------------------------------------------------------------------------

def test_an_outcome_the_call_does_not_show_blocks():
    said = turn("Strategist", "The new campaign brought in four good leads in the first week.")
    b = with_caption(base(), 0, body="Her new campaign booked four weddings in its first week.")
    flagged = of(run(b, evidence=[said]), "copy.outcome_verbs")
    assert flagged and flagged[0]["severity"] == "blocking"
    passing = with_caption(base(), 0, body="Her new campaign brought in four good leads in its first week.")
    assert not of(run(passing, evidence=[said]), "copy.outcome_verbs")
    assert not of(run(b), "copy.outcome_verbs"), "without a dossier there is nothing to check against"


# A self-audit last line, the takeaway test and DIY drift --------------------------------------------------------------

def test_a_self_audit_last_line_is_flagged():
    b = with_caption(base(), 0, ending="Take a look at what you've been asking Meta to find.")
    assert of(run(b), "copy.self_audit")
    passing = with_caption(base(), 0, ending="Budget should follow the proof.")
    assert not of(run(passing), "copy.self_audit")


def test_an_ending_that_tells_the_reader_what_to_do_fails_the_takeaway_test():
    b = with_caption(base(), 1, ending="You should check your follow-up before you raise your budget.")
    assert of(run(b), "copy.takeaway")
    assert not of(run(with_caption(base(), 1, ending="More budget should be something your ads earn.")), "copy.takeaway")


def test_how_to_steps_on_any_asset_are_diy_drift():
    b = with_caption(base(), 2, body="First, turn off your retargeting campaigns. Then set your budget to half.")
    assert of(run(b), "copy.diy_drift")
    passing = with_caption(base(), 2, body="We turned off the campaign that was spending the most, before the call was over.")
    assert not of(run(passing), "copy.diy_drift")


# Aphoristic kickers --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("kicker", [
    "Meta is great at following instructions. Somebody has to write good ones.",
    "But a click isn't an inquiry. And it's definitely not a booking.",
    "None of that replaces her. It keeps her in the conversation.",
    "It's automated, but it's still her.",
])
def test_an_aphoristic_kicker_closing_a_paragraph_is_flagged(kicker):
    b = with_caption(base(), 0, body="We rebuilt the follow-up around her calendar. " + kicker)
    assert of(run(b), "copy.kicker")


@pytest.mark.parametrize("line", [
    "You'd never see that in an ads report. But it changed what we built for her.",
    "She can't add tour times. Saturdays are weddings, and her team is small.",
    "It's automated, but every message still sounds and looks like her.",
])
def test_a_story_beat_or_a_plain_closing_is_not_a_kicker(line):
    assert not of(run(with_caption(base(), 0, body="We rebuilt the follow-up around her calendar. " + line)), "copy.kicker")


# Detail density ------------------------------------------------------------------------------------------------------

def test_more_than_three_operational_details_in_one_story_is_flagged():
    heavy = ("Her daily budget was cut to about half, a retargeting audience of 45 days was paused, and the cost per lead "
             "dropped once tracking was fixed.")
    assert of(run(with_caption(base(), 0, body=heavy)), "copy.detail_density")
    light = "We brought her budget down to about half and started a fresh campaign."
    assert not of(run(with_caption(base(), 0, body=light)), "copy.detail_density")


# Sibling overlap -----------------------------------------------------------------------------------------------------

def test_siblings_repeating_a_sentence_are_flagged_and_a_subject_may_repeat_the_anchor_hook():
    line = "One of the first things we did for a new venue client this summer was lower her ad budget."
    b = base()
    b["format_plan"]["reels"][0]["script"] = line + " Here's why."
    b["format_plan"]["email"]["body"] = line + "\n\nMore follows."
    flagged = of(run(b), "copy.sibling_overlap")
    assert flagged and flagged[0]["severity"] == "warning"
    allowed = base()
    hook = "Why we lowered a new client's ad budget before launching anything new"
    allowed["format_plan"]["reels"][0]["on_screen_hook"] = hook
    allowed["format_plan"]["email"]["subject_options"][0] = hook
    assert not of(run(allowed), "copy.sibling_overlap")


# CTA patterns she never uses -------------------------------------------------------------------------------------------

def test_a_cta_she_never_uses_is_flagged():
    assert of(run(with_caption(base(), 0, ending="Follow along for more.")), "copy.never_used_cta")
    assert not of(run(with_caption(base(), 0, ending="If you want that kind of support, DM me \"ADS.\"")), "copy.never_used_cta")


# Hook fidelity against the ledger (blocking unless attested) ---------------------------------------------------------

def test_a_hook_saying_a_tool_did_more_than_the_call_shows_blocks_unless_attested():
    said = turn("Prospect", "My AI assistant helped me set up my Google Ads.")
    b = base()
    b["format_plan"]["email"]["subject_options"][0] = "Her AI assistant ran her Google Ads for a month"
    flagged = of(run(b, evidence=[said]), "copy.hook_fidelity")
    assert flagged and flagged[0]["severity"] == "blocking"
    assert not of(run(b, evidence=[said], attested=["Her AI assistant ran her Google Ads for a month."]), "copy.hook_fidelity")
    b["format_plan"]["email"]["subject_options"][0] = "Her AI assistant set up her Google Ads"
    assert not of(run(b, evidence=[said]), "copy.hook_fidelity")


def test_a_hook_crediting_wia_with_a_decision_the_client_raised_blocks():
    turns = [turn("Strategist", "How do you feel about your budget right now?", 1000),
             turn("Owner", "Honestly I'd love to lower it, it keeps going up.", 2000),
             turn("Strategist", "So we'll lower it to about half and start fresh.", 3000)]
    b = base()
    b["narrative_outline"]["hooks"][0]["text"] = "Our first recommendation was to lower her budget."
    flagged = of(run(b, evidence=turns, roster=ROSTER), "copy.hook_fidelity")
    assert flagged and flagged[0]["severity"] == "blocking" and flagged[0]["field"] == "narrative_outline.hooks[0].text"
    b["narrative_outline"]["hooks"][0]["text"] = "We lowered her budget before launching anything new."
    assert not of(run(b, evidence=turns, roster=ROSTER), "copy.hook_fidelity")


def test_a_hook_saying_how_much_of_a_call_something_took_is_a_persons_check():
    b = base()
    b["format_plan"]["reels"][0]["on_screen_hook"] = "We spent most of that call talking about her ads"
    flagged = of(run(b), "copy.hook_fidelity")
    assert [f["severity"] for f in flagged] == ["warning"]


# The email: send header and no bullet lists ---------------------------------------------------------------------------

def test_the_email_needs_its_send_header_and_no_bullet_lists():
    b = base()
    b["format_plan"]["email"]["send_header"]["date"] = " "
    b["format_plan"]["email"]["body"] = "What we built:\n- a welcome video\n- a selfie in the confirmation"
    found = run(b)
    assert of(found, "format.send_header") and of(found, "format.email_bullets")


# Captions: -Whitney on first-person captions ----------------------------------------------------------------------------

def test_a_first_person_caption_ends_with_whitney():
    b = with_caption(base(), 0, body="I had a discovery call this summer that stayed with me.", ending="DM me \"ADS.\"")
    assert of(run(b), "format.caption_signoff")
    signed = with_caption(base(), 0, body="I had a discovery call this summer that stayed with me.", ending="DM me \"ADS.\"\n\n-Whitney")
    assert not of(run(signed), "format.caption_signoff")
    question = with_caption(base(), 0, body="Is it the campaign, or is it something I did?")
    assert not of(run(question), "format.caption_signoff"), "the reader's own question is not Whitney speaking"


# The carousel's CTA for both readers ---------------------------------------------------------------------------------

def test_the_carousel_cta_speaks_to_both_readers():
    b = base()
    b["format_plan"]["carousel"]["slides"][-1]["text"] = "DM us \"ADS\" and let's talk."
    assert of(run(b), "format.carousel_cta")
    assert not of(run(base()), "format.carousel_cta")
    # Both readers named in the third person, as the pack finisher wrote N4's carousel on production, are both readers.
    third = base()
    third["format_plan"]["carousel"]["slides"][-2]["text"] = "We believe understanding an owner's vision belongs with accuracy."
    third["format_plan"]["carousel"]["slides"][-1]["text"] = ("Some venue owners want us to manage their ads for them.\nOthers want us to "
                                                             "launch their campaigns and guide them while they run them.")
    assert not of(run(third), "format.carousel_cta")
    one = base()
    one["format_plan"]["carousel"]["slides"][-2]["text"] = "We believe understanding an owner's vision belongs with accuracy."
    one["format_plan"]["carousel"]["slides"][-1]["text"] = "Some venue owners want us to manage their ads for them."
    assert of(run(one), "format.carousel_cta")


# The offer descriptor on CONVERT assets --------------------------------------------------------------------------------

def test_the_offer_descriptors_file_names_its_purpose_source_and_offers():
    data = load_data("offer-descriptors.json")
    assert data["purpose"] and data["source"] and {o["offer"] for o in data["offers"]} >= {"ELEVATE", "Ads Accelerators", "LeadLock"}
    assert offer_descriptors({"offer_descriptors": {"offers": []}}) == [], "a brief reads the descriptors it pinned"


def test_a_convert_asset_naming_an_offer_carries_its_descriptor():
    b = with_caption(base(), 0, body="That's what our Ads Accelerators were built for.")
    assert of(run(b, pillar="CONVERT"), "format.offer_descriptor")
    assert not of(run(b, pillar="WARM"), "format.offer_descriptor"), "the check is for CONVERT assets"
    described = with_caption(base(), 0, body="That's what our Ads Accelerators were built for: we launch your campaigns, then guide "
                                               "you while you run them.")
    described["format_plan"]["reels"][0]["offer_descriptor"] = "we launch your campaigns, then guide you while you run them"
    assert not of(run(described, pillar="CONVERT"), "format.offer_descriptor")
    member = with_caption(base(), 0, body="We met with one of our Accelerator members recently.")
    assert not of(run(member, pillar="CONVERT"), "format.offer_descriptor"), "a member is not the offer named as the solution"


# Register by format --------------------------------------------------------------------------------------------------

def test_register_scripts_are_spoken_and_emails_and_captions_are_not():
    b = base()
    b["format_plan"]["reels"][0]["script"] = "Okay, so here is what happened with a new client this summer."
    b["format_plan"]["reels"][1]["register"] = "on_screen"
    b["format_plan"]["email"]["body"] = "So, um, you guys know how this goes, right?"
    written = ("When a new client comes to us we do not begin with the question of how much more they could be spending "
               "because the first thing that we look at is what their current budget is already doing for them and whether "
               "each campaign has been given a job that it is able to do")
    b["format_plan"]["reels"][2]["kind"] = "stance"
    b["format_plan"]["reels"][2]["register"] = "spoken"
    b["format_plan"]["reels"][2]["script"] = written
    messages = [f["message"] for f in of(run(b), "format.register")]
    assert any("Okay, so" in m for m in messages) and any("register is spoken" in m for m in messages)
    assert any("spoken filler" in m for m in messages) and any("reads as written" in m for m in messages)
    assert not of(run(base()), "format.register")


# The Reel set (D30) ----------------------------------------------------------------------------------------------------

def test_the_reel_set_is_the_story_then_other_doors_and_two_reels_are_allowed():
    two = base()
    two["format_plan"]["reels"] = two["format_plan"]["reels"][:2]
    assert not of(run(two), "format.reels"), "two Reels when the idea does not support three (D30)"
    same = base()
    same["format_plan"]["reels"][1]["kind"] = "story"
    assert of(run(same), "format.reels")
    many = base()
    many["format_plan"]["reels"][2]["screens"] = ["One.", "Two.", "Three.", "Four."]
    assert of(run(many), "format.reels")
    one = base()
    one["format_plan"]["reels"] = one["format_plan"]["reels"][:1]
    assert of(run(one), "format.reels")


# Across the cycle's briefs -------------------------------------------------------------------------------------------

def sibling(cover="Why your budget should follow the proof", cta=False):
    b = base()
    for i, text in enumerate((cover, "Questions that aren't about ads", "Ads amplify what is already there")):
        b["format_plan"]["reels"][i]["cover_text"] = text
    if cta:
        b["format_plan"]["reels"][0]["caption"]["ending"] = "If you want that kind of support, DM me \"ADS.\""
    return {"brief_id": "brief_other", "title": "Another idea", "body": b}


def test_one_offer_cta_a_week_on_instagram():
    mine = with_caption(base(), 0, ending="If you want that kind of support, DM me \"ADS.\"")
    assert of(week_findings(mine, [sibling(cta=True)]), "week.offer_cta")
    assert not of(week_findings(mine, [sibling()]), "week.offer_cta")


def test_covers_are_distinct_across_the_week():
    assert of(week_findings(base(), [sibling(cover="The question we ask before touching your ads")]), "week.covers")
    assert not of(week_findings(base(), [sibling()]), "week.covers")


def test_every_check_is_named_in_the_module_doc():
    names = {"outcome", "self-audit", "sibling overlap", "kickers", "detail density", "hook fidelity", "takeaway", "DIY drift",
             "send header", "-Whitney", "both DIY and done-for-you", "offer descriptor", "register", "never uses", "one offer CTA"}
    doc = asset_checks.__doc__
    assert all(n in doc for n in names), [n for n in names if n not in doc]
    assert copy.deepcopy(caption("a", "b", "c")) == {"hook": "a", "body": "b", "ending": "c"}


def test_e_b24_decided_the_house_rules_block_and_the_readings_stay_warnings():
    """Phase N6: bullets in the email, an unsigned first-person caption and a CTA she never uses block; the send header (a
    proposal WIA confirms) stays a warning."""
    b = with_caption(base(), 0, body="I had a discovery call this summer that stayed with me.", ending="Follow along for more.")
    b["format_plan"]["email"]["send_header"]["date"] = " "
    b["format_plan"]["email"]["body"] = "What we built:\n- a welcome video\n- a selfie in the confirmation"
    found = run(b)
    assert {f["severity"] for f in of(found, "format.email_bullets")} == {"blocking"}
    assert {f["severity"] for f in of(found, "format.caption_signoff")} == {"blocking"}
    assert {f["severity"] for f in of(found, "copy.never_used_cta")} == {"blocking"}
    assert {f["severity"] for f in of(found, "format.send_header")} == {"warning"}
