"""Shared Google OAuth (installed-app refresh token for hello@). Read-only scopes only."""
import threading
import time

import httpx

from backend.config import get_settings
from backend.services.shared.errors import AuthInvalidError, TransientError

READ_SCOPES = {
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
}

_lock = threading.Lock()
_cache: dict = {"token": None, "expires": 0.0, "scopes": []}


def access_token(force: bool = False) -> str:
    with _lock:
        if not force and _cache["token"] and _cache["expires"] > time.time() + 60:
            return _cache["token"]
        s = get_settings()
        if not (s.google_client_id and s.google_client_secret and s.google_refresh_token):
            raise AuthInvalidError("google OAuth credentials not configured")
        try:
            r = httpx.post("https://oauth2.googleapis.com/token", timeout=25, data={
                "grant_type": "refresh_token", "refresh_token": s.google_refresh_token,
                "client_id": s.google_client_id, "client_secret": s.google_client_secret})
        except httpx.TransportError as exc:
            raise TransientError("google token endpoint unreachable") from exc
        if r.status_code >= 500:
            raise TransientError(f"google token HTTP {r.status_code}")
        if r.status_code != 200:
            raise AuthInvalidError(f"google refresh rejected: {r.json().get('error', 'unknown')}")
        data = r.json()
        granted = set(data.get("scope", "").split())
        if granted - READ_SCOPES:
            # A broader grant than read-only is a configuration error for a read-only KB.
            raise AuthInvalidError("google token carries scopes beyond the read-only set")
        _cache.update(token=data["access_token"], expires=time.time() + int(data.get("expires_in", 3600)),
                      scopes=sorted(granted))
        return _cache["token"]


def granted_scopes() -> list[str]:
    access_token()
    return list(_cache["scopes"])


def bind(client) -> None:
    """Attach a fresh bearer token to a ProviderClient."""
    client.set_header("Authorization", f"Bearer {access_token()}")


def refresh(client) -> None:
    client.set_header("Authorization", f"Bearer {access_token(force=True)}")
