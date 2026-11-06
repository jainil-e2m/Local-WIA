"""Pipeline invariants with a fake adapter (no provider calls)."""
import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from backend.db import transaction
from backend.models.db import (
    Business,
    ConnectorAccount,
    ContentUnit,
    RecordAssociation,
    SourceRecord,
    SourceScope,
    SourceVersion,
    SyncCursor,
    SyncRun,
    WorkItem,
)
from backend.models.domain.intake import ChangeBatch, IdentityRef, NormalisedRecord, UnitIn
from backend.services.intake import pipeline
from backend.services.shared.errors import TransientError
from backend.workers import queue, runner


class FakeAdapter:
    provider = "slack"
    parser_version = "fake-v1"
    pages: list = []
    fail_on_page: int | None = None

    def backfill_page(self, ctx, cursor):
        n = json.loads(cursor)["page"] if cursor else 0
        if FakeAdapter.fail_on_page == n:
            raise TransientError("boom")
        recs, last = FakeAdapter.pages[n]
        return ChangeBatch(records=recs, next_cursor=None if last else json.dumps({"page": n + 1}),
                           terminal=last, discovered=len(recs))


def _rec(ext, text):
    author = IdentityRef("U1", "Ann")
    return NormalisedRecord("slack_message", ext, None, None, None, {"channel": "C1"},
                            [UnitIn("message", text, {"ts": ext}, author=author)], participants=[author])


@pytest.fixture
def scope(monkeypatch):
    monkeypatch.setattr(pipeline, "get_adapter", lambda provider: FakeAdapter())
    FakeAdapter.fail_on_page = None
    with transaction() as s:
        b = Business(id=uuid4(), name="Venue", slug="venue")
        a = ConnectorAccount(id=uuid4(), provider="slack", provider_account_id="T1", expected_identity="T1",
                             credential_ref="SLACK_BOT_TOKEN")
        s.add_all([b, a])
        s.flush()
        sc = SourceScope(id=uuid4(), connector_account_id=a.id, kind="channel", external_id="C1", name="#c",
                         state="approved", default_domain="communications", association_mode="dedicated",
                         business_id=b.id)
        s.add(sc)
    return sc.id


def _drain():
    while runner.run_one(["bulk"]):
        pass


def _count(model):
    with transaction() as s:
        return s.execute(select(func.count()).select_from(model)).scalar_one()


def test_backfill_is_idempotent_and_associates(scope):
    FakeAdapter.pages = [([_rec("1", "hello"), _rec("2", "world")], False), ([_rec("3", "!")], True)]
    with transaction() as s:
        pipeline.start_backfill(s, [scope], 30)
    _drain()
    assert _count(SourceRecord) == 3 and _count(SourceVersion) == 3 and _count(ContentUnit) == 3
    assert _count(RecordAssociation) == 3
    with transaction() as s:
        run = s.execute(select(SyncRun)).scalar_one()
        assert run.state == "succeeded" and run.pages == 2
        assert s.get(SourceScope, scope).last_successful_sync_at == run.window_end

    with transaction() as s:  # second run over unchanged data: no new versions
        pipeline.start_backfill(s, [scope], 30)
    _drain()
    assert _count(SourceVersion) == 3

    FakeAdapter.pages[0] = ([_rec("1", "hello EDITED"), _rec("2", "world")], False)
    with transaction() as s:
        pipeline.start_backfill(s, [scope], 30)
    _drain()
    assert _count(SourceVersion) == 4  # edit = new version; the old one is kept
    assert _count(ContentUnit) == 4


def test_failed_page_does_not_advance_cursor_or_last_sync(scope):
    FakeAdapter.pages = [([_rec("1", "a")], False), ([_rec("2", "b")], True)]
    FakeAdapter.fail_on_page = 1
    with transaction() as s:
        pipeline.start_backfill(s, [scope], 30)
    for _ in range(10):  # page 0 succeeds; page 1 fails until retries run out (each retry forced due)
        with transaction() as s:
            s.execute(WorkItem.__table__.update().values(next_run_at=func.now()))
        runner.run_one(["bulk"])
    with transaction() as s:
        run = s.execute(select(SyncRun)).scalar_one()
        cursor = s.execute(select(SyncCursor)).scalar_one()
        assert run.state == "failed"
        assert json.loads(cursor.cursor) == {"page": 1}  # stopped at the failed page, not past it
        assert s.get(SourceScope, scope).last_successful_sync_at is None
    assert _count(SourceRecord) == 1


def test_lost_lease_cannot_publish(scope):
    FakeAdapter.pages = [([_rec("1", "a")], True)]
    with transaction() as s:
        pipeline.start_backfill(s, [scope], 30)
    with transaction() as s:
        item = queue.claim(s, ["bulk"])
        work_id, payload = item.id, item.payload
    with pytest.raises(queue.LeaseLostError):
        pipeline.run_backfill_page(work_id, uuid4(), payload)  # someone else's token
    assert _count(SourceRecord) == 0

