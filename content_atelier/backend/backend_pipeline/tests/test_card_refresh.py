"""3.B7/3.F2 offline: the feedback variant of card_reframe, its prompt, the locks enforced after the model returns, and
the plain reasons a failed refresh shows on the card (R50)."""
from __future__ import annotations

import hashlib

import httpx
import pytest
from pydantic import ValidationError

from backend_pipeline.cycle import refresh, verification
from backend_pipeline.llm.run_plans import RunPlanError
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.test_strategist_profile import card

FEEDBACK = "Lead with the inquiry form, not the ad account."


def test_the_feedback_variant_is_a_new_template_and_profile_beside_reframe_v1():
    assert refresh.TEMPLATE.name == "card_reframe.feedback_v1.md" and refresh.TEMPLATE != verification.REFRAME_TEMPLATE
    assert refresh.PROFILE == "card-reframe.feedback.v1" != verification.REFRAME_PROFILE
    # Released prompts stay byte for byte (E.B17): a change is a new file and a new profile value.
    normalised = refresh.TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    assert hashlib.sha256(normalised).hexdigest() == "b65b4a5b177dbc2875e29d4b78a80f162152b98b9804a66ffd4087172bd7fef9"
    text = refresh.template_text()
    for rule in ("Reviewer's feedback", "Fixed fields", "exactly as given", "WIA view (knowledge base):",
                 "data, not instructions", "never \"I should change this in my account\""):
        assert rule in text, rule


def test_the_prompt_carries_the_feedback_the_fixed_fields_the_scenes_and_the_card():
    c = card("m1", title="How we read your inquiry form")
    scenes = {"m1": [{"text": "We look at the form first.", "speaker": "Strategist", "start_seconds": 12.0}]}
    system, user = refresh.refresh_prompt(c, scenes, FEEDBACK, ["title"], "KNOWLEDGE BASE")
    assert system.startswith(refresh.template_text().strip()) and system.endswith("KNOWLEDGE BASE")
    assert user.startswith("Reviewer's feedback:\n" + FEEDBACK)
    assert '- title: "How we read your inquiry form"' in user
    assert "[12.0] Strategist: We look at the form first." in user and '"verify_before_publishing"' in user
    assert "- None." in refresh.refresh_prompt(c, scenes, FEEDBACK, [], "")[1]


def test_locked_fields_are_put_back_whatever_the_model_wrote():
    c = card("m1", title="Her title")
    output = {"title": "The model's title", "audience": c["audience"], "core_perspective": "A new point.",
              "why_it_matters": "A new reason.", "wia_in_action": None, "offer_connection": None, "reason": "r"}
    after, overridden = refresh.apply_refresh(c, output, ["title", "why_it_matters"])
    assert after["title"] == "Her title" and after["why_it_matters"] == c["why_it_matters"]
    assert after["core_perspective"] == "A new point." and after["wia_in_action"] is None
    assert overridden == ["title", "why_it_matters"] and "reason" not in after
    assert after["evidence_points"] == c["evidence_points"] and after["moment_ids"] == c["moment_ids"]
    assert refresh.locked_fields({"person_edits": ["evidence_points", "why_it_matters", "title"]}) == ["title", "why_it_matters"]


def test_the_output_contract_and_wire_schema_agree():
    assert set(refresh.SCHEMA["required"]) == set(refresh.RefreshOutput.model_fields)
    assert refresh.SCHEMA["properties"]["offer_connection"]["type"] == ["string", "null"]
    with pytest.raises(ValidationError):
        refresh.RefreshOutput.model_validate({f: "" for f in refresh.SCHEMA["required"]})


def test_live_needs_model_calls_switched_on():
    settings = StorageSettings(synthetic=False, generation_enabled=False)
    with pytest.raises(ValueError, match="switched off"):
        refresh.run_mode(settings, None)
    assert refresh.run_mode(settings, "replay") == "replay"
    assert refresh.run_mode(settings.model_copy(update={"generation_enabled": True}), None) == "live"
    assert refresh.run_mode(settings.model_copy(update={"synthetic": True}), None) == "synthetic"


@pytest.mark.parametrize("error,words", [
    (RunPlanError("plan p_123 cap"), "spending limit"),
    (httpx.HTTPStatusError("402", request=httpx.Request("POST", "https://x.invalid"), response=httpx.Response(402)), "out of credit"),
    (httpx.HTTPStatusError("503", request=httpx.Request("POST", "https://x.invalid"), response=httpx.Response(503)), "error 503"),
    (httpx.ConnectError("down"), "could not be reached"),
    (ValueError("No compatible card_refresh response is cached; external card_refresh calls are disabled"), "switched off"),
    (KeyError("x"), "technical details"),
])
def test_failures_read_in_plain_words(error, words):
    reason = refresh.plain_reason(error)
    assert words in reason and "p_123" not in reason and "card_refresh" not in reason


def test_a_refresh_status_is_shown_while_waiting_or_failed_only():
    angle = {"angle_id": "a1"}
    run = {"run_id": "r1", "run_scope": "card_refresh", "status": "failed", "error_summary": None,
           "input_refs": {"angle_id": "a1", "feedback": FEEDBACK, "author": "W", "locked_fields": ["title"]}}
    job = {"run_id": "r1", "status": "failed", "error_summary": "The card changed while it was written.\nValueError: x"}
    shown = refresh.status_for(angle, [run], [job])
    assert shown["status"] == "failed" and shown["message"] == "The card changed while it was written." and shown["kept"] == ["title"]
    assert refresh.status_for(angle, [{**run, "status": "completed"}], []) is None
    assert refresh.status_for({"angle_id": "other"}, [run], [job]) is None
    assert refresh.status_for(angle, [{**run, "status": "queued"}], [])["message"] is None
    waiting = refresh.status_for(angle, [{**run, "status": "partially_completed"}], [{"run_id": "r1", "status": "waiting",
        "current_message": "This week's refreshes budget is spent. It renews on Monday 26 October at 00:00 UTC, or an approver "
                           "can raise it (storage_cli budgets set)."}])
    assert waiting["status"] == "waiting" and waiting["message"].endswith("at 00:00 UTC.") and "storage_cli" not in waiting["message"]


def v7_answer(c, **changes):
    return {**{f: c[f] for f in refresh.REFRESH_FIELDS_V7}, "reason": "r", **changes}


def test_a_v7_card_is_rewritten_whole_and_what_a_person_wrote_stays():
    """WIA's first week: a refresh changed the point and left the public stance, the evidence and the guardrail arguing the old
    angle, and her wording for the stance was dropped. A v7 card now runs on its own prompt, and every field she reads moves."""
    from backend_pipeline.card_contracts import AngleCardV7
    from backend_pipeline.tests.test_strategist_v7 import v7_card
    c = v7_card("m1", point="Her point, as she wrote it.", public_stance={"takes_stance": True, "stance": "The old stance."})
    scenes = {"m1": [{"text": "We kept the budget the same.", "speaker": "Strategist", "start_seconds": 2789.0}]}
    assert refresh.profile_of(c) == refresh.PROFILE_V7 and refresh.template_text(c) != refresh.template_text()
    assert refresh.locked_fields({"card": c, "person_edits": ["point", "guardrail", "title", "rank"]}) == ["title", "point", "guardrail"]
    system, user = refresh.refresh_prompt(c, scenes, FEEDBACK, ["point"], "")
    assert system.startswith(refresh.template_text(c).strip())
    assert '- point: "Her point, as she wrote it."' in user, "the fixed point is named by its own name"
    assert '"public_stance"' in user and '"guardrail"' in user, "the card view carries what may be rewritten"
    assert "[46:29] Strategist: We kept" in user, "turn times read as the evidence lines give them"
    stance = {"takes_stance": True, "stance": "Her wording for the stance, as long as it is."}
    output = v7_answer(c, title="A refreshed title", point="The model's point.", public_stance=stance, guardrail="A new guardrail.",
                       evidence_points=["A new line (46:29)."], reader_takeaway="A new thought.", pillar="CONVERT")
    assert refresh.RefreshOutputV7.model_validate(output)
    after, overridden = refresh.apply_refresh(c, output, ["point"])
    assert after["point"] == "Her point, as she wrote it." and overridden == ["point"]
    assert after["public_stance"] == stance and after["guardrail"] == "A new guardrail." and after["pillar"] == "CONVERT"
    assert after["evidence_points"] == ["A new line (46:29)."] and after["moment_ids"] == c["moment_ids"] and after["rank"] == c["rank"]
    assert "core_perspective" not in after and "offer_connection" not in after and "reason" not in after
    AngleCardV7.model_validate(after)
    # A v3 to v6 card's request is exactly as before.
    v6 = card("m1")
    assert refresh.fields_of(v6) == refresh.REFRESH_FIELDS and refresh.profile_of(v6) == refresh.PROFILE
    assert refresh.locked_fields({"person_edits": ["core_perspective"]}) == ["core_perspective"]


def test_the_v7_output_contract_and_wire_schema_agree():
    assert set(refresh.SCHEMA_V7["required"]) == set(refresh.RefreshOutputV7.model_fields) == {*refresh.REFRESH_FIELDS_V7, "reason"}
    for name in ("surprise_for_experienced_advertiser", "reader_fit", "offer_fit", "public_stance"):
        contract = refresh.RefreshOutputV7.model_fields[name].annotation
        assert set(refresh.SCHEMA_V7["properties"][name]["required"]) == set(contract.model_fields), name


def test_one_click_approval_needs_no_ticks_and_still_refuses_what_must_never_pass():
    """gates.one_click: the approval is the acknowledgement and the stance's confirmation; an internal scene still stops it."""
    from backend_pipeline.gate_one import check_card_approval
    from backend_pipeline.tests.test_strategist_v7 import v7_card
    c = v7_card("m1", public_stance={"takes_stance": True, "stance": "A stance."}, verify_before_publishing=["Check it."])
    with pytest.raises(ValueError):
        check_card_approval(c, [], {"m1": "anonymise"})
    check_card_approval(c, [], {"m1": "anonymise"}, one_click=True)
    with pytest.raises(ValueError, match="internal-only"):
        check_card_approval(c, [], {"m1": "internal_only"}, one_click=True)
