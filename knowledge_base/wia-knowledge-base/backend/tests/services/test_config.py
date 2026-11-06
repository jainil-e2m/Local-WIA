"""PRODUCTION_MODE: one switch between on-demand local development and scheduled production intake."""
import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.config import ConfigError, Settings
from backend.routes.access import hash_password

REMOTE_DB = "postgresql+psycopg://kb:pw@db.internal-example.net:5432/kb"
PRODUCTION = dict(production_mode=True, database_url=REMOTE_DB, kb_secret_key="k", ops_token="t",
                  kb_team_password_hash=hash_password("team"))


@pytest.fixture(autouse=True)
def no_ambient_env(monkeypatch):
    """Only what each test passes counts: not the developer's .env, not the test runner's variables.
    DATABASE_URL stays: it points the shared engine at kb_test, and tests that care pass their own."""
    for name in Settings.model_fields:
        if name != "database_url":
            monkeypatch.delenv(name.upper(), raising=False)


def _settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


def test_local_is_the_default_and_runs_on_demand():
    s = _settings()
    assert (s.mode, s.environment, s.sync_scheduler_enabled) == ("local", "local", False)
    assert s.config_problems() == []


def test_production_mode_turns_the_scheduler_on():
    s = _settings(**PRODUCTION)
    assert (s.mode, s.environment, s.sync_scheduler_enabled) == ("production", "production", True)
    assert s.config_problems() == []


def test_staging_runs_in_production_mode():
    s = _settings(**PRODUCTION, environment="staging")
    assert s.environment == "staging" and s.sync_scheduler_enabled and s.config_problems() == []


def test_scheduler_can_be_paused_in_production_and_tried_locally():
    assert _settings(**PRODUCTION, sync_scheduler_enabled=False).sync_scheduler_enabled is False
    assert _settings(sync_scheduler_enabled=True).sync_scheduler_enabled is True


def test_production_mode_with_environment_local_is_refused():
    # ENVIRONMENT=local opens the unauthenticated local-only routes
    assert any("ENVIRONMENT" in p for p in _settings(**PRODUCTION, environment="local").config_problems())
    assert any("PRODUCTION_MODE=true" in p for p in _settings(environment="production").config_problems())
    assert _settings(environment="prod").config_problems() == ["ENVIRONMENT must be local, staging or production"]


def test_production_requirements_are_all_reported():
    problems = _settings(production_mode=True, database_url="postgresql+psycopg://kb:kb@localhost:5440/kb",
                         ingest_window_days=30).config_problems()
    assert [p.split()[0] for p in problems] == ["DATABASE_URL", "KB_SECRET_KEY", "OPS_TOKEN", "KB_TEAM_PASSWORD_HASH",
                                                 "INGEST_WINDOW_DAYS"]


def test_oauth_addresses_are_checked_only_for_configured_apps():
    assert _settings(**PRODUCTION).config_problems() == []  # neither app configured yet: localhost defaults are fine
    problems = _settings(**PRODUCTION, clickup_oauth_client_id="c", leadlock_app_client_id="l").config_problems()
    assert [p.split()[0] for p in problems] == ["KB_APP_URL", "CLICKUP_OAUTH_REDIRECT_URI", "LEADLOCK_REDIRECT_URI"]
    ok = _settings(**PRODUCTION, clickup_oauth_client_id="c", kb_app_url="https://kb.example.com",
                   clickup_oauth_redirect_uri="https://api.example.com/api/v1/clickup/oauth/callback")
    assert ok.config_problems() == []


def test_outbound_live_is_refused_outside_production():
    assert _settings(outbound_mode="live").config_problems() == ["OUTBOUND_MODE=live is refused outside PRODUCTION_MODE"]
    assert _settings(**PRODUCTION, outbound_mode="live").config_problems() == []
    assert _settings(outbound_mode="on").config_problems() == ["OUTBOUND_MODE must be off, sandbox or live"]


def test_refusal_names_settings_but_never_their_values(monkeypatch):
    secret_db = "postgresql+psycopg://kb:sup3r-secret@127.0.0.1:5440/kb"
    monkeypatch.setattr(config, "Settings", lambda: _settings(production_mode=True, database_url=secret_db,
                                                             kb_secret_key="fernet-secret-value"))
    with pytest.raises(ConfigError) as error:
        config.get_settings.__wrapped__()
    message = str(error.value)
    assert "DATABASE_URL" in message and "OPS_TOKEN" in message
    assert "sup3r-secret" not in message and "fernet-secret-value" not in message


def test_health_reports_the_mode():
    from backend.app import app
    body = TestClient(app).get("/health/ready").json()
    assert body["mode"] == "local" and body["environment"] == "local" and body["sync_scheduler"] is False


def test_railway_postgres_url_uses_the_installed_driver():
    for url in ("postgresql://u:p@db.internal-example.net:5432/railway", "postgres://u:p@db.internal-example.net:5432/railway"):
        assert _settings(database_url=url).database_url == "postgresql+psycopg://u:p@db.internal-example.net:5432/railway"
