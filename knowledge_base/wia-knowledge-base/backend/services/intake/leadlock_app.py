"""LeadLock (white-labelled HighLevel) Marketplace app: agency grant, per-sub-account tokens, install webhooks (S1).

Flow (HighLevel "Target User: Sub-Account, installed by an Agency"):
  agency admin installs the private app across sub-accounts
    -> GET /api/v1/leadlock/oauth/callback?code=...   exchange_code() + store_installation()  (Company token)
    -> reconcile(): list the sub-accounts the app is installed on, then mint a token for each
  a sub-account added later (auto-install for future sub-accounts) or removed
    -> POST /api/v1/leadlock/webhooks   verify_signature() + handle_event(): INSTALL / UNINSTALL

Design choices:
  * Only grants for LEADLOCK_COMPANY_ID are stored, so a forged or foreign install can't plant itself.
  * The agency refresh token is the only rotating credential. Each refresh returns a new refresh token and
    invalidates the old one, so a refresh runs under a row lock and commits at once. Location tokens are
    re-minted from the agency token when they expire rather than refreshed.
  * Tokens are Fernet-encrypted (KB_SECRET_KEY). Errors carry status codes and HighLevel error codes,
    never tokens or response bodies.
"""
import base64
import hashlib
import json
from datetime import timedelta
from uuid import uuid4

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.config import get_settings
from backend.db import transaction
from backend.logging.config import get_logger
from backend.models.db import AuditEvent, LeadLockAppEvent, LeadLockInstallation, LeadLockLocation
from backend.models.db.base import utcnow
from backend.services.shared.errors import AuthInvalidError, TransientError
from backend.services.shared.secrets import decrypt, encrypt
from backend.workers import queue

log = get_logger(__name__)

API = "https://services.leadconnectorhq.com"
OAUTH_VERSION = "v3"  # the OAuth endpoints' API version (data endpoints use their own)
# HighLevel sits behind Cloudflare, which refuses some default client User-Agents (error 1010)
USER_AGENT = "wia-client-knowledge-base/1.0"
EXPIRY_SKEW = timedelta(minutes=5)
TOKEN_JOB = "leadlock.location_token"
RECONCILE_JOB = "leadlock.reconcile"
LANE = "maintenance"


class LeadLockAppError(RuntimeError):
    pass


def _app():
    s = get_settings()
    missing = [n for n, v in (("LEADLOCK_APP_CLIENT_ID", s.leadlock_app_client_id),
                              ("LEADLOCK_APP_CLIENT_SECRET", s.leadlock_app_client_secret),
                              ("LEADLOCK_COMPANY_ID", s.leadlock_company_id)) if not v]
    if missing:
        raise LeadLockAppError(f"{', '.join(missing)} not configured")
    return s


def _error_code(response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    if not isinstance(body, dict):
        return ""
    # HighLevel's own short codes and descriptions (e.g. "Authorization code not found"); never echoes secrets
    # ...and its API errors' "message" (e.g. "Location is not active" for a paused sub-account)
    parts = [p for p in (body.get("error"), body.get("error_description"), body.get("message"))
             if isinstance(p, str) and p]
    return ": ".join(parts)[:120]


def _call(http, method: str, path: str, *, data=None, params=None, token: str | None = None) -> dict:
    headers = {"Version": OAUTH_VERSION, "Accept": "application/json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = http.request(method, API + path, data=data, params=params, headers=headers,
                         timeout=get_settings().http_timeout_seconds)
    except httpx.TransportError as exc:
        raise TransientError(f"leadlock: transport error {type(exc).__name__}") from exc
    code = _error_code(r) if r.status_code >= 400 else ""
    detail = f"HTTP {r.status_code}" + (f" {code}" if code else "")
    if r.status_code == 429 or r.status_code >= 500:
        raise TransientError(f"leadlock {path}: {detail}")
    if r.status_code in (400, 401, 403):
        raise AuthInvalidError(f"leadlock {path}: {detail}")
    if r.status_code >= 300:
        raise LeadLockAppError(f"leadlock {path}: {detail}")
    return r.json()


# --- agency grant ---------------------------------------------------------------------------------------

def exchange_code(code: str, http=httpx) -> dict:
    s = _app()
    try:
        return _call(http, "POST", "/oauth/token", data={
            "client_id": s.leadlock_app_client_id, "client_secret": s.leadlock_app_client_secret,
            "grant_type": "authorization_code", "code": code, "user_type": "Company",
            "redirect_uri": s.leadlock_redirect_uri})
    except AuthInvalidError as exc:
        raise LeadLockAppError(f"HighLevel refused the authorization code ({exc})") from None


def store_installation(s, token: dict, *, actor: str) -> LeadLockInstallation:
    """Keep the agency grant from an install. Refuses anything but WIA's own agency's Company token."""
    settings = _app()
    if str(token.get("userType", "")).lower() != "company":
        raise LeadLockAppError("the grant is not an agency (Company) grant; install the app from the agency view")
    company_id = str(token.get("companyId") or "")
    if company_id != settings.leadlock_company_id:
        raise LeadLockAppError("the grant belongs to a different agency; only the configured LeadLock agency is accepted")
    if not token.get("access_token") or not token.get("refresh_token"):
        raise LeadLockAppError("HighLevel returned no access or refresh token")
    now = utcnow()
    for old in s.execute(select(LeadLockInstallation).where(LeadLockInstallation.company_id == company_id,
                                                            LeadLockInstallation.revoked_at.is_(None))).scalars():
        old.revoked_at, old.revoked_reason = now, "replaced by a new install"
    s.flush()
    approved = [str(x) for x in token.get("approvedLocations") or []]
    inst = LeadLockInstallation(
        company_id=company_id, app_id=settings.leadlock_app_id, installed_by_user_id=token.get("userId"),
        access_token_encrypted=encrypt(token["access_token"]), refresh_token_encrypted=encrypt(token["refresh_token"]),
        access_expires_at=now + timedelta(seconds=int(token.get("expires_in") or 0)),
        scopes=sorted(str(token.get("scope") or "").split()), is_bulk_installation=token.get("isBulkInstallation"),
        install_to_future_locations=token.get("installToFutureLocations"),
        approve_all_locations=token.get("approveAllLocations"), approved_location_ids=approved, installed_at=now)
    s.add(inst)
    s.flush()
    for location_id in approved:
        _upsert_location(s, location_id, installation_id=inst.id, installed=True)
    s.add(AuditEvent(actor=actor, action="leadlock.install", target_type="leadlock_company", target_id=company_id,
                     details={"approved_locations": len(approved), "scopes": len(inst.scopes),
                              "install_to_future_locations": inst.install_to_future_locations}))
    queue.enqueue(s, RECONCILE_JOB, LANE, f"{RECONCILE_JOB}:{uuid4()}", {})
    return inst


def _active_installation(s, *, for_update: bool = False) -> LeadLockInstallation | None:
    q = select(LeadLockInstallation).where(LeadLockInstallation.company_id == _app().leadlock_company_id,
                                           LeadLockInstallation.revoked_at.is_(None))
    return s.execute(q.with_for_update() if for_update else q).scalar_one_or_none()


def company_token(http=httpx) -> tuple[str, str]:
    """A valid agency access token and its company ID, refreshing it if needed.

    The refresh holds the installation row lock and commits before returning: two workers can never spend
    the same refresh token, and the new one is stored the moment HighLevel issues it. A rejected refresh
    revokes the grant: the app must then be reinstalled from the agency."""
    settings = _app()
    rejected = None
    with transaction() as s:
        inst = _active_installation(s, for_update=True)
        if inst is None:
            raise LeadLockAppError("the LeadLock app is not installed (no active agency grant)")
        if inst.access_expires_at - EXPIRY_SKEW > utcnow():
            return decrypt(inst.access_token_encrypted), inst.company_id
        try:
            fresh = _call(http, "POST", "/oauth/token", data={
                "client_id": settings.leadlock_app_client_id, "client_secret": settings.leadlock_app_client_secret,
                "grant_type": "refresh_token", "refresh_token": decrypt(inst.refresh_token_encrypted),
                "user_type": "Company", "redirect_uri": settings.leadlock_redirect_uri})
        except AuthInvalidError as exc:
            # Commit the revocation (raising inside the block would roll it back), then fail below.
            inst.revoked_at, inst.revoked_reason = utcnow(), "refresh rejected; reinstall the app"
            log.error("leadlock agency refresh rejected", extra={"company_id": inst.company_id})
            rejected = exc
            fresh = None
        if fresh is not None and (not fresh.get("access_token") or not fresh.get("refresh_token")):
            # Don't store a half answer: the old refresh token may already be spent, so say so loudly.
            raise LeadLockAppError("HighLevel's refresh response had no tokens; check the grant with `kb leadlock status`")
        if fresh is not None:
            now = utcnow()
            inst.access_token_encrypted = encrypt(fresh["access_token"])
            inst.refresh_token_encrypted = encrypt(fresh["refresh_token"])
            inst.access_expires_at = now + timedelta(seconds=int(fresh.get("expires_in") or 0))
            inst.refreshed_at, inst.revision = now, inst.revision + 1
            if fresh.get("scope"):
                inst.scopes = sorted(str(fresh["scope"]).split())
            company_id = inst.company_id
    if rejected is not None:
        raise LeadLockAppError(f"HighLevel rejected the refresh ({rejected}); reinstall the app from the agency")
    return fresh["access_token"], company_id


# --- sub-accounts ---------------------------------------------------------------------------------------

def _upsert_location(s, location_id: str, *, installation_id=None, name: str | None = None,
                     installed: bool = False) -> LeadLockLocation:
    loc = s.execute(select(LeadLockLocation).where(LeadLockLocation.location_id == location_id)
                    .with_for_update()).scalar_one_or_none()
    if loc is None:
        loc = LeadLockLocation(location_id=location_id, state="pending", scopes=[])
        s.add(loc)
    if installation_id is not None:
        loc.installation_id = installation_id
    if name:
        loc.name = name[:300]
    if installed and loc.state in ("uninstalled", "failed", "pending"):
        loc.state, loc.installed_at, loc.uninstalled_at = "pending", loc.installed_at or utcnow(), None
    s.flush()
    return loc


def mint_location_token(location_id: str, http=httpx) -> str:
    """Mint (or re-mint) a sub-account token from the agency token and store it encrypted."""
    token, company_id = company_token(http)
    try:
        data = _call(http, "POST", "/oauth/location-token", data={"companyId": company_id, "locationId": location_id},
                     token=token)
    except AuthInvalidError as exc:
        with transaction() as s:
            loc = _upsert_location(s, location_id)
            loc.state, loc.last_error = "failed", f"token refused: not installed here or access denied ({exc})"[:300]
        raise
    if not data.get("access_token"):
        raise LeadLockAppError("HighLevel returned no location token")
    now = utcnow()
    with transaction() as s:
        inst = _active_installation(s)
        loc = _upsert_location(s, location_id, installation_id=inst.id if inst else None)
        loc.state, loc.last_error, loc.last_token_at = "active", None, now
        loc.access_token_encrypted = encrypt(data["access_token"])
        loc.access_expires_at = now + timedelta(seconds=int(data.get("expires_in") or 0))
        loc.scopes = sorted(str(data.get("scope") or "").split())
        loc.installed_at = loc.installed_at or now
    return data["access_token"]


def location_token(location_id: str, http=httpx) -> str:
    """A valid token for one client sub-account: the stored one, or a freshly minted one near expiry."""
    with transaction() as s:
        loc = s.execute(select(LeadLockLocation).where(LeadLockLocation.location_id == location_id)).scalar_one_or_none()
        if loc is None or loc.state == "uninstalled":
            raise LeadLockAppError("the LeadLock app is not installed on this sub-account")
        if (loc.state == "active" and loc.access_token_encrypted and loc.access_expires_at
                and loc.access_expires_at - EXPIRY_SKEW > utcnow()):
            return decrypt(loc.access_token_encrypted)
    return mint_location_token(location_id, http)


def installed_locations(http=httpx) -> tuple[list[dict], bool | None]:
    """Every sub-account the app is installed on (all pages), and the agency's 'install to future
    sub-accounts' setting as HighLevel reports it."""
    settings = _app()
    if not settings.leadlock_app_id:
        raise LeadLockAppError("LEADLOCK_APP_ID is not configured")
    token, company_id = company_token(http)
    items, page_token, future = [], None, None
    for _ in range(100):  # 100 pages x 100 = far beyond WIA's sub-accounts; a guard, not a limit
        params = {"companyId": company_id, "appId": settings.leadlock_app_id, "isInstalled": "true", "pageSize": 100}
        if page_token:
            params["pageToken"] = page_token
        data = _call(http, "GET", "/oauth/installed-locations", params=params, token=token)
        items += [{"location_id": str(i["_id"]), "name": i.get("name")} for i in data.get("items", []) if i.get("_id")]
        future = data.get("installToFutureLocations", future)
        page_token = (data.get("pagination") or {}).get("nextPageToken")
        if not page_token or not (data.get("pagination") or {}).get("hasNextPage", True):
            return items, future
    raise LeadLockAppError("installed-locations pagination did not finish")


def reconcile(http=httpx) -> dict:
    """Make the sub-account rows match HighLevel: add new installs, mark removed ones uninstalled.

    Runs only after a complete listing, so a failed page never marks anything uninstalled. Returns the
    location IDs that still need a token."""
    listed, future = installed_locations(http)
    listed_ids = {i["location_id"] for i in listed}
    with transaction() as s:
        inst = _active_installation(s)
        if inst is not None and future is not None:
            inst.install_to_future_locations = future
        for item in listed:
            _upsert_location(s, item["location_id"], installation_id=inst.id if inst else None, name=item["name"],
                             installed=True)
        removed = 0
        for loc in s.execute(select(LeadLockLocation).where(LeadLockLocation.state.in_(("pending", "active", "failed")),
                                                            LeadLockLocation.location_id.not_in(listed_ids))).scalars():
            _mark_uninstalled(loc)
            removed += 1
        needs = [l.location_id for l in s.execute(select(LeadLockLocation).where(
            LeadLockLocation.state.in_(("pending", "failed")))).scalars()]
    return {"installed": len(listed), "removed": removed, "needs_token": needs, "install_to_future_locations": future}


def _mark_uninstalled(loc: LeadLockLocation) -> None:
    loc.state, loc.uninstalled_at = "uninstalled", utcnow()
    loc.access_token_encrypted = loc.access_expires_at = None


# --- webhooks -------------------------------------------------------------------------------------------

def verify_signature(raw: bytes, signature_b64: str | None) -> bool:
    """HighLevel's X-GHL-Signature: base64 Ed25519 over the body. HighLevel's own example signs the
    re-serialised JSON (JSON.stringify of the parsed body), so a compact re-serialisation is also accepted."""
    if not signature_b64:
        return False
    try:
        key = load_pem_public_key(get_settings().leadlock_webhook_public_key.encode())
        signature = base64.b64decode(signature_b64, validate=True)
    except ValueError:
        return False
    if not isinstance(key, Ed25519PublicKey):
        return False
    candidates = [raw]
    try:
        candidates.append(json.dumps(json.loads(raw), separators=(",", ":"), ensure_ascii=False).encode())
    except ValueError:
        pass
    for body in candidates:
        try:
            key.verify(signature, body)
            return True
        except InvalidSignature:
            continue
    return False


def handle_event(s, event: dict, raw: bytes) -> str:
    """Apply one verified install/uninstall event, exactly once. Returns a short outcome for the log."""
    settings = get_settings()
    delivery_key = str(event.get("webhookId") or "") or "sha256:" + hashlib.sha256(raw).hexdigest()
    kind = str(event.get("type") or "unknown")[:40]
    company_id, location_id = event.get("companyId"), event.get("locationId")
    inserted = s.execute(insert(LeadLockAppEvent).values(
        id=uuid4(), delivery_key=delivery_key[:200], event_type=kind, company_id=company_id, location_id=location_id,
        outcome="received", received_at=utcnow()).on_conflict_do_nothing(index_elements=["delivery_key"])
        .returning(LeadLockAppEvent.id)).scalar_one_or_none()
    if inserted is None:
        return "duplicate"
    outcome = _apply(s, settings, kind, company_id, location_id, delivery_key, event)
    s.get(LeadLockAppEvent, inserted).outcome = outcome[:60]
    return outcome


def _apply(s, settings, kind, company_id, location_id, delivery_key, event) -> str:
    if settings.leadlock_app_id and event.get("appId") and event["appId"] != settings.leadlock_app_id:
        return "ignored: another app"
    if company_id and settings.leadlock_company_id and company_id != settings.leadlock_company_id:
        return "ignored: another agency"
    inst = _active_installation(s) if settings.leadlock_company_id else None
    if kind == "INSTALL" and location_id:
        # The event's companyName is the agency's; the sub-account's own name arrives with reconcile.
        _upsert_location(s, location_id, installation_id=inst.id if inst else None, installed=True)
        queue.enqueue(s, TOKEN_JOB, LANE, f"{TOKEN_JOB}:{location_id}:{delivery_key}"[:300], {"location_id": location_id})
        # The sub-account's own name only arrives with reconcile. It then waits on the Connections screen as
        # "Needs a client"; nothing of it is read until an admin maps it (S2).
        queue.enqueue(s, RECONCILE_JOB, LANE, f"{RECONCILE_JOB}:{delivery_key}"[:300], {})
        return "sub-account installed"
    if kind == "INSTALL":
        queue.enqueue(s, RECONCILE_JOB, LANE, f"{RECONCILE_JOB}:{delivery_key}"[:300], {})
        return "agency installed"
    if kind == "UNINSTALL" and location_id:
        loc = s.execute(select(LeadLockLocation).where(LeadLockLocation.location_id == location_id)
                        .with_for_update()).scalar_one_or_none()
        if loc is None:
            return "sub-account uninstalled (unknown)"
        _mark_uninstalled(loc)
        return "sub-account uninstalled"
    if kind == "UNINSTALL" and company_id:
        if inst is not None:
            inst.revoked_at, inst.revoked_reason = utcnow(), "app uninstalled from the agency"
        for loc in s.execute(select(LeadLockLocation).where(LeadLockLocation.state != "uninstalled")).scalars():
            _mark_uninstalled(loc)
        s.add(AuditEvent(actor="leadlock-webhook", action="leadlock.uninstall", target_type="leadlock_company",
                         target_id=company_id, details={}))
        return "agency uninstalled"
    return f"ignored: {kind}"


# --- jobs (PostgreSQL work queue) -----------------------------------------------------------------------

def run_location_token_job(work_id, lease_token, payload: dict) -> None:
    location_id = payload["location_id"]
    with transaction() as s:
        has_grant = _active_installation(s) is not None
    if has_grant:
        try:
            mint_location_token(location_id)
        except AuthInvalidError:
            pass  # recorded on the row as failed; reconcile or the next install event retries it
    else:
        with transaction() as s:
            loc = _upsert_location(s, location_id)
            loc.last_error = "waiting for the agency install; reconcile will mint the token"
    with transaction() as s:
        queue.complete(s, work_id, lease_token)


def run_reconcile_job(work_id, lease_token, payload: dict) -> None:
    result = reconcile()
    with transaction() as s:
        for location_id in result["needs_token"]:
            queue.enqueue(s, TOKEN_JOB, LANE, f"{TOKEN_JOB}:{location_id}:{work_id}", {"location_id": location_id})
        queue.complete(s, work_id, lease_token)
    log.info("leadlock reconcile", extra={"installed": result["installed"], "removed": result["removed"],
                                          "needs_token": len(result["needs_token"])})


JOBS = {TOKEN_JOB: run_location_token_job, RECONCILE_JOB: run_reconcile_job}
