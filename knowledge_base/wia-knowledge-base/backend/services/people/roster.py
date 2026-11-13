"""Session-taking, audited people commands shared by CLI and future admin API."""
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import yaml
from sqlalchemy import select, text

from backend.db import transaction, wait_for_locks
from backend.models.db import (AccountTeamMember, Business, MailboxHolder, Person, PersonAddress,
                               ProviderIdentity, SenderRule)
from backend.models.db.people import ADDRESS_KINDS, FUNCTIONS, INTERNAL_KINDS, PERSON_KINDS
from backend.models.db.base import utcnow
from backend.services.clients.mapping import RevisionConflict, _audit, _check
from backend.services.shared.emails import clean


class PeopleError(ValueError):
    pass


def _person(s, person_id, expected_revision=None):
    wait_for_locks(s)
    person = s.get(Person, person_id, with_for_update=True, populate_existing=True)
    if person is None:
        raise PeopleError(f"unknown person {person_id}")
    if person.merged_into_id:
        raise PeopleError(f"person was merged into {person.merged_into_id}")
    _check(person, expected_revision)
    return person


def person_by_name_or_id(s, value):
    try:
        identifier = value if isinstance(value, UUID) else UUID(value)
    except (ValueError, TypeError, AttributeError):
        rows = s.execute(select(Person).where(Person.name == value, Person.merged_into_id.is_(None))).scalars().all()
        if len(rows) != 1:
            raise PeopleError("person name is missing or ambiguous; use their UUID")
        return rows[0]
    person = s.get(Person, identifier)
    if person is None:
        raise PeopleError(f"unknown person {identifier}")
    visited = set()
    while person.merged_into_id:
        if person.id in visited:
            raise PeopleError("cyclic person merge")
        visited.add(person.id)
        person = s.get(Person, person.merged_into_id)
    return person


def _validate(name, kind, functions, business_id, status, s):
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 200:
        raise PeopleError("name must contain 1 to 200 characters")
    if kind not in PERSON_KINDS or status not in ("confirmed", "pending"):
        raise PeopleError("invalid person kind or status")
    if isinstance(functions, str) or not set(functions) <= FUNCTIONS:
        raise PeopleError("invalid person functions")
    if functions and kind not in INTERNAL_KINDS:
        raise PeopleError("only internal people have staff functions")
    if kind == "client_contact" and business_id is None:
        raise PeopleError("client contacts need a business")
    if business_id is not None and s.get(Business, business_id) is None:
        raise PeopleError("unknown business")


def create_person(s, *, name, kind, functions=(), business_id=None, status="confirmed", actor, notes=None):
    _validate(name, kind, functions, business_id, status, s)
    if notes is not None and (not isinstance(notes, str) or len(notes) > 500):
        raise PeopleError("notes must be at most 500 characters")
    person = Person(id=uuid4(), name=name.strip(), kind=kind, functions=sorted(set(functions)),
        business_id=business_id, status=status, notes=notes, revision=1)
    s.add(person)
    s.flush()
    _audit(s, actor, "person.create", "person", person.id, kind=kind, status=status)
    return person


def update_person(s, person_id, *, expected_revision, actor, name=None, kind=None, functions=None, status=None,
                  notes=None):
    person = _person(s, person_id, expected_revision)
    values = dict(name=name if name is not None else person.name,
        kind=kind if kind is not None else person.kind, functions=functions if functions is not None else person.functions,
        status=status if status is not None else person.status)
    _validate(**values, business_id=person.business_id, s=s)
    if notes is not None:
        if len(notes) > 500:
            raise PeopleError("notes must be at most 500 characters")
        values["notes"] = notes
    values["name"] = values["name"].strip()
    values["functions"] = sorted(set(values["functions"]))
    if values["kind"] not in INTERNAL_KINDS:
        active_team = s.execute(select(AccountTeamMember.id).where(AccountTeamMember.person_id == person.id,
            AccountTeamMember.status != "ended")).first()
        if active_team:
            raise PeopleError("end this person's account-team memberships before making them external")
    if person.kind == "shared_mailbox" and values["kind"] != "shared_mailbox" and s.execute(
            select(MailboxHolder.id).where(MailboxHolder.mailbox_person_id == person.id)).first():
        raise PeopleError("a shared mailbox with holder history cannot become a human person")
    if values["kind"] not in INTERNAL_KINDS - {"shared_mailbox", "service_account"} and s.execute(
            select(MailboxHolder.id).where(MailboxHolder.holder_person_id == person.id)).first():
        raise PeopleError("a recorded mailbox holder must remain an internal human person")
    changed = {key: value for key, value in values.items() if getattr(person, key) != value}
    if changed:
        for key, value in changed.items():
            setattr(person, key, value)
        person.revision += 1
        _audit(s, actor, "person.update", "person", person.id, fields=sorted(changed))
    return person


def _address(kind, value):
    if kind not in ADDRESS_KINDS or not isinstance(value, str):
        raise PeopleError("invalid address kind or value")
    value = value.strip()
    if kind in ("email", "fathom_email"):
        value = clean(value)
        if not value:
            raise PeopleError("addresses must be exact email addresses, never domains")
    if not value or len(value) > 320:
        raise PeopleError("address must contain 1 to 320 characters")
    if kind == "display_name" and value.startswith("speaker:"):
        value = value[len("speaker:"):].strip()
    return value


def add_address(s, person_id, kind, value, *, actor, source="admin", expected_revision=None):
    value = _address(kind, value)
    if source not in ("roster", "admin", "client_contact"):
        raise PeopleError("invalid address source")
    person = _person(s, person_id, expected_revision)
    family = "email" if kind in ("email", "fathom_email") else kind
    # The unique index handles each kind; this value-level lock also serializes
    # collisions across email/fathom_email, which represent one real address.
    s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
              {"key": f"person-address:{family}:{value}"})
    if kind == "display_name" and person.kind not in INTERNAL_KINDS:
        raise PeopleError("display-name aliases are only for internal Fathom speakers")
    # email/fathom_email are the same real address and cannot belong to different people.
    kinds = ("email", "fathom_email") if kind in ("email", "fathom_email") else (kind,)
    rows = s.execute(select(PersonAddress).where(PersonAddress.kind.in_(kinds),
                                                PersonAddress.value == value)).scalars().all()
    if any(a.person_id != person.id for a in rows):
        raise PeopleError("address already belongs to another person")
    existing = next((a for a in rows if a.kind == kind), None)
    if existing:
        return existing
    address = PersonAddress(id=uuid4(), person_id=person.id, kind=kind, value=value, source=source)
    s.add(address)
    person.revision += 1
    s.flush()
    _audit(s, actor, "person.address.add", "person", person.id, kind=kind, value=value)
    return address


def remove_address(s, person_id, kind, value, *, actor, expected_revision=None):
    person = _person(s, person_id, expected_revision)
    value = _address(kind, value)
    row = s.execute(select(PersonAddress).where(PersonAddress.person_id == person.id,
        PersonAddress.kind == kind, PersonAddress.value == value)).scalar_one_or_none()
    if row:
        s.delete(row)
        person.revision += 1
        _audit(s, actor, "person.address.remove", "person", person.id, kind=kind, value=value)


def internal_addresses(s):
    addresses = set(s.execute(select(PersonAddress.value).join(Person, Person.id == PersonAddress.person_id).where(
        Person.kind.in_(INTERNAL_KINDS), Person.merged_into_id.is_(None),
        PersonAddress.kind.in_(("email", "fathom_email")))).scalars())
    addresses.update(s.execute(select(SenderRule.email).where(SenderRule.kind == "team",
                                                             SenderRule.email.is_not(None))).scalars())
    return addresses


def internal_ids(s):
    result = {"slack_user": set(), "clickup_user": set()}
    for kind, value in s.execute(select(PersonAddress.kind, PersonAddress.value).join(Person).where(
            Person.kind.in_(INTERNAL_KINDS), Person.merged_into_id.is_(None),
            PersonAddress.kind.in_(result))):
        result[kind].add(value)
    return result


def set_mailbox_holder(s, mailbox_id, holder_id, *, valid_from=None, actor, expected_revision=None):
    people = {p.id: p for p in s.execute(select(Person).where(Person.id.in_([mailbox_id, holder_id]))
        .order_by(Person.id).with_for_update().execution_options(populate_existing=True)).scalars()}
    if mailbox_id not in people or holder_id not in people:
        raise PeopleError("unknown mailbox or holder")
    mailbox, holder = people[mailbox_id], people[holder_id]
    if mailbox.merged_into_id or holder.merged_into_id:
        raise PeopleError("mailbox and holder must be canonical people")
    _check(mailbox, expected_revision)
    if mailbox.kind != "shared_mailbox" or holder.kind not in INTERNAL_KINDS or holder.kind in ("shared_mailbox", "service_account"):
        raise PeopleError("a shared mailbox must be covered by an internal human person")
    starts = valid_from or date.today()
    if type(starts) is not date:
        raise PeopleError("valid_from must be a date")
    rows = s.execute(select(MailboxHolder).where(MailboxHolder.mailbox_person_id == mailbox.id)
        .with_for_update().execution_options(populate_existing=True)).scalars().all()
    open_rows = [r for r in rows if r.valid_to is None]
    known_open = [r for r in open_rows if r.valid_from is not None]
    # Replaying the current handoff does not invent dates for older undated
    # assertions. Those remain unresolved until an operator supplies evidence.
    current = next((r for r in known_open if r.holder_person_id == holder.id and
                    (valid_from is None or r.valid_from == starts)), None)
    if current is not None and len(known_open) == 1:
        return current
    if valid_from is None and len(open_rows) == 1 and open_rows[0].holder_person_id == holder.id:
        return open_rows[0]
    if any(r.valid_to is not None and r.valid_to >= starts for r in rows):
        raise PeopleError("new holder overlaps recorded holder history")
    for old in known_open:
        if old.valid_from >= starts:
            raise PeopleError("new holder starts before or on an existing open holder's start date")
    for old in known_open:
        old.valid_to = starts - timedelta(days=1)
    row = MailboxHolder(id=uuid4(), mailbox_person_id=mailbox.id, holder_person_id=holder.id, valid_from=starts)
    s.add(row)
    mailbox.revision += 1
    _audit(s, actor, "mailbox.holder.set", "person", mailbox.id, holder_id=str(holder.id), valid_from=starts.isoformat())
    return row


def merge_people(s, keep_id, merge_id, *, actor, expected_revision=None, merge_expected_revision=None):
    if keep_id == merge_id:
        raise PeopleError("cannot merge a person into themselves")
    # Consistent lock order prevents two opposing merges from deadlocking.
    locked = {p.id: p for p in s.execute(select(Person).where(Person.id.in_([keep_id, merge_id]))
        .order_by(Person.id).with_for_update().execution_options(populate_existing=True)).scalars()}
    if keep_id not in locked or merge_id not in locked:
        raise PeopleError("unknown person")
    keep, merged = locked[keep_id], locked[merge_id]
    _check(keep, expected_revision)
    _check(merged, merge_expected_revision)
    if merged.merged_into_id == keep.id:
        return keep
    if keep.merged_into_id or merged.merged_into_id:
        raise PeopleError("merge canonical people only")
    if (keep.kind == "shared_mailbox") != (merged.kind == "shared_mailbox"):
        raise PeopleError("shared mailboxes cannot be merged into human people")
    if keep.business_id and merged.business_id and keep.business_id != merged.business_id:
        raise PeopleError("people assigned to different client businesses cannot be merged")
    if keep.kind in ("shared_mailbox", "service_account") and s.execute(select(MailboxHolder.id).where(
            MailboxHolder.holder_person_id.in_([keep.id, merged.id]))).first():
        raise PeopleError("a mailbox holder cannot be merged into a non-human identity")
    active_teams = s.execute(select(AccountTeamMember).where(AccountTeamMember.person_id.in_([keep.id, merged.id]))).scalars().all()
    if any(t.status != "ended" for t in active_teams) and keep.kind not in INTERNAL_KINDS:
        raise PeopleError("account team membership requires an internal person")
    for address in s.execute(select(PersonAddress).where(PersonAddress.person_id == merged.id)).scalars():
        address.person_id = keep.id
    party = ("shared_mailbox" if keep.kind == "shared_mailbox" else "internal" if keep.kind in INTERNAL_KINDS
             else "client" if keep.kind == "client_contact" else "partner" if keep.kind == "partner" else "unknown")
    for identity in s.execute(select(ProviderIdentity).where(ProviderIdentity.person_id == merged.id)).scalars():
        identity.person_id, identity.party = keep.id, party
        identity.party_business_id = keep.business_id if party == "client" else None
        identity.is_internal = party in ("internal", "shared_mailbox")
        identity.resolved_at = utcnow()
    keeper_rows = {(t.business_id, t.role): t for t in active_teams if t.person_id == keep.id and t.status != "ended"}
    for team in active_teams:
        if team.person_id != merged.id:
            continue
        match = keeper_rows.get((team.business_id, team.role)) if team.status != "ended" else None
        if match:
            if team.status == "confirmed" and match.status == "suggested":
                # End the conflicting row before promoting the surviving membership.
                team.status, team.ended_on = "ended", date.today()
                s.flush()
                match.status, match.confirmed_by, match.confirmed_at = "confirmed", team.confirmed_by, team.confirmed_at
                match.revision += 1
            else:
                team.status, team.ended_on = "ended", date.today()
                s.flush()
        team.person_id = keep.id
        team.revision += 1
    for row in s.execute(select(MailboxHolder).where(MailboxHolder.mailbox_person_id == merged.id)).scalars():
        row.mailbox_person_id = keep.id
    for row in s.execute(select(MailboxHolder).where(MailboxHolder.holder_person_id == merged.id)).scalars():
        row.holder_person_id = keep.id
    merged.merged_into_id = keep.id
    merged.revision += 1
    keep.revision += 1
    _audit(s, actor, "person.merge", "person", keep.id, merged_id=str(merged.id))
    return keep


def _date(value):
    if value is None or type(value) is date:
        return value
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise PeopleError("holder dates must be ISO dates") from exc


def load_roster(path, actor="cli"):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PeopleError("roster must be a YAML mapping")
    counts = {"people_created": 0, "people_updated": 0, "addresses_added": 0, "holders_added": 0, "teams_set": 0}
    with transaction() as s:
        # Serialize file bootstrap with other roster loads without a new lock table.
        s.execute(text("SELECT pg_advisory_xact_lock(30420261030)"))
        # A load may change many people before assigning account teams. Acquire
        # existing people in the same order as merge and resolver snapshots,
        # before taking any business, identity, address, or membership locks.
        s.execute(select(Person).order_by(Person.id).with_for_update()
                  .execution_options(populate_existing=True)).scalars().all()
        def load_person(entry, *, mailbox=False):
            name = entry.get("name", "")
            kind = "shared_mailbox" if mailbox else entry.get("kind", "unknown")
            rows = s.execute(select(Person).where(Person.name == name, Person.kind == kind,
                Person.merged_into_id.is_(None))).scalars().all()
            if len(rows) > 1:
                raise PeopleError("duplicate roster names/kinds require manual resolution")
            status = entry.get("status", "pending")
            person = rows[0] if rows else create_person(s, name=name, kind=kind, functions=entry.get("functions", []),
                status=status, actor=actor, notes=entry.get("notes"))
            counts["people_created"] += not bool(rows)
            if rows:
                rev = person.revision
                update_person(s, person.id, expected_revision=rev, actor=actor, name=name, kind=kind,
                    functions=entry.get("functions", []), status=status, notes=entry.get("notes"))
                counts["people_updated"] += person.revision != rev
            fields = {"emails": "email", "slack": "slack_user", "clickup": "clickup_user", "fathom": "fathom_email", "display_names": "display_name"}
            for field, address_kind in fields.items():
                values = [entry["email"]] if mailbox and field == "emails" and entry.get("email") else entry.get(field, [])
                if not isinstance(values, list):
                    raise PeopleError(f"{field} must be a list")
                for value in values:
                    before = person.revision
                    add_address(s, person.id, address_kind, str(value), actor=actor, source="roster", expected_revision=person.revision)
                    counts["addresses_added"] += person.revision != before
            return person
        for entry in data.get("people", []):
            load_person(entry)
        for entry in data.get("shared_mailboxes", []):
            mailbox = load_person(entry, mailbox=True)
            for holder_entry in entry.get("holders", []):
                holder = person_by_name_or_id(s, holder_entry["person"])
                if holder.kind not in INTERNAL_KINDS or holder.kind in ("shared_mailbox", "service_account"):
                    raise PeopleError("mailbox holder must be an internal human")
                lo, hi = _date(holder_entry.get("from")), _date(holder_entry.get("to"))
                if lo and hi and lo > hi:
                    raise PeopleError("holder date range is reversed")
                note = holder_entry.get("note")
                if note is None and lo is None:
                    note = "Holder start date was not provided; chronology is unresolved."
                if note is not None and (not isinstance(note, str) or len(note) > 500):
                    raise PeopleError("holder note must be at most 500 characters")
                row = s.execute(select(MailboxHolder).where(MailboxHolder.mailbox_person_id == mailbox.id,
                    MailboxHolder.holder_person_id == holder.id, MailboxHolder.valid_from == lo,
                    MailboxHolder.valid_to == hi)).scalar_one_or_none()
                if row is None:
                    s.add(MailboxHolder(id=uuid4(), mailbox_person_id=mailbox.id, holder_person_id=holder.id,
                        valid_from=lo, valid_to=hi, note=note))
                    mailbox.revision += 1
                    counts["holders_added"] += 1
                    _audit(s, actor, "mailbox.holder.import", "person", mailbox.id, holder_id=str(holder.id),
                           valid_from=lo.isoformat() if lo else None, valid_to=hi.isoformat() if hi else None)
                    s.flush()
        from backend.services.people.teams import set_team_member
        from backend.services.clients.mapping import business_by_slug
        for slug, roles in data.get("account_teams", {}).items():
            business = business_by_slug(s, slug)
            for role, name in roles.items():
                person = person_by_name_or_id(s, name)
                before = s.execute(select(AccountTeamMember).where(AccountTeamMember.business_id == business.id,
                    AccountTeamMember.role == role, AccountTeamMember.person_id == person.id,
                    AccountTeamMember.status != "ended")).scalar_one_or_none()
                changed = before is None or before.status != "confirmed"
                set_team_member(s, business.id, role, person.id, actor=actor, source="roster_file")
                counts["teams_set"] += changed
    return counts
