"""E.X4 (provisional, revision 7): the committed production configuration is valid, and applying it is all or nothing."""
import json

import pytest

from backend_pipeline import settings_store
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.cycle.verification import family

PROFILE = BACKEND_ROOT / "deploy" / "production-settings.json"


def test_the_production_configuration_validates_and_moves_off_the_rated_defaults():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    typed = settings_store.validate_profile(profile)
    assert typed["prompts.profile.strategist"] != settings_store.default("prompts.profile.strategist"), \
        "production must not run the strategist WIA rated 1 of 5"
    # Brief contract v4 with writer v5.2 (N8, 25 October: v5.1 with identities, account memory and team-practice evidence,
    # after its paid brief on copy D; before it v5.1, NP.B10, and v5, N2's minimal gate, D40); the pair is checked together,
    # and the ledger's verifier comes from another family than the writer (R42).
    assert typed["prompts.profile.brief"] == "brief_document_v4" and typed["prompts.profile.brief_writer"] == "v5.3"
    # Round 2 (27 October): writer v5.3 and the pack's finisher v3, check v4, repair v2 and refinish v2.
    assert (typed["prompts.profile.pack_finish"], typed["prompts.profile.pack_check"], typed["prompts.profile.pack_repair"],
            typed["prompts.profile.pack_refinish"]) == ("2026-10-27.pack-finish.v4", "2026-10-27.pack-check.v4",
                                                       "2026-10-27.pack-repair.v2", "2026-10-27.pack-refinish.v3")
    # Strategist v9 since N11's benchmark (v8 since N8's readings before it); scene profile v4 (both keys) since N8's;
    # card verification v4 since N2's.
    assert typed["prompts.profile.strategist"] == "2026-10-25.wia-strategist.v9"
    assert typed["moments.extraction_profile"] == typed["prompts.profile.extraction"] == "2026-10-25.scenes.v4"
    # Internal meetings are evidence of how WIA works (D24, 1.B13's extension).
    assert "internal" in typed["documents.included_call_types"]
    assert typed["prompts.profile.card_verification"] == "card-verification.v4"
    assert family(typed["models.brief_review"]) != family(typed["models.brief"])
    for key in ("models.brief", "models.brief_review", "models.default"):
        assert key in typed, f"{key} is set explicitly, as a live brief requires (S.B8)"
    assert family(typed["models.card_verification"]) != family(typed["models.angle_generation"]), \
        "the verifier comes from another family than the strategist (E.B10)"


def test_the_production_configuration_turns_the_learning_loop_on_with_a_categoriser_of_another_family():
    """Revision 8 (M4 step 5): the weekly loop's paid categorisation is on in production, and its model is not the writer's."""
    typed = settings_store.validate_profile(json.loads(PROFILE.read_text(encoding="utf-8")))
    assert typed["context.schedule.mining_live"] is True and settings_store.default("context.schedule.mining_live") is False
    assert family(typed["models.context_mining"]) != family(typed["models.brief"])


def test_every_result_the_configuration_cites_is_committed_and_names_the_committed_knowledge_base():
    """R44: the configuration names the recorded results behind it; each is in the repository, and the knowledge-base
    benchmark it cites is the one of the committed version."""
    from backend_pipeline.knowledge_base import load_knowledge_base
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    paths = [entry.split(" (")[0] for entry in profile["evidence"]]
    missing = [p for p in paths if not (BACKEND_ROOT.parent / p).is_file()]
    assert paths and not missing, missing
    assert any(load_knowledge_base(BACKEND_ROOT / "knowledge_base").version in p for p in paths)


def test_a_file_with_one_bad_key_or_value_is_refused_whole():
    with pytest.raises(settings_store.SettingError, match="no.such.key|Unknown"):
        settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v2", "no.such.key": 1}})
    with pytest.raises(settings_store.SettingError):
        settings_store.validate_profile({"settings": {"prompts.profile.brief_writer": "v9"}})
    with pytest.raises(settings_store.SettingError):
        settings_store.validate_profile({"settings": {}})
