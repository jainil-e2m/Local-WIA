"""S2 client mapping commands. The CLI calls them today; the admin API and UI (S10/S11/S13) call the
same functions, so the mapping rules live in one place.

Every command writes an audit event. Commands on an existing object take `expected_revision`, so two
admins cannot silently overwrite each other (None skips the check: bootstrap files and the CLI).
Archiving a client pauses its syncing; see `backend.services.intake.scoping`.
"""
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.models.db import (
    AuditEvent,
    Business,
    BusinessAlias,
    ClientSourceDecision,
    ConnectorAccount,
    Contact,
    RecordAssociation,
    SenderRule,
    SourceRecord,
    SourceScope,
    SyncStream,
)
from backend.models.db.base import utcnow
from backend.services.intake import requalify
from backend.services.read_models import portfolio
from backend.services.intake.adapters import PROVIDERS
from backend.services.intake.scoping import live_scope
from backend.services.shared.emails import PUBLIC_DOMAINS, clean, is_internal, is_platform_domain, within
from backend.services.shared.errors import IntakeError
from backend.workers import queue

DISCOVER_JOB = "client.discover"


class MappingError(ValueError):
    pass


class RevisionConflict(MappingError):
    """The object changed since the admin loaded it; reload and retry."""


def _check(obj, expected_revision: int | None) -> None:
    if expected_revision is not None and obj.revision != expected_revision:
        raise RevisionConflict(f"{type(obj).__name__} {obj.id} is at revision {obj.revision}, "
                               f"not {expected_revision}")


def _audit(s, actor: str, action: str, target_type: str, target_id, **details) -> None:
    s.add(AuditEvent(actor=actor, action=action, target_type=target_type, target_id=str(target_id),
                     details=details))
    portfolio.request_refresh(s)  # every mapping decision changes what the portfolio shows


def _business(s, business_id: UUID) -> Business:
    business = s.get(Business, business_id, with_for_update=True)
    if business is None:
        raise MappingError(f"unknown client {business_id}")
    return business


def business_by_slug(s, slug: str) -> Business:
    business = s.execute(select(Business).where(Business.slug == slug)).scalar_one_or_none()
    if business is None:
        raise MappingError(f"unknown client slug {slug!r}")
    return business


# Clients

def create_client(s, *, name: str, slug: str, aliases=(), actor: str, discover: bool = True) -> Business:
    if s.execute(select(Business.id).where(Business.slug == slug)).first():
        raise MappingError(f"client slug {slug!r} already exists")
    business = Business(id=uuid4(), name=name, slug=slug, status="active", revision=1)
    s.add(business)
    s.flush()
    for alias in {name, *aliases}:
        s.add(BusinessAlias(id=uuid4(), business_id=business.id, alias=alias))
    _audit(s, actor, "business.create", "business", business.id, slug=slug)
    if discover:
        enqueue_discovery(s, business)
    return business


def update_client(s, business_id: UUID, *, expected_revision: int | None, actor: str,
                  name: str | None = None, add_aliases=(), remove_aliases=()) -> Business:
    business = _business(s, business_id)
    _check(business, expected_revision)
    if name and name != business.name:
        business.name = name
    existing = {a.alias: a for a in s.execute(
        select(BusinessAlias).where(BusinessAlias.business_id == business.id)).scalars()}
    for alias in add_aliases:
        if alias not in existing:
            s.add(BusinessAlias(id=uuid4(), business_id=business.id, alias=alias))
    for alias in remove_aliases:
        if alias in existing:
            s.delete(existing[alias])
    business.revision += 1
    _audit(s, actor, "business.update", "business", business.id, name=name,
           add_aliases=list(add_aliases), remove_aliases=list(remove_aliases))
    return business


def set_client_status(s, business_id: UUID, status: str, *, expected_revision: int | None,
                      actor: str) -> Business:
    """Archive (`inactive`) pauses syncing of the client's dedicated scopes and contacts; cursors and
    history stay. Reactivating needs nothing more here: the scheduler sees `status_changed_at` is newer than
    each stream's last full re-check and re-reads it (sync.sweep), and resumes copies the archive stopped."""
    if status not in ("active", "inactive"):
        raise MappingError("status must be active or inactive")
    business = _business(s, business_id)
    _check(business, expected_revision)
    if business.status == status:
        return business
    previous_change = business.status_changed_at
    business.status, business.status_changed_at = status, utcnow()
    business.revision += 1
    if status == "inactive":
        _reanchor_shared_streams(s, business.id)
    else:
        requalify.request_for_business(s, business.id)  # shared-source records from the paused period (P-02)
    _audit(s, actor, "business.archive" if status == "inactive" else "business.reactivate", "business",
           business.id, paused_since=previous_change.isoformat() if status == "active" and previous_change else None)
    return business


def _reanchor_shared_streams(s, business_id: UUID) -> None:
    """Drive streams are account-wide and anchored on one folder scope; never leave one anchored on a
    paused client's folder while other clients' folders are live."""
    for stream in s.execute(select(SyncStream).join(SourceScope, SourceScope.id == SyncStream.scope_id).where(
            SourceScope.business_id == business_id, SyncStream.stream_key == "drive:account")).scalars():
        other = s.execute(select(SourceScope.id).where(
            SourceScope.connector_account_id == stream.connector_account_id, SourceScope.business_id != business_id,
            live_scope()).limit(1)).scalar_one_or_none()
        if other:
            stream.scope_id = other


# Scopes

# A LeadLock sub-account is one venue and its contacts are that venue's leads, not the client's own
# contacts, so it can never qualify records "by contact": it is dedicated to one client or not read at all.
DEDICATED_ONLY = {"leadlock"}


def _provider(s, scope: SourceScope) -> str:
    return s.get(ConnectorAccount, scope.connector_account_id).provider


def assign_scope(s, scope_id: UUID, *, business_id: UUID | None, expected_revision: int | None,
                 actor: str) -> SourceScope:
    """Approve a scope. With a client it is dedicated to that client; without one it is shared and
    qualifies records one at a time by approved contacts.

    Re-pointing a dedicated scope at another client moves the records it already collected: ingestion
    only ever adds associations, so without this the old client would keep them (the 3 Nov Drive trap)."""
    scope = s.get(SourceScope, scope_id, with_for_update=True)
    if scope is None:
        raise MappingError(f"unknown scope {scope_id}")
    _check(scope, expected_revision)
    if business_id is None and _provider(s, scope) in DEDICATED_ONLY:
        raise MappingError(f"{_provider(s, scope)} scopes belong to exactly one client; choose the client")
    if business_id is not None:
        _business(s, business_id)
    previous = scope.business_id if scope.state == "approved" and scope.association_mode == "dedicated" else None
    moved = 0
    if previous and business_id and previous != business_id:
        moved = _move_dedicated_records(s, scope, previous, business_id)
    scope.association_mode, scope.business_id = ("dedicated", business_id) if business_id else ("per_record", None)
    scope.state, scope.approved_at, scope.approved_by = "approved", utcnow(), actor
    scope.revision += 1
    _audit(s, actor, "scope.approved", "source_scope", scope.id, business_id=str(business_id) if business_id else None,
           mode=scope.association_mode, previous_business_id=str(previous) if previous else None,
           moved_records=moved)
    return scope


def _move_dedicated_records(s, scope: SourceScope, old_business_id: UUID, new_business_id: UUID) -> int:
    """Re-attach every record this scope collected for the old client to the new one. The old link is kept
    as `rejected` (who it pointed at stays auditable); records linked by other means are left alone."""
    links = s.execute(select(RecordAssociation).join(SourceRecord, SourceRecord.id == RecordAssociation.record_id)
                      .where(SourceRecord.scope_id == scope.id, RecordAssociation.business_id == old_business_id,
                             RecordAssociation.basis == "scope_mapping", RecordAssociation.status == "associated")
                      .with_for_update(of=RecordAssociation)).scalars().all()
    for link in links:
        link.status = "rejected"
        stmt = pg_insert(RecordAssociation).values(id=uuid4(), record_id=link.record_id, business_id=new_business_id,
                                                   basis="scope_mapping", status="associated", multi_client=False,
                                                   created_at=utcnow())
        s.execute(stmt.on_conflict_do_update(index_elements=["record_id", "business_id"],
                                             set_={"status": "associated", "basis": "scope_mapping"}))
    s.flush()
    return len(links)


def unassign_scope(s, scope_id: UUID, *, expected_revision: int | None, actor: str) -> SourceScope:
    """Stop reading a scope and return it to the unmapped list. What it already collected stays with the
    client it was collected for (to move it instead, map the scope to the right client)."""
    scope = s.get(SourceScope, scope_id, with_for_update=True)
    if scope is None:
        raise MappingError(f"unknown scope {scope_id}")
    _check(scope, expected_revision)
    if scope.state != "approved":
        raise MappingError("only a mapped scope can be unmapped")
    previous = scope.business_id
    scope.state, scope.business_id, scope.approved_at, scope.approved_by = "candidate", None, None, None
    scope.association_mode = "dedicated" if _provider(s, scope) in DEDICATED_ONLY else scope.association_mode
    scope.revision += 1
    _audit(s, actor, "scope.unmapped", "source_scope", scope.id,
           previous_business_id=str(previous) if previous else None)
    return scope


def exclude_scope(s, scope_id: UUID, *, expected_revision: int | None, actor: str,
                  reason: str | None = None) -> SourceScope:
    scope = s.get(SourceScope, scope_id, with_for_update=True)
    if scope is None:
        raise MappingError(f"unknown scope {scope_id}")
    _check(scope, expected_revision)
    scope.state = "excluded"
    scope.revision += 1
    _audit(s, actor, "scope.excluded", "source_scope", scope.id, reason=reason)
    return scope


def restore_scope(s, scope_id: UUID, *, expected_revision: int | None, actor: str) -> SourceScope:
    """Undo an exclusion: the scope is unmapped again and waits for an admin."""
    scope = s.get(SourceScope, scope_id, with_for_update=True)
    if scope is None:
        raise MappingError(f"unknown scope {scope_id}")
    _check(scope, expected_revision)
    if scope.state != "excluded":
        raise MappingError("only an excluded scope can be restored")
    scope.state = "candidate"
    scope.revision += 1
    _audit(s, actor, "scope.restored", "source_scope", scope.id)
    return scope


def add_scope_by_id(s, provider: str, kind: str, external_id: str, *, business_id: UUID, actor: str,
                    describe=None) -> SourceScope:
    """G-02: an admin adds a scope discovery did not propose (archived list, unhelpful name). The
    adapter confirms it exists and is readable before it is approved."""
    account = s.execute(select(ConnectorAccount).where(ConnectorAccount.provider == provider)).scalar_one_or_none()
    if account is None:
        raise MappingError(f"{provider} is not connected")
    scope = s.execute(select(SourceScope).where(SourceScope.connector_account_id == account.id,
        SourceScope.kind == kind, SourceScope.external_id == external_id)).scalar_one_or_none()
    if scope is None:
        if describe is None:
            from backend.services.intake.adapters import get_adapter
            adapter = get_adapter(provider)
            if not hasattr(adapter, "describe_scope"):
                raise MappingError(f"adding a scope by ID is not supported for {provider}")
            describe = adapter.describe_scope
        try:
            found = describe(kind, external_id)
        except IntakeError as exc:
            raise MappingError(f"{provider} {kind} {external_id} is not readable: {exc}") from exc
        scope = SourceScope(id=uuid4(), connector_account_id=account.id, kind=kind, external_id=external_id,
                            name=found.name[:500], parent_name=found.parent_name, state="candidate",
                            default_domain=found.default_domain, association_mode="dedicated",
                            discovery_stats=found.stats, suggestion_reason="added by ID", revision=1)
        s.add(scope)
        s.flush()
    return assign_scope(s, scope.id, business_id=business_id, expected_revision=None, actor=actor)


# Contacts

def add_contact(s, business_id: UUID, *, actor: str, email: str | None = None, domain: str | None = None) -> Contact:
    email, domain = clean(email), (domain or "").strip().lower() or None
    if bool(email) == bool(domain):
        raise MappingError("give exactly one of email or domain")
    if domain in PUBLIC_DOMAINS:
        raise MappingError(f"{domain} is a public email domain; approve the person's address instead")
    _business(s, business_id)
    q = select(Contact).where(Contact.business_id == business_id)
    contact = s.execute(q.where(Contact.email == email) if email else q.where(Contact.domain == domain)).scalar_one_or_none()
    if contact is None or contact.status != "approved":
        if contact is None:
            contact = Contact(id=uuid4(), business_id=business_id, email=email, domain=domain, status="approved",
                              origin="manual", revision=1)
            s.add(contact)
            s.flush()
        else:
            contact.status = "approved"
            contact.revision += 1
        requalify.request(s, contact)  # attach what was read before this approval (P-02)
    _audit(s, actor, "contact.approved", "contact", contact.id, business_id=str(business_id))
    return contact


def review_contact(s, contact_id: UUID, *, approve: bool, expected_revision: int | None, actor: str,
                   business_id: UUID | None = None) -> Contact:
    contact = s.get(Contact, contact_id, with_for_update=True)
    if contact is None:
        raise MappingError(f"unknown contact {contact_id}")
    _check(contact, expected_revision)
    if approve and contact.domain in PUBLIC_DOMAINS:
        raise MappingError(f"{contact.domain} is a public email domain and cannot be approved")
    if business_id is not None and business_id != contact.business_id:
        _business(s, business_id)
        contact.business_id = business_id
    contact.status = "approved" if approve else "rejected"
    contact.revision += 1
    if approve:
        requalify.request(s, contact)
    _audit(s, actor, f"contact.{contact.status}", "contact", contact.id, business_id=str(contact.business_id))
    return contact


# Sender rules: team, partner and blocked senders, for every client

SENDER_KINDS = ("team", "partner", "blocked")


class SenderRules:
    """Matcher over the admin's sender rules. An exact address rule wins over a domain rule."""

    def __init__(self, rules):
        self.by_email = {r.email: r.kind for r in rules if r.email}
        self.by_domain = {r.domain: r.kind for r in rules if r.domain}

    def kind_of(self, email: str | None = None, domain: str | None = None) -> str | None:
        if email and email in self.by_email:
            return self.by_email[email]
        domain = domain or (email.split("@", 1)[1] if email and "@" in email else None)
        for root, kind in self.by_domain.items():
            if within(domain, [root]):
                return kind
        return None


def sender_rules(s) -> SenderRules:
    return SenderRules(s.execute(select(SenderRule)).scalars().all())


def add_sender_rule(s, kind: str, *, actor: str, reason: str, email: str | None = None,
                    domain: str | None = None) -> SenderRule:
    if kind not in SENDER_KINDS:
        raise MappingError(f"kind must be one of {', '.join(SENDER_KINDS)}")
    email, domain = clean(email), (domain or "").strip().lower().lstrip("@") or None
    if bool(email) == bool(domain):
        raise MappingError("give exactly one of email or domain")
    if domain and domain in PUBLIC_DOMAINS:
        raise MappingError(f"{domain} is a public email domain; rule on the person's address instead")
    if not reason.strip():
        raise MappingError("say why")
    q = select(SenderRule).where(SenderRule.email == email) if email else select(SenderRule).where(SenderRule.domain == domain)
    rule = s.execute(q).scalar_one_or_none()
    if rule is None:
        rule = SenderRule(id=uuid4(), email=email, domain=domain)
        s.add(rule)
    rule.kind, rule.reason, rule.created_by, rule.created_at = kind, reason[:300], actor, utcnow()
    _audit(s, actor, f"sender_rule.{kind}", "sender_rule", rule.id, email=email, domain=domain, reason=reason)
    return rule


def remove_sender_rule(s, *, actor: str, email: str | None = None, domain: str | None = None) -> None:
    email, domain = clean(email), (domain or "").strip().lower().lstrip("@") or None
    q = select(SenderRule).where(SenderRule.email == email) if email else select(SenderRule).where(SenderRule.domain == domain)
    rule = s.execute(q).scalar_one_or_none()
    if rule is not None:
        s.delete(rule)
        _audit(s, actor, "sender_rule.removed", "sender_rule", rule.id, email=email, domain=domain)


def contact_conflicts(s) -> list[tuple[Contact, str]]:
    """Approved contacts that a sender rule or the built-in filters now say are not client contacts.
    A partner kept on a client's record is a link, not a conflict (see partner_links)."""
    from backend.models.db.people import INTERNAL_KINDS, Person, PersonAddress
    roster_emails = set(s.execute(select(PersonAddress.value).join(Person, Person.id == PersonAddress.person_id)
        .where(Person.kind.in_(INTERNAL_KINDS), Person.merged_into_id.is_(None),
               PersonAddress.kind.in_(("email", "fathom_email")))).scalars())
    rules, out = sender_rules(s), []
    for c in s.execute(select(Contact).where(Contact.status == "approved")).scalars():
        kind = rules.kind_of(c.email, c.domain)
        domain = c.domain or (c.email.split("@", 1)[1] if c.email else None)
        if c.email and c.email.lower() in roster_emails:
            out.append((c, "team member (roster)"))
            continue
        if kind == "partner":
            continue
        if kind:
            out.append((c, f"{kind} sender rule"))
        elif is_platform_domain(domain):
            out.append((c, "platform domain"))
        elif (c.email and is_internal(c.email)) or within(domain, ["weddingindustryads.com", "leadlockpro.com"]):
            out.append((c, "internal address"))
    return out


def partner_links(s) -> dict[str, list[str]]:
    """Partner rule ("@domain" or address) -> slugs of clients that keep it as an approved contact.
    The admin page shows these as "partner, linked to ..."; linked partners never decide association."""
    rules = sender_rules(s)
    links = {("@" + d if d else e): [] for e, d, k in s.execute(
        select(SenderRule.email, SenderRule.domain, SenderRule.kind)) if k == "partner"}
    for c, slug in s.execute(select(Contact, Business.slug).join(Business, Business.id == Contact.business_id)
                             .where(Contact.status == "approved")):
        if rules.kind_of(c.email, c.domain) != "partner":
            continue
        for key in links:
            if (key.startswith("@") and within(c.domain or c.email.split("@", 1)[1], [key[1:]])) or key == c.email:
                links[key].append(slug)
    return links


# Sources that do not apply

def mark_not_applicable(s, business_id: UUID, provider: str, *, reason: str, actor: str) -> ClientSourceDecision:
    if provider not in PROVIDERS:
        raise MappingError(f"unknown provider {provider!r}")
    if not reason.strip():
        raise MappingError("say why the source does not apply")
    _business(s, business_id)
    decision = s.execute(select(ClientSourceDecision).where(ClientSourceDecision.business_id == business_id,
        ClientSourceDecision.provider == provider)).scalar_one_or_none()
    if decision is None:
        decision = ClientSourceDecision(id=uuid4(), business_id=business_id, provider=provider)
        s.add(decision)
    decision.state, decision.reason, decision.decided_by, decision.decided_at = "not_applicable", reason[:300], actor, utcnow()
    _audit(s, actor, "source.not_applicable", "business", business_id, provider=provider, reason=reason)
    return decision


def clear_not_applicable(s, business_id: UUID, provider: str, *, actor: str) -> None:
    decision = s.execute(select(ClientSourceDecision).where(ClientSourceDecision.business_id == business_id,
        ClientSourceDecision.provider == provider)).scalar_one_or_none()
    if decision is not None:
        s.delete(decision)
        _audit(s, actor, "source.applicable", "business", business_id, provider=provider)


# Discovery for one client

def enqueue_discovery(s, business: Business) -> None:
    """Adding a client proposes its scopes and contacts within minutes, as a background job."""
    queue.enqueue(s, DISCOVER_JOB, "maintenance", f"discover:{business.id}:{business.revision}",
                  {"business_id": str(business.id)})


# Coverage: the S2 done-when, one row per client and source

def coverage(s) -> list[dict]:
    """Every (client, source) cell is one of: mapped, via_contacts, paused, not_applicable, suggested,
    missing, not_connected. "missing" is what must reach zero before the production backfill."""
    accounts = {a.provider: a for a in s.execute(select(ConnectorAccount)).scalars()}
    shared = {p for (p,) in s.execute(select(ConnectorAccount.provider).join(
        SourceScope, SourceScope.connector_account_id == ConnectorAccount.id).where(
        SourceScope.state == "approved", SourceScope.association_mode == "per_record").distinct())}
    dedicated = {(b, p): n for b, p, n in s.execute(select(SourceScope.business_id, ConnectorAccount.provider,
        func.count()).join(ConnectorAccount).where(SourceScope.state == "approved",
        SourceScope.business_id.is_not(None)).group_by(SourceScope.business_id, ConnectorAccount.provider))}
    suggested = {(b, p): n for b, p, n in s.execute(select(SourceScope.suggested_business_id, ConnectorAccount.provider,
        func.count()).join(ConnectorAccount).where(SourceScope.state == "candidate",
        SourceScope.suggested_business_id.is_not(None)).group_by(SourceScope.suggested_business_id,
        ConnectorAccount.provider))}
    contacts = {(b, st): n for b, st, n in s.execute(select(Contact.business_id, Contact.status, func.count())
        .group_by(Contact.business_id, Contact.status))}
    not_applicable = {(d.business_id, d.provider): d.reason for d in s.execute(select(ClientSourceDecision)).scalars()}

    rows = []
    for b in s.execute(select(Business).order_by(Business.status, Business.name)).scalars():
        cells = {}
        for provider in PROVIDERS:
            n = dedicated.get((b.id, provider), 0)
            approved_contacts = contacts.get((b.id, "approved"), 0)
            if provider not in accounts:
                cells[provider] = ("not_connected", "")
            elif (b.id, provider) in not_applicable:
                cells[provider] = ("not_applicable", not_applicable[(b.id, provider)])
            elif n and b.status != "active":
                cells[provider] = ("paused", f"{n} scope(s)")
            elif n:
                cells[provider] = ("mapped", f"{n} scope(s)")
            elif provider in shared and approved_contacts:
                cells[provider] = ("paused" if b.status != "active" else "via_contacts", f"{approved_contacts} contact(s)")
            elif suggested.get((b.id, provider)) or (provider in shared and contacts.get((b.id, "candidate"))):
                cells[provider] = ("suggested", "awaiting review")
            else:
                cells[provider] = ("missing", "")
        rows.append({"business_id": b.id, "slug": b.slug, "name": b.name, "status": b.status,
                     "revision": b.revision, "cells": cells})
    return rows
