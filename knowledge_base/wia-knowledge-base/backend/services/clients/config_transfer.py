"""Move the KB's configuration (not its data) into a new database: the production bootstrap.

    kb config export .local/prod_config.json        # locally
    kb config import - < .local/prod_config.json    # in production (railway ssh), on an empty database

Moved: clients, aliases, services, contacts, source decisions, sender rules, people and their addresses,
mailbox holders, account teams, connector accounts, source scopes (the mappings) and provider identities.
Not moved: any source data (records, versions, text, associations, reviews, runs, streams, work), stored OAuth
tokens (ClickUp connections, the LeadLock install) and LeadLock/GHL accounts, because production does its own
install and maps its sub-accounts in the Connections tab. Production then fills itself by backfills.

The file holds client names and contact addresses: keep it under backend/.local/ (gitignored) and delete it
after the import.
"""
import json
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Uuid, func, insert, select, update

from backend.models.db import AuditEvent, Base, Business
from backend.models.db.base import utcnow
from backend.services.read_models import portfolio

FORMAT = "kb-config-v1"
EXCLUDED_PROVIDERS = ("leadlock", "ghl_billing")
ORDER = ("businesses", "business_aliases", "service_engagements", "contacts", "client_source_decisions",
         "sender_rules", "people", "person_addresses", "mailbox_holders", "account_team_members",
         "connector_accounts", "source_scopes", "provider_identities")
# Per-database runtime state: never carried over.
RESET = {
    "connector_accounts": dict(lease_token=None, lease_work_id=None, lease_until=None, next_request_at=None,
                               heavy_request_at=None, last_verified_at=None),
    "source_scopes": dict(last_successful_sync_at=None),
}


def _json(value):
    if isinstance(value, (UUID, datetime, date)):
        return value.isoformat() if not isinstance(value, UUID) else str(value)
    raise TypeError(f"cannot export {type(value).__name__}")


def _typed(table, row: dict) -> dict:
    out = {}
    for col in table.columns:
        if col.name not in row:
            continue
        v = row[col.name]
        if v is not None and isinstance(col.type, Uuid):
            v = UUID(v)
        elif v is not None and isinstance(col.type, DateTime):
            v = datetime.fromisoformat(v)
        elif v is not None and isinstance(col.type, Date):
            v = date.fromisoformat(v)
        out[col.name] = v
    return out


def export(s) -> dict:
    tables = Base.metadata.tables
    accounts = tables["connector_accounts"]
    kept = select(accounts.c.id).where(accounts.c.provider.not_in(EXCLUDED_PROVIDERS))
    out = {}
    for name in ORDER:
        t = tables[name]
        q = select(t)
        if name == "connector_accounts":
            q = q.where(t.c.provider.not_in(EXCLUDED_PROVIDERS))
        elif name in ("source_scopes", "provider_identities"):
            q = q.where(t.c.connector_account_id.in_(kept))
        rows = [{**dict(r), **RESET.get(name, {})} for r in s.execute(q.order_by(t.c.id)).mappings()]
        out[name] = rows
    return {"format": FORMAT, "exported_at": utcnow().isoformat(), "tables": out}


def dumps(data: dict) -> str:
    return json.dumps(data, default=_json, ensure_ascii=False)


def import_(s, data: dict, *, actor: str) -> dict:
    """Into an empty database only, in one transaction (the caller's)."""
    if data.get("format") != FORMAT:
        raise ValueError(f"not a {FORMAT} file")
    if s.scalar(select(func.count()).select_from(Business)):
        raise ValueError("this database already has clients; configuration is only imported into an empty one")
    tables = Base.metadata.tables
    counts = {}
    for name in ORDER:
        t = tables[name]
        rows = [_typed(t, r) for r in data["tables"].get(name, [])]
        merged = {}
        if name == "people":  # self-reference: insert unmerged, then point merged people at their survivor
            merged = {r["id"]: r["merged_into_id"] for r in rows if r.get("merged_into_id")}
            rows = [{**r, "merged_into_id": None} for r in rows]
        if rows:
            s.execute(insert(t), rows)
        for person_id, into in merged.items():
            s.execute(update(t).where(t.c.id == person_id).values(merged_into_id=into))
        counts[name] = len(rows)
    s.add(AuditEvent(actor=actor, action="config.import", target_type="database", target_id="config",
                     details={"counts": counts, "exported_at": data.get("exported_at")}))
    portfolio.request_refresh(s)
    return counts
