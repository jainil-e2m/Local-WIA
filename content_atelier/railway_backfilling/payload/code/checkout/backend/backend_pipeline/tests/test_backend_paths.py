from pathlib import Path

from backend_pipeline import config
from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT, ROOT, Settings


def test_restructure_preserves_existing_datastore_and_transcript_root():
    assert ROOT.name == "backend_pipeline"
    assert ROOT.parent == BACKEND_ROOT
    assert BACKEND_ROOT.name == "backend"
    assert BACKEND_ROOT.parent == PROJECT_ROOT
    settings = Settings()
    assert settings.data_root == PROJECT_ROOT / "testing" / ".data"
    assert settings.transcript_root == BACKEND_ROOT / "zoom_backfill_meetings"


def test_backend_env_precedence_and_legacy_root_fallback(tmp_path: Path, monkeypatch):
    project = tmp_path / "project"
    backend = project / "backend"
    backend.mkdir(parents=True)
    (project / ".env").write_text(
        "OPENROUTER_MOMENTS_MODEL=legacy/moments\nOPENROUTER_ANGLES_MODEL=legacy/angles\n", encoding="utf-8"
    )
    (backend / ".env").write_text("OPENROUTER_MOMENTS_MODEL=backend/moments\n", encoding="utf-8")
    monkeypatch.setattr(config, "PROJECT_ROOT", project)
    monkeypatch.setattr(config, "BACKEND_ROOT", backend)
    for name in ("OPENROUTER_MOMENTS_MODEL", "OPENROUTER_ANGLES_MODEL", "OPENROUTER_MODEL"):
        monkeypatch.delenv(name, raising=False)
    # The loader deliberately sets process defaults; register their restoration
    # with monkeypatch before exercising it. No actual .env is opened.
    monkeypatch.setenv("OPENROUTER_MOMENTS_MODEL", "process/moments")
    monkeypatch.delenv("OPENROUTER_ANGLES_MODEL", raising=False)
    settings = Settings.from_env()
    assert settings.openrouter_moments_model == "process/moments"
    assert settings.openrouter_angles_model == "legacy/angles"
    monkeypatch.delenv("OPENROUTER_MOMENTS_MODEL")
    assert Settings.from_env().openrouter_moments_model == "backend/moments"
