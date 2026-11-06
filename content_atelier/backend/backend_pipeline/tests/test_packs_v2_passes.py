"""NP-7 offline: the post-recording pass (NP.B14), finishing again with a permission (NP.B15) and pack-check.v3's sources.
Recorded (synthetic) answers; no database, no model call (R48: invented text only)."""
from __future__ import annotations

import copy
import json

import pytest

from backend_pipeline.packs import assemble, contracts_v2 as c2, fidelity, finalize, finish, passes
from backend_pipeline.tests.pack_v2_fixtures import finish_answer
from backend_pipeline.tests.test_packs_v2_finisher import draft_of

SAID = ("Before we touch anyone's ads, we ask one thing. How do you answer a new inquiry? One owner told us it usually takes "
        "two days. So that's where we started, with the reply.")
BY = {"by": "editor@example.com", "at": "2026-10-26T15:00:00+00:00", "delegated": True}


def current_pack():
    """A finished pack's draft as Finish again sees it (the previous version's pieces and body)."""
    draft, handoff = draft_of(("story", "broll_text"))
    done = finish.apply(draft, c2.FinishOutput.model_validate(finish_answer()), "finish", handoff)
    body = {**done["body"], "stronger_with_permission": ["Naming how much faster replies became would make the story land."]}
    again = assemble.draft(handoff, finish_mode="finish", previous={"body": body, "pieces": done["pieces"]})
    return {**again, "finish_mode": "finish"}, handoff


def caption_answer(**over):
    answer = {"cover_text": "The one question before we touch your ads",
              "cover_alternates": ["We start with your reply", "Two days to reply"],
              "caption": {"hook": "Most of the sale happens after the inquiry.",
                          "body": "One owner told us replies usually take two days.\n\nSo we started with the reply.",
                          "ending": "Save this for your next review. -Whitney"},
              "no_offer_ending": None, "notes": []}
    answer.update(over)
    return c2.CaptionOutput.model_validate(answer)


# NP.B14: the post-recording pass ----------------------------------------------------------------------------------------

def test_the_take_becomes_the_script_word_for_word_locked_as_the_person_s_line():
    draft, _ = current_pack()
    out = passes.prepare(draft, {"kind": "caption", "piece": "reel_1", "said": SAID, **BY})
    reel = out["pieces"]["reel_1"]
    assert reel["content"]["script"] == SAID
    assert reel["content"]["spoken_opening"] == "Before we touch anyone's ads, we ask one thing."
    locks = {lock["path"]: lock for lock in reel["locks"]}
    assert locks["script"]["author"] == "editor@example.com" and locks["script"]["origin"] == "pack" and locks["script"]["delegated"]
    assert {c["path"] for c in reel["changes"] if c["kind"] == "recorded"} == {"script", "spoken_opening"}
    assert out["pieces"]["email"] == draft["pieces"]["email"], "nothing else changes"
    assert out["body"]["recorded_takes"] == {"reel_1": SAID}, "kept on the pack for every later check"


def test_a_later_run_keeps_the_recorded_take_as_a_source():
    """NP-7's shakedown: a permission re-finish after a recorded take flagged the caption's restatement of the take, because
    the later run's check did not have the take. It is kept on the pack and carried to every later run."""
    draft, handoff = current_pack()
    out = passes.prepare(draft, {"kind": "caption", "piece": "reel_1", "said": SAID, **BY})
    pieces = passes.apply_caption(out, caption_answer(), "reel_1")
    later = assemble.draft(handoff, finish_mode="finish", previous={"body": out["body"], "pieces": pieces})
    assert later["body"]["recorded_takes"] == {"reel_1": SAID}
    c2.PackBody.model_validate({**later["body"], "fidelity": {}, "change": passes.change_record({"kind": "caption", "piece": "reel_1",
                                "said": SAID, **BY}), "provenance": {"brief_id": "b", "approved_hash": "h", "brief_schema": "v4",
                                "handoff_version": c2.HANDOFF_VERSION, "run_id": "r", "mode": "synthetic", "finish_mode": "finish",
                                "profiles": {}, "models": {}, "knowledge_base_version": None, "approved_by": None,
                                "approval_delegated": True}})


def test_the_post_recording_pass_refuses_the_b_roll_reel():
    draft, _ = current_pack()
    with pytest.raises(ValueError, match="face-to-camera"):
        passes.prepare(draft, {"kind": "caption", "piece": "reel_3", "said": SAID, **BY})


def test_the_caption_and_covers_are_written_and_a_locked_caption_line_and_the_take_stay():
    draft, _ = current_pack()
    draft["pieces"]["reel_1"]["locks"].append({"path": "caption.ending", "author": "approver@example.com", "delegated": False,
                                               "at": None, "origin": "pack"})
    kept = draft["pieces"]["reel_1"]["content"]["caption"]["ending"]
    draft = passes.prepare(draft, {"kind": "caption", "piece": "reel_1", "said": SAID, **BY})
    pieces = passes.apply_caption(draft, caption_answer(caption={"hook": "A new hook.", "body": "A new body.", "ending": "Model's ending."}),
                                  "reel_1")
    reel = pieces["reel_1"]["content"]
    assert reel["cover_text"] == "The one question before we touch your ads" and reel["cover_alternates"] == ["We start with your reply", "Two days to reply"]
    assert reel["caption"]["hook"] == "A new hook." and reel["caption"]["ending"] == kept, "a person's line is put back"
    assert reel["script"] == SAID, "the take is never touched"
    kinds = {(c["path"], c["kind"]) for c in pieces["reel_1"]["changes"]}
    assert ("cover_text", "captioned") in kinds and ("caption.ending", "restored_lock") in kinds
    c2.COPY_MODELS["reel"].model_validate(reel)


def test_the_caption_packet_carries_what_was_said_and_no_identifiers_and_is_deterministic():
    draft, handoff = current_pack()
    draft = passes.prepare(draft, {"kind": "caption", "piece": "reel_1", "said": SAID, **BY})
    packet = passes.caption_packet(draft, handoff, "reel_1")
    text = json.dumps(packet)
    assert packet["reel"]["said"] == SAID and packet["reel"]["kind"] == "story"
    assert "brief_synthetic" not in text and "ev_synthetic" not in text and "editor@example.com" not in text
    assert packet == passes.caption_packet(copy.deepcopy(draft), copy.deepcopy(handoff), "reel_1")


def test_the_caption_answer_has_exactly_two_alternates():
    with pytest.raises(ValueError):
        caption_answer(cover_alternates=["Only one"])


def test_the_pass_s_check_reads_only_the_caption_and_covers_with_the_take_among_its_sources():
    draft, handoff = current_pack()
    draft = passes.prepare(draft, {"kind": "caption", "piece": "reel_1", "said": SAID, **BY})
    pieces = passes.apply_caption(draft, caption_answer(), "reel_1")
    only = {k: set(v) for k, v in passes.check_only("reel_1").items()}
    pack, skip = fidelity.view(pieces, only=only, keys=["reel_1"])
    assert set(pack) == {"reel_1"} and set(pack["reel_1"]) <= set(passes.CAPTION_LEAVES) and "cover_text" in pack["reel_1"]
    assert "script" not in pack["reel_1"]
    sources = fidelity.sources(handoff, said={"reel_1": SAID})
    assert sources["recorded_take"] == {"reel_1": SAID}


def test_a_flag_that_survives_in_the_pass_s_reel_stays_open_and_the_brief_s_caption_is_not_put_back():
    draft, _ = current_pack()
    draft = passes.prepare(draft, {"kind": "caption", "piece": "reel_1", "said": SAID, **BY})
    pieces = passes.apply_caption(draft, caption_answer(), "reel_1")
    flag = {"piece": "reel_1", "path": "caption.hook", "text": "Most of the sale happens after the inquiry.", "verdict": "unsupported",
            "why": "Not in the take"}
    settled, record = finalize.settle(pieces, [flag], open_keys=["reel_1"])
    assert record[0]["outcome"] == "open_finding"
    assert settled["reel_1"]["content"]["caption"]["hook"] == "Most of the sale happens after the inquiry."
    assert settled["reel_1"]["findings"][-1]["status"] == "open"
    _, before = finalize.settle(pieces, [flag])
    assert before[0]["outcome"] == "put_back", "without the pass a brief piece's flag still puts the brief's line back"


def test_the_pass_s_change_record_names_the_person_who_started_it():
    record = passes.change_record({"kind": "caption", "piece": "reel_2", "said": SAID, **BY})
    c2.ChangeRecord.model_validate(record)
    assert record["kind"] == "recorded_take" and record["by"] == "editor@example.com" and record["pieces"] == ["reel_2"]


# NP.B15: finishing again with a permission ------------------------------------------------------------------------------

GRANT = {"item_id": "S1", "item": "Naming how much faster replies became would make the story land.",
         "statement": "The owner now replies the same day; we may say so.", **BY}


def test_a_grant_is_evidence_for_the_finisher_and_kept_on_the_pack():
    draft, handoff = current_pack()
    out = passes.prepare(draft, {"kind": "refinish", "grants": [GRANT], **BY})
    assert GRANT["statement"] in out["attested"]
    assert out["body"]["granted"] == [GRANT]
    packet = finish.packet(out, handoff, "refinish", granted=passes.granted_items(out["body"]))
    assert packet["mode"] == "refinish" and "granted items as evidence" in packet["task"]
    assert packet["granted"] == [{"item": GRANT["item"], "statement": GRANT["statement"]}]
    assert GRANT["statement"] in packet["attested"]


def test_a_finish_without_grants_sends_exactly_what_it_sent_before():
    draft, handoff = draft_of(("story", "broll_text"))
    packet = finish.packet(draft, handoff, "finish")
    assert "granted" not in packet, "an earlier pack's saved answer keeps replaying"


def test_finish_again_after_a_grant_keeps_it_as_evidence():
    draft, handoff = current_pack()
    out = passes.prepare(draft, {"kind": "refinish", "grants": [GRANT], **BY})
    done = finish.apply(out, c2.FinishOutput.model_validate(finish_answer()), "finish", handoff)
    later = assemble.draft(handoff, finish_mode="finish", previous={"body": done["body"], "pieces": done["pieces"]})
    assert later["body"]["granted"] == [GRANT] and GRANT["statement"] in later["attested"]
    c2.Grant.model_validate(later["body"]["granted"][0])


def test_the_refinish_record_and_the_run_s_stages():
    record = passes.change_record({"kind": "refinish", "grants": [GRANT], **BY})
    c2.ChangeRecord.model_validate(record)
    assert record["kind"] == "refinish" and "1 granted item" in record["note"]
    assert c2.stages_for("refinish") == ("pack_assemble", "pack_refinish", "pack_check", "pack_repair", "pack_recheck", "pack_finalize")
    assert c2.stages_for("caption")[1] == "pack_caption" and c2.stages_for(None) == c2.STAGES


# pack-check.v3 ----------------------------------------------------------------------------------------------------------

def test_the_check_s_sources_add_the_approved_perspective_only_under_v3():
    _, handoff = draft_of(("story", "broll_text"))
    plain = fidelity.sources(handoff)
    assert "approved_perspective" not in plain and "recorded_take" not in plain, "v2's request is unchanged, so it replays"
    v3 = fidelity.sources(handoff, perspective=True)
    assert v3["approved_perspective"]["wia_perspective"] == handoff["strategy"]["wia_perspective"]
    assert v3["approved_perspective"]["central_point"] == handoff["strategy"]["central_point"]
    assert {k: v for k, v in v3.items() if k != "approved_perspective"} == plain
    assert c2.PERSPECTIVE_CHECKS == ("2026-10-26.pack-check.v3", "2026-10-27.pack-check.v4")
    assert "2026-10-26.pack-check.v3" in c2.RELEASED["pack_check"]


def test_a_repair_that_cuts_a_whole_cover_alternate_removes_it_and_never_leaves_an_empty_line():
    """NP-7's shakedown: a repair cut two flagged cover alternates to "", and the empty strings failed the Reel's contract at
    finalize. A cut line of a list is removed; a list that must keep a line (screens, subject options) keeps its last one."""
    draft, _ = current_pack()
    pieces = passes.apply_caption(passes.prepare(draft, {"kind": "caption", "piece": "reel_1", "said": SAID, **BY}), caption_answer(), "reel_1")
    flags = [{"piece": "reel_1", "path": "cover_alternates[0]", "text": "We start with your reply", "verdict": "unsupported", "why": ""},
             {"piece": "reel_1", "path": "cover_alternates[1]", "text": "Two days to reply", "verdict": "unsupported", "why": ""}]
    patched, applied, missed = fidelity.apply_patches(pieces, [{"piece": "reel_1", "old": "We start with your reply", "new": ""},
                                                               {"piece": "reel_1", "old": "Two days to reply", "new": ""}], flags)
    assert patched["reel_1"]["content"]["cover_alternates"] == [] and len(applied) == 2 and not missed
    c2.COPY_MODELS["reel"].model_validate(patched["reel_1"]["content"])
    screens = pieces["reel_3"]["content"]["screens"]
    one = copy.deepcopy(pieces)
    one["reel_3"]["content"]["screens"] = screens[:1]
    kept, _, missed = fidelity.apply_patches(one, [{"piece": "reel_3", "old": screens[0], "new": ""}],
                                             [{"piece": "reel_3", "path": "screens[0]", "text": screens[0], "verdict": "unsupported", "why": ""}])
    assert kept["reel_3"]["content"]["screens"] == screens[:1] and missed, "a b-roll Reel keeps its one screen"


def test_finalize_drops_an_empty_cover_alternate_left_by_a_run_saved_before_the_fix():
    draft, _ = current_pack()
    pieces = copy.deepcopy(draft["pieces"])
    pieces["reel_1"]["content"]["cover_alternates"] = ["", "Two days to reply"]
    settled, _ = finalize.settle(pieces, [])
    assert settled["reel_1"]["content"]["cover_alternates"] == ["Two days to reply"]
    c2.COPY_MODELS["reel"].model_validate(settled["reel_1"]["content"])
