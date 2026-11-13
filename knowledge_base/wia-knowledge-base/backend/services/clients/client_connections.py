"""Connections, client by client (5 Nov): each client and the channels the KB reads it from.

Five channels, because that is how intake actually works:
  leadlock, slack, clickup, drive   dedicated: a sub-account / channel / list / folder belongs to one client and is
                                    only read once linked (unlinked ones are never read)
  contacts                          shared: hello@ email, the team calendars and Fathom are read account-wide, and a
                                    message or meeting attaches to a client only through its approved contacts

Each (client, channel) cell has one state:
  linked          at least one linked source (or approved contact)
  paused          linked, but the client is archived, so nothing of it is read
  suggested       nothing linked yet; something waits for a person to confirm
  missing         nothing linked or suggested
  not_applicable  an admin said the channel isn't part of this client's engagement
  not_connected   the KB has no account for that provider
Commands go through `mapping` (and `connections` for LeadLock sub-accounts), so the rules live in one place.
"""
from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select

from backend.models.db import (Business, ClientSourceDecision, ConnectorAccount, Contact, SourceRecord, SourceScope,
                               SyncRun)
from backend.services.clients import connections, mapping

DEDICATED = ("leadlock", "slack", "clickup", "drive")
SHARED = ("gmail", "calendar", "fathom")  # the "contacts" channel
CHANNELS = [
    {"id": "leadlock", "label": "LeadLock", "kind": "dedicated", "unit": "sub-account"},
    {"id": "slack", "label": "Slack", "kind": "dedicated", "unit": "channel"},
    {"id": "clickup", "label": "ClickUp", "kind": "dedicated", "unit": "list"},
    {"id": "drive", "label": "Drive", "kind": "dedicated", "unit": "folder"},
    {"id": "contacts", "label": "Email & meetings", "kind": "shared", "unit": "contact"},
]


def _providers_of(channel: str) -> tuple[str, ...]:
    return SHARED if channel == "contacts" else (channel,)


def overview(s) -> dict:
    accounts = {a.provider: a for a in s.execute(select(ConnectorAccount)).scalars()}
    businesses = s.execute(select(Business).order_by(Business.status, func.lower(Business.name))).scalars().all()
    scopes = s.execute(select(SourceScope).where(SourceScope.connector_account_id.in_(
        [a.id for p, a in accounts.items() if p in DEDICATED]))).scalars().all()
    provider_of = {a.id: p for p, a in accounts.items()}
    records = dict(s.execute(select(SourceRecord.scope_id, func.count()).group_by(SourceRecord.scope_id)).all())
    last_sync = dict(s.execute(select(SyncRun.scope_id, func.max(SyncRun.finished_at)).where(
        SyncRun.state.in_(("succeeded", "partial")), SyncRun.mode != "discovery").group_by(SyncRun.scope_id)).all())
    not_applicable = {(d.business_id, d.provider): d.reason for d in s.execute(select(ClientSourceDecision)).scalars()}
    contacts = defaultdict(list)
    for c in s.execute(select(Contact).where(Contact.status.in_(("approved", "candidate"))).order_by(Contact.email, Contact.domain)).scalars():
        contacts[c.business_id].append(c)

    def item(scope: SourceScope) -> dict:
        return {"ref": {"kind": "scope", "id": str(scope.id)}, "name": scope.name, "parent": scope.parent_name,
                "records": records.get(scope.id, 0),
                "last_synced_at": last_sync[scope.id].isoformat() if last_sync.get(scope.id) else None,
                "revision": scope.revision, "reason": scope.suggestion_reason}

    linked, suggested = defaultdict(list), defaultdict(list)
    options = {p: [] for p in DEDICATED if p != "leadlock"}  # unlinked sources a person can pick from
    for scope in scopes:
        p = provider_of[scope.connector_account_id]
        if p == "leadlock":
            continue  # LeadLock comes from the app's own sub-account list below
        if scope.state == "approved" and scope.business_id:
            linked[(scope.business_id, p)].append(item(scope))
        elif scope.state == "candidate":
            options[p].append({"ref": {"kind": "scope", "id": str(scope.id)}, "name": scope.name,
                               "parent": scope.parent_name, "revision": scope.revision})
            if scope.suggested_business_id:
                suggested[(scope.suggested_business_id, p)].append(item(scope))

    leadlock = connections.leadlock_rows(s) if "leadlock" in accounts else {"rows": []}
    by_slug = {b.slug: b.id for b in businesses}
    unassigned = []
    for r in leadlock["rows"]:
        entry = {"ref": {"kind": "location", "id": r["location_id"]}, "name": r["name"], "parent": "LeadLock",
                 "records": r["records"], "last_synced_at": r["last_synced_at"], "revision": r["revision"],
                 "collection": r["collection"], "access": r["access"]}
        if r["state"] == "mapped":
            linked[(by_slug[r["client"]["slug"]], "leadlock")].append(entry)
        elif r["state"] == "suggested" and r["suggestion"]["kind"] == "client":
            suggested[(by_slug[r["suggestion"]["client"]["slug"]], "leadlock")].append({**entry, "reason": r["suggestion"]["reason"]})
        else:
            unassigned.append(r)
    options["leadlock"] = [{"ref": {"kind": "location", "id": r["location_id"]}, "name": r["name"], "parent": "LeadLock",
                            "revision": r["revision"]} for r in leadlock["rows"]
                           if r["state"] in ("suggested", "needs_client") and r["access"] == "active"]

    out = []
    for b in businesses:
        cells = {}
        for ch in CHANNELS:
            cid, providers = ch["id"], _providers_of(ch["id"])
            na = next((not_applicable[(b.id, p)] for p in providers if (b.id, p) in not_applicable), None)
            if cid == "contacts":
                mine = contacts.get(b.id, [])
                cell = {"linked": [_contact(c) for c in mine if c.status == "approved"],
                        "suggested": [_contact(c) for c in mine if c.status == "candidate"]}
                connected = any(p in accounts for p in providers)
            else:
                cell = {"linked": linked.get((b.id, cid), []), "suggested": suggested.get((b.id, cid), [])}
                connected = cid in accounts
            cell["not_applicable"] = na
            cell["state"] = ("not_connected" if not connected else
                             "not_applicable" if na and not cell["linked"] else
                             ("paused" if b.status != "active" else "linked") if cell["linked"] else
                             "suggested" if cell["suggested"] else "missing")
            cells[cid] = cell
        out.append({"slug": b.slug, "name": b.name, "status": b.status, "revision": b.revision, "cells": cells,
                    # A waiting suggestion needs a person whatever the client's status; a gap only matters while active.
                    "needs_attention": any(c["state"] == "suggested" or (c["state"] == "missing" and b.status == "active")
                                           for c in cells.values())})
    return {"channels": CHANNELS, "clients": out, "options": options,
            "accounts": {p: a.display_identity for p, a in accounts.items()},
            "unassigned_leadlock": {"count": len(unassigned),
                                    "by_state": {st: sum(1 for r in unassigned if r["state"] == st)
                                                 for st in ("needs_client", "suggested", "access_failed", "not_a_client")}}}


def _contact(c: Contact) -> dict:
    return {"ref": {"kind": "contact", "id": str(c.id)}, "name": c.email or f"anyone @{c.domain}",
            "display_name": c.display_name, "origin": c.origin, "revision": c.revision}


# Commands -----------------------------------------------------------------------------------------------------

def link(s, *, client: str, channel: str, ref: dict, expected_revision: int | None, actor: str,
         reactivate: bool = False) -> dict:
    if channel == "leadlock":
        if ref.get("kind") != "location":
            raise mapping.MappingError("a LeadLock link needs a sub-account")
        return connections.map_location(s, ref["id"], client, expected_revision=expected_revision, actor=actor,
                                        reactivate=reactivate)
    if channel == "contacts":
        if ref.get("kind") != "contact":
            raise mapping.MappingError("pick a suggested contact, or add an address")
        contact = mapping.review_contact(s, UUID(ref["id"]), approve=True, expected_revision=expected_revision,
                                         actor=actor, business_id=mapping.business_by_slug(s, client).id)
        return {"revision": contact.revision, "collection": "via_contacts"}
    scope = _dedicated_scope(s, channel, ref)
    business = mapping.business_by_slug(s, client)
    if reactivate and business.status != "active":
        mapping.set_client_status(s, business.id, "active", expected_revision=None, actor=actor)
    mapping.assign_scope(s, scope.id, business_id=business.id, expected_revision=expected_revision, actor=actor)
    s.flush()
    # The caller starts collection after this commits (connections.start_collection).
    return {"revision": scope.revision, "scope_id": str(scope.id)}


def unlink(s, *, channel: str, ref: dict, expected_revision: int | None, actor: str) -> dict:
    if channel == "leadlock":
        return connections.unmap_location(s, ref["id"], expected_revision=expected_revision, actor=actor)
    if channel == "contacts":
        contact = mapping.review_contact(s, UUID(ref["id"]), approve=False, expected_revision=expected_revision, actor=actor)
        return {"revision": contact.revision}
    scope = _dedicated_scope(s, channel, ref)
    mapping.unassign_scope(s, scope.id, expected_revision=expected_revision, actor=actor)
    return {"revision": scope.revision}


def add_contact(s, *, client: str, value: str, actor: str) -> dict:
    value = value.strip().lower().lstrip("@")
    business = mapping.business_by_slug(s, client)
    contact = (mapping.add_contact(s, business.id, actor=actor, email=value) if "@" in value
               else mapping.add_contact(s, business.id, actor=actor, domain=value))
    return {"revision": contact.revision}


def set_applicable(s, *, client: str, channel: str, applicable: bool, reason: str | None, actor: str) -> dict:
    business = mapping.business_by_slug(s, client)
    for provider in _providers_of(channel):
        if applicable:
            mapping.clear_not_applicable(s, business.id, provider, actor=actor)
        else:
            mapping.mark_not_applicable(s, business.id, provider, reason=reason or "not part of this engagement",
                                        actor=actor)
    return {}


def _dedicated_scope(s, channel: str, ref: dict) -> SourceScope:
    if channel not in DEDICATED or ref.get("kind") != "scope":
        raise mapping.MappingError(f"unknown channel or source for {channel}")
    scope = s.get(SourceScope, UUID(ref["id"]))
    if scope is None or s.get(ConnectorAccount, scope.connector_account_id).provider != channel:
        raise mapping.MappingError("that source isn't part of this channel")
    if scope.association_mode == "per_record" and scope.state == "approved":
        raise mapping.MappingError("that source is shared across clients and is attached by contacts")
    return scope
