"""LeadLock Marketplace app (S1): agency grant, token rotation, sub-account tokens, signed install webhooks."""
import base64
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import LeadLockAppEvent, LeadLockInstallation, LeadLockLocation, WorkItem
from backend.models.db.base import utcnow
from backend.services.intake import leadlock_app
from backend.services.shared.errors import AuthInvalidError
from backend.services.shared.secrets import decrypt

COMPANY = "company-example"
SIGNING_KEY = Ed25519PrivateKey.generate()


@pytest.fixture(autouse=True)
def app_settings(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "kb_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(s, "leadlock_app_client_id", "example-client-id")
    monkeypatch.setattr(s, "leadlock_app_client_secret", "example-client-secret")
    monkeypatch.setattr(s, "leadlock_app_id", "app-example")
    monkeypatch.setattr(s, "leadlock_company_id", COMPANY)
    monkeypatch.setattr(s, "leadlock_webhook_public_key", SIGNING_KEY.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode())


class FakeHighLevel:
    """Answers by (method, path). A handler is a (status, body) tuple, a list of them (one per call), or a
    function of the request returning one."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def request(self, method, url, data=None, params=None, headers=None, timeout=None):
        path = url.removeprefix(leadlock_app.API)
        self.calls.append(SimpleNamespace(method=method, path=path, data=data, params=params, headers=headers))
        handler = self.routes[(method, path)]
        if isinstance(handler, list):
            handler = handler.pop(0)
        status, body = handler(data, params, headers) if callable(handler) else handler
        return SimpleNamespace(status_code=status, json=lambda: body)


def grant(**overrides):
    return {"access_token": "agency-access-1", "refresh_token": "agency-refresh-1", "expires_in": 86399,
            "scope": "contacts.readonly invoices.readonly oauth.write", "userType": "Company", "companyId": COMPANY,
            "userId": "user-example", "isBulkInstallation": True, "installToFutureLocations": True,
            "approvedLocations": ["loc-a", "loc-b"], **overrides}


def install(**overrides):
    with transaction() as s:
        return leadlock_app.store_installation(s, grant(**overrides), actor="test").id


def expire_agency_token():
    with transaction() as s:
        s.execute(select(LeadLockInstallation)).scalar_one().access_expires_at = utcnow() - timedelta(minutes=1)


# --- agency grant ---------------------------------------------------------------------------------------

def test_exchange_code_asks_for_a_company_token_with_the_saved_redirect():
    fake = FakeHighLevel({("POST", "/oauth/token"): (200, grant())})
    assert leadlock_app.exchange_code("good-code", fake)["companyId"] == COMPANY
    call = fake.calls[0]
    assert call.data["grant_type"] == "authorization_code" and call.data["user_type"] == "Company"
    assert call.data["redirect_uri"] == get_settings().leadlock_redirect_uri
    assert call.headers["User-Agent"] == leadlock_app.USER_AGENT  # Cloudflare 1010 refuses default agents
    with pytest.raises(leadlock_app.LeadLockAppError, match="refused the authorization code"):
        leadlock_app.exchange_code("bad", FakeHighLevel({("POST", "/oauth/token"): (400, {"error": "invalid_grant"})}))


def test_install_stores_encrypted_tokens_and_queues_a_sync():
    install()
    with transaction() as s:
        inst = s.execute(select(LeadLockInstallation)).scalar_one()
        assert "agency-access-1" not in inst.access_token_encrypted and "agency-refresh-1" not in inst.refresh_token_encrypted
        assert decrypt(inst.refresh_token_encrypted) == "agency-refresh-1"
        assert inst.install_to_future_locations is True and inst.scopes == sorted(grant()["scope"].split())
        assert {l.location_id: l.state for l in s.execute(select(LeadLockLocation)).scalars()} == {
            "loc-a": "pending", "loc-b": "pending"}
        assert [w.kind for w in s.execute(select(WorkItem)).scalars()] == [leadlock_app.RECONCILE_JOB]


def test_install_refuses_other_agencies_and_sub_account_grants():
    with transaction() as s:
        with pytest.raises(leadlock_app.LeadLockAppError, match="different agency"):
            leadlock_app.store_installation(s, grant(companyId="someone-else"), actor="test")
        with pytest.raises(leadlock_app.LeadLockAppError, match="not an agency"):
            leadlock_app.store_installation(s, grant(userType="Location"), actor="test")
    with transaction() as s:
        assert s.execute(select(LeadLockInstallation)).first() is None


def test_reinstall_replaces_the_previous_grant():
    install()
    install(access_token="agency-access-2")
    with transaction() as s:
        rows = s.execute(select(LeadLockInstallation)).scalars().all()
        assert len(rows) == 2 and [r.revoked_reason for r in rows if r.revoked_at] == ["replaced by a new install"]


def test_valid_agency_token_is_used_without_calling_highlevel():
    install()
    fake = FakeHighLevel({})
    assert leadlock_app.company_token(fake) == ("agency-access-1", COMPANY) and fake.calls == []


def test_expired_agency_token_refreshes_and_stores_the_rotated_refresh_token():
    install()
    expire_agency_token()
    fake = FakeHighLevel({("POST", "/oauth/token"): (200, grant(access_token="agency-access-2",
                                                                refresh_token="agency-refresh-2"))})
    assert leadlock_app.company_token(fake) == ("agency-access-2", COMPANY)
    assert fake.calls[0].data["grant_type"] == "refresh_token" and fake.calls[0].data["refresh_token"] == "agency-refresh-1"
    with transaction() as s:
        inst = s.execute(select(LeadLockInstallation)).scalar_one()
        assert decrypt(inst.refresh_token_encrypted) == "agency-refresh-2" and inst.revision == 2


def test_rejected_refresh_revokes_the_grant_and_says_reinstall():
    install()
    expire_agency_token()
    fake = FakeHighLevel({("POST", "/oauth/token"): (401, {"error": "invalid_grant"})})
    with pytest.raises(leadlock_app.LeadLockAppError, match="reinstall"):
        leadlock_app.company_token(fake)
    with transaction() as s:  # the revocation was committed, not rolled back with the error
        assert s.execute(select(LeadLockInstallation)).scalar_one().revoked_reason == "refresh rejected; reinstall the app"
    with pytest.raises(leadlock_app.LeadLockAppError, match="not installed"):
        leadlock_app.company_token(FakeHighLevel({}))


# --- sub-account tokens ---------------------------------------------------------------------------------

def test_location_token_is_minted_once_then_reused_until_it_nears_expiry():
    install()
    fake = FakeHighLevel({("POST", "/oauth/location-token"): (200, {"access_token": "loc-a-token", "expires_in": 86399,
                                                                    "scope": "contacts.readonly"})})
    assert leadlock_app.location_token("loc-a", fake) == "loc-a-token"
    assert fake.calls[0].data == {"companyId": COMPANY, "locationId": "loc-a"}
    assert fake.calls[0].headers["Authorization"] == "Bearer agency-access-1"
    assert leadlock_app.location_token("loc-a", fake) == "loc-a-token" and len(fake.calls) == 1
    with transaction() as s:
        loc = s.execute(select(LeadLockLocation).where(LeadLockLocation.location_id == "loc-a")).scalar_one()
        assert loc.state == "active" and "loc-a-token" not in loc.access_token_encrypted
        loc.access_expires_at = utcnow() + timedelta(minutes=2)  # inside the 5-minute margin
    fake.routes[("POST", "/oauth/location-token")] = (200, {"access_token": "loc-a-token-2", "expires_in": 86399})
    assert leadlock_app.location_token("loc-a", fake) == "loc-a-token-2"


def test_refused_location_token_marks_the_sub_account_failed():
    install()
    fake = FakeHighLevel({("POST", "/oauth/location-token"): (403, {"error": "forbidden"})})
    with pytest.raises(AuthInvalidError):
        leadlock_app.mint_location_token("loc-b", fake)
    with transaction() as s:
        loc = s.execute(select(LeadLockLocation).where(LeadLockLocation.location_id == "loc-b")).scalar_one()
        assert loc.state == "failed" and "HTTP 403" in loc.last_error and loc.access_token_encrypted is None


def test_reconcile_adds_new_sub_accounts_and_marks_removed_ones_after_a_full_listing():
    install(approvedLocations=["loc-a", "loc-gone"])
    pages = [(200, {"items": [{"_id": "loc-a", "name": "Venue A"}], "installToFutureLocations": False,
                    "pagination": {"hasNextPage": True, "nextPageToken": "p2"}}),
             (200, {"items": [{"_id": "loc-new", "name": "Venue New"}], "pagination": {"hasNextPage": False}})]
    fake = FakeHighLevel({("GET", "/oauth/installed-locations"): pages})
    result = leadlock_app.reconcile(fake)
    assert result["installed"] == 2 and result["removed"] == 1 and result["install_to_future_locations"] is False
    assert sorted(result["needs_token"]) == ["loc-a", "loc-new"]
    assert fake.calls[0].params["appId"] == "app-example" and fake.calls[1].params["pageToken"] == "p2"
    with transaction() as s:
        states = {l.location_id: (l.state, l.name) for l in s.execute(select(LeadLockLocation)).scalars()}
        assert states == {"loc-a": ("pending", "Venue A"), "loc-new": ("pending", "Venue New"),
                          "loc-gone": ("uninstalled", None)}
        assert s.execute(select(LeadLockInstallation)).scalar_one().install_to_future_locations is False


def test_a_failed_listing_page_marks_nothing_uninstalled():
    install(approvedLocations=["loc-a"])
    fake = FakeHighLevel({("GET", "/oauth/installed-locations"): [
        (200, {"items": [], "pagination": {"hasNextPage": True, "nextPageToken": "p2"}}), (503, {})]})
    with pytest.raises(Exception):
        leadlock_app.reconcile(fake)
    with transaction() as s:
        assert s.execute(select(LeadLockLocation)).scalar_one().state == "pending"


# --- webhook signatures and events ----------------------------------------------------------------------

def signed(event: dict, *, raw: bytes | None = None, key=SIGNING_KEY) -> tuple[bytes, str]:
    body = raw if raw is not None else json.dumps(event, separators=(",", ":")).encode()
    return body, base64.b64encode(key.sign(body)).decode()


def test_signature_accepts_highlevel_signed_bodies_only():
    body, sig = signed({"type": "INSTALL"})
    assert leadlock_app.verify_signature(body, sig)
    assert not leadlock_app.verify_signature(body + b" ", base64.b64encode(b"x" * 64).decode())
    assert not leadlock_app.verify_signature(body.replace(b"INSTALL", b"UNINSTALL"), sig)
    assert not leadlock_app.verify_signature(body, signed({"type": "INSTALL"}, key=Ed25519PrivateKey.generate())[1])
    assert not leadlock_app.verify_signature(body, None) and not leadlock_app.verify_signature(body, "not base64!")


def test_signature_over_the_compact_json_is_accepted_for_a_pretty_printed_body():
    event = {"type": "INSTALL", "locationId": "loc-a"}
    _, sig = signed(event)  # signed over JSON.stringify-style compact JSON
    assert leadlock_app.verify_signature(json.dumps(event, indent=2).encode(), sig)


@pytest.fixture
def client():
    from backend.app import app
    return TestClient(app, follow_redirects=False)


def post_event(client, event, **kw):
    body, sig = signed(event, **kw)
    return client.post("/api/v1/leadlock/webhooks", content=body,
                       headers={"x-ghl-signature": sig, "content-type": "application/json"})


def test_webhook_rejects_unsigned_or_forged_requests(client):
    r = client.post("/api/v1/leadlock/webhooks", json={"type": "INSTALL", "locationId": "loc-x"})
    assert r.status_code == 401
    r = post_event(client, {"type": "INSTALL", "locationId": "loc-x"}, key=Ed25519PrivateKey.generate())
    assert r.status_code == 401
    with transaction() as s:
        assert s.execute(select(LeadLockLocation)).first() is None and s.execute(select(LeadLockAppEvent)).first() is None


def test_new_sub_account_install_queues_its_token_once_even_if_redelivered(client):
    install(approvedLocations=[])
    reconciles = lambda s: len(s.execute(select(WorkItem).where(WorkItem.kind == leadlock_app.RECONCILE_JOB)).scalars().all())
    with transaction() as s:
        before = reconciles(s)  # the agency install queues its own
    event = {"type": "INSTALL", "appId": "app-example", "companyId": COMPANY, "locationId": "loc-new",
             "companyName": "Agency Example", "webhookId": "wh-1"}
    assert post_event(client, event).json() == {"ok": True, "outcome": "sub-account installed"}
    assert post_event(client, event).json()["outcome"] == "duplicate"
    with transaction() as s:
        loc = s.execute(select(LeadLockLocation)).scalar_one()
        assert (loc.location_id, loc.state, loc.name) == ("loc-new", "pending", None)  # agency name not used
        assert [w.kind for w in s.execute(select(WorkItem).where(WorkItem.kind == leadlock_app.TOKEN_JOB)).scalars()] == [
            leadlock_app.TOKEN_JOB]
        # Its name arrives with reconcile, so it shows up named on the Connections screen, waiting for an admin.
        assert reconciles(s) == before + 1  # once, even though the event was delivered twice


def test_uninstall_drops_the_sub_account_token(client):
    install()
    fake = FakeHighLevel({("POST", "/oauth/location-token"): (200, {"access_token": "loc-a-token", "expires_in": 86399})})
    leadlock_app.mint_location_token("loc-a", fake)
    r = post_event(client, {"type": "UNINSTALL", "appId": "app-example", "locationId": "loc-a", "webhookId": "wh-2"})
    assert r.json()["outcome"] == "sub-account uninstalled"
    with transaction() as s:
        loc = s.execute(select(LeadLockLocation).where(LeadLockLocation.location_id == "loc-a")).scalar_one()
        assert loc.state == "uninstalled" and loc.access_token_encrypted is None
    with pytest.raises(leadlock_app.LeadLockAppError, match="not installed"):
        leadlock_app.location_token("loc-a", fake)


def test_events_for_other_agencies_or_apps_are_ignored(client):
    install(approvedLocations=[])
    assert post_event(client, {"type": "INSTALL", "companyId": "someone-else", "locationId": "loc-x",
                               "webhookId": "wh-3"}).json()["outcome"] == "ignored: another agency"
    assert post_event(client, {"type": "INSTALL", "appId": "other-app", "locationId": "loc-y",
                               "webhookId": "wh-4"}).json()["outcome"] == "ignored: another app"
    with transaction() as s:
        assert s.execute(select(LeadLockLocation)).first() is None


def test_agency_uninstall_revokes_the_grant_and_every_sub_account(client):
    install()
    r = post_event(client, {"type": "UNINSTALL", "appId": "app-example", "companyId": COMPANY, "webhookId": "wh-5"})
    assert r.json()["outcome"] == "agency uninstalled"
    with transaction() as s:
        assert s.execute(select(LeadLockInstallation)).scalar_one().revoked_reason == "app uninstalled from the agency"
        assert {l.state for l in s.execute(select(LeadLockLocation)).scalars()} == {"uninstalled"}


# --- install callback -----------------------------------------------------------------------------------

def test_callback_connects_the_agency_and_says_what_it_did(client, monkeypatch):
    monkeypatch.setattr(leadlock_app, "exchange_code", lambda code: grant())
    r = client.get("/api/v1/leadlock/oauth/callback", params={"code": "good-code"})
    assert r.status_code == 200 and "LeadLock connected" in r.text and "new sub-accounts: on" in r.text
    assert "agency-access-1" not in r.text
    with transaction() as s:
        assert s.execute(select(LeadLockInstallation)).scalar_one().company_id == COMPANY


def test_callback_refusals_show_a_reason_and_store_nothing(client, monkeypatch):
    assert client.get("/api/v1/leadlock/oauth/callback", params={"error": "access_denied"}).status_code == 400
    monkeypatch.setattr(leadlock_app, "exchange_code", lambda code: grant(companyId="someone-else"))
    r = client.get("/api/v1/leadlock/oauth/callback", params={"code": "good-code"})
    assert r.status_code == 400 and "different agency" in r.text
    with transaction() as s:
        assert s.execute(select(LeadLockInstallation)).first() is None


# --- the worker runs the new jobs -----------------------------------------------------------------------

def test_worker_runs_a_token_job_and_waits_when_there_is_no_grant_yet():
    from backend.workers import queue, runner
    assert leadlock_app.TOKEN_JOB in runner.JOBS and leadlock_app.RECONCILE_JOB in runner.JOBS
    with transaction() as s:
        queue.enqueue(s, leadlock_app.TOKEN_JOB, leadlock_app.LANE, "test:loc-early", {"location_id": "loc-early"})
    assert runner.run_one([leadlock_app.LANE])
    with transaction() as s:
        assert s.execute(select(WorkItem)).scalar_one().state == "succeeded"
        assert "waiting for the agency install" in s.execute(select(LeadLockLocation)).scalar_one().last_error


def test_a_refresh_refused_for_another_reason_keeps_the_grant():
    """A wrong client secret or redirect URI is fixed in the settings; it must not force a reinstall."""
    install()
    expire_agency_token()
    fake = FakeHighLevel({("POST", "/oauth/token"): (400, {"error": "invalid_client"})})
    with pytest.raises(leadlock_app.LeadLockAppError, match="LEADLOCK_"):
        leadlock_app.company_token(fake)
    with transaction() as s:
        assert s.execute(select(LeadLockInstallation)).scalar_one().revoked_at is None
    ok = FakeHighLevel({("POST", "/oauth/token"): (200, grant(access_token="agency-access-2", refresh_token="agency-refresh-2"))})
    assert leadlock_app.company_token(ok) == ("agency-access-2", COMPANY)
