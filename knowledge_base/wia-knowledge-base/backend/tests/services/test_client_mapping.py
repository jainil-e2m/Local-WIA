"""S2 client mapping: admin commands, archive pauses syncing, coverage, ClickUp client-space discovery."""
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from backend.db import transaction
from backend.models.db import AuditEvent, ConnectorAccount, Contact, SourceScope, WorkItem
from backend.models.domain.intake import BusinessHint, DiscoveryResult, ScopeCandidate
from backend.services.clients import mapping
from backend.services.intake import discovery, pipeline, sync
from backend.services.intake.adapters.clickup import ClickUpAdapter
from backend.services.intake.scoping import is_live, live_contacts, live_scope


def _account(s, provider):
    a = ConnectorAccount(id=uuid4(), provider=provider, provider_account_id=f"{provider}-1",
                         expected_identity=f"{provider}-1", credential_ref="X")
    s.add(a)
    s.flush()
    return a


def _scope(s, account, external_id, *, business_id=None, state="approved"):
    sc = SourceScope(id=uuid4(), connector_account_id=account.id, kind="channel", external_id=external_id,
                     name=f"#{external_id}", state=state, default_domain="communications",
                     association_mode="dedicated" if business_id else "per_record", business_id=business_id)
    s.add(sc)
    s.flush()
    return sc


@pytest.fixture
def venue():
    with transaction() as s:
        return mapping.create_client(s, name="Venue One", slug="venue-one", aliases=["V1"], actor="admin").id


def test_create_client_records_aliases_audit_and_queues_discovery(venue):
    with transaction() as s:
        b = mapping.business_by_slug(s, "venue-one")
        assert b.status == "active" and b.revision == 1
        assert s.execute(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "business.create", AuditEvent.actor == "admin")).scalar_one() == 1
        job = s.execute(select(WorkItem).where(WorkItem.kind == mapping.DISCOVER_JOB)).scalar_one()
        assert job.payload == {"business_id": str(venue)}
        with pytest.raises(mapping.MappingError):
            mapping.create_client(s, name="Again", slug="venue-one", actor="admin")


def test_stale_revision_is_refused(venue):
    with transaction() as s:
        mapping.update_client(s, venue, expected_revision=1, actor="a", add_aliases=["Venue 1"])
    with transaction() as s, pytest.raises(mapping.RevisionConflict):
        mapping.update_client(s, venue, expected_revision=1, actor="b", name="Overwrite")


def test_archive_pauses_dedicated_scopes_and_contacts_then_resumes(venue):
    with transaction() as s:
        slack = _account(s, "slack")
        own = _scope(s, slack, "C1", business_id=venue)
        shared = _scope(s, slack, "C2")
        mapping.add_contact(s, venue, actor="a", domain="venueone.com")
        mapping.set_client_status(s, venue, "inactive", expected_revision=None, actor="a")
    with transaction() as s:
        assert not is_live(s, s.get(SourceScope, own.id)) and is_live(s, s.get(SourceScope, shared.id))
        assert {x.id for x in s.execute(select(SourceScope).where(live_scope())).scalars()} == {shared.id}
        assert live_contacts(s) == []
        assert pipeline.start_backfill(s, [own.id], 30) == []
        with pytest.raises(ValueError, match="archived"):
            sync.request_run(s, own.id)
        assert mapping.coverage(s)[0]["cells"]["slack"][0] == "paused"
    with transaction() as s:
        b = mapping.set_client_status(s, venue, "active", expected_revision=None, actor="a")
        assert b.status_changed_at is not None
    with transaction() as s:
        assert is_live(s, s.get(SourceScope, own.id)) and len(live_contacts(s)) == 1
        assert s.execute(select(AuditEvent.action).where(AuditEvent.target_id == str(venue))
                         .order_by(AuditEvent.created_at)).scalars().all()[-2:] == ["business.archive", "business.reactivate"]


def test_public_domains_are_never_approved(venue):
    with transaction() as s:
        with pytest.raises(mapping.MappingError):
            mapping.add_contact(s, venue, actor="a", domain="gmail.com")
        c = Contact(id=uuid4(), business_id=venue, domain="aol.com", status="candidate", origin="discovery")
        s.add(c)
        s.flush()
        with pytest.raises(mapping.MappingError):
            mapping.review_contact(s, c.id, approve=True, expected_revision=None, actor="a")


def test_add_scope_by_id_confirms_with_provider_and_approves(venue):
    with transaction() as s:
        _account(s, "clickup")
        found = ScopeCandidate(kind="list", external_id="901", name="Old onboarding", parent_name="Space / Folder",
                               default_domain="actions", association_mode="dedicated", stats={"archived": True})
        scope = mapping.add_scope_by_id(s, "clickup", "list", "901", business_id=venue, actor="a",
                                        describe=lambda kind, ext: found)
        assert (scope.state, scope.association_mode, scope.business_id) == ("approved", "dedicated", venue)
        assert scope.discovery_stats == {"archived": True} and scope.revision == 2
        with pytest.raises(mapping.MappingError, match="not connected"):
            mapping.add_scope_by_id(s, "drive", "folder", "F1", business_id=venue, actor="a")


def test_coverage_marks_every_cell_explicitly(venue):
    with transaction() as s:
        slack, gmail = _account(s, "slack"), _account(s, "gmail")
        _account(s, "clickup")
        _scope(s, slack, "C1", business_id=venue)
        _scope(s, gmail, "hello@")  # shared mailbox, per record
        mapping.add_contact(s, venue, actor="a", domain="venueone.com")
        mapping.mark_not_applicable(s, venue, "clickup", reason="no ClickUp work", actor="a")
        cells = {p: st for p, (st, _) in mapping.coverage(s)[0]["cells"].items()}
    assert cells == {"slack": "mapped", "gmail": "via_contacts", "clickup": "not_applicable",
                     "drive": "not_connected", "calendar": "not_connected", "fathom": "not_connected",
                     "leadlock": "not_connected"}


def test_one_client_discovery_never_clears_another_clients_suggestion(venue, monkeypatch):
    with transaction() as s:
        other = mapping.create_client(s, name="Other", slug="other", actor="a", discover=False).id
        _account(s, "slack")

    class Fake:
        def discover(self, hints, start, end):
            hit = next((h for h in hints if h.business_id == other), None)
            return DiscoveryResult(scopes=[ScopeCandidate("channel", "C9", "#other", None, "communications",
                "dedicated", suggested_business_id=hit.business_id if hit else None, reason="match" if hit else None)])

    monkeypatch.setattr(discovery, "get_adapter", lambda provider: Fake())
    discovery.discover("slack", 30)
    discovery.discover("slack", 30, [venue])
    with transaction() as s:
        scope = s.execute(select(SourceScope).where(SourceScope.external_id == "C9")).scalar_one()
        assert scope.suggested_business_id == other and scope.suggestion_reason == "match"


class FakeHttp:
    def __init__(self, responses):
        self.responses = responses

    def get_json(self, path, params=None):
        return self.responses.get((path, (params or {}).get("archived")), {"spaces": [], "folders": [], "lists": []})


def test_clickup_proposes_every_client_space_folder_and_flags_archived(monkeypatch):
    monkeypatch.setattr("backend.services.intake.adapters.clickup.get_settings",
                        lambda: type("S", (), {"clickup_client_spaces": ["Clients"]})())
    a = ClickUpAdapter.__new__(ClickUpAdapter)
    a.team_id = "T"
    a.http = FakeHttp({
        ("team/T/space", "false"): {"spaces": [{"id": "S1", "name": "Clients"}, {"id": "S2", "name": "Internal"}]},
        ("space/S1/folder", "false"): {"folders": [
            {"id": "F1", "name": "Known Venue", "lists": [{"id": "L1", "name": "Client Management"}]},
            {"id": "F2", "name": "Brand New Venue", "lists": [{"id": "L2", "name": "Client Management"}]}]},
        ("folder/F1/list", "true"): {"lists": [{"id": "L3", "name": "Old Onboarding", "archived": True}]},
        ("space/S2/list", "false"): {"lists": [{"id": "L4", "name": "Carmen"}]},
    })
    known = BusinessHint(uuid4(), "Known Venue", ("Known Venue",))
    found = {c.external_id: c for c in a.discover([known], None, None).scopes}
    assert set(found) == {"L1", "L2", "L3"}  # nothing from the non-client space
    assert found["L1"].suggested_business_id == known.business_id
    assert found["L2"].suggested_business_id is None and "no client matches" in found["L2"].reason
    assert found["L2"].stats["client_container"] == "Brand New Venue"
    assert found["L3"].stats["archived"] and found["L3"].reason.startswith("archived; ")
