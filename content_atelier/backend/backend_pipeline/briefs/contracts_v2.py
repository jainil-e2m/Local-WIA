"""Brief contract version 2 (E.B15 a; R47; plan section 4.5).

The body is what the editor reads, the header carries the structured fields other stages and the UI need, and the
ledger carries the proof. The writer returns the body and its claims (BriefBodyV2); the server builds the header
from the approved card and the pinned inputs, so nothing the writer says can change what was approved.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ..contracts import Contract, Text
from .contracts import NumericFact

SCHEMA_V1, SCHEMA_V2 = "brief_document_v1", "brief_document_v2"
# The channel set WIA confirmed (format guide; rulings R-10, R-11): Stories and Threads are optional extras.
CHANNELS = ("reel", "carousel", "email", "caption", "stories", "threads")
DEFAULT_CHANNELS = ("reel", "carousel", "email", "caption")
CLAIM_CLASSES = ("particular_interaction", "general_approach", "recommendation", "prevalence", "outcome")


class ApprovedAngle(Contract):
    title: Text
    core_perspective: Text


class SharpenedPoint(Contract):
    text: Text
    reason: Text


class StrategicPurpose(Contract):
    pillar: Literal["ATTRACT", "WARM", "CONVERT"]
    content_type: Text
    why_now: Text


class AudienceSection(Contract):
    who: Text
    reason_to_care: Text


class IntendedShift(Contract):
    understand: Text
    believe: Text
    do: Text


class SupportingExample(Contract):
    scene: Text
    wia_move: Text
    client_contribution: Text


class Hook(Contract):
    style: Literal["observation", "contrarian_belief", "question", "result", "cultural_moment", "story"]
    text: Text


class NarrativeOutline(Contract):
    hooks: list[Hook] = Field(min_length=2, max_length=4)
    problems_desires_symptoms: list[Text] = Field(min_length=1, max_length=5)
    main_point: Text
    transformation: Text
    cta: Text


class ReelPlan(Contract):
    job: Text
    cover_text: Text
    spoken_opening: Text
    beats: list[Text] = Field(min_length=2, max_length=8)
    read_time_seconds: int = Field(ge=5, le=180)
    source: Literal["existing_clip", "new_script"]
    evidence_ids: list[Text]


class Slide(Contract):
    number: int = Field(ge=1, le=12)
    job: Text
    text: Text
    evidence_ids: list[Text]


class CarouselPlan(Contract):
    job: Text
    slides: list[Slide] = Field(min_length=7, max_length=12)


class EmailPlan(Contract):
    subject_options: list[Text] = Field(min_length=2, max_length=4)
    preview: Text
    opening: Text
    argument: Text
    transformation: Text
    ending: Text
    evidence_ids: list[Text]


class CaptionPlan(Contract):
    hook: Text
    adds: Text
    ending: Text


class StoriesPlan(Contract):
    frames: list[Text] = Field(min_length=1, max_length=8)


class FormatPlan(Contract):
    reels: list[ReelPlan] = Field(max_length=3)
    carousel: CarouselPlan | None
    email: EmailPlan | None
    caption: CaptionPlan | None
    stories: StoriesPlan | None


class BriefCTA(Contract):
    """{choice, track, action, offer_connection, chosen_by} (R46). A writer may propose; only a person confirms."""
    choice: Literal["explicit", "no_explicit_ask", "decide_in_development"]
    track: Text | None
    action: Text | None
    offer_connection: Text | None
    chosen_by: Literal["writer", "person"]

    @model_validator(mode="after")
    def explicit_has_an_action(self):
        if self.choice == "explicit" and not (self.action or "").strip():
            raise ValueError("An explicit CTA needs its action")
        return self


class BeforePublishing(Contract):
    text: Text
    kind: Literal["fact", "permission", "offer", "cta", "do_not_claim", "other"]
    required: bool
    answer: str | None


class EvidenceRef(Contract):
    evidence_id: Text
    speaker: str | None
    start_ms: int | None
    quote: Text


class ClaimV2(Contract):
    claim_id: Text
    text: Text
    claim_class: Literal["particular_interaction", "general_approach", "recommendation", "prevalence", "outcome"]
    evidence_ids: list[Text]
    # A "general approach" claim cites the knowledge-base document that states it (section 4.5).
    knowledge_base_document: str | None
    numeric_facts: list[NumericFact]
    quote: str | None
    public_quote: bool


class BriefBodyV2(Contract):
    """What the writer returns."""
    approved_angle: ApprovedAngle
    sharpened_point: SharpenedPoint | None
    strategic_purpose: StrategicPurpose
    audience: AudienceSection
    intended_shift: IntendedShift
    point_of_view: Literal["we", "I"]
    wia_perspective: Text
    supporting_example: SupportingExample
    narrative_outline: NarrativeOutline
    format_plan: FormatPlan
    cta: BriefCTA
    cta_why: Text
    before_publishing: list[BeforePublishing] = Field(max_length=5)
    evidence: list[EvidenceRef] = Field(min_length=1)
    claims: list[ClaimV2] = Field(min_length=1)


class BriefHeaderV2(Contract):
    schema_version: Literal["brief_document_v2"]
    angle_id: Text
    angle_hash: Text
    purpose: Literal["ATTRACT", "WARM", "CONVERT"]
    content_type: Text
    audience: Text
    intended_shift: IntendedShift
    point_of_view: Literal["we", "I"]
    cta: BriefCTA
    channels: list[Text]
    pinned_inputs: dict


class BriefDocumentV2(Contract):
    header: BriefHeaderV2
    body: BriefBodyV2


EDITABLE_V2 = {"sharpened_point", "strategic_purpose", "audience", "intended_shift", "point_of_view", "wia_perspective",
               "supporting_example", "narrative_outline", "format_plan", "cta_why", "before_publishing", "claims"}


def writer_schema_v2(channels):
    """The body schema the writer receives, with formats outside the confirmed channel set forced to null."""
    schema = BriefBodyV2.model_json_schema()
    plan = schema["$defs"]["FormatPlan"]["properties"]
    if "reel" not in channels:
        plan["reels"]["maxItems"] = 0
    for name in ("carousel", "email", "caption", "stories"):
        if name not in channels:
            plan[name] = {"type": "null", "title": plan[name].get("title", name)}
    return schema
