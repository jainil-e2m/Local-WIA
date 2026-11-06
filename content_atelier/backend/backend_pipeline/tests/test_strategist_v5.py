"""E.B21: strategist profile v5. Offline only: a fake provider, the committed knowledge base v2, no HTTP."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

from backend_pipeline.angle_profiles import (EXAMPLE_PROVENANCE, STRATEGIST_V5_PROFILE, STRATEGIST_TEMPLATES,
                                             card_schema, check_live_profile, strategist_angle_prompt, strategist_user)
from backend_pipeline.card_contracts import WeeklyAngleCardsV5
from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.tests.test_strategist_profile import SOL, card, strategist_settings, week  # noqa: F401 (fixture)

TEMPLATE = STRATEGIST_TEMPLATES[STRATEGIST_V5_PROFILE].read_text(encoding="utf-8")


def v5_output(scene="S1"):
    first, second = card(scene, 1, series="Watch Us Build an Ad Strategy"), card(scene, 2, pillar="ATTRACT",
                                                                               content_type="polarizing_opinion", series=None)
    return {"week_summary": "One planner call shows how WIA diagnoses lead quality. Publish rank 2, then rank 1 with the CTA.",
            "angles": [first, second],
            "internal_insights": [{"moment_ids": [scene], "insight": "Pricing objection.", "use": "Sales enablement."}],
            "considered_not_selected": [{"moment_ids": [scene], "idea": "Negative keyword tips.", "reason": "Too narrow."}],
            "publishing_order": [2, 1],
            "pillar_notes": [{"pillar": "CONVERT", "note": "No scene shows an offer decision this week."}],
            "seed_pairings": [{"seed_ref": "F1", "moment_ids": [scene], "note": "The call shows the diagnostic question."}]}


class V5Provider:
    def __init__(self):
        self.calls, self.seen = Counter(), {}

    def json_call(self, *, stage, system, user, schema, fingerprint):
        from backend_pipeline.tests.test_strategist_profile import CardProvider
        self.calls[stage] += 1
        self.seen[stage] = (system, user, schema)
        if stage == "moment_extraction":
            return CardProvider().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        output = v5_output()
        return output, {"fake": True, "raw": {"id": "synthetic-only", "usage": {"cost": 0},
                        "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]}}

    def embed(self, *, text, fingerprint):
        raise AssertionError("Embedding provider must remain disconnected")


def test_v5_template_contains_the_rules_e_b21_lists():
    text = TEMPLATE.lower()
    for rule in ("strategic fit", "distinctiveness", "audience resonance", "misconceptions", "objections", "aha moments",
                 "several ideas", "second look", "pillar_notes", "series", "publishing_order", "seed",
                 "no call evidence", "process catalogue", "rejection rules", "never disparage referrals"):
        assert rule in text, rule


def test_v5_template_passes_the_style_lint_on_its_own_text():
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    assert lint(TEMPLATE) == []


def test_every_v5_example_is_invented_and_none_derives_from_a_benchmark_week():
    examples = EXAMPLE_PROVENANCE[STRATEGIST_V5_PROFILE]
    assert examples and all(e["derived_from_weeks"] == [] for e in examples)
    for example in examples:
        assert example["text"].split(";")[0][:40].lower() in TEMPLATE.lower()


def test_v5_schema_adds_series_order_pillars_and_seeds_without_changing_v4():
    from backend_pipeline.angle_profiles import STRATEGIST_V4_PROFILE
    v5 = card_schema(STRATEGIST_V5_PROFILE)
    assert {"publishing_order", "pillar_notes", "seed_pairings"} <= set(v5["required"])
    assert "series" in json.dumps(v5)
    assert "series" not in json.dumps(card_schema(STRATEGIST_V4_PROFILE)), "v4's schema and saved requests are unchanged"
    with pytest.raises(ValueError, match="each at most once"):
        WeeklyAngleCardsV5.model_validate({**v5_output(), "publishing_order": [1, 1]})
    with pytest.raises(ValueError, match="angle ranks of this slate"):
        WeeklyAngleCardsV5.model_validate({**v5_output(), "publishing_order": [2, 1, 3]})
    # A card left out of the order is held for a later week (about three pieces a week, R-10), not a contract failure.
    held = WeeklyAngleCardsV5.model_validate({**v5_output(), "publishing_order": [2]})
    assert held.publishing_order == [2] and held.held == [1]
    check_live_profile(STRATEGIST_V5_PROFILE, "live")


def test_v5_user_message_has_scenes_and_seeds_but_no_reel_scripts():
    packet = [{"moment_id": "moment_a", "source_ids": ["zoom:w/call"], "source_metadata": {}, "sensitivity": "unknown",
               "qualifications": [], "source_evidence": [{"text": "How does your landing page describe pricing?",
                                                          "speaker": "Carmen", "start_seconds": 4}]}]
    seeds = [{"kind": "thought", "author": "Whitney", "text": "Couples book faster when the first reply names a date.",
              "target_offer": "LeadLock"}]
    user = strategist_user(packet, STRATEGIST_V5_PROFILE, seeds)
    assert "## Scene S1" in user and "Seed F1 (thought, from Whitney): Target offer: LeadLock." in user
    assert "Reel" not in user, "the Reels are exemplars in the knowledge base for v5 (E.B11 d)"
    assert "No founder seeds this cycle." in strategist_user(packet, STRATEGIST_V5_PROFILE)


def test_an_offline_v5_run_uses_the_committed_knowledge_base_and_records_the_week_fields(week):  # noqa: F811
    provider = V5Provider()
    settings = strategist_settings(week, BACKEND_ROOT / "knowledge_base", angle_prompt_profile=STRATEGIST_V5_PROFILE)
    pipeline = Pipeline(settings, provider)
    result = pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1} and result["angles"] == 2
    system, user, schema = provider.seen["angle_generation"]
    assert system.startswith(TEMPLATE.strip()) and "wia-kb-2026-10-22.c-a1a75795" in system
    assert "Exemplars (Whitney's published Reels" in system and "Format guide" not in system, "strategist stage only"
    assert "Reel scripts" not in user and schema["title"] == "WeeklyAngleCardsV5"
    run_dir = f"experiments/default/runs/{result['run_id']}"
    selection = pipeline.store.read_json(f"{run_dir}/angle_selection.json")
    assert selection["publishing_order"] == [2, 1] and selection["pillar_notes"][0]["pillar"] == "CONVERT"
    assert re.match(r"moment_", selection["seed_pairings"][0]["moment_ids"][0]), "seed scene references resolve to moments"
    cards = pipeline.store.read_json(f"{run_dir}/angle_cards.json")
    assert cards[0]["series"] == "Watch Us Build an Ad Strategy"
    manifest = pipeline.store.read_json(f"{run_dir}/manifest.json")
    assert manifest["input_refs"]["knowledge_base"]["stage"] == "strategist"
    # The committed version has no draft document; a run on a version with drafts names them (version 2 below).
    assert manifest["input_refs"]["knowledge_base"]["drafts_used"] == []
    v2 = load_knowledge_base(BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.v2", stage="strategist")
    assert "exemplars" in v2.refs()["drafts_used"]


def test_v5_card_edits_keep_the_series_field():
    from backend_pipeline.gate_one import edited_card_body
    body = {"card": card("moment_a", 1, series="Stop Boosting Posts"), "title": "t"}
    edited = edited_card_body(body, {"series": None, "title": "A plainer title"})
    assert edited["card"]["series"] is None and edited["title"] == "A plainer title"
    with pytest.raises(ValueError):
        edited_card_body({"card": card("moment_a", 1), "title": "t"}, {"series": "x"})


# A client result figure: a count of leads, bookings or weddings, a return, a dollar result, or a spelled-out sum.
RESULT_FIGURE = re.compile(
    r"\b\d[\d,]*\+?\s+(?:new\s+|more\s+|qualified\s+|booked\s+)?(?:leads?|inquiries|bookings?|weddings|events|consultations"
    r"|calls|followers|contracts|couples)\b|\bby\s+\d[\d,.]*\s?%|\b\d[\d,.]*\s?%\s+(?:return|roas)\b"
    r"|\b\d+(?:\.\d+)?\s?x\s+(?:return|roas)\b|\$\s?\d[\d,.]*\s?k\b|\$\s?\d[\d,.]*\s+(?:in\s+)?(?:booked|new|revenue|bookings|sales)\b"
    r"|\b(?:ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[- ]?(?:k|thousand)\b", re.I)
# Where a client figure is cleared: WIA's own published copy (the exemplars) and the results WIA published or the client
# allowed (Rulings 2.4); the register's private results carry no figure.
CLEARED_RESULTS = ("Published results", "Results the client has allowed")


def uncleared_result_figures(root: Path) -> list[str]:
    """Client result figures in the strategist request outside cleared material, unless the same figure is cleared."""
    kb = load_knowledge_base(root, stage="strategist")
    scenes = [{"moment_id": "m", "source_ids": ["z"], "source_metadata": {}, "sensitivity": "public_candidate",
               "qualifications": [], "source_evidence": [{"span_id": "s", "speaker": "A", "start_seconds": 1.0, "text": "Hi."}]}]
    system, user = strategist_angle_prompt(scenes, kb, STRATEGIST_V5_PROFILE)
    register = kb.document("results_register").text
    cleared = [kb.document("exemplars").text, *("## " + part for part in register.removeprefix("## ").split("\n\n## ")
                                                 if part.startswith(CLEARED_RESULTS))]
    rest = system + "\n" + user
    for part in cleared:
        assert part in rest
        rest = rest.replace(part, "")
    known = {" ".join(m.lower().split()) for part in cleared for m in RESULT_FIGURE.findall(part)}
    return sorted({m for m in RESULT_FIGURE.findall(rest) if " ".join(m.lower().split()) not in known})


def test_the_strategist_request_carries_no_client_result_figure_outside_cleared_material():
    """E.B11 (4): Whitney's Reel scripts (with their client results) no longer reach the strategist, and every client
    figure it receives is one WIA published or the client allowed. Version 5 still quotes, in a rule, the figure a venue
    client vetoed; version 6 removes it, and versions 7 and 8 (archived) keep it out. Version 9 (committed) carries two
    figures the check cannot clear by wording: "90 events" is the published ELEVATE result (KB 12, "Published results": 17
    events last year to 90 this year, which the register writes without the second "events"), in Whitney's own Reel in
    document 19; "17 weddings" is that document's note naming her slip, which RR-10 blocks in copy."""
    from backend_pipeline.prompts import REEL_CORPUS
    from backend_pipeline.tests.test_held_out import V5, V6, V7, V8
    reels = RESULT_FIGURE.findall(REEL_CORPUS.read_text(encoding="utf-8"))
    assert "Seventy K" in reels, "the check finds the Reels' client figures"
    assert uncleared_result_figures(V6) == [] and uncleared_result_figures(V7) == [] and uncleared_result_figures(V8) == []
    assert uncleared_result_figures(V5) == ["1,200 weddings"]
    assert uncleared_result_figures(BACKEND_ROOT / "knowledge_base") == ["17 weddings", "90 events"]


def test_the_harness_lint_module_exists():
    assert (Path(PROJECT_ROOT) / "research" / "chatgpt-export-2026-10-18" / "lint.py").is_file()
