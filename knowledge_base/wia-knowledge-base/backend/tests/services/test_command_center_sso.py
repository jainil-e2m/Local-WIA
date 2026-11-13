"""Sign-in through Command Center, as the Content Atelier does: PKCE hand-off, session checks, one sign-out."""
import hashlib
from base64 import urlsafe_b64encode
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, get_settings
from backend.routes import access, auth
from backend.services.clients import mapping
from backend.db import transaction

CC_AUTH, CC_PUBLIC, KB = "http://cc.internal", "https://cc.example.com", "https://kb.example.com"
TOKEN = "eyJlbWFpbCI6IngifQ.c2lnbmF0dXJl"
USER = {"email": "jainil@agency.example", "name": "Jainil Trivedi", "role": "team"}


class FakeCommandCenter:
    """Answers the three Command Center endpoints the Knowledge Base calls."""

    def __init__(self):
        self.sessions = {TOKEN: USER}
        self.codes, self.logouts = {}, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        cookie = request.headers.get("cookie", "").removeprefix("wahha_session=")
        if path == "/api/auth/session":
            user = self.sessions.get(cookie)
            return httpx.Response(200, json={"user": user}) if user else httpx.Response(401, json={"error": "no"})
        if path == "/api/auth/knowledge-base/exchange":
            body = httpx.Request("POST", "/", content=request.content).read()
            import json
            data = json.loads(body)
            challenge = self.codes.pop(data["code"], None)
            proof = urlsafe_b64encode(hashlib.sha256(data["code_verifier"].encode()).digest()).decode().rstrip("=")
            if challenge != proof or data["redirect_uri"] != f"{KB}/api/auth/sso/callback":
                return httpx.Response(401, json={"error": "bad proof"})
            return httpx.Response(200, json={"sessionToken": TOKEN, "expiresIn": 3600, "user": USER})
        if path == "/api/auth/logout":
            self.logouts.append(cookie)
            self.sessions.pop(cookie, None)
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)


@pytest.fixture
def cc(monkeypatch):
    fake = FakeCommandCenter()
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(fake), **kw))
    s = get_settings()
    monkeypatch.setattr(s, "command_center_auth_origin", CC_AUTH)
    monkeypatch.setattr(s, "command_center_public_origin", CC_PUBLIC)
    monkeypatch.setattr(s, "kb_app_url", KB)
    access._sessions.clear()
    auth._pending.clear()
    with transaction() as session:
        mapping.create_client(session, name="Venue One", slug="venue-one", actor="t", discover=False)
    return fake


def client():
    from backend.app import app
    return TestClient(app, base_url=KB, follow_redirects=False)


def sign_in(c, fake, return_to="/"):
    start = c.get("/api/auth/sso/start", params={"returnTo": return_to})
    q = parse_qs(urlparse(start.headers["location"]).query)
    fake.codes["C" * 43] = q["code_challenge"][0]
    return start, c.get("/api/auth/sso/callback", params={"state": q["state"][0], "code": "C" * 43})


def test_start_sends_the_browser_to_command_center_with_a_pkce_challenge_and_no_secret(cc):
    start = client().get("/api/auth/sso/start", params={"returnTo": "/clients"})
    url = urlparse(start.headers["location"])
    q = parse_qs(url.query)
    assert start.status_code == 302 and f"{url.scheme}://{url.netloc}{url.path}" == f"{CC_PUBLIC}/api/auth/knowledge-base/authorize"
    assert q["redirect_uri"] == [f"{KB}/api/auth/sso/callback"] and q["code_challenge_method"] == ["S256"]
    assert len(q["code_challenge"][0]) == 43 and "kb_sso_state" in start.headers["set-cookie"]
    verifier = next(iter(auth._pending.values()))[0]
    assert verifier not in start.headers["location"]  # the verifier never leaves the server


def test_a_completed_sign_in_keeps_the_session_cookie_and_returns_to_the_page(cc):
    c = client()
    _, done = sign_in(c, cc, "/clients")
    assert done.status_code == 302 and done.headers["location"] == "/clients"
    assert f"wahha_session={TOKEN}" in done.headers["set-cookie"] and "HttpOnly" in done.headers["set-cookie"]
    me = c.get("/api/auth/session").json()
    assert me == {"user": USER, "signIn": "command-center", "rbac": False, "viewAs": "Whitney"}


def test_a_forged_or_replayed_callback_is_refused(cc):
    c = client()
    start = c.get("/api/auth/sso/start")
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    assert c.get("/api/auth/sso/callback", params={"state": "x" * 43, "code": "C" * 43}).status_code == 400
    assert c.get("/api/auth/sso/callback", params={"state": state, "code": "C" * 43}).status_code == 502  # no such code
    assert c.get("/api/auth/sso/callback", params={"state": state, "code": "C" * 43}).status_code == 400  # one use


def test_the_gate_asks_command_center_and_sends_pages_to_sign_in(cc):
    c = client()
    assert c.get("/api/v1/edits").status_code == 401
    page = c.get("/clients")
    assert page.status_code == 302 and page.headers["location"] == "/api/auth/sso/start?returnTo=%2Fclients"
    c.cookies.set("wahha_session", TOKEN)
    assert c.get("/api/v1/edits").status_code == 200
    cc.sessions[TOKEN] = {**USER, "role": "client"}
    access._sessions.clear()
    assert c.get("/api/v1/edits").status_code == 403  # team only
    cc.sessions.pop(TOKEN)
    access._sessions.clear()
    assert c.get("/api/v1/edits").status_code == 401  # revoked at Command Center


def test_a_change_is_recorded_as_the_signed_in_person_not_who_the_app_names(cc):
    c = client()
    c.cookies.set("wahha_session", TOKEN)
    saved = c.put("/api/v1/edits/client/venue-one", json={"changes": {"archived": True}, "viewer": "Whitney"})
    assert saved.json()["by"] == "Jainil Trivedi <jainil@agency.example>"


def test_sign_out_revokes_at_command_center_and_passes_through_its_sign_out(cc):
    c = client()
    c.cookies.set("wahha_session", TOKEN)
    out = c.get("/api/auth/signout")
    assert out.headers["location"] == f"{CC_PUBLIC}/api/auth/signout?from=knowledge-base"
    assert cc.logouts == [TOKEN] and 'wahha_session=""' in out.headers["set-cookie"]
    assert c.get("/api/auth/signout", params={"from": "command-center"}).headers["location"] == f"{CC_PUBLIC}/login"


@pytest.mark.parametrize("value", ["//evil.example/x", "https://evil.example", "/api/auth/signout", "/\\evil", "x"])
def test_return_paths_never_leave_this_host(value):
    assert auth.local_return_to(value) == "/"
    assert auth.local_return_to("/clients?tab=now") == "/clients?tab=now"


def test_production_accepts_command_center_sign_in_without_a_password():
    base = dict(_env_file=None, production_mode=True, database_url="postgresql://u:p@db.example:5432/kb",
                kb_secret_key="k", ops_token="t", kb_app_url=KB)
    assert Settings(**base, command_center_auth_origin=CC_AUTH, command_center_public_origin=CC_PUBLIC).config_problems() == []
    half = Settings(**base, command_center_public_origin=CC_PUBLIC).config_problems()
    assert any("both COMMAND_CENTER_AUTH_ORIGIN" in p for p in half) and any("Sign-in is required" in p for p in half)
    plain_http = Settings(**base, command_center_auth_origin=CC_AUTH, command_center_public_origin="http://cc.example.com")
    assert any("COMMAND_CENTER_PUBLIC_ORIGIN must be" in p for p in plain_http.config_problems())
