"""Per-person ClickUp connections through the "WIA Knowledge Base" OAuth app (S1).

Each KB user connects their own ClickUp account once; their edits are then made with their own token, so
ClickUp shows their name. There is no fallback identity: without an active connection, ClickUp edits are
refused for that person (decided 29 Oct). Tokens are stored encrypted and never logged.
"""
import base64
import hashlib
import hmac
import json
import secrets as pysecrets
import time
from urllib.parse import urlencode

import httpx
from sqlalchemy import select

from backend.config import get_settings
from backend.models.db import AuditEvent
from backend.models.db.base import utcnow
from backend.models.db.outbound import ClickUpConnection
from backend.models.db.people import Person, PersonAddress
from backend.services.shared.secrets import decrypt, encrypt

AUTHORIZE_URL = "https://app.clickup.com/api"
API = "https://api.clickup.com/api/v2/"


class ClickUpConnectError(RuntimeError):
    pass


class NotConnected(ClickUpConnectError):
    """The person has no active ClickUp connection: their ClickUp edits are blocked."""


def _app():
    s = get_settings()
    if not s.clickup_oauth_client_id or not s.clickup_oauth_client_secret:
        raise ClickUpConnectError("CLICKUP_OAUTH_CLIENT_ID / CLICKUP_OAUTH_CLIENT_SECRET are not configured")
    return s


def authorize_url(state: str) -> str:
    s = _app()
    return AUTHORIZE_URL + "?" + urlencode({"client_id": s.clickup_oauth_client_id,
                                            "redirect_uri": s.clickup_oauth_redirect_uri, "state": state})


STATE_TTL_SECONDS = 600


def _state_key() -> bytes:
    key = get_settings().kb_secret_key
    if not key:
        raise ClickUpConnectError("KB_SECRET_KEY is not set")
    return hashlib.sha256(b"clickup-oauth-state:" + key.encode()).digest()


def safe_return_path(path: str | None) -> str:
    """Only a path inside the KB app: never another site (no open redirect)."""
    if not path or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/"
    return path


def make_state(return_to: str | None = None) -> str:
    """Signed, short-lived state: proves the callback answers a start we issued, and carries where to return."""
    body = base64.urlsafe_b64encode(json.dumps({"n": pysecrets.token_urlsafe(12), "r": safe_return_path(return_to),
                                                 "e": int(time.time()) + STATE_TTL_SECONDS}).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(hmac.new(_state_key(), body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{body}.{sig}"


def read_state(state: str | None) -> dict:
    try:
        body, sig = (state or "").split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(_state_key(), body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(sig, expected):
            raise ValueError
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except (ValueError, json.JSONDecodeError):
        raise ClickUpConnectError("invalid sign-in state; start the connection again") from None
    if data.get("e", 0) < time.time():
        raise ClickUpConnectError("the connection attempt expired; start it again")
    return data


def exchange_code(code: str, http=httpx) -> str:
    s = _app()
    r = http.post(API + "oauth/token", params={"client_id": s.clickup_oauth_client_id,
                                               "client_secret": s.clickup_oauth_client_secret, "code": code},
                  timeout=s.http_timeout_seconds)
    if r.status_code != 200 or "access_token" not in r.json():
        raise ClickUpConnectError(f"ClickUp refused the authorization code (HTTP {r.status_code})")
    return r.json()["access_token"]


def whoami(token: str, http=httpx) -> tuple[dict, list[str]]:
    """The ClickUp user behind a token, and the workspaces it was granted."""
    headers, timeout = {"Authorization": token}, get_settings().http_timeout_seconds
    user = http.get(API + "user", headers=headers, timeout=timeout)
    if user.status_code != 200:
        raise ClickUpConnectError(f"ClickUp token is not valid (HTTP {user.status_code})")
    teams = http.get(API + "team", headers=headers, timeout=timeout).json().get("teams", [])
    return user.json()["user"], [str(t["id"]) for t in teams]


def connect(s, token: str, *, actor: str, http=httpx) -> ClickUpConnection:
    """Store a person's connection after checking who the token belongs to.

    The ClickUp user must already be on the roster (a clickup_user address) and must have granted the WIA
    workspace. Any earlier active connection for that person is revoked."""
    user, workspaces = whoami(token, http)
    team_id = str(get_settings().clickup_team_id or "")
    if team_id and team_id not in workspaces:
        raise ClickUpConnectError("the WIA workspace was not selected when authorizing; connect again and tick it")
    user_id = str(user["id"])
    person = s.execute(select(Person).join(PersonAddress, PersonAddress.person_id == Person.id).where(
        PersonAddress.kind == "clickup_user", PersonAddress.value == user_id)).scalar_one_or_none()
    if person is None:
        raise ClickUpConnectError(f"ClickUp user {user.get('username') or user_id} is not on the KB roster; add them first")
    if person.kind == "shared_mailbox":
        raise ClickUpConnectError("a shared login (e.g. WIA Support) cannot be connected: edits must carry a person's name")
    now = utcnow()
    for old in s.execute(select(ClickUpConnection).where(ClickUpConnection.person_id == person.id,
                                                         ClickUpConnection.revoked_at.is_(None))).scalars():
        old.revoked_at, old.revoked_reason = now, "replaced by a new connection"
    s.flush()
    conn = ClickUpConnection(person_id=person.id, clickup_user_id=user_id, clickup_username=user.get("username"),
                             workspace_ids=workspaces, token_encrypted=encrypt(token), connected_by=actor,
                             connected_at=now, last_verified_at=now)
    s.add(conn)
    s.add(AuditEvent(actor=actor, action="clickup.connect", target_type="person", target_id=str(person.id),
                     details={"clickup_user_id": user_id, "workspaces": workspaces}))
    s.flush()
    return conn


def active_connection(s, person_id) -> ClickUpConnection:
    conn = s.execute(select(ClickUpConnection).where(ClickUpConnection.person_id == person_id,
                                                     ClickUpConnection.revoked_at.is_(None))).scalar_one_or_none()
    if conn is None:
        raise NotConnected("this person has not connected ClickUp; their ClickUp edits are blocked")
    return conn


def token_for(s, person_id) -> str:
    return decrypt(active_connection(s, person_id).token_encrypted)


def verify(s, person_id, http=httpx) -> ClickUpConnection:
    """Re-check a stored token. A token ClickUp rejects is revoked, which blocks that person's edits."""
    conn = active_connection(s, person_id)
    try:
        whoami(decrypt(conn.token_encrypted), http)
    except ClickUpConnectError:
        conn.revoked_at, conn.revoked_reason = utcnow(), "rejected by ClickUp"
        raise
    conn.last_verified_at = utcnow()
    return conn


def disconnect(s, person_id, *, actor: str, reason: str = "disconnected by admin") -> None:
    conn = active_connection(s, person_id)
    conn.revoked_at, conn.revoked_reason = utcnow(), reason
    s.add(AuditEvent(actor=actor, action="clickup.disconnect", target_type="person", target_id=str(person_id),
                     details={"reason": reason}))
