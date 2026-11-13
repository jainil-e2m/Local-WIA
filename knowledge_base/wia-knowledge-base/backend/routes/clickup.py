"""ClickUp connection flow for KB users (production path for S1/S12).

  "Connect ClickUp" in the KB  ->  GET /api/v1/clickup/oauth/start?return_to=/settings
                               ->  ClickUp's authorize page (person approves)
                               ->  GET /api/v1/clickup/oauth/callback  (this server)
                               ->  302 back to the KB at return_to, with ?clickup=connected or ?clickup=error

The state is signed and expires after 10 minutes, so a callback is only accepted for a start we issued.
The person is identified by the ClickUp account that approved (it must be on the roster).
S10 adds: require a KB session on /start, and check that the approving ClickUp user is that session's person.
"""
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from backend.config import get_settings
from backend.db import transaction
from backend.logging.config import get_logger
from backend.models.db.people import Person
from backend.services.outbound import clickup_oauth

log = get_logger(__name__)
router = APIRouter()


def _back_to_kb(path: str, **params) -> RedirectResponse:
    base = get_settings().kb_app_url.rstrip("/")
    sep = "&" if "?" in path else "?"
    return RedirectResponse(f"{base}{clickup_oauth.safe_return_path(path)}{sep}{urlencode(params)}", status_code=302)


@router.get("/oauth/start")
def start(return_to: str = "/") -> RedirectResponse:
    return RedirectResponse(clickup_oauth.authorize_url(clickup_oauth.make_state(return_to)), status_code=302)


@router.get("/oauth/callback")
def callback(code: str | None = None, state: str | None = None, error: str | None = None) -> RedirectResponse:
    try:
        data = clickup_oauth.read_state(state)
    except clickup_oauth.ClickUpConnectError:
        return _back_to_kb("/", clickup="error", reason="expired_or_invalid")
    if error or not code:
        return _back_to_kb(data["r"], clickup="error", reason="not_approved")
    try:
        token = clickup_oauth.exchange_code(code)
        with transaction() as s:
            conn = clickup_oauth.connect(s, token, actor="clickup-oauth")
            name = s.get(Person, conn.person_id).name
    except clickup_oauth.ClickUpConnectError as exc:
        log.warning("clickup connect refused", extra={"reason": str(exc)})
        reason = ("not_on_roster" if "roster" in str(exc) else "workspace_not_granted" if "workspace" in str(exc)
                  else "shared_login" if "shared login" in str(exc) else "clickup_refused")
        return _back_to_kb(data["r"], clickup="error", reason=reason)
    return _back_to_kb(data["r"], clickup="connected", **{"as": name})
