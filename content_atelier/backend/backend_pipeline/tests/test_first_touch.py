"""E.B34: WIA's corrections as rules, her text as the tests (R60; plan section 4.3, first-touch rules 1 to 5).

Each of Whitney's notes of 20 October on the v2 packs (W3 to W8) and of 13 October (the subject line and slide 1) is a case
the checks flag on the text she corrected and pass on her corrected text. The lines below are first-touch copy without a
name, venue or figure (R48); the whole v2 pack document is read from `research/` when it is there, and that test is skipped
when it is not. Where Whitney named the fix without wording it (W3, W4, W8's cover), the passing line applies her note.
None of this text is in a prompt or an exemplar (D28)."""
from __future__ import annotations

import copy

import pytest

from backend_pipeline.briefs import first_touch
from backend_pipeline.briefs.first_touch import first_touch_findings, insider_terms, load_data, pinned_data
from backend_pipeline.briefs.pack_markdown import check_packs, parse_packs
from backend_pipeline.config import PROJECT_ROOT
from backend_pipeline.tests.brief_v4_fixtures import v4_body

def turn(speaker, said, at_ms=None, role=None):
    # A synthetic turn, built here so the file holds no transcript-shaped JSON (R48, test_client_material_guard).
    return {"speaker": speaker, "excerpt": f"{speaker}: {said}", "start_ms": at_ms, **({"role": role} if role else {})}


PACKET = {"approved_angle": {"title": "How we read follow-up", "core_perspective": "Follow-up shapes lead quality."},
          "card": {"pillar": "CONVERT"}, "evidence": [turn("Strategist", "How do you answer a new inquiry today?", 1000, role="anchor")]}
V2_PACKS = PROJECT_ROOT / "research" / "v2-reassessment-2026-10-20" / "packs" / "WIA-Content-Packs-Week-of-8-14-June-2026-v2.md"
# W8: the fact Whitney stated on 20 October, as an approver attests it at a gate (5.B7).
W8_FACT = ("Her AI assistant was plugged into her Google Ads account and made the changes itself; she had no idea what it "
           "had changed.")


def body(**plan_changes):
    b = v4_body(PACKET)
    plan = b["format_plan"]
    for path, value in plan_changes.items():
        node, *rest = path.split("__")
        target = plan[node]
        keys = [int(k) if k.isdigit() else k for k in rest]
        for k in keys[:-1]:
            target = target[k]
        if keys:
            target[keys[-1]] = value
        else:
            plan[node] = value
    return b


def checks(b, **kw):
    return first_touch_findings(b, terms=insider_terms(), **kw)


def found(findings, check, field=None):
    return [f for f in findings if f["check"] == check and (field is None or f["field"] == field)]


def test_the_fixture_passes_every_first_touch_rule():
    assert checks(v4_body(PACKET)) == []


# (a) Subject lines ---------------------------------------------------------------------------------------------------

def test_w3_a_subject_narrating_what_a_third_party_did_is_flagged():
    flagged = checks(body(email__subject_options=["She used AI to set up her Google Ads", "When your ads stop working"]))
    assert found(flagged, "first_touch.subject", "format_plan.email.subject_options[0]")
    # W3 named the problem, not the wording; her 13 October rule ("the problem than the process") is the fix.
    fixed = checks(body(email__subject_options=["Your ads were working. Then they stopped.", "When your ads stop working"]))
    assert not found(fixed, "first_touch.subject")


def test_13_october_a_subject_about_the_process_is_flagged_and_her_line_passes():
    flagged = checks(body(email__subject_options=["More inquiries? Here's what we look at next", "When more inquiries aren't enough"]))
    assert [f["field"] for f in found(flagged, "first_touch.subject")] == ["format_plan.email.subject_options[0]"]
    # W2: a subject stating WIA's counter-expected decision passes too.
    passing = checks(body(email__subject_options=["When more inquiries aren't enough", "Why we lowered a new client's ad budget"]))
    assert not found(passing, "first_touch.subject")


# (b) Slide 1 ---------------------------------------------------------------------------------------------------------

def carousel(title, slide_one):
    c = copy.deepcopy(v4_body(PACKET)["format_plan"]["carousel"])
    c["title"], c["slides"][0]["text"] = title, slide_one
    return c


def test_w4_a_bare_quote_on_slide_one_is_flagged_and_the_title_tied_in_passes():
    title = "The part of your ads AI can't do for you"
    quote = '"I don\'t know what I\'ve done. I don\'t know what we changed."\nA wedding pro said that to us this summer.'
    flagged = found(checks(body(carousel=carousel(title, quote))), "first_touch.slide_one")
    assert {"bare quote" in f["message"] for f in flagged} == {True, False}, "a bare quote, and the title's promise missing"
    tied = "The part of your ads AI can't do for you.\n" + quote
    assert not found(checks(body(carousel=carousel(title, tied))), "first_touch.slide_one")


def test_13_october_slide_one_opening_on_good_news_is_flagged_and_her_problem_led_line_passes():
    title = "What we investigate when more inquiries aren't turning into attended tours"
    good_news = ("More inquiries. More tours booked.\nSo why are some couples still disappearing before they visit?\n"
                 "Here's what we look at when that question comes up in a client review.")
    flagged = found(checks(body(carousel=carousel(title, good_news))), "first_touch.slide_one")
    assert flagged and "good news" in flagged[0]["message"]
    hers = ("When more inquiries and more tours still aren't moving the needle...\nOur ads were bringing one of our venue owners "
            "more of both. But there was another layer we needed to dig into with her.")
    assert not found(checks(body(carousel=carousel(title, hers))), "first_touch.slide_one")


# (c) Specific --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(("field", "before", "after"), [
    ("reels__0__cover_text", "Something's working, and then it stops", "Your ads are working, and then they stop"),   # W5
    ("reels__1__cover_text", "Did I set this up wrong?", "Did I set my ads up wrong?"),                                # W7
    ("reels__2__cover_text", "What changed?", "What changed in her Google Ads?"),                                      # W8
    ("reels__1__on_screen_hook", "Did I set this up wrong?", "Did I set my ads up wrong?"),
    ("reels__2__screens__0", "She changed a few things.", "She set up her own Google Ads."),
])
def test_w5_w7_w8_first_touch_text_names_its_concrete_subject(field, before, after):
    flagged = found(checks(body(**{field: before})), "first_touch.specific")
    assert len(flagged) == 1 and before[:20] in flagged[0]["message"]
    assert not found(checks(body(**{field: after})), "first_touch.specific")


def test_specificity_is_never_traded_for_distinctness():
    # Two covers naming the same subject are both specific; nothing asks the second to drop "ads" to differ.
    b = body(reels__0__cover_text="Your ads are working, and then they stop", reels__1__cover_text="Did I set my ads up wrong?")
    assert not found(checks(b), "first_touch.specific")


# (d) Insider terms ---------------------------------------------------------------------------------------------------

def test_the_insider_terms_file_names_its_purpose_source_and_office_hours():
    data = load_data(first_touch.INSIDER_TERMS)
    assert data["purpose"] and data["source"] and data["version"]
    assert any(t["term"] == "office hours" for t in data["terms"])
    assert pinned_data()["insider_terms"] == data


def test_w6_office_hours_on_a_hook_and_twice_in_a_script_is_flagged():
    hook = "One of our members brought one question to office hours: did I set this up wrong?"
    script = ("One of our members came to Google Ads office hours with one question. That's exactly what office hours are for. "
              "That's what our members get from office hours.")
    flagged = checks(body(reels__1__on_screen_hook=hook, reels__1__script=script))
    blocking = [f for f in found(flagged, "first_touch.insider_term") if f["severity"] == "blocking"]
    assert {f["field"] for f in blocking} == {"format_plan.reels[1].on_screen_hook", "format_plan.reels[1].script"}
    # Her correction: the term stays off the hook and is "sprinkled in" the script once, explained.
    hers = ("We met with one of our Accelerator members recently. He brought one question to his weekly call with our experts, "
            "in office hours, where we look at your own account with you: did I set my ads up wrong?")
    fixed = checks(body(reels__1__on_screen_hook="We met with one of our Accelerator members recently", reels__1__script=hers))
    assert not found(fixed, "first_touch.insider_term")


def test_one_unexplained_use_in_a_body_is_a_warning():
    flagged = found(checks(body(**{"reels__0__caption": {"hook": "A member asked us something.", "body": "He brought it to office hours.",
                                                          "ending": "We loved it."}})), "first_touch.insider_term")
    assert [f["severity"] for f in flagged] == ["warning"]


def test_an_offer_name_is_not_an_insider_term():
    b = body(email__subject_options=["What the Ads Accelerators are for", "When your ads stop working"])
    assert not found(checks(b), "first_touch.insider_term")


# (e) Who did what ----------------------------------------------------------------------------------------------------

def test_w8_a_beat_crediting_the_client_with_what_her_ai_did_is_flagged_against_the_attested_fact():
    screens = ["A wedding pro used her own AI assistant to set up her Google Ads.",
               "Four good leads in the first week. Then she changed a few things.", "She didn't know what had changed."]
    flagged = found(checks(body(reels__2__screens=screens), attested=[W8_FACT]), "first_touch.who_did_what")
    assert [f["field"] for f in flagged] == ["format_plan.reels[2].screens[1]"] and flagged[0]["severity"] == "blocking"
    hers = [screens[0], "Four good leads in the first week. Then the AI assistant made a few changes.",
            "\"I don't know what changed, and it isn't working.\""]
    assert not found(checks(body(reels__2__screens=hers), attested=[W8_FACT]), "first_touch.who_did_what")


def test_who_did_what_reads_the_call_when_nothing_is_attested_and_an_attestation_overrides_it():
    said = turn("Prospect", "I had to go in and optimize it, and then I changed a few campaigns.")
    screens = ["Her Google Ads were working.", "Then her AI assistant made a few changes.", "Nothing was coming in."]
    flagged = found(checks(body(reels__2__screens=screens), evidence=[said]), "first_touch.who_did_what")
    assert flagged and "the call has the client doing it" in flagged[0]["message"]
    assert not found(checks(body(reels__2__screens=screens), evidence=[said], attested=[W8_FACT]), "first_touch.who_did_what")


def test_the_offers_close_is_not_a_story_beat():
    # N11's benchmark pack: the offers' close was blocked as crediting the client with running (and, against another call,
    # our team with managing), though it says what owners may want, not what anyone in the story did.
    roster = [{"aliases": ["Strategist"], "status": "current"}]
    ours = turn("Strategist", "We have been running these keywords since the launch, and we run the reporting monthly.")
    close = ("Some owners want a team to manage their ads.\nOthers want us to launch their campaigns and guide them while "
             "they run them.")
    slides = [close, "Her ads were working.", "Then she ran them herself."]
    flagged = found(checks(body(reels__2__screens=slides), evidence=[ours], roster=roster), "first_touch.who_did_what")
    assert [f["field"] for f in flagged] == ["format_plan.reels[2].screens[2]"], "the story's own beat is still read"
    hers = turn("Owner", "I ran the ads myself for two years before this.")
    assert not found(checks(body(reels__2__screens=[close, "Her ads were working.", "We built the page."]), evidence=[hers],
                            roster=roster), "first_touch.who_did_what"), "nor the close's managing team, nor the fixture's"


def test_a_line_to_the_reader_about_the_offer_is_not_a_story_beat():
    # N11's second benchmark pack: the offer sheet says WIA sets the follow-up system up, the copy says so to the reader, and
    # the client had said on the call that nothing was set up for her texts.
    roster = [{"aliases": ["Strategist"], "status": "current"}]
    hers = turn("Owner", "We don't really have an SMS set up for the post tour sequence.")
    offer = "Inside it, we set up the follow-up system around your own conversations. You run the platform."
    assert not found(checks(body(email__body=offer), evidence=[hers], roster=roster), "first_touch.who_did_what")
    ours = turn("Strategist", "I set up the texts for the tour sequence last week.")
    story = ["Her tours were up.", "Then she set up the texts herself.", "We want follow-up to fit."]
    flagged = found(checks(body(reels__2__screens=story), evidence=[ours], roster=roster), "first_touch.who_did_what")
    assert [f["field"] for f in flagged] == ["format_plan.reels[2].screens[1]"], "a beat in the third person is still read"


def test_attested_facts_are_read_from_the_ledger_entries_and_context_items():
    ledger = {"text": W8_FACT, "status": "attested", "field": "context_items",
              "attested": {"kind": "attested_fact", "context_id": "c1", "by": "approver@example.com", "on": "2026-10-20"}}
    item = {"id": "c2", "kind": "attested_fact", "text": W8_FACT, "author": "approver@example.com", "created_at": "2026-10-20"}
    copy_line = {**ledger, "field": "format_plan.reels[3].screens[1]"}
    assert len(first_touch.attested_texts([ledger, item, copy_line, {"kind": "context", "text": "A note"}])) == 2


# The v2 packs, whole --------------------------------------------------------------------------------------------------

W_CODES = {  # (pack, check, field) -> the note of 20 October it is
    (3, "first_touch.subject", "format_plan.email.subject_options[0]"): "W3",
    (3, "first_touch.slide_one", "format_plan.carousel.slides[0].text"): "W4",
    (3, "first_touch.specific", "format_plan.reels[0].cover_text"): "W5",
    (3, "first_touch.specific", "format_plan.reels[1].cover_text"): "W7",
    (3, "first_touch.specific", "format_plan.reels[1].on_screen_hook"): "W6",
    (3, "first_touch.specific", "format_plan.reels[2].cover_text"): "W8",
}


def w_code(pack, f):
    if f["check"] == "first_touch.insider_term" and pack == 3:
        return "W6"
    if f["check"] == "first_touch.who_did_what" and pack == 3:
        return "W8"
    return W_CODES.get((pack, f["check"], f["field"]))


@pytest.mark.skipif(not V2_PACKS.is_file(), reason="The v2 packs live under research/ (R48); not in this checkout")
def test_the_v2_packs_raise_every_note_w3_to_w8_and_no_other_first_touch_or_blocking_finding():
    packs = parse_packs(V2_PACKS.read_text(encoding="utf-8"))
    assert [p["pillar"] for p in packs] == ["ATTRACT", "WARM", "CONVERT"]
    results = check_packs(packs, attested={3: [W8_FACT]})
    named = {w_code(n, f) for n, fs in results.items() for f in fs} - {None}
    assert named == {"W3", "W4", "W5", "W6", "W7", "W8"}
    # Every first-touch finding and every blocking finding is one of her notes; the asset checks' warnings are reported
    # (scripts/pack_checks.py) and are not her notes.
    stray = [(n, f["check"], f["field"]) for n, fs in results.items() for f in fs
             if (f["check"].startswith("first_touch.") or f["severity"] == "blocking") and not w_code(n, f)]
    assert stray == []
    # Packs 1 and 2 drew no note from her, and no first-touch finding here.
    assert not [f for n in (1, 2) for f in results[n] if f["check"].startswith("first_touch.")]


@pytest.mark.skipif(not V2_PACKS.is_file(), reason="The v2 packs live under research/ (R48); not in this checkout")
def test_the_v2_pack_with_her_corrections_applied_passes_the_first_touch_rules():
    text = V2_PACKS.read_text(encoding="utf-8")
    pack = parse_packs(text)[2]
    plan = pack["body"]["format_plan"]
    plan["email"]["subject_options"] = ["Your ads were working. Then they stopped."]
    plan["carousel"]["slides"][0]["text"] = plan["carousel"]["title"] + ".\n" + plan["carousel"]["slides"][0]["text"]
    plan["reels"][0]["cover_text"] = "Your ads are working, and then they stop"
    plan["reels"][1]["cover_text"] = "Did I set my ads up wrong?"
    plan["reels"][1]["on_screen_hook"] = "We met with one of our Accelerator members recently. His question: did I set my ads up wrong?"
    plan["reels"][2]["cover_text"] = "What changed in her Google Ads?"
    plan["reels"][2]["screens"][1] = "Four good leads in the first week. Then the AI assistant made a few changes."
    left = first_touch_findings(pack["body"], terms=insider_terms(), attested=[W8_FACT])
    assert not [f for f in left if f["check"] in ("first_touch.subject", "first_touch.slide_one", "first_touch.specific")]
    assert [f for f in left if f["check"] == "first_touch.who_did_what"], "the same beat in the other assets still needs her fact"


def test_pack_parsing_needs_no_research_file():
    text = ("# Pack 1 · WARM\n\n## Content angle\n\n### How we read follow-up\n\n## Email\n\n**DATE:** Tuesday\n**SEND TIME:** 9am\n"
            "**RECIPIENTS:** all\n**SUBJECT:** When more inquiries aren't enough\n**PREVIEW TEXT:** It starts after.\n\nHi {{contact.first_name}},\n\n"
            "Opening.\n\nBody one.\n\nBody two.\n\nReply and tell me.\n\nTalk soon,\nWhitney\n\n---\n\n## Reel 1: The story\n\n"
            "**Format:** face to camera (story)\n**Cover:** Your ads are working\n**On-screen hook:** Your ads are working\n\n"
            "**Script:**\n\nLine one.\n\n**Caption:**\n\nHook.\n\nBody.\n\nEnd.\n\n---\n\n## Carousel: When more inquiries aren't enough\n\n"
            "**Slide 1**\nWhen more inquiries aren't enough.\n\n**Slide 2**\nTwo.\n\n*For a CONVERT week, add:* DM us.\n\n**Caption:**\n\nHook.\n\nEnd.\n")
    pack = parse_packs(text)[0]
    plan = pack["body"]["format_plan"]
    assert plan["email"]["send_header"] == {"date": "Tuesday", "send_time": "9am", "recipients": "all"}
    assert plan["reels"][0]["kind"] == "story" and plan["reels"][0]["caption"]["hook"] == "Hook."
    assert [s["text"] for s in plan["carousel"]["slides"]] == ["When more inquiries aren't enough.", "Two."], "variants are left out"


def test_e_b24_decided_the_subject_the_cover_and_slide_one_block_where_wia_corrected_them_twice():
    """Phase N6: the subject sent first, a cover without its subject and a slide 1 that is a bare quote block (a pack's repair
    then fixes them); a later subject option and the good-news order stay warnings."""
    b = body(email__subject_options=["She used AI to set up her Google Ads", "She used AI to set up her Google Ads, again",
                                     "Why we lowered a new client's ad budget"])
    severities = {f["field"]: f["severity"] for f in found(checks(b), "first_touch.subject")}
    assert severities == {"format_plan.email.subject_options[0]": "blocking", "format_plan.email.subject_options[1]": "warning"}
    b = body(reels__0__cover_text="Did I set this up wrong?")
    assert [f["severity"] for f in found(checks(b), "first_touch.specific", "format_plan.reels[0].cover_text")] == ["blocking"]
    b = body()
    b["format_plan"]["carousel"]["slides"][0]["text"] = '"I don\'t know what I\'ve done."'
    assert {f["severity"] for f in found(checks(b), "first_touch.slide_one")} == {"blocking"}
