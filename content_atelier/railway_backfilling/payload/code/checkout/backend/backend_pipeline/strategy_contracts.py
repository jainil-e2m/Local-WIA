"""Founder-feedback discovery contracts; legacy contracts remain readable."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import Contract, Text, Texts, Score, MomentDraft, CompactMomentDraft, MeetingCoverage

STRATEGY_VERSION = "2026-10-13.wia-strategic-discovery.v1"
Purpose = Literal["ATTRACT", "WARM", "CONVERT"]
Lens = Literal["audience_insight", "wia_expertise", "service_value", "broader_principle"]
ContentType = Literal[
    "opinion", "founder_forward", "campaign_breakdown", "trend", "uvp", "thought_shift",
    "process", "behind_the_scenes", "education", "founder_story", "solution_selling", "social_proof",
]


class Discovery(Contract):
    lenses: Annotated[list[Lens], Field(min_length=1)]
    destination: Literal["public_opportunity", "internal_intelligence", "research_needed"]
    wia_contribution: Text | None
    attention_reason: Text
    research_questions: list[Text]

    @model_validator(mode="after")
    def research_has_a_question(self):
        if len(self.lenses) != len(set(self.lenses)):
            raise ValueError("Discovery lenses must be unique")
        if self.destination == "research_needed" and not self.research_questions:
            raise ValueError("A research-needed moment requires a specific research question")
        return self


class StrategicMomentDraft(MomentDraft):
    discovery: Discovery


class StrategicMomentResponse(Contract):
    moments: list[StrategicMomentDraft]
    processed_span_ids: list[Text]
    coverage_notes: list[Text]


class StrategicCompactMomentDraft(CompactMomentDraft):
    discovery: Discovery


class StrategicCompactMomentResponse(Contract):
    moments: list[StrategicCompactMomentDraft]
    processed_meetings: list[MeetingCoverage]
    coverage_notes: list[Text]


class StrategicQuality(Contract):
    grounding: Score
    strategic_fit: Score
    distinctiveness: Score
    audience_resonance: Score
    source_strength: Score
    reasons: Texts


class StrategicAngleDraft(Contract):
    local_key: Text
    title: Text
    content_opportunity: Text
    strategic_purpose: Purpose
    content_type: ContentType
    strategic_rationale: Text
    audience: Text
    core_perspective: Text
    tension: Text
    wia_expertise_in_action: Text | None
    service_relevance: Text | None
    reader_decision: Text | None
    evidence_readiness: Literal["supported", "research_required"]
    research_questions: list[Text]
    selection_reason: Text
    moment_ids: Texts
    source_assertions: Texts
    inference: Text | None
    qualifiers: list[Text]
    risks: list[Text]
    quality: StrategicQuality

    @model_validator(mode="after")
    def research_is_explicit(self):
        if self.evidence_readiness == "research_required" and not self.research_questions:
            raise ValueError("A research-required opportunity needs a specific research question")
        return self


class InternalInsight(Contract):
    moment_ids: Texts
    insight: Text
    strategic_use: Text
    research_questions: list[Text]


class StrategicAngleResponse(Contract):
    angles: list[StrategicAngleDraft]
    internal_insights: list[InternalInsight]
    processed_moment_ids: list[Text]
    coverage_notes: list[Text]


class StrategicRefinementOutcome(Contract):
    original_id: Text
    outcome: Literal["replacement", "no_supported_alternative"]
    replacement: StrategicAngleDraft | None
    explanation: Text


class StrategicRefinementResponse(Contract):
    outcomes: list[StrategicRefinementOutcome]
    processed_moment_ids: list[Text]
    coverage_notes: list[Text]


def is_strategic_angle_response(output: dict) -> bool:
    return "internal_insights" in output or any("core_perspective" in a for a in output.get("angles", []))


def is_strategic_moment_response(output: dict) -> bool:
    return any("discovery" in m for m in output.get("moments", []))
