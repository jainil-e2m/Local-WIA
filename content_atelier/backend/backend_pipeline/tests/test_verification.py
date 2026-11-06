"""E.B10 "done when", offline, on the 18 October outputs the judges reviewed (research/quality-experiments-2026-10-18).

The model-pass responses are the saved VER-* runs (paid once under run plan plan_0c8e0998817e435d9dc7); merging them is
free and deterministic. Judges' findings are read from the saved J* judgments.
"""
from __future__ import annotations

import json
import re
import sys

import pytest

from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT
from backend_pipeline.cycle import verification as v
from backend_pipeline.knowledge_base import team_roster

HARNESS = PROJECT_ROOT / "research" / "quality-experiments-2026-10-18"
sys.path.insert(0, str(HARNESS))
exp_verify = pytest.importorskip("exp_verify")
sys.path.pop(0)
KB = BACKEND_ROOT / "knowledge_base"
SONNET = ("P1-week1-claude-sonnet-5", "P1-week2-claude-sonnet-5")
SOL = ("P1-week1-gpt-6.1-sol", "P1-week2-gpt-6.1-sol", "B0-week1-gpt-6.1-sol", "B0-week2-gpt-6.1-sol")


def deterministic(run_id):
    return [ledger for _, ledger in exp_verify.deterministic(run_id)[0]]


def merged(run_id):
    """The deterministic ledgers with the saved model pass merged in, as the product does."""
    pairs, found = exp_verify.deterministic(run_id)
    model = exp_verify.VERIFIER[run_id.split("-", 2)[2]]
    saved = json.loads((HARNESS / "runs" / f"VER-{model.split('/')[-1]}-{run_id}.json").read_text(encoding="utf-8"))
    _, _, refs = v.model_pass_prompt([c for c, _ in pairs], found, [ledger for _, ledger in pairs], "")
    by_rank = {item["rank"]: item for item in saved["output"]["cards"]}
    return [v.merge_model_pass(ledger, by_rank.get(c["rank"], {}), refs, model) for c, ledger in pairs]


def judged(run_id):
    """Indexes (0-based, in rank order) of the cards where any 18 October judge recorded a factual problem."""
    raised = set()
    for path in HARNESS.glob("runs/J*.json"):
        m = re.search(r"X_(.+?)-Y_(.+)\.json$", path.name)
        if not m or path.name.startswith(("JP-", "JB")):
            continue
        for problem in json.loads(path.read_text(encoding="utf-8"))["output"].get("factual_problems", []):
            if (m.group(1) if problem["set"] == "X" else m.group(2)) == run_id:
                raised |= {int(n) - 1 for n in re.findall(r"[XY](\d+)", problem["angle"])}
    return raised


def kinds(ledger, severity=None):
    return {f["kind"] for f in ledger["flags"] if severity is None or f["severity"] == severity}


def test_the_deterministic_pass_catches_the_stated_as_done_and_zero_claims():
    first = deterministic("P1-week2-claude-sonnet-5")[0]
    assert {"tense", "zero_claim"} <= kinds(first, v.BLOCK), "removed for 'gonna take those out'; 'no conversions yet'"
    assert any('"every week"' in f["message"] for f in first["flags"]), "a frequency claim the call does not show"
    assert any(f["kind"] == "price" and "$197" in f["message"] for f in deterministic("P1-week2-claude-sonnet-5")[3]["flags"])


def test_no_deterministic_block_on_the_sol_outputs():
    for run_id in SOL:
        for i, ledger in enumerate(deterministic(run_id)):
            assert not v.blocking(ledger), (run_id, i, v.blocking(ledger))


def test_jacqueline_is_not_flagged_now_that_the_roster_includes_her():
    roster = {r["name"]: r for r in team_roster(KB)}
    assert roster["Jacqueline Hood"]["status"] == "current"
    for run_id in SONNET + SOL:
        for ledger in merged(run_id):
            assert not any("Jacqueline" in f["message"] and f["kind"] == "misattribution" for f in ledger["flags"])


def test_the_week_1_b0_angle_without_a_wia_contribution_is_flagged_and_staff_turn_cards_are_not():
    b0 = deterministic("B0-week1-gpt-6.1-sol")
    assert "no_wia_contribution" in kinds(b0[1]) and all("no_wia_contribution" not in kinds(x) for i, x in enumerate(b0) if i != 1)
    for ledger in deterministic("P1-week2-gpt-6.1-sol"):
        assert not kinds(ledger) & {"no_wia_contribution", "wia_contribution_unbound"}, "built on WIA staff turns"


def test_with_the_model_pass_every_sonnet_card_the_judges_faulted_is_blocked():
    for run_id in SONNET:
        ledgers = merged(run_id)
        for i in judged(run_id):
            assert v.blocking(ledgers[i]), (run_id, i)
    week2 = merged("P1-week2-claude-sonnet-5")
    assert "invented_reason" in kinds(week2[0], v.BLOCK), "'may have been generating accidental clicks'"
    assert "invented_reason" in kinds(week2[2], v.BLOCK), "the personalization gap stated as the cause"
    assert kinds(week2[3], v.BLOCK) & {"overclaim", "invented_reason"}, "'without rebuilding' when an overhaul was possible"


def test_no_blocking_flag_on_a_sol_card_the_judges_did_not_fault():
    for run_id in SOL:
        raised = judged(run_id)
        for i, ledger in enumerate(merged(run_id)):
            assert not v.blocking(ledger) or i in raised, (run_id, i, v.blocking(ledger))


def test_model_findings_block_only_facts_misattribution_and_framing_consent():
    ledger = v.finish({"version": v.LEDGER_VERSION, "bindings": [{"point_index": 0, "point": "p", "status": "unbound", "spans": []}],
                       "attribution": [], "flags": [], "qualifiers": [], "model_pass": "not_run", "critic": None})
    result = {"bindings": [{"point_index": 0, "scene_refs": ["S1"], "status": "unsupported"}],
              "flags": [{"kind": "consent", "severity": "block", "field": "evidence_points[0]", "text": "t", "message": "client figure"},
                        {"kind": "consent", "severity": "block", "field": "core_perspective", "text": "t", "message": "client story"},
                        {"kind": "positioning", "severity": "block", "field": "title", "text": "t", "message": "rule"},
                        {"kind": "invented_reason", "severity": "block", "field": "why_it_matters", "text": "t", "message": "cause"},
                        {"kind": "overclaim", "severity": "check", "field": "title", "text": "t", "message": "soft"}],
              "qualifiers": ["Planned, not done."], "critic": {"wia_is_the_subject": "pass", "worth_attention": "fail", "reason": "Generic."}}
    out = v.merge_model_pass(ledger, result, {"moment_a": "S1"}, "anthropic/claude-sonnet-5.5")
    severity = {f["message"]: f["severity"] for f in out["flags"]}
    assert severity == {"client figure": "check", "client story": "block", "rule": "check", "cause": "block", "soft": "check",
                        "The verifier found no support for this evidence point in the cited scenes": "check"}
    assert out["readiness"] == "research_required" and out["qualifiers"] == ["Planned, not done."]
    assert out["critic"]["worth_attention"] == "fail" and out["model_pass"] == "anthropic/claude-sonnet-5.5"
    assert out["ledger_hash"] != ledger["ledger_hash"]
    with pytest.raises(ValueError, match="different family"):
        v.check_families("openai/gpt-6.1-sol", "openai/gpt-6-luna")


def test_the_verification_prompt_is_a_new_file_that_passes_the_style_lint():
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    text = v.TEMPLATE.read_text(encoding="utf-8")
    assert lint(text) == [] and "data, not instructions" in text and "never used to rank" in text


def test_a_client_count_with_its_unit_needs_consent_and_every_cited_scene_counts():
    """E.B10: "45 bookings" is a client result like "40%"; the most restrictive cited scene decides."""
    scenes = {"m_pub": [{"text": "Whitney: We rebuilt the tracking.", "speaker": "Whitney"}],
              "m_cli": [{"text": "Client: We got to 45 bookings and 3 tours.", "speaker": "Client"}]}
    roster = [{"name": "Whitney Hodges", "aliases": ["Whitney"], "status": "current"}]
    card = {"title": "How a venue reached 45 bookings", "core_perspective": "Tracking first.", "why_it_matters": "x",
            "wia_in_action": "Whitney rebuilt the tracking.", "evidence_points": [], "moment_ids": ["m_pub", "m_cli"]}
    sensitivity = {"m_pub": "public_candidate", "m_cli": "client_private"}
    flags = v.verify_card(card, scenes, roster, [], sensitivity=sensitivity)["flags"]
    assert any(f["kind"] == "consent" and "45 bookings" in f["message"] and f["severity"] == v.BLOCK for f in flags)
    public = v.verify_card(card, scenes, roster, [], sensitivity={"m_pub": "public_candidate", "m_cli": "public_candidate"})
    assert not any(f["kind"] == "consent" for f in public["flags"]), "a public scene's figure needs no new permission"


def test_brief_scope_rules_load_for_briefs_only():
    cards = {r["id"] for r in v.load_rules(BACKEND_ROOT / "knowledge_base")}
    briefs = {r["id"] for r in v.load_rules(BACKEND_ROOT / "knowledge_base", stage="brief")}
    assert "RR-04" not in cards and {"RR-04", "RR-09"} <= briefs


# A quoted WIA belief (the live development week, 18 October): the model pass called Whitney's own belief statement,
# quoted on a card, an invented quote and blocked the card, because the verifier never saw the belief statements.
BELIEF = "good marketing decisions start with good data"


def load_kb_document(key):
    from backend_pipeline.knowledge_base import load_knowledge_base
    return load_knowledge_base(KB).document(key)


def belief_ledger():
    return v.finish({"version": v.LEDGER_VERSION, "bindings": [], "attribution": [], "flags": [], "qualifiers": [],
                     "model_pass": "not_run", "critic": None})


def test_the_verifier_receives_the_belief_statements_and_its_prompt_says_how_to_treat_a_quoted_belief():
    from backend_pipeline.knowledge import assembly
    kb = assembly.assemble("verifier", root=KB)
    assert kb.document("belief_statements") is not None and BELIEF in kb.text.lower()
    full = [d.entry.key for d in load_knowledge_base_all().documents]
    keys = [d.entry.key for d in kb.documents]
    assert keys == [k for k in full if k in keys], "in manifest order"
    assert {"team_roster", "rejection_rules", "belief_statements"} <= set(keys) and "format_guide" not in keys
    assert assembly.assemble("extraction", root=KB).document("belief_statements") is None, "only the verifier gains it"
    assert v.MODEL_PASS_PROFILE == "card-verification.v3" and v.TEMPLATE.name == "card_verification.v3.md"
    assert v.TEMPLATES["card-verification.v1"].is_file() and v.TEMPLATES["card-verification.v2"].is_file(), \
        "the released prompts stay for replay"
    text = v.TEMPLATE.read_text(encoding="utf-8")
    assert "belief statements" in text and "never as something said on the call" in text


def load_knowledge_base_all():
    from backend_pipeline.knowledge_base import load_knowledge_base
    return load_knowledge_base(KB)


@pytest.mark.parametrize("kind", ["misattribution", "invented_reason", "overclaim", "other"])
def test_a_model_block_on_a_quoted_belief_statement_becomes_a_check(kind):
    beliefs = v.belief_index(load_kb_document("belief_statements"))
    result = {"bindings": [], "qualifiers": [], "critic": None, "flags": [
        {"kind": kind, "severity": "block", "field": "why_it_matters",
         "text": f"It supports her belief that '{BELIEF}'", "message": "Whitney does not say this in S4; an invented quote."}]}
    out = v.merge_model_pass(belief_ledger(), result, {}, "anthropic/claude-sonnet-5.5", beliefs=beliefs)
    [flag] = out["flags"]
    assert flag["severity"] == v.CHECK and flag["kind"] == "belief_quote" and flag["source"] == "model"
    assert "belief statements" in flag["message"] and "not something said on this call" in flag["message"]
    assert "an invented quote" in flag["message"], "the verifier's own reason stays visible"
    assert out["readiness"] == "needs_check" and not v.blocking(out)
    # Without the belief statements a blocking kind still blocks, as before ("other" was never more than a check).
    before = v.merge_model_pass(belief_ledger(), result, {}, "anthropic/claude-sonnet-5.5")
    assert bool(v.blocking(before)) == (kind in v.MODEL_BLOCK_KINDS) and before["flags"][0]["kind"] == kind


def test_an_invented_quote_or_a_block_without_a_belief_quote_still_blocks():
    beliefs = v.belief_index(load_kb_document("belief_statements"))
    flags = [{"kind": "misattribution", "severity": "block", "field": "why_it_matters",
              "text": "Whitney's belief that 'every venue should double its ad budget in winter'", "message": "Invented quote."},
             {"kind": "misattribution", "severity": "block", "field": "core_perspective",
              "text": "Carmen rebuilt the campaign", "message": "Carmen does not speak in S1."},
             {"kind": "misattribution", "severity": "block", "field": "why_it_matters",
              "text": f"Whitney's belief that '{BELIEF}', and 'every venue should double its ad budget'", "message": "Mixed."},
             {"kind": "consent", "severity": "block", "field": "title", "text": f"'{BELIEF}' and 45 bookings", "message": "Figure."}]
    out = v.merge_model_pass(belief_ledger(), {"bindings": [], "qualifiers": [], "critic": None, "flags": flags}, {},
                             "anthropic/claude-sonnet-5.5", beliefs=beliefs)
    assert [f["severity"] for f in out["flags"]] == [v.BLOCK] * 4, "only a block whose every quote is a belief is downgraded"


def test_the_deterministic_pass_treats_a_quoted_belief_credited_to_its_owner_as_a_check():
    beliefs = v.belief_index(load_kb_document("belief_statements"))
    roster = [{"name": "Whitney Hodges", "aliases": ["Whitney"], "status": "current"},
              {"name": "Carmen Ruiz", "aliases": ["Carmen"], "status": "current"},
              {"name": "Mia Lane", "aliases": ["Mia"], "status": "current"}]
    scenes = {"m1": [{"text": "We pulled the booking data before we changed anything.", "speaker": "Carmen"}]}
    card = {"title": "Why we pull the booking data first", "core_perspective": f"Whitney says '{BELIEF}'.",
            "why_it_matters": "x", "wia_in_action": "Carmen pulled the booking data.", "evidence_points": [], "moment_ids": ["m1"]}
    flags = v.verify_card(card, scenes, roster, [], beliefs=beliefs)["flags"]
    assert [f["kind"] for f in flags if f["field"] == "core_perspective"] == ["belief_quote"]
    assert not any(f["severity"] == v.BLOCK for f in flags)
    assert any(f["kind"] == "misattribution" for f in v.verify_card(card, scenes, roster, [])["flags"]), "unchanged without beliefs"
    # The same belief credited to someone other than its owner is still a misattribution.
    other = {**card, "core_perspective": f"Mia says '{BELIEF}'."}
    flags = v.verify_card(other, scenes, roster, [], beliefs=beliefs)["flags"]
    assert any(f["kind"] == "misattribution" and f["severity"] == v.BLOCK for f in flags)


# E.B26 ---------------------------------------------------------------------------------------------------------------
TEAM = [{"name": "Whitney Hodges", "aliases": ["Whitney"], "status": "current"},
        {"name": "Carmen Cruickshank", "aliases": ["Carmen", "Cruikshank"], "status": "current"},
        {"name": "Jacqueline Hood", "aliases": ["Jacqueline"], "status": "current"},
        {"name": "Fallon Looney", "aliases": ["Fallon"], "status": "former"}]


def team_card(text, field="wia_in_action", moment_ids=("m1",)):
    card = {"title": "t", "core_perspective": "c", "why_it_matters": "w", "wia_in_action": "w", "evidence_points": [],
            "moment_ids": list(moment_ids)}
    if field.startswith("evidence_points"):
        card["evidence_points"] = [text]
    else:
        card[field] = text
    return card


WHITNEY_SPEAKS = {"m1": [{"text": "I'd start with a review of the campaigns and the landing pages.", "speaker": "Whitney Hodges"}]}


@pytest.mark.parametrize("text", [
    # Real sentences from strategist v5 samples on benchmark v1: Whitney acts; Carmen and Jacqueline are objects.
    "Whitney recommended a diagnostic review with Carmen and explained that a Google Search Accelerator recommendation "
    "could follow if Carmen found a need for a new search campaign or substantial page changes.",
    "Whitney asked for feedback from Jacqueline and explicitly said the corporate page needed a clearer next step.",
    "Whitney proposed a review with our Google Ads lead Carmen and explained how the findings could shape the next step.",
    "Whitney told Carmen and explained the plan to the owner.",
])
def test_a_name_that_is_not_the_subject_is_not_credited_with_the_verb(text):
    ledger = v.verify_card(team_card(text), WHITNEY_SPEAKS, TEAM, [])
    assert not any(f["kind"] == "misattribution" for f in ledger["flags"]), ledger["flags"]
    assert not v.blocking(ledger)


@pytest.mark.parametrize("text", ["Carmen rebuilt the campaign.", "Whitney met with the client and Carmen rebuilt the campaign.",
                                  "Whitney asked for feedback, and Jacqueline said the page was strong.",
                                  "A review with Whitney found nothing; Carmen explained the gap."])
def test_a_credited_subject_who_does_not_speak_still_blocks(text):
    flags = v.verify_card(team_card(text), WHITNEY_SPEAKS, TEAM, [])["flags"]
    assert any(f["kind"] == "misattribution" and f["severity"] == v.BLOCK for f in flags), flags


@pytest.mark.parametrize("text", [
    # Real evidence points from a strategist v5 sample (knowledge base 7, week 2, sample 2): 52 blocking number flags.
    "At 08:00–09:21, Fallon reviewed movement from inquiry to tour and asked what happens after the tour is booked.",
    "At 32:02–32:32, Whitney recommended a review of the existing campaigns before any rebuild.",
    "Between 1:04:10 and 1:05:02, and again from 12:30 to 12:45, Whitney asked about the landing page.",
])
def test_scene_timestamps_are_never_figures(text):
    scenes = {"m1": [{"text": "What happens after the tour is booked?", "speaker": "Fallon Looney"},
                     {"text": "Let us review the campaigns first.", "speaker": "Whitney Hodges"}]}
    flags = v.verify_card(team_card(text, "evidence_points[0]"), scenes, TEAM, [])["flags"]
    assert not any(f["kind"] in ("number", "consent") for f in flags), flags


def test_an_unsupported_figure_beside_a_timestamp_still_blocks():
    text = "At 32:02–32:32, Whitney said the venue reached 45 bookings."
    flags = v.verify_card(team_card(text, "evidence_points[0]"), WHITNEY_SPEAKS, TEAM, [])["flags"]
    assert [f["message"] for f in flags if f["kind"] == "number"] == ['"45 bookings" is not in the cited scenes']
    assert all(f["severity"] == v.BLOCK for f in flags if f["kind"] == "number")


CARMEN_SPEAKS = {"m1": [{"text": "I really would like to determine if it's good or not by 100 clicks.",
                         "speaker": "Carmen Cruickshank"}]}


@pytest.mark.parametrize("text", [
    "In the accounts she manages, Carmen sees most couples check the landing page twice before they inquire.",
    "Carmen usually waits for about 100 clicks before she judges a new campaign.",
    "In our experience, couples rarely book from a single visit.",
    "We see it every time: couples always ask about the date first.",
])
def test_attributed_experience_is_not_a_prevalence_claim(text):
    ledger = v.verify_card(team_card(text, "core_perspective"), CARMEN_SPEAKS, TEAM, [])
    assert not any(f["kind"] == "frequency" for f in ledger["flags"]), ledger["flags"]


@pytest.mark.parametrize("text,scenes", [
    ("Most couples check the landing page twice before they inquire.", CARMEN_SPEAKS),
    ("Jacqueline sees most couples check the landing page twice.", CARMEN_SPEAKS),
    ("In our experience, couples rarely book from a single visit.", {"m1": [{"text": "Hi.", "speaker": "Client"}]}),
])
def test_an_unattributed_or_unsupported_prevalence_claim_is_still_flagged(text, scenes):
    flags = v.verify_card(team_card(text, "core_perspective"), scenes, TEAM, [])["flags"]
    assert any(f["kind"] == "frequency" and f["severity"] == v.CHECK for f in flags), flags


def test_a_model_prevalence_finding_on_attributed_experience_becomes_a_check():
    text = "In the accounts she manages, Carmen sees most couples check the landing page twice before they inquire."
    card = team_card(text, "core_perspective")
    flags = [{"kind": "frequency", "severity": "block", "field": "core_perspective", "text": "most couples",
              "message": "A prevalence claim the scene does not measure."},
             {"kind": "overclaim", "severity": "block", "field": "core_perspective", "text": text,
              "message": "States a general pattern from one strategist's view."},
             {"kind": "overclaim", "severity": "block", "field": "core_perspective", "text": "check the landing page twice",
              "message": "The landing page change was planned, not made."},
             {"kind": "misattribution", "severity": "block", "field": "core_perspective", "text": text,
              "message": "Carmen is credited with Jacqueline's view."}]
    result = {"bindings": [], "qualifiers": [], "critic": None, "flags": flags}
    out = v.merge_model_pass(belief_ledger(), result, {"m1": "S1"}, "anthropic/claude-sonnet-5.5", card=card,
                             scenes=CARMEN_SPEAKS, roster=TEAM)
    assert [(f["kind"], f["severity"]) for f in out["flags"]] == [
        ("attributed_experience", v.CHECK), ("attributed_experience", v.CHECK), ("overclaim", v.BLOCK),
        ("misattribution", v.BLOCK)], "only the prevalence readings are downgraded"
    assert "not a prevalence claim" in out["flags"][0]["message"] and "does not measure" in out["flags"][0]["message"]
    # Credited to someone who does not speak in the cited scenes, or without the card: unchanged.
    silent = {"m1": [{"text": "Hi.", "speaker": "Client"}]}
    for kwargs in ({"card": card, "scenes": silent, "roster": TEAM}, {}):
        before = v.merge_model_pass(belief_ledger(), result, {"m1": "S1"}, "anthropic/claude-sonnet-5.5", **kwargs)
        assert [f["kind"] for f in before["flags"]] == ["frequency", "overclaim", "overclaim", "misattribution"]
        assert [f["severity"] for f in before["flags"]] == [v.CHECK, v.BLOCK, v.BLOCK, v.BLOCK]


def test_the_v3_verification_prompt_says_attributed_experience_is_not_a_prevalence_claim():
    text = v.TEMPLATE.read_text(encoding="utf-8")
    assert "**Attributed experience.**" in text and "not a prevalence claim" in text and "Quoted beliefs" in text
    v2 = v.TEMPLATES["card-verification.v2"].read_text(encoding="utf-8")
    assert "Attributed experience" not in v2, "v2 is kept byte for byte for replay"


PLANS_TO_BUILD = {"m1": [{"text": "We're going to build a survey for couples who just booked.", "speaker": "Whitney Hodges"}]}


@pytest.mark.parametrize("text", [
    # A real sentence from a strategist v6 sample (knowledge base 8): the reader built the experience, not WIA.
    "You've built an experience couples love. Learning what led them to book helps WIA advertise the reasons that mattered.",
    "You have already built a strong referral base, and the survey shows what made couples book.",
])
def test_what_the_reader_has_done_is_not_wia_stating_its_work_as_done(text):
    flags = v.verify_card(team_card(text, field="why_it_matters"), PLANS_TO_BUILD, TEAM, [])["flags"]
    assert not any(f["kind"] == "tense" for f in flags), flags


def test_wia_stating_as_done_what_it_only_plans_still_blocks():
    flags = v.verify_card(team_card("We built a survey for couples who just booked.", field="why_it_matters"), PLANS_TO_BUILD,
                          TEAM, [])["flags"]
    assert any(f["kind"] == "tense" and f["severity"] == v.BLOCK for f in flags), flags
