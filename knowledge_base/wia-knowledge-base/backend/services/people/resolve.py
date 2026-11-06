"""Deterministic people resolution. Identity resolution never changes client association."""
from collections import Counter, defaultdict
from datetime import date
import unicodedata
from uuid import uuid4

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError

from backend.models.db import (AuditEvent, ConnectorAccount, Contact, ContentUnit, ProviderIdentity,
                              SenderRule)
from backend.models.db.base import utcnow
from backend.models.db.people import INTERNAL_KINDS, MailboxHolder, Person, PersonAddress
from backend.services.shared.emails import INTERNAL_DOMAINS, clean, domain_of, is_automated_sender, is_internal, within


def name_key(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value or "").casefold()
                            if not unicodedata.combining(c)).split())


class Resolver:
    """Run/page snapshot of lookup data; resolution of an existing person makes no queries.

    Approved contacts of archived clients are deliberately included for historical
    attribution. Team/partner/blocked rules never qualify a contact as a client.
    """

    def __init__(self, s):
        # Hold a stable roster through publication. Merges also lock people before
        # identities, so they cannot scan identities and then miss a late loser link.
        self.people = {p.id: p for p in s.execute(select(Person).order_by(Person.id)
            .with_for_update(read=True).execution_options(populate_existing=True)).scalars()}
        self.addresses = defaultdict(set)
        self.contact_addresses = set()
        self.names = defaultdict(set)
        for p in self.people.values():
            if p.kind in INTERNAL_KINDS and p.merged_into_id is None:
                self.names[name_key(p.name)].add(p.id)
        for a in s.execute(select(PersonAddress)).scalars():
            pid = self.canonical_id(a.person_id)
            if pid:
                key = a.value.lower() if a.kind in ("email", "fathom_email") else a.value
                self.addresses[(a.kind, key)].add(pid)
                if a.source == "client_contact":
                    self.contact_addresses.add((a.kind, key, pid))
                if a.kind == "display_name" and self.people[pid].kind in INTERNAL_KINDS:
                    self.names[name_key(a.value)].add(pid)
        self.providers = dict(s.execute(select(ConnectorAccount.id, ConnectorAccount.provider)).all())
        self.rules = list(s.execute(select(SenderRule)).scalars())
        self.exact_rules = {r.email: r.kind for r in self.rules if r.email}
        # Longest domain wins deterministically when there are nested domain rules.
        self.domain_rules = sorted(((r.domain, r.kind) for r in self.rules if r.domain),
                                   key=lambda x: (-len(x[0]), x[0]))
        self.contact_emails = defaultdict(set)
        self.contact_domains = defaultdict(set)
        self.contact_names = {}
        self.partner_businesses = defaultdict(set)
        for c in s.execute(select(Contact).where(Contact.status == "approved")).scalars():
            rule = self.rule_for(c.email, c.domain)
            if rule == "partner":
                self.partner_businesses[("email", c.email) if c.email else ("domain", c.domain)].add(c.business_id)
            if rule or (c.email and (self.email_people(c.email) or is_internal(c.email))) or within(c.domain, INTERNAL_DOMAINS):
                continue
            if c.email:
                self.contact_emails[c.email.lower()].add(c.business_id)
                self.contact_names[(c.email.lower(), c.business_id)] = c.display_name
            elif c.domain:
                self.contact_domains[c.domain.lower()].add(c.business_id)

    def canonical_id(self, person_id):
        seen = set()
        while person_id in self.people and person_id not in seen:
            seen.add(person_id)
            p = self.people[person_id]
            if p.merged_into_id is None:
                return p.id
            person_id = p.merged_into_id
        return None

    def email_people(self, email):
        return self.addresses[("email", email.lower())] | self.addresses[("fathom_email", email.lower())]

    def rule_for(self, email=None, domain=None):
        if email in self.exact_rules:
            return self.exact_rules[email]
        domain = domain or domain_of(email)
        return next((kind for root, kind in self.domain_rules if within(domain, [root])), None)

    def partner_for(self, email):
        matches = set(self.partner_businesses.get(("email", email), ()))
        d = domain_of(email)
        for (kind, value), ids in self.partner_businesses.items():
            if kind == "domain" and within(d, [value]):
                matches.update(ids)
        return next(iter(matches)) if len(matches) == 1 else None

    def client_person(self, s, email, business_id, name):
        """The exact email's unique address prevents duplicate people on racing runs."""
        # Roster edits use this same lock for both email alias kinds. Recheck only
        # for a new contact person: another publisher may have filled the address
        # after this resolver's preload, including under the fathom_email kind.
        s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                  {"key": f"person-address:email:{email}"})
        existing = s.execute(select(PersonAddress).where(PersonAddress.kind.in_(("email", "fathom_email")),
                                                        PersonAddress.value == email)).scalars().all()
        if existing:
            person_ids = {a.person_id for a in existing}
            if len(person_ids) != 1:
                return None
            person_id = next(iter(person_ids))
            seen = set()
            while person_id not in seen:
                seen.add(person_id)
                person = s.execute(select(Person).where(Person.id == person_id).with_for_update(read=True)
                                   .execution_options(populate_existing=True)).scalar_one()
                self.people[person.id] = person
                if not person.merged_into_id:
                    self.addresses[("email", email)].add(person.id)
                    if any(a.source == "client_contact" for a in existing):
                        self.contact_addresses.add(("email", email, person.id))
                    return person
                person_id = person.merged_into_id
            return None
        try:
            with s.begin_nested():
                person = Person(id=uuid4(), name=(name or email)[:200], kind="client_contact", business_id=business_id,
                                functions=[], status="confirmed", revision=1)
                s.add(person)
                s.flush()
                s.add(PersonAddress(id=uuid4(), person_id=person.id, kind="email", value=email,
                                    source="client_contact"))
                s.flush()
                s.add(AuditEvent(actor="system", action="person.create", target_type="person",
                                target_id=str(person.id), details={"source": "client_contact"}))
        except IntegrityError:
            # Only this rare concurrency path queries for the winning address.
            address = s.execute(select(PersonAddress).where(PersonAddress.kind == "email",
                                                            PersonAddress.value == email)).scalar_one_or_none()
            if address is None:
                raise
            person = s.get(Person, address.person_id)
        self.people[person.id] = person
        self.addresses[("email", email)].add(person.id)
        self.contact_addresses.add(("email", email, person.id))
        return person


def _person_party(person):
    if person.kind == "shared_mailbox":
        return "shared_mailbox", None
    if person.kind == "service_account" and "bot" in (person.functions or []):
        return "bot", None  # chat bots (e.g. Slack apps posting as users): never an author or owner
    if person.kind in INTERNAL_KINDS:
        return "internal", None
    if person.kind == "client_contact":
        return "client", person.business_id
    if person.kind == "partner":
        return "partner", person.business_id
    return "unknown", None


def _assign(identity, person=None, *, party="unknown", business_id=None, basis=None):
    if person is not None:
        party, business_id = _person_party(person)
    values = (person.id if person else None, party, business_id, basis, party in ("internal", "shared_mailbox"))
    old = (identity.person_id, identity.party, identity.party_business_id, identity.resolution_basis, identity.is_internal)
    if old != values:
        (identity.person_id, identity.party, identity.party_business_id,
         identity.resolution_basis, identity.is_internal) = values
        identity.resolved_at = utcnow()


def resolve_identity(s, identity, ctx):
    # Explicit admin links are pinned, while a merge redirects to the surviving person.
    if identity.resolution_basis == "admin" and identity.person_id:
        pid = ctx.canonical_id(identity.person_id)
        if pid:
            _assign(identity, ctx.people[pid], basis="admin")
            return
    key = identity.external_key
    if key.startswith("bot:"):
        _assign(identity, party="bot", basis="automated")
        return
    provider = ctx.providers.get(identity.connector_account_id)
    native_kind = {"slack": "slack_user", "clickup": "clickup_user"}.get(provider)
    if native_kind and ctx.addresses.get((native_kind, key)):
        matches = ctx.addresses[(native_kind, key)]
        if len(matches) == 1:
            _assign(identity, ctx.people[next(iter(matches))], basis="provider_id")
            return
    email = clean(identity.email) or clean(key)
    matches = ctx.email_people(email) if email else set()
    if matches:
        if len(matches) == 1:
            person = ctx.people[next(iter(matches))]
            basis = "client_contact" if person.kind == "client_contact" and any(
                (kind, email, person.id) in ctx.contact_addresses for kind in ("email", "fathom_email")) else "email"
            _assign(identity, person, basis=basis)
        else:
            _assign(identity)  # conflicting cross-kind aliases require admin review
        return
    if provider == "fathom" and key.startswith("speaker:"):
        matches = ctx.names.get(name_key(key[len("speaker:"):]), set())
        if len(matches) == 1:
            _assign(identity, ctx.people[next(iter(matches))], basis="display_name")
            return
    rule = ctx.rule_for(email)
    # Sender rules remain disqualifying even when a contact stays linked to a client.
    clients = ctx.contact_emails.get(email, set()) if email and not rule else set()
    if len(clients) == 1:
        bid = next(iter(clients))
        person = ctx.client_person(s, email, bid, ctx.contact_names.get((email, bid)) or identity.display_name)
        if person is None:
            _assign(identity)
        else:
            basis = "client_contact" if ("email", email, person.id) in ctx.contact_addresses else "email"
            _assign(identity, person, basis=basis)
        return
    if len(clients) > 1:
        _assign(identity)
        return
    domains = set()
    if email and not rule:
        for d, ids in ctx.contact_domains.items():
            if within(domain_of(email), [d]):
                domains.update(ids)
    if len(domains) == 1:
        _assign(identity, party="client", business_id=next(iter(domains)), basis="client_domain")
    elif len(domains) > 1:
        _assign(identity)
    elif rule == "partner":
        _assign(identity, party="partner", business_id=ctx.partner_for(email), basis="partner_rule")
    elif is_internal(email) or rule == "team":
        _assign(identity, party="internal", basis="email")
    elif is_automated_sender(email):
        _assign(identity, party="automated", basis="automated")
    else:
        _assign(identity)


def resolve_all(s, only_unresolved=False):
    ctx = Resolver(s)
    q = select(ProviderIdentity).order_by(ProviderIdentity.id)
    if only_unresolved:
        q = q.where(or_(ProviderIdentity.person_id.is_(None), ProviderIdentity.party.is_(None),
                        ProviderIdentity.party == "unknown"))
    identities = s.execute(q).scalars().all()
    for identity in identities:
        resolve_identity(s, identity, ctx)
    s.flush()
    return dict(Counter(i.party for i in identities))


def mailbox_holder_at(s, mailbox_person_id, when: date):
    mailbox = s.get(Person, mailbox_person_id)
    if mailbox is None or mailbox.kind != "shared_mailbox":
        return None
    rows = s.execute(select(MailboxHolder).where(MailboxHolder.mailbox_person_id == mailbox_person_id,
        or_(MailboxHolder.valid_from.is_(None), MailboxHolder.valid_from <= when),
        or_(MailboxHolder.valid_to.is_(None), MailboxHolder.valid_to >= when))).scalars().all()
    # Conflicting undated assertions are deliberately not turned into guessed dates.
    holders = {r.holder_person_id for r in rows}
    return s.get(Person, next(iter(holders))) if len(holders) == 1 else None


def unknown_people(s, limit=100):
    if not 1 <= limit <= 1000:
        from backend.services.people.roster import PeopleError
        raise PeopleError("limit must be between 1 and 1000")
    counts = select(ContentUnit.author_identity_id.label("identity_id"), func.count().label("n")).group_by(
        ContentUnit.author_identity_id).subquery()
    rows = s.execute(select(ProviderIdentity, ConnectorAccount.provider, func.coalesce(counts.c.n, 0))
        .join(ConnectorAccount, ConnectorAccount.id == ProviderIdentity.connector_account_id)
        .outerjoin(counts, counts.c.identity_id == ProviderIdentity.id)
        .where(or_(ProviderIdentity.party.is_(None), ProviderIdentity.party == "unknown",
                   (ProviderIdentity.party == "internal") & ProviderIdentity.person_id.is_(None)))
        .order_by(func.coalesce(counts.c.n, 0).desc(), ProviderIdentity.id).limit(limit)).all()
    return [{"id": str(i.id), "provider": provider, "external_key": i.external_key,
             "display_name": i.display_name, "email": i.email, "party": i.party, "unit_count": count,
             "reason": "internal, not on roster" if i.party == "internal" else "unresolved"}
            for i, provider, count in rows]


def link_identity(s, identity_id, person_id, *, actor="cli", expected_revision=None):
    from backend.services.clients.mapping import _check
    from backend.services.people.roster import PeopleError, add_address
    person = s.get(Person, person_id, with_for_update=True, populate_existing=True)
    identity = s.get(ProviderIdentity, identity_id, with_for_update=True, populate_existing=True)
    if person is None or person.merged_into_id is not None or identity is None:
        raise PeopleError("unknown identity or active person")
    _check(person, expected_revision)
    provider = s.scalar(select(ConnectorAccount.provider).where(ConnectorAccount.id == identity.connector_account_id))
    key = identity.external_key
    if key.startswith("bot:"):
        raise PeopleError("bot identities cannot be linked to a human roster entry")
    email = clean(identity.email) or clean(key)
    native_kind = {"slack": "slack_user", "clickup": "clickup_user"}.get(provider)
    if native_kind:
        add_address(s, person.id, native_kind, key, actor=actor)
    elif email:
        add_address(s, person.id, "email", email, actor=actor)
    elif provider == "fathom" and key.startswith("speaker:") and person.kind in INTERNAL_KINDS:
        add_address(s, person.id, "display_name", key[len("speaker:"):], actor=actor)
    else:
        raise PeopleError("identity has no supported exact address; Fathom name links require an internal person")
    _assign(identity, person, basis="admin")
    s.add(AuditEvent(actor=actor, action="identity.link", target_type="provider_identity", target_id=str(identity.id),
                    details={"person_id": str(person.id)}))
    return identity
