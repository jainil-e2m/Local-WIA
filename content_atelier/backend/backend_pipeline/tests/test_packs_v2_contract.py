"""Content pack contract v2 (NP.B1, NP.B5): the frozen contract both build tracks share. Synthetic data only (R48)."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from backend_pipeline.packs import contracts_v2 as c2
from backend_pipeline.packs import model


def test_gate_two_locks_translate_by_a_fixed_table_where_only_the_reel_index_changes():
    assert c2.translate_lock("format_plan.email.opening") == ("email", "opening")
    assert c2.translate_lock("format_plan.email.subject_options[0]") == ("email", "subject_options[0]")
    assert c2.translate_lock("format_plan.carousel.slides[2].text") == ("carousel", "slides[2].text")
    assert c2.translate_lock("format_plan.reels[0].caption.hook") == ("reel_1", "caption.hook")
    assert c2.translate_lock("format_plan.reels[1].screens[0]") == ("reel_2", "screens[0]")
    assert c2.translate_lock("format_plan.reels[1]") == ("reel_2", None), "a whole Reel"
    assert c2.translate_lock("format_plan") == ("*", None), "the whole format plan, as locks were recorded before 22 October"
    assert c2.translate_lock("wia_perspective") is None, "a strategy line has no piece"
    assert c2.translate_lock("supporting_example.scene") is None


def test_a_person_edits_copy_leaves_never_direction():
    assert c2.is_editable("email", "subject_options[1]") and c2.is_editable("email", "send_header.date")
    assert c2.is_editable("carousel", "slides[3].text") and not c2.is_editable("carousel", "slides[3].number")
    assert not c2.is_editable("carousel", "slides[3].job")
    assert c2.is_editable("reel", "caption.hook") and c2.is_editable("reel", "cover_alternates[0]")
    assert not c2.is_editable("reel", "kind") and not c2.is_editable("reel", "beats[0]")
    assert not c2.is_editable("email", "cta"), "the CTA kind is the brief's decision"


def test_the_wire_schemas_leave_out_what_anthropics_structured_output_refuses():
    def keywords(node, out):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("properties", "$defs"):
                    for sub in v.values():
                        keywords(sub, out)
                else:
                    out.add(k)
                    keywords(v, out)
        elif isinstance(node, list):
            for v in node:
                keywords(v, out)
        return out
    for stage in c2.OUTPUTS:
        used = keywords(c2.wire_schema(stage), set())
        assert not used & {"pattern", "minLength", "maxLength", "title", "maxItems", "minimum", "maximum"}, stage
        assert '"additionalProperties": false' in json.dumps(c2.wire_schema(stage)), "strict objects"
    reel = c2.wire_schema("pack_finish")["$defs"]["FinishReel"]
    assert "title" in reel["properties"] and "title" in reel["required"], "a field named title is kept"


def _reel(kind):
    return {"kind": kind, "title": "A working title", "job": "Its job", "cover_text": "Cover", "cover_alternates": ["A", "B"],
            "on_screen_hook": "Hook", "spoken_opening": None if kind == "broll_text" else "Hi", "script": None if kind == "broll_text" else "Script",
            "screens": ["One", "Two"] if kind == "broll_text" else None, "beats": ["Beat"],
            "caption": {"hook": "h", "body": "b", "ending": "-Whitney"}, "personal_lines": [], "read_time_seconds": 40,
            "cta": "none", "no_offer_ending": None, "offer_descriptor": None}


def _finish(reels):
    return {"email": {"subject_options": ["One", "Two", "Three"], "preview": "p", "opening": "Hi {{contact.first_name}},",
                      "body": "b", "ending": "Talk soon,\nWhitney", "offer_descriptor": None, "cta": "reply"},
            "reels": reels, "carousel": {"title": "T", "slides": [{"number": n, "text": f"Slide {n}"} for n in range(1, 8)],
                                          "caption": {"hook": "h", "body": "b", "ending": "e"}, "cta": "none",
                                          "no_offer_ending": None, "offer_descriptor": None},
            "client_quotes": [], "stronger_with_permission": [], "pack_notes": [], "change_notes": []}


def test_the_finisher_returns_exactly_three_reels():
    c2.FinishOutput.model_validate(_finish([_reel(k) for k in c2.REEL_KINDS]))
    with pytest.raises(ValidationError):
        c2.FinishOutput.model_validate(_finish([_reel("story"), _reel("broll_text")]))


def test_marks_on_notes_stay_outside_the_manifest_so_a_clearance_never_changes_readiness():
    body = {"before_publishing": [{"id": "P1", "text": "Client's okay", "done": None}],
            "client_quotes": [{"quote_id": "Q1", "quote": "x", "cleared": None}], "title": "T"}
    marked = {**body, "before_publishing": [{"id": "P1", "text": "Client's okay", "done": {"by": "a", "at": "t"}}],
              "client_quotes": [{"quote_id": "Q1", "quote": "x", "cleared": {"by": "a", "at": "t"}}]}
    pack = {"source_brief_id": "b", "source_brief_hash": "h", "content_body": body}
    rows = [{"slot_key": "email", "ordinal": 1, "content_hash": "e"}]
    assert model.manifest(pack, rows) == model.manifest({**pack, "content_body": marked}, rows)
    assert model.manifest(pack, rows) != model.manifest({**pack, "content_body": {**body, "title": "Other"}}, rows)


def test_the_pack_reads_as_a_v4_format_plan_with_reels_in_kind_order_and_no_pack_extras():
    pieces = {"reel_1": {"content": {**_reel("story"), "register": "spoken", "source": "new_script"}},
              "reel_2": {"content": None}, "reel_3": {"content": {**_reel("broll_text"), "register": "on_screen", "source": "new_script"}},
              "carousel": {"content": None}, "email": {"content": None}}
    plan = model.v4_format_plan(pieces)
    assert [r["kind"] for r in plan["reels"]] == ["story", "broll_text"], "a not-written Reel is left out"
    assert "title" not in plan["reels"][0] and "cover_alternates" not in plan["reels"][0] and "cta" not in plan["reels"][0]
    assert plan["carousel"] is None and plan["email"] is None and plan["stories"] is None


def test_the_new_settings_have_their_defaults_and_the_pack_writer_runs_at_medium_effort():
    from backend_pipeline.config import Settings
    from backend_pipeline.settings_store import _BY_KEY
    assert _BY_KEY["packs.finish_mode"].default == "finish"
    assert _BY_KEY["prompts.profile.pack_finish"].default == c2.PROFILES["pack_finish"] == "2026-10-25.pack-finish.v2"
    assert _BY_KEY["features.packs"].default is False, "packs stay off until a deployment turns them on"
    models = Settings()
    assert models.reasoning_effort_for("pack_finish") == "medium" and models.reasoning_effort_for("pack_repair") == "medium"
    assert models.reasoning_effort_for("pack_check") == "medium" and models.reasoning_effort_for("pack_recheck") == "medium"


def test_an_opus_request_has_no_temperature_asks_for_usage_and_has_a_price():
    from backend_pipeline.costs import estimate_usd
    from backend_pipeline.llm.request import chat_body
    body = chat_body(model="anthropic/claude-opus-5.5", system="s", user="u", schema={"type": "object"}, max_tokens=100,
                     reasoning_effort="medium")
    assert "temperature" not in body and body["usage"] == {"include": True} and body["reasoning"] == {"effort": "medium"}
    assert estimate_usd("anthropic/claude-opus-5.5", 1_000_000, 1_000_000) == 24.0


def test_the_live_provider_accepts_every_pack_stage():
    """NP.X2a found the live provider refusing pack stages as unsupported: every model stage of the pack is a JSON stage."""
    from backend_pipeline.llm.providers import JSON_STAGES
    assert set(c2.MODEL_STAGES) <= JSON_STAGES


def test_a_saved_answer_of_every_pack_stage_is_a_valid_stage_artifact():
    """The NP exit test found StageArtifact refusing the v2 pack stages, so no answer could be saved or replayed."""
    from typing import get_args
    from backend_pipeline.models import StageArtifact
    assert set(c2.MODEL_STAGES) <= set(get_args(StageArtifact.model_fields["stage"].annotation))


def test_budgets_set_accepts_the_packs_purpose(capsys):
    """Found in NP.X1: `storage_cli budgets set` listed the six purposes by hand, so the packs cap could not be set."""
    from backend_pipeline import storage_cli
    with pytest.raises(SystemExit):
        storage_cli.main(["budgets", "set", "--help"])
    assert "packs" in capsys.readouterr().out


def test_a_frozen_execution_contract_still_matches_after_the_database_round_trip():
    """NP.X1: the knowledge base's stable refs hold tuples, which JSON (the run's input_refs) turns into lists; a frozen
    contract read back must still equal the one computed now, and the output cap stays outside it (K74)."""
    import json
    from backend_pipeline.packs.runtime_v2 import stable_contract
    contract = {"version": c2.VERSION, "writer": "anthropic/claude-opus-5.5", "max_tokens": 32000,
                "knowledge_base": {"version": "kb-9", "manifest_sha256": "m", "documents": [{"key": "founder_voice_guide", "sha256": "a"},
                                                                                           {"key": "cta_catalogue", "sha256": "b"}],
                                   "context": {"source": "database", "on": "2026-10-24", "items": {"cta_catalogue": [{"id": "i1"}]}}}}
    stored = json.loads(json.dumps(contract))
    later = {**contract, "max_tokens": 48000,
             "knowledge_base": {**contract["knowledge_base"], "context": {"source": "database", "on": "2026-10-25", "items": {}}}}
    assert stable_contract(stored) == stable_contract(contract) == stable_contract(later)
    changed = {**contract, "knowledge_base": {**contract["knowledge_base"], "documents": [{"key": "founder_voice_guide", "sha256": "z"}]}}
    assert stable_contract(changed) != stable_contract(stored), "an identity document's change still voids the run"


def test_a_refused_free_request_names_the_free_policy_it_was_sent_under():
    """NP.X1: OpenRouter refused a free model because the account's data policy excludes free endpoints; the message named
    the paid policy, which the request was not sent under."""
    import httpx
    from backend_pipeline.llm.routing import FREE_POLICY, RoutingError, raise_for_routing
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions", json={"model": "x/y:free"})
    with pytest.raises(RoutingError, match=FREE_POLICY):
        raise_for_routing(httpx.Response(404, json={"error": {"message": "No endpoints"}}, request=request))


def test_every_released_pack_profile_stays_selectable_and_v2_keeps_the_example_s_own_order_and_outcome():
    """NP.X3's stop rule: v2 is the default; v1 stays selectable so a pack made under it replays (the frozen contract).
    Round 2's profiles are released and selected by setting; the default stays the last profile before them."""
    from types import SimpleNamespace
    from backend_pipeline.packs import runtime_v2
    from backend_pipeline.settings_store import _BY_KEY, PACK_PROFILES
    assert PACK_PROFILES == c2.RELEASED
    for stage, released in c2.RELEASED.items():
        before = [p for p in released if p not in c2.ROUND_TWO]
        assert _BY_KEY[f"prompts.profile.{stage}"].choices == released and c2.PROFILES[stage] == before[-1]
        assert _BY_KEY[f"prompts.profile.{stage}"].default == before[-1]
        for profile in released:
            assert runtime_v2.template(profile).strip(), profile
    v1 = SimpleNamespace(pack_finish_profile="2026-10-25.pack-finish.v1", pack_check_profile="2026-10-25.pack-check.v1",
                         pack_repair_profile="2026-10-25.pack-repair.v1")
    assert runtime_v2.profiles(v1)["pack_recheck"] == "2026-10-25.pack-check.v1"
    finish, check = runtime_v2.template(c2.PROFILES["pack_finish"]), runtime_v2.template(c2.PROFILES["pack_check"])
    assert "supporting example's own order and outcome" in finish and '"ended up with"' in finish
    assert "asks for nothing" in finish, "the carousel's close asks for nothing when Instagram keeps no offer"
    assert '"ended up with"' in check and "standard close, not an offer ask" in check
    # v3 (NP-7): the approved stance is a source, and one moment widened into a practice is unsupported (NP.X5's two cases).
    assert c2.PROFILES["pack_check"] == "2026-10-26.pack-check.v3"
    assert "approved_perspective" in check and "One moment is not a practice" in check and "by placement too" in check


def test_the_pack_stages_wire_schemas_are_pinned_because_a_saved_answer_replays_only_under_its_schema():
    """NP-6: editing a contract model's docstring changed the finisher's wire schema (descriptions are part of it), so the
    paid proof's saved answers stopped matching on production. A wire-schema change voids every saved pack answer: make it
    only with a new profile and a note in the record, and then update these hashes."""
    from backend_pipeline.store import canonical_hash
    # NP-7 added the post-recording pass's schema and the refinish (the finisher's schema); the four before are unchanged.
    assert {s: canonical_hash(c2.wire_schema(s)) for s in sorted(c2.OUTPUTS)} == {
        "pack_caption": "5e4d456ec6ab3131a189465ed12acb4b4cae4329a486661fc20cd6e230f85e02",
        "pack_refinish": "298e8b2ea3ebfda413e010f7b13dc2d6d7fbb09df0619b065d90b4267e44b84b",
        "pack_check": "12b74f7e529a1dc2e9192a65eab7b84e2554501a94ad8af188b500c2113657e4",
        "pack_finish": "298e8b2ea3ebfda413e010f7b13dc2d6d7fbb09df0619b065d90b4267e44b84b",
        "pack_recheck": "12b74f7e529a1dc2e9192a65eab7b84e2554501a94ad8af188b500c2113657e4",
        "pack_repair": "3ca8c7a424998ec6dbb67e6bfe64f293a01495ca685f8979e262acd9d0e51641"}
