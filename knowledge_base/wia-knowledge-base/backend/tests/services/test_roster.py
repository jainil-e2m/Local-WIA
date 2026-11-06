"""Roster commands use invented people, addresses and native IDs only."""
from datetime import date
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import func, select

from backend.db import transaction
from backend.models.db import (AccountTeamMember, AuditEvent, Business, ConnectorAccount, MailboxHolder,
                               Person, PersonAddress, ProviderIdentity, SenderRule)
from backend.models.db.base import utcnow
from backend.services.clients.mapping import RevisionConflict
from backend.services.people import roster


def person(s, name="Alex Example", kind="staff", **kw):
    return roster.create_person(s, name=name, kind=kind, actor="test", **kw)


def test_roster_load_is_idempotent_including_revisions_and_audits(tmp_path):
    with transaction() as s:
        business = Business(id=uuid4(), name="Example Client", slug="example-client")
        s.add(business)
    path = tmp_path / "roster.yaml"
    path.write_text(yaml.safe_dump({
        "people": [{"name": "Alex Example", "kind": "staff", "functions": ["ads_google"],
                    "emails": ["ALEX@example.com"], "clickup": ["10000001"], "slack": ["U000EXAMPLE1"]}],
        "shared_mailboxes": [{"name": "Example Main Inbox", "email": "hello@example.org",
                               "clickup": ["10000002"], "holders": [{"person": "Alex Example", "from": "2026-01-01"}]}],
        "account_teams": {"example-client": {"owner": "Alex Example"}},
    }), encoding="utf-8")
    counts = roster.load_roster(path)
    assert counts["people_created"] == 2 and counts["addresses_added"] == 5
    with transaction() as s:
        first = [(p.id, p.revision) for p in s.execute(select(Person).order_by(Person.name)).scalars()]
        audit_count = s.scalar(select(func.count()).select_from(AuditEvent))
        assert all(p.status == "pending" for p in s.execute(select(Person)).scalars())
        assert s.execute(select(PersonAddress.value).where(PersonAddress.kind == "email",
            PersonAddress.person_id == first[0][0])).scalar_one() == "alex@example.com"
        assert s.scalar(select(func.count()).select_from(MailboxHolder)) == 1
        assert s.scalar(select(func.count()).select_from(AccountTeamMember)) == 1
    assert not any(roster.load_roster(path).values())
    with transaction() as s:
        assert [(p.id, p.revision) for p in s.execute(select(Person).order_by(Person.name)).scalars()] == first
        assert s.scalar(select(func.count()).select_from(AuditEvent)) == audit_count


def test_addresses_are_exact_lowercase_unique_across_email_kinds():
    with transaction() as s:
        a, b = person(s), person(s, "Sam Sample")
        addr = roster.add_address(s, a.id, "email", "ALEX@EXAMPLE.COM", actor="test")
        assert addr.value == "alex@example.com"
        assert roster.add_address(s, a.id, "email", "alex@example.com", actor="test").id == addr.id
        for kind in ("email", "fathom_email"):
            with pytest.raises(roster.PeopleError, match="another person"):
                roster.add_address(s, b.id, kind, "alex@example.com", actor="test")
        for domain in ("gmail.com", "@gmail.com", "example.com"):
            with pytest.raises(roster.PeopleError, match="exact email"):
                roster.add_address(s, a.id, "email", domain, actor="test")
        roster.add_address(s, a.id, "fathom_email", "alex@example.com", actor="test")


def test_update_revision_and_internal_function_validation():
    with transaction() as s:
        a = person(s)
        roster.update_person(s, a.id, expected_revision=1, actor="test", functions=["ads_meta"])
        assert a.revision == 2
        with pytest.raises(RevisionConflict):
            roster.update_person(s, a.id, expected_revision=1, actor="test", name="Stale Example")
        with pytest.raises(roster.PeopleError):
            person(s, "Unknown Example", "partner", functions=["ads_google"])
        with pytest.raises(roster.PeopleError):
            person(s, "Other Example", functions=["unsupported_function"])


def test_remove_address_is_audited_revision_checked_and_idempotent():
    with transaction() as s:
        a = person(s)
        roster.add_address(s, a.id, "email", "alex@example.com", actor="test")
        with pytest.raises(RevisionConflict):
            roster.remove_address(s, a.id, "email", "alex@example.com", actor="test", expected_revision=1)
        roster.remove_address(s, a.id, "email", "alex@example.com", actor="test", expected_revision=2)
        assert a.revision == 3
        roster.remove_address(s, a.id, "email", "alex@example.com", actor="test", expected_revision=3)
        assert a.revision == 3


def test_mailbox_holder_intervals_are_inclusive_and_handoff_is_idempotent():
    with transaction() as s:
        a, b, box = person(s), person(s, "Sam Sample"), person(s, "Example Shared Inbox", "shared_mailbox")
        old = roster.set_mailbox_holder(s, box.id, a.id, valid_from=date(2026, 1, 1), actor="test")
        current = roster.set_mailbox_holder(s, box.id, b.id, valid_from=date(2026, 3, 1), actor="test")
        assert old.valid_to == date(2026, 2, 28)
        revision = box.revision
        assert roster.set_mailbox_holder(s, box.id, b.id, valid_from=date(2026, 3, 1), actor="test").id == current.id
        assert box.revision == revision
        with pytest.raises(roster.PeopleError):
            roster.set_mailbox_holder(s, box.id, a.id, valid_from=date(2026, 2, 1), actor="test")


def test_loader_preserves_undated_holder_history_without_guessing(tmp_path):
    path = tmp_path / "roster.yaml"
    path.write_text(yaml.safe_dump({"people": [{"name": n, "kind": "staff"} for n in ("Alex Example", "Sam Sample")],
        "shared_mailboxes": [{"name": "Example Shared Inbox", "email": "support@example.net", "holders":
                             [{"person": "Alex Example"}, {"person": "Sam Sample"}]}]}), encoding="utf-8")
    roster.load_roster(path)
    with transaction() as s:
        rows = s.execute(select(MailboxHolder)).scalars().all()
        assert len(rows) == 2 and all(r.valid_from is None and r.valid_to is None for r in rows)
        assert all("unresolved" in r.note for r in rows)


def test_mailbox_handoff_keeps_undated_evidence_and_rejects_closed_history_overlap():
    with transaction() as s:
        a, b, box = person(s), person(s, "Sam Sample"), person(s, "Example Shared Inbox", "shared_mailbox")
        historical = MailboxHolder(id=uuid4(), mailbox_person_id=box.id, holder_person_id=a.id,
                                   note="Historical holder; transfer date is unknown.")
        s.add(historical)
        current = roster.set_mailbox_holder(s, box.id, b.id, valid_from=date(2026, 3, 1), actor="test")
        assert historical.valid_from is None and historical.valid_to is None
        revision = box.revision
        assert roster.set_mailbox_holder(s, box.id, b.id, valid_from=date(2026, 3, 1), actor="test").id == current.id
        assert box.revision == revision
        current.valid_to = date(2026, 3, 31)
        s.flush()
        with pytest.raises(roster.PeopleError, match="overlaps"):
            roster.set_mailbox_holder(s, box.id, a.id, valid_from=date(2026, 3, 15), actor="test")


def test_internal_addresses_include_roster_and_legacy_team_rules():
    with transaction() as s:
        a, p = person(s), person(s, "Partner Example", "partner")
        roster.add_address(s, a.id, "email", "alex@example.com", actor="test")
        roster.add_address(s, a.id, "clickup_user", "10000001", actor="test")
        roster.add_address(s, p.id, "email", "partner@example.net", actor="test")
        s.add(SenderRule(id=uuid4(), kind="team", email="legacy@example.org", reason="legacy", created_by="test", created_at=utcnow()))
        s.flush()
        assert roster.internal_addresses(s) == {"alex@example.com", "legacy@example.org"}
        assert roster.internal_ids(s) == {"slack_user": set(), "clickup_user": {"10000001"}}


def test_merge_moves_addresses_identities_teams_and_preserves_history():
    with transaction() as s:
        keep, merged = person(s), person(s, "Duplicate Example", "contractor")
        roster.add_address(s, merged.id, "email", "duplicate@example.net", actor="test")
        business = Business(id=uuid4(), name="Example Client", slug="example-client")
        account = ConnectorAccount(id=uuid4(), provider="slack", provider_account_id="TEXAMPLE",
            expected_identity="TEXAMPLE", credential_ref="TEST")
        s.add_all([business, account])
        s.flush()
        identity = ProviderIdentity(id=uuid4(), connector_account_id=account.id, external_key="U000EXAMPLE1",
            person_id=merged.id, party="internal", is_internal=True, resolution_basis="admin")
        keeper_team = AccountTeamMember(id=uuid4(), business_id=business.id, person_id=keep.id, role="ads_google",
            status="suggested", source="admin")
        duplicate_team = AccountTeamMember(id=uuid4(), business_id=business.id, person_id=merged.id, role="ads_google",
            status="confirmed", source="admin")
        s.add_all([identity, keeper_team, duplicate_team])
        s.flush()
        roster.merge_people(s, keep.id, merged.id, actor="test")
        s.flush()
        assert merged.merged_into_id == keep.id
        assert identity.person_id == keep.id and identity.party == "internal" and identity.resolution_basis == "admin"
        assert keeper_team.status == "confirmed" and duplicate_team.status == "ended"
        assert duplicate_team.person_id == keep.id
        assert s.execute(select(PersonAddress.person_id).where(PersonAddress.value == "duplicate@example.net")).scalar_one() == keep.id
        assert roster.person_by_name_or_id(s, merged.id).id == keep.id


def test_shared_mailboxes_cannot_merge_into_people_and_names_can_be_ambiguous():
    with transaction() as s:
        a, b, box = person(s), person(s, "Alex Example", "contractor"), person(s, "Example Inbox", "shared_mailbox")
        with pytest.raises(roster.PeopleError, match="ambiguous"):
            roster.person_by_name_or_id(s, "Alex Example")
        with pytest.raises(roster.PeopleError, match="shared mailboxes"):
            roster.merge_people(s, a.id, box.id, actor="test")
        assert roster.person_by_name_or_id(s, a.id).id == a.id
