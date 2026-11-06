"""Invented identities exercise party resolution, idempotence and roster filters."""
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select

from backend.db import engine, transaction
from backend.models.db import Business, ConnectorAccount, Contact, ProviderIdentity
from backend.models.db.people import Person, PersonAddress
from backend.models.domain.intake import ContactCandidate, DiscoveryResult, IdentityRef
from backend.services.clients import mapping
from backend.services.intake import discovery, scoping
from backend.services.intake.persist import IdentityCache
from backend.services.people import resolve, roster


@pytest.fixture
def world():
    with transaction() as s:
        client = mapping.create_client(s, name="Example Venue", slug="example-venue", actor="test", discover=False)
        accounts = {}
        for provider in ("slack", "clickup", "gmail", "calendar", "drive", "fathom"):
            a = ConnectorAccount(id=uuid4(), provider=provider, provider_account_id="test-" + provider,
                                 expected_identity="test-" + provider, credential_ref="TEST")
            s.add(a)
            accounts[provider] = a.id
        return client.id, accounts


def person(s, name="Alex Example", kind="staff", **kwargs):
    return roster.create_person(s, name=name, kind=kind, actor="test", **kwargs)


def identity(s, world, provider="slack", key="U000EXAMPLE1", email=None, name=None):
    row = ProviderIdentity(id=uuid4(), connector_account_id=world[1][provider], external_key=key,
                           email=email, display_name=name)
    s.add(row)
    s.flush()
    return row


def do_resolve(s, row):
    resolve.resolve_identity(s, row, resolve.Resolver(s))
    return row


def test_bot_first_even_when_its_email_is_on_roster(world):
    with transaction() as s:
        p = person(s)
        roster.add_address(s, p.id, "email", "alex@example.com", actor="test")
        row = do_resolve(s, identity(s, world, key="bot:B000EXAMPLE1", email="alex@example.com"))
        assert row.party == "bot" and row.person_id is None and row.is_internal is False


@pytest.mark.parametrize("provider,kind,key", [("slack", "slack_user", "U000EXAMPLE1"),
                                              ("clickup", "clickup_user", "10000001")])
def test_native_id_precedes_conflicting_email(world, provider, kind, key):
    with transaction() as s:
        a, b = person(s), person(s, "Sam Sample")
        roster.add_address(s, a.id, kind, key, actor="test")
        roster.add_address(s, b.id, "email", "sam@example.org", actor="test")
        row = do_resolve(s, identity(s, world, provider, key, "sam@example.org"))
        assert row.person_id == a.id and row.party == "internal" and row.resolution_basis == "provider_id"


@pytest.mark.parametrize("provider", ["gmail", "calendar", "drive", "fathom"])
def test_exact_email_resolves_across_providers(world, provider):
    with transaction() as s:
        p = person(s, kind="contractor")
        roster.add_address(s, p.id, "email", "alex@example.com", actor="test")
        row = do_resolve(s, identity(s, world, provider, "alex@example.com"))
        assert row.person_id == p.id and row.party == "internal" and row.is_internal is True
        assert row.resolution_basis == "email"


def test_fathom_email_alias(world):
    with transaction() as s:
        p = person(s)
        roster.add_address(s, p.id, "fathom_email", "alex@example.org", actor="test")
        row = do_resolve(s, identity(s, world, "fathom", "speaker:Unmatched", "alex@example.org"))
        assert row.person_id == p.id and row.resolution_basis == "email"


@pytest.mark.parametrize("speaker", ["ALEX EXAMPLE", "Álex Éxample"])
def test_fathom_full_name_is_case_and_accent_insensitive(world, speaker):
    with transaction() as s:
        p = person(s)
        row = do_resolve(s, identity(s, world, "fathom", "speaker:" + speaker))
        assert row.person_id == p.id and row.resolution_basis == "display_name"


def test_fathom_display_alias_only_applies_to_internal_people(world):
    with transaction() as s:
        p = person(s)
        roster.add_address(s, p.id, "display_name", "Alex E.", actor="test")
        row = do_resolve(s, identity(s, world, "fathom", "speaker:Alex E."))
        assert row.person_id == p.id
        client = person(s, "Sam Sample", "client_contact", business_id=world[0])
        with pytest.raises(roster.PeopleError):
            roster.add_address(s, client.id, "display_name", "Sam S.", actor="test")
        row = do_resolve(s, identity(s, world, "fathom", "speaker:Sam S."))
        assert row.person_id is None and row.party == "unknown"


@pytest.mark.parametrize("provider", ["slack", "clickup", "gmail", "calendar", "drive"])
def test_fathom_name_alias_is_not_global_across_providers(world, provider):
    with transaction() as s:
        p = person(s)
        roster.add_address(s, p.id, "display_name", "Alex E.", actor="test")
        row = do_resolve(s, identity(s, world, provider, "speaker:Alex E."))
        assert row.person_id is None and row.party == "unknown"


def test_former_native_user_and_email_free_outsider_remain_distinct(world):
    with transaction() as s:
        p = person(s, kind="former")
        roster.add_address(s, p.id, "slack_user", "U000FORMER", actor="test")
        former = do_resolve(s, identity(s, world, "slack", "U000FORMER"))
        outsider = do_resolve(s, identity(s, world, "slack", "U000OUTSIDER"))
        assert former.person_id == p.id and former.party == "internal"
        assert outsider.party == "unknown" and outsider.email is None
        assert [item["id"] for item in resolve.unknown_people(s)] == [str(outsider.id)]


def test_fathom_never_matches_client_name_or_partial_staff_name(world):
    with transaction() as s:
        person(s, "Alex Example", "client_contact", business_id=world[0])
        person(s, "Sam Sample")
        for key in ("speaker:Alex Example", "speaker:Sam"):
            row = do_resolve(s, identity(s, world, "fathom", key))
            assert row.person_id is None and row.party == "unknown"


def test_ambiguous_full_names_do_not_guess(world):
    with transaction() as s:
        person(s)
        person(s, kind="contractor")
        row = do_resolve(s, identity(s, world, "fathom", "speaker:Alex Example"))
        assert row.person_id is None and row.party == "unknown"


def test_contact_address_creates_one_person_and_resolution_is_idempotent(world):
    with transaction() as s:
        mapping.add_contact(s, world[0], email="client@example.org", actor="test")
        rows = [identity(s, world, p, "client@example.org", email="client@example.org") for p in ("gmail", "calendar")]
        ctx = resolve.Resolver(s)
        for row in rows:
            resolve.resolve_identity(s, row, ctx)
        assert rows[0].person_id == rows[1].person_id
        assert all(r.party == "client" and r.party_business_id == world[0] and r.resolution_basis == "client_contact" for r in rows)
        before = [(r.person_id, r.resolution_basis, r.resolved_at) for r in rows]
        count = s.scalar(select(func.count()).select_from(Person))
        resolve.resolve_all(s)
        assert before == [(r.person_id, r.resolution_basis, r.resolved_at) for r in rows]
        assert s.scalar(select(func.count()).select_from(Person)) == count == 1


def test_archived_client_contacts_still_resolve_for_history(world):
    with transaction() as s:
        mapping.add_contact(s, world[0], email="client@example.org", actor="test")
        s.get(Business, world[0]).status = "inactive"
        row = do_resolve(s, identity(s, world, "gmail", "client@example.org"))
        assert row.party == "client" and row.person_id is not None
        assert scoping.live_contacts(s) == []


def test_client_domain_has_no_guessed_person(world):
    with transaction() as s:
        mapping.add_contact(s, world[0], domain="example.org", actor="test")
        row = do_resolve(s, identity(s, world, "gmail", "new@example.org"))
        assert row.party == "client" and row.party_business_id == world[0]
        assert row.person_id is None and row.resolution_basis == "client_domain"
        assert s.scalar(select(func.count()).select_from(Person)) == 0


def test_ambiguous_client_contacts_do_not_choose_a_business(world):
    with transaction() as s:
        other = mapping.create_client(s, name="Example Other", slug="example-other", actor="test", discover=False)
        for bid in (world[0], other.id):
            mapping.add_contact(s, bid, email="shared@example.org", actor="test")
        row = do_resolve(s, identity(s, world, "gmail", "shared@example.org"))
        assert row.party == "unknown" and row.person_id is None and row.party_business_id is None


def test_partner_rule_prevents_client_resolution_but_keeps_one_client_link(world):
    with transaction() as s:
        mapping.add_contact(s, world[0], email="consultant@example.org", actor="test")
        mapping.add_sender_rule(s, "partner", domain="example.org", actor="test", reason="shared consultant")
        row = do_resolve(s, identity(s, world, "gmail", "consultant@example.org"))
        assert row.party == "partner" and row.person_id is None
        assert row.party_business_id == world[0] and row.resolution_basis == "partner_rule"


def test_internal_not_on_roster_is_visible_in_unknown_queue(world, monkeypatch):
    monkeypatch.setattr(resolve, "is_internal", lambda e: e == "unlisted@example.com")
    with transaction() as s:
        row = do_resolve(s, identity(s, world, "gmail", "unlisted@example.com"))
        assert row.party == "internal" and row.person_id is None and row.is_internal is True
        queue = resolve.unknown_people(s)
        assert queue[0]["id"] == str(row.id) and queue[0]["reason"] == "internal, not on roster"


def test_team_rule_is_backwards_compatible(world):
    with transaction() as s:
        mapping.add_contact(s, world[0], email="external@example.org", actor="test")
        mapping.add_sender_rule(s, "team", email="external@example.org", actor="test", reason="roster pending")
        row = do_resolve(s, identity(s, world, "gmail", "external@example.org"))
        assert row.party == "internal" and row.person_id is None


def test_automated_and_unknown(world):
    with transaction() as s:
        row = do_resolve(s, identity(s, world, "gmail", "billing@example.net"))
        assert row.party == "automated"
        row = do_resolve(s, identity(s, world, "gmail", "outsider@example.net"))
        assert row.party == "unknown" and row.person_id is None


@pytest.mark.parametrize("kind", ["prospect", "programme_member"])
def test_known_external_person_is_not_internal_or_client(world, kind):
    with transaction() as s:
        p = person(s, kind=kind)
        roster.add_address(s, p.id, "email", "alex@example.org", actor="test")
        row = do_resolve(s, identity(s, world, "gmail", "alex@example.org"))
        assert row.party == "unknown" and row.person_id == p.id and row.is_internal is False


def test_shared_mailbox_and_holder_history(world):
    with transaction() as s:
        box = person(s, "Example Inbox", "shared_mailbox")
        a, b = person(s), person(s, "Sam Sample")
        roster.add_address(s, box.id, "email", "hello@example.org", actor="test")
        roster.set_mailbox_holder(s, box.id, a.id, valid_from=date(2026, 1, 1), actor="test")
        roster.set_mailbox_holder(s, box.id, b.id, valid_from=date(2026, 3, 1), actor="test")
        row = do_resolve(s, identity(s, world, "gmail", "hello@example.org"))
        assert row.party == "shared_mailbox" and row.person_id == box.id and row.is_internal is True
        assert resolve.mailbox_holder_at(s, box.id, date(2026, 2, 28)).id == a.id
        assert resolve.mailbox_holder_at(s, box.id, date(2026, 3, 1)).id == b.id


def test_intake_resolution_preserves_admin_link_and_partial_metadata(world):
    with transaction() as s:
        p = person(s)
        iid = IdentityCache(s, world[1]["slack"]).resolve(IdentityRef("U000EXAMPLE1", "Old Name", "unlisted@example.org"))
        resolve.link_identity(s, iid, p.id, actor="test", expected_revision=p.revision)
        linked_at = s.get(ProviderIdentity, iid).resolved_at
    with transaction() as s:
        assert IdentityCache(s, world[1]["slack"]).resolve(IdentityRef("U000EXAMPLE1")) == iid
        row = s.get(ProviderIdentity, iid)
        assert row.person_id == p.id and row.resolution_basis == "admin" and row.is_internal is True
        assert row.email == "unlisted@example.org" and row.resolved_at == linked_at


def test_manual_link_requires_current_person_revision_and_is_audited(world):
    with transaction() as s:
        p = person(s)
        row = identity(s, world, "slack", "U000EXAMPLE1")
        with pytest.raises(mapping.RevisionConflict):
            resolve.link_identity(s, row.id, p.id, actor="test", expected_revision=p.revision + 1)
        assert row.person_id is None
        resolve.link_identity(s, row.id, p.id, actor="test", expected_revision=p.revision)
        from backend.models.db import AuditEvent
        audit = s.execute(select(AuditEvent).where(AuditEvent.action == "identity.link")).scalar_one()
        assert audit.target_id == str(row.id) and audit.details == {"person_id": str(p.id)}


def test_pipeline_publication_resolves_people_and_preserves_admin_link(world, monkeypatch):
    from backend.models.db import SourceScope, SyncRun
    from backend.models.domain.intake import ChangeBatch, NormalisedRecord, UnitIn
    from backend.services.intake import pipeline
    from backend.workers import runner

    class FakeAdapter:
        provider = "slack"
        parser_version = "example-v1"
        content = "Example message"
        email = None

        def backfill_page(self, ctx, cursor):
            author = IdentityRef("U000EXAMPLE1", "Provider Name", self.email)
            record = NormalisedRecord("slack_message", "000001.000001", None, None, None,
                {"channel": "C000EXAMPLE"}, [UnitIn("message", self.content,
                {"ts": "000001.000001"}, author=author)], participants=[author])
            return ChangeBatch(records=[record], next_cursor=None, terminal=True, discovered=1)

    adapter = FakeAdapter()
    monkeypatch.setattr(pipeline, "get_adapter", lambda provider: adapter)
    with transaction() as s:
        p, other = person(s), person(s, "Sam Sample")
        roster.add_address(s, p.id, "slack_user", "U000EXAMPLE1", actor="test")
        roster.add_address(s, other.id, "email", "sam@example.org", actor="test")
        scope = SourceScope(id=uuid4(), connector_account_id=world[1]["slack"], kind="channel",
            external_id="C000EXAMPLE", name="#example", state="approved", default_domain="communications",
            association_mode="dedicated", business_id=world[0])
        s.add(scope)
        s.flush()
        scope_id, person_id = scope.id, p.id
        pipeline.start_backfill(s, [scope_id], 30)
    while runner.run_one(["bulk"]):
        pass
    with transaction() as s:
        row = s.execute(select(ProviderIdentity)).scalar_one()
        assert row.person_id == person_id and row.party == "internal"
        resolve.link_identity(s, row.id, person_id, actor="test", expected_revision=s.get(Person, person_id).revision)
        identity_id, linked_at = row.id, row.resolved_at
        assert s.execute(select(SyncRun.state)).scalar_one() == "succeeded"
    adapter.content = "Example message edited"
    adapter.email = "sam@example.org"
    with transaction() as s:
        pipeline.start_backfill(s, [scope_id], 30)
    while runner.run_one(["bulk"]):
        pass
    with transaction() as s:
        row = s.get(ProviderIdentity, identity_id)
        assert row.person_id == person_id and row.party == "internal" and row.resolution_basis == "admin"
        assert row.email == "sam@example.org" and row.resolved_at == linked_at


def test_all_provider_identity_resolution_is_idempotent(world):
    with transaction() as s:
        p = person(s)
        roster.add_address(s, p.id, "email", "alex@example.com", actor="test")
        for provider in world[1]:
            identity(s, world, provider, "alex@example.com")
        counts = resolve.resolve_all(s)
        before = s.execute(select(ProviderIdentity.id, ProviderIdentity.person_id, ProviderIdentity.party,
                                  ProviderIdentity.resolved_at).order_by(ProviderIdentity.id)).all()
        assert resolve.resolve_all(s) == counts == {"internal": 6}
        assert s.execute(select(ProviderIdentity.id, ProviderIdentity.person_id, ProviderIdentity.party,
                                ProviderIdentity.resolved_at).order_by(ProviderIdentity.id)).all() == before


def test_roster_filters_client_candidates_live_contacts_and_conflicts(world):
    with transaction() as s:
        p = person(s, kind="contractor")
        roster.add_address(s, p.id, "email", "personal@example.org", actor="test")
        mapping.add_contact(s, world[0], email="personal@example.org", actor="test")
        internal = roster.internal_addresses(s)
        result = DiscoveryResult(contacts=[ContactCandidate(world[0], "personal@example.org", None, None, "test")])
        discovery.filter_contacts({"gmail": result}, mapping.sender_rules(s), internal_emails=internal)
        assert result.contacts == [] and scoping.live_contacts(s) == []
        assert [(c.email, why) for c, why in mapping.contact_conflicts(s)] == [("personal@example.org", "team member (roster)")]


def test_intake_resolver_lookup_queries_are_bounded_per_page(world):
    with transaction() as s:
        p = person(s)
        for n in range(40):
            roster.add_address(s, p.id, "slack_user", f"U000EXAMPLE{n}", actor="test")
    selects = []
    def count(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)
    event.listen(engine, "before_cursor_execute", count)
    try:
        with transaction() as s:
            cache = IdentityCache(s, world[1]["slack"])
            for n in range(40):
                cache.resolve(IdentityRef(f"U000EXAMPLE{n}"))
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert len(selects) <= 8, len(selects)


def test_service_account_marked_bot_resolves_as_bot_others_stay_internal(world):
    with transaction() as s:
        chat_bot = person(s, name="Example Chat Bot", kind="service_account", functions=["bot"])
        roster.add_address(s, chat_bot.id, "slack_user", "U000BOT0001", actor="test")
        service = person(s, name="Example Service", kind="service_account")
        roster.add_address(s, service.id, "slack_user", "U000SVC0001", actor="test")
        bot_row = do_resolve(s, identity(s, world, key="U000BOT0001", name="Example Chat Bot"))
        svc_row = do_resolve(s, identity(s, world, key="U000SVC0001"))
        assert (bot_row.party, bot_row.person_id, bot_row.is_internal) == ("bot", chat_bot.id, False)
        assert svc_row.party == "internal" and svc_row.is_internal is True
