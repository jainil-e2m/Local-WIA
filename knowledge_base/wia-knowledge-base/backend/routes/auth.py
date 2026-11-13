"""Sign-in through Command Center: the same hand-off the Content Atelier uses (its frontend/server/sso.mjs).

Command Center's "View Here" for the Knowledge Base opens /api/auth/knowledge-base/launch there, which sends the
browser here to /api/auth/sso/start. This host then:
1. keeps a random `state` (in a short-lived HttpOnly cookie and here) and a PKCE verifier (here only), and sends
   the browser to Command Center's /api/auth/knowledge-base/authorize with the verifier's S256 challenge;
2. on /api/auth/sso/callback, checks the state, and trades the one-use 60-second code for the session token on
   the server backchannel (/api/auth/knowledge-base/exchange), proving the verifier;
3. keeps that token in its own `wahha_session` cookie (HttpOnly, SameSite=Lax, Secure in production), with the
   session's own expiry, and returns to the page that was asked for.

No token, verifier or identity ever travels in a browser URL. Sign-out revokes the token at Command Center (both
apps hold the same one) and passes the browser through Command Center's sign-out, which clears its own cookie and
the Atelier's.

shortcut: pending sign-ins live in this process's memory, which is right while the web service runs one process
(the Atelier's prototype has the same limit). Move them to Postgres if the web service ever runs several.
"""
import hashlib
import re
import secrets
import time
from base64 import urlsafe_b64encode
from urllib.parse import unquote, urlencode, urlparse

import httpx
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse

from backend.config import get_settings
from backend.routes import access

router = APIRouter()
STATE_COOKIE, STATE_PATH = "kb_sso_state", "/api/auth/sso"
LIFETIME = 180  # seconds a started sign-in may take
CODE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_pending: dict[str, tuple[str, str, float]] = {}  # state -> (verifier, return path, expires at)
NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


def local_return_to(value: str | None) -> str:
    """A path on this host to return to after sign-in, never another site, the sign-in routes or a protocol trick."""
    if not value or not value.startswith("/") or value.startswith("//") or re.search(r"[\\\r\n]", value):
        return "/"
    decoded = unquote(value.split("?")[0])
    if decoded.startswith("//") or re.search(r"[\\\r\n]", decoded) or decoded.startswith("/api/auth/"):
        return "/"
    url = urlparse(value)
    return value if not url.scheme and not url.netloc else "/"


def _callback() -> str:
    return get_settings().kb_app_url.rstrip("/") + "/api/auth/sso/callback"


def _cookie_secure() -> bool:
    return get_settings().production_mode


def _purge() -> None:
    now = time.monotonic()
    for state in [s for s, (_, _, expires) in _pending.items() if expires <= now]:
        _pending.pop(state, None)


@router.get("/sso/start")
def start(request: Request, returnTo: str | None = None):  # noqa: N803 — the Atelier's parameter name
    settings = get_settings()
    if not settings.sso_enabled:
        return PlainTextResponse("Command Center sign-in isn't configured for this Knowledge Base.", status_code=503,
                                 headers=NO_STORE)
    _purge()
    previous = request.cookies.get(STATE_COOKIE)
    if previous:
        _pending.pop(previous, None)
    if len(_pending) >= 1000:
        return PlainTextResponse("Sign-in is busy. Please retry shortly.", status_code=503, headers=NO_STORE)
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    _pending[state] = (verifier, local_return_to(returnTo), time.monotonic() + LIFETIME)
    challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    query = urlencode({"redirect_uri": _callback(), "state": state, "code_challenge": challenge,
                       "code_challenge_method": "S256"})
    response = RedirectResponse(f"{settings.command_center_public_origin.rstrip('/')}/api/auth/knowledge-base/authorize?{query}",
                                status_code=302, headers=NO_STORE)
    response.set_cookie(STATE_COOKIE, state, max_age=LIFETIME, path=STATE_PATH, httponly=True, samesite="lax",
                        secure=_cookie_secure())
    return response


@router.get("/sso/callback")
async def callback(request: Request, state: str | None = None, code: str | None = None):
    _purge()
    browser_state = request.cookies.get(STATE_COOKIE)
    if not state or not browser_state or state != browser_state or not code or not CODE.match(code):
        return PlainTextResponse("Sign-in could not be verified. Open the Knowledge Base from Command Center again.",
                                 status_code=400, headers=NO_STORE)
    pending = _pending.pop(state, None)
    if pending is None:
        return PlainTextResponse("Sign-in expired or was already completed. Open the Knowledge Base again.",
                                 status_code=400, headers=NO_STORE)
    verifier, return_to, _ = pending
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            r = await client.post(f"{settings.command_center_auth_origin.rstrip('/')}/api/auth/knowledge-base/exchange",
                                  json={"code": code, "redirect_uri": _callback(), "code_verifier": verifier},
                                  headers={"accept": "application/json"})
        if r.status_code != 200 or "application/json" not in r.headers.get("content-type", ""):
            raise ValueError("exchange refused")
        body = r.json()
        token, expires_in, user = body.get("sessionToken"), body.get("expiresIn"), body.get("user") or {}
        if not (isinstance(token, str) and len(token) <= 4096 and access.TOKEN.match(token)
                and isinstance(expires_in, (int, float)) and expires_in >= 1
                and isinstance(user.get("email"), str) and user.get("role") in ("team", "client")):
            raise ValueError("invalid session")
    except (httpx.HTTPError, ValueError):
        return PlainTextResponse("Command Center sign-in could not be completed. Open the Knowledge Base from "
                                 "Command Center again.", status_code=502, headers=NO_STORE)
    response = RedirectResponse(return_to, status_code=302, headers=NO_STORE)
    response.delete_cookie(STATE_COOKIE, path=STATE_PATH)
    response.set_cookie(access.SESSION_COOKIE, token, max_age=min(int(expires_in), 7 * 24 * 3600), path="/",
                        httponly=True, samesite="lax", secure=_cookie_secure())
    return response


@router.get("/session")
def session() -> JSONResponse:
    """Who is signed in, and which view they get (behind the gate, so a Command Center user is always set there)."""
    settings = get_settings()
    return JSONResponse({"user": access.current_user.get(), "signIn": "command-center" if settings.sso_enabled else
                         ("password" if settings.kb_team_password_hash else "local"),
                         "rbac": settings.rbac_enabled, "viewAs": settings.kb_default_viewer}, headers=NO_STORE)


@router.get("/signout")
async def signout(request: Request):
    """Ends the session in every app: Command Center revokes the token, this cookie is cleared, and the browser
    passes through Command Center's own sign-out (which also clears the Atelier's). `from=command-center` is the
    leg Command Center started: it goes back to Command Center's login instead of looping."""
    settings = get_settings()
    from_ = request.query_params.get("from")
    token = request.cookies.get(access.SESSION_COOKIE)
    if settings.sso_enabled and token and access.TOKEN.match(token):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(f"{settings.command_center_auth_origin.rstrip('/')}/api/auth/logout",
                                  headers={"cookie": f"{access.SESSION_COOKIE}={token}", "accept": "application/json"})
        except httpx.HTTPError:
            pass  # Command Center's own leg below revokes it again
    access.forget_session(token)
    if not settings.sso_enabled:
        target = "/"
    else:
        cc = settings.command_center_public_origin.rstrip("/")
        target = f"{cc}/login" if from_ == "command-center" else f"{cc}/api/auth/signout?from=knowledge-base"
    response = RedirectResponse(target, status_code=302, headers=NO_STORE)
    response.delete_cookie(access.SESSION_COOKIE, path="/", secure=_cookie_secure(), httponly=True, samesite="lax")
    return response
