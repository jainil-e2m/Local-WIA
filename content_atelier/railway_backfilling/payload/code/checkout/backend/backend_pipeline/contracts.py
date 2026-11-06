"""Versioned LLM response contracts shared by the prompt, provider and validator."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Texts = Annotated[list[Text], Field(min_length=1)]
Score = Annotated[float, Field(ge=0, le=5, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=False)


class MomentDraft(Contract):
    local_key: Text
    anchor_span_ids: Texts
    context_span_ids: Texts
    quote: Text
    context_summary: Text
    moment_type: Literal["result", "objection", "decision", "tension", "mechanism", "observation", "story"]
    proposition: Text
    audience_relevance: Text
    qualifications: list[Text]
    claim_status: Literal["reported", "measured", "estimated", "planned", "hypothetical", "inferred"]
    sensitivity: Literal["public_candidate", "internal_only", "unknown"]
    strength: Score
    reasons: Texts


class MomentResponse(Contract):
    moments: list[MomentDraft]
    processed_span_ids: list[Text]
    coverage_notes: list[Text]


class MeetingCoverage(Contract):
    meeting_ref: Text
    first_span_id: Text
    last_span_id: Text
    span_count: Annotated[int, Field(gt=0)]


class CompactMomentDraft(Contract):
    local_key: Text
    anchor_span_ids: Texts
    context_first_span_id: Text
    context_last_span_id: Text
    quote: Text
    context_summary: Text
    moment_type: Literal["result", "objection", "decision", "tension", "mechanism", "observation", "story"]
    proposition: Text
    audience_relevance: Text
    qualifications: list[Text]
    claim_status: Literal["reported", "measured", "estimated", "planned", "hypothetical", "inferred"]
    sensitivity: Literal["public_candidate", "internal_only", "unknown"]
    strength: Score
    reasons: Texts


class CompactMomentResponse(Contract):
    moments: list[CompactMomentDraft]
    processed_meetings: list[MeetingCoverage]
    coverage_notes: list[Text]


class QualityDraft(Contract):
    grounding: Score
    source_relevance: Score
    audience_fit: Score
    specificity: Score
    editorial_usefulness: Score
    reasons: Texts


class AngleDraft(Contract):
    local_key: Text
    title: Text
    argument: Text
    audience: Text
    tension: Text
    take: Text
    mechanism: Text
    reader_decision: Text
    moment_ids: Texts
    source_assertions: Texts
    inference: Text | None
    qualifiers: list[Text]
    risks: list[Text]
    quality: QualityDraft


class AngleResponse(Contract):
    angles: list[AngleDraft]
    processed_moment_ids: list[Text]
    coverage_notes: list[Text]


class RefinementOutcome(Contract):
    original_id: Text
    outcome: Literal['replacement', 'no_supported_alternative']
    replacement: AngleDraft | None
    explanation: Text


class RefinementResponse(Contract):
    outcomes: list[RefinementOutcome]
    processed_moment_ids: list[Text]
    coverage_notes: list[Text]


def signature_from_fields(angle: dict) -> str:
    """One semantic embedding input; title/scores/recency must not decorate it."""
    if angle.get("strategy"):
        return signature_from_fields(angle["strategy"])
    if "core_perspective" in angle:
        # Purpose/type labels alone must not create distinct arguments.
        fields = [
            ("Opportunity", "content_opportunity"), ("Audience", "audience"),
            ("Tension", "tension"), ("Argument", "core_perspective"),
            ("WIA expertise", "wia_expertise_in_action"),
        ]
        return " | ".join(f"{label}: {' '.join((angle[field] or '').split())}" for label, field in fields)
    fields = [
        ("Audience", "audience"),
        ("Tension", "tension"),
        ("Argument", "argument"),
        ("Take", "take"),
        ("Mechanism", "mechanism"),
        ("Reader decision", "reader_decision"),
    ]
    return " | ".join(f"{label}: {' '.join(angle[field].split())}" for label, field in fields)
