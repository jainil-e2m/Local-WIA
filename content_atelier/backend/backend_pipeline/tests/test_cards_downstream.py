"""Offline checks for strategist cards downstream (E.B16), per-moment extraction (E.B12a) and prompt hygiene (E.B17).

Synthetic fixtures and fake providers only: no HTTP, no client documents, no paid model calls. The PostgreSQL
paths are covered end to end in test_cards_sql.py, which needs an isolated atelier_test database.
"""
from __future__ import annotations

import copy
import json
import re
from collections import Counter

import pytest
from pydantic import ValidationError

from backend_pipeline import gate_one
from backend_pipeline.angle_profiles import (
    EXAMPLE_PROVENANCE,
    LEGACY_PROFILE,
    STRATEGIST_PROFILE,
    STRATEGIST_TEMPLATES,
    STRATEGIST_V4_PROFILE,
    card_reference_problems,
    resolve_card_references,
    scene_references,
    strategist_user,
    uses_cards,
    uses_scene_references,
)
from backend_pipeline.config import Settings
from backend_pipeline.contracts import signature_from_fields
from backend_pipeline.matching import card_visibility, split_history
from backend_pipeline.models import RunManifest
from backend_pipeline.moment_validation import REPAIR_RULE, repair_quote, resolve_moment_references_partial
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.prompts import weekly_moment_prompt
from backend_pipeline.repository import card_selection_view, current_versions
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.store import canonical_hash
from backend_pipeline.strategy_contracts import StrategicCompactMomentResponse
from backend_pipeline.tests.test_strategist_profile import card, cards_output, moment, write_kb
from backend_pipeline.weekly import meeting_inventory

SOL, LUNA = "openai/gpt-6.1-sol", "openai/gpt-6-luna"


# (h) Model override scoped to the strategist ------------------------------------------------------------


@pytest.mark.parametrize("profile,expected", [(LEGACY_PROFILE, LUNA), (STRATEGIST_PROFILE, SOL), (STRATEGIST_V4_PROFILE, SOL)])
def test_angle_generation_override_applies_to_strategist_profiles_only(profile, expected):
    settings = Settings(angle_prompt_profile=profile, openrouter_angle_generation_model=SOL)
    assert settings.model_for("angle_generation") == expected
    assert settings.model_for("moment_extraction") == settings.model_for("angle_refinement") == LUNA


# E.B17 Prompt hygiene ------------------------------------------------------------------------------------


def template(profile):
    return STRATEGIST_TEMPLATES[profile].read_text(encoding="utf-8")


def test_v4_prompt_drops_week_derived_examples_and_keeps_v3_for_replay():
    v3, v4 = template(STRATEGIST_PROFILE), template(STRATEGIST_V4_PROFILE)
    for derived in ("LeadLock features", "where to advertise a venue", "geographic reach", "negative keywords",
                    "far below her minimum", "a keyword, a landing-page image"):
        assert derived in v3 and derived not in v4
    # The general rule about pricing objections stays a rule.
    assert "Do not turn a prospect's objection to WIA's own pricing into public advice" in v4
    assert uses_cards(STRATEGIST_V4_PROFILE) and uses_scene_references(STRATEGIST_V4_PROFILE)
    assert not uses_scene_references(STRATEGIST_PROFILE) and not uses_scene_references(LEGACY_PROFILE)


def test_profile_records_the_source_of_every_example_and_v4_derives_from_no_week():
    v4 = template(STRATEGIST_V4_PROFILE)
    for entry in EXAMPLE_PROVENANCE[STRATEGIST_V4_PROFILE]:
        assert entry["source"] and entry["kind"] in {"example", "rule"}
        assert entry["derived_from_weeks"] == []
        assert entry["text"] in v4
    assert {e["location"] for e in EXAMPLE_PROVENANCE[STRATEGIST_PROFILE]} == {
        e["location"] for e in EXAMPLE_PROVENANCE[STRATEGIST_V4_PROFILE]}
    assert any(e["derived_from_weeks"] for e in EXAMPLE_PROVENANCE[STRATEGIST_PROFILE])


# (f) Scene tags and (i) short references ---------------------------------------------------------------


DISCOVERY = {"lenses": ["wia_expertise"], "destination": "internal_intelligence", "wia_contribution": None,
             "attention_reason": "Pricing reaction.", "research_questions": []}


def packet():
    public = moment("moment_public", qualifications=["Not a measured result"], sensitivity="public_candidate")
    internal = moment("moment_internal", qualifications=[], sensitivity="internal_only", discovery=DISCOVERY)
    spans = [{"start_seconds": 1.0, "speaker": "Team Member", "text": "Scene text."}]
    return [{**m.model_dump(mode="json"), "source_evidence": spans} for m in (public, internal)]


def test_v4_user_message_shows_handling_and_short_references_only():
    user = strategist_user(packet(), STRATEGIST_V4_PROFILE)
    assert "## Scene S1 " in user and "## Scene S2 " in user and "moment_public" not in user and "moment_internal" not in user
    s2 = user.split("## Scene S2", 1)[1]
    assert "internal only: use this scene in internal_insights only" in s2
    assert "suggested destination (a pointer, not a ruling): internal_intelligence" in s2
    assert "Qualifications to respect: none recorded." in s2
    assert "Qualifications to respect: Not a measured result." in user.split("## Scene S2", 1)[0]
    # Version 3 keeps its replayable format: full moment IDs, no tags.
    v3 = strategist_user(packet(), STRATEGIST_PROFILE)
    assert "## Moment moment_public " in v3 and "Handling:" not in v3


def test_reference_problems_cover_unknown_repeated_and_internal_only_public_use():
    refs = scene_references(packet())
    sensitivity = {"moment_public": "public_candidate", "moment_internal": "internal_only"}
    good = cards_output("S1", internal_insights=[{"moment_ids": ["S2"], "insight": "Pricing.", "use": "Sales."}],
                        considered_not_selected=[])
    assert card_reference_problems(good, refs, sensitivity) == []
    resolved = resolve_card_references(good, refs)
    assert resolved["angles"][0]["moment_ids"] == ["moment_public"] and good["angles"][0]["moment_ids"] == ["S1"]
    assert resolved["internal_insights"][0]["moment_ids"] == ["moment_internal"]
    bad = copy.deepcopy(good)
    bad["angles"][0]["moment_ids"] = ["S9"]
    bad["angles"][1]["moment_ids"] = ["S2"]
    bad["considered_not_selected"] = [{"moment_ids": ["S1", "S1"], "idea": "x", "reason": "y"}]
    problems = card_reference_problems(bad, refs, sensitivity)
    assert any("unknown scene references: S9" in p for p in problems)
    assert any("internal-only scenes S2" in p for p in problems)
    assert any("repeats a scene reference" in p for p in problems)


class ScenesProvider:
    """Fake strategist for version 4: cites short references; the first answer can be wrong once."""

    def __init__(self, *, first="unknown", repair_ok=True):
        self.calls, self.users, self.first, self.repair_ok = Counter(), [], first, repair_ok

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls[stage] += 1
        self.users.append(user)
        if stage == "moment_extraction":
            refs = re.findall(r"^(m\d+\.t\d+)\|", user, re.MULTILINE)
            base = {"local_key": "m1", "anchor_span_ids": [refs[0]], "context_first_span_id": refs[0],
                    "context_last_span_id": refs[0], "quote": "How does your landing page describe pricing?",
                    "context_summary": "Pricing copy.", "moment_type": "observation", "proposition": "Copy filters leads.",
                    "audience_relevance": "Planners", "qualifications": ["Not a measured result"], "claim_status": "reported",
                    "sensitivity": "unknown", "strength": 4.0, "reasons": ["Concrete"], "discovery": DISCOVERY}
            internal = {**base, "local_key": "m2", "anchor_span_ids": [refs[1]], "context_first_span_id": refs[1],
                        "context_last_span_id": refs[1], "quote": "We never mention it.", "sensitivity": "internal_only"}
            return {"moments": [base, internal], "coverage_notes": [],
                    "processed_meetings": [{"meeting_ref": "m1", "first_span_id": refs[0], "last_span_id": refs[-1],
                                            "span_count": len(refs)}]}, {"fake": True}
        assert re.findall(r"^## Scene (S\d+) ", user, re.MULTILINE) == ["S1", "S2"]
        repair = "## Correction needed" in user
        output = cards_output("S1", internal_insights=[{"moment_ids": ["S2"], "insight": "Pricing.", "use": "Sales."}])
        if not repair or not self.repair_ok:
            if self.first == "unknown":
                output["angles"][0]["moment_ids"] = ["S7"]
            elif self.first == "internal":
                output["angles"][0]["moment_ids"] = ["S2"]
        return output, {"fake": True}

    def embed(self, *, text, fingerprint):
        raise AssertionError("No embeddings in this test")


@pytest.fixture
def week(tmp_path):
    folder = tmp_path / "inputs" / "week1"
    folder.mkdir(parents=True)
    (folder / "meeting.vtt").write_bytes(
        b"WEBVTT\n\n1\n00:00:00.000 --> 00:00:05.000\nTeam Member: How does your landing page describe pricing?\n\n"
        b"2\n00:00:04.000 --> 00:00:09.500\nPlanner: We never mention it.\n\n")
    return tmp_path


def v4_settings(root, **changes):
    values = dict(data_root=root / "data", transcript_root=root / "inputs", llm_payload_format="compact_weekly",
                  embedding_dimensions=3, angle_prompt_profile=STRATEGIST_V4_PROFILE,
                  knowledge_base_root=write_kb(root / "kb"), openrouter_angle_generation_model=SOL)
    values.update(changes)
    return Settings(**values)


@pytest.mark.parametrize("first", ["unknown", "internal"])
def test_bad_reference_gets_exactly_one_repair_call_and_replay_reuses_both(week, first):
    provider = ScenesProvider(first=first)
    pipeline = Pipeline(v4_settings(week), provider)
    result = pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 2}
    assert "## Correction needed" in provider.users[-1] and "Cite scenes only with these references: S1, S2" in provider.users[-1]
    run_dir = f"experiments/default/runs/{result['run_id']}"
    repair = pipeline.store.read_json(f"{run_dir}/angle_reference_repair.json")
    assert repair["problems"] and repair["first_request_fingerprint"] != repair["repair_request_fingerprint"]
    cards = pipeline.store.read_json(f"{run_dir}/angle_cards.json")
    assert [c["rank"] for c in cards] == [1, 2] and all(c["moment_ids"][0].startswith("moment_") for c in cards)
    selection = pipeline.store.read_json(f"{run_dir}/angle_selection.json")
    assert selection["internal_insights"][0]["moment_ids"][0].startswith("moment_")
    Pipeline(v4_settings(week), provider).run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 2}


def test_a_second_bad_answer_fails_without_a_third_call(week):
    provider = ScenesProvider(first="unknown", repair_ok=False)
    with pytest.raises(ValueError, match="still invalid after one repair"):
        Pipeline(v4_settings(week), provider).run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 2}


def test_good_references_need_no_repair(week):
    provider = ScenesProvider(first="none")
    Pipeline(v4_settings(week), provider).run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}


# (a) Selection without scores ------------------------------------------------------------------------------


def test_card_visibility_is_rank_plus_duplicate_check_without_a_threshold():
    cards = [{"angle_id": "c", "rank": 3}, {"angle_id": "a", "rank": 1}, {"angle_id": "b", "rank": 2},
             {"angle_id": "d", "rank": 4}]
    pairs = {"c": [{"angle_id": "a", "cosine": .95}], "a": [{"angle_id": "c", "cosine": .95}],
             "b": [{"angle_id": "a", "cosine": .85}], "d": [{"angle_id": "c", "cosine": .99}]}
    result = card_visibility(cards, pairs)
    assert result["a"] == {"selection_status": "visible", "reason": "ranked", "display_rank": 1}
    assert result["b"]["selection_status"] == "visible" and result["b"]["display_rank"] == 2
    assert result["c"] == {"selection_status": "suppressed", "reason": "duplicate", "duplicate_of": "a", "cosine": .95}
    # A twin of a collapsed card is not collapsed into it.
    assert result["d"]["selection_status"] == "visible"
    superseded = card_visibility(cards, pairs, superseded={"a"})
    assert superseded["a"]["reason"] == "superseded_by_edit" and superseded["c"]["selection_status"] == "visible"


class ProvenanceConn:
    def __init__(self, vectors):
        self.vectors = vectors

    def execute(self, statement, params=()):
        assert statement.startswith("SELECT result_refs FROM pipeline_jobs")
        return [{"result_refs": {"contract": "c", "vectors": self.vectors}}]


def test_history_never_encoded_is_a_recorded_gap_but_a_lost_vector_still_counts():
    from backend_pipeline.matching import vector_digest

    body = {"card": card("moment_a")}
    vector = [1.] + [0.] * 1535
    ih = canonical_hash(signature_from_fields(body))
    embedded = {"angle_id": "a1", "content_body": body, "embedding": vector, "embedding_input_hash": ih}
    never = {"angle_id": "a2", "content_body": body, "embedding": None, "embedding_input_hash": None}
    lost = {"angle_id": "a3", "content_body": body, "embedding": None, "embedding_input_hash": None}
    other_model = {"angle_id": "a4", "content_body": body, "embedding": vector, "embedding_input_hash": ih}
    conn = ProvenanceConn([{"angle_id": aid, "input_hash": ih, "vector_digest": vector_digest(vector)} for aid in ("a1", "a3")])
    usable, gaps = split_history(conn, [embedded, never, lost, other_model], "c")
    # The lost vector stays in history, so matching still pauses on it as an integrity problem.
    assert [a["angle_id"] for a in usable] == ["a1", "a3"]
    assert gaps == [{"id": "a2", "reason": "no_compatible_vector"}, {"id": "a4", "reason": "no_compatible_vector"}]
    assert split_history(conn, [never], None) == ([never], [])


# (b) Approval rule -----------------------------------------------------------------------------------------


def test_card_cta_may_be_decided_in_development_and_text_still_works():
    assert gate_one.cta_kind({"choice": "decide_in_development"}, card=True) == "decide_in_development"
    assert gate_one.cta_kind({"text": "Book a call"}, card=True) == "text"
    for bad in (None, {}, {"text": " "}, {"choice": "later"}):
        with pytest.raises(ValueError, match="CTA"):
            gate_one.cta_kind(bad, card=True)
    # The default profile's rule is unchanged: it needs written CTA text.
    with pytest.raises(ValueError, match="A selected CTA is required"):
        gate_one.cta_kind({"choice": "decide_in_development"}, card=False)


def test_every_verify_item_must_be_acknowledged_and_internal_scenes_block_approval():
    item = card("moment_a", verify_before_publishing=["Confirm the client may be named.", "Check the month."])
    with pytest.raises(ValueError, match="Check the month"):
        gate_one.check_card_approval(item, ["Confirm the client may be named."], {"moment_a": "unknown"})
    gate_one.check_card_approval(item, item["verify_before_publishing"], {"moment_a": "unknown"})
    gate_one.check_card_approval(card("moment_a", verify_before_publishing=[]), None, {"moment_a": "public_candidate"})
    with pytest.raises(ValueError, match="internal-only"):
        gate_one.check_card_approval(item, item["verify_before_publishing"], {"moment_a": "internal_only"})


# (c) Edit path ---------------------------------------------------------------------------------------------


def card_body():
    value = card("moment_a")
    return {"title": value["title"], "argument": value["core_perspective"], "audience": value["audience"], "tension": "",
            "take": value["core_perspective"], "mechanism": value["wia_in_action"], "reader_decision": None,
            "source_assertions": [], "inference": None, "qualifiers": ["Not a measured result"], "risks": ["r"],
            "card": value, "source_family_id": "source_family_x"}


def test_card_edit_validates_against_the_card_contract_and_changes_the_signature():
    body = card_body()
    edited = gate_one.edited_card_body(body, {"core_perspective": "A sharper point.", "title": "A plainer title"})
    assert edited["card"]["core_perspective"] == edited["argument"] == edited["take"] == "A sharper point."
    assert edited["title"] == edited["card"]["title"] == "A plainer title"
    assert edited["card"]["rank"] == 1 and edited["card"]["moment_ids"] == ["moment_a"]
    assert edited["qualifiers"] == body["qualifiers"] and body["card"]["core_perspective"] != "A sharper point."
    assert signature_from_fields(edited) != signature_from_fields(body)
    assert canonical_hash({"body": edited, "moments": ["moment_a"]}) != canonical_hash({"body": body, "moments": ["moment_a"]})
    # Pillar-only edits do not change the argument, so the vector can be reused.
    assert signature_from_fields(gate_one.edited_card_body(body, {"pillar": "CONVERT"})) == signature_from_fields(body)
    for changes in ({"rank": 2}, {"moment_ids": ["moment_b"]}, {"argument": "x"}, {}):
        with pytest.raises(ValueError, match="Card edits"):
            gate_one.edited_card_body(body, changes)
    with pytest.raises(ValidationError):
        gate_one.edited_card_body(body, {"verify_before_publishing": ["a", "b", "c"]})
    with pytest.raises(ValidationError):
        gate_one.edited_card_body(body, {"pillar": "SELL"})


def test_edit_routes_cards_to_the_card_path_and_rescore_refuses_cards(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    row = {"angle_id": "angle_card", "content_body": card_body(), "week_id": "w", "run_id": "r",
           "first_generated_at": None, "embedding": None, "embedding_input_hash": None}

    class Conn:
        def execute(self, statement, params=()):
            assert statement.startswith("SELECT moment_id FROM angle_moments")
            return [{"moment_id": "moment_a"}]

    @contextmanager
    def connection():
        yield Conn()

    writes = []
    repo = SimpleNamespace(connection=connection, event=lambda *a, **k: None, settings=SimpleNamespace(brief_approvers=("tester",), brief_editors=("editor",)))
    monkeypatch.setattr(gate_one, "locked", lambda *a, **k: row)
    monkeypatch.setattr(gate_one, "insert", lambda conn, table, data: writes.append((table, data)))
    # The new version's comparison check is queued in the database (test_gate_one_decisions_db.py covers it).
    monkeypatch.setattr(gate_one, "queue_card_check", lambda *a, **k: {"status": "queued"})
    saved = gate_one.edit(repo, "angle_card", "h", {"why_it_matters": "Owners see the process."}, "editor")
    body = writes[0][1]["content_body"]
    assert writes[0][1]["supersedes_id"] == "angle_card" and body["card"]["why_it_matters"] == "Owners see the process."
    assert saved["content_hash"] == canonical_hash({"body": body, "moments": ["moment_a"]})
    with pytest.raises(ValueError, match="ranked, not scored"):
        gate_one.rescore(repo, "angle_card", "h", {"grounding": 5., "source_relevance": 5., "audience_fit": 5.,
                                                   "specificity": 5., "editorial_usefulness": 5., "reasons": ["r"]}, "editor")


# (d) Profile frozen at submit -------------------------------------------------------------------------------


def test_worker_refuses_a_run_frozen_under_another_profile(tmp_path):
    worker = object.__new__(SQLWorker)
    worker.models = Settings(angle_prompt_profile=LEGACY_PROFILE)
    assert worker.frozen_profile({"input_refs": {}}) == LEGACY_PROFILE
    assert worker.frozen_profile({"input_refs": {"angle_prompt_profile": LEGACY_PROFILE}}) == LEGACY_PROFILE
    with pytest.raises(ValueError, match="frozen at submit"):
        worker.frozen_profile({"input_refs": {"angle_prompt_profile": STRATEGIST_V4_PROFILE}})


def test_worker_refuses_a_run_whose_models_changed_after_submit():
    """E.B16 (n): a run submitted under Sol is never silently run under another model after a worker restart."""
    from backend_pipeline.sql_pipeline import frozen_models
    submitted = Settings(angle_prompt_profile=STRATEGIST_V4_PROFILE, openrouter_angle_generation_model="openai/gpt-6.1-sol")
    worker = object.__new__(SQLWorker)
    worker.models = submitted
    run = {"input_refs": {"angle_prompt_profile": STRATEGIST_V4_PROFILE, "models": frozen_models(submitted)}}
    assert worker.frozen_profile(run) == STRATEGIST_V4_PROFILE
    assert frozen_models(submitted)["angle_generation"] == "openai/gpt-6.1-sol"
    worker.models = submitted.model_copy(update={"openrouter_angle_generation_model": "openai/gpt-6-luna"})
    with pytest.raises(ValueError, match="models frozen at submit"):
        worker.frozen_profile(run)


# (g) Selection block ---------------------------------------------------------------------------------------


def test_selection_block_ranks_cards_and_follows_edits():
    refs = {"week_summary": "Summary.", "ranked_angle_ids": ["a1", "a2"], "considered_not_selected": [{"idea": "x"}],
            "internal_insights": [{"insight": "y"}], "unreferenced_moment_ids": ["m9"]}
    angles = {"a2": {"content_body": {"card": {"title": "Second"}}, "selection_status": "visible", "approval_status": "pending",
                     "matching_result": {"selection": {"selection_status": "visible"}}},
              "a1e": {"content_body": {"card": {"title": "First, edited"}}, "selection_status": "candidate",
                      "approval_status": "pending", "matching_result": None}}
    lineage = {"a1": None, "a2": None, "a1e": "a1"}
    view = card_selection_view("run_1", refs, angles, lineage)
    assert [(r["rank"], r["angle_id"], r["current_angle_id"], r["title"]) for r in view["ranking"]] == [
        (1, "a1", "a1e", "First, edited"), (2, "a2", "a2", "Second")]
    # Each considered idea carries its index for the revive and decision routes (E.B20).
    assert view["week_summary"] == "Summary." and view["considered_not_selected"] == [{"idea": "x", "index": 0}]
    assert view["internal_insights"] == [{"insight": "y"}] and view["unreferenced_moment_ids"] == ["m9"]
    assert view["selection_hash"] and "publishing_order" not in view, "v5 fields appear only when the run has them"
    v5 = card_selection_view("run_1", {**refs, "publishing_order": [2, 1], "pillar_notes": [], "seed_pairings": []}, angles, lineage)
    assert v5["publishing_order"] == [2, 1] and v5["pillar_notes"] == [] and v5["seed_pairings"] == []
    assert card_selection_view("run_2", refs, angles, lineage)["selection_hash"] != view["selection_hash"], "bound to its run"
    assert current_versions({"x": None, "y": "x", "z": "y"}) == {"x": "z", "y": "z", "z": "z"}


# E.B12a Per-moment extraction ------------------------------------------------------------------------------


def test_repair_matches_words_ignoring_whitespace_punctuation_and_the_first_words_case():
    text = "Planner: We never — honestly — mention   it, ever."
    assert repair_quote("We never honestly mention it", [text]) == ("We never — honestly — mention   it", 0)
    assert repair_quote("never, honestly: mention it ever", ["other", text]) == ("never — honestly — mention   it, ever", 1)
    # Only the first word's case may differ (a quote starting mid-sentence is capitalised); elsewhere case is not punctuation.
    assert repair_quote("we never honestly mention it", [text]) == ("We never — honestly — mention   it", 0)
    assert repair_quote("We Never honestly mention it", [text]) is None
    assert repair_quote("We always mention it", [text]) is None
    assert repair_quote("mention it", [text]) is None  # Too short to bind safely.


def extraction(refs, moments):
    return {"moments": moments, "coverage_notes": [],
            "processed_meetings": [{"meeting_ref": "m1", "first_span_id": refs[0], "last_span_id": refs[-1], "span_count": len(refs)}]}


def draft(key, ref, quote, **changes):
    value = {"local_key": key, "anchor_span_ids": [ref], "context_first_span_id": ref, "context_last_span_id": ref,
             "quote": quote, "context_summary": "s", "moment_type": "observation", "proposition": "p",
             "audience_relevance": "a", "qualifications": [], "claim_status": "reported", "sensitivity": "unknown",
             "strength": 3.0, "reasons": ["r"], "discovery": DISCOVERY}
    value.update(changes)
    return value


@pytest.fixture
def compact(week):
    pipeline = Pipeline(v4_settings(week, angle_prompt_profile=LEGACY_PROFILE))
    transcripts, packet_text = pipeline.load_week(1)
    return pipeline, transcripts, packet_text, pipeline._compact_refs


def mixed_output(refs):
    return extraction(list(refs), [
        draft("exact", "m1.t0001", "How does your landing page describe pricing?"),
        draft("near", "m1.t0002", "We never  mention it"),
        draft("wrong", "m1.t0002", "We always mention pricing on every page."),
        draft("unknown", "m1.t0099", "We never mention it."),
    ])


def test_one_bad_quote_keeps_every_bindable_moment(compact):
    pipeline, transcripts, _packet, refs = compact
    resolved, unresolved = resolve_moment_references_partial(mixed_output(refs), refs)
    result = pipeline._partition_moments(resolved, "run", transcripts, unresolved=unresolved)
    assert [m.quote for m in result.moments] == ["How does your landing page describe pricing?", "We never mention it"]
    assert result.repairs == [{"local_key": "near", "rule": REPAIR_RULE, "original_quote": "We never  mention it",
                               "repaired_quote": "We never mention it", "anchor_span_id": result.moments[1].anchor_span_ids[0],
                               "moment_id": result.moments[1].moment_id}]
    assert {u["local_key"]: u["usable_as_proof"] for u in result.unverified} == {"wrong": False, "unknown": False}
    assert "quote must match" in next(u for u in result.unverified if u["local_key"] == "wrong")["reason"]
    assert "unknown compact source ID" in next(u for u in result.unverified if u["local_key"] == "unknown")["reason"]
    # An exact moment keeps the identity the strict parser gives it.
    exact = extraction(list(refs), [draft("exact", "m1.t0001", "How does your landing page describe pricing?")])
    from backend_pipeline.weekly import resolve_moment_references
    strict = pipeline._parse_moments(resolve_moment_references(exact, refs), "run", transcripts)
    assert strict[0].moment_id == result.moments[0].moment_id
    summary = result.summary()
    assert summary["unverified_count"] == 2 and summary["unverified_usable_as_proof"] is False


@pytest.mark.parametrize("mutation", ["schema", "coverage"])
def test_only_a_response_level_failure_fails_the_week(compact, mutation):
    pipeline, transcripts, _packet, refs = compact
    output = mixed_output(refs)
    if mutation == "schema":
        output["moments"][2]["strength"] = "high"
    else:
        output["processed_meetings"][0]["span_count"] = 99
    with pytest.raises(ValueError):
        resolved, unresolved = resolve_moment_references_partial(output, refs)
        pipeline._partition_moments(resolved, "run", transcripts, unresolved=unresolved)


class SavedResponseProvider:
    def __init__(self, output):
        self.output, self.calls = output, 0

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls += 1
        if self.output is None:
            raise AssertionError("Re-validation must not call the provider")
        return copy.deepcopy(self.output), {"fake": True, "raw": {"usage": {"cost": 0.01}}}


def test_saved_failed_extraction_is_revalidated_without_a_provider_call(compact, week, monkeypatch):
    from backend_pipeline.tests.test_extraction_partition import strict_extraction
    pipeline, _transcripts, _packet, refs = compact
    settings = v4_settings(week, angle_prompt_profile=LEGACY_PROFILE)
    first = SavedResponseProvider(mixed_output(refs))
    strict = Pipeline(settings, first)
    with monkeypatch.context() as earlier:
        # A response saved before E.B12a reached the file runner, when one unbindable quote failed the week.
        earlier.setattr(Pipeline, "_extraction_partition", strict_extraction)
        with pytest.raises(ValueError):
            strict.run(1, run_id="strict-extraction")
    assert first.calls == 1

    none = SavedResponseProvider(None)
    sql_like = Pipeline(settings, none)
    transcripts, packet_text = sql_like.load_week(1)
    system, user = weekly_moment_prompt(packet_text, meeting_inventory(sql_like._compact_refs))
    input_hash = canonical_hash({"system": system, "user": user,
                                 "source": [{"source_id": t.source_id, "revision": t.content_hash} for t in transcripts]})
    run = RunManifest(run_id="revalidation", week_index=1, source_root="x", source_ids=[t.source_id for t in transcripts],
                      prompt_profile="p", model_id=LUNA, embedding_profile="e", mode="fake")

    def partition(out):
        resolved, unresolved = resolve_moment_references_partial(out, sql_like._compact_refs)
        return sql_like._partition_moments(resolved, run.run_id, transcripts, unresolved=unresolved)

    artifact = sql_like._call_json("moment_extraction", run, "experiments/sql/runs/revalidation", system, user, input_hash,
                                   StrategicCompactMomentResponse.model_json_schema(), validate=partition)
    assert none.calls == 0
    assert artifact.status == "validated" and artifact.metadata["revalidated_from_attempt"].startswith("service_calls/")
    assert artifact.metadata["original_error"]  # The earlier strict failure stays on record.
    result = partition(artifact.output)
    assert len(result.moments) == 2 and len(result.repairs) == 1 and len(result.unverified) == 2
    # The promoted artifact is cached: the next run reuses it directly.
    again = sql_like._call_json("moment_extraction", run, "experiments/sql/runs/revalidation", system, user, input_hash,
                                StrategicCompactMomentResponse.model_json_schema(), validate=partition)
    assert again.artifact_id == artifact.artifact_id and none.calls == 0
    cost = json.loads((settings.data_root / "experiments/sql/runs/revalidation/costs" / f"{artifact.artifact_id}.json").read_text())
    assert cost["new_cost_usd"] == 0
