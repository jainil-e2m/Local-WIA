"""Google Ads through WIA's manager account (MCC): list the client accounts under it, and read daily campaign
figures. Read-only by construction: the only calls are GAQL searches (`googleAds:search`), never a mutate.

Credentials (backend/.env): GOOGLE_ADS_DEVELOPER_TOKEN (MCC API Center), GOOGLE_ADS_LOGIN_CUSTOMER_ID (the MCC id),
GOOGLE_ADS_REFRESH_TOKEN (a grant with the adwords scope from a user who can see the MCC: `kb ads google-auth`).
"""
import threading
import time
from datetime import date

import httpx

from backend.config import get_settings
from backend.services.shared.errors import AuthInvalidError, TransientError
from backend.services.shared.http import ProviderClient

SCOPE = "https://www.googleapis.com/auth/adwords"
_lock = threading.Lock()
_token = {"value": None, "expires": 0.0}


def configured() -> bool:
    s = get_settings()
    return bool(s.google_ads_developer_token and s.google_ads_login_customer_id and s.google_ads_refresh_token
                and (s.google_ads_client_id or s.google_client_id) and (s.google_ads_client_secret or s.google_client_secret))


def _access_token(force: bool = False) -> str:
    with _lock:
        if not force and _token["value"] and _token["expires"] > time.time() + 60:
            return _token["value"]
        s = get_settings()
        try:
            r = httpx.post("https://oauth2.googleapis.com/token", timeout=25, data={
                "grant_type": "refresh_token", "refresh_token": s.google_ads_refresh_token,
                "client_id": s.google_ads_client_id or s.google_client_id,
                "client_secret": s.google_ads_client_secret or s.google_client_secret})
        except httpx.TransportError as exc:
            raise TransientError("google token endpoint unreachable") from exc
        if r.status_code >= 500:
            raise TransientError(f"google token HTTP {r.status_code}")
        if r.status_code != 200:
            raise AuthInvalidError(f"google ads refresh rejected: {r.json().get('error', 'unknown')}")
        data = r.json()
        _token.update(value=data["access_token"], expires=time.time() + int(data.get("expires_in", 3600)))
        return _token["value"]


class GoogleAds:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        s = get_settings()
        self.mcc = s.google_ads_login_customer_id
        self.client = ProviderClient("google_ads", f"https://googleads.googleapis.com/{s.google_ads_api_version}/",
                                     headers={"developer-token": s.google_ads_developer_token or "",
                                              "login-customer-id": self.mcc or ""}, min_interval_seconds=0.2)
        if transport is not None:  # tests
            self.client._client = httpx.Client(transport=transport, base_url=self.client._client.base_url,
                                               headers=self.client._client.headers)
        self._auth()

    def _auth(self, force=False):
        self.client.set_header("Authorization", f"Bearer {_access_token(force)}")

    def search(self, customer_id: str, query: str) -> list[dict]:
        rows, token = [], None
        while True:
            body = {"query": query, **({"pageToken": token} if token else {})}
            data = self.client.request("POST", f"customers/{customer_id}/googleAds:search", json=body,
                                       auth_retry=lambda: self._auth(force=True)).json()
            rows += data.get("results", [])
            token = data.get("nextPageToken")
            if not token:
                return rows

    def accounts(self) -> list[dict]:
        """Every non-manager client account directly or indirectly under the MCC."""
        rows = self.search(self.mcc, "SELECT customer_client.id, customer_client.descriptive_name, "
                                     "customer_client.currency_code, customer_client.status, customer_client.manager "
                                     "FROM customer_client WHERE customer_client.level >= 1")
        out = []
        for r in rows:
            c = r.get("customerClient", {})
            if c.get("manager"):
                continue
            out.append({"account_id": str(c.get("id")), "name": c.get("descriptiveName") or f"Account {c.get('id')}",
                        "currency": c.get("currencyCode"), "status": c.get("status"), "via": f"MCC {self.mcc}"})
        return out

    def daily(self, account_id: str, since: date, until: date) -> list[dict]:
        """Campaign x day figures. Cost comes in micros; `conversions` is the account's primary conversions."""
        rows = self.search(account_id, (
            "SELECT segments.date, campaign.id, campaign.name, campaign.advertising_channel_type, "
            "metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, "
            "metrics.search_budget_lost_impression_share, metrics.search_impression_share "
            f"FROM campaign WHERE segments.date BETWEEN '{since.isoformat()}' AND '{until.isoformat()}' "
            "AND metrics.impressions > 0"))
        out = []
        for r in rows:
            c, m, seg = r.get("campaign", {}), r.get("metrics", {}), r.get("segments", {})
            extra = {k: m[src] for k, src in (("budget_lost_is", "searchBudgetLostImpressionShare"),
                                              ("search_is", "searchImpressionShare")) if m.get(src) is not None}
            out.append({"campaign_id": str(c.get("id")), "campaign_name": c.get("name") or "",
                        "channel": f"Google {(c.get('advertisingChannelType') or 'other').replace('_', ' ').title()}",
                        "day": date.fromisoformat(seg["date"]), "spend": int(m.get("costMicros") or 0) / 1_000_000,
                        "impressions": int(m.get("impressions") or 0), "clicks": int(m.get("clicks") or 0),
                        "conversions": float(m.get("conversions") or 0), "extra": extra})
        return out

    def close(self):
        self.client.close()
