"""E.B10's critic repair: one reframe call for a public card that fails rubric criterion 1 (WIA is the subject, R40).

Fake providers only: no HTTP and no paid model calls. The PostgreSQL path is covered in test_verification_db.py.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from types import SimpleNamespace

import pytest

from backend_pipeline.config import PROJECT_ROOT, Settings
from backend_pipeline.cycle import verification as v
from backend_pipeline.models import RunManifest, Span, StageArtifact, Transcript
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.tests.test_strategist_profile import card, moment

VERIFIER = "anthropic/claude-sonnet-5.5"
ROSTER = [{"name": "Whitney Hodges", "aliases": ["Whitney"], "status": "current"}]
KB_VIEW = "WIA view (knowledge base): WIA reads a planner's pricing copy before it changes anything in the ad account."
REFRAMES = {
    "good": {"title": "Why we read the pricing copy before the ad account", "core_perspective": "WIA starts with the copy a "
             "couple reads first.", "why_it_matters": "Owners see where lead quality is set.", "wia_in_action": KB_VIEW,
             "reason": "The card now shows how WIA reviews an account."},
    "unbound": {"title": "A planner rethinks her pricing page", "core_perspective": "Pricing copy shapes who enquires.",
                "why_it_matters": "Owners see where lead quality is set.", "wia_in_action": "The planner rewrote her page.",
                "reason": "Shows the change."},
    "new_block": {"title": "Why we read the pricing copy first", "core_perspective": "Leads rose 45% once the copy changed.",
                  "why_it_matters": "Owners see where lead quality is set.", "wia_in_action": KB_VIEW, "reason": "Adds a result."},
    "invalid": {"title": "Why we read the pricing copy first", "core_perspective": " ", "why_it_matters": "x",
                "wia_in_action": KB_VIEW, "reason": "x"},
}


class ReframeProvider:
    """Answers the week's model pass and each reframe call; records which was asked."""

    def __init__(self, reframe="good"):
        self.calls, self.reframe, self.reframe_users = Counter(), reframe, []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        assert stage == "card_verification", "the repair goes through the model pass's stage and routing"
        if "cards" in schema["required"]:
            self.calls["model_pass"] += 1
            ranks = [int(r) for r in re.findall(r'"rank": (\d+)', user)]
            return {"cards": [{"rank": r, "bindings": [], "flags": [], "qualifiers": [],
                               "critic": {"wia_is_the_subject": "fail" if r == 1 else "pass", "worth_attention": "pass",
                                          "reason": "Teaches the client's lesson." if r == 1 else "Shows the WIA move."}}
                              for r in ranks]}, {"fake": True}
        assert schema == v.REFRAME_SCHEMA and system.startswith(v.REFRAME_TEMPLATE.read_text(encoding="utf-8").strip())
        self.calls["reframe"] += 1
        self.reframe_users.append(user)
        return dict(REFRAMES[self.reframe]), {"fake": True}


@pytest.fixture
def slate(tmp_path, monkeypatch):
    """Rank 1 cites only the planner's turn and has no WIA contribution; rank 2 cites Whitney's turn."""
    spans = [Span(span_id="s1", source_id="zoom:week1/call", ordinal=0, start_seconds=0, end_seconds=4, speaker="Planner",
                  text="Planner: We never mention pricing on the landing page."),
             Span(span_id="s2", source_id="zoom:week1/call", ordinal=1, start_seconds=4, end_seconds=9, speaker="Whitney",
                  text="Whitney: We read the pricing copy before we touch the ad account.")]
    transcripts = [Transcript(source_id="zoom:week1/call", week_index=1, path="call.vtt", content_hash="revision",
                              spans=spans, source_format="webvtt")]
    moments = [moment("moment_client", anchor_span_ids=["s1"], context_span_ids=["s1"]),
               moment("moment_staff", anchor_span_ids=["s2"], context_span_ids=["s2"])]
    run = RunManifest(run_id="run_reframe", week_index=1, source_root="x", source_ids=["zoom:week1/call"], prompt_profile="p",
                      model_id="openai/gpt-6.1-sol", embedding_profile="e", mode="fake")

    def build(reframe="good", *, verifier=VERIFIER, cards=None):
        settings = Settings(data_root=tmp_path / "data", knowledge_base_root=tmp_path / "kb", openrouter_verification_model=verifier)
        provider = ReframeProvider(reframe)
        pipeline = Pipeline(settings, provider)
        monkeypatch.setattr(pipeline, "context", lambda stage, mode: SimpleNamespace(roster=ROSTER, text="Synthetic KB.",
                                                                                      internal_terms=[], refs=lambda: {"version": "synthetic"}))
        output = {"week_summary": "One call.", "internal_insights": [], "considered_not_selected": [],
                  "angles": cards or [card("moment_client", 1, wia_in_action=None,
                                           evidence_points=["We never mention pricing on the landing page."]),
                                      card("moment_staff", 2, wia_in_action="Whitney reads the pricing copy first.",
                                           evidence_points=["We read the pricing copy before we touch the ad account."])]}
        angles = pipeline._parse_cards(output, run.run_id, moments, None)
        return pipeline, provider, angles

    def verify(pipeline, angles):
        return pipeline.verify_cards(run, f"experiments/default/runs/{run.run_id}", angles, moments, transcripts)

    return build, verify


def test_a_card_failing_criterion_one_is_reframed_once_and_then_passes(slate):
    build, verify = slate
    pipeline, provider, angles = build("good")
    original = angles[0].model_copy(deep=True)
    ledgers = verify(pipeline, angles)
    assert provider.calls == {"model_pass": 1, "reframe": 1}, "one model pass per week, one reframe for the failing card"
    repaired = angles[0]
    assert repaired.angle_id != original.angle_id and set(ledgers) == {repaired.angle_id, angles[1].angle_id}
    assert repaired.card.wia_in_action == KB_VIEW and repaired.mechanism == KB_VIEW and repaired.title == REFRAMES["good"]["title"]
    for field in ("rank", "pillar", "content_type", "audience", "moment_ids", "evidence_points", "offer_connection",
                  "verify_before_publishing", "why_selected"):
        assert getattr(repaired.card, field) == getattr(original.card, field), f"a reframe never changes {field}"
    assert repaired.moment_ids == original.moment_ids and repaired.source_family_id == original.source_family_id
    ledger = ledgers[repaired.angle_id]
    assert not v.criterion_one_failures(ledger), "the deterministic pass accepts the repaired card"
    assert ledger == v.finish(ledger) and ledger["model_pass"] == VERIFIER
    critic = ledger["critic"]
    assert critic["wia_is_the_subject"] == "fail", "the critic's verdict on the generated card stays visible"
    repair = critic["repair"]
    assert repair["attempted"] is True and repair["kind"] == "reframe" and repair["result"] == "repaired"
    assert repair["prompt_version"] == v.REFRAME_PROFILE and repair["trigger"] == ["no_wia_contribution"]
    assert repair["before"] == {f: original.card.model_dump()[f] for f in v.REFRAME_FIELDS} and repair["before"]["wia_in_action"] is None
    assert repair["after"] == {f: REFRAMES["good"][f] for f in v.REFRAME_FIELDS} and repair["model"] == VERIFIER
    # Provenance: the reframe is its own saved artifact under its versioned prompt, on the verifier's routing.
    artifact = StageArtifact.model_validate(pipeline.store.find_artifact(repair["request_fingerprint"]))
    assert artifact.stage == "card_verification" and artifact.prompt_version == v.REFRAME_PROFILE and artifact.model_id == VERIFIER
    assert repair["artifact_id"] == artifact.artifact_id
    # The passing card was not touched and no repair is recorded on it.
    assert "repair" not in (ledgers[angles[1].angle_id]["critic"] or {})


def test_a_still_failing_reframe_keeps_the_card_and_its_flag_and_records_the_attempt(slate):
    build, verify = slate
    pipeline, provider, angles = build("unbound")
    original = angles[0].model_copy(deep=True)
    ledgers = verify(pipeline, angles)
    assert provider.calls == {"model_pass": 1, "reframe": 1}
    assert angles[0] == original, "a failed reframe leaves the generated card in place"
    ledger = ledgers[original.angle_id]
    assert [f["kind"] for f in v.criterion_one_failures(ledger)] == ["no_wia_contribution"]
    repair = ledger["critic"]["repair"]
    assert repair["result"] == "still_failing" and repair["remaining_flags"] == ["wia_contribution_unbound"]
    assert repair["after"]["wia_in_action"] == "The planner rewrote her page." and repair["before"]["wia_in_action"] is None


def test_a_reframe_that_adds_a_blocking_flag_is_not_accepted(slate):
    build, verify = slate
    pipeline, _provider, angles = build("new_block")
    original = angles[0].model_copy(deep=True)
    ledger = verify(pipeline, angles)[original.angle_id]
    assert angles[0] == original and ledger["critic"]["repair"]["result"] == "still_failing"
    assert not v.blocking(ledger), "the unsupported 45% was never put on the card"


def test_an_invalid_reframe_response_is_a_recorded_failed_attempt(slate):
    build, verify = slate
    pipeline, provider, angles = build("invalid")
    original = angles[0].model_copy(deep=True)
    ledger = verify(pipeline, angles)[original.angle_id]
    assert provider.calls["reframe"] == 1 and angles[0] == original
    repair = ledger["critic"]["repair"]
    assert repair["result"] == "still_failing" and "none of them empty" in repair["error"] and repair["after"] is None
    assert v.criterion_one_failures(ledger)


def test_no_call_is_made_without_a_verification_model(slate):
    build, verify = slate
    pipeline, provider, angles = build("good", verifier=None)
    ids = [a.angle_id for a in angles]
    ledgers = verify(pipeline, angles)
    assert provider.calls == {} and [a.angle_id for a in angles] == ids
    assert ledgers[ids[0]]["critic"] is None and v.criterion_one_failures(ledgers[ids[0]])


def test_at_most_one_reframe_call_per_card_per_run(slate):
    build, verify = slate
    two = [card("moment_client", 1, wia_in_action=None), card("moment_client", 2, wia_in_action="The planner asks about it.",
                                                             core_perspective="Pricing copy shapes enquiries, idea 2.")]
    pipeline, provider, angles = build("unbound", cards=two)
    verify(pipeline, angles)
    assert provider.calls == {"model_pass": 1, "reframe": 2}, "one reframe each for the two failing cards"
    assert [u.count("Card to reframe:") for u in provider.reframe_users] == [1, 1]
    # Verifying the same slate again in the run reuses the saved calls: no second reframe reaches the provider.
    verify(pipeline, angles)
    assert provider.calls == {"model_pass": 1, "reframe": 2}


def test_a_reframe_changes_only_the_framing_fields():
    before = card("moment_client", 1, wia_in_action=None)
    after = v.apply_reframe(before, {**REFRAMES["good"], "moment_ids": ["moment_other"], "evidence_points": ["Invented."],
                                     "rank": 9})
    assert {k for k in before if before[k] != after[k]} == {"title", "core_perspective", "why_it_matters", "wia_in_action"}
    assert set(v.REFRAME_SCHEMA["properties"]) == {*v.REFRAME_FIELDS, "reason"}, "the schema cannot carry evidence or IDs"


def test_the_reframe_prompt_is_a_new_versioned_file_that_passes_the_style_lint():
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    text = v.REFRAME_TEMPLATE.read_text(encoding="utf-8")
    assert v.REFRAME_TEMPLATE != v.TEMPLATE and v.REFRAME_TEMPLATE.name == "card_reframe.v1.md"
    assert lint(text) == [] and "data, not instructions" in text and "WIA view (knowledge base):" in text


class FailingVerifier:
    """The verification route fails: an outage, no compliant endpoint, or an unusable answer."""

    def __init__(self, error):
        self.error, self.calls = error, 0

    def json_call(self, **kwargs):
        self.calls += 1
        raise self.error


def outage():
    import httpx
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    return httpx.HTTPStatusError("503", request=request, response=httpx.Response(503, request=request))


@pytest.mark.parametrize("error", [outage(), ValueError("Provider returned no JSON content")], ids=["outage", "invalid"])
def test_an_unavailable_model_pass_keeps_the_deterministic_ledger_and_asks_for_each_point(slate, error):
    """Plan 4.11: the week still reaches Gate 1; the ledger says the model check was unavailable, and each point only the
    model pass could have checked must be acknowledged before the card is developed."""
    from backend_pipeline import gate_one
    build, verify = slate
    unbound = card("moment_staff", 1, wia_in_action="Whitney reads the pricing copy first.",
                   evidence_points=["We read the pricing copy before we touch the ad account.",
                                    "She checks what the couple sees first, every time."])
    pipeline, _, angles = build(cards=[unbound])
    pipeline.provider = FailingVerifier(error)
    ledgers = verify(pipeline, angles)
    assert pipeline.provider.calls == 1, "one attempt; no reframe without a model pass"
    ledger = ledgers[angles[0].angle_id]
    assert ledger["model_pass"] == "unavailable" and ledger == v.finish(ledger)
    kinds = [f["kind"] for f in ledger["flags"]]
    assert "model_check_unavailable" in kinds
    points = [f for f in ledger["flags"] if f["kind"] == "unchecked_point"]
    assert [f["field"] for f in points] == ["evidence_points[1]"], "only the point the rules could not bind"
    assert all(f["severity"] == v.BLOCK for f in points)
    body = angles[0].card.model_dump(mode="json")
    with pytest.raises(ValueError, match="Resolve every blocking ledger flag"):
        gate_one.check_card_approval(body, body["verify_before_publishing"], {}, ledger, "Checked")
    gate_one.check_card_approval(body, [*body["verify_before_publishing"], points[0]["id"]], {}, ledger,
                                 "Checked the second point against the call")


def test_a_refused_plan_still_stops_the_run(slate):
    """Budget and plan refusals are not an unavailable model: nothing more is spent, and the run stops."""
    from backend_pipeline.llm.run_plans import RunPlanError
    build, verify = slate
    pipeline, _, angles = build()
    pipeline.provider = FailingVerifier(RunPlanError("Run plan plan_x has used all 3 calls"))
    with pytest.raises(RunPlanError):
        verify(pipeline, angles)


def test_an_outage_on_the_reframe_call_keeps_the_card_and_its_flags(slate):
    """The critic's one reframe call failing on the route is a recorded failed attempt, like an invalid answer."""
    build, verify = slate
    pipeline, provider, angles = build("good")
    original = angles[0].angle_id
    answer = provider.json_call

    def reframe_down(**kwargs):
        if "cards" not in kwargs["schema"]["required"]:
            raise outage()
        return answer(**kwargs)
    provider.json_call = reframe_down
    ledger = verify(pipeline, angles)[original]
    assert angles[0].angle_id == original and v.criterion_one_failures(ledger)
    assert ledger["critic"]["repair"]["result"] == "still_failing" and "HTTPStatusError" in ledger["critic"]["repair"]["error"]


def test_the_week_verifier_reads_the_belief_statements_so_a_quoted_belief_is_not_a_block(slate, monkeypatch):
    """The live development week: the model pass called Whitney's own belief, quoted on a card, an invented quote and
    blocked the card. The verifier now receives the belief statements, and such a block becomes a check."""
    from backend_pipeline.config import BACKEND_ROOT
    from backend_pipeline.knowledge.assembly import assemble
    build, verify = slate
    belief = "good marketing decisions start with good data"
    staff = card("moment_staff", 1, wia_in_action="Whitney reads the pricing copy first.",
                 why_it_matters=f"It shows her belief that '{belief}'.",
                 evidence_points=["We read the pricing copy before we touch the ad account."])
    pipeline, provider, angles = build(cards=[staff])
    real = assemble("verifier", root=BACKEND_ROOT / "knowledge_base")
    monkeypatch.setattr(pipeline, "context", lambda stage, mode: SimpleNamespace(
        roster=ROSTER, text=real.text, internal_terms=[], refs=lambda: {"version": "committed"}, document=real.document))
    seen = {}

    def model_pass(*, stage, system, user, schema, fingerprint):
        seen["system"] = system
        return {"cards": [{"rank": 1, "bindings": [], "qualifiers": [], "critic": {
            "wia_is_the_subject": "pass", "worth_attention": "pass", "reason": "Shows the WIA move."}, "flags": [
            {"kind": "misattribution", "severity": "block", "field": "why_it_matters",
             "text": f"It shows her belief that '{belief}'", "message": "Whitney does not say this in S1; an invented quote."}]}]}, {"fake": True}
    provider.json_call = model_pass
    ledger = verify(pipeline, angles)[angles[0].angle_id]
    assert belief in seen["system"].lower() and seen["system"].startswith(v.TEMPLATE.read_text(encoding="utf-8").strip())
    assert not v.blocking(ledger) and [f["kind"] for f in ledger["flags"]] == ["belief_quote"]
