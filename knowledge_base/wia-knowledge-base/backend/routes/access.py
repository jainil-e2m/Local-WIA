"""Who may reach the portfolio and its API.

Interim (decided 6 Nov): one shared team password, sent as HTTP Basic auth (any user name), checked against
KB_TEAM_PASSWORD_HASH. Named Google sign-in with roles replaces it; until then nobody can approve AI actions.

- Local (ENVIRONMENT=local, no hash set): everything is open, as before.
- Anywhere else the hash is required (config_problems), and every path except the signed provider callbacks,
  the ops API (its own token) and health checks needs the password.
"""
import base64
import binascii
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from backend.config import get_settings

OPEN_PATHS = ("/health/", "/api/v1/leadlock/webhooks", "/api/v1/leadlock/oauth/callback",
              "/api/v1/clickup/oauth/callback", "/api/v1/ops/")
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
    stored = get_settings().kb_team_password_hash
    if not stored or request.url.path.startswith(OPEN_PATHS):
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


def require_team() -> None:
    """Team-only routes: open locally; elsewhere only behind the gate (the middleware has already checked)."""
    settings = get_settings()
    if settings.environment != "local" and not settings.kb_team_password_hash:
        raise HTTPException(status_code=404, detail={"code": "local_only"})


def actor() -> str:
    return "kb-ui (local, no login yet)" if get_settings().environment == "local" else SHARED_ACTOR
