from pathlib import Path

import pytest

from backend_pipeline import config
from backend_pipeline.config import Settings

APODEX = "apodex/apodex-1.1-mini:free"
LUNA = "openai/gpt-6-luna"
ENV_NAMES = (
    "OPENROUTER_API_KEY",
    "OPENROUTER_MOMENTS_KEY",
    "OPENROUTER_ANGLES_KEY",
    "OPENROUTER_MOMENTS_MODEL",
    "OPENROUTER_ANGLES_MODEL",
    "OPENROUTER_MODEL",
    "EMBEDDING_API_KEY",
    "OPENAI_API_KEY",
    "CONTENT_ATELIER_LIVE",
    "CONTENT_ATELIER_EMBEDDINGS_ENABLED",
    "CONTENT_ATELIER_LLM_INPUT_LIMITS_ENABLED",
    "CONTENT_ATELIER_LLM_COMPLETION_TOKENS",
)


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch):
    project = tmp_path / "project"
    backend = project / "backend"
    backend.mkdir(parents=True)
    monkeypatch.setattr(config, "PROJECT_ROOT", project)
    monkeypatch.setattr(config, "BACKEND_ROOT", backend)
    for name in ENV_NAMES:
        # Register restoration even when the name was absent before dotenv
        # loading; tests never load the actual private backend/.env file.
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)
    return backend


def test_luna_defaults_preserve_live_embedding_and_size_safeguards():
    settings = Settings()
    assert settings.openrouter_moments_model == LUNA
    assert settings.openrouter_angles_model == LUNA
    assert settings.live_enabled is False
    assert settings.embeddings_enabled is False
    assert settings.max_llm_request_characters == 120000
    assert settings.llm_input_limits_enabled is True
    assert settings.embedding_dimensions == 1536


def test_one_shared_free_key_resolves_both_stages_not_embeddings(isolated_env):
    (isolated_env / ".env").write_text(
        "OPENROUTER_API_KEY=synthetic-free-key\n"
        "OPENROUTER_MOMENTS_KEY=\nOPENROUTER_ANGLES_KEY=\n"
        "EMBEDDING_API_KEY=synthetic-paid-key\n",
        encoding="utf-8",
    )
    settings = Settings.from_env()
    assert settings.openrouter_moments_key == settings.openrouter_angles_key == "synthetic-free-key"
    assert settings.embedding_api_key == "synthetic-paid-key"
    settings.validate_live()


def test_explicit_stage_key_overrides_shared_key(isolated_env):
    (isolated_env / ".env").write_text(
        "OPENROUTER_API_KEY=synthetic-shared-key\nOPENROUTER_MOMENTS_KEY=synthetic-moments-key\n",
        encoding="utf-8",
    )
    settings = Settings.from_env()
    assert settings.openrouter_moments_key == "synthetic-moments-key"
    assert settings.openrouter_angles_key == "synthetic-shared-key"
    assert settings.embedding_api_key is None


def test_shared_free_key_cannot_satisfy_embedding_requirement(isolated_env):
    (isolated_env / ".env").write_text("OPENROUTER_API_KEY=synthetic-free-key\n", encoding="utf-8")
    settings = Settings.from_env()
    settings.embeddings_enabled = True
    with pytest.raises(RuntimeError, match=r"Missing live configuration: EMBEDDING_API_KEY$"):
        settings.validate_live()


def test_blank_template_keys_fail_before_provider_selection(isolated_env):
    (isolated_env / ".env").write_text(
        "OPENROUTER_API_KEY=\nOPENROUTER_MOMENTS_KEY=\nOPENROUTER_ANGLES_KEY=\nEMBEDDING_API_KEY=\n",
        encoding="utf-8",
    )
    settings = Settings.from_env()
    assert settings.openrouter_moments_key is None
    assert settings.openrouter_angles_key is None
    assert settings.embedding_api_key is None
    with pytest.raises(RuntimeError, match="OPENROUTER_MOMENTS_KEY, OPENROUTER_ANGLES_KEY"):
        settings.validate_live()


def test_model_environment_overrides_remain_configurable(isolated_env):
    (isolated_env / ".env").write_text(
        "OPENROUTER_MOMENTS_MODEL=synthetic/moments\nOPENROUTER_ANGLES_MODEL=synthetic/angles\n",
        encoding="utf-8",
    )
    settings = Settings.from_env()
    assert settings.openrouter_moments_model == "synthetic/moments"
    assert settings.openrouter_angles_model == "synthetic/angles"


def test_uncapped_env_omits_output_reserve_and_disables_input_gate(isolated_env):
    (isolated_env / ".env").write_text(
        "CONTENT_ATELIER_LLM_COMPLETION_TOKENS=\nCONTENT_ATELIER_LLM_INPUT_LIMITS_ENABLED=false\n", encoding="utf-8"
    )
    settings = Settings.from_env()
    assert settings.llm_completion_tokens is None and settings.llm_input_limits_enabled is False
    assert settings.embeddings_enabled is False and settings.live_enabled is False
