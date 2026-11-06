"""E.B26: strategist profile v6 and its benchmark report. Offline only: a fake provider, saved samples, no HTTP."""
from __future__ import annotations

import hashlib
import json
import sys

from backend_pipeline import settings_store
from backend_pipeline.angle_profiles import (EXAMPLE_PROVENANCE, STRATEGIST_TEMPLATES, STRATEGIST_V5_PROFILE,
                                             STRATEGIST_V6_PROFILE, card_contract, card_schema, check_live_profile,
                                             strategist_angle_prompt, strategist_user, uses_scene_references)
from backend_pipeline.card_contracts import WeeklyAngleCardsV5
from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT, Settings
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.tests.test_strategist_profile import card, strategist_settings, week  # noqa: F401 (fixture)
from backend_pipeline.tests.test_strategist_v5 import V5Provider

V6 = STRATEGIST_TEMPLATES[STRATEGIST_V6_PROFILE].read_text(encoding="utf-8")
V5 = STRATEGIST_TEMPLATES[STRATEGIST_V5_PROFILE].read_text(encoding="utf-8")


def test_v6_template_carries_e_b26_rules_and_keeps_v5s():
    text = V6.lower()
    for rule in (
            # Kept from v5.
            "strategic fit", "distinctiveness", "audience resonance", "several ideas", "second look", "pillar_notes",
            "series", "publishing_order", "no call evidence", "process catalogue", "never disparage referrals",
            "internal_insights", "verify before publishing",
            # E.B26 (section 1.9.2, ruling R-8, the content plan's mix, ce58751's held card).
            "attributed experience", "credit it to that person", '"our team"', "never turn attributed experience into a claim",
            "never drop it as unsupported", "states that view as she said it", "may challenge an idea or a belief common",
            "never questions the reader's competence", "never opens on pain or desperation",
            "mostly warm, attract for reach, about one convert", "include at least one attract card",
            "at most one title in the slate", "held for a later week", "do not lead with timestamps"):
        assert rule in text, rule
    assert len(V6) < len(V5) * 1.3, "v6 adds rules without bloating the prompt"


def test_v5_is_unchanged_for_replay():
    normalised = V5.replace("\r\n", "\n").encode("utf-8")
    assert hashlib.sha256(normalised).hexdigest() == "28cacd4d7ef3b57714ca388fd1294f47ed118767f28f7f7bc1db47c9ba3d4235"


def test_v6_template_passes_the_style_lint():
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    assert lint(V6) == []


def test_every_v6_example_is_invented_and_none_derives_from_a_benchmark_week():
    examples = EXAMPLE_PROVENANCE[STRATEGIST_V6_PROFILE]
    assert examples and all(e["derived_from_weeks"] == [] for e in examples)
    for example in examples:
        assert example["text"].split(";")[0][:40].lower() in V6.lower(), example["text"]
    # The benchmark's own Week 2 scenes (golden g07 and g09) are not quoted to the strategist.
    for phrase in ("market research", "100 clicks", "breathing room"):
        assert phrase not in V6.lower()


def test_v6_reads_the_knowledge_base_and_scenes_like_v5_with_the_same_contract():
    kb = load_knowledge_base(BACKEND_ROOT / "knowledge_base", stage="strategist")
    packet = [{"moment_id": "moment_a", "source_ids": ["zoom:w/call"], "source_metadata": {}, "sensitivity": "unknown",
               "qualifications": [], "source_evidence": [{"text": "How does your landing page describe pricing?",
                                                          "speaker": "Carmen", "start_seconds": 4}]}]
    seeds = [{"kind": "thought", "author": "Whitney", "text": "Reply with a date.", "target_offer": "LeadLock"}]
    v5_system, v5_user = strategist_angle_prompt(packet, kb, STRATEGIST_V5_PROFILE, seeds)
    v6_system, v6_user = strategist_angle_prompt(packet, kb, STRATEGIST_V6_PROFILE, seeds)
    assert v6_user == v5_user == strategist_user(packet, STRATEGIST_V6_PROFILE, seeds)
    assert v6_system.startswith(V6.strip()) and v6_system.removeprefix(V6.strip()) == v5_system.removeprefix(V5.strip())
    assert card_schema(STRATEGIST_V6_PROFILE) == card_schema(STRATEGIST_V5_PROFILE)
    assert card_contract(STRATEGIST_V6_PROFILE) is WeeklyAngleCardsV5 and uses_scene_references(STRATEGIST_V6_PROFILE)
    check_live_profile(STRATEGIST_V6_PROFILE, "live")


def test_v6_stays_selectable_after_v7_replaced_it_in_production():
    definition = settings_store.definition("prompts.profile.strategist")
    assert STRATEGIST_V6_PROFILE in definition.choices and definition.default != STRATEGIST_V6_PROFILE
    assert Settings(angle_prompt_profile=STRATEGIST_V6_PROFILE).angle_prompt_profile == STRATEGIST_V6_PROFILE
    production = json.loads((BACKEND_ROOT / "deploy" / "production-settings.json").read_text(encoding="utf-8"))
    # Production from 20 October (E.B26) until N2's minimal gate chose v7 (D40, 23 October); v6 stays a choice, the
    # setting WIA's switch-back would name (contingency A, D40).
    assert production["settings"]["prompts.profile.strategist"] != STRATEGIST_V6_PROFILE


def test_an_offline_v6_run_records_the_week_fields(week):  # noqa: F811
    provider = V5Provider()
    pipeline = Pipeline(strategist_settings(week, BACKEND_ROOT / "knowledge_base", angle_prompt_profile=STRATEGIST_V6_PROFILE),
                        provider)
    result = pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1} and result["angles"] == 2
    system, user, schema = provider.seen["angle_generation"]
    assert system.startswith(V6.strip()) and schema["title"] == "WeeklyAngleCardsV5"
    run_dir = f"experiments/default/runs/{result['run_id']}"
    assert pipeline.store.read_json(f"{run_dir}/angle_selection.json")["publishing_order"] == [2, 1]
    assert pipeline.store.read_json(f"{run_dir}/manifest.json")["input_refs"]["angle_prompt_profile"] == STRATEGIST_V6_PROFILE


# The benchmark: the v6 configuration and E.B26's report on saved samples.

def test_the_v6_benchmark_request_differs_from_v5_only_in_the_prompt():
    from evaluation import run
    v5, _ = run.request("strategist_v5", "week2")
    v6, moments = run.request("strategist_v6", "week2")
    assert run.CONFIGS["strategist_v6"] == {**run.CONFIGS["strategist_v5"], "profile": STRATEGIST_V6_PROFILE}
    assert v6["model"] == "openai/gpt-6.1-sol" and v6["reasoning"] == {"effort": "high"}
    assert v6["messages"][1] == v5["messages"][1] and v6["response_format"] == v5["response_format"]
    assert v6["messages"][0]["content"].startswith(V6.strip())
    assert run.generate("strategist_v6", "week2", 1, dry=True)["dry"] is True


def v6_record(titles_and_pillars, cites):
    angles = []
    for rank, ((title, pillar), (scene, perspective, action)) in enumerate(zip(titles_and_pillars, cites), 1):
        angles.append({**card(scene, rank, pillar=pillar, series=None), "title": title, "core_perspective": perspective,
                       "wia_in_action": action, "evidence_points": ["A team member spoke on the call."]})
    output = {"week_summary": "s", "angles": angles, "internal_insights": [], "considered_not_selected": [],
              "publishing_order": list(range(1, len(angles) + 1)), "pillar_notes": [], "seed_pairings": []}
    return {"sample": 1, "output": output}


def test_the_stance_report_finds_the_golden_scenes_and_checks_credit_claim_and_flags():
    from evaluation import stance
    goldens = stance.golden_scenes("week2")
    assert {g: (x["moment_id"], x["speaker"]) for g, x in goldens.items()} == {
        "g07": ("w2_m1_buying_research", "Whitney Hodges"), "g09": ("w2_m3_clicks_no_conversions", "Carmen Cruickshank")}
    record = v6_record(
        [("Reviews are not market research", "ATTRACT"), ("Why we wait before we judge a campaign", "WARM"),
         ("Your reviews tell couples you're lovely", "WARM")],
        [("S1", "Whitney's view: reviews are not market research, and real market research makes the ads stronger.",
          "Whitney described the buying-trigger survey WIA sends its own new clients."),
         ("S3", "Carmen waits for about 100 clicks before she judges a new campaign.",
          "Carmen checked how long visitors stayed on the landing page."),
         ("S1", "Glowing reviews and the reason a couple booked can tell us different things.",
          "The owner shared reviews.")])
    out = stance.sample_report("strategist_v6", "week2", record)
    assert out["attract_cards"] == 1 and out["template_titles"] == 1 and out["cards"] == 3
    g07 = {row["rank"]: row for row in out["scenes"]["g07"]["cards"]}
    assert g07[1]["survives"] and g07[1]["credited"] and g07[1]["claim_present"]
    assert not g07[3]["claim_present"] and not g07[3]["credited"], "the softened card loses the stance and the credit"
    [g09] = out["scenes"]["g09"]["cards"]
    assert g09["survives"] and g09["blocking_flags"] == [] and out["scenes"]["g09"]["survives"]


def test_the_stance_command_reads_saved_samples_only(monkeypatch, tmp_path):
    from backend_pipeline.llm import transport
    from evaluation import run, stance
    monkeypatch.setattr(run, "OUT", tmp_path)
    monkeypatch.setattr(transport, "send", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no paid call")))
    (tmp_path / "runs").mkdir()
    record = v6_record([("Reviews are not market research", "ATTRACT")],
                       [("S1", "Whitney's view: reviews are not market research.", "Whitney named the survey.")])
    (tmp_path / "runs" / "strategist_v6-week2-s1.kb.json").write_text(json.dumps(record), encoding="utf-8")
    result = stance.report(["strategist_v6"], ["week2"], 2, ".kb")["configs"]["strategist_v6"]["week2"]
    assert result["missing"] == ["strategist_v6-week2-s2.kb.json"]
    assert result["summary"] == {"samples": 1, "samples_with_attract": 1, "template_titles": "0 of 1",
                                 "g07_survives_in_samples": 1, "g09_survives_in_samples": 0}
