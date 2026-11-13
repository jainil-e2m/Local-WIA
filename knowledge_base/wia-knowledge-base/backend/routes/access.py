"""Who may reach the portfolio and its API.

- **Command Center sign-in** (COMMAND_CENTER_* set; production): the person's own Command Center session, the
  same as the Content Atelier's. Its token arrives once through the sign-in hand-off (routes/auth.py) and is kept
  in this host's `wahha_session` cookie; every request is checked with Command Center (`/api/auth/session`), at
  most every SESSION_RECHECK seconds per token, so a sign-out or a removed account takes effect within that.
  Team accounts only. The signed-in person is the actor on every change (`actor()`), whatever the app sends.
- **Shared team password** (fallback where Command Center isn't configured): HTTP Basic, any user name, checked
  against KB_TEAM_PASSWORD_HASH.
- **Local** (ENVIRONMENT=local, neither set): everything is open, as before.

Always open: the signed provider callbacks, the ops API (its own token), health checks and the sign-in hand-off.
"""
import base64
import binascii
import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque
from contextvars import ContextVar
from urllib.parse import quote

import httpx
from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, RedirectResponse, Response

from backend.config import get_settings

OPEN_PATHS = ("/health/", "/api/v1/leadlock/webhooks", "/api/v1/leadlock/oauth/callback",
              "/api/v1/clickup/oauth/callback", "/api/v1/ops/", "/api/auth/sso/", "/api/auth/signout")
SESSION_COOKIE = "wahha_session"  # Command Center's cookie name; this host holds the same token
TOKEN = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
SESSION_RECHECK = 30  # seconds a checked session is trusted before Command Center is asked again
current_user: ContextVar[dict | None] = ContextVar("kb_user", default=None)
# shortcut: in this process's memory, right while the web service runs one process (as the Atelier's hand-off).
_sessions: dict[str, tuple[dict | None, float]] = {}  # sha256(token) -> (user or None, checked at)


class AuthUnavailable(Exception):
    """Command Center couldn't say whether the session is valid: refuse (503), never guess."""


async def session_user(token: str | None) -> dict | None:
    """The Command Center user behind a session token, or None (missing, malformed, expired, revoked)."""
    if not token or len(token) > 4096 or not TOKEN.match(token):
        return None
    key, now = hashlib.sha256(token.encode()).hexdigest(), time.monotonic()
    hit = _sessions.get(key)
    if hit and now - hit[1] < SESSION_RECHECK:
        return hit[0]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{get_settings().command_center_auth_origin.rstrip('/')}/api/auth/session",
                                 headers={"cookie": f"{SESSION_COOKIE}={token}", "accept": "application/json"})
    except httpx.HTTPError:
        raise AuthUnavailable() from None
    if r.status_code == 401:
        user = None
    elif r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
        u = (r.json() or {}).get("user") or {}
        if not (isinstance(u.get("email"), str) and isinstance(u.get("name"), str) and u.get("role") in ("team", "client")):
            raise AuthUnavailable()
        user = {"email": u["email"], "name": u["name"], "role": u["role"]}
    else:
        raise AuthUnavailable()
    if len(_sessions) > 1000:
        _sessions.clear()
    _sessions[key] = (user, now)
    return user


def forget_session(token: str | None) -> None:
    if token:
        _sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)
SCRYPT = {"n": 2**14, "r": 8, "p": 1}
MAX_FAILURES, FAILURE_WINDOW = 10, 15 * 60
SHARED_ACTOR = "team (shared login)"

# shortcut: both live in this process's memory, which is right while the web service runs one process.
# Move them to Postgres if it ever runs several.
_accepted: set[str] = set()  # sha256 of Authorization headers that already passed (skips scrypt per request)
_failures: dict[str, deque] = defaultdict(deque)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def valid_hash(stored: str) -> bool:
    parts = stored.split("$")
    try:
        return len(parts) == 3 and parts[0] == "scrypt" and all(base64.b64decode(p, validate=True) for p in parts[1:])
    except (binascii.Error, ValueError):
        return False


def check_password(password: str, stored: str) -> bool:
    _, salt, digest = stored.split("$")
    actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), **SCRYPT)
    return hmac.compare_digest(actual, base64.b64decode(digest))


def _password(header: str) -> str | None:
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "basic":
        return None
    try:
        return base64.b64decode(value, validate=True).decode().partition(":")[2]
    except (binascii.Error, UnicodeDecodeError):
        return None


def _client_ip(request: Request) -> str:
    # Railway's edge appends the caller to X-Forwarded-For; earlier hops can be forged by the caller.
    forwarded = request.headers.get("x-forwarded-for", "")
    return request.headers.get("x-real-ip") or (forwarded.split(",")[-1].strip() if forwarded else "") or \
        (request.client.host if request.client else "unknown")


async def gate(request: Request, call_next):
    settings = get_settings()
    if request.url.path.startswith(OPEN_PATHS):
        return await call_next(request)
    if settings.sso_enabled:
        return await _command_center_gate(request, call_next)
    stored = settings.kb_team_password_hash
    if not stored:
        return await call_next(request)
    header = request.headers.get("authorization", "")
    key = hashlib.sha256(header.encode()).hexdigest()
    if header and key in _accepted:
        return await call_next(request)
    ip, now = _client_ip(request), time.monotonic()
    recent = _failures[ip]
    while recent and now - recent[0] > FAILURE_WINDOW:
        recent.popleft()
    if len(recent) >= MAX_FAILURES:
        return JSONResponse({"detail": {"code": "too_many_attempts"}}, status_code=429)
    password = _password(header)
    if password is not None and await run_in_threadpool(check_password, password, stored):
        if len(_accepted) > 1000:
            _accepted.clear()
        _accepted.add(key)
        return await call_next(request)
    if header:
        recent.append(now)  # the browser's first request carries no credentials: not an attempt
    return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="WIA Client Portfolio", charset="UTF-8"'})


async def _command_center_gate(request: Request, call_next):
    path = request.url.path
    try:
        user = await session_user(request.cookies.get(SESSION_COOKIE))
    except AuthUnavailable:
        return JSONResponse({"detail": {"code": "auth_unavailable",
                                        "message": "Command Center sign-in is unavailable. Please retry."}}, status_code=503)
    if user is None:
        if path.startswith("/api/"):
            return JSONResponse({"detail": {"code": "signed_out", "message": "Your session ended. Sign in again."}},
                                status_code=401)
        # A page: sign in through Command Center and come back to it (the #route survives the redirects).
        back = path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(f"/api/auth/sso/start?returnTo={quote(back, safe='')}", status_code=302)
    if user["role"] != "team":
        return JSONResponse({"detail": {"code": "team_only", "message": "The Knowledge Base is for the WIA team."}},
                            status_code=403)
    reset = current_user.set(user)
    try:
        return await call_next(request)
    finally:
        current_user.reset(reset)


def require_team() -> None:
    """Team-only routes: open locally; elsewhere only behind the gate (the middleware has already checked)."""
    settings = get_settings()
    if settings.environment != "local" and not settings.kb_team_password_hash and not settings.sso_enabled:
        raise HTTPException(status_code=404, detail={"code": "local_only"})


def actor() -> str:
    """Who made a change: the signed-in Command Center person when there is one (never what the app claims)."""
    user = current_user.get()
    if user:
        return f"{user['name']} <{user['email']}>"[:200]
    return "kb-ui (local, no login yet)" if get_settings().environment == "local" else SHARED_ACTOR
