"""Per-person ClickUp connections (S1): encrypted tokens, roster checks, no fallback identity."""
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from backend.config import get_settings
from backend.db import transaction
from backend.models.db.outbound import ClickUpConnection
from backend.services.outbound import clickup_oauth
from backend.services.people import roster
from backend.services.shared import secrets


@pytest.fixture(autouse=True)
def app_settings(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "kb_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(s, "clickup_oauth_client_id", "example-client-id")
    monkeypatch.setattr(s, "clickup_oauth_client_secret", "example-client-secret")
    monkeypatch.setattr(s, "clickup_team_id", "9000001")


class FakeClickUp:
    def __init__(self, user_id="10000001", teams=("9000001",), token_ok=True):
        self.user_id, self.teams, self.token_ok, self.calls = user_id, teams, token_ok, []

    def post(self, url, params=None, timeout=None):
        self.calls.append(("post", url, params))
        ok = params.get("code") == "good-code"
        return SimpleNamespace(status_code=200 if ok else 400,
                               json=lambda: {"access_token": "tok-example"} if ok else {"err": "bad"})

    def get(self, url, headers=None, timeout=None):
        self.calls.append(("get", url, headers))
        if not self.token_ok:
            return SimpleNamespace(status_code=401, json=lambda: {})
        if url.endswith("user"):
            return SimpleNamespace(status_code=200, json=lambda: {"user": {"id": self.user_id, "username": "Alex Example"}})
        return SimpleNamespace(status_code=200, json=lambda: {"teams": [{"id": t} for t in self.teams]})


@pytest.fixture
def alex():
    with transaction() as s:
        p = roster.create_person(s, name="Alex Example", kind="staff", actor="test")
        roster.add_address(s, p.id, "clickup_user", "10000001", actor="test")
        return p.id


def test_authorize_url_carries_app_redirect_and_state():
    url = clickup_oauth.authorize_url("st4te")
    assert url.startswith("https://app.clickup.com/api?") and "client_id=example-client-id" in url
    assert "state=st4te" in url and "redirect_uri=http" in url


def test_exchange_code_returns_token_or_refuses():
    assert clickup_oauth.exchange_code("good-code", FakeClickUp()) == "tok-example"
    with pytest.raises(clickup_oauth.ClickUpConnectError):
        clickup_oauth.exchange_code("bad-code", FakeClickUp())


def test_connect_stores_encrypted_token_for_the_roster_person(alex):
    with transaction() as s:
        conn = clickup_oauth.connect(s, "tok-example", actor="test", http=FakeClickUp())
        assert conn.person_id == alex and conn.workspace_ids == ["9000001"]
        assert conn.token_encrypted != "tok-example" and "tok-example" not in conn.token_encrypted
    with transaction() as s:
        assert clickup_oauth.token_for(s, alex) == "tok-example"


def test_reconnecting_replaces_the_previous_connection(alex):
    with transaction() as s:
        clickup_oauth.connect(s, "tok-example", actor="test", http=FakeClickUp())
    with transaction() as s:
        clickup_oauth.connect(s, "tok-example", actor="test", http=FakeClickUp())
    with transaction() as s:
        rows = s.execute(select(ClickUpConnection)).scalars().all()
        assert len(rows) == 2 and sum(r.revoked_at is None for r in rows) == 1


def test_refuses_users_not_on_roster_shared_logins_and_missing_workspace(alex):
    with transaction() as s:
        with pytest.raises(clickup_oauth.ClickUpConnectError, match="not on the KB roster"):
            clickup_oauth.connect(s, "tok", actor="test", http=FakeClickUp(user_id="10009999"))
        with pytest.raises(clickup_oauth.ClickUpConnectError, match="workspace"):
            clickup_oauth.connect(s, "tok", actor="test", http=FakeClickUp(teams=("1234",)))
        shared = roster.create_person(s, name="Example Support", kind="shared_mailbox", actor="test")
        roster.add_address(s, shared.id, "clickup_user", "10000002", actor="test")
        with pytest.raises(clickup_oauth.ClickUpConnectError, match="shared login"):
            clickup_oauth.connect(s, "tok", actor="test", http=FakeClickUp(user_id="10000002"))


def test_no_connection_means_blocked_and_rejected_tokens_are_revoked(alex):
    with transaction() as s:
        with pytest.raises(clickup_oauth.NotConnected):
            clickup_oauth.token_for(s, alex)
        clickup_oauth.connect(s, "tok-example", actor="test", http=FakeClickUp())
    with transaction() as s:
        with pytest.raises(clickup_oauth.ClickUpConnectError):
            clickup_oauth.verify(s, alex, http=FakeClickUp(token_ok=False))
    with transaction() as s:
        with pytest.raises(clickup_oauth.NotConnected):
            clickup_oauth.token_for(s, alex)


def test_disconnect_blocks_further_edits(alex):
    with transaction() as s:
        clickup_oauth.connect(s, "tok-example", actor="test", http=FakeClickUp())
        clickup_oauth.disconnect(s, alex, actor="test")
        with pytest.raises(clickup_oauth.NotConnected):
            clickup_oauth.token_for(s, alex)


def test_missing_secret_key_refuses_to_store(monkeypatch):
    monkeypatch.setattr(get_settings(), "kb_secret_key", None)
    with pytest.raises(secrets.SecretKeyMissing):
        secrets.encrypt("x")


# Production flow: API start + callback redirect back into the KB

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from backend.app import app
    monkeypatch.setattr(get_settings(), "kb_app_url", "https://kb.example.com")
    return TestClient(app, follow_redirects=False)


def _state_from(start_response):
    return parse_qs(urlparse(start_response.headers["location"]).query)["state"][0]


def test_start_sends_people_to_clickup_with_signed_state(client):
    r = client.get("/api/v1/clickup/oauth/start", params={"return_to": "/settings/connections"})
    assert r.status_code == 302 and r.headers["location"].startswith("https://app.clickup.com/api?")
    assert clickup_oauth.read_state(_state_from(r))["r"] == "/settings/connections"


def test_callback_connects_and_redirects_back_into_the_kb(client, alex, monkeypatch):
    fake = FakeClickUp()
    monkeypatch.setattr(clickup_oauth, "exchange_code", lambda code: "tok-example")
    real_connect = clickup_oauth.connect
    monkeypatch.setattr(clickup_oauth, "connect", lambda s, token, actor: real_connect(s, token, actor=actor, http=fake))
    state = _state_from(client.get("/api/v1/clickup/oauth/start", params={"return_to": "/settings"}))
    r = client.get("/api/v1/clickup/oauth/callback", params={"code": "good-code", "state": state})
    assert r.status_code == 302
    loc = urlparse(r.headers["location"])
    assert (loc.scheme, loc.netloc, loc.path) == ("https", "kb.example.com", "/settings")
    assert parse_qs(loc.query) == {"clickup": ["connected"], "as": ["Alex Example"]}
    with transaction() as s:
        assert clickup_oauth.token_for(s, alex) == "tok-example"


def test_callback_errors_return_to_the_kb_not_a_crash(client, alex, monkeypatch):
    r = client.get("/api/v1/clickup/oauth/callback", params={"code": "x", "state": "forged.state"})
    assert r.status_code == 302 and "reason=expired_or_invalid" in r.headers["location"]
    state = _state_from(client.get("/api/v1/clickup/oauth/start"))
    r = client.get("/api/v1/clickup/oauth/callback", params={"error": "access_denied", "state": state})
    assert "clickup=error" in r.headers["location"] and "reason=not_approved" in r.headers["location"]
    monkeypatch.setattr(clickup_oauth, "exchange_code", lambda code: "tok-example")
    real_connect = clickup_oauth.connect
    monkeypatch.setattr(clickup_oauth, "connect",
                        lambda s, token, actor: real_connect(s, token, actor=actor, http=FakeClickUp(user_id="10009999")))
    r = client.get("/api/v1/clickup/oauth/callback", params={"code": "good-code", "state": state})
    assert "reason=not_on_roster" in r.headers["location"]


@pytest.mark.parametrize("bad", ["https://evil.example.org/x", "//evil.example.org", "settings", None])
def test_return_path_never_leaves_the_kb(bad):
    assert clickup_oauth.safe_return_path(bad) == "/"


def test_expired_state_is_refused(monkeypatch):
    state = clickup_oauth.make_state("/x")
    monkeypatch.setattr(clickup_oauth.time, "time", lambda: 10**12)
    with pytest.raises(clickup_oauth.ClickUpConnectError, match="expired"):
        clickup_oauth.read_state(state)
