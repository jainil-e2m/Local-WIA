"""Offline checks for the WIA strategist angle profile, lean card contract and knowledge base (E.B9, E.B11).

Synthetic fixtures only: no HTTP, no client documents, no paid model calls.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend_pipeline import config
from backend_pipeline import repository as repository_module
from backend_pipeline.angle_profiles import (
    LEGACY_PROFILE,
    REEL_LABEL,
    STRATEGIST_PROFILE,
    STRATEGIST_TEMPLATE,
    card_schema,
    strategist_angle_prompt,
    uses_cards,
)
from backend_pipeline.card_contracts import WeeklyAngleCards
from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.knowledge_base import HEADER, REQUIRED_DOCUMENTS, load_knowledge_base
from backend_pipeline.tests.plans import OpenTestPlan
from backend_pipeline.models import Moment
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.prompts import ANGLE_PROMPT_VERSION
from backend_pipeline.llm import LiveProvider
from backend_pipeline.repository import ContentRepository

SOL, LUNA = "openai/gpt-6.1-sol", "openai/gpt-6-luna"
SONNET = "anthropic/claude-sonnet-5.5"  # the documented brief review model, now also the code default (V12, 0.B8)
DOCS = {
    "content_strategy": ("01-strategy.md", "Document 1: Synthetic content strategy", "Pillars: ATTRACT, WARM, CONVERT."),
    "founder_voice_guide": ("02-voice.md", "Document 2: Synthetic voice guide", "Principles before tactics."),
    "accelerator_strategy": ("03-accelerator.md", "Document 3: Synthetic accelerator sections", "Ideal client: established."),
    "team_roster": ("04-roster.md", "Synthetic team", "- Team Member: strategist."),
    "offer_sheet": ("05-offers.md", "Synthetic offers", "- Offer A: waitlist only."),
}


def write_kb(root: Path, docs=DOCS, *, version="kb-test.v1") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for key, (file, heading, text) in docs.items():
        (root / file).write_text(text + "\n", encoding="utf-8")
        entries.append({"key": key, "file": file, "heading": heading, "version": "v1", "owner": "Synthetic owner",
                        "status": "unconfirmed" if key in {"team_roster", "offer_sheet"} else "supplied"})
    (root / "manifest.json").write_text(json.dumps({"knowledge_base_version": version, "documents": entries}), encoding="utf-8")
    return root


@pytest.fixture
def kb_dir(tmp_path):
    return write_kb(tmp_path / "kb")


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Settings.from_env() without opening the real backend or project .env files."""
    backend = tmp_path / "project" / "backend"
    backend.mkdir(parents=True)
    monkeypatch.setattr(config, "PROJECT_ROOT", backend.parent)
    monkeypatch.setattr(config, "BACKEND_ROOT", backend)
    for name in ("CONTENT_ATELIER_ANGLE_PROMPT_PROFILE", "CONTENT_ATELIER_KNOWLEDGE_BASE_DIR",
                 "OPENROUTER_ANGLE_GENERATION_MODEL", "OPENROUTER_MODEL"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def card(moment_id, rank=1, **changes):
    value = {
        "rank": rank, "title": f"How we read a planner's lead quality, idea {rank}", "pillar": "WARM",
        "content_type": "behind_the_scenes", "audience": "Established wedding planners",
        "core_perspective": f"Lead quality starts before the ad account, idea {rank}.",
        "why_it_matters": "Owners stop blaming the platform.", "wia_in_action": "The strategist asks about pricing copy.",
        "offer_connection": None, "moment_ids": [moment_id], "evidence_points": ["The strategist asks about pricing."],
        "verify_before_publishing": ["Confirm the client may be referenced."], "why_selected": "Shows WIA's process.",
    }
    value.update(changes)
    return value


def cards_output(moment_id, **changes):
    value = {
        "week_summary": "One planner call shows how WIA thinks about lead quality.",
        "angles": [card(moment_id, 2, pillar="ATTRACT", content_type="polarizing_opinion"), card(moment_id, 1)],
        "internal_insights": [{"moment_ids": [moment_id], "insight": "Pricing objection.", "use": "Sales enablement."}],
        "considered_not_selected": [{"moment_ids": [moment_id], "idea": "Negative keyword tips.", "reason": "Too narrow."}],
    }
    value.update(changes)
    return value


def moment(moment_id="moment_a", **changes):
    value = dict(moment_id=moment_id, source_ids=["zoom:week1/call"], anchor_span_ids=["s1"], context_span_ids=["s1", "s2"],
                 quote="quote", context_summary="EXTRACTOR SUMMARY", moment_type="observation",
                 proposition="EXTRACTOR PROPOSITION", audience_relevance="owners", qualifications=["Not a measured result"],
                 claim_status="reported", sensitivity="unknown", strength=4.0, reasons=["r"])
    value.update(changes)
    return Moment(**value)


# Knowledge base -------------------------------------------------------------------------------------------


def test_knowledge_base_records_file_hashes_and_assembles_whole_documents(kb_dir):
    kb = load_knowledge_base(kb_dir)
    refs = kb.refs()
    assert refs["version"] == "kb-test.v1"
    assert refs["manifest_sha256"] == hashlib.sha256((kb_dir / "manifest.json").read_bytes()).hexdigest()
    assert [d["key"] for d in refs["documents"]] == list(REQUIRED_DOCUMENTS)
    for d in refs["documents"]:
        assert d["sha256"] == hashlib.sha256((kb_dir / d["file"]).read_bytes()).hexdigest()
    assert refs["sha256"] == hashlib.sha256(kb.text.encode()).hexdigest()
    assert kb.text.startswith(HEADER)
    positions = [kb.text.index(f"## {heading}\n{text}") for _file, heading, text in DOCS.values()]
    assert positions == sorted(positions)
    # Identity only: no document text in the refs that go into run input refs.
    assert not any(text in json.dumps(refs) for _f, _h, text in DOCS.values())


def test_changing_one_document_changes_only_its_hash_and_the_prefix(kb_dir):
    before = load_knowledge_base(kb_dir).refs()
    (kb_dir / "05-offers.md").write_text("- Offer A: open.\n", encoding="utf-8")
    after = load_knowledge_base(kb_dir).refs()
    changed = [b["key"] for b, a in zip(before["documents"], after["documents"]) if b["sha256"] != a["sha256"]]
    assert changed == ["offer_sheet"] and before["sha256"] != after["sha256"]


def test_line_endings_do_not_change_the_prompt_prefix(kb_dir):
    before = load_knowledge_base(kb_dir)
    (kb_dir / "02-voice.md").write_bytes(b"\xef\xbb\xbfPrinciples before tactics.\r\n")
    after = load_knowledge_base(kb_dir)
    assert after.text == before.text and after.sha256 == before.sha256
    assert after.refs()["documents"][1]["sha256"] != before.refs()["documents"][1]["sha256"]


@pytest.mark.parametrize("problem", ["missing_manifest", "missing_required", "duplicate_key", "empty", "missing_file",
                                     "outside_folder", "bad_status"])
def test_knowledge_base_rejects_incomplete_folders(kb_dir, problem):
    manifest = json.loads((kb_dir / "manifest.json").read_text(encoding="utf-8"))
    if problem == "missing_manifest":
        (kb_dir / "manifest.json").unlink()
    elif problem == "missing_required":
        manifest["documents"] = [d for d in manifest["documents"] if d["key"] != "team_roster"]
    elif problem == "duplicate_key":
        manifest["documents"].append(dict(manifest["documents"][0]))
    elif problem == "empty":
        (kb_dir / "01-strategy.md").write_text(" \n", encoding="utf-8")
    elif problem == "missing_file":
        (kb_dir / "03-accelerator.md").unlink()
    elif problem == "outside_folder":
        (kb_dir.parent / "outside.md").write_text("text", encoding="utf-8")
        manifest["documents"][0]["file"] = "../outside.md"
    elif problem == "bad_status":
        manifest["documents"][0]["status"] = "final"
    if problem != "missing_manifest":
        (kb_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises((ValueError, FileNotFoundError)):
        load_knowledge_base(kb_dir)


def test_committed_example_folder_is_complete_but_placeholder_only():
    example = BACKEND_ROOT / "knowledge_base.example"
    with pytest.raises(ValueError, match="placeholder"):
        load_knowledge_base(example)
    kb = load_knowledge_base(example, allow_placeholders=True)
    assert [d.entry.key for d in kb.documents] == list(REQUIRED_DOCUMENTS)
    assert {d.entry.key: d.entry.status for d in kb.documents}["offer_sheet"] == "unconfirmed"


def test_committed_knowledge_base_is_complete_and_real():
    folder = BACKEND_ROOT / "knowledge_base"
    # Committed by the owner's decision (R48); a missing folder is a failure, never a silent skip (S.B6).
    assert (folder / "manifest.json").is_file(), "backend/knowledge_base/ is committed; restore it or update this path"
    kb = load_knowledge_base(folder)
    keys = [d.entry.key for d in kb.documents]
    assert keys[:len(REQUIRED_DOCUMENTS)] == list(REQUIRED_DOCUMENTS)
    status = {d.entry.key: d.entry.status for d in kb.documents}
    # Version 9 (E.B25 (i), (j), L.B12, 22 October; version 8 with Whitney's spoken voice and transformations, document 05's
    # descriptors and glossary, document 09's first-touch rules, document 13 at piece level): compiled from the store built from committed inputs, Week 6 withheld; every
    # document is confirmed except the three WIA supplied as written, and no draft remains.
    assert kb.version == "wia-kb-2026-10-22.c-a1a75795" and kb.format == 2
    # The hashes every environment records for this version (E.B11): the store's export produced these bytes, and CI
    # recomputes them on another machine from the committed files (LF everywhere, .gitattributes).
    assert kb.sha256 == "0aa167df0adbd19c60725d3b10326f5ca899ecfbf3860d52024f881fb7349d64"
    assert {k for k, v in status.items() if v != "confirmed"} == {"content_strategy", "founder_voice_guide", "accelerator_strategy"}
    assert {status[k] for k in ("content_strategy", "founder_voice_guide", "accelerator_strategy")} == {"supplied"}
    # No document derives from the held-out benchmark weeks (E.B17).
    assert not any({5, 6} & set(d.entry.provenance.derived_from_weeks) for d in kb.documents)
    # Every document shows its status and effective date in the prefix (E.B11 c).
    assert all(f"Status: {d.entry.status}; effective {d.entry.effective_date.isoformat()}" in kb.text for d in kb.documents)
    assert "authoritative for strategy, positioning and voice;" not in kb.text.split("\n", 1)[0]


def test_the_archived_v1_knowledge_base_still_loads_for_replay():
    archived = load_knowledge_base(BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.v1")
    assert archived.version == "wia-kb-2026-10-18.v1" and archived.format == 1
    v2 = load_knowledge_base(BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.v2")
    assert v2.version == "wia-kb-2026-10-18.v2" and v2.format == 2 and len(v2.documents) == 16
    assert [d.entry.key for d in archived.documents] == list(REQUIRED_DOCUMENTS)
    assert archived.text.startswith(HEADER)


def test_stages_load_only_their_documents():
    folder = BACKEND_ROOT / "knowledge_base"
    strategist = {d.entry.key for d in load_knowledge_base(folder, stage="strategist").documents}
    brief = {d.entry.key for d in load_knowledge_base(folder, stage="brief").documents}
    assert "format_guide" in brief and "format_guide" not in strategist
    assert "recent_published" in strategist and "recent_published" not in brief
    assert {d.entry.key for d in load_knowledge_base(folder, stage="verifier").documents} >= {"team_roster", "rejection_rules"}


# Profile selection and models ------------------------------------------------------------------------------


def test_default_profile_and_models_are_unchanged():
    settings = Settings()
    assert settings.angle_prompt_profile == LEGACY_PROFILE == ANGLE_PROMPT_VERSION
    assert not uses_cards(settings.angle_prompt_profile)
    assert settings.openrouter_angle_generation_model is None
    assert {stage: settings.model_for(stage) for stage in ("moment_extraction", "angle_generation", "angle_refinement",
            "brief_plan")} == {"moment_extraction": LUNA, "angle_generation": LUNA, "angle_refinement": LUNA, "brief_plan": SONNET}
    # The brief stages carry their documented models in code (V12): a fresh deployment writes with Sol.
    assert settings.model_for("brief_write") == SOL and settings.model_for("brief_review") == SONNET


def test_profile_knowledge_base_and_stage_model_are_selected_by_settings(isolated_env, tmp_path):
    monkeypatch = isolated_env
    monkeypatch.setenv("CONTENT_ATELIER_ANGLE_PROMPT_PROFILE", STRATEGIST_PROFILE)
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(tmp_path / "kb"))
    monkeypatch.setenv("OPENROUTER_ANGLE_GENERATION_MODEL", SOL)
    monkeypatch.setenv("OPENROUTER_MOMENTS_MODEL", LUNA)
    monkeypatch.setenv("OPENROUTER_ANGLES_MODEL", LUNA)
    settings = Settings.from_env()
    assert uses_cards(settings.angle_prompt_profile) and settings.knowledge_base_root == tmp_path / "kb"
    assert settings.model_for("angle_generation") == SOL
    # Extraction keeps its model; refinement, which inherits the angles model, is untouched, and a brief stage keeps its own.
    assert settings.model_for("moment_extraction") == settings.model_for("angle_refinement") == LUNA
    assert settings.model_for("brief_review") == SONNET


def test_unknown_profile_is_rejected(isolated_env):
    monkeypatch = isolated_env
    monkeypatch.setenv("CONTENT_ATELIER_ANGLE_PROMPT_PROFILE", "2026-10-18.made-up.v9")
    from backend_pipeline.settings_store import SettingError
    with pytest.raises(SettingError, match="CONTENT_ATELIER_ANGLE_PROMPT_PROFILE"):
        Settings.from_env()
    with pytest.raises(ValidationError):
        Settings(angle_prompt_profile="2026-10-18.made-up.v9")
    with pytest.raises(ValueError):
        uses_cards("2026-10-18.made-up.v9")


def test_live_provider_sends_the_stage_model_without_network(monkeypatch):
    sent = []

    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]}

        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, headers, json):
            sent.append(json["model"])
            return Response()

    monkeypatch.setattr("httpx.Client", Client)
    provider = LiveProvider(llm_base_url="https://example.invalid", moments_model=LUNA, moments_key="synthetic",
                            angles_model=LUNA, angles_key="synthetic", embedding_base_url="https://example.invalid",
                            embedding_model="e", embedding_key=None, dimensions=3, timeout=1,
                            stage_models={"angle_generation": SOL}, plan=OpenTestPlan())
    for stage in ("moment_extraction", "angle_generation", "angle_refinement"):
        provider.json_call(stage=stage, system="s", user="u", schema={"type": "object"}, fingerprint="f")
    assert sent == [LUNA, SOL, LUNA]


# Prompt assembly -------------------------------------------------------------------------------------------


def packet():
    return [{"moment_id": "moment_a", "source_ids": ["zoom:week1/call"], "context_summary": "EXTRACTOR SUMMARY",
             "proposition": "EXTRACTOR PROPOSITION",
             "source_metadata": {"zoom:week1/call": {"filename_label": "Planner strategy call", "date": "2026-10-06"}},
             "source_evidence": [
                 {"span_id": "s1", "speaker": "Team Member", "start_seconds": 4.0, "text": "How does your landing page describe pricing?"},
                 {"span_id": "s2", "speaker": None, "start_seconds": 3725.5, "text": "We never mention it."},
             ]}]


def test_strategist_prompt_puts_trusted_knowledge_in_system_and_scenes_in_user(kb_dir):
    kb = load_knowledge_base(kb_dir)
    system, user = strategist_angle_prompt(packet(), kb)
    template = STRATEGIST_TEMPLATE.read_text(encoding="utf-8").strip()
    assert system == template + "\n\n" + kb.text
    assert template.startswith("You are the content strategist for Wedding Industry Ads (WIA)")
    assert template.endswith("Return only JSON matching the supplied schema.")
    assert "How does your landing page" not in system
    assert "## Moment moment_a (recording: Planner strategy call, 2026-10-06)" in user
    assert "[00:04] Team Member: How does your landing page describe pricing?" in user
    assert "[1:02:05] Unknown speaker: We never mention it." in user
    # The extractor's interpretation is left out; the angle stage reads the scene.
    assert "EXTRACTOR" not in user
    assert REEL_LABEL in user and user.index(REEL_LABEL) > user.index("We never mention it.")
    assert not any(text in user for _f, _h, text in DOCS.values())


def test_system_prefix_is_stable_across_weeks(kb_dir):
    kb = load_knowledge_base(kb_dir)
    other = copy.deepcopy(packet())
    other[0]["moment_id"] = "moment_b"
    assert strategist_angle_prompt(packet(), kb)[0] == strategist_angle_prompt(other, kb)[0]


def test_template_matches_appendix_a_when_the_analysis_is_present():
    analysis = BACKEND_ROOT / "docs" / "Content-Atelier-Content-Quality-Analysis.md"
    # Committed; a moved analysis must fail here instead of skipping silently (S.B6).
    assert analysis.is_file(), "Content-Atelier-Content-Quality-Analysis.md moved; update this test's path"
    appendix = analysis.read_text(encoding="utf-8").split("## Appendix A.", 1)[1].split("## Appendix B.", 1)[0]
    block = re.search(r"````text\n(.*?)\n````", appendix.replace("\r\n", "\n"), re.DOTALL)[1]
    assert STRATEGIST_TEMPLATE.read_text(encoding="utf-8").strip() == block.strip()


# Contract --------------------------------------------------------------------------------------------------


def test_card_contract_matches_the_lean_card_fields():
    schema = card_schema()
    assert schema["title"] == "WeeklyAngleCards"
    assert schema["required"] == ["week_summary", "angles", "internal_insights", "considered_not_selected"]
    assert schema["$defs"]["AngleCard"]["required"] == [
        "rank", "title", "pillar", "content_type", "audience", "core_perspective", "why_it_matters", "wia_in_action",
        "offer_connection", "moment_ids", "evidence_points", "verify_before_publishing", "why_selected"]
    for definition in schema["$defs"].values():
        assert definition["additionalProperties"] is False
    assert not {"quality", "source_assertions", "qualifiers", "risks"} & set(schema["$defs"]["AngleCard"]["properties"])
    WeeklyAngleCards.model_validate(cards_output("moment_a"))


@pytest.mark.parametrize("change", [
    {"rank": 3}, {"pillar": "NURTURE"}, {"content_type": "opinion"}, {"evidence_points": []}, {"moment_ids": []},
    {"verify_before_publishing": ["a", "b", "c"]}, {"title": " "}, {"rank": 1.0}, {"quality": {}},
])
def test_card_contract_rejects_invalid_cards(change):
    output = cards_output("moment_a")
    output["angles"][0].update(change)
    with pytest.raises(ValidationError):
        WeeklyAngleCards.model_validate(output)


def test_card_contract_rejects_duplicate_ranks_and_missing_week_fields():
    with pytest.raises(ValidationError):
        WeeklyAngleCards.model_validate(cards_output("moment_a", angles=[card("moment_a", 1), card("moment_a", 1)]))
    for key in ("week_summary", "considered_not_selected"):
        output = cards_output("moment_a")
        output.pop(key)
        with pytest.raises(ValidationError):
            WeeklyAngleCards.model_validate(output)
    WeeklyAngleCards.model_validate(cards_output("moment_a", angles=[], internal_insights=[], considered_not_selected=[]))


# Parsing and persistence -----------------------------------------------------------------------------------


def parser():
    return object.__new__(Pipeline)


def test_cards_parse_into_ranked_angles_without_self_scores():
    moments = [moment("moment_a", sensitivity="internal_only"), moment("moment_b")]
    angles = parser()._parse_angles(cards_output("moment_a"), "run_x", moments)
    assert [a.card.rank for a in angles] == [1, 2]
    first = angles[0]
    assert first.quality is None and first.base_score is None and first.strategy is None
    assert first.title == first.card.title and first.argument == first.card.core_perspective
    assert first.mechanism == first.card.wia_in_action and first.source_assertions == []
    # Verify-before-publishing stays on the card, not duplicated into the Angle's qualifiers.
    assert first.qualifiers == ["Not a measured result"]
    assert first.risks == ["handling: internal_only; public reuse needs review"]
    assert first.source_family_id.startswith("source_family_")
    assert len({a.angle_id for a in angles}) == 2 and len({a.signature for a in angles}) == 2
    selection = Pipeline.card_selection(cards_output("moment_a"), angles, moments)
    assert selection["ranked_angle_ids"] == [a.angle_id for a in angles]
    assert selection["unreferenced_moment_ids"] == ["moment_b"]


@pytest.mark.parametrize("where", ["angle_unknown", "angle_duplicate", "insight_unknown", "considered_unknown"])
def test_cards_keep_moment_id_validation(where):
    output = cards_output("moment_a")
    if where == "angle_unknown":
        output["angles"][0]["moment_ids"] = ["moment_zzz"]
    elif where == "angle_duplicate":
        output["angles"][0]["moment_ids"] = ["moment_a", "moment_a"]
    elif where == "insight_unknown":
        output["internal_insights"][0]["moment_ids"] = ["moment_zzz"]
    else:
        output["considered_not_selected"][0]["moment_ids"] = ["moment_zzz"]
    with pytest.raises(ValueError, match="moments"):
        parser()._parse_angles(output, "run_x", [moment()])


def test_duplicate_card_arguments_are_rejected():
    output = cards_output("moment_a", angles=[card("moment_a", 1), card("moment_a", 2, title="Different title",
                                                                           core_perspective=card("moment_a", 1)["core_perspective"])])
    with pytest.raises(ValueError, match="Duplicate"):
        parser()._parse_angles(output, "run_x", [moment()])


def test_sql_persistence_stores_the_card_and_no_self_score(monkeypatch):
    angles = parser()._parse_angles(cards_output("moment_a"), "run_x", [moment()])
    rows = []

    class Conn:
        def execute(self, *args):
            class Result(list):
                def fetchone(self):
                    return None
            return Result()

    monkeypatch.setattr(repository_module, "insert", lambda conn, table, record, conflict=False: rows.append((table, record)))
    ContentRepository.save_angles(None, Conn(), "week_x", angles)
    saved = [record for table, record in rows if table == "content_angles"]
    assert len(saved) == 2
    assert saved[0]["content_body"]["card"] == angles[0].card.model_dump(mode="json")
    assert saved[0]["content_body"]["source_family_id"] == angles[0].source_family_id
    assert "strategy" not in saved[0]["content_body"]
    assert saved[0]["quality_scores"] is None and saved[0]["base_score"] is None
    assert [record["moment_id"] for table, record in rows if table == "angle_moments"] == ["moment_a", "moment_a"]


# End-to-end offline run ------------------------------------------------------------------------------------


class CardProvider:
    """Synthetic responses only; no HTTP, private inputs or billing."""

    def __init__(self):
        self.calls = Counter()
        self.seen = {}

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls[stage] += 1
        self.seen[stage] = (system, user, schema)
        if stage == "moment_extraction":
            refs = re.findall(r"^(m\d+\.t\d+)\|", user, re.MULTILINE)
            output = {
                "moments": [{
                    "local_key": "m1", "anchor_span_ids": [refs[0]], "context_first_span_id": refs[0],
                    "context_last_span_id": refs[-1], "quote": "How does your landing page describe pricing?",
                    "context_summary": "Pricing copy and lead quality.", "moment_type": "observation",
                    "proposition": "Pricing copy filters leads.", "audience_relevance": "Wedding planners",
                    "qualifications": ["Not a measured result"], "claim_status": "reported", "sensitivity": "unknown",
                    "strength": 4.0, "reasons": ["Concrete process"],
                    "discovery": {"lenses": ["wia_expertise"], "destination": "public_opportunity", "wia_contribution": None,
                                  "attention_reason": "Shows a diagnostic question.", "research_questions": []},
                }],
                "processed_meetings": [{"meeting_ref": "m1", "first_span_id": refs[0], "last_span_id": refs[-1],
                                        "span_count": len(refs)}],
                "coverage_notes": [],
            }
        else:
            moment_ids = re.findall(r"^## Moment (\S+) \(recording", user, re.MULTILINE)
            output = cards_output(moment_ids[0])
        return output, {"fake": True, "raw": {"id": "synthetic-only", "usage": {"cost": 0},
                        "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]}}

    def embed(self, *, text, fingerprint):
        raise AssertionError("Embedding provider must remain disconnected")


@pytest.fixture
def week(tmp_path):
    folder = tmp_path / "inputs" / "week1"
    folder.mkdir(parents=True)
    (folder / "meeting.vtt").write_bytes(
        b"WEBVTT\r\n\r\n1\r\n00:00:00.000 --> 00:00:05.000\r\n"
        b"Team Member: How does your landing page describe pricing?\r\n\r\n"
        b"2\r\n00:00:04.000 --> 00:00:09.500\r\nPlanner: We never mention it.\r\n\r\n"
    )
    return tmp_path


def strategist_settings(root, kb_dir, **changes):
    values = dict(data_root=root / "data", transcript_root=root / "inputs", llm_payload_format="compact_weekly",
                  embedding_dimensions=3, angle_prompt_profile=STRATEGIST_PROFILE, knowledge_base_root=kb_dir,
                  openrouter_angle_generation_model=SOL)
    values.update(changes)
    return Settings(**values)


def test_offline_strategist_run_records_profile_model_and_knowledge_base(week, kb_dir):
    provider = CardProvider()
    pipeline = Pipeline(strategist_settings(week, kb_dir), provider)
    result = pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}
    assert result["angles"] == 2 and result["angle_prompt_profile"] == STRATEGIST_PROFILE
    run_dir = f"experiments/default/runs/{result['run_id']}"
    store = pipeline.store
    kb = load_knowledge_base(kb_dir)
    manifest = store.read_json(f"{run_dir}/manifest.json")
    assert manifest["model_id"] == SOL
    assert manifest["input_refs"] == {"angle_prompt_profile": STRATEGIST_PROFILE, "angle_model": SOL,
                                      "knowledge_base": kb.refs()}
    requests = {json.loads(p.read_text(encoding="utf-8"))["stage"]: json.loads(p.read_text(encoding="utf-8"))["request"]
                for p in pipeline.settings.data_root.glob("service_calls/*/attempts/*/request.json")}
    assert requests["moment_extraction"]["model"] == LUNA and requests["angle_generation"]["model"] == SOL
    assert requests["angle_generation"]["messages"][0]["content"].endswith(kb.text)
    assert store.read_json(f"{run_dir}/angle_generation.json")["prompt_version"] == STRATEGIST_PROFILE
    cards = store.read_json(f"{run_dir}/angle_cards.json")
    assert [c["rank"] for c in cards] == [1, 2] and all(c["angle_id"].startswith("angle_") for c in cards)
    selection = store.read_json(f"{run_dir}/angle_selection.json")
    assert selection["week_summary"].startswith("One planner call")
    assert selection["ranked_angle_ids"] == [c["angle_id"] for c in cards]
    assert selection["considered_not_selected"][0]["reason"] == "Too narrow."
    review = store.read_json(f"{run_dir}/review.json")
    assert review["angle_prompt_profile"] == STRATEGIST_PROFILE and review["similarity_status"] == "not_run"
    # Identical rerun reuses both saved responses.
    pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}


def test_changed_knowledge_base_is_a_new_angle_request(week, kb_dir):
    provider = CardProvider()
    Pipeline(strategist_settings(week, kb_dir), provider).run(1)
    (kb_dir / "05-offers.md").write_text("- Offer A: open.\n", encoding="utf-8")
    Pipeline(strategist_settings(week, kb_dir), provider).run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 2}


def test_default_fake_provider_handles_the_card_contract(week):
    example = BACKEND_ROOT / "knowledge_base.example"
    result = Pipeline(strategist_settings(week, example)).run(1)
    assert result["angles"] == 0 and result["angle_prompt_profile"] == STRATEGIST_PROFILE


def test_live_run_refuses_a_placeholder_knowledge_base_before_any_call(week):
    provider = CardProvider()
    # Version 5: versions 3 and 4 are refused for live runs before the knowledge base is read (E.B17).
    settings = strategist_settings(week, BACKEND_ROOT / "knowledge_base.example", live_enabled=True,
                                   openrouter_moments_key="synthetic-only", openrouter_angles_key="synthetic-only",
                                   angle_prompt_profile="2026-10-18.wia-strategist.v5")
    with pytest.raises(ValueError, match="placeholder"):
        Pipeline(settings, provider).run(1, mode="live")
    assert provider.calls == Counter()


def test_strategist_profile_refuses_similarity_ranking(week, kb_dir):
    provider = CardProvider()
    with pytest.raises(ValueError, match="generation-only"):
        Pipeline(strategist_settings(week, kb_dir, embeddings_enabled=True), provider).run(1)
    assert provider.calls == Counter()


def test_legacy_profile_never_reads_the_knowledge_base(week, tmp_path):
    settings = Settings(data_root=week / "data", transcript_root=week / "inputs", llm_payload_format="compact_weekly",
                        embedding_dimensions=3, knowledge_base_root=tmp_path / "does-not-exist")
    pipeline = Pipeline(settings)
    result = pipeline.run(1)
    run_dir = f"experiments/default/runs/{result['run_id']}"
    assert pipeline.store.read_json(f"{run_dir}/manifest.json")["input_refs"] is None
    assert pipeline.store.read_json(f"{run_dir}/angle_generation.json")["prompt_version"] == ANGLE_PROMPT_VERSION
    assert "angle_prompt_profile" not in result


# SQL worker card path (fake repository; the PostgreSQL suite needs an isolated atelier_test database) --------


class FakeRepo:
    def __init__(self, refs):
        self.refs, self.saved, self.finished, self.ledgers = refs, None, None, {}

    def connection(self):
        repo = self

        class Rows(list):
            def fetchone(self):
                return self[0] if self else None

        class Conn:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def execute(self, statement, params=()):
                if statement.startswith("SELECT input_refs"):
                    return Rows([{"input_refs": copy.deepcopy(repo.refs)}])
                if statement.startswith("UPDATE pipeline_runs"):
                    repo.refs = params[0].obj
                    return Rows()
                if statement.startswith("UPDATE content_angles SET content_body=content_body||"):
                    repo.ledgers[params[1]] = params[0].obj  # E.B10: the evidence ledger on its card
                    return Rows()
                if statement.startswith("SELECT to_regclass('public.brand_kit_items')"):
                    return Rows([{"t": None}])  # no context store: no content-plan warning (L.B10)
                if statement.startswith("SELECT stage,status,result_refs FROM pipeline_jobs"):
                    return Rows()  # the run's scene coverage (3.B3): no extraction job in this fake
                raise AssertionError(statement)

        return Conn()

    def guard(self, conn, job):
        return job

    def save_angles(self, conn, week_id, angles):
        self.saved = angles

    def finish(self, conn, job, result, **kwargs):
        self.finished = result


def sql_inputs(tmp_path, kb_dir):
    from backend_pipeline.models import RunManifest, Span, Transcript
    from backend_pipeline.sql_pipeline import SQLWorker

    spans = [Span(span_id="s1", source_id="zoom:w1/call", ordinal=0, start_seconds=0.0, end_seconds=4.0,
                  speaker="Team Member", text="How does your landing page describe pricing?"),
             Span(span_id="s2", source_id="zoom:w1/call", ordinal=1, start_seconds=4.0, end_seconds=9.0,
                  speaker="Planner", text="We never mention it.")]
    transcripts = [Transcript(source_id="zoom:w1/call", week_index=1, path="call", content_hash="h", spans=spans,
                              source_format="webvtt")]
    settings = strategist_settings(tmp_path, kb_dir)
    worker = object.__new__(SQLWorker)
    worker.models = settings
    worker.repo = FakeRepo({"transcripts": [], "mode": "synthetic"})
    pipeline = Pipeline(settings, CardProvider())
    pipeline.store = type(pipeline.store)(tmp_path / "artifacts")
    run = {"run_id": "run_sql", "week_id": "week_x", "input_refs": {}}
    manifest = RunManifest(run_id="run_sql", week_index=1, source_root="sql", source_ids=["zoom:w1/call"],
                           prompt_profile="p", model_id=settings.model_for("angle_generation"), embedding_profile="e",
                           mode="fake", execution_scope="generation_only")
    return worker, pipeline, run, manifest, [moment("moment_a", source_ids=["zoom:w1/call"])], transcripts


def test_sql_card_stage_freezes_the_angle_contract_and_saves_the_selection(tmp_path, kb_dir):
    worker, p, run, manifest, moments, transcripts = sql_inputs(tmp_path, kb_dir)
    job = {"job_id": "job_1", "run_id": "run_sql"}
    worker.cards(job, run, p, manifest, "experiments/sql/runs/run_sql", moments, transcripts, ["moment_a"])
    frozen = worker.repo.refs["angle_contract"]
    assert frozen == {"angle_prompt_profile": STRATEGIST_PROFILE, "angle_model": SOL,
                      "knowledge_base": load_knowledge_base(kb_dir).refs()}
    result = worker.repo.finished
    assert result["angle_prompt_profile"] == STRATEGIST_PROFILE and result["angle_model"] == SOL
    assert result["knowledge_base_sha256"] == frozen["knowledge_base"]["sha256"]
    assert result["week_summary"] and result["ranked_angle_ids"] == [a.angle_id for a in worker.repo.saved]
    assert [a.card.rank for a in worker.repo.saved] == [1, 2]
    # E.B10: each card carries its deterministic ledger; no model pass without a verification model.
    assert set(worker.repo.ledgers) == {a.angle_id for a in worker.repo.saved}
    assert result["verification"]["cards"] == 2 and result["verification"]["model_pass"] == ["not_run"]
    assert all(ledger["ledger_hash"] and ledger["readiness"] in {"ready", "needs_check", "research_required"}
               for ledger in worker.repo.ledgers.values())
    # A retry after the documents change refuses to mix knowledge-base versions.
    (kb_dir / "05-offers.md").write_text("- Offer A: open.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen angle profile"):
        worker.cards(job, run, p, manifest, "experiments/sql/runs/run_sql", moments, transcripts, ["moment_a"])


def test_format_two_hashes_are_the_same_on_crlf_and_lf_checkouts(tmp_path):
    """Two environments record the same hashes for a version (E.B11 e), whatever git did to line endings."""
    import shutil
    lf = tmp_path / "lf"
    shutil.copytree(BACKEND_ROOT / "knowledge_base", lf, ignore=shutil.ignore_patterns("archive"))
    crlf = tmp_path / "crlf"
    shutil.copytree(lf, crlf)
    for path in crlf.iterdir():
        if path.is_file():
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    for path in lf.iterdir():
        if path.is_file():
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    assert load_knowledge_base(crlf).refs() == load_knowledge_base(lf).refs()
