"""NP.B1, NP.B7, NP.B8 offline: assembly from hand-off view v2, the finisher's answer applied with locks put back, the
fidelity loop's flags and patches, and finalize's put-back and open findings. Recorded (synthetic) answers; no database, no
model call (R48: invented text only)."""
from __future__ import annotations

import copy
import json

import pytest

from backend_pipeline.packs import assemble, contracts_v2 as c2, fidelity, finalize, finish
from backend_pipeline.tests.pack_v2_fixtures import brief_row, finish_answer, handoff_v2


def draft_of(kinds=("story", "stance", "broll_text"), locked=(), mode="finish", changes=None):
    row = brief_row(kinds, locked, changes)
    handoff = handoff_v2(row)
    return {**assemble.draft(handoff, finish_mode=mode), "finish_mode": mode}, handoff


def test_a_two_reel_brief_assembles_by_kind_and_leaves_the_stance_reel_for_the_finisher():
    draft, _ = draft_of(("story", "broll_text"))
    pieces = draft["pieces"]
    assert [pieces[k]["origin"] for k in c2.PIECE_KEYS] == ["brief", "brief", "brief", "not_written", "brief"]
    assert pieces["reel_3"]["content"]["kind"] == "broll_text" and pieces["reel_3"]["brief_key"] == "reel_2", "mapped by kind"
    assert "stance" in pieces["reel_2"]["not_written_reason"] and draft["missing"] == ["reel_2"]
    assert pieces["email"]["brief_copy"] == pieces["email"]["content"] and pieces["email"]["content"]["cta"] == "reply"
    assert pieces["reel_1"]["content"]["title"] == "The question we ask before touching your ads", "a working title, not the job"


def test_assemble_mode_says_a_missing_kind_is_not_written_and_makes_no_call():
    draft, handoff = draft_of(("story", "broll_text"), mode="assemble")
    assert "assemble" in draft["pieces"]["reel_2"]["not_written_reason"]
    done = finish.run(None, None, None, draft, handoff)  # no worker: a call would fail
    assert done["called"] is False and done["pieces"] == draft["pieces"]


def test_gate_two_locks_land_on_their_pack_leaves_and_a_broll_lock_moves_to_reel_3():
    locked = ["format_plan.email.opening", "format_plan.reels[0].caption.hook", "format_plan.carousel.slides[2].text",
              "format_plan.reels[1].screens[0]", "wia_perspective"]
    draft, _ = draft_of(("story", "broll_text"), locked)
    found = {k: [(lock["path"], lock["origin"]) for lock in p["locks"]] for k, p in draft["pieces"].items() if p["locks"]}
    assert found == {"email": [("opening", "gate_two")], "reel_1": [("caption.hook", "gate_two")],
                     "carousel": [("slides[2].text", "gate_two")], "reel_3": [("screens[0]", "gate_two")]}
    assert all(lock["delegated"] for p in draft["pieces"].values() for lock in p["locks"]), "no WIA reviewer list: delegated"


def test_hand_off_v2_carries_the_strategy_claim_places_and_locks():
    row = brief_row(("story", "broll_text"), ["format_plan.reels[1].screens[0]"])
    handoff = handoff_v2(row)
    assert handoff["strategy"]["supporting_example"]["credits"] and handoff["strategy"]["cta_why"]
    quote_claim = next(c for c in handoff["claims"] if c["claim_id"] == "c_2")
    assert quote_claim["path"] == "format_plan.reels[0].script" and quote_claim["piece"] == "reel_1" and quote_claim["leaf"] == "script"
    assert handoff["locks"][0] == {**handoff["locks"][0], "piece": "reel_2", "leaf": "screens[0]", "value": "Her inquiries were up."}


def test_the_finisher_writes_three_reels_of_the_three_kinds_from_a_two_reel_brief():
    draft, handoff = draft_of(("story", "broll_text"))
    done = finish.apply(draft, c2.FinishOutput.model_validate(finish_answer()), "finish", handoff)
    pieces = done["pieces"]
    assert [pieces[k]["content"]["kind"] for k in ("reel_1", "reel_2", "reel_3")] == ["story", "stance", "broll_text"]
    assert pieces["reel_2"]["origin"] == "written" and pieces["reel_2"]["brief_copy"] is None
    assert pieces["reel_2"]["changes"][0]["kind"] == "written"
    assert pieces["email"]["origin"] == "finished" and any(c["path"] == "subject_options[0]" for c in pieces["email"]["changes"])
    assert pieces["email"]["content"]["send_header"] == pieces["email"]["brief_copy"]["send_header"], "the send header is kept"
    assert done["body"]["client_quotes"] == [{"quote_id": "Q1", "piece": "reel_1", "quote": "it usually takes us two days to reply",
                                              "speaker": "The owner", "evidence_id": "ev_synthetic_2", "cleared": None}]
    for key in c2.PIECE_KEYS:
        c2.COPY_MODELS[c2.CHANNEL[key]].model_validate(pieces[key]["content"])


def test_a_locked_line_the_model_changed_is_put_back_and_recorded():
    draft, handoff = draft_of(locked=["format_plan.email.opening", "format_plan.reels[0].caption.hook"])
    answer = finish_answer()
    answer["email"]["opening"] = "Hi {{contact.first_name}},\n\nA rewritten opening the model should not have made."
    answer["reels"][0]["caption"]["hook"] = "A rewritten hook."
    done = finish.apply(draft, c2.FinishOutput.model_validate(answer), "finish", handoff)
    email, reel = done["pieces"]["email"], done["pieces"]["reel_1"]
    assert email["content"]["opening"] == email["brief_copy"]["opening"]
    assert reel["content"]["caption"]["hook"] == reel["brief_copy"]["caption"]["hook"]
    assert {(c["path"], c["kind"]) for c in email["changes"]} >= {("opening", "restored_lock")}
    assert {(c["path"], c["kind"]) for c in reel["changes"]} >= {("caption.hook", "restored_lock")}


def test_a_renumbered_carousel_with_a_locked_slide_keeps_the_brief_carousel_and_records_it():
    draft, handoff = draft_of(locked=["format_plan.carousel.slides[2].text"])
    answer = finish_answer()
    answer["carousel"]["slides"] = [{"number": n, "text": f"A re-split slide {n}."} for n in (1, 2, 4, 5, 6, 7, 8)]
    done = finish.apply(draft, c2.FinishOutput.model_validate(answer), "finish", handoff)
    carousel = done["pieces"]["carousel"]
    assert carousel["content"] == carousel["brief_copy"]
    assert carousel["changes"][0]["kind"] == "kept_brief_carousel"


def test_missing_only_changes_no_existing_line_and_writes_the_missing_reel():
    draft, handoff = draft_of(("story", "broll_text"), mode="missing_only")
    done = finish.apply(draft, c2.FinishOutput.model_validate(finish_answer()), "missing_only", handoff)
    for key in ("email", "carousel", "reel_1", "reel_3"):
        assert done["pieces"][key]["content"] == draft["pieces"][key]["content"], key
    assert done["pieces"]["reel_2"]["origin"] == "written"


def test_the_finisher_answer_must_have_the_three_kinds_in_order():
    answer = finish_answer()
    answer["reels"] = [answer["reels"][0], answer["reels"][0], answer["reels"][2]]
    with pytest.raises(ValueError, match="story, stance and broll_text"):
        c2.FinishOutput.model_validate(answer)


def test_the_finisher_packet_holds_no_identifiers_or_times_and_shows_locked_lines():
    draft, handoff = draft_of(("story", "broll_text"), ["format_plan.email.opening"])
    packet = finish.packet(draft, handoff, "finish")
    text = json.dumps(packet)
    assert "brief_synthetic" not in text and "c_1" not in text and "approver@example.com" not in text
    assert "ev_synthetic" not in text, "the finisher cites nothing; evidence goes by speaker and time"
    assert packet["pieces"]["reel_2"] == {"missing": True, "kind": "stance", "label": "Reel 2"}
    assert packet["pieces"]["carousel"]["title"] == draft["pieces"]["carousel"]["content"]["title"], "the carousel's title is copy"
    assert "title" not in packet["pieces"]["reel_1"], "a Reel's working title is the finisher's to write"
    assert packet["locked"] == [{"piece": "email", "path": "opening", "value": draft["pieces"]["email"]["content"]["opening"]}]
    assert packet == finish.packet(copy.deepcopy(draft), copy.deepcopy(handoff), "finish"), "deterministic"


def finished(locked=()):
    draft, handoff = draft_of(("story", "broll_text"), locked)
    return finish.apply(draft, c2.FinishOutput.model_validate(finish_answer()), "finish", handoff)["pieces"], handoff


def test_the_check_skips_locked_lines_and_personal_lines():
    pieces, _ = finished(["format_plan.reels[0].caption.hook"])
    pieces["reel_2"]["content"]["personal_lines"] = ["I love this part of the job."]
    pack, skip = fidelity.view(pieces)
    assert "caption.hook" not in pack["reel_1"]
    assert {"piece": "reel_1", "text": pieces["reel_1"]["content"]["caption"]["hook"], "why": "written by a person"} in skip
    assert any(s["why"].startswith("a personal line") for s in skip)
    statements = [{"piece": "reel_2", "text": "I love this part of the job.", "verdict": "unsupported", "why": "", "source": "",
                   "in_moment": None},
                  {"piece": "reel_1", "text": "The owner told us it usually takes two days to reply.", "verdict": "supported",
                   "why": "", "source": "", "in_moment": False}]
    flags = fidelity.flagged(statements, pieces, skip)
    assert [(f["piece"], f["path"], f["verdict"]) for f in flags] == [("reel_1", "script", "unsupported")], \
        "a personal line is skipped; a quote out of its moment counts as unsupported"


def test_a_flagged_sentence_is_repaired_and_a_locked_line_is_never_patched():
    pieces, _ = finished(["format_plan.reels[0].caption.hook"])
    flags = [{"piece": "reel_1", "path": "script", "text": "The owner told us it usually takes two days to reply.",
              "verdict": "unsupported", "why": "", "source": ""},
             {"piece": "reel_1", "path": "caption.hook", "text": pieces["reel_1"]["content"]["caption"]["hook"],
              "verdict": "unsupported", "why": "", "source": ""}]
    patches = [{"piece": "reel_1", "old": "The owner told us it usually takes two days to reply.", "new": "The owner walked us through it."},
               {"piece": "reel_1", "old": pieces["reel_1"]["content"]["caption"]["hook"], "new": "A changed hook."}]
    out, applied, missed = fidelity.apply_patches(pieces, patches, flags)
    assert "The owner walked us through it." in out["reel_1"]["content"]["script"]
    assert out["reel_1"]["content"]["caption"]["hook"] == pieces["reel_1"]["content"]["caption"]["hook"], "a locked line is never patched"
    assert [a["path"] for a in applied] == ["script"] and len(missed) == 1
    assert any(c["kind"] == "missed_patch" for c in out["reel_1"]["changes"])


def test_a_patch_whose_old_text_is_not_found_is_dropped_and_recorded():
    pieces, _ = finished()
    flags = [{"piece": "email", "path": "body", "text": "Follow-up is part of the ad.", "verdict": "unsupported", "why": "", "source": ""}]
    out, applied, missed = fidelity.apply_patches(pieces, [{"piece": "email", "old": "Words that are not there.", "new": "x"}], flags)
    assert applied == [] and missed == [{"piece": "email", "old": "Words that are not there.", "new": "x"}]
    assert out["email"]["content"] == pieces["email"]["content"]


def test_a_surviving_flag_in_a_brief_piece_puts_back_that_sentence_only():
    pieces, _ = finished()
    script = pieces["reel_1"]["content"]["script"]
    survivor = {"piece": "reel_1", "path": "script", "text": "The owner told us it usually takes two days to reply.",
                "verdict": "unsupported", "why": "Moved out of its moment", "source": ""}
    out, record = finalize.settle(pieces, [survivor])
    new = out["reel_1"]["content"]["script"]
    assert "The owner told us it usually takes two days to reply." not in new
    assert new.startswith("Before we touch your ads, we ask one thing. How do you answer a new inquiry?"), "the rest is kept"
    assert new != script and record[0]["outcome"] == "put_back"
    assert out["reel_1"]["changes"][-1]["kind"] == "put_back" and not out["reel_1"]["findings"]


def test_a_surviving_flag_in_a_written_reel_is_an_open_blocking_finding():
    pieces, _ = finished()
    survivor = {"piece": "reel_2", "path": "script", "text": "We asked one owner how they answer a new inquiry, and that question told us where to start.",
                "verdict": "unsupported", "why": "Adds a conclusion", "source": ""}
    out, record = finalize.settle(pieces, [survivor])
    finding = out["reel_2"]["findings"][0]
    assert finding["status"] == "open" and finding["severity"] == "blocking" and finding["path"] == "script"
    assert out["reel_2"]["content"] == pieces["reel_2"]["content"], "a written Reel's text is left for a person"
    assert record[0]["outcome"] == "open_finding"
    c2.Finding.model_validate(finding)


def test_a_flagged_cover_alternate_the_brief_never_had_is_removed():
    pieces, _ = finished()
    alt = pieces["reel_1"]["content"]["cover_alternates"][1]
    out, _ = finalize.settle(pieces, [{"piece": "reel_1", "path": "cover_alternates[1]", "text": alt, "verdict": "guardrail",
                                       "why": "", "source": ""}])
    assert out["reel_1"]["content"]["cover_alternates"] == [pieces["reel_1"]["content"]["cover_alternates"][0]]


def test_the_team_s_words_are_quotable_only_with_public_use_or_a_clearance_and_a_client_s_always():
    """Found in NP.X1 on the October calls (public_use false on every collected call): the finisher is told which evidence
    copy may quote; a client's words are quotable as a before-publishing note (never a gate)."""
    from backend_pipeline.briefs.handoff import quotable
    roster = [{"name": "Whitney Hodges", "role": "Founder", "status": "current", "aliases": ["Whitney Hodges", "Whitney"]}]
    assert quotable({"speaker": "Whitney Hodges", "public_use": False, "permission_recorded": False}, roster) is False
    assert quotable({"speaker": "Whitney Hodges", "public_use": False, "permission_recorded": True}, roster) is True
    assert quotable({"speaker": "Whitney Hodges", "public_use": True, "permission_recorded": False}, roster) is True
    assert quotable({"speaker": "The owner", "public_use": False, "permission_recorded": False}, roster) is True
    draft, handoff = draft_of()
    assert [e["quotable"] for e in finish.packet(draft, handoff, "finish")["evidence"]] == [False, True]


def test_a_put_back_sentence_that_would_repeat_its_neighbour_puts_back_the_brief_s_paragraph():
    """NP.X3: the finisher split the brief's sentence in two and only one half was flagged, so putting back the brief's
    sentence alone repeated the half beside it; the brief's paragraph goes back instead, and the rest is kept."""
    brief = ("We test one thing at a time.\n\nWe bring the ad expertise, while your team brings what it knows about the "
             "venue, the market and the couples. That gives us a better basis for a decision.\n\nReply and tell me more.")
    finished_body = ("We test one thing at a time, every week.\n\nWe bring the ad expertise and own every result. Your team "
                     "brings what it knows about the venue, the market and its couples, and we want both on the table."
                     "\n\nReply and tell me more.")
    pieces = {"email": {"content": {"body": finished_body}, "brief_copy": {"body": brief}, "changes": [], "findings": [],
                        "locks": [], "origin": "finished", "channel": "email"}}
    survivor = {"piece": "email", "path": "body", "text": "We bring the ad expertise and own every result.",
                "verdict": "unsupported", "why": "Adds a promise", "source": ""}
    change = finalize.put_back(pieces["email"], survivor)
    body = pieces["email"]["content"]["body"]
    assert "own every result" not in body and body.count("what it knows about the venue") == 1
    assert "We bring the ad expertise, while your team brings what it knows about the venue, the market and the couples. " \
           "That gives us a better basis for a decision." in body
    assert body.startswith("We test one thing at a time, every week."), "the paragraphs that were not flagged are kept"
    assert change["kind"] == "put_back" and "paragraph" in change["note"]
    plain = {"email": {"content": {"body": "One. We bring the ad expertise and own every result. Two."},
                       "brief_copy": {"body": "One. We bring the ad expertise. Two."}, "changes": [], "findings": [],
                       "locks": [], "origin": "finished", "channel": "email"}}
    survivor["text"] = "We bring the ad expertise and own every result."
    assert "the brief's sentence is put back" in finalize.put_back(plain["email"], survivor)["note"]
    assert plain["email"]["content"]["body"] == "One. We bring the ad expertise. Two."


def test_finish_again_keeps_a_reel_the_finisher_wrote_marked_written():
    """NP.X3: Finish again assembled the stance Reel the finisher had written as existing copy, and finishing it marked it
    "finished", as if the brief had it; it stays "written", with no brief copy, so it still needs a person's reading."""
    draft, handoff = draft_of(("story", "broll_text"))
    first = finish.apply(draft, c2.FinishOutput.model_validate(finish_answer()), "finish", handoff)
    again = assemble.draft(handoff, finish_mode="finish", previous={"body": first["body"], "pieces": first["pieces"]})
    assert again["pieces"]["reel_2"]["origin"] == "written" and again["pieces"]["reel_2"]["content"] is not None
    answer = finish_answer()
    answer["reels"][1]["script"] += " That is the part I keep coming back to."
    done = finish.apply(again, c2.FinishOutput.model_validate(answer), "finish", handoff)
    reel = done["pieces"]["reel_2"]
    assert reel["origin"] == "written" and reel["brief_copy"] is None
    assert any(c["kind"] == "finished" and c["path"] == "script" for c in reel["changes"])
