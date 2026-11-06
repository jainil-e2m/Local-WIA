"""E.B30, E.B32, E.B29 (change): strategist profile v7 and card verification v4. Offline only: constructed cards, a fake
provider, the committed knowledge base; no HTTP. Every example is invented or anonymised (R48)."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter

import pytest
from pydantic import ValidationError

from backend_pipeline import gate_one, settings_store
from backend_pipeline.angle_profiles import (EXAMPLE_PROVENANCE, STRATEGIST_TEMPLATES, STRATEGIST_V6_PROFILE, STRATEGIST_V7_PROFILE,
                                             card_contract, card_schema, check_live_profile, conversation_problems,
                                             demote_same_conversation, order_packet, strategist_angle_prompt, strategist_user)
from backend_pipeline.card_contracts import (AngleCardV5, AngleCardV7, WeeklyAngleCardsV7, card_contract_for, card_point,
                                             is_v7)
from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT, Settings
from backend_pipeline.contracts import signature_from_fields
from backend_pipeline.cycle import verification as v
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.tests.test_strategist_profile import card, strategist_settings, week  # noqa: F401 (fixture)

V7 = STRATEGIST_TEMPLATES[STRATEGIST_V7_PROFILE].read_text(encoding="utf-8")
V6 = STRATEGIST_TEMPLATES[STRATEGIST_V6_PROFILE].read_text(encoding="utf-8")
ROSTER = [{"name": "Team Member", "role": "strategist", "status": "current", "aliases": ["Team Member", "Team"]}]
SCENES = {"moment_a": [{"text": "I'd keep your budget where it is until the new page has a month of inquiries.",
                        "speaker": "Team Member", "start_seconds": 845}]}
PUBLIC_USE = set(v.PUBLIC_USE_KINDS)


def v7_card(scene="S1", rank=1, **changes):
    """A card that passes every test: a WIA standard, a reader's thought, an established reader."""
    value = {
        "rank": rank, "title": f"How we decide when a florist's ad budget should grow, idea {rank}", "pillar": "WARM",
        "content_type": "behind_the_scenes", "series": None, "audience": "Established florists who already run ads.",
        "why_it_matters": "Owners hear 'spend more' from every platform; a team that says 'not yet' is rare.",
        "wia_in_action": "Our strategist kept the budget the same until the new page had a month of inquiries.",
        "evidence_points": ["The strategist recommends keeping the budget where it is until the new page has a month of inquiries (14:05)."],
        "guardrail": "Never present the florist's old page as a failing; the strategist decided, not the owner. Next: a WARM Reel.",
        "point": "We grow a budget only after the page has proved itself, because more spend on an unproven page buys nothing.",
        "point_is_about": "wia_standard",
        "surprise_for_experienced_advertiser": {"surprising": True, "reason": "Agencies usually ask for more budget first."},
        "reader_takeaway": "I want a team that tells me when not to spend.",
        "reader_fit": {"buyer": "elevate", "buyer_statement": "Established owners who already invest and want to double down on what works.",
                       "why": "The reader already runs ads and wants judgement, not more spend."},
        "belief_ref": "B1",
        "offer_fit": {"offer": "ELEVATE", "cta_slot": "soft_invitation", "calendar_note": "ELEVATE is on the waitlist this window."},
        "public_stance": {"takes_stance": False, "stance": None},
        "recurrence": None,
        "moment_ids": [scene], "verify_before_publishing": ["Confirm the florist may be referenced."],
        "why_selected": "A counter-expected decision that shows WIA's judgement.",
    }
    value.update(changes)
    return value


def v7_output(cards=None, **changes):
    value = {"week_summary": "One call shows WIA holding a budget back until the page proves itself.",
             "angles": cards if cards is not None else [v7_card()],
             "internal_insights": [], "considered_not_selected": [{"moment_ids": ["S1"], "idea": "Budget tips.", "reason": "A tactic."}],
             "publishing_order": [1], "pillar_notes": [], "seed_pairings": []}
    value.update(changes)
    return value


def ledger_of(card_value, **kw):
    resolved = {**card_value, "moment_ids": ["moment_a"]}
    return v.verify_card(resolved, SCENES, ROSTER, [], **kw)


def public_kinds(ledger):
    return sorted(f["kind"] for f in ledger["flags"] if f["kind"] in PUBLIC_USE)


# The template and its provenance -------------------------------------------------------------------------------

def test_v7_template_carries_the_method_the_five_tests_and_her_card_format():
    text = V7.lower()
    for rule in ("strategy brief", "belief_ref", "human line", "counter-expected decision", "one real moment proves",
                 "point, not subject", "surprise", "takeaway", "reader", "fit", "platform_or_tactic",
                 "i want a team that thinks like this", "never an instruction", "never present ads or a wia offer as frustrating",
                 "never undercuts an offer", "one public card per client conversation", "never rank a card higher because of it",
                 "how we...", "what our...", "what goes into our...", "guardrail", "public_stance", "document 19", "if it does not",
                 "attributed experience", "never disparage referrals", "internal_insights", "verify before publishing"):
        assert rule in text, rule
    # v6's limit on "we"-led titles is dropped (D32).
    assert "at most one title in the slate" not in text


def test_v6_and_verification_v3_are_unchanged_for_replay():
    def digest(name):
        path = BACKEND_ROOT / "backend_pipeline" / "prompt_templates" / name
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert digest("angle_generation.wia_strategist_v6.md") == "7cd9af2696b4983eefbd932dbaec5a0fc7a24abfa2ebf992f3ae10972424786b"
    assert digest("card_verification.v3.md") == "262d4f8a315d9bc4138710be7bd1b0e05ae8d1842dbf1c5202268ccfecced397"
    assert "at most one title in the slate" in V6.lower()


def test_v7_template_passes_the_style_lint():
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    assert lint(V7) == []


def test_v7_contrasts_come_from_week_1_only_and_name_no_one():
    examples = EXAMPLE_PROVENANCE[STRATEGIST_V7_PROFILE]
    assert examples and all(set(e["derived_from_weeks"]) <= {1} for e in examples)
    for example in examples:
        assert example["text"].lower() in V7.lower(), example["text"]
    # Week 2's scenes and its hand-built packs never reach the prompt (D28), nor do Week 1's people or places.
    for phrase in ("office hours", "budget reset", "beyond the ads", "on paper", "i don't know what we changed", "market research",
                   "shannon", "colorado", "florida", "leadlock objection"):
        assert phrase not in V7.lower(), phrase
    check_live_profile(STRATEGIST_V7_PROFILE, "live")


def test_v7_stays_selectable_as_the_switch_back_and_is_not_the_code_default():
    definition = settings_store.definition("prompts.profile.strategist")
    assert STRATEGIST_V7_PROFILE in definition.choices and definition.default != STRATEGIST_V7_PROFILE
    assert Settings(angle_prompt_profile=STRATEGIST_V7_PROFILE).angle_prompt_profile == STRATEGIST_V7_PROFILE
    production = json.loads((BACKEND_ROOT / "deploy" / "production-settings.json").read_text(encoding="utf-8"))
    # v7 passed N2's card reading (D40); v8 (v7 with identities, team practice and founder notes) replaced it in N8's reading,
    # and v9 (v8 with decisions and stakes in public) replaced v8 in N11's benchmark; v8 and v7 stay as switch-backs.
    assert production["settings"]["prompts.profile.strategist"] == "2026-10-25.wia-strategist.v9"
    verification_profile = settings_store.definition("prompts.profile.card_verification")
    assert verification_profile.default == "card-verification.v3" and "card-verification.v4" in verification_profile.choices


# The contract ------------------------------------------------------------------------------------------------

def test_the_v7_contract_parses_her_fields_and_the_point_tests():
    parsed = WeeklyAngleCardsV7.model_validate(v7_output())
    assert parsed.angles[0].point.startswith("We grow a budget") and parsed.angles[0].guardrail
    assert card_contract(STRATEGIST_V7_PROFILE) is WeeklyAngleCardsV7
    schema = card_schema(STRATEGIST_V7_PROFILE)
    assert schema["title"] == "WeeklyAngleCardsV7"
    item = schema["$defs"]["AngleCardV7"]
    assert {"point", "point_is_about", "surprise_for_experienced_advertiser", "reader_takeaway", "reader_fit", "belief_ref",
            "offer_fit", "public_stance", "guardrail", "recurrence"} <= set(item["required"])
    assert "core_perspective" not in item["properties"]
    for broken in ({"point": None}, {"point_is_about": "a hunch"}, {"evidence_points": ["a", "b", "c", "d"]},
                   {"reader_fit": {"buyer": "elevate", "why": "x"}}, {"guardrail": ""}):
        with pytest.raises(ValidationError):
            AngleCardV7.model_validate(v7_card(**broken))
    with pytest.raises(ValidationError):
        WeeklyAngleCardsV7.model_validate(v7_output(publishing_order=[2]))


def test_old_cards_still_load_and_new_ones_read_through_the_same_accessors():
    v6_card = {**card("moment_a"), "series": None}
    assert card_contract_for(v6_card) is AngleCardV5 and not is_v7(v6_card) and card_point(v6_card) == v6_card["core_perspective"]
    v7 = v7_card()
    assert card_contract_for(v7) is AngleCardV7 and card_point(v7) == v7["point"]
    # The embedding signature of a v6 card is unchanged; a v7 card is signed by its point.
    assert "Argument: " in signature_from_fields(v6_card) and "Point: We grow" in signature_from_fields(v7)


# The packet --------------------------------------------------------------------------------------------------

def packet():
    def scene(mid, kind, text):
        return {"moment_id": mid, "moment_type": kind, "source_ids": [f"zoom:w/{mid}"], "source_metadata": {},
                "sensitivity": "unknown", "qualifications": [], "source_evidence": [{"text": text, "speaker": "Owner", "start_seconds": 4}]}
    return [scene("m_obs", "observation", "We post twice a week."),
            scene("m_human", "human_line", "Honestly, I still feel like I'm faking it every time I quote a price."),
            scene("m_decision", "counter_expected_decision", "I'd keep your budget where it is for now.")]


def test_v7_lists_human_lines_and_counter_expected_decisions_first_and_reads_the_brief():
    kb = load_knowledge_base(BACKEND_ROOT / "knowledge_base", stage="strategist")
    ordered = order_packet(packet())
    assert [m["moment_id"] for m in ordered] == ["m_human", "m_decision", "m_obs"]
    brief = {"publishing_window": {"from": "2026-10-27", "to": "2026-11-09"}, "season": {"label": "Engagement season soon"},
             "beliefs_to_prove": [{"ref": "B1", "stage": "WARM", "offers": ["ELEVATE"], "belief": "We judge ads by booked weddings.",
                                   "priority_series": None, "quotes": [{"text": "We measure conversions, not clicks."}],
                                   "do_not_repeat": []}],
             "live_offers": [{"offer": "Audit Offer", "status": "delivering", "ends": "2026-11-08", "do_not_undercut": ["An audit is not enough"]}],
             "recent_central_points": []}
    system, user = strategist_angle_prompt(ordered, kb, STRATEGIST_V7_PROFILE, [], brief)
    assert system.startswith(V7.strip())
    assert user.index("## Scene S1") < user.index("Scene kind: a human line") < user.index("## Scene S2")
    assert "Scene kind: a counter-expected decision" in user and "This window's strategy brief" in user
    assert "B1 (WARM; offer: ELEVATE)" in user and "Do not make this point while it runs: An audit is not enough" in user
    assert user.index("Founder seeds") < user.index("This window's strategy brief")
    # v6's user message is untouched by the brief and the kinds, so its saved requests replay.
    assert strategist_user(packet(), STRATEGIST_V6_PROFILE, []) == strategist_angle_prompt(packet(), kb, STRATEGIST_V6_PROFILE, [])[1]
    assert "Scene kind" not in strategist_user(packet(), STRATEGIST_V6_PROFILE, [])
    no_brief = strategist_user(ordered, STRATEGIST_V7_PROFILE, [])
    assert 'use belief_ref "none"' in no_brief


def test_v7_names_each_speaker_once_and_v6_keeps_its_released_packet():
    """N1 shakedown: a transcript line already begins with its speaker ("Owner: words"), so every v7 turn read
    "[00:04] Owner: Owner: words". v7 names the speaker once; v6's released request is unchanged, so its saved runs replay."""
    def turn(words, at):
        return dict(text=words, speaker="Owner", start_seconds=at)
    scenes = [{**m, "source_evidence": [turn("Owner: We post twice a week.", 4), turn("Owner's partner said so.", 9)]}
              for m in packet()[:1]]
    v7 = strategist_user(scenes, STRATEGIST_V7_PROFILE, [])
    assert "[00:04] Owner: We post twice a week." in v7 and "Owner: Owner:" not in v7
    assert "[00:09] Owner: Owner's partner said so." in v7, "only a whole 'Speaker:' prefix is dropped"
    assert "[00:04] Owner: Owner: We post twice a week." in strategist_user(scenes, STRATEGIST_V6_PROFILE, [])


# One public card per client conversation --------------------------------------------------------------------

def test_one_public_card_per_client_conversation():
    conversations = {"moment_a": ["zoom:w/call1"], "moment_b": ["zoom:w/call1"], "moment_c": ["zoom:w/call2"]}
    refs = {"S1": "moment_a", "S2": "moment_b", "S3": "moment_c"}
    output = v7_output([v7_card("S1", 1), v7_card("S2", 2), v7_card("S3", 3)], publishing_order=[3, 2, 1])
    problems = conversation_problems(output, refs, conversations)
    assert len(problems) == 1 and "rank 1 and rank 2" in problems[0] and "zoom:w/call1" in problems[0]
    assert conversation_problems(v7_output([v7_card("S1", 1), v7_card("S3", 2)], publishing_order=[1]), refs, conversations) == []
    # One card citing two scenes of the same call is one card, not two.
    assert conversation_problems(v7_output([v7_card("S1", 1, moment_ids=["S1", "S2"])]), refs, conversations) == []
    demoted, moved = demote_same_conversation(output, refs, conversations)
    assert [a["rank"] for a in demoted["angles"]] == [1, 2] and demoted["angles"][1]["moment_ids"] == ["S3"]
    assert demoted["publishing_order"] == [2, 1] and moved[0]["rank"] == 2
    assert demoted["considered_not_selected"][-1]["reason"].startswith("A better-ranked card already draws on this conversation")
    WeeklyAngleCardsV7.model_validate(demoted)


# Card verification v4: the point tests ----------------------------------------------------------------------

@pytest.mark.parametrize("changes, kind", [
    ({"point_is_about": "platform_or_tactic"}, "point_is_tactic"),
    ({"point": "Meta optimises a campaign for whatever objective it is given."}, "point_is_tactic"),
    ({"point": "Give each market its own landing page."}, "point_is_tactic"),
    ({"reader_takeaway": "Save this and check your own budget settings tonight."}, "takeaway_instructs"),
    ({"reader_takeaway": "I should change this in my account."}, "takeaway_instructs"),
    ({"reader_fit": {"buyer": "elevate", "buyer_statement": "Owners who are frustrated that their ads are wasting money.",
                     "why": "They need rescue."}}, "frustration_framing"),
    ({"audience": "Desperate owners who can't get leads."}, "frustration_framing"),
])
def test_each_point_test_trips_once(changes, kind):
    ledger = ledger_of(v7_card(**changes))
    assert public_kinds(ledger) == [kind]
    assert ledger["public_use"]["allowed"] is False and ledger["public_use"]["kinds"] == [kind]
    assert ledger["public_use"]["reasons"][0].startswith("Rejected for public use") and ledger["readiness"] == "research_required"


def test_a_passing_card_raises_nothing():
    ledger = ledger_of(v7_card())
    assert public_kinds(ledger) == [] and "public_use" not in ledger
    # A platform named inside WIA's own stance is WIA's view, not a platform lesson.
    ours = ledger_of(v7_card(point="Meta wants your budget, so we keep your ads pointed at booked couples."))
    assert public_kinds(ours) == []
    # Earlier cards carry none of the fields and none of the flags: their ledgers are what they were.
    old = {**card("moment_a"), "moment_ids": ["moment_a"]}
    assert not any(f["kind"] in PUBLIC_USE | {"public_stance", "offer_undercut"} for f in
                   v.verify_card(old, SCENES, ROSTER, [])["flags"])


def test_a_public_use_rejection_cannot_be_acknowledged_past_and_a_stance_needs_confirmation():
    rejected = v7_card(reader_takeaway="Check your landing page tonight.")
    ledger = ledger_of(rejected)
    flag_ids = [f["id"] for f in v.blocking(ledger)]
    with pytest.raises(ValueError, match="mark it internal"):
        gate_one.check_card_approval(rejected, rejected["verify_before_publishing"] + flag_ids, {}, ledger, "checked")
    stance = v7_card(public_stance={"takes_stance": True, "stance": "AI can set up ads; it cannot decide what a business stands for."})
    stance_ledger = ledger_of(stance)
    assert [f["kind"] for f in stance_ledger["flags"] if f["kind"] == "public_stance"] == ["public_stance"]
    assert not v.blocking(stance_ledger)
    with pytest.raises(ValueError, match="public stance"):
        gate_one.check_card_approval(stance, stance["verify_before_publishing"], {}, stance_ledger, None)
    confirmation = {"stance": stance["public_stance"]["stance"], "point": stance["point"], "by": "tester", "at": "now"}
    gate_one.check_card_approval(stance, stance["verify_before_publishing"], {}, stance_ledger, None, confirmation)
    # An edited stance needs a new confirmation.
    edited = copy.deepcopy(stance)
    edited["public_stance"]["stance"] = "AI changes everything."
    with pytest.raises(ValueError, match="public stance"):
        gate_one.check_card_approval(edited, edited["verify_before_publishing"], {}, stance_ledger, None, confirmation)


def test_verification_v4_model_pass_reads_the_point_and_rejects_with_its_reason():
    resolved = {**v7_card(), "moment_ids": ["moment_a"]}
    ledger = v.verify_card(resolved, SCENES, ROSTER, [])
    system, user, refs = v.model_pass_prompt([resolved], SCENES, [ledger], "KB", v.MODEL_PASS_V4)
    assert system.startswith(v.TEMPLATES[v.MODEL_PASS_V4].read_text(encoding="utf-8").strip()[:80])
    assert '"point": "We grow a budget' in user and '"reader_takeaway"' in user
    schema = v.model_pass_schema(v.MODEL_PASS_V4)
    assert "point_tests" in schema["properties"]["cards"]["items"]["required"]
    assert "point_tests" not in v.MODEL_PASS_SCHEMA["properties"]["cards"]["items"]["required"], "v3's schema is unchanged"
    # v3's view of an old card is unchanged.
    old = {**card("moment_a"), "moment_ids": ["moment_a"]}
    assert '"point"' not in v.model_pass_prompt([old], SCENES, [ledger], "KB")[1]
    result = {"rank": 1, "bindings": [], "flags": [], "qualifiers": [], "critic": None,
              "point_tests": {"point_is_about": "platform_or_tactic", "takeaway_instructs": False, "frustration_framing": False,
                              "reason": "The point is how a bidding setting behaves."}}
    merged = v.merge_model_pass(ledger, result, refs, "anthropic/claude-sonnet-5.5", card=resolved)
    tactic = [f for f in merged["flags"] if f["kind"] == "point_is_tactic"]
    assert len(tactic) == 1 and tactic[0]["source"] == "model" and "bidding setting" in tactic[0]["message"]
    assert merged["public_use"]["kinds"] == ["point_is_tactic"]
    passing = {**result, "point_tests": {**result["point_tests"], "point_is_about": "wia_standard"}}
    assert "public_use" not in v.merge_model_pass(ledger, passing, refs, "anthropic/claude-sonnet-5.5", card=resolved)


# Gate 1 edits and the brief writer ----------------------------------------------------------------------------

def test_a_v7_card_edits_under_its_own_contract_and_core_perspective_edits_its_point():
    body = {"card": v7_card(moment_ids=["moment_a"]), "title": "t", "argument": "a"}
    edited = gate_one.edited_card_body(body, {"core_perspective": "We let a page prove itself before a budget grows."})
    assert edited["card"]["point"] == "We let a page prove itself before a budget grows." and "core_perspective" not in edited["card"]
    assert edited["argument"] == edited["card"]["point"]
    assert gate_one.edited_card_body(body, {"guardrail": "Keep the owner anonymous."})["card"]["guardrail"] == "Keep the owner anonymous."
    with pytest.raises(ValidationError):
        gate_one.edited_card_body(body, {"point_is_about": "a hunch"})
    old = {"card": {**card("moment_a"), "series": None}, "title": "t", "argument": "a"}
    assert gate_one.edited_card_body(old, {"core_perspective": "New."})["card"]["core_perspective"] == "New."


def test_the_brief_writer_reads_the_guardrail_of_a_v7_card_and_an_older_packet_is_unchanged():
    from backend_pipeline.briefs.workflow import WRITER_V7_FIELDS, writer_packet_v2, writer_packet_v3
    dossier = {"evidence": [], "prior": [], "gaps": [], "brand": {"documents": {}}}

    def run_for(c):
        return {"input_refs": {"angle": {"body": {"title": c["title"], "argument": card_point(c), "audience": c["audience"],
                                                 "card": c}, "steer": None, "cta": None}, "channels": ["email"]}}
    v7 = v7_card(moment_ids=["moment_a"])
    packet = writer_packet_v3(run_for(v7), dossier)
    assert packet["card"]["guardrail"] == v7["guardrail"] and packet["card"]["point"] == v7["point"]
    assert packet["approved_angle"]["core_perspective"] == v7["point"] and "guardrail" in WRITER_V7_FIELDS
    old = {**card("moment_a"), "series": None}
    assert set(writer_packet_v2(run_for(old), dossier)["card"]) == {"pillar", "content_type", "audience", "why_it_matters",
                                                                     "wia_in_action", "offer_connection", "evidence_points",
                                                                     "verify_before_publishing", "series"}


# An offline cycle on the file runner ---------------------------------------------------------------------------

class V7Provider:
    """Extraction from the shared fake; the strategist answers twice with two cards on one call, so the repair call is made and
    the later-ranked card is demoted."""

    def __init__(self):
        self.calls, self.seen = Counter(), {}

    def json_call(self, *, stage, system, user, schema, fingerprint):
        from backend_pipeline.tests.test_strategist_profile import CardProvider
        self.calls[stage] += 1
        self.seen.setdefault(stage, []).append((system, user, schema))
        if stage == "moment_extraction":
            return CardProvider().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        output = v7_output([v7_card("S1", 1), v7_card("S1", 2, title="How we read a florist's inquiries, idea 2",
                                                       point="We read the inquiries before we touch the ads.")],
                           publishing_order=[2, 1])
        return output, {"fake": True, "raw": {"id": "synthetic-only", "usage": {"cost": 0},
                        "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]}}

    def embed(self, *, text, fingerprint):
        raise AssertionError("Embedding provider must remain disconnected")


def test_an_offline_v7_run_reads_the_brief_repairs_once_and_keeps_one_card_per_conversation(week):  # noqa: F811
    provider = V7Provider()
    pipeline = Pipeline(strategist_settings(week, BACKEND_ROOT / "knowledge_base", angle_prompt_profile=STRATEGIST_V7_PROFILE),
                        provider)
    result = pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 2} and result["angles"] == 1
    first_user, repair_user = provider.seen["angle_generation"][0][1], provider.seen["angle_generation"][1][1]
    assert "This window's strategy brief" in first_user and "B1 (" in first_user
    assert "same conversation" in repair_user
    run_dir = f"experiments/default/runs/{result['run_id']}"
    manifest = pipeline.store.read_json(f"{run_dir}/manifest.json")
    brief = manifest["input_refs"]["strategy_brief"]
    assert 4 <= len(brief["beliefs_to_prove"]) <= 6 and brief["brief_hash"]
    repair = pipeline.store.read_json(f"{run_dir}/angle_reference_repair.json")
    assert repair["demoted_same_conversation"][0]["rank"] == 2
    selection = pipeline.store.read_json(f"{run_dir}/angle_selection.json")
    assert selection["publishing_order"] == [1]
    cards = pipeline.store.read_json(f"{run_dir}/angle_cards.json")
    assert [c["point"] for c in cards] == [v7_card()["point"]] and "core_perspective" not in cards[0]


def test_after_its_repair_a_v7_slate_settles_its_considered_ideas_and_insights_and_never_its_cards():
    """N1 shakedown: the strategist's considered ideas still cited internal-only scenes after its one repair, and that failed
    the whole cycle (a paid strategist call lost). A considered idea on internal-only scenes becomes an internal insight; an
    unknown reference is dropped; a card is never touched."""
    from backend_pipeline.angle_profiles import card_reference_problems, tidy_non_card_references
    refs = {"S1": "m_public", "S2": "m_internal"}
    sensitivity = {"m_public": "public_candidate", "m_internal": "internal_only"}
    output = v7_output([v7_card("S1", 1)], considered_not_selected=[
        {"moment_ids": ["S2"], "idea": "Budget by season", "reason": "Internal"},
        {"moment_ids": ["S1", "S9"], "idea": "Another angle", "reason": "Weaker"},
        {"moment_ids": ["S9"], "idea": "Gone", "reason": "None known"}])
    output["internal_insights"] = [{"moment_ids": ["S2", "S44"], "insight": "Seasonal budgets", "use": "Planning"}]
    tidied, done = tidy_non_card_references(output, refs, sensitivity)
    assert card_reference_problems(tidied, refs, sensitivity) == []
    assert [c["idea"] for c in tidied["considered_not_selected"]] == ["Another angle"]
    assert tidied["considered_not_selected"][0]["moment_ids"] == ["S1"]
    assert [i["insight"] for i in tidied["internal_insights"]] == ["Seasonal budgets", "Budget by season"]
    assert tidied["internal_insights"][0]["moment_ids"] == ["S2"] and tidied["angles"] == output["angles"]
    assert {d["action"] for d in done} >= {"moved to internal insights: it draws on internal-only scenes",
                                          "dropped: no known scene left", "dropped unknown or repeated scene references"}
    WeeklyAngleCardsV7.model_validate(tidied)
    leaky = v7_output([v7_card("S2", 1)])
    assert card_reference_problems(tidy_non_card_references(leaky, refs, sensitivity)[0], refs, sensitivity), "a card still fails"


class UnknownReferenceProvider(V7Provider):
    """The strategist cites a scene it was never given, in a considered idea and an insight, in its first answer and its
    repair alike."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage != "angle_generation":
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        self.calls[stage] += 1
        self.seen.setdefault(stage, []).append((system, user, schema))
        output = v7_output([v7_card("S1", 1)], considered_not_selected=[{"moment_ids": ["S99"], "idea": "Ghost", "reason": "None"}])
        output["internal_insights"] = [{"moment_ids": ["S1", "S98"], "insight": "Kept", "use": "Team"}]
        return output, {"fake": True, "raw": {"id": "synthetic-only", "usage": {"cost": 0},
                        "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]}}


def test_an_offline_v7_run_settles_a_considered_ideas_bad_reference_after_its_repair(week):  # noqa: F811
    provider = UnknownReferenceProvider()
    pipeline = Pipeline(strategist_settings(week, BACKEND_ROOT / "knowledge_base", angle_prompt_profile=STRATEGIST_V7_PROFILE),
                        provider)
    result = pipeline.run(1)
    assert provider.calls["angle_generation"] == 2 and result["angles"] == 1, "one repair, then the slate stands"
    run_dir = f"experiments/default/runs/{result['run_id']}"
    repair = pipeline.store.read_json(f"{run_dir}/angle_reference_repair.json")
    assert {d["item"] for d in repair["tidied_references"]} == {"considered idea 1", "internal insight 1"}
    selection = pipeline.store.read_json(f"{run_dir}/angle_selection.json")
    assert selection["considered_not_selected"] == [] and len(selection["internal_insights"]) == 1


def test_v9_adds_only_its_section_and_carries_no_benchmark_week_text():
    """N11: v9 is v8 plus "Decisions and stakes belong in public"; its examples are invented, and nothing from the held-out
    Weeks 1 and 2 (their ideas, phrases or people) reaches it (D28)."""
    from backend_pipeline.angle_profiles import STRATEGIST_TEMPLATES, STRATEGIST_V8_PROFILE, STRATEGIST_V9_PROFILE
    v8 = STRATEGIST_TEMPLATES[STRATEGIST_V8_PROFILE].read_text(encoding="utf-8")
    v9 = STRATEGIST_TEMPLATES[STRATEGIST_V9_PROFILE].read_text(encoding="utf-8")
    head, section = v9.split("## Decisions and stakes belong in public", 1)
    section, tail = section.split("## Positioning", 1)
    assert head + "## Positioning" + tail == v8, "everything outside the new section is v8's text"
    for phrase in ("office hours", "budget", "beyond the ads", "on paper", "i don't know what we changed", "market research",
                   "pause", "rain plan", "tour", "survey", "widget"):
        assert phrase not in section.lower(), phrase
