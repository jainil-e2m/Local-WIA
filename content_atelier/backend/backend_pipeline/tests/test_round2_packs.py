"""Round 2 (WIA's feedback of 26 October 2026) offline: writer v5.3's Reels (the central story and two premises of their
own, production apart from the premise, the premises weighed), finisher v3's answer applied, an earlier brief's or pack's
retold Reels replaced, check v4's editorial notes carried to findings, the agency-comparison warning, and the profiles
selected by setting. Invented text only (R48); no database, no model call."""
from __future__ import annotations

import copy
import json

import pytest

from backend_pipeline import prompt_files
from backend_pipeline.briefs import contracts_v4 as c4
from backend_pipeline.packs import assemble, checks, contracts_v2 as c2, fidelity, finalize, finish, runtime_v2
from backend_pipeline.tests.pack_v2_fixtures import brief_row, finish_answer, handoff_v2

PREMISES = {"central": ("A venue owner's slow first reply was where we started", "face_to_camera"),
            "second": ("What our team reads in an inquiry thread before we change a campaign", "face_to_camera"),
            "third": ("The one question we ask about a venue's tour calendar", "on_screen_text")}


def premise_row():
    """The synthetic brief as writer v5.3 writes it: the central story and two premises of their own."""
    row = brief_row()
    plan = row["content_body"]["document"]["body"]["format_plan"]
    for reel, kind in zip(plan["reels"], c4.PREMISE_KINDS):
        premise, production = PREMISES[kind]
        reel.update(kind=kind, production=production, premise=premise, takeaway="A team that reads the whole journey",
                    distinct_because=f"It answers its own question: {premise.lower()}", timestamps=["0:04 the question"])
    plan["premise_options"] = [{"premise": p, "type": "behind_the_scenes", "material": "0:04 to 0:09",
                                "used_for": f"reel_{i}", "why": "Independent and supported"}
                               for i, (p, _) in enumerate(PREMISES.values(), 1)]
    return row


def answer_v3(**changes):
    """A finisher v3 writing answer: finish_answer's pieces, the Reels as the central story and two premises."""
    answer = finish_answer()
    for reel, kind in zip(answer["reels"], c4.PREMISE_KINDS):
        reel["kind"] = kind
        if PREMISES[kind][1] == "face_to_camera" and not reel.get("script"):
            reel.update(script="We read the thread before the campaign. That's where it starts.", screens=None,
                        spoken_opening="We read the thread first.")
    answer.update(changes)
    return answer


def plan_v3():
    """Finisher v3's plan: each Reel's premise and production, and the openings weighed."""
    return c2.PlanOutput.model_validate({
        "reels": [{"kind": kind, "production": production, "premise": premise, "takeaway": "A team that reads the whole journey",
                   "distinct_because": "A different question", "timestamps": ["0:09 the owner on replies"],
                   "openings": ["Before we touch your ads, one question", "Her replies took two days"],
                   "opening": "Before we touch your ads, one question", "why": "It names the subject and the decision"}
                  for kind, (premise, production) in PREMISES.items()],
        "openings": [{"piece": "email", "openings": ["The reply before the ads", "Why we read your first reply"],
                      "opening": "Why we read your first reply", "why": "The reader's own question"}]})


# Writer v5.3's contract ---------------------------------------------------------------------------------------------------

def test_writer_v53_writes_the_central_story_and_two_premises_with_the_premises_it_weighed():
    body = premise_row()["content_body"]["document"]["body"]
    write = c4.BriefWriteV53.model_validate(c4.writer_part_v4(body))
    assert [r.kind for r in write.format_plan.reels] == ["central", "second", "third"]
    assert write.format_plan.reels[2].production == "on_screen_text" and len(write.format_plan.premise_options) == 3
    # The stored body takes either plan; an earlier brief dumps exactly as stored.
    old = brief_row()["content_body"]["document"]
    assert c4.BriefDocumentV4.model_validate(old).model_dump(mode="json")["body"]["format_plan"] == old["body"]["format_plan"]
    c4.BriefDocumentV4.model_validate(premise_row()["content_body"]["document"])


def test_writer_v53_refuses_a_retold_set_a_text_reel_with_a_script_and_too_few_premises_weighed():
    body = premise_row()["content_body"]["document"]["body"]
    bad = copy.deepcopy(body)
    bad["format_plan"]["reels"][1]["kind"] = "third"
    with pytest.raises(ValueError, match="central, second and third"):
        c4.BriefWriteV53.model_validate(c4.writer_part_v4(bad))
    bad = copy.deepcopy(body)
    bad["format_plan"]["reels"][2]["script"] = "A script on a text Reel."
    with pytest.raises(ValueError, match="on_screen_text"):
        c4.BriefWriteV53.model_validate(c4.writer_part_v4(bad))
    bad = copy.deepcopy(body)
    bad["format_plan"]["premise_options"] = bad["format_plan"]["premise_options"][:2]
    with pytest.raises(ValueError, match="at least three"):
        c4.BriefWriteV53.model_validate(c4.writer_part_v4(bad))


def test_writer_v53_schema_asks_for_three_reels_and_every_earlier_writer_schema_is_unchanged():
    schema = c4.writer_schema_v53(["reel", "carousel", "email", "caption"])
    assert schema["$defs"]["FormatPlanV5"]["properties"]["reels"]["minItems"] == 3
    assert "production" in schema["$defs"]["ReelPlanV5"]["properties"]
    assert "production" not in json.dumps(c4.writer_schema_v51(["reel", "carousel", "email", "caption"]))


def test_the_shared_craft_guide_is_included_in_the_new_prompts_and_never_in_an_earlier_one():
    folder = runtime_v2.TEMPLATES
    finisher = runtime_v2.template("2026-10-27.pack-finish.v3")
    writer = prompt_files.read(folder / "brief_write.v5.3.md")
    for text in (finisher, writer):
        assert "## 5. Editorial judgment" in text and "{{>" not in text
        assert "most agencies" not in text.replace("most agencies do", "").replace("what most owners or most agencies", "")
    assert runtime_v2.template("2026-10-25.pack-finish.v2") == (folder / "pack_finish.v2.md").read_text(encoding="utf-8")


# Assembly and the finisher ------------------------------------------------------------------------------------------------

def test_under_finisher_v3_an_earlier_brief_keeps_its_story_as_the_central_reel_and_its_retold_reels_are_source_material():
    handoff = handoff_v2(brief_row())
    draft = assemble.draft(handoff, finish_mode="finish", premises=True)
    pieces = draft["pieces"]
    assert pieces["reel_1"]["content"]["kind"] == "central" and pieces["reel_1"]["content"]["production"] == "face_to_camera"
    assert pieces["reel_1"]["origin"] == "brief"
    for key in ("reel_2", "reel_3"):
        assert pieces[key]["origin"] == "not_written" and "premise of its own" in pieces[key]["not_written_reason"]
    assert draft["missing"] == ["reel_2", "reel_3"] and draft["sources"] == {"reel_2": ["reel_2"], "reel_3": ["reel_3"]}
    packet = finish.packet({**draft, "finish_mode": "finish", "premises": True}, handoff, "finish")
    assert packet["pieces"]["reel_2"] == {"missing": True, "kind": "second", "label": "Reel 2"}
    assert packet["source_material"]["reel_2"][0]["script"], "the retold stance Reel is there to draw on"


def test_a_v53_brief_maps_by_its_kinds_and_needs_finisher_v3():
    handoff = handoff_v2(premise_row())
    draft = assemble.draft(handoff, finish_mode="finish", premises=True)
    assert [draft["pieces"][k]["content"]["kind"] for k in ("reel_1", "reel_2", "reel_3")] == ["central", "second", "third"]
    assert draft["pieces"]["reel_3"]["content"]["premise"] == PREMISES["third"][0]
    assert draft["pieces"]["reel_3"]["content"]["register"] == "on_screen" and not draft["missing"]
    with pytest.raises(ValueError, match="finisher v3"):
        assemble.draft(handoff, finish_mode="finish", premises=False)


def test_the_finisher_v3_answer_lands_with_premises_production_and_the_choices_weighed():
    handoff = handoff_v2(brief_row())
    draft = {**assemble.draft(handoff, finish_mode="finish", premises=True), "finish_mode": "finish", "premises": True}
    done = finish.apply(draft, c2.FinishOutputV3.model_validate(answer_v3()), "finish", handoff, plan_v3())
    pieces = done["pieces"]
    assert [pieces[k]["content"]["kind"] for k in ("reel_1", "reel_2", "reel_3")] == ["central", "second", "third"]
    third = pieces["reel_3"]["content"]
    assert third["production"] == "on_screen_text" and third["script"] is None and third["screens"] and third["register"] == "on_screen"
    assert third["premise"] == PREMISES["third"][0] and third["timestamps"] == ["0:09 the owner on replies"]
    assert pieces["reel_2"]["origin"] == "written" and "retold the central story" in pieces["reel_2"]["changes"][0]["note"]
    assert pieces["reel_1"]["origin"] == "finished"
    assert [c["piece"] for c in done["body"]["creative_choices"]] == ["email", "reel_1", "reel_2", "reel_3"]
    assert done["body"]["creative_choices"][0]["chosen"] == "Why we read your first reply"
    for key in c2.PIECE_KEYS:
        c2.COPY_MODELS[c2.CHANNEL[key]].model_validate(pieces[key]["content"])
    c2.PackBody.model_validate({**done["body"], "fidelity": {}, "change": {"kind": "generated", "by": "x", "at": "t",
                                                                          "delegated": False},
                                "provenance": {"brief_id": "b", "approved_hash": "h", "brief_schema": "s", "handoff_version": "v",
                                               "run_id": "r", "mode": "live", "finish_mode": "finish", "profiles": {},
                                               "models": {}, "knowledge_base_version": None, "approved_by": None,
                                               "approval_delegated": False}})


def test_the_finisher_v3_answer_refuses_a_retold_set_and_a_text_reel_one():
    bad = answer_v3()
    bad["reels"][0].update(script=None, spoken_opening=None, screens=["One screen."])
    with pytest.raises(ValueError, match="Reel 1"):
        c2.FinishOutputV3.model_validate(bad)
    bad = answer_v3()
    bad["reels"][2]["script"] = "A script beside the screens."
    with pytest.raises(ValueError, match="script and screens"):
        c2.FinishOutputV3.model_validate(bad)
    plan = plan_v3().model_dump()
    plan["reels"][0]["production"] = "on_screen_text"
    with pytest.raises(ValueError, match="Reel 1"):
        c2.PlanOutput.model_validate(plan)
    bad = answer_v3()
    bad["reels"] = [bad["reels"][0], bad["reels"][0], bad["reels"][2]]
    with pytest.raises(ValueError, match="central, second and third"):
        c2.FinishOutputV3.model_validate(bad)


def test_finishing_an_earlier_pack_again_under_finisher_v3_replaces_its_retold_reels_and_keeps_a_persons_line_as_a_note():
    handoff = handoff_v2(brief_row())
    first = assemble.draft(handoff, finish_mode="finish")
    done = finish.apply({**first, "finish_mode": "finish"}, c2.FinishOutput.model_validate(finish_answer()), "finish", handoff)
    pieces = copy.deepcopy(done["pieces"])
    pieces["reel_2"]["locks"] = [{"path": "script", "author": "a@example.com", "delegated": False, "at": None, "origin": "pack"}]
    body = {**first["body"], "client_quotes": [], "stronger_with_permission": []}
    again = assemble.draft(handoff, finish_mode="finish", previous={"body": body, "pieces": pieces}, premises=True)
    assert again["pieces"]["reel_1"]["content"]["kind"] == "central"
    assert again["pieces"]["reel_2"]["content"] is None and again["missing"] == ["reel_2", "reel_3"]
    assert again["sources"]["reel_2"][0]["retold"]["kind"] == "stance"
    assert any("was not carried" in n["text"] for n in again["body"]["before_publishing"])
    packet = finish.packet({**again, "finish_mode": "finish", "premises": True}, handoff, "finish")
    assert packet["source_material"]["reel_3"][0]["kind"] == "broll_text"


# Check v4's editorial notes -----------------------------------------------------------------------------------------------

def test_editorial_notes_become_flags_with_their_severity_and_survivors_become_open_editorial_findings():
    handoff = handoff_v2(brief_row())
    draft = {**assemble.draft(handoff, finish_mode="finish", premises=True), "finish_mode": "finish", "premises": True}
    pieces = finish.apply(draft, c2.FinishOutputV3.model_validate(answer_v3()), "finish", handoff, plan_v3())["pieces"]
    pack, skip = fidelity.view(pieces)
    hook = pieces["email"]["content"]["subject_options"][0]
    notes = [{"piece": "email", "text": hook, "issue": "lead_quality", "why": "More tours beside ghosting"},
             {"piece": "reel_2", "text": pieces["reel_2"]["content"]["on_screen_hook"], "issue": "premise_overlap", "why": "Retells Reel 1"}]
    flags = fidelity.editorial_flags(notes, pieces, skip)
    assert [(f["verdict"], f["issue"], f["severity"]) for f in flags] == [("editorial", "lead_quality", "blocking"),
                                                                          ("editorial", "premise_overlap", "warning")]
    assert flags[0]["path"] == "subject_options[0]"
    settled, record = finalize.settle(pieces, flags)
    found = settled["email"]["findings"]
    assert found[0]["kind"] == "editorial" and found[0]["severity"] == "blocking" and found[0]["issue"] == "lead_quality"
    assert settled["email"]["content"]["subject_options"][0] == hook, "an editorial note is never put back to the brief's line"
    assert {r["outcome"] for r in record} == {"open_finding"}
    for key in c2.PIECE_KEYS:
        for f in settled[key]["findings"]:
            c2.Finding.model_validate(f)


def test_check_v4_answers_with_editorial_notes_and_a_reading_of_each_piece():
    answer = {"statements": [], "editorial": [{"piece": "reel_3", "text": "x", "issue": "slogan", "why": "a motto"}],
              "pieces": [{"piece": "email", "strength": "acceptable", "why": "plain"}]}
    out = c2.output_model("pack_check", "2026-10-27.pack-check.v4").model_validate(answer)
    assert out.editorial[0].issue == "slogan"
    with pytest.raises(ValueError):
        c2.CheckOutputV4.model_validate({**answer, "editorial": [{**answer["editorial"][0], "issue": "made_up"}]})
    assert c2.output_model("pack_check", "2026-10-26.pack-check.v3") is c2.CheckOutput
    assert set(c2.EDITORIAL_ISSUES.values()) == {"blocking", "warning"}


# Deterministic checks -----------------------------------------------------------------------------------------------------

def test_a_premise_pack_is_composed_of_the_central_story_and_two_premises():
    handoff = handoff_v2(brief_row())
    draft = {**assemble.draft(handoff, finish_mode="finish", premises=True), "finish_mode": "finish", "premises": True}
    pieces = finish.apply(draft, c2.FinishOutputV3.model_validate(answer_v3()), "finish", handoff, plan_v3())["pieces"]
    assert checks.composition_findings(pieces) == []
    assert not [f for f in checks.format_findings(pieces) if f["path"] == "screens"]
    waiting = assemble.draft(handoff, finish_mode="finish", premises=True)["pieces"]
    messages = [f["message"] for f in checks.composition_findings(waiting)]
    assert any("Reel 2 (second premise) was not written" in m for m in messages)


@pytest.mark.parametrize("line,flagged", [("Unlike most agencies, we start with the reply.", True),
                                          ("That's not what you'd expect to hear from an ads agency.", True),
                                          ("Most marketing teams skip this.", True),
                                          ("The agency the client used before set up the campaign.", False),
                                          ("Others want us to launch their campaigns and guide them.", False)])
def test_copy_that_compares_wia_with_other_agencies_is_a_voice_warning(line, flagged):
    pieces = {"email": {"key": "email", "channel": "email", "content": {"subject_options": ["A plain subject"], "preview": "p",
                                                                        "opening": "Hi,", "body": line, "ending": "Talk soon"}}}
    found = checks.voice_findings(pieces)
    assert bool(found) is flagged and all(f["severity"] == "warning" for f in found)


# Settings ---------------------------------------------------------------------------------------------------------------

def test_a_premise_finisher_plans_before_it_writes_under_its_own_prompt():
    class Storage:
        pack_finish_profile, pack_check_profile, pack_repair_profile = ("2026-10-27.pack-finish.v3", "2026-10-27.pack-check.v4",
                                                                        "2026-10-27.pack-repair.v2")
        pack_caption_profile, pack_refinish_profile = "2026-10-26.pack-caption.v1", "2026-10-27.pack-refinish.v2"
    found = runtime_v2.profiles(Storage())
    assert found["pack_plan"] == c2.PLAN_PROFILE and c2.output_model("pack_finish", c2.PLAN_PROFILE) is c2.PlanOutput
    plan = runtime_v2.template(c2.PLAN_PROFILE)
    assert "## 7. Several independent ideas" in plan and "openings" in plan
    Storage.pack_finish_profile, Storage.pack_refinish_profile = "2026-10-25.pack-finish.v2", "2026-10-26.pack-refinish.v1"
    assert "pack_plan" not in runtime_v2.profiles(Storage())


def test_round_two_profiles_are_released_and_chosen_by_setting_while_the_defaults_stay_as_before():
    from backend_pipeline.settings_store import PACK_PROFILES, BRIEF_WRITERS, PREMISE_WRITERS
    for stage, released in c2.RELEASED.items():
        assert PACK_PROFILES[stage] == released
    assert c2.PROFILES["pack_finish"] == "2026-10-25.pack-finish.v2" and c2.PROFILES["pack_check"] == "2026-10-26.pack-check.v3"
    assert "2026-10-27.pack-finish.v3" in c2.PREMISE_FINISHERS and "2026-10-27.pack-check.v4" in c2.EDITORIAL_CHECKS
    assert "v5.3" in BRIEF_WRITERS and PREMISE_WRITERS == ("v5.3",)
    for profile in c2.ROUND_TWO:
        assert "{{>" not in runtime_v2.template(profile)


def test_a_person_can_edit_a_v53_brief_at_gate_two_and_an_earlier_brief_still_dumps_as_stored():
    from backend_pipeline.briefs import validation_v3
    row = premise_row()
    row["selected_evidence"] = []
    row["content_body"]["review"]["ledger"] = {}
    full = validation_v3.rebuild(row, {"format_plan": {**row["content_body"]["document"]["body"]["format_plan"],
                                                       "reels": [{**r, "on_screen_hook": "A plainer hook"} if r["kind"] == "third" else r
                                                                 for r in row["content_body"]["document"]["body"]["format_plan"]["reels"]]}})
    assert full["format_plan"]["reels"][2]["on_screen_hook"] == "A plainer hook" and full["format_plan"]["premise_options"]
    old = brief_row()["content_body"]["document"]["body"]
    assert c4.BriefEditV4.model_validate(c4.writer_part_v4(old)).model_dump(mode="json")["format_plan"] == old["format_plan"]


def test_an_editorial_note_on_a_persons_line_is_kept_for_them_as_a_warning_and_never_repaired():
    handoff = handoff_v2(brief_row(locked=["format_plan.email.opening"]))
    draft = {**assemble.draft(handoff, finish_mode="finish", premises=True), "finish_mode": "finish", "premises": True}
    pieces = finish.apply(draft, c2.FinishOutputV3.model_validate(answer_v3()), "finish", handoff, plan_v3())["pieces"]
    _, skip = fidelity.view(pieces)
    opening = pieces["email"]["content"]["opening"]
    flags = fidelity.editorial_flags([{"piece": "email", "text": opening, "issue": "lead_quality", "why": "More tours beside quiet couples"}],
                                     pieces, skip)
    assert flags[0]["severity"] == "warning" and "a person wrote" in flags[0]["why"]
    assert fidelity.locked_leaf(pieces["email"], flags[0]["path"]), "the repair leaves a locked line alone"


# The second pass: the card's whole call for the plan, the turns behind each premise, repeated wording to the repair -------

CALL = [{"at": f"{m}:{s:02d}", "start_ms": (m * 60 + s) * 1000, "speaker": who, "said": said, "call_date": "2026-06-10"}
        for m, s, who, said in [(4, 0, "Strategist", "How do you answer a new inquiry?"),
                                (10, 40, "Owner", "We changed the tour calendar to Saturdays only."),
                                (11, 5, "Strategist", "That gives couples a clear day to plan around."),
                                (35, 0, "Owner", "Most couples book after the second visit.")]]


def test_the_turns_behind_each_premise_come_from_the_plans_times():
    from backend_pipeline.packs import call as card_call
    plan = plan_v3().model_copy(update={"reels": [r.model_copy(update={"timestamps": t}) for r, t in
                                                  zip(plan_v3().reels, [["4:00 the question"], ["10:40 to 11:05: the calendar"], ["35:00"]])]})
    found = card_call.material(CALL, plan)
    assert set(found) == {"reel_2", "reel_3"}, "Reel 1 keeps the brief's evidence"
    assert [t["at"] for t in found["reel_2"]] == ["10:40", "11:05"] and [t["at"] for t in found["reel_3"]] == ["35:00"]
    evidence = card_call.as_evidence(found)
    assert {e["quotable"] for e in evidence} == {False} and evidence[0]["start_ms"] == 640000
    assert evidence == card_call.as_evidence(found), "deterministic"


def test_the_checks_accept_a_figure_from_the_turns_behind_a_premise():
    from backend_pipeline.packs import call as card_call  # noqa: F401
    row = brief_row()
    pieces = {"email": {"key": "email", "channel": "email", "content": {"subject_options": ["A subject"], "preview": "p", "opening": "Hi,",
                                                                        "body": "About 40 couples booked after a second visit.", "ending": "Talk soon"}}}
    material = {"premise_material": {"reel_2": [{"at": "35:00", "speaker": "Owner", "said": "About 40 couples booked after a second visit.",
                                                 "call_date": None}]}}
    assert any(f["check"] == "pack.new_number" for f in checks.new_fact_findings(pieces, row))
    assert not any(f["check"] == "pack.new_number" for f in checks.new_fact_findings(pieces, row, material))


def test_wording_a_piece_repeats_from_an_earlier_one_goes_to_the_repair():
    handoff = handoff_v2(brief_row())
    draft = {**assemble.draft(handoff, finish_mode="finish", premises=True), "finish_mode": "finish", "premises": True}
    pieces = finish.apply(draft, c2.FinishOutputV3.model_validate(answer_v3()), "finish", handoff, plan_v3())["pieces"]
    line = "She told us the first reply usually takes two whole days to send out."
    pieces["email"]["content"]["body"] += "\n\n" + line
    pieces["carousel"]["content"]["slides"][2]["text"] = line
    _, skip = fidelity.view(pieces)
    flags = fidelity.repetition_flags(pieces, skip)
    assert [(f["piece"], f["issue"], f["severity"]) for f in flags if f["text"] == line] == [("carousel", "repetition", "warning")]
    assert "Email" in flags[0]["why"]


def test_finisher_v4_plans_with_plan_v2_and_reads_the_call():
    class Storage:
        pack_finish_profile, pack_check_profile, pack_repair_profile = ("2026-10-27.pack-finish.v4", "2026-10-27.pack-check.v4",
                                                                        "2026-10-27.pack-repair.v2")
        pack_caption_profile, pack_refinish_profile = "2026-10-26.pack-caption.v1", "2026-10-27.pack-refinish.v3"
    found = runtime_v2.profiles(Storage())
    assert found["pack_plan"] == "2026-10-27.pack-plan.v2" and "2026-10-27.pack-finish.v4" in c2.CALL_FINISHERS
    assert "`call`" in runtime_v2.template("2026-10-27.pack-plan.v2")
    assert "premise_material" in runtime_v2.template("2026-10-27.pack-finish.v4")
    assert c2.PROFILES["pack_finish"] == "2026-10-25.pack-finish.v2", "the default is unchanged"


def test_a_later_piece_repeating_a_persons_locked_line_is_flagged_and_the_locked_line_is_not():
    handoff = handoff_v2(brief_row())
    draft = {**assemble.draft(handoff, finish_mode="finish", premises=True), "finish_mode": "finish", "premises": True}
    pieces = finish.apply(draft, c2.FinishOutputV3.model_validate(answer_v3()), "finish", handoff, plan_v3())["pieces"]
    line = "I had a call with one of our venue clients about her first reply to couples."
    pieces["reel_1"]["content"]["script"] = line + " " + pieces["reel_1"]["content"]["script"]
    pieces["reel_1"]["locks"] = [{"path": "script", "author": "a@example.com", "delegated": False, "at": None, "origin": "gate_two"}]
    pieces["reel_2"]["content"]["script"] = line + " " + pieces["reel_2"]["content"]["script"]
    _, skip = fidelity.view(pieces)
    flagged = [(f["piece"], f["path"]) for f in fidelity.repetition_flags(pieces, skip) if f["text"] == line]
    assert flagged == [("reel_2", "script")]
