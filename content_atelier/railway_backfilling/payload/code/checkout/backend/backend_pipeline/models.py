from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .strategy_contracts import Discovery, StrategicAngleDraft


def now() -> datetime:
    return datetime.now(UTC)


class Span(BaseModel):
    model_config = ConfigDict(extra="forbid")
    span_id: str
    source_id: str
    ordinal: int
    start_seconds: float | None
    end_seconds: float | None
    speaker: str | None = None
    text: str


class Transcript(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    week_index: int
    path: str
    content_hash: str
    spans: list[Span]
    source_format: Literal["webvtt", "timestamped_text", "plain_text"]
    source_metadata: dict = Field(default_factory=dict)


class Moment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    moment_id: str
    source_ids: list[str]
    anchor_span_ids: list[str]
    context_span_ids: list[str]
    quote: str
    context_summary: str
    moment_type: str
    proposition: str
    audience_relevance: str
    qualifications: list[str] = Field(default_factory=list)
    claim_status: str
    sensitivity: str = "unknown"
    strength: float = Field(ge=0, le=5)
    reasons: list[str] = Field(default_factory=list)
    discovery: Discovery | None = None


class Quality(BaseModel):
    grounding: float = Field(ge=0, le=5)
    source_relevance: float = Field(ge=0, le=5)
    audience_fit: float = Field(ge=0, le=5)
    specificity: float = Field(ge=0, le=5)
    editorial_usefulness: float = Field(ge=0, le=5)
    reasons: list[str] = Field(default_factory=list)
    strategic_fit: float | None = Field(default=None, ge=0, le=5)
    distinctiveness: float | None = Field(default=None, ge=0, le=5)
    audience_resonance: float | None = Field(default=None, ge=0, le=5)
    source_strength: float | None = Field(default=None, ge=0, le=5)

    def score(self) -> float:
        strategic = (self.strategic_fit, self.distinctiveness, self.audience_resonance, self.source_strength)
        if all(value is not None for value in strategic):
            # Provisional bottleneck, not calibrated weights: strong grounding
            # cannot compensate for poor strategy fit or audience relevance.
            return 20 * min(self.grounding, *strategic)
        return 20 * (
            0.35 * self.grounding
            + 0.25 * self.source_relevance
            + 0.15 * self.audience_fit
            + 0.15 * self.specificity
            + 0.10 * self.editorial_usefulness
        )


class Angle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    angle_id: str
    run_id: str
    title: str
    argument: str
    audience: str
    tension: str
    take: str
    mechanism: str
    reader_decision: str | None
    moment_ids: list[str]
    source_assertions: list[str]
    inference: str | None = None
    qualifiers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    signature: str
    quality: Quality
    base_score: float
    status: Literal["candidate", "visible", "suppressed", "invalid"] = "candidate"
    generated_at: datetime = Field(default_factory=now)
    embedding: list[float] | None = None
    max_similarity: float | None = None
    adjusted_score: float | None = None
    strategy: StrategicAngleDraft | None = None
    source_family_id: str | None = None


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    week_index: int
    source_root: str
    source_ids: list[str]
    prompt_profile: str
    model_id: str
    embedding_profile: str
    mode: Literal["plan", "replay", "live", "fake"]
    created_at: datetime = Field(default_factory=now)
    parent_run_id: str | None = None
    status: Literal["planned", "partial", "generation_completed", "completed", "failed"] = "planned"
    execution_scope: Literal["generation_only", "full"] = "full"


class StageArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cache_version: int = 2
    artifact_id: str
    run_id: str
    stage: Literal["moment_extraction", "angle_generation", "angle_refinement", "embedding", "brief_plan", "brief_grade", "brief_write", "brief_review", "brief_repair", "brief_web", "pack_write", "pack_review"]
    request_fingerprint: str
    prompt_version: str | None = None
    model_id: str
    status: Literal["planned", "response_saved", "validated", "failed", "reused"]
    input_hashes: list[str]
    request: dict | None = None
    output_hash: str | None = None
    metadata: dict = Field(default_factory=dict)
    output: dict | list | None = None
    raw_response: dict | None = None
    usage: dict | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=now)
