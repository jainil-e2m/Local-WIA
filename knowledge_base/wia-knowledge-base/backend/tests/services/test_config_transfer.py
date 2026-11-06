"""Production bootstrap: configuration moves to an empty database; source data, tokens and LeadLock stay behind."""
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from backend.db import engine, transaction
from backend.models.db import (Business, ConnectorAccount, Contact, Person, SourceRecord, SourceScope)
from backend.services.clients import config_transfer, mapping


def _seed():
    with transaction() as s:
        b = mapping.create_client(s, name="Venue One", slug="venue-one", aliases=["V One"], actor="t", discover=False)
        s.add(Contact(id=uuid4(), business_id=b.id, email="dana@venue-example.com", status="approved"))
        keep = Person(id=uuid4(), name="Alex", kind="staff")
        s.add(keep)
        s.flush()
        s.add(Person(id=uuid4(), name="Alex (old)", kind="staff", merged_into_id=keep.id))
        slack = ConnectorAccount(id=uuid4(), provider="slack", provider_account_id="T1", expected_identity="T1",
                                 credential_ref="SLACK_BOT_TOKEN", lease_until=datetime.now(UTC))
        ll = ConnectorAccount(id=uuid4(), provider="leadlock", provider_account_id="co", expected_identity="co",
                              credential_ref="leadlock_installations")
        s.add_all([slack, ll])
        s.flush()
        channel = SourceScope(id=uuid4(), connector_account_id=slack.id, kind="channel", external_id="C1", name="venue",
                              state="approved", default_domain="communications", association_mode="dedicated",
                              business_id=b.id, last_successful_sync_at=datetime.now(UTC))
        s.add_all([channel, SourceScope(id=uuid4(), connector_account_id=ll.id, kind="location", external_id="loc",
                                        name="venue", state="approved", default_domain="leads",
                                        association_mode="dedicated", business_id=b.id)])
        s.flush()
        s.add(SourceRecord(id=uuid4(), connector_account_id=slack.id, scope_id=channel.id, record_kind="slack_message",
                           external_id="m1"))


def _wipe():
    with engine.begin() as conn:
        tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' "
                                   "AND tablename <> 'alembic_version'")).scalars()
        conn.execute(text("TRUNCATE " + ", ".join(tables) + " CASCADE"))


def test_export_then_import_into_an_empty_database():
    _seed()
    with transaction() as s:
        data = json.loads(config_transfer.dumps(config_transfer.export(s)))
    assert "slack_message" not in json.dumps(data)  # no source data in the file
    _wipe()
    with transaction() as s:
        counts = config_transfer.import_(s, data, actor="test")
    assert counts == {name: len(rows) for name, rows in data["tables"].items()}
    assert counts["businesses"] == 1 and counts["contacts"] == 1 and counts["people"] == 2
    assert counts["connector_accounts"] == 1 and counts["source_scopes"] == 1  # LeadLock stays behind
    with transaction() as s:
        assert s.scalar(select(func.count()).select_from(SourceRecord)) == 0
        account = s.execute(select(ConnectorAccount)).scalar_one()
        assert account.provider == "slack" and account.lease_until is None
        scope = s.execute(select(SourceScope)).scalar_one()
        assert scope.business_id == s.execute(select(Business.id)).scalar_one() and scope.last_successful_sync_at is None
        old = s.execute(select(Person).where(Person.name == "Alex (old)")).scalar_one()
        assert s.get(Person, old.merged_into_id).name == "Alex"


def test_import_refuses_a_database_that_already_has_clients():
    _seed()
    with transaction() as s:
        data = json.loads(config_transfer.dumps(config_transfer.export(s)))
    with pytest.raises(ValueError, match="already has clients"), transaction() as s:
        config_transfer.import_(s, data, actor="test")
