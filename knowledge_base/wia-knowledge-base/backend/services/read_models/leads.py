"""Leads read model (S9): one client's LeadLock records turned into the Leads tab's figures.

Reads only what intake stored (no provider calls, no personal data: the adapter never keeps it). Every figure is
a count or a share of stored records, by a rule written here:

  inquiry        an opportunity, dated when it was created
  tour booked    an appointment created in the period that isn't cancelled
  upcoming tour  an appointment starting in the next 30 days that isn't cancelled or a no-show
  awaiting reply a conversation whose last message came in from the lead, in the period, and is still unread.
                 Older unread threads are counted apart: LeadLock keeps a thread unread until someone opens it there,
                 so a venue that replies elsewhere piles up stale ones.
  won            an opportunity marked won, dated by its last status change. Shown only when the venue really
                 uses won/lost/abandoned (at least 10% of opportunities); many venues leave everything open.
"""
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select

from backend.models.db import (Business, ConnectorAccount, RecordAssociation, SourceRecord, SourceScope, SourceVersion,
                               SyncRun)

PERIODS = {"7d": timedelta(days=7), "14d": timedelta(days=14), "30d": timedelta(days=30), "90d": timedelta(days=90),
           "180d": timedelta(days=180), "12m": timedelta(days=365), "all": None}
MAX_RANGE = timedelta(days=366 * 10)
OUTCOME_TRACKED_SHARE = 0.10
UPCOMING = timedelta(days=30)
TOP = 6


class UnknownClient(LookupError):
    pass


def _dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _channel(value: str | None) -> str:
    raw = (value or "unknown").upper().removeprefix("TYPE_")
    return {"PHONE": "SMS / phone", "SMS": "SMS", "EMAIL": "Email", "FB_MESSENGER": "Facebook",
            "FACEBOOK": "Facebook", "INSTAGRAM": "Instagram", "LIVE_CHAT": "Website chat", "WEBCHAT": "Website chat",
            "GMB": "Google Business", "REVIEW": "Reviews", "WHATSAPP": "WhatsApp"}.get(raw, raw.replace("_", " ").title())


def _tidy_sources(values) -> list[dict]:
    """LeadLock's source is free text: merge spelling variants ("Website Inquiry Form" / "website inquiry form ")
    under their most common spelling, and treat blanks or punctuation-only values (",") as not recorded.
    Returns every source, largest first."""
    counts, spellings = Counter(), defaultdict(Counter)
    for raw in values:
        text = " ".join(str(raw or "").split())
        if not any(ch.isalnum() for ch in text):
            text = "Not recorded"
        key = text.casefold()
        counts[key] += 1
        spellings[key][text] += 1
    return [{"label": spellings[k].most_common(1)[0][0], "count": n} for k, n in counts.most_common()]


def _top(counter: Counter, n: int = TOP) -> list[dict]:
    items = counter.most_common()
    rows = [{"label": label, "count": count} for label, count in items[:n]]
    rest = sum(count for _, count in items[n:])
    if rest:
        rows.append({"label": "Other", "count": rest})
    return rows


def client_leads(s, slug: str, period: str = "90d", now: datetime | None = None,
                 start_date: date | None = None, end_date: date | None = None) -> dict:
    """`period` is a preset (PERIODS) ending now, or pass start_date and end_date (inclusive, UTC days) for a custom
    range; the comparison window is then the same number of days just before it."""
    custom = start_date is not None or end_date is not None
    if custom:
        if start_date is None or end_date is None:
            raise ValueError("a custom range needs both start and end")
        if start_date > end_date:
            raise ValueError("start must be on or before end")
        if end_date - start_date > MAX_RANGE:
            raise ValueError("a custom range can span at most ten years")
    elif period not in PERIODS:
        raise ValueError(f"period must be one of {', '.join(PERIODS)}")
    business = s.execute(select(Business).where(Business.slug == slug)).scalar_one_or_none()
    if business is None:
        raise UnknownClient(slug)
    now = now or datetime.now(UTC)
    if custom:
        period = "custom"
        start = datetime.combine(start_date, time.min, tzinfo=UTC)
        end_at = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC) - timedelta(microseconds=1)
        span = end_at - start + timedelta(microseconds=1)
    else:
        span = PERIODS[period]
        start = now - span if span else None
        end_at = now
    prev_start = start - span if span else None

    def in_period(dt):
        return dt is not None and (start is None or dt >= start) and dt <= end_at

    def in_previous(dt):
        return dt is not None and prev_start is not None and prev_start <= dt < start

    scopes = s.execute(select(SourceScope).join(ConnectorAccount).where(
        ConnectorAccount.provider == "leadlock", SourceScope.business_id == business.id,
        SourceScope.state == "approved")).scalars().all()
    rows = s.execute(select(SourceRecord.record_kind, SourceRecord.occurred_at, SourceVersion.attributes,
                            SourceRecord.scope_id)
                     .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
                     .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
                     .where(RecordAssociation.business_id == business.id, RecordAssociation.status == "associated",
                            SourceRecord.availability == "available",
                            SourceRecord.record_kind.like("leadlock_%"))).all()
    # Unlinked: the history it collected stays with the client, so "last synced" is that of the old sub-account.
    synced_scopes = [sc.id for sc in scopes] or list({r.scope_id for r in rows if r.scope_id})
    synced = s.execute(select(SyncRun.finished_at).where(SyncRun.scope_id.in_(synced_scopes),
                                                         SyncRun.state.in_(("succeeded", "partial")))
                       .order_by(SyncRun.finished_at.desc()).limit(1)).scalar_one_or_none() if synced_scopes else None
    by_kind: dict[str, list[tuple[datetime | None, dict]]] = defaultdict(list)
    for kind, occurred, attrs, _ in rows:
        by_kind[kind.removeprefix("leadlock_")].append((_dt(occurred), attrs or {}))

    opps, appts = by_kind["opportunity"], by_kind["appointment"]
    convs, contacts, forms = by_kind["conversation"], by_kind["contact"], by_kind["form_submission"]

    # Outcomes: only meaningful when the venue closes opportunities in LeadLock
    all_status = Counter((a.get("status") or "open") for _, a in opps)
    closed = sum(n for st, n in all_status.items() if st != "open")
    tracked = bool(opps) and closed / len(opps) >= OUTCOME_TRACKED_SHARE

    def won_in(check):
        return sum(1 for created, a in opps if a.get("status") == "won"
                   and check(_dt(a.get("last_status_change_at")) or created))

    def booked(check):
        return sum(1 for created, a in appts if check(created) and (a.get("status") or "") != "cancelled")

    unread = [(_dt(a.get("last_message_at")), a) for _, a in convs
              if (a.get("last_message_direction") or "").lower() == "inbound" and (a.get("unread_count") or 0) > 0]
    awaiting = [(dt, a) for dt, a in unread if in_period(dt)]
    oldest = min((dt for dt, _ in awaiting if dt), default=None)
    upcoming = sum(1 for _, a in appts if (start_at := _dt(a.get("start_at"))) and now <= start_at <= now + UPCOMING
                   and (a.get("status") or "") not in ("cancelled", "noshow"))

    kpis = {
        "inquiries": {"value": sum(1 for c, _ in opps if in_period(c)),
                      "previous": sum(1 for c, _ in opps if in_previous(c)) if span else None},
        "tours_booked": {"value": booked(in_period), "previous": booked(in_previous) if span else None},
        "upcoming_tours": {"value": upcoming},
        "awaiting_reply": {"value": len(awaiting), "oldest_days": (min(now, end_at) - oldest).days if oldest else None,
                           "older_unread": len(unread) - len(awaiting)},
        "won": {"tracked": tracked, "value": won_in(in_period) if tracked else None,
                "previous": won_in(in_previous) if tracked and span else None},
    }

    # Last 12 calendar months: inquiries by creation, tours by tour date (cancelled excluded)
    months = []
    cursor = datetime(now.year, now.month, 1, tzinfo=UTC)
    for _ in range(12):
        months.insert(0, cursor.strftime("%Y-%m"))
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    monthly = {m: {"month": m, "inquiries": 0, "tours": 0} for m in months}
    for created, _ in opps:
        if created and created.strftime("%Y-%m") in monthly:
            monthly[created.strftime("%Y-%m")]["inquiries"] += 1
    for _, a in appts:
        start_at = _dt(a.get("start_at"))
        if start_at and start_at.strftime("%Y-%m") in monthly and (a.get("status") or "") != "cancelled":
            monthly[start_at.strftime("%Y-%m")]["tours"] += 1

    # Funnel: opportunities created in the period, by their current stage, in HighLevel's stage order
    period_opps = [a for c, a in opps if in_period(c)]
    # A pipeline belongs to one sub-account: two sub-accounts' same-named pipelines (e.g. "Inquiry") stay apart.
    sub_names = {sc.external_id: sc.name for sc in scopes}
    defs = {}
    for _, a in by_kind["pipeline"]:
        defs[(a.get("location_id"), a.get("name"))] = [st.get("name") for st in a.get("stages") or []]
    per_pipeline: dict[tuple, Counter] = defaultdict(Counter)
    for a in period_opps:
        per_pipeline[(a.get("location_id"), a.get("pipeline") or "Unnamed pipeline")][a.get("stage") or "Unknown stage"] += 1
    pipelines = []
    for (location_id, name), counts in sorted(per_pipeline.items(), key=lambda kv: -sum(kv[1].values())):
        order = defs.get((location_id, name)) or []
        stages = [{"stage": st, "count": counts.get(st, 0)} for st in order]
        stages += [{"stage": st, "count": n} for st, n in counts.items() if st not in order]
        pipelines.append({"pipeline": name, "sub_account": sub_names.get(location_id), "total": sum(counts.values()),
                          "ordered": bool(order), "stages": stages})

    outcome_counts = Counter((a.get("status") or "open") for a in period_opps)
    sources = _tidy_sources(a.get("source") for c, a in contacts if in_period(c))
    form_counts = Counter((a.get("form") or "Unnamed form") for c, a in forms if in_period(c))
    channel_total, channel_waiting = Counter(), Counter()
    for _, a in convs:
        if in_period(_dt(a.get("last_message_at"))):
            channel_total[_channel(a.get("channel"))] += 1
    for _, a in awaiting:
        channel_waiting[_channel(a.get("channel"))] += 1
    appt_status = Counter((a.get("status") or "unknown") for c, a in appts if in_period(_dt(a.get("start_at")) or c))

    first = min((c for c, _ in opps if c), default=None)
    return {
        "client": {"slug": business.slug, "name": business.name},
        "as_of": now.isoformat(),
        "synced_at": synced.isoformat() if synced else None,
        "period": {"key": period, "start": start.isoformat() if start else None, "end": end_at.isoformat(),
                   "days": round(span / timedelta(days=1)) if span else None},
        "sub_accounts": [{"location_id": sc.external_id, "name": sc.name} for sc in scopes],
        "collecting": bool(scopes),  # False with history = unlinked: shown as "Not collected since <synced_at>"
        "kpis": kpis,
        "monthly": list(monthly.values()),
        "pipelines": pipelines,
        "outcomes": {"tracked": tracked, "counts": dict(outcome_counts), "all_time": dict(all_status)},
        "sources": sources,  # every source, tidied; the card folds the tail into "Other" itself
        "forms": _top(form_counts),
        "channels": [{"label": label, "count": n, "awaiting": channel_waiting.get(label, 0)}
                     for label, n in channel_total.most_common()],
        "appointments": dict(appt_status),
        "coverage": {"records": {k: len(v) for k, v in by_kind.items()},
                     "first_inquiry": first.date().isoformat() if first else None},
    }
