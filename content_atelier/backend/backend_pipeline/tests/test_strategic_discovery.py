"""Feedback-driven invariants; synthetic outputs are not editorial-quality proof."""
import copy
import json

import pytest
from pydantic import ValidationError

from backend_pipeline.config import Settings
from backend_pipeline.contracts import signature_from_fields
from backend_pipeline.models import Span, Transcript
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.prompts import angle_prompt, moment_prompt, weekly_moment_prompt, sql_angle_prompt, sql_refinement_prompt
from backend_pipeline.scoring import rank
from backend_pipeline.strategy_contracts import (
    Discovery, StrategicAngleResponse, StrategicMomentResponse, StrategicCompactMomentResponse,
    StrategicRefinementResponse, STRATEGY_VERSION,
)


@pytest.fixture
def strategy_case(tmp_path):
    texts = [
        "Client: Couples ask whether they need to arrange every supplier separately.",
        "Team: Let's make the package inclusions easier to understand on the page.",
        "Client: I already have a chart showing what the package includes.",
        "Team: We can review where that chart would help explain the offer.",
    ]
    spans = [Span(span_id=f"s{i}", source_id="venue-call", ordinal=i, start_seconds=i, end_seconds=i+1, text=t)
             for i,t in enumerate(texts)]
    transcript = Transcript(source_id="venue-call", week_index=1, path="synthetic.vtt", content_hash="r1",
                            spans=spans, source_format="webvtt")
    moment = {"local_key":"m1", "anchor_span_ids":["s1","s2","s3"], "context_span_ids":[s.span_id for s in spans],
        "quote":"Let's make the package inclusions easier to understand on the page.",
        "context_summary":"The client and team discuss an existing comparison chart and possible page placement.",
        "moment_type":"decision", "proposition":"The team proposes reviewing where the client's chart could explain the offer.",
        "audience_relevance":"Owners whose distinct service package is hard for buyers to compare.",
        "qualifications":["Placement was proposed; no outcome is supplied."], "claim_status":"planned",
        "sensitivity":"unknown", "strength":4., "reasons":["The exchange shows a positioning decision and client contribution."],
        "discovery":{"lenses":["wia_expertise","broader_principle"], "destination":"public_opportunity",
            "wia_contribution":"The team considers where an existing chart can clarify the offer.",
            "attention_reason":"Buyers may not readily understand what a different package includes.", "research_questions":[]}}
    output = {"moments":[moment], "processed_span_ids":[s.span_id for s in spans], "coverage_notes":[]}
    pipeline = Pipeline(Settings(data_root=tmp_path/"data"))
    moments = pipeline._parse_moments(output, "synthetic", [transcript])
    mid = moments[0].moment_id
    angle = {"local_key":"a1", "title":"How we make a distinctive venue offer understandable",
        "content_opportunity":"Show the positioning work behind deciding where package comparisons belong.",
        "strategic_purpose":"WARM", "content_type":"process",
        "strategic_rationale":"Makes the team's judgment and collaborative working process tangible.",
        "audience":"Wedding-business owners whose offering differs from easy-to-compare alternatives.",
        "core_perspective":"Making an offer's value understandable is part of the advertising work.",
        "tension":"An owner understands the package, while an unfamiliar couple may not.",
        "wia_expertise_in_action":"The team proposes reviewing page placement for the client's existing chart.",
        "service_relevance":"Positioning and landing-page discussion.", "reader_decision":None,
        "evidence_readiness":"supported", "research_questions":[],
        "selection_reason":"Shows concrete work beyond a general lesson about package prices.",
        "moment_ids":[mid], "source_assertions":[f"[{mid}] The client already has a chart; the team proposes reviewing its placement."],
        "inference":None, "qualifiers":[], "risks":[],
        "quality":{"grounding":4., "strategic_fit":4., "distinctiveness":4., "audience_resonance":4.,
                   "source_strength":4., "reasons":["Concrete proposed collaboration, not a performance result."]}}
    response = {"angles":[angle], "internal_insights":[], "processed_moment_ids":[mid], "coverage_notes":[]}
    return pipeline, transcript, moments, response


def test_current_schemas_are_closed_and_every_field_is_explicit():
    def check(value):
        if isinstance(value,dict):
            if value.get("type")=="object":
                assert value.get("additionalProperties") is False
                assert set(value["required"])==set(value["properties"])
            for child in value.values(): check(child)
        elif isinstance(value,list):
            for child in value: check(child)
    for contract in (StrategicMomentResponse,StrategicCompactMomentResponse,StrategicAngleResponse,StrategicRefinementResponse):
        check(contract.model_json_schema())
    assert "argument" not in StrategicAngleResponse.model_json_schema()["$defs"]["StrategicAngleDraft"]["properties"]
    assert "take" not in StrategicAngleResponse.model_json_schema()["$defs"]["StrategicAngleDraft"]["properties"]


def test_optional_decision_and_strategy_survive_parsing_and_storage(strategy_case):
    p,t,m,response = strategy_case
    angle = p._parse_angles(response,"synthetic",m)[0]
    assert angle.reader_decision is None
    assert angle.strategy.core_perspective==response["angles"][0]["core_perspective"]
    assert angle.strategy.strategic_purpose=="WARM"
    assert m[0].discovery.wia_contribution
    assert m[0].qualifications[0] in angle.qualifiers
    assert m[0].qualifications[0] in angle.strategy.qualifiers
    p._write_discovery_outputs("preview",response,[angle])
    saved = p.store.read_json("preview/opportunities.json")[0]
    assert saved["reader_decision"] is None and "take" not in saved
    assert saved["source_family_id"]==angle.source_family_id
    assert p.store.read_json("preview/internal_insights.json")==[]


def test_purpose_labels_cannot_make_identical_perspectives_distinct(strategy_case):
    p,_t,m,response = strategy_case
    other = copy.deepcopy(response["angles"][0])
    other.update(local_key="a2",title="A new hook",strategic_purpose="CONVERT",content_type="solution_selling")
    assert signature_from_fields(other)==signature_from_fields(response["angles"][0])
    response["angles"].append(other)
    with pytest.raises(ValueError,match="Duplicate canonical"):
        p._parse_angles(response,"synthetic",m)


def test_substantive_treatments_share_the_source_family(strategy_case):
    p,_t,m,response = strategy_case
    other = copy.deepcopy(response["angles"][0])
    other.update(local_key="a2",strategic_purpose="CONVERT",content_type="solution_selling",
        content_opportunity="Explain what an owner receives from collaborative positioning support.",
        core_perspective="Management support includes interpreting client knowledge into a clearer offer.",
        tension="The owner knows the offer but needs help communicating it to couples.")
    response["angles"].append(other)
    angles = p._parse_angles(response,"synthetic",m)
    assert len(angles)==2 and angles[0].signature!=angles[1].signature
    assert angles[0].source_family_id==angles[1].source_family_id


def test_internal_learning_does_not_require_public_angles(strategy_case):
    p,_t,m,response = strategy_case
    response["angles"]=[]
    response["internal_insights"]=[{"moment_ids":[m[0].moment_id],"insight":"The client already has comparison material.",
        "strategic_use":"Explore how onboarding discovers existing client assets.","research_questions":[]}]
    assert p._parse_angles(response,"synthetic",m)==[]
    response["internal_insights"][0]["moment_ids"]=["invented"]
    with pytest.raises(ValueError,match="Internal insight"):
        p._parse_angles(response,"synthetic",m)


def test_research_hypothesis_cannot_become_visible_or_hide_its_question(strategy_case):
    p,_t,m,response = strategy_case
    response["angles"][0]["evidence_readiness"]="research_required"
    with pytest.raises(ValidationError,match="research question"):
        p._parse_angles(response,"synthetic",m)
    response["angles"][0]["research_questions"]=["Review earlier context to establish the proposed page's audience."]
    angles = p._parse_angles(response,"synthetic",m)
    ranked = rank(angles,[],threshold=.78,visible_threshold=0,half_life=28,max_penalty=.5)
    assert ranked[0].status=="suppressed" and ranked[0].strategy.evidence_readiness=="research_required"
    from backend_pipeline.angle_workflow import diagnoses
    assert "source_research_required" in diagnoses({"evidence_readiness":"research_required",
        "grounding_valid":True,"coverage_complete":True,"base_score":100.,"max_historical_cosine":0.},.78)
    with pytest.raises(ValidationError,match="research question"):
        Discovery.model_validate({"lenses":["service_value"],"destination":"research_needed","wia_contribution":None,
                                  "attention_reason":"Product praise needs context.","research_questions":[]})


def test_high_grounding_cannot_compensate_for_weak_strategic_fit(strategy_case):
    p,_t,m,response = strategy_case
    q=response["angles"][0]["quality"]
    for key in ("grounding","distinctiveness","audience_resonance","source_strength"): q[key]=5.
    q["strategic_fit"]=1.
    assert p._parse_angles(response,"synthetic",m)[0].base_score==20.


def test_current_contract_rejects_missing_strategy_instead_of_filling_defaults(strategy_case):
    p,_t,_m,response = strategy_case
    del response["angles"][0]["strategic_purpose"]
    with pytest.raises(ValidationError):
        p._validate_current_contract(response,StrategicAngleResponse.model_json_schema())


def test_all_prompt_paths_receive_the_same_trusted_strategy_and_current_fields(strategy_case):
    p,t,m,_response = strategy_case
    pool=p._moment_packet(m,[t])
    paths=[moment_prompt([s.model_dump() for s in t.spans]),weekly_moment_prompt("m1.t0001|0+1|source",[]),
           angle_prompt(pool,[]),sql_angle_prompt(pool,[]),sql_refinement_prompt(pool,[],[],[])]
    for system,_user in paths:
        assert STRATEGY_VERSION in system
        assert "Five discovery lenses" in system and "Calibration contrasts" in system
        assert "No exact action, CTA" in system or "Do not require an exact audience action" in system
    for system,user in paths[2:]:
        assert "core_perspective" in system+user and "strategic_purpose" in system+user
        assert any(text in system for text in ("private step-by-step reasoning", "no explanatory prose or private reasoning"))
    assert json.loads(paths[3][1])["evidence_by_id"]["s2"]["text"]==t.spans[2].text


def test_gate_edit_keeps_the_authoritative_perspective_and_compatibility_view_in_sync(strategy_case,monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from backend_pipeline import gate_one
    p,_t,m,response=strategy_case
    angle=p._parse_angles(response,"synthetic",m)[0]
    body=angle.model_dump(mode="json",include={"title","argument","audience","tension","take","mechanism",
        "reader_decision","source_assertions","inference","qualifiers","risks","strategy","source_family_id"})
    row={"content_body":body,"angle_id":angle.angle_id,"week_id":"week1","run_id":"synthetic",
         "first_generated_at":angle.generated_at,"embedding":None,"embedding_input_hash":None}
    class Connection:
        def execute(self,query,params=None):
            if "SELECT moment_id" in query: return [{"moment_id":m[0].moment_id}]
            if "SELECT moment_body" in query: return [{"moment_body":{"qualifications":m[0].qualifications}}]
            raise AssertionError("Unexpected database interaction")
    @contextmanager
    def connection(): yield Connection()
    repo=SimpleNamespace(connection=connection,event=lambda *args,**kwargs:None,settings=SimpleNamespace(brief_approvers=("tester",), brief_editors=("editor",)))
    writes=[]
    monkeypatch.setattr(gate_one,"locked",lambda *args,**kwargs:row)
    monkeypatch.setattr(gate_one,"insert",lambda conn,table,data:writes.append((table,data)))
    gate_one.edit(repo,angle.angle_id,"current",{"core_perspective":"Client knowledge is part of collaborative positioning."},"editor")
    saved=writes[0][1]["content_body"]
    assert saved["argument"]==saved["take"]==saved["strategy"]["core_perspective"]
    assert signature_from_fields(saved)!=angle.signature
    assert saved["reader_decision"] is None
    with pytest.raises(ValueError,match="Source qualifications"):
        gate_one.edit(repo,angle.angle_id,"current",{"qualifiers":[]},"editor")


def test_gate_rejects_research_hypothesis_before_approval(strategy_case,monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from backend_pipeline import gate_one
    p,_t,m,response=strategy_case
    response["angles"][0].update(evidence_readiness="research_required",research_questions=["Review missing source detail."])
    angle=p._parse_angles(response,"synthetic",m)[0]
    row={"content_body":{"strategy":angle.strategy.model_dump()},"approval_status":"pending"}
    @contextmanager
    def connection(): yield object()
    repo=SimpleNamespace(connection=connection,settings=SimpleNamespace(brief_enabled=False,brief_approvers=("tester",),brief_editors=("editor",)))
    monkeypatch.setattr(gate_one,"comparison_owned",lambda *args:False)
    monkeypatch.setattr("backend_pipeline.removal.mark_of",lambda *args:None)  # no database here (6.B12's mark)
    monkeypatch.setattr(gate_one,"locked",lambda *args,**kwargs:row)
    with pytest.raises(ValueError,match="Source research is required"):
        gate_one.decide(repo,angle.angle_id,"current","approved",None,False,"","tester")
