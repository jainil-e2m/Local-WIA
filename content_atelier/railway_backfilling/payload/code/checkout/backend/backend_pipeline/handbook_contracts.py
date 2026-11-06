"""Isolated handbook prompt-test contracts; existing production contracts are unchanged."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import Contract, Text, Texts

VERSION = "2026-10-13.wia-handbook.v2-test"
Lens = Literal["wia_expertise", "process_collaboration", "offer_value", "audience_insight", "proof_transformation"]
ClaimState = Literal["spoken_view", "proposed_action", "reported_action", "reported_result",
                     "expressed_understanding", "brand_perspective", "editorial_inference"]


class Region(Contract):
    first_ref: Text
    last_ref: Text


class Claim(Contract):
    claim: Text
    state: ClaimState
    source_refs: list[Text]
    knowledge_refs: list[Text]


class Contribution(Contract):
    speaker_label: Text
    contribution: Text
    source_refs: Texts


class RetrievalNeed(Contract):
    question: Text
    known_refs: list[Text]
    needed_segment_or_record: Text
    resolution_condition: Text


class Recording(Contract):
    meeting_ref: Text
    source_id: Text
    first_ref: Text
    last_ref: Text
    turn_count: Annotated[int, Field(gt=0)]
    reviewed_extent: Literal["all_supplied", "partial_supplied", "not_assessed"]
    context: Text
    speaker_ambiguities: list[Text]
    coverage_limitations: list[Text]


class HandbookMoment(Contract):
    local_key: Text
    meeting_ref: Text
    anchor_refs: Texts
    context_regions: Annotated[list[Region], Field(min_length=1)]
    situation: Text
    source_proposition: Text
    assertions: Annotated[list[Claim], Field(min_length=1)]
    contributions: list[Contribution]
    lenses: Annotated[list[Lens], Field(min_length=1)]
    strategic_significance: Text
    audience_relevance: Text
    possible_uses: Annotated[list[Literal["public_candidate", "internal_intelligence", "evidence_needed"]], Field(min_length=1)]
    retrieval_needs: list[RetrievalNeed]
    claim_boundaries: list[Text]
    shortlist_reason: Text

    @model_validator(mode="after")
    def unique_labels(self):
        for values in (self.anchor_refs, self.lenses, self.possible_uses):
            if len(values) != len(set(values)):
                raise ValueError("Moment references and labels must be unique")
        if "evidence_needed" in self.possible_uses and not self.retrieval_needs:
            raise ValueError("Evidence-needed use requires a precise retrieval need")
        return self


class SkippedMaterial(Contract):
    meeting_ref: Text
    source_refs: list[Text]
    reason: Text


class HandbookMomentResponse(Contract):
    recordings: list[Recording]
    moments: list[HandbookMoment]
    skipped_material: list[SkippedMaterial]
    input_limitations: list[Text]


class Judgment(Contract):
    value: Annotated[int, Field(ge=1, le=5)]
    reason: Text


class Judgments(Contract):
    audience_relevance: Judgment
    strategic_value_brand_fit: Judgment
    distinctiveness: Judgment
    appropriate_depth: Judgment
    voice_framing: Judgment
    source_support: Judgment


class Alternative(Contract):
    candidate_key: Text | None
    central_point: Text | None
    comparison_reason: Text


class SelectedAngle(Contract):
    local_key: Text
    rank: Annotated[int, Field(gt=0)]
    disposition: Literal["SELECT"]
    title: Text
    central_point: Text
    why_worthwhile: Text
    audience: Text
    intended_shift: Text
    primary_pillar: Literal["ATTRACT", "WARM", "CONVERT"]
    content_type: Literal["opinion", "founder_forward", "campaign_breakdown", "trend", "uvp",
        "thought_shift", "process", "behind_the_scenes", "education", "founder_story", "solution_selling", "social_proof"]
    strategic_rationale: Text
    source_demonstration: Text
    moment_keys: Texts
    evidence_refs: Texts
    claims: Annotated[list[Claim], Field(min_length=1)]
    claim_boundaries: list[Text]
    development_direction: Text
    tension: Text | None
    offer_connection: Text | None
    possible_format: Text | None
    judgments: Judgments
    nearest_alternative: Alternative


class OtherFinding(Contract):
    local_key: Text
    disposition: Literal["REFRAME", "HOLD", "INTERNAL", "SKIP"]
    moment_keys: Texts
    evidence_refs: list[Text]
    summary: Text
    disposition_reason: Text
    proposed_reframe: Text | None
    retrieval_needs: list[RetrievalNeed]
    internal_use: Text | None

    @model_validator(mode="after")
    def disposition_has_next_step(self):
        if self.disposition == "HOLD" and not self.retrieval_needs:
            raise ValueError("HOLD requires precise retrieval needs")
        if self.disposition == "INTERNAL" and not self.internal_use:
            raise ValueError("INTERNAL requires an intended use")
        if self.disposition == "REFRAME" and not self.proposed_reframe:
            raise ValueError("REFRAME requires a proposed correction")
        return self


class SourceAccounting(Contract):
    moment_key: Text
    finding_keys: list[Text]
    treatment_note: Text


class BatchNotes(Contract):
    selection_rationale: Text
    mix_rationale: Text
    history_check: Literal["not_supplied", "checked_supplied_history"]
    plan_check: Literal["not_supplied", "checked_supplied_plan"]
    limitations: list[Text]
    evidence_dependent_gaps: list[Text]


class HandbookAngleResponse(Contract):
    selected_angles: list[SelectedAngle]
    other_findings: list[OtherFinding]
    source_accounting: list[SourceAccounting]
    batch_notes: BatchNotes
