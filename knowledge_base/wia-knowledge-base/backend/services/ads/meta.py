"""Meta (Facebook and Instagram) ads through the Marketing API: list the ad accounts WIA's Business portfolio owns
or has partner access to, and read daily campaign insights. Read-only: GET requests with an ads_read token.

Credentials (backend/.env): META_ACCESS_TOKEN, a never-expiring system user token from WIA's Business portfolio with
only `ads_read`. It lists exactly the ad accounts assigned to that system user (/me/adaccounts), so access is decided
in Business Settings, account by account. META_BUSINESS_ID is optional: set it only if the token also has
`business_management` and every account the portfolio owns or is partnered on should be listed. A client portfolio
that never gave WIA partner access can add its own token to META_EXTRA_TOKENS ('{"label": "token"}').
"""
from datetime import date, timedelta

import httpx

from backend.config import get_settings
from backend.services.shared.http import ProviderClient

LEAD_ACTIONS = ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead")


def configured() -> bool:
    s = get_settings()
    return bool(s.meta_access_token or s.meta_extra_tokens)


def leads_from(actions: list[dict] | None) -> float:
    """Meta reports one lead several ways; `lead` is the total when present, else the others add up."""
    by = {a.get("action_type"): float(a.get("value") or 0) for a in actions or []}
    return by["lead"] if "lead" in by else sum(by.get(k, 0) for k in LEAD_ACTIONS[1:])


class Meta:
    def __init__(self, token: str, label: str, transport: httpx.BaseTransport | None = None):
        s = get_settings()
        self.token, self.label = token, label
        self.client = ProviderClient("meta", f"https://graph.facebook.com/{s.meta_api_version}/", min_interval_seconds=0.2)
        if transport is not None:  # tests
            self.client._client = httpx.Client(transport=transport, base_url=self.client._client.base_url)

    def _pages(self, path: str, params: dict) -> list[dict]:
        out, params = [], {**params, "access_token": self.token, "limit": 200}
        url = path
        while url:
            data = self.client.get_json(url, params=params)
            out += data.get("data", [])
            nxt = (data.get("paging") or {}).get("next")
            # The next link carries every parameter (token included); keep only its cursor.
            after = (data.get("paging") or {}).get("cursors", {}).get("after") if nxt else None
            url, params = (path, {**params, "after": after}) if after else (None, params)
        return out

    def accounts(self, business_id: str | None) -> list[dict]:
        fields = {"fields": "account_id,name,currency,account_status"}
        if business_id:
            rows = self._pages(f"{business_id}/owned_ad_accounts", fields) + self._pages(f"{business_id}/client_ad_accounts", fields)
        else:
            rows = self._pages("me/adaccounts", fields)
        seen, out = set(), []
        for a in rows:
            if a["account_id"] in seen:
                continue
            seen.add(a["account_id"])
            out.append({"account_id": a["account_id"], "name": a.get("name") or f"Account {a['account_id']}",
                        "currency": a.get("currency"), "status": {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 101: "CLOSED"}
                        .get(a.get("account_status"), str(a.get("account_status"))), "via": self.label})
        return out

    def daily(self, account_id: str, since: date, until: date) -> list[dict]:
        out = []
        # Insights are read in 30-day slices: long ranges at daily granularity time out on busy accounts.
        start = since
        while start <= until:
            end = min(start + timedelta(days=29), until)
            rows = self._pages(f"act_{account_id}/insights", {
                "level": "campaign", "time_increment": 1,
                "time_range": f'{{"since":"{start.isoformat()}","until":"{end.isoformat()}"}}',
                "fields": "campaign_id,campaign_name,objective,spend,impressions,clicks,inline_link_clicks,actions"})
            for r in rows:
                actions = {a.get("action_type"): float(a.get("value") or 0) for a in r.get("actions") or []}
                out.append({"campaign_id": r["campaign_id"], "campaign_name": r.get("campaign_name") or "",
                            "channel": "Meta", "day": date.fromisoformat(r["date_start"]),
                            "spend": float(r.get("spend") or 0), "impressions": int(r.get("impressions") or 0),
                            "clicks": int(r.get("clicks") or 0), "conversions": leads_from(r.get("actions")),
                            "extra": {"link_clicks": int(r.get("inline_link_clicks") or 0),
                                      "landing_page_views": actions.get("landing_page_view", 0),
                                      "objective": r.get("objective")}})
            start = end + timedelta(days=1)
        return out

    def close(self):
        self.client.close()


def clients() -> list[tuple[Meta, str | None]]:
    """(client, business id) for WIA's own token and each extra token."""
    s = get_settings()
    out = []
    if s.meta_access_token:
        out.append((Meta(s.meta_access_token, "WIA system user"), s.meta_business_id or None))
    for label, token in s.meta_extra_tokens.items():
        out.append((Meta(token, label), None))
    return out
