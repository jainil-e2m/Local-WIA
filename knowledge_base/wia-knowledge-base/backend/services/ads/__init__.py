"""Ad-platform figures for call prep: discover accounts, map them to clients, pull daily campaign figures, summarise.

    kb ads status                         what is configured, accounts seen, mapped, last pull
    kb ads discover                       list the accounts each platform shows (and suggest a client for each)
    kb ads map <provider> <account> <client-slug | none>
    kb ads pull [--days N] [--account ID] read figures for mapped accounts (also a daily worker job)

Only mapped accounts are read. Figures are campaign totals per day: no person-level data exists at this level.
"""
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import AdAccount, AdDaily, Business, BusinessAlias
from backend.models.db.base import utcnow
from backend.workers import queue

JOB = "ads.pull"
PROVIDERS = {"google_ads": "Google Ads", "meta": "Meta"}


def configured() -> dict[str, bool]:
    from backend.services.ads import google_ads, meta
    return {"google_ads": google_ads.configured(), "meta": meta.configured()}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def suggest_client(s, name: str) -> str | None:
    """The active client whose name or alias appears in the ad account's name (longest match wins)."""
    target = _norm(name)
    best = None
    for slug, label in s.execute(select(Business.slug, Business.name).where(Business.status == "active")).all() + \
            s.execute(select(Business.slug, BusinessAlias.alias).join(Business, Business.id == BusinessAlias.business_id)
                      .where(Business.status == "active")).all():
        key = _norm(label)
        if len(key) >= 4 and key in target and (best is None or len(key) > best[1]):
            best = (slug, len(key))
    return best[0] if best else None


def discover() -> list[dict]:
    """Ask each configured platform for its accounts and record them (unmapped ones stay unread)."""
    from backend.services.ads import google_ads, meta
    found = []
    if google_ads.configured():
        g = google_ads.GoogleAds()
        try:
            found += [{**a, "provider": "google_ads"} for a in g.accounts()]
        finally:
            g.close()
    for client, business_id in meta.clients():
        try:
            found += [{**a, "provider": "meta"} for a in client.accounts(business_id)]
        finally:
            client.close()
    with transaction() as s:
        for a in found:
            s.execute(insert(AdAccount).values(provider=a["provider"], account_id=a["account_id"], name=a["name"][:300],
                                               currency=a.get("currency"), status=a.get("status"), via=a.get("via"),
                                               discovered_at=utcnow())
                      .on_conflict_do_update(index_elements=["provider", "account_id"],
                                             set_={"name": a["name"][:300], "currency": a.get("currency"),
                                                   "status": a.get("status"), "via": a.get("via")}))
        for a in found:
            row = s.execute(select(AdAccount).where(AdAccount.provider == a["provider"],
                                                    AdAccount.account_id == a["account_id"])).scalar_one()
            a["mapped_to"] = s.get(Business, row.business_id).slug if row.business_id else None
            a["suggested"] = None if row.business_id else suggest_client(s, a["name"])
    return found


def map_account(s, provider: str, account_id: str, client_slug: str | None, *, actor: str) -> AdAccount:
    row = s.execute(select(AdAccount).where(AdAccount.provider == provider, AdAccount.account_id == account_id)).scalar_one_or_none()
    if row is None:
        raise ValueError(f"{PROVIDERS.get(provider, provider)} account {account_id} hasn't been discovered: run `kb ads discover`")
    if client_slug:
        b = s.execute(select(Business).where(Business.slug == client_slug, Business.status == "active")).scalar_one_or_none()
        if b is None:
            raise ValueError(f"unknown client {client_slug}")
        row.business_id = b.id
    else:
        row.business_id = None
        s.execute(AdDaily.__table__.delete().where(AdDaily.ad_account_id == row.id))  # unmapped: keep nothing
    row.mapped_by, row.mapped_at = actor, utcnow()
    return row


def pull(days: int | None = None, account: str | None = None, today: date | None = None) -> list[dict]:
    """Read figures for every mapped account: the full backfill the first time, then the last few days (late
    conversions change recent days). One account failing is recorded on it and doesn't stop the others."""
    from backend.services.ads import google_ads, meta
    settings, today = get_settings(), today or datetime.now(UTC).date()
    with transaction() as s:
        q = select(AdAccount).where(AdAccount.business_id.is_not(None))
        if account:
            q = q.where(AdAccount.account_id == account)
        targets = [(a.id, a.provider, a.account_id, a.via, a.last_pulled_at) for a in s.execute(q).scalars()]
    clients, report = {}, []
    if any(p == "google_ads" for _, p, *_ in targets) and google_ads.configured():
        clients["google_ads"] = google_ads.GoogleAds()
    meta_by_label = {c.label: c for c, _ in meta.clients()} if any(p == "meta" for _, p, *_ in targets) else {}
    try:
        for row_id, provider, account_id, via, last in targets:
            span = days or (settings.ads_refresh_days if last else settings.ads_backfill_days)
            since, until = today - timedelta(days=span), today - timedelta(days=1)
            client = clients.get("google_ads") if provider == "google_ads" else meta_by_label.get(via)
            if client is None:
                _note(row_id, f"{PROVIDERS[provider]} credentials for this account are not configured")
                report.append({"account": account_id, "provider": provider, "error": "not configured"})
                continue
            try:
                rows = client.daily(account_id, since, until)
            except Exception as error:  # noqa: BLE001 — recorded on the account; the next pull tries again
                _note(row_id, f"{type(error).__name__}: {str(error)[:300]}")
                report.append({"account": account_id, "provider": provider, "error": type(error).__name__})
                continue
            with transaction() as s:
                s.execute(AdDaily.__table__.delete().where(AdDaily.ad_account_id == row_id, AdDaily.day >= since,
                                                           AdDaily.day <= until))
                for r in rows:
                    s.add(AdDaily(ad_account_id=row_id, campaign_id=r["campaign_id"], day=r["day"],
                                  campaign_name=r["campaign_name"][:300], channel=r["channel"],
                                  spend=Decimal(str(round(r["spend"], 2))), impressions=r["impressions"],
                                  clicks=r["clicks"], conversions=Decimal(str(round(r["conversions"], 2))),
                                  extra=r["extra"]))
                a = s.get(AdAccount, row_id)
                a.last_pulled_at, a.last_error = utcnow(), None
                a.pulled_from = min(a.pulled_from or since, since)
                from backend.services.read_models import portfolio
                portfolio.request_refresh(s)
            report.append({"account": account_id, "provider": provider, "rows": len(rows), "from": since.isoformat()})
    finally:
        for c in [*clients.values(), *meta_by_label.values()]:
            c.close()
    return report


def _note(row_id, error: str) -> None:
    with transaction() as s:
        s.get(AdAccount, row_id).last_error = error


def _totals(rows) -> dict:
    spend = sum((r.spend for r in rows), Decimal(0))
    conv = sum((r.conversions for r in rows), Decimal(0))
    clicks = sum(r.clicks for r in rows)
    impressions = sum(r.impressions for r in rows)
    link = sum(int((r.extra or {}).get("link_clicks") or 0) for r in rows)
    lpv = sum(float((r.extra or {}).get("landing_page_views") or 0) for r in rows)
    out = {"spend": float(spend), "leads": float(conv), "clicks": clicks, "impressions": impressions,
           "cpl": round(float(spend / conv), 2) if conv else None,
           "ctr": round(100 * clicks / impressions, 2) if impressions else None}
    if link:
        out["link_ctr"] = round(100 * link / impressions, 2) if impressions else None
        out["lpv_rate"] = round(100 * lpv / link, 1)
    budget_lost = [float(r.extra["budget_lost_is"]) for r in rows if (r.extra or {}).get("budget_lost_is") is not None]
    if budget_lost:
        out["budget_lost_is"] = round(100 * sum(budget_lost) / len(budget_lost), 1)
    return out


def summary(s, business_id, today: date, days: int = 30) -> dict:
    """Per platform: this period against the one before, for the pulse, the Performance tab and the pack.
    `state` is connected (figures), not_mapped (the platform is set up but no account is mapped to this client)
    or not_connected (no credentials)."""
    cfg = configured()
    accounts = s.execute(select(AdAccount).where(AdAccount.business_id == business_id)).scalars().all()
    end, mid, start = today - timedelta(days=1), today - timedelta(days=days), today - timedelta(days=2 * days)
    out = {"period_days": days, "through": end.isoformat(), "platforms": []}
    for provider, label in PROVIDERS.items():
        mine = [a for a in accounts if a.provider == provider]
        if not mine:
            out["platforms"].append({"provider": provider, "label": label,
                                     "state": "not_mapped" if cfg[provider] else "not_connected"})
            continue
        rows = s.execute(select(AdDaily).where(AdDaily.ad_account_id.in_([a.id for a in mine]),
                                               AdDaily.day > start, AdDaily.day <= end)).scalars().all()
        now = [r for r in rows if r.day > mid]
        before = [r for r in rows if r.day <= mid]
        covered = min((a.pulled_from for a in mine if a.pulled_from), default=None)
        out["platforms"].append({
            "provider": provider, "label": label, "state": "connected",
            "accounts": [{"id": a.account_id, "name": a.name, "currency": a.currency, "error": a.last_error,
                          "pulled": a.last_pulled_at.isoformat() if a.last_pulled_at else None} for a in mine],
            "current": _totals(now),
            "previous": _totals(before) if covered and covered <= (mid - timedelta(days=days - 1)) else None,
            "campaigns": _campaigns(now),
        })
    return out


def _campaigns(rows) -> list[dict]:
    by = {}
    for r in rows:
        by.setdefault((r.campaign_id, r.campaign_name, r.channel), []).append(r)
    out = [{"name": name, "channel": channel, **_totals(rs)} for (_, name, channel), rs in by.items()]
    return sorted(out, key=lambda c: -c["spend"])[:8]


def sweep(s) -> bool:
    """Queue one pull a day while any platform is configured."""
    if not any(configured().values()):
        return False
    queue.enqueue(s, JOB, "maintenance", f"ads:{datetime.now(UTC).date().isoformat()}", {})
    return True


def run_job(work_id, lease_token, payload: dict) -> None:
    pull()
    with transaction() as s:
        queue.complete(s, work_id, lease_token)


def status(s) -> dict:
    rows = s.execute(select(AdAccount.provider, func.count(), func.count(AdAccount.business_id),
                            func.max(AdAccount.last_pulled_at)).group_by(AdAccount.provider)).all()
    seen = {p: {"accounts": n, "mapped": m, "last_pull": last.isoformat() if last else None} for p, n, m, last in rows}
    return {p: {"configured": c, **seen.get(p, {"accounts": 0, "mapped": 0, "last_pull": None})}
            for p, c in configured().items()}
