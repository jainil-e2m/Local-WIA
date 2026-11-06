"""Account teams: suggestions are evidence, confirmed membership is an admin decision."""
from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from backend.models.db import (Business, ConnectorAccount, RecordAssociation, SourceRecord,
                              SourceVersion)
from backend.models.db.base import utcnow
from backend.models.db.people import AccountTeamMember, INTERNAL_KINDS, Person, PersonAddress, TEAM_ROLES
from backend.services.clients.mapping import RevisionConflict, _audit, _check
from backend.services.people.roster import PeopleError

FUNCTION_ROLES = {
    "ads_google": "ads_google", "ads_meta": "ads_meta", "leadlock_copy": "copy",
    "leadlock_technical": "technical", "creative": "creative", "operations": "operations",
    "support": "operations",
}


def _business(s, business_id):
    business = s.get(Business, business_id, with_for_update=True, populate_existing=True)
    if business is None:
        raise PeopleError("unknown client")
    return business


def _person(s, person_id):
    person = s.get(Person, person_id, with_for_update=True, populate_existing=True)
    if person is None or person.merged_into_id:
        raise PeopleError("unknown or merged person; use the canonical person")
    if person.kind not in INTERNAL_KINDS:
        raise PeopleError("account team members must be internal people")
    return person


def _day(value):
    if value is not None and type(value) is not date:
        raise PeopleError("membership dates must be dates")
    return value


def _assignments(s, days):
    """One current task per business, never one count per historical source version."""
    if days is not None and (not isinstance(days, int) or isinstance(days, bool) or days < 1):
        raise PeopleError("days must be a positive integer")
    now = utcnow()
    people = {a.value: p for a, p in s.execute(select(PersonAddress, Person).join(
        Person, Person.id == PersonAddress.person_id).where(
        PersonAddress.kind == "clickup_user", Person.merged_into_id.is_(None)))}
    query = select(SourceRecord, SourceVersion, Business).join(
        SourceVersion, SourceVersion.id == SourceRecord.current_version_id).join(
        ConnectorAccount, ConnectorAccount.id == SourceRecord.connector_account_id).join(
        RecordAssociation, RecordAssociation.record_id == SourceRecord.id).join(
        Business, Business.id == RecordAssociation.business_id).where(
        ConnectorAccount.provider == "clickup", SourceRecord.record_kind == "clickup_task",
        SourceRecord.availability == "available", RecordAssociation.status == "associated",
        Business.status == "active")
    if days is not None:
        query = query.where(SourceVersion.provider_updated_at >= now - timedelta(days=days),
                            SourceVersion.provider_updated_at <= now)
    return people, s.execute(query).all()


def suggest_teams(s, days=120, *, actor="system") -> int:
    people, tasks = _assignments(s, days)
    counts = defaultdict(set)
    for record, version, business in tasks:
        for user_id in set(map(str, version.attributes.get("assignee_ids") or [])):
            person = people.get(user_id)
            if person is None or person.kind not in INTERNAL_KINDS or person.kind == "former":
                continue
            roles = {FUNCTION_ROLES[f] for f in person.functions or [] if f in FUNCTION_ROLES}
            for role in roles:
                counts[(business.id, role, person.id)].add(record.id)
    changed = 0
    # Roster loads and merges also lock people first. Lock every candidate in one
    # UUID order before accumulating any business locks across the suggestion run.
    locked_people = {p.id: p for p in s.execute(select(Person).where(
        Person.id.in_({pid for _, _, pid in counts})).order_by(Person.id).with_for_update()
        .execution_options(populate_existing=True)).scalars()} if counts else {}
    for (bid, role, pid), task_ids in sorted(counts.items(), key=lambda x: tuple(map(str, x[0]))):
        person = locked_people.get(pid)
        if person is None or person.merged_into_id or person.kind not in INTERNAL_KINDS or person.kind == "former":
            continue
        if role not in {FUNCTION_ROLES[f] for f in person.functions or [] if f in FUNCTION_ROLES}:
            continue
        if _business(s, bid).status != "active":
            continue
        # Re-read after obtaining the business lock: another operator may have decided.
        rows = s.execute(select(AccountTeamMember).where(AccountTeamMember.business_id == bid,
            AccountTeamMember.role == role, AccountTeamMember.person_id == pid)
            .execution_options(populate_existing=True)).scalars().all()
        if any(row.status in ("confirmed", "ended") for row in rows):
            continue
        evidence = {"clickup_tasks_120d" if days == 120 else f"clickup_tasks_{days}d": len(task_ids)}
        row = next((r for r in rows if r.status == "suggested"), None)
        if row is not None and row.evidence == evidence:
            continue
        if row is None:
            row = AccountTeamMember(id=uuid4(), business_id=bid, person_id=pid, role=role,
                status="suggested", source="clickup_assignments", evidence=evidence, revision=1)
            s.add(row)
        else:
            row.evidence = evidence
            row.revision += 1
        _audit(s, actor, "team.suggest", "account_team_member", row.id, evidence=evidence)
        changed += 1
    s.flush()
    return changed


def set_team_member(s, business_id, role, person_id, *, actor, started_on=None,
                    expected_revision=None, source="admin") -> AccountTeamMember:
    if role not in TEAM_ROLES:
        raise PeopleError("unsupported account-team role")
    if source not in ("admin", "roster_file"):
        raise PeopleError("confirmed membership source must be admin or roster_file")
    started_on = _day(started_on)
    _person(s, person_id)
    _business(s, business_id)
    row = s.execute(select(AccountTeamMember).where(AccountTeamMember.business_id == business_id,
        AccountTeamMember.role == role, AccountTeamMember.person_id == person_id,
        AccountTeamMember.status != "ended").with_for_update()
        .execution_options(populate_existing=True)).scalar_one_or_none()
    if row is None and expected_revision is not None:
        raise RevisionConflict("account-team membership is no longer active")
    if row is not None:
        _check(row, expected_revision)
    if row is not None and row.status == "confirmed" and (started_on is None or row.started_on == started_on):
        return row
    if role == "owner":
        previous = s.execute(select(AccountTeamMember).where(AccountTeamMember.business_id == business_id,
            AccountTeamMember.role == "owner", AccountTeamMember.status == "confirmed",
            AccountTeamMember.person_id != person_id).with_for_update()
            .execution_options(populate_existing=True)).scalars().all()
        for old in previous:
            end = started_on or utcnow().date()
            if old.started_on and end < old.started_on:
                raise PeopleError("replacement owner cannot start before the previous owner's membership")
            old.status, old.ended_on = "ended", end
            old.revision += 1
            _audit(s, actor, "team.end", "account_team_member", old.id, reason="owner_replaced",
                   ended_on=end.isoformat())
        # Explicitly release the partial unique index before inserting/confirming the new owner.
        s.flush()
    if row is None:
        row = AccountTeamMember(id=uuid4(), business_id=business_id, role=role, person_id=person_id,
            status="confirmed", source=source, evidence={}, started_on=started_on, revision=1)
        s.add(row)
    else:
        row.status, row.source = "confirmed", source
        if started_on is not None:
            row.started_on = started_on
        row.revision += 1
    row.confirmed_by, row.confirmed_at = actor, utcnow()
    row.ended_on = None
    _audit(s, actor, "team.confirm", "account_team_member", row.id, business_id=str(business_id),
           person_id=str(person_id), role=role)
    s.flush()
    return row


def end_team_member(s, member_id, *, expected_revision, actor, ended_on=None):
    probe = s.get(AccountTeamMember, member_id)
    if probe is None:
        raise PeopleError("unknown account-team membership")
    _business(s, probe.business_id)
    row = s.execute(select(AccountTeamMember).where(AccountTeamMember.id == member_id)
        .with_for_update().execution_options(populate_existing=True)).scalar_one()
    _check(row, expected_revision)
    if row.status == "ended":
        return row
    end = _day(ended_on) or utcnow().date()
    if row.started_on and end < row.started_on:
        raise PeopleError("end date precedes membership start")
    row.status, row.ended_on = "ended", end
    row.revision += 1
    _audit(s, actor, "team.end", "account_team_member", row.id, ended_on=end.isoformat())
    s.flush()
    return row


def team_for(s, business_id) -> list[dict]:
    return [{"id": m.id, "business_id": m.business_id, "person_id": m.person_id,
             "person": p.name, "kind": p.kind, "role": m.role, "status": m.status,
             "source": m.source, "evidence": m.evidence, "revision": m.revision,
             "started_on": m.started_on, "ended_on": m.ended_on}
            for m, p in s.execute(select(AccountTeamMember, Person).join(Person).where(
                AccountTeamMember.business_id == business_id, AccountTeamMember.status != "ended")
                .order_by(AccountTeamMember.role, Person.name))]


def clients_for_person(s, person_id) -> list[UUID]:
    person = s.get(Person, person_id)
    seen = set()
    while person is not None and person.merged_into_id:
        if person.id in seen:
            raise PeopleError("person merge cycle")
        seen.add(person.id)
        person = s.get(Person, person.merged_into_id)
    if person is None:
        return []
    return list(s.execute(select(AccountTeamMember.business_id).where(
        AccountTeamMember.person_id == person.id, AccountTeamMember.status == "confirmed")
        .distinct().order_by(AccountTeamMember.business_id)).scalars())


def former_assignments(s) -> list[dict]:
    # An unchanged old task can still be outstanding work. The suggestion window
    # must not hide former staff who remain assigned to those current tasks.
    people, tasks = _assignments(s, days=None)
    found = {}
    for record, version, business in tasks:
        if (version.attributes.get("status") or {}).get("type") in ("done", "closed"):
            continue
        for user_id in set(map(str, version.attributes.get("assignee_ids") or [])):
            person = people.get(user_id)
            if person is None or person.kind != "former":
                continue
            key = (business.id, person.id)
            row = found.setdefault(key, {"business_id": business.id, "client": business.name,
                "slug": business.slug, "person_id": person.id, "person": person.name, "tasks": {}})
            row["tasks"][str(record.id)] = version.attributes.get("name") or record.external_id
    return [{**row, "task_count": len(row["tasks"])}
            for row in sorted(found.values(), key=lambda r: (r["client"], r["person"]))]


def clients_without_owner(s) -> list[Business]:
    owned = select(AccountTeamMember.id).where(AccountTeamMember.business_id == Business.id,
        AccountTeamMember.role == "owner", AccountTeamMember.status == "confirmed").exists()
    return list(s.execute(select(Business).where(Business.status == "active", ~owned)
        .order_by(Business.name)).scalars())
