from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field

from . import settings_store
from .settings_store import CARD_PROFILES, LoadedSettings, default

ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent
# Card-producing strategist profiles (angle_profiles.py) are defined with the settings (settings_store.CARD_PROFILES,
# imported above). Version 3 is kept for replay only.

# The one embedding contract. The research archive was encoded through OpenRouter
# with this model string; every stored vector and its provenance digest is bound
# to these three values. Change them only to re-encode the archive deliberately.
EMBEDDING_ENDPOINT = default("embedding.endpoint")
EMBEDDING_MODEL = default("embedding.model")
EMBEDDING_DIMENSIONS = default("embedding.dimensions")


def embedding_contract(models) -> dict:
    """Endpoint, model string and dimensions shared by every embedding digest.

    Stage digests extend this dict with their own input version. canonical_hash
    sorts keys, so the digests equal those recorded before this was centralised.
    """
    if models.embedding_dimensions != EMBEDDING_DIMENSIONS:
        raise ValueError(f"Embedding contract requires the approved {EMBEDDING_DIMENSIONS} dimensions")
    return {"endpoint": models.embedding_base_url.rstrip("/"), "model": models.embedding_model,
            "dimensions": EMBEDDING_DIMENSIONS}


class Settings(LoadedSettings):
    """The model-side configuration. Defaults here are the registry's (settings_store.DEFINITIONS), which equal the
    documented defaults of the example environment files; `from_env` adds the environment files, the process
    environment and the settings table, in that order of precedence (settings_store module docstring)."""
    data_root: Path = Field(default=PROJECT_ROOT / "testing" / ".data")
    transcript_root: Path = Field(default=PROJECT_ROOT / "backend" / "zoom_backfill_meetings")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_moments_model: str = default("models.moment_extraction")
    openrouter_angles_model: str = default("models.default")
    # Per-stage override for strategist angle generation only; blank keeps openrouter_angles_model.
    # The default profile, refinement and brief stages that inherit the angles model are unaffected.
    openrouter_angle_generation_model: str | None = default("models.angle_generation")
    # E.B10's model pass over each week's cards; must be another model family than the strategist's. Blank skips it.
    openrouter_verification_model: str | None = default("models.card_verification")
    # The learning loop's edit categoriser (L.B6): a different family from the brief writer. Unset: rules only.
    openrouter_context_mining_model: str | None = default("models.context_mining")
    # Places a document the classification rules cannot (plan 1.B4). Unset: rules only, and the document is marked for a person.
    openrouter_document_classification_model: str | None = default("models.document_classification")
    # The brief and pack models (also on StorageSettings); stages without one fall back to openrouter_angles_model.
    brief_model: str | None = default("models.brief")
    brief_review_model: str | None = default("models.brief_review")
    pack_writer_model: str | None = default("models.pack_writer")
    pack_review_model: str | None = default("models.pack_review")
    openrouter_moments_key: str | None = None
    openrouter_angles_key: str | None = None
    embedding_base_url: str = EMBEDDING_ENDPOINT
    embedding_api_key: str | None = None
    embedding_model: str = EMBEDDING_MODEL
    embedding_dimensions: int = EMBEDDING_DIMENSIONS
    # Disabled throughout prompt calibration. Reconnection requires user approval.
    embeddings_enabled: bool = False
    llm_payload_format: Literal["legacy_flat", "compact_weekly"] = default("models.payload_format")
    llm_completion_tokens: int | None = Field(default=default("models.completion_tokens"), gt=0)
    # Output cap of one stage (key suffix of models.completion_tokens.*); a stage without one uses llm_completion_tokens.
    stage_completion_tokens: dict[str, int | None] = Field(default_factory=dict)
    # Explicit test override: false disables local input-size rejection only.
    # Output caps remain optional via llm_completion_tokens; providers still limit both.
    llm_input_limits_enabled: bool = default("models.input_limits_enabled")
    llm_reasoning_effort: Literal["low", "medium", "high"] | None = default("models.reasoning_effort.default")
    # Reasoning effort of one stage (key suffix of models.reasoning_effort.*); a stage without one uses the default.
    # The pack writer and reviewer default to medium (NP.B5, the planning probe's effort); every other stage to the default.
    stage_reasoning_effort: dict[str, Literal["low", "medium", "high"] | None] = Field(
        default_factory=lambda: {"pack_writer": "medium", "pack_review": "medium"})
    llm_response_format: Literal["json_schema", "json_object"] = default("models.response_format")
    similarity_threshold: float = default("matching.related")
    close_similarity_threshold: float = default("matching.close")
    visible_threshold: float = default("scoring.visible_threshold")
    recency_half_life_days: float = default("matching.half_life_days")
    max_recency_penalty: float = default("matching.max_recency_penalty")
    request_timeout_seconds: float = default("models.request_timeout_seconds")
    # An operational safeguard, not a substitute for route-specific token budgets.
    max_llm_request_characters: int = Field(default=default("models.max_request_characters"), gt=0)
    live_enabled: bool = False
    # Default stays on the legacy profile until WIA has reviewed strategist results.
    angle_prompt_profile: Literal[
        "2026-10-19.reel-editorial.v2", "2026-10-16.reel-editorial.v1", "2026-10-18.wia-strategist.v3",
        "2026-10-18.wia-strategist.v4", "2026-10-18.wia-strategist.v5", "2026-10-20.wia-strategist.v6",
        "2026-10-23.wia-strategist.v7", "2026-10-25.wia-strategist.v8", "2026-10-25.wia-strategist.v9"
    ] = default("prompts.profile.strategist")
    knowledge_base_root: Path = Field(default=BACKEND_ROOT / "knowledge_base")
    # E.B12: the ledger's per-document scene profile v2 (the default), the whole-week weekly v3 prompt, or the v1 scene loop.
    # Frozen at submit with the run.
    extraction_profile: Literal["2026-10-19.scenes.v2", "2026-10-13.weekly.v3", "2026-10-18.scenes.v1",
                                "2026-10-23.scenes.v3", "2026-10-25.scenes.v4"] = default("prompts.profile.extraction")
    # E.B10's model pass: v3, or v4 with strategist v7's point tests (E.B30).
    card_verification_profile: Literal["card-verification.v3", "card-verification.v4"] = default(
        "prompts.profile.card_verification")

    def model_for(self, stage: str) -> str:
        """The model of one stage: its own setting, else the default model (models.default)."""
        if stage == "moment_extraction":
            return self.openrouter_moments_model
        if (stage == "angle_generation" and self.openrouter_angle_generation_model
                and self.angle_prompt_profile in CARD_PROFILES):
            return self.openrouter_angle_generation_model
        if stage == "card_verification" and self.openrouter_verification_model:
            return self.openrouter_verification_model
        if stage == "context_mining" and self.openrouter_context_mining_model:
            return self.openrouter_context_mining_model
        if stage == "document_classification" and self.openrouter_document_classification_model:
            return self.openrouter_document_classification_model
        suffix = settings_store.STAGE_SUFFIX.get(stage)
        own = {"brief": self.brief_model, "brief_review": self.brief_review_model, "pack_writer": self.pack_writer_model,
               "pack_review": self.pack_review_model}.get(suffix)
        return own or self.openrouter_angles_model

    def completion_tokens_for(self, stage: str) -> int | None:
        """Output cap of one stage: models.completion_tokens.<stage>, else models.completion_tokens (N1: a scene extraction
        of a long call needs more than a card or a brief)."""
        return self.stage_completion_tokens.get(stage) or self.llm_completion_tokens

    def reasoning_effort_for(self, stage: str) -> str | None:
        """Reasoning effort of one stage (0.B4, 0.B8): models.reasoning_effort.<stage>, else the default value."""
        suffix = settings_store.STAGE_SUFFIX.get(stage)
        return self.stage_reasoning_effort.get(suffix) or self.llm_reasoning_effort

    def explicit_model_gaps(self) -> list[str]:
        """Paid-stage models left at the code default (section 4.10): none for an object built by hand."""
        return settings_store.explicit_model_gaps(self)

    def require_explicit_models(self) -> None:
        """Live mode refuses to start a paid stage whose model was not set explicitly (section 4.10)."""
        settings_store.require_explicit_models(self)

    def validate_live(self) -> None:
        missing = []
        if not self.openrouter_moments_key and not os.getenv("OPENROUTER_API_KEY"):
            missing.append("OPENROUTER_MOMENTS_KEY")
        if not self.openrouter_angles_key and not os.getenv("OPENROUTER_API_KEY"):
            missing.append("OPENROUTER_ANGLES_KEY")
        if self.embeddings_enabled and not self.embedding_api_key and not os.getenv("OPENAI_API_KEY"):
            missing.append("EMBEDDING_API_KEY")
        if missing:
            raise RuntimeError("Missing live configuration: " + ", ".join(missing))

    @classmethod
    def from_env(cls, conn=None, *, database_url: str | None = None) -> Settings:
        """Build the settings: code defaults, then the legacy environment, then the settings table.

        The legacy files (backend/.env, the root .env, .env.storage.local, .env.intake.local) are loaded by the one
        reader in settings_store, the process environment winning. The table is read from `conn`, `database_url`
        or ATELIER_DATABASE_URL when one is set (a database that cannot be reached falls back to the environment).
        """
        return cls.from_effective(settings_store.load(conn, database_url=database_url))

    @classmethod
    def from_effective(cls, eff) -> Settings:
        values: dict[str, object] = {}
        stage_efforts: dict[str, str | None] = {}
        stage_tokens: dict[str, int | None] = {}
        for d in settings_store.DEFINITIONS:
            if "models" not in (d.target or "").split("+") or not d.field:
                continue
            if d.field_key:
                (stage_tokens if d.field == "stage_completion_tokens" else stage_efforts)[d.field_key] = eff.values[d.key]
            elif d.key == "knowledge_base.directory":
                if eff.values[d.key]:
                    values[d.field] = eff.values[d.key]
            else:
                values[d.field] = eff.values[d.key]
        values["stage_reasoning_effort"] = stage_efforts
        values["stage_completion_tokens"] = stage_tokens
        for env, field in {"CONTENT_ATELIER_DATA_ROOT": "data_root", "CONTENT_ATELIER_TRANSCRIPT_ROOT": "transcript_root",
                           "OPENROUTER_BASE_URL": "openrouter_base_url", "OPENROUTER_MOMENTS_KEY": "openrouter_moments_key",
                           "OPENROUTER_ANGLES_KEY": "openrouter_angles_key", "EMBEDDING_API_KEY": "embedding_api_key"}.items():
            if os.getenv(env):
                values[field] = os.environ[env]
        # One shared-account key can serve both LLM stages. Explicit stage keys
        # take precedence; the separate embedding credential never uses it.
        if common_llm_key := os.getenv("OPENROUTER_API_KEY"):
            values.setdefault("openrouter_moments_key", common_llm_key)
            values.setdefault("openrouter_angles_key", common_llm_key)
        # Environment-only safety catches: never settings.
        values["live_enabled"] = os.getenv("CONTENT_ATELIER_LIVE", "false").lower() == "true"
        values["embeddings_enabled"] = os.getenv("CONTENT_ATELIER_EMBEDDINGS_ENABLED", "false").lower() == "true"
        return cls(**values)._attach(eff)


def frozen_models(settings: "Settings") -> dict:
    """The models a weekly run is submitted under (E.B16 n): frozen at submit, so a worker restarted with another
    model refuses the run instead of silently running it under the new one."""
    return {"moment_extraction": settings.model_for("moment_extraction"), "angle_generation": settings.model_for("angle_generation"),
            "card_verification": settings.openrouter_verification_model or None}
