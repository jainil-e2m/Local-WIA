"""The production sync loop: first copy on the resumable path, streams switched on after it, the scheduler's
sweep (due streams, per-source intervals, reactivation re-checks, resuming copies a decision stopped) and its
single-sweeper lock. Uses the real LeadLock reader against the fake HighLevel API from the adapter tests."""
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from backend.config import get_settings
from backend.db import engine, transaction
from backend.models.db import ConnectorAccount, RecordAssociation, SourceScope, SyncRun, SyncStream, WorkItem
from backend.services.intake.adapters.base import ConnectorIdentity
from backend.services.clients import mapping
from backend.services.intake import leadlock_app, pipeline, sync
from backend.services.intake.adapters import leadlock as ll
from backend.tests.services.test_leadlock_adapter import LOC, FakeAPI, routes
from backend.workers import queue, runner


@pytest.fixture
def venue(monkeypatch):
    monkeypatch.setattr(leadlock_app, "location_token", lambda location_id, http=None: "loc-token")
    adapter = ll.LeadLockAdapter()
    adapter.http = FakeAPI(routes())
    adapter.identify = lambda: ConnectorIdentity(provider_account_id="co", display_identity="co",
                                                 expected_identity_value="co", granted_scopes=[], credential_ref="db")
    monkeypatch.setattr(pipeline, "get_adapter", lambda provider: adapter)
    monkeypatch.setattr(get_settings(), "sync_scheduler_enabled", True)
    with transaction() as s:
        business = mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
        account = ConnectorAccount(id=uuid4(), provider="leadlock", provider_account_id="co", expected_identity="co",
                                   credential_ref="leadlock_installations")
        s.add(account)
        s.flush()
        scope = SourceScope(id=uuid4(), connector_account_id=account.id, kind="location", external_id=LOC,
                            name="Venue One", state="approved", default_domain="leads", association_mode="dedicated",
                            business_id=business.id, revision=1)
        s.add(scope)
        return scope.id, business.id


def sweep():
    with transaction() as s:
        return sync.sweep(s)


def drain(pages=None):
    """Run queued page jobs (all of them, or `pages` of them)."""
    n = 0
    while (pages is None or n < pages) and runner.run_one(["bulk", "sync"]):
        n += 1


def stream_of(scope_id):
    with transaction() as s:
        return s.execute(select(SyncStream).where(SyncStream.scope_id == scope_id)).scalar_one()


def runs(scope_id):
    with transaction() as s:
        return s.execute(select(SyncRun).where(SyncRun.scope_id == scope_id).order_by(SyncRun.started_at)).scalars().all()


def test_first_copy_runs_on_the_resumable_path_then_the_stream_is_kept_current(venue):
    scope_id, business_id = venue
    assert sweep() == 1  # a live source nothing collects yet: its first full copy
    assert sweep() == 0  # already running: nothing more
    drain()
    run = runs(scope_id)[-1]
    assert (run.mode, run.state, run.window_start) == ("backfill", "succeeded", None)
    assert "verify" not in run.checkpoint  # LeadLock skips the deletion pass
    with transaction() as s:
        assert s.scalar(select(func.count()).select_from(RecordAssociation)
                        .where(RecordAssociation.business_id == business_id)) > 0
        now = queue.db_now(s)
    stream = stream_of(scope_id)
    assert stream.enabled and stream.last_reconciled_at is not None
    assert sweep() == 0  # nothing due right after a copy
    with transaction() as s:
        s.get(SyncStream, stream.id).next_sync_at = now - timedelta(seconds=1)
    assert sweep() == 1
    assert runs(scope_id)[-1].mode == "incremental"
    drain()
    # LeadLock re-reads everything, so it's polled every 6 hours, not every 5 minutes.
    assert stream_of(scope_id).next_sync_at - now > timedelta(hours=5, minutes=59)


def test_a_copy_stopped_by_archiving_resumes_from_its_checkpoint_when_reactivated(venue):
    scope_id, business_id = venue
    sweep()
    drain(pages=2)  # part of the copy
    with transaction() as s:
        mapping.set_client_status(s, business_id, "inactive", expected_revision=None, actor="t")
    drain()  # the next page sees the archive and stops the run
    stopped = runs(scope_id)[-1]
    assert (stopped.state, stopped.error_class, stopped.pages) == ("failed", "client_archived", 2)
    assert sweep() == 0  # archived: nothing to start
    with transaction() as s:
        mapping.set_client_status(s, business_id, "active", expected_revision=None, actor="t")
    assert sweep() == 1
    resumed = runs(scope_id)
    assert len(resumed) == 1 and resumed[0].state == "running" and resumed[0].pages == 2  # same run, continued
    drain()
    assert runs(scope_id)[0].state == "succeeded" and stream_of(scope_id).enabled


def test_reactivating_a_kept_current_client_triggers_a_full_recheck(venue):
    scope_id, business_id = venue
    sweep()
    drain()
    for status in ("inactive", "active"):
        with transaction() as s:
            mapping.set_client_status(s, business_id, status, expected_revision=None, actor="t")
    assert sweep() == 1
    assert runs(scope_id)[-1].mode == "reconcile"
    drain()
    assert sweep() == 0  # the re-check is newer than the reactivation now


def test_only_one_worker_sweeps_and_a_disabled_scheduler_sweeps_nothing(venue, monkeypatch):
    with engine.connect() as other:
        other.execute(text("SELECT pg_advisory_lock(:k)"), {"k": sync.SWEEP_LOCK})
        try:
            assert sweep() == 0  # another worker holds the sweep
        finally:
            other.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": sync.SWEEP_LOCK})
    monkeypatch.setattr(get_settings(), "sync_scheduler_enabled", False)
    assert sweep() == 0
    with transaction() as s:  # no copy queued (creating the client queued only a portfolio rebuild)
        assert not s.execute(select(WorkItem).where(WorkItem.kind != "portfolio.refresh")).first()


def test_an_operator_stop_holds_until_an_operator_resumes(venue):
    scope_id, _ = venue
    with transaction() as s:
        run_id = sync.request_run(s, scope_id, "backfill")[0].id
    drain(pages=2)
    with transaction() as s:
        sync.operator_stop(s, run_id)
    drain()  # the queued next page is acknowledged without publishing
    stopped = runs(scope_id)[-1]
    assert (stopped.state, stopped.error_class) == ("failed", "operator_stopped")
    assert sweep() == 0  # not a mapping decision: the scheduler leaves it alone
    with transaction() as s:
        sync.resume(s, run_id)
    drain()
    assert runs(scope_id)[-1].state == "succeeded" and len(runs(scope_id)) == 1
