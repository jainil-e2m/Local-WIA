"""LeadLock Marketplace app endpoints (S1). See services/intake/leadlock_app.py for the flow.

  GET  /api/v1/leadlock/oauth/callback   HighLevel sends the agency admin here after they install the app
  POST /api/v1/leadlock/webhooks         HighLevel posts INSTALL / UNINSTALL events here (signed)

The callback is reached from HighLevel's install screen, not from a KB page, so it answers with a short
page saying what was connected instead of redirecting into the KB. The webhook must answer quickly with
a 2xx (HighLevel retries anything else up to 12 times); slow work goes to the job queue.
"""
import html
import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.db import transaction
from backend.logging.config import get_logger
from backend.services.intake import leadlock_app

log = get_logger(__name__)
router = APIRouter()


def _page(title: str, lines: list[str], status: int = 200) -> HTMLResponse:
    body = "".join(f"<p>{html.escape(line)}</p>" for line in lines)
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>"
                        f"<body style='font-family:system-ui;max-width:40rem;margin:4rem auto;line-height:1.5'>"
                        f"<h1 style='font-size:1.3rem'>{html.escape(title)}</h1>{body}</body>", status_code=status)


@router.get("/oauth/callback")
def callback(code: str | None = None, error: str | None = None) -> HTMLResponse:
    if error or not code:
        return _page("LeadLock not connected", ["The install was not approved, so nothing was connected."], 400)
    try:
        token = leadlock_app.exchange_code(code)
        with transaction() as s:
            inst = leadlock_app.store_installation(s, token, actor="leadlock-install")
            approved, future = len(inst.approved_location_ids), inst.install_to_future_locations
    except leadlock_app.LeadLockAppError as exc:
        log.warning("leadlock install refused", extra={"reason": str(exc)})
        return _page("LeadLock not connected", [str(exc)], 400)
    future_text = {True: "on", False: "off"}.get(future, "not reported")
    log.info("leadlock installed", extra={"approved_locations": approved})
    return _page("LeadLock connected to the Client Knowledge Base", [
        f"Sub-accounts approved in this install: {approved or 'all (listed on the next sync)'}.",
        f"Install automatically on new sub-accounts: {future_text}.",
        "A token for each sub-account is being set up now. You can close this tab.",
    ])


@router.post("/webhooks")
async def webhooks(request: Request) -> JSONResponse:
    raw = await request.body()
    if not leadlock_app.verify_signature(raw, request.headers.get("x-ghl-signature")):
        log.warning("leadlock webhook signature rejected")
        return JSONResponse({"code": "bad_signature"}, status_code=401)
    try:
        event = json.loads(raw)
    except ValueError:
        return JSONResponse({"code": "bad_json"}, status_code=400)
    if not isinstance(event, dict):
        return JSONResponse({"code": "bad_json"}, status_code=400)

    def apply() -> str:
        with transaction() as s:
            return leadlock_app.handle_event(s, event, raw)

    outcome = await run_in_threadpool(apply)
    log.info("leadlock webhook", extra={"type": event.get("type"), "outcome": outcome})
    return JSONResponse({"ok": True, "outcome": outcome})
