"""Interim shared team password: HTTP Basic in front of everything except signed callbacks, ops and health."""
import base64

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, get_settings
from backend.routes import access

HASH = access.hash_password("orchid-lantern-42")


def basic(password, user="team"):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


@pytest.fixture
def gated(monkeypatch):
    monkeypatch.setattr(get_settings(), "kb_team_password_hash", HASH)
    monkeypatch.setattr(get_settings(), "environment", "staging")
    access._accepted.clear()
    access._failures.clear()
    from backend.app import app
    return TestClient(app)


def test_hash_round_trip():
    assert access.valid_hash(HASH) and not access.valid_hash("orchid-lantern-42")
    assert access.check_password("orchid-lantern-42", HASH) and not access.check_password("wrong", HASH)
    assert access.hash_password("x") != access.hash_password("x")  # salted


def test_team_routes_need_the_password(gated):
    r = gated.get("/api/v1/connections/clients")
    assert r.status_code == 401 and r.headers["www-authenticate"].startswith("Basic")
    assert gated.get("/api/v1/connections/clients", headers=basic("wrong")).status_code == 401
    assert gated.get("/api/v1/clients/nobody/leads", headers=basic("orchid-lantern-42", user="anyone")).status_code == 404


def test_callbacks_ops_and_health_stay_reachable(gated):
    assert gated.get("/health/live").status_code == 200
    r = gated.get("/api/v1/ops/runs")
    assert "www-authenticate" not in r.headers  # the ops API answers with its own token check
    r = gated.post("/api/v1/leadlock/webhooks", content=b"{}")
    assert r.status_code == 401 and r.json() == {"code": "bad_signature"}


def test_repeated_wrong_passwords_are_throttled(gated):
    for _ in range(access.MAX_FAILURES):
        assert gated.get("/api/v1/connections/clients", headers=basic("guess")).status_code == 401
    assert gated.get("/api/v1/connections/clients", headers=basic("orchid-lantern-42")).status_code == 429


def test_production_refuses_to_start_without_the_hash():
    s = Settings(production_mode=True, database_url="postgresql+psycopg://kb:kb@db.internal:5432/kb",
                 kb_secret_key="k", ops_token="t", _env_file=None)
    # Production needs a way in: Command Center sign-in or the shared password (test_command_center_sso.py)
    assert any("Sign-in is required" in p and "KB_TEAM_PASSWORD_HASH" in p for p in s.config_problems())
    s = Settings(kb_team_password_hash="plain-text", _env_file=None)
    assert "KB_TEAM_PASSWORD_HASH is not a hash from `kb password-hash`" in s.config_problems()
