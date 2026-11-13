"""Invented people and task IDs only: account-team evidence and admin decisions."""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.db import transaction
from backend.models.db import (AuditEvent, Business, ConnectorAccount, RecordAssociation,
                              SourceRecord, SourceVersion)
from backend.models.db.people import AccountTeamMember
from backend.models.db.base import utcnow
from backend.services.clients import mapping
from backend.services.people import roster, teams


def _client(s, slug="example-client"):
    return mapping.create_client(s, name="Example Client", slug=slug, actor="test", discover=False)


def _person(s, name="Alex Example", kind="staff", functions=("ads_google",)):
    return roster.create_person(s, name=name, kind=kind, functions=functions, actor="test")


def _account(s):
    account = ConnectorAccount(id=uuid4(), provider="clickup", provider_account_id="example-workspace",
        expected_identity="example-workspace", credential_ref="TEST_TOKEN")
    s.add(account)
    s.flush()
    return account


def _task(s, account, client, assignees, *, age=10, availability="available", done=False):
    record = SourceRecord(id=uuid4(), connector_account_id=account.id, record_kind="clickup_task",
        external_id="example-task-" + uuid4().hex, availability=availability, qualification="content")
    s.add(record)
    s.flush()
    version = SourceVersion(id=uuid4(), record_id=record.id, version_key=uuid4().hex,
        content_sha256="0" * 64, provider_updated_at=utcnow() - timedelta(days=age), observed_at=utcnow(),
        parser_version="test-v1", content_state="content", unit_count=0,
        attributes={"assignee_ids": list(assignees), "name": "Example task",
                    "status": {"type": "done" if done else "open"}})
    s.add(version)
    s.flush()
    record.current_version_id = version.id
    s.add(RecordAssociation(id=uuid4(), record_id=record.id, business_id=client.id,
                           basis="verified_contact", status="associated", multi_client=False))
    s.flush()
    return record, version


def _member(s, client, person, role="ads_google", status="suggested"):
    row = AccountTeamMember(id=uuid4(), business_id=client.id, person_id=person.id,
        role=role, status=status, source="clickup_assignments", evidence={}, revision=1)
    s.add(row)
    s.flush()
    return row


def test_suggestions_use_current_versions_distinct_tasks_and_functions():
    with transaction() as s:
        client, account = _client(s), _account(s)
        alex = _person(s, functions=("ads_google", "ads_meta", "operations", "support"))
        sam = _person(s, "Sam Sample", functions=("creative",))
        roster.add_address(s, alex.id, "clickup_user", "10000001", actor="test")
        roster.add_address(s, sam.id, "clickup_user", "10000002", actor="test")
        record, current = _task(s, account, client, ["10000001", "10000001"])
        historical = SourceVersion(id=uuid4(), record_id=record.id, version_key=uuid4().hex,
            content_sha256="1" * 64, provider_updated_at=utcnow() - timedelta(days=20), observed_at=utcnow(),
            parser_version="test-v1", content_state="content", unit_count=0,
            attributes={"assignee_ids": ["10000002"]})
        s.add(historical)
        _task(s, account, client, ["10000001"])
        _task(s, account, client, ["10000001"], age=121)
        _task(s, account, client, ["10000001"], availability="deleted_upstream")
        assert teams.suggest_teams(s) == 3
        rows = teams.team_for(s, client.id)
        assert {r["role"] for r in rows} == {"ads_google", "ads_meta", "operations"}
        assert all(r["person_id"] == alex.id and r["evidence"] == {"clickup_tasks_120d": 2} for r in rows)
        before = [(r["id"], r["revision"]) for r in rows]
        audits = s.scalar(select(func.count()).select_from(AuditEvent))
        assert teams.suggest_teams(s) == 0
        assert [(r["id"], r["revision"]) for r in teams.team_for(s, client.id)] == before
        assert s.scalar(select(func.count()).select_from(AuditEvent)) == audits


def test_suggestions_never_overwrite_confirmed_or_resurrect_ended_decisions():
    with transaction() as s:
        client, account = _client(s), _account(s)
        alex = _person(s, functions=("ads_google", "ads_meta", "creative"))
        roster.add_address(s, alex.id, "clickup_user", "10000001", actor="test")
        confirmed = teams.set_team_member(s, client.id, "ads_google", alex.id, actor="admin")
        ended = teams.set_team_member(s, client.id, "ads_meta", alex.id, actor="admin")
        teams.end_team_member(s, ended.id, expected_revision=ended.revision, actor="admin")
        _task(s, account, client, ["10000001"])
        assert teams.suggest_teams(s) == 1
        assert confirmed.status == "confirmed" and confirmed.revision == 1 and confirmed.evidence == {}
        assert ended.status == "ended"
        assert len(s.execute(select(AccountTeamMember).where(AccountTeamMember.role == "ads_meta")).scalars().all()) == 1


def test_former_people_are_reported_and_archived_clients_not_suggested():
    with transaction() as s:
        client, account = _client(s), _account(s)
        former = _person(s, "Taylor Placeholder", kind="former", functions=("creative",))
        staff = _person(s)
        roster.add_address(s, former.id, "clickup_user", "10000001", actor="test")
        roster.add_address(s, staff.id, "clickup_user", "10000002", actor="test")
        _task(s, account, client, ["10000001"])
        _task(s, account, client, ["10000001"], done=True)
        archived = _client(s, "archived-example")
        archived.status = "inactive"
        _task(s, account, archived, ["10000002"])
        assert teams.suggest_teams(s) == 0
        report = teams.former_assignments(s)
        assert len(report) == 1 and report[0]["person_id"] == former.id and report[0]["task_count"] == 1


def test_owner_handoff_ends_previous_owner_before_confirmation():
    with transaction() as s:
        client, alex, sam = _client(s), _person(s), _person(s, "Sam Sample")
        first = teams.set_team_member(s, client.id, "owner", alex.id, actor="first", started_on=date(2026, 1, 1))
        second = teams.set_team_member(s, client.id, "owner", sam.id, actor="second", started_on=date(2026, 3, 1))
        assert first.status == "ended" and first.ended_on == date(2026, 3, 1) and first.revision == 2
        assert second.status == "confirmed" and second.confirmed_by == "second"
        assert teams.clients_for_person(s, alex.id) == []
        assert teams.clients_for_person(s, sam.id) == [client.id]
        assert teams.clients_without_owner(s) == []
        audits = s.scalar(select(func.count()).select_from(AuditEvent))
        assert teams.set_team_member(s, client.id, "owner", sam.id, actor="repeat").revision == 1
        assert s.scalar(select(func.count()).select_from(AuditEvent)) == audits


def test_partial_unique_index_blocks_two_confirmed_owners_even_without_service():
    with transaction() as s:
        client, alex, sam = _client(s), _person(s), _person(s, "Sam Sample")
        _member(s, client, alex, role="owner", status="confirmed")
        with pytest.raises(IntegrityError), s.begin_nested():
            _member(s, client, sam, role="owner", status="confirmed")


def test_clients_for_person_returns_confirmed_only_and_end_is_revision_checked():
    with transaction() as s:
        client, other, alex = _client(s), _client(s, "other-example"), _person(s)
        row = teams.set_team_member(s, client.id, "ads_google", alex.id, actor="admin")
        _member(s, other, alex)
        assert teams.clients_for_person(s, alex.id) == [client.id]
        with pytest.raises(mapping.RevisionConflict):
            teams.end_team_member(s, row.id, expected_revision=999, actor="stale")
        teams.end_team_member(s, row.id, expected_revision=1, actor="admin")
        assert teams.clients_for_person(s, alex.id) == []
        with pytest.raises(mapping.RevisionConflict):
            teams.end_team_member(s, row.id, expected_revision=1, actor="stale")


def test_invalid_roles_external_people_and_backdated_end_are_rejected():
    with transaction() as s:
        client, staff = _client(s), _person(s)
        outsider = _person(s, "Pat Prospect", kind="prospect", functions=())
        with pytest.raises(roster.PeopleError):
            teams.set_team_member(s, client.id, "invalid", staff.id, actor="test")
        with pytest.raises(roster.PeopleError):
            teams.set_team_member(s, client.id, "owner", outsider.id, actor="test")
        row = teams.set_team_member(s, client.id, "ads_google", staff.id, actor="test", started_on=date(2026, 3, 1))
        with pytest.raises(roster.PeopleError):
            teams.end_team_member(s, row.id, expected_revision=1, actor="test", ended_on=date(2026, 1, 1))
        assert row.status == "confirmed"


def test_suggestion_recount_changes_revision_but_does_not_infer_owner():
    with transaction() as s:
        client, account, alex = _client(s), _account(s), _person(s, functions=("leadership", "ads_google"))
        roster.add_address(s, alex.id, "clickup_user", "10000001", actor="test")
        _task(s, account, client, ["10000001"])
        assert teams.suggest_teams(s) == 1
        _task(s, account, client, ["10000001"])
        assert teams.suggest_teams(s) == 1
        rows = teams.team_for(s, client.id)
        assert len(rows) == 1 and rows[0]["role"] == "ads_google" and rows[0]["revision"] == 2
        assert rows[0]["evidence"] == {"clickup_tasks_120d": 2}
        assert [b.id for b in teams.clients_without_owner(s)] == [client.id]


def test_former_open_work_is_reported_even_when_older_than_suggestion_window():
    with transaction() as s:
        client, account = _client(s), _account(s)
        former = _person(s, "Taylor Placeholder", kind="former")
        roster.add_address(s, former.id, "clickup_user", "10000001", actor="test")
        _task(s, account, client, ["10000001"], age=240)
        _task(s, account, client, ["10000001"], age=240, done=True)
        assert teams.suggest_teams(s) == 0
        assert teams.former_assignments(s)[0]["task_count"] == 1


def test_confirmation_refreshes_cached_membership_before_revision_check():
    with transaction() as s:
        client, alex = _client(s), _person(s)
        row = _member(s, client, alex)
        member_id, client_id, person_id = row.id, client.id, alex.id
    with transaction() as s:
        cached = s.get(AccountTeamMember, member_id)
        assert cached.revision == 1
        with transaction() as other:
            updated = other.get(AccountTeamMember, member_id)
            updated.evidence, updated.revision = {"clickup_tasks_120d": 2}, 2
        with pytest.raises(mapping.RevisionConflict):
            teams.set_team_member(s, client_id, "ads_google", person_id,
                                  expected_revision=1, actor="stale")
        assert cached.status == "suggested" and cached.revision == 2
