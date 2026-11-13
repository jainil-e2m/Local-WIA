"""Connections > LeadLock: every sub-account the agency app is installed on, and which client it belongs to.

This is the source-side view of S2 mapping (decided 5 Nov). The client-side view (Accounts & sources) and
the add-client wizard call the same commands in `mapping`, so the rules live in one place.

A sub-account is in exactly one state:
  mapped        approved and dedicated to a client; it is read (paused while that client is archived)
  not_a_client  excluded by an admin (WIA's own, demo, or another business); never read
  access_failed the app has no working token for it; nothing can be read until LeadLock access is fixed
  suggested     unmapped, and its name matches a client (or looks like WIA's own/demo account)
  needs_client  unmapped, nothing matches
Unmapped sub-accounts are never read: mapping is what starts collection (FR-INT-01).

The list reads the app's own records (`leadlock_locations`), so it makes no LeadLock calls; only Refresh does.
"""
import re
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from backend.models.db import (Business, BusinessAlias, ConnectorAccount, LeadLockLocation, RecordAssociation,
                               SourceRecord, SourceScope, SyncRun)
from backend.models.db.base import utcnow
from backend.services.clients import mapping
from backend.services.intake import sync
from backend.services.intake.scoping import is_live

PROVIDER, KIND = "leadlock", "location"
NEW_FOR = timedelta(days=7)

# Words that say what kind of business it is, not which one ("Evergreen Venue" = "Evergreen Venues").
_GENERIC = {"the", "and", "by", "of", "llc", "inc", "co", "company", "event", "events", "wedding", "weddings",
            "venue", "venues"}
# WIA's own, template and demo sub-accounts: suggested as "not a client", never auto-applied.
_INTERNAL = re.compile(r"snapshot|template|\bdemo\b|playground|junk|wedding industry ads|^leadlock pro$|advisory master",
                       re.IGNORECASE)


class ConnectionsError(mapping.MappingError):
    pass


def _tokens(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = set()
    for w in words:
        if w in _GENERIC:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)  # "Designs" = "Design"
    return frozenset(out)


def suggest_client(name: str | None, clients: list[tuple[Business, list[str]]]) -> tuple[Business, str] | None:
    """The client a sub-account name points to, when exactly one does. Matching is by distinctive words:
    one name's words must all appear in the other's ("The Weinberg" ~ "The Weinberg at Wixon Valley")."""
    if not name:
        return None
    mine = _tokens(name)
    if not mine or not any(len(t) >= 3 for t in mine):
        return None
    hits = []
    for business, aliases in clients:
        for alias in {business.name, *aliases}:
            theirs = _tokens(alias)
            if theirs and any(len(t) >= 3 for t in theirs) and (mine <= theirs or theirs <= mine):
                hits.append((business, alias))
                break
    if len({b.id for b, _ in hits}) != 1:
        return None  # none, or ambiguous: an admin decides
    business, alias = hits[0]
    return business, f"name matches “{alias}”"


def _account(s) -> ConnectorAccount:
    account = s.execute(select(ConnectorAccount).where(ConnectorAccount.provider == PROVIDER)).scalar_one_or_none()
    if account is None:
        raise ConnectionsError("LeadLock is not connected")
    return account


def _clients(s) -> list[tuple[Business, list[str]]]:
    aliases: dict[UUID, list[str]] = {}
    for business_id, alias in s.execute(select(BusinessAlias.business_id, BusinessAlias.alias)):
        aliases.setdefault(business_id, []).append(alias)
    return [(b, aliases.get(b.id, [])) for b in s.execute(select(Business).order_by(Business.name)).scalars()]


def _client(b: Business | None) -> dict | None:
    return {"slug": b.slug, "name": b.name, "status": b.status, "revision": b.revision} if b else None


def leadlock_rows(s, client_slug: str | None = None) -> dict:
    account = _account(s)
    clients = _clients(s)
    by_id = {b.id: b for b, _ in clients}
    scopes = {sc.external_id: sc for sc in s.execute(select(SourceScope).where(
        SourceScope.connector_account_id == account.id, SourceScope.kind == KIND)).scalars()}
    records = dict(s.execute(select(SourceRecord.scope_id, func.count()).where(
        SourceRecord.connector_account_id == account.id).group_by(SourceRecord.scope_id)).all())
    last_sync = dict(s.execute(select(SyncRun.scope_id, func.max(SyncRun.finished_at)).where(
        SyncRun.connector_account_id == account.id, SyncRun.state.in_(("succeeded", "partial")),
        SyncRun.mode != "discovery").group_by(SyncRun.scope_id)).all())
    running = set(s.execute(select(SyncRun.scope_id).where(
        SyncRun.connector_account_id == account.id, SyncRun.state.in_(("queued", "running")))).scalars())
    now = utcnow()
    # "New" = added by auto-install after the agency's first install, in the last week (not the initial batch).
    first_install = s.execute(select(func.min(LeadLockLocation.installed_at))).scalar_one_or_none()
    rows = []
    for loc in s.execute(select(LeadLockLocation).where(LeadLockLocation.state != "uninstalled")
                         .order_by(func.lower(LeadLockLocation.name))).scalars():
        scope = scopes.get(loc.location_id)
        client = by_id.get(scope.business_id) if scope and scope.business_id else None
        suggestion = None
        if scope and scope.state == "approved" and client:
            state = "mapped"
        elif scope and scope.state == "excluded":
            state = "not_a_client"
        elif loc.state != "active":
            state = "access_failed"
        else:
            hit = suggest_client(loc.name, clients)
            if hit:
                suggestion = {"kind": "client", "client": _client(hit[0]), "reason": hit[1]}
            elif loc.name and _INTERNAL.search(loc.name):
                suggestion = {"kind": "not_a_client", "reason": "looks like WIA's own, template or demo account"}
            state = "suggested" if suggestion else "needs_client"
        if state == "mapped":
            collection = ("collecting" if scope.id in running else
                          "paused_client_archived" if client.status != "active" else
                          "no_access" if loc.state != "active" else
                          "up_to_date" if last_sync.get(scope.id) else "waiting")
        else:
            collection = None
        row = {
            "location_id": loc.location_id, "name": loc.name or loc.location_id, "state": state,
            "access": loc.state, "access_error": loc.last_error if loc.state != "active" else None,
            "is_new": bool(loc.installed_at and first_install and loc.installed_at - first_install > timedelta(days=1)
                           and now - loc.installed_at < NEW_FOR),
            "client": _client(client), "suggestion": suggestion, "collection": collection,
            "records": records.get(scope.id, 0) if scope else 0,
            "last_synced_at": last_sync[scope.id].isoformat() if scope and last_sync.get(scope.id) else None,
            "revision": scope.revision if scope else None,
        }
        if client_slug and not (client and client.slug == client_slug) and not (
                suggestion and suggestion.get("client") and suggestion["client"]["slug"] == client_slug):
            continue
        rows.append(row)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    return {"rows": rows, "counts": counts,
            "clients": [_client(b) for b, _ in clients],
            "installed": len(rows) if client_slug is None else None}


def _location(s, location_id: str) -> LeadLockLocation:
    loc = s.execute(select(LeadLockLocation).where(LeadLockLocation.location_id == location_id)).scalar_one_or_none()
    if loc is None or loc.state == "uninstalled":
        raise ConnectionsError("the LeadLock app is not installed on that sub-account")
    return loc


def _scope(s, location_id: str) -> SourceScope | None:
    return s.execute(select(SourceScope).where(SourceScope.connector_account_id == _account(s).id,
        SourceScope.kind == KIND, SourceScope.external_id == location_id)).scalar_one_or_none()


def start_collection(s, scope_id: UUID, *, explicit: bool = True) -> str:
    """Linking starts collection. Call it in its own transaction after the mapping commits: queueing locks the
    sync stream, and a page job holds that stream while it waits for the scope the mapping locked (deadlock).
    If this step is lost, the scheduler's sweep finds the idle live source and starts it anyway."""
    scope = s.get(SourceScope, scope_id)
    business = s.get(Business, scope.business_id) if scope.business_id else None
    if business is not None and business.status != "active":
        return "waiting_client_archived"
    account = s.get(ConnectorAccount, scope.connector_account_id)
    if account.provider == PROVIDER and _location(s, scope.external_id).state != "active":
        return "waiting_access"
    if not is_live(s, scope) or account.state != "active":
        return "not_live"
    try:
        return sync.collect(s, scope.id, explicit=explicit)
    except ValueError:  # it stopped being live between the checks and the request
        return "not_live"


def map_location(s, location_id: str, client_slug: str, *, expected_revision: int | None, actor: str,
                 reactivate: bool = False) -> dict:
    _location(s, location_id)
    business = mapping.business_by_slug(s, client_slug)
    scope = _scope(s, location_id)
    if scope is not None and scope.state == "excluded":
        raise ConnectionsError("this sub-account is marked “not a client”; restore it first")
    if scope is not None and expected_revision is not None:
        mapping._check(scope, expected_revision)
    moved = 0
    if scope is not None and scope.state == "approved" and scope.business_id and scope.business_id != business.id:
        moved = s.execute(select(func.count()).select_from(RecordAssociation).join(
            SourceRecord, SourceRecord.id == RecordAssociation.record_id).where(
            SourceRecord.scope_id == scope.id, RecordAssociation.business_id == scope.business_id,
            RecordAssociation.basis == "scope_mapping", RecordAssociation.status == "associated")).scalar_one()
    if reactivate and business.status != "active":
        mapping.set_client_status(s, business.id, "active", expected_revision=None, actor=actor)
    if scope is None:
        scope = mapping.add_scope_by_id(s, PROVIDER, KIND, location_id, business_id=business.id, actor=actor)
    else:
        scope = mapping.assign_scope(s, scope.id, business_id=business.id, expected_revision=expected_revision,
                                     actor=actor)
    s.flush()
    # The caller starts collection after this commits (start_collection).
    return {"scope_id": str(scope.id), "moved_records": moved, "revision": scope.revision}


def unmap_location(s, location_id: str, *, expected_revision: int | None, actor: str) -> dict:
    _location(s, location_id)
    scope = _scope(s, location_id)
    if scope is None:
        raise ConnectionsError("this sub-account is not mapped")
    mapping.unassign_scope(s, scope.id, expected_revision=expected_revision, actor=actor)
    return {"revision": scope.revision}


def mark_not_a_client(s, location_id: str, *, expected_revision: int | None, actor: str,
                      reason: str | None = None) -> dict:
    """Remember that a sub-account is not a KB client (WIA's own, demo, or another business)."""
    loc = _location(s, location_id)
    scope = _scope(s, location_id)
    if scope is not None and scope.state == "approved":
        raise ConnectionsError("unmap this sub-account before marking it “not a client”")
    if scope is None:
        scope = SourceScope(id=uuid4(), connector_account_id=_account(s).id, kind=KIND, external_id=location_id,
                            name=(loc.name or location_id)[:500], parent_name="LeadLock", state="candidate",
                            default_domain="leads", association_mode="dedicated",
                            suggestion_reason="added from Connections", revision=1)
        s.add(scope)
        s.flush()
    mapping.exclude_scope(s, scope.id, expected_revision=expected_revision, actor=actor,
                          reason=reason or "not a client")
    return {"revision": scope.revision}


def restore_location(s, location_id: str, *, expected_revision: int | None, actor: str) -> dict:
    _location(s, location_id)
    scope = _scope(s, location_id)
    if scope is None:
        raise ConnectionsError("nothing to restore")
    mapping.restore_scope(s, scope.id, expected_revision=expected_revision, actor=actor)
    return {"revision": scope.revision}
