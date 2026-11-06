from typing import Literal

from pydantic import Field

from ..calendar.contracts import Mutation
from ..contracts import Contract, Text

VERSION = "production_pack_v1"
SLOTS = ("email", "carousel", "reel_1", "reel_2", "reel_3")
STAGES = ("pack_prepare", *(f"pack_{s}" for s in SLOTS), "pack_validation", "pack_assembly")


class Claim(Contract):
    text: Text
    brief_claim_ids: list[Text]
    qualifications: list[Text]


class Copy(Contract):
    title: Text
    claims: list[Claim]
    evidence_ids: list[Text]
    cta: dict


class Email(Copy):
    subject_lines: list[Text] = Field(min_length=1, max_length=5)
    subject: Text
    preview_text: Text
    body: Text


class Slide(Contract):
    number: int = Field(ge=1)
    headline: Text
    body: Text
    direction: str


class Carousel(Copy):
    slides: list[Slide] = Field(min_length=1, max_length=30)
    caption: Text


class Reel(Copy):
    spoken_script: Text
    caption: Text
    visual_directions: list[Text]


class Review(Contract):
    preserves_approved_direction: bool
    grounded: bool
    distinct_contributions: bool
    findings: list[Text]


class Generate(Mutation):
    expected_brief_hash: str = Field(min_length=1, max_length=128)
    mode: Literal["replay", "live"] = "replay"
    supersedes_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,140}$")


class Decision(Mutation):
    expected_manifest_hash: str = Field(min_length=1, max_length=128)
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=4000)


def schema(slot):
    return Email if slot == "email" else Carousel if slot == "carousel" else Reel
