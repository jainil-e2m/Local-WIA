from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseModel):
    data_root: Path = Field(default=PROJECT_ROOT / "testing" / ".data")
    transcript_root: Path = Field(default=PROJECT_ROOT / "backend" / "zoom_backfill_meetings")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_moments_model: str = "openai/gpt-6-luna"
    openrouter_angles_model: str = "openai/gpt-6-luna"
    openrouter_moments_key: str | None = None
    openrouter_angles_key: str | None = None
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    # Disabled throughout prompt calibration. Reconnection requires user approval.
    embeddings_enabled: bool = False
    llm_payload_format: Literal["legacy_flat", "compact_weekly"] = "legacy_flat"
    llm_completion_tokens: int | None = Field(default=None, gt=0)
    # Explicit test override: false disables local input-size rejection only.
    # Output caps remain optional via llm_completion_tokens; providers still limit both.
    llm_input_limits_enabled: bool = True
    llm_reasoning_effort: Literal["low", "medium", "high"] | None = None
    llm_response_format: Literal["json_schema", "json_object"] = "json_schema"
    similarity_threshold: float = 0.78
    close_similarity_threshold: float = 0.90
    visible_threshold: float = 70.0
    recency_half_life_days: float = 28.0
    max_recency_penalty: float = 0.50
    request_timeout_seconds: float = 180.0
    # An operational safeguard, not a substitute for route-specific token budgets.
    max_llm_request_characters: int = Field(default=120000, gt=0)
    live_enabled: bool = False

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
    def from_env(cls) -> Settings:
        # Lightweight dotenv loading keeps the test harness dependency-free.
        # Process environment wins; backend-local values precede the legacy
        # project-root file. Existing secrets/datastores need no relocation.
        for env_path in (BACKEND_ROOT / ".env", PROJECT_ROOT / ".env"):
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        values: dict[str, object] = {}
        mappings = {
            "CONTENT_ATELIER_DATA_ROOT": "data_root",
            "CONTENT_ATELIER_TRANSCRIPT_ROOT": "transcript_root",
            "OPENROUTER_BASE_URL": "openrouter_base_url",
            "OPENROUTER_MOMENTS_MODEL": "openrouter_moments_model",
            "OPENROUTER_ANGLES_MODEL": "openrouter_angles_model",
            "OPENROUTER_MOMENTS_KEY": "openrouter_moments_key",
            "OPENROUTER_ANGLES_KEY": "openrouter_angles_key",
            "EMBEDDING_BASE_URL": "embedding_base_url",
            "EMBEDDING_API_KEY": "embedding_api_key",
            "OPENAI_EMBEDDING_MODEL": "embedding_model",
            "CONTENT_ATELIER_LLM_PAYLOAD_FORMAT": "llm_payload_format",
            "CONTENT_ATELIER_LLM_REASONING_EFFORT": "llm_reasoning_effort",
            "CONTENT_ATELIER_LLM_RESPONSE_FORMAT": "llm_response_format",
        }
        for env, field in mappings.items():
            if os.getenv(env):
                values[field] = os.environ[env]
        # One shared-account key can serve both LLM stages. Explicit stage keys
        # take precedence; the separate embedding credential never uses it.
        if common_llm_key := os.getenv("OPENROUTER_API_KEY"):
            values.setdefault("openrouter_moments_key", common_llm_key)
            values.setdefault("openrouter_angles_key", common_llm_key)
        # Backward-compatible aliases from the first implementation.
        if os.getenv("OPENROUTER_MODEL") and not os.getenv("OPENROUTER_ANGLES_MODEL"):
            values["openrouter_angles_model"] = os.environ["OPENROUTER_MODEL"]
        for env, field, cast in [
            ("CONTENT_ATELIER_EMBEDDING_DIMENSIONS", "embedding_dimensions", int),
            ("CONTENT_ATELIER_VISIBLE_THRESHOLD", "visible_threshold", float),
            ("CONTENT_ATELIER_SIMILARITY_THRESHOLD", "similarity_threshold", float),
            ("CONTENT_ATELIER_CLOSE_THRESHOLD", "close_similarity_threshold", float),
            ("CONTENT_ATELIER_MAX_LLM_REQUEST_CHARACTERS", "max_llm_request_characters", int),
            ("CONTENT_ATELIER_LLM_COMPLETION_TOKENS", "llm_completion_tokens", int),
            ("CONTENT_ATELIER_REQUEST_TIMEOUT_SECONDS", "request_timeout_seconds", float),
        ]:
            if os.getenv(env):
                values[field] = cast(os.environ[env])
        values["live_enabled"] = os.getenv("CONTENT_ATELIER_LIVE", "false").lower() == "true"
        values["embeddings_enabled"] = os.getenv("CONTENT_ATELIER_EMBEDDINGS_ENABLED", "false").lower() == "true"
        values["llm_input_limits_enabled"] = os.getenv("CONTENT_ATELIER_LLM_INPUT_LIMITS_ENABLED", "true").lower() == "true"
        return cls(**values)
