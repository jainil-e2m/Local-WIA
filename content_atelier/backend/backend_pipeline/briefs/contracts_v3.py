"""Brief contract version 3 (E.B23; plan sections 1.9.2 and 1.9.8, standard 2.4a, R54).

Version 2's contract pushed hedging: every Reel, slide and email carried `evidence_ids`, so assets read as claims;
`CaptionPlan.adds` and `EmailPlan.argument` read as directions to a writer; the reader decision was mandatory; and the
writer wrote its own claims ledger beside the copy, so it cited and qualified inside the copy. Version 3:

- the writer returns finished copy and short directions only (BriefWriteV3): no `evidence_ids` on any asset, no claims,
  no evidence list; the caption has a `body` and the email a `body` of finished paragraphs; a new-script Reel has its
  `script`; `IntendedShift.do` is optional (Whitney: the reader decision is optional);
- the claims ledger (claims and quoted turns) is built after writing, in a separate step (briefs/ledger_v3.py):
  deterministic binding of each statement in the copy to the evidence, then the verifier from another model family on
  what the binding could not settle (as R42 does for cards).

The document a person reviews (BriefDocumentV3) is the writer's body plus that ledger. Field descriptions are part of the
schema the writer receives, so they say which fields are copy and which are direction.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from ..contracts import Contract, Text
from .contracts import NumericFact
from .contracts_v2 import (ApprovedAngle, AudienceSection, BeforePublishing, BriefCTA, EvidenceRef, NarrativeOutline,
                           SharpenedPoint, StoriesPlan, StrategicPurpose, SupportingExample)

SCHEMA_V3 = "brief_document_v3"
# A WIA team member's first-person observation from their own work is attributed experience (E.B26), never a prevalence claim.
CLAIM_CLASSES_V3 = ("particular_interaction", "general_approach", "recommendation", "prevalence", "outcome", "attributed_experience")
COPY = "Copy: finished words the audience reads or hears, in WIA's voice, ready to publish. "
DIRECTION = "Direction: a short note to the person who makes the asset; never published. "


class IntendedShiftV3(Contract):
    understand: Text
    believe: Text
    do: str | None = Field(description="What the reader might do next, or null: the reader decision is optional")


class ReelPlanV3(Contract):
    job: Text = Field(description=DIRECTION + "What this Reel does for the reader")
    cover_text: Text = Field(description=COPY + "The on-screen cover text")
    spoken_opening: Text = Field(description=COPY + "The first spoken line")
    script: str | None = Field(description=COPY + "For a new script: the whole spoken script, start to end, as Whitney would "
                                                  "say it. Null for an existing clip")
    beats: list[Text] = Field(min_length=2, max_length=8,
                              description=DIRECTION + "The beats in order; for an existing clip, the exact start and end lines")
    read_time_seconds: int = Field(ge=5, le=180)
    source: Literal["existing_clip", "new_script"]


class SlideV3(Contract):
    number: int = Field(ge=1, le=12)
    job: Text = Field(description=DIRECTION + "What this slide does")
    text: Text = Field(description=COPY + "The slide's finished text")


class CarouselPlanV3(Contract):
    job: Text = Field(description=DIRECTION + "What the carousel does for the reader")
    slides: list[SlideV3] = Field(min_length=7, max_length=12)


class EmailPlanV3(Contract):
    subject_options: list[Text] = Field(min_length=2, max_length=4, description=COPY + "Subject lines to choose from")
    preview: Text = Field(description=COPY + "The preview text")
    opening: Text = Field(description=COPY + "The greeting and the opening paragraph")
    body: Text = Field(description=COPY + "The rest of the email in finished paragraphs, separated by blank lines: the "
                                          "argument, the story, the principle and the change in thinking")
    ending: Text = Field(description=COPY + "The closing paragraph with its ask, and the sign-off")


class CaptionPlanV3(Contract):
    hook: Text = Field(description=COPY + "The caption's first line, distinct from the Reel's hook")
    body: Text = Field(description=COPY + "The finished caption after the hook, in paragraphs")
    ending: Text = Field(description=COPY + "The caption's last line: its ask or closing thought, and any sign-off")


class FormatPlanV3(Contract):
    reels: list[ReelPlanV3] = Field(max_length=3)
    carousel: CarouselPlanV3 | None
    email: EmailPlanV3 | None
    caption: CaptionPlanV3 | None
    stories: StoriesPlan | None


class BriefWriteV3(Contract):
    """What the writer returns: copy and direction, with every caveat under Before publishing. No claims, no citations."""
    approved_angle: ApprovedAngle
    sharpened_point: SharpenedPoint | None
    strategic_purpose: StrategicPurpose
    audience: AudienceSection
    intended_shift: IntendedShiftV3
    point_of_view: Literal["we", "I"]
    wia_perspective: Text = Field(description=COPY + "WIA's belief or practice, as Whitney would say it")
    supporting_example: SupportingExample
    narrative_outline: NarrativeOutline
    format_plan: FormatPlanV3
    cta: BriefCTA
    cta_why: Text
    before_publishing: list[BeforePublishing] = Field(max_length=5)


# The ledger -------------------------------------------------------------------------------------------------------
# How a statement in the copy was settled: bound by the rules to the call's words, judged by the verifier, or kept by a
# person who edited the section that holds it after the verifier found no support.
# `attested` (R57, 5.B7): a statement an approver attested at a gate, or the attested fact itself; settled by a person.
STATUSES = ("bound", "supported", "unsupported", "unchecked", "kept_by_person", "attested")


class LedgerFlag(Contract):
    """The verifier's note on a statement, as the card verifier's (E.B10): a block is repaired, a check is a person's look."""
    kind: Literal["invented_reason", "overclaim", "tense", "misattribution", "frequency", "consent", "positioning", "other"]
    severity: Literal["block", "check"]
    message: Text
    source: str | None


class Attestation(Contract):
    """Who stated a fact at a gate, and when (R57). A paraphrase is a client's words in the approver's: never a quote."""
    kind: Literal["attested_fact", "paraphrase"]
    context_id: Text
    by: Text
    on: Text


class LedgerClaim(Contract):
    """A statement in the copy and what supports it. The fields v2's claim checks read come first, unchanged."""
    claim_id: Text
    text: Text
    claim_class: Literal["particular_interaction", "general_approach", "recommendation", "prevalence", "outcome",
                         "attributed_experience"]
    evidence_ids: list[Text]
    knowledge_base_document: str | None
    numeric_facts: list[NumericFact]
    quote: str | None
    public_quote: bool
    field: Text
    status: Literal["bound", "supported", "unsupported", "unchecked", "kept_by_person", "attested"]
    settled_by: Literal["deterministic", "verifier", "person", "none"]
    note: str | None
    flag: LedgerFlag | None
    # Set on an attested fact's own entry and on each statement of the copy it supports (5.B7).
    attested: Attestation | None = None


class BriefBodyV3(BriefWriteV3):
    """The writer's body with the ledger built after writing."""
    evidence: list[EvidenceRef]
    claims: list[LedgerClaim]


class BriefHeaderV3(Contract):
    schema_version: Literal["brief_document_v3"]
    angle_id: Text
    angle_hash: Text
    purpose: Literal["ATTRACT", "WARM", "CONVERT"]
    content_type: Text
    audience: Text
    intended_shift: IntendedShiftV3
    point_of_view: Literal["we", "I"]
    cta: BriefCTA
    channels: list[Text]
    pinned_inputs: dict


class BriefDocumentV3(Contract):
    header: BriefHeaderV3
    body: BriefBodyV3


# A person edits the writer's sections; the ledger is rebuilt from them (validation_v3.rebuild), never edited by hand.
EDITABLE_V3 = {"sharpened_point", "strategic_purpose", "audience", "intended_shift", "point_of_view", "wia_perspective",
               "supporting_example", "narrative_outline", "format_plan", "cta_why", "before_publishing"}
WRITER_FIELDS_V3 = tuple(BriefWriteV3.model_fields)


def writer_schema_v3(channels):
    """The writer's schema, with formats outside the confirmed channel set forced to null (as v2)."""
    schema = BriefWriteV3.model_json_schema()
    plan = schema["$defs"]["FormatPlanV3"]["properties"]
    if "reel" not in channels:
        plan["reels"]["maxItems"] = 0
    for name in ("carousel", "email", "caption", "stories"):
        if name not in channels:
            plan[name] = {"type": "null", "title": plan[name].get("title", name)}
    return schema


def writer_part(body: dict) -> dict:
    """The writer's sections of a v3 body (a repair or a revision is given these, never the ledger)."""
    return {k: body[k] for k in WRITER_FIELDS_V3 if k in body}
