"""Lean editorial card contract for the WIA strategist angle profile (E.B9, analysis 9.3 and Appendix A).

The creative call returns cards, a ranking and the selection reasoning. Assertions, qualifiers, risks and
self-scores belong to the later evidence ledger (E.B10), not to this contract.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import Contract, Text, Texts

Pillar = Literal["ATTRACT", "WARM", "CONVERT"]
CardContentType = Literal[
    "polarizing_opinion", "founder_forward", "campaign_breakdown", "trend", "uvp", "lightbulb_moment",
    "process_or_framework", "behind_the_scenes", "education", "founder_story", "solution_selling", "social_proof",
]


class AngleCard(Contract):
    rank: Annotated[int, Field(ge=1)]
    title: Text
    pillar: Pillar
    content_type: CardContentType
    audience: Text
    core_perspective: Text
    why_it_matters: Text
    wia_in_action: Text | None
    offer_connection: Text | None
    moment_ids: Texts
    evidence_points: Texts
    verify_before_publishing: Annotated[list[Text], Field(max_length=2)]
    why_selected: Text


class CardInternalInsight(Contract):
    moment_ids: Texts
    insight: Text
    use: Text


class ConsideredIdea(Contract):
    moment_ids: Texts
    idea: Text
    reason: Text


class WeeklyAngleCards(Contract):
    week_summary: Text
    angles: list[AngleCard]
    internal_insights: list[CardInternalInsight]
    considered_not_selected: list[ConsideredIdea]

    @model_validator(mode="after")
    def ranks_are_contiguous(self):
        if sorted(a.rank for a in self.angles) != list(range(1, len(self.angles) + 1)):
            raise ValueError("Angle ranks must be unique and contiguous from 1")
        return self


def is_card_response(output: dict) -> bool:
    return isinstance(output, dict) and "week_summary" in output


# Strategist profile v5 (E.B21). A separate contract, so the v3 and v4 schemas and their saved requests are unchanged.

class AngleCardV5(AngleCard):
    # One of the content strategy's priority series, when the idea belongs to one.
    series: Text | None


class PillarNote(Contract):
    pillar: Pillar
    note: Text


class SeedPairing(Contract):
    seed_ref: Text
    # Scene references that support the seed; empty means "no call evidence".
    moment_ids: list[Text]
    note: Text


class WeeklyAngleCardsV5(WeeklyAngleCards):
    angles: list[AngleCardV5]
    # The ranks in the order the strategist would publish them this week. A card it leaves out is held for a later week:
    # WIA publishes about three pieces a week (ruling R-10), so a four-card slate often schedules three.
    publishing_order: list[Annotated[int, Field(ge=1)]]
    # When the slate sits in one pillar: for each other pillar, whether any scene supports it.
    pillar_notes: list[PillarNote]
    seed_pairings: list[SeedPairing]

    @model_validator(mode="after")
    def publishing_order_names_each_rank_once(self):
        ranks = {a.rank for a in self.angles}
        order = self.publishing_order or []
        if len(order) != len(set(order)) or not set(order) <= ranks:
            raise ValueError("publishing_order must list angle ranks of this slate, each at most once")
        return self

    @property
    def held(self) -> list[int]:
        """The ranks the publishing order leaves for a later week."""
        return sorted({a.rank for a in self.angles} - set(self.publishing_order)) if self.publishing_order else []


# Strategist profile v7 (E.B30, E.B32, E.B29 change; plan section 4.2). Whitney's own angle format: her six fields at her
# length (content pillar and type, audience, why this matters, WIA's expertise or process, evidence in the referenced call,
# editorial guardrail and next step), then the point and its five tests. The point replaces v3 to v6's core_perspective;
# read either through `card_point`. A separate contract: the v3 to v6 schemas and their saved requests are unchanged.

PointIsAbout = Literal["wia_belief", "wia_standard", "client_experience", "platform_or_tactic"]
Buyer = Literal["elevate", "accelerators", "leadlock", "established_owner"]
CtaSlot = Literal["offer_cta", "soft_invitation", "none"]


class Surprise(Contract):
    # Would an established owner who already runs ads be surprised by the point? Why, or why not.
    surprising: bool
    reason: Text


class ReaderFit(Contract):
    # Whose buyer the reader is, matched against Whitney's own buyer statements (knowledge base 11 and 16).
    buyer: Buyer
    buyer_statement: Text
    why: Text


class OfferFit(Contract):
    # The offer the card serves this window (the strategy brief's), the CTA slot it takes, and why it fits the calendar.
    offer: Text | None
    cta_slot: CtaSlot
    calendar_note: Text


class PublicStance(Contract):
    # True when the card takes a public position (for example, a view on AI); Whitney confirms it before development (D31).
    takes_stance: bool
    stance: Text | None


class AngleCardV7(Contract):
    rank: Annotated[int, Field(ge=1)]
    title: Text
    # Her six fields, one to three sentences each.
    pillar: Pillar
    content_type: CardContentType
    series: Text | None
    audience: Text
    why_it_matters: Text
    wia_in_action: Text
    evidence_points: Annotated[list[Text], Field(min_length=1, max_length=3)]
    guardrail: Text
    # The point, tested.
    point: Text
    point_is_about: PointIsAbout
    surprise_for_experienced_advertiser: Surprise
    reader_takeaway: Text
    reader_fit: ReaderFit
    belief_ref: Text
    offer_fit: OfferFit
    public_stance: PublicStance
    # How often the moment's topic came up this week: context for Whitney, never a ranking input (E.B29 change).
    recurrence: Text | None
    moment_ids: Texts
    verify_before_publishing: Annotated[list[Text], Field(max_length=2)]
    why_selected: Text


class WeeklyAngleCardsV7(Contract):
    week_summary: Text
    angles: list[AngleCardV7]
    internal_insights: list[CardInternalInsight]
    considered_not_selected: list[ConsideredIdea]
    publishing_order: list[Annotated[int, Field(ge=1)]]
    pillar_notes: list[PillarNote]
    seed_pairings: list[SeedPairing]

    @model_validator(mode="after")
    def ranks_and_order(self):
        ranks = sorted(a.rank for a in self.angles)
        if ranks != list(range(1, len(self.angles) + 1)):
            raise ValueError("Angle ranks must be unique and contiguous from 1")
        order = self.publishing_order or []
        if len(order) != len(set(order)) or not set(order) <= set(ranks):
            raise ValueError("publishing_order must list angle ranks of this slate, each at most once")
        return self

    @property
    def held(self) -> list[int]:
        return sorted({a.rank for a in self.angles} - set(self.publishing_order)) if self.publishing_order else []


# The fields v7 adds to a card, for the brief writer's packet and the API (the integrator adds them to Gate 1's field map).
V7_POINT_FIELDS = ("point", "point_is_about", "surprise_for_experienced_advertiser", "reader_takeaway", "reader_fit",
                   "belief_ref", "offer_fit", "public_stance", "guardrail", "recurrence")


def is_v7(card: dict | None) -> bool:
    return isinstance(card, dict) and "point" in card


def card_point(card: dict | None) -> str | None:
    """A card's central point: v7's `point`, or v3 to v6's `core_perspective`."""
    card = card or {}
    return card.get("point") if "point" in card else card.get("core_perspective")


def card_contract_for(card: dict):
    """The contract a stored card was made under: v7 (a point), v5 and v6 (a series), else v3 and v4."""
    if is_v7(card):
        return AngleCardV7
    return AngleCardV5 if "series" in card else AngleCard


def takes_public_stance(card: dict | None) -> bool:
    return bool(((card or {}).get("public_stance") or {}).get("takes_stance"))
