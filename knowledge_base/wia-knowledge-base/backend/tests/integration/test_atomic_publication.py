"""Real PostgreSQL crash/replay/lease tests for BOTH publication paths.

No provider calls. Failures are injected into real publication transactions, not
into a mock repository; assertions include accounting, continuations and state.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from threading import Barrier, Event, Thread, current_thread
from uuid import uuid4
import json
import subprocess
import sys

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.db import transaction
from backend.models.db import (Business, ConnectorAccount, ContentUnit, CoverageWindow, SourceRecord,
                               SourceScope, SourceVersion, SyncRun, SyncStream, WorkItem)
from backend.models.domain.intake import ChangeBatch, IdentityRef, NormalisedRecord, UnitIn
from backend.services.intake import execution, pipeline, positions, sync
from backend.services.shared.errors import AuthInvalidError, IntakeError, TransientError
from backend.workers import queue, runner


class Adapter:
    provider, parser_version = "slack", "atomic-test-v1"
    pages = []
    calls = []
    before_return = None

    def _batch(self, n):
        type(self).calls.append(n)
        hook = type(self).before_return
        if hook:
            hook(n)
        records, last = type(self).pages[n]
        return ChangeBatch(records, None if last else str(n + 1), last,
                           discovered=len(records), excluded=0)

    def backfill_page(self, ctx, cursor):
        return self._batch(int(cursor or 0))

    def read_page(self, ctx, checkpoint):
        n = checkpoint.get("n", 0)
        batch = self._batch(n)
        batch.checkpoint = {"done": True} if batch.terminal else {"n": n + 1}
        batch.committed_cursor = {"watermark": "test-end"}
        return batch


def rec(ext):
    author = IdentityRef("U1", "Ann")
    return NormalisedRecord("slack_message", ext, None, None, None, {"channel": "C1"},
        [UnitIn("message", "text " + ext, {"ts": ext}, author=author)], participants=[author])


@dataclass
class Trial:
    executor: str
    run_id: object
    scope_id: object
    account_id: object

    @property
    def module(self):
        return pipeline if self.executor == "legacy" else execution

    def claim(self):
        with transaction() as s:
            item = queue.claim(s, ["bulk", "sync"])
            assert item is not None
            return item.id, item.lease_token, deepcopy(item.payload)

    def execute(self, claim):
        pipeline.run_backfill_page(*claim)


@pytest.fixture(params=["legacy", "sync"])
def trial(request, monkeypatch):
    Adapter.pages, Adapter.calls, Adapter.before_return = [([rec("1"), rec("2")], False), ([rec("3")], True)], [], None
    monkeypatch.setattr(pipeline, "get_adapter", lambda _: Adapter())
    with transaction() as s:
        business = Business(id=uuid4(), name="Venue", slug="venue")
        account = ConnectorAccount(id=uuid4(), provider="slack", provider_account_id="T1",
            expected_identity="T1", credential_ref="SLACK_BOT_TOKEN")
        s.add_all([business, account])
        s.flush()
        scope = SourceScope(id=uuid4(), connector_account_id=account.id, kind="channel", external_id="C1",
            name="#venue", state="approved", default_domain="communications", association_mode="dedicated",
            business_id=business.id)
        s.add(scope)
        s.flush()
        if request.param == "legacy":
            run_id = pipeline.start_backfill(s, [scope.id], 30)[0]
        else:
            # Incremental uses the same sync publisher without adding reconciliation's verification pages.
            run_id = sync.request_run(s, scope.id, "incremental")[0].id
    return Trial(request.param, run_id, scope.id, account.id)


def state(trial):
    with transaction() as s:
        run = s.get(SyncRun, trial.run_id)
        cov = s.execute(select(CoverageWindow).where(CoverageWindow.run_id == run.id)).scalar_one()
        work = s.execute(select(WorkItem).where(WorkItem.kind == pipeline.PAGE_JOB,
            WorkItem.payload["run_id"].astext == str(run.id))).scalars().all()
        return {"run": run.state, "pages": run.pages, "counts": dict(cov.counts), "coverage": cov.state,
                "checkpoint": dict(run.checkpoint), "gaps": list(cov.gaps),
                "work": {w.id: w.state for w in work},
                "records": s.scalar(select(func.count()).select_from(SourceRecord)),
                "versions": s.scalar(select(func.count()).select_from(SourceVersion)),
                "units": s.scalar(select(func.count()).select_from(ContentUnit)),
                "last_sync": s.get(SourceScope, trial.scope_id).last_successful_sync_at}


def expire(work_id):
    with transaction() as s:
        item = s.get(WorkItem, work_id, with_for_update=True)
        item.lease_until = queue.db_now(s) - timedelta(seconds=1)


def drain():
    for _ in range(20):
        if not runner.run_one(["bulk", "sync"]):
            return
    raise AssertionError("unexpected continuation chain")


def test_crash_after_commit_needs_no_runner_success_transaction(trial):
    claim = trial.claim()
    trial.execute(claim)  # worker disappears here: no runner follow-up
    saved = state(trial)
    assert saved["work"][claim[0]] == "succeeded"
    assert saved["pages"] == 1 and saved["counts"]["discovered"] == 2
    assert list(saved["work"].values()).count("pending") == 1
    with pytest.raises(queue.LeaseLostError):
        trial.execute(claim)
    assert state(trial) == saved
    drain()
    final = state(trial)
    assert final["run"] == "succeeded" and final["pages"] == 2
    assert final["counts"]["discovered"] == 3 and len(final["work"]) == 2
    assert Adapter.calls == [0, 1]


@pytest.mark.parametrize("failure_point", ["records", "coverage", "continuation", "completion"])
def test_publication_failure_rolls_back_every_effect(trial, monkeypatch, failure_point):
    claim = trial.claim()
    before = state(trial)
    with monkeypatch.context() as m:
        if failure_point == "records":
            original = trial.module.persist_record
            def fail(*args, **kwargs):
                original(*args, **kwargs)
                raise RuntimeError("crash after records")
            m.setattr(trial.module, "persist_record", fail)
        elif failure_point == "coverage":
            def fail(s, *_):
                if any(isinstance(x, CoverageWindow) and x.counts.get("discovered", 0) for x in s.dirty):
                    raise RuntimeError("crash after coverage")
            event.listen(Session, "before_flush", fail)
        else:
            owner, name = (positions, "enqueue_page") if failure_point == "continuation" else (queue, "complete")
            original = getattr(owner, name)
            def fail(*args, **kwargs):
                original(*args, **kwargs)
                raise RuntimeError("crash before commit")
            m.setattr(owner, name, fail)
        try:
            with pytest.raises(RuntimeError, match="crash"):
                trial.execute(claim)
        finally:
            if failure_point == "coverage":
                event.remove(Session, "before_flush", fail)
    assert state(trial) == before
    expire(claim[0])
    drain()
    final = state(trial)
    assert final["run"] == "succeeded" and final["counts"]["discovered"] == 3
    assert final["pages"] == 2 and final["records"] == final["versions"] == final["units"] == 3


def test_commit_confirmation_or_cleanup_error_cannot_fail_committed_run(trial, monkeypatch):
    handler = runner.JOBS[pipeline.PAGE_JOB]
    def lost_confirmation(*args):
        handler(*args)
        raise OperationalError(None, None, Exception("lost commit response"), connection_invalidated=True)
    monkeypatch.setitem(runner.JOBS, pipeline.PAGE_JOB, lost_confirmation)
    assert runner.run_one(["bulk", "sync"])
    saved = state(trial)
    assert saved["run"] == "running" and list(saved["work"].values()).count("succeeded") == 1
    drain()
    assert state(trial)["run"] == "succeeded"


def test_old_failure_cannot_mutate_success_or_reassigned_attempt(trial):
    claim = trial.claim()
    expire(claim[0])
    replacement = trial.claim()
    assert replacement[0] == claim[0] and replacement[1] != claim[1]
    before = state(trial)
    assert runner._handle_failure(*claim[:2], pipeline.PAGE_JOB, claim[2], 0, AuthInvalidError("old")) is False
    assert state(trial) == before
    with transaction() as s:
        assert s.get(ConnectorAccount, trial.account_id).state == "active"
    trial.execute(replacement)
    before = state(trial)
    assert runner._handle_failure(*replacement[:2], pipeline.PAGE_JOB, replacement[2], 0, AuthInvalidError("late")) is False
    assert state(trial) == before


def test_expired_lease_cannot_publish_or_be_revived(trial):
    claim = trial.claim()
    expire(claim[0])
    with transaction() as s:
        assert queue.renew(s, claim[0], claim[1]) is False
    with pytest.raises(queue.LeaseLostError):
        trial.execute(claim)
    assert not Adapter.calls and state(trial)["pages"] == 0
    assert runner._handle_failure(*claim[:2], pipeline.PAGE_JOB, claim[2], 0, IntakeError("late")) is False
    drain()
    assert state(trial)["run"] == "succeeded"


def test_expiry_during_locked_publication_does_not_allow_reclaim(trial, monkeypatch):
    claim = trial.claim()
    original = trial.module.persist_record
    checked = []
    def persist(s, *args, **kwargs):
        if not checked:
            item = s.get(WorkItem, claim[0])
            item.lease_until = queue.db_now(s) - timedelta(seconds=1)
            s.flush()
            # An independent connection must skip the publication's locked row,
            # even though the visible predecessor lease has expired.
            with transaction() as other:
                assert queue.claim(other, ["bulk", "sync"]) is None
                assert queue.renew(other, claim[0], claim[1]) is None
            checked.append(True)
        return original(s, *args, **kwargs)
    monkeypatch.setattr(trial.module, "persist_record", persist)
    trial.execute(claim)
    assert checked and state(trial)["work"][claim[0]] == "succeeded"
    with transaction() as s:
        assert queue.renew(s, claim[0], claim[1]) is False


def test_expiry_during_fetch_rejects_publication(trial):
    claim = trial.claim()
    Adapter.before_return = lambda _: expire(claim[0])
    try:
        with pytest.raises(queue.LeaseLostError):
            trial.execute(claim)
    finally:
        Adapter.before_return = None
    assert state(trial)["pages"] == 0 and state(trial)["records"] == 0


def test_duplicate_work_row_is_acknowledged_without_refetch(trial):
    claim = trial.claim()
    trial.execute(claim)
    before = state(trial)
    with transaction() as s:
        queue.enqueue(s, pipeline.PAGE_JOB, "duplicates", "duplicate:" + str(uuid4()), claim[2])
    with transaction() as s:
        item = queue.claim(s, ["duplicates"])
        duplicate = item.id, item.lease_token, deepcopy(item.payload)
    trial.execute(duplicate)
    after = state(trial)
    assert after["pages"] == before["pages"] and after["counts"] == before["counts"]
    assert Adapter.calls == [0] and after["work"][duplicate[0]] == "succeeded"
    assert list(after["work"].values()).count("pending") == 1


def test_concurrent_equivalent_work_publishes_once(trial, monkeypatch):
    first = trial.claim()
    with transaction() as s:
        queue.enqueue(s, pipeline.PAGE_JOB, "duplicates", "duplicate:" + str(uuid4()), first[2])
    with transaction() as s:
        item = queue.claim(s, ["duplicates"])
        second = item.id, item.lease_token, deepcopy(item.payload)
    # Preclaim and fetch both copies before either publication can proceed. The
    # sync executor intentionally serializes the connector, so exercise its
    # publisher directly for the duplicated-delivery race.
    if trial.executor == "sync":
        with transaction() as s:
            run = s.get(SyncRun, trial.run_id)
            stream = s.get(SyncStream, run.stream_id)
            scope = s.get(SourceScope, trial.scope_id)
            ctx = execution.context(s, scope, run, stream)
            account = s.get(ConnectorAccount, trial.account_id)
            account.lease_token, account.lease_work_id = first[1], first[0]
            account.lease_until = queue.db_now(s) + timedelta(seconds=90)
        batch = Adapter().read_page(ctx, {})
        entered, contending, errors = Event(), Event(), []
        original = execution.persist_record
        def hold_publication(*args, **kwargs):
            if current_thread().name == "publisher":
                entered.set()
                assert contending.wait(timeout=5)
            return original(*args, **kwargs)
        monkeypatch.setattr(execution, "persist_record", hold_publication)
        from backend.db import engine
        def observe_contention(conn, cursor, statement, parameters, context, executemany):
            if current_thread().name == "duplicate" and "FROM sync_runs" in statement:
                contending.set()
        def publisher(claim):
            try:
                execution.publish(*claim[:2], trial.run_id, ctx, Adapter(), 0, {}, deepcopy(batch), payload=claim[2])
            except BaseException as exc:
                errors.append(exc)
        threads = [Thread(target=publisher, args=(c,), name=n)
                   for c, n in ((first, "publisher"), (second, "duplicate"))]
        event.listen(engine, "before_cursor_execute", observe_contention)
        try:
            threads[0].start()
            assert entered.wait(timeout=5)
            threads[1].start()
            for t in threads:
                t.join(timeout=10)
        finally:
            event.remove(engine, "before_cursor_execute", observe_contention)
        assert not errors and not any(t.is_alive() for t in threads)
    else:
        barrier, errors = Barrier(2), []
        Adapter.before_return = lambda _: barrier.wait(timeout=10)
        def worker(claim):
            try:
                trial.execute(claim)
            except BaseException as exc:
                errors.append(exc)
        threads = [Thread(target=worker, args=(c,)) for c in (first, second)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
        Adapter.before_return = None
        assert not errors and not any(t.is_alive() for t in threads)
    saved = state(trial)
    assert saved["pages"] == 1 and saved["counts"]["discovered"] == 2
    assert list(saved["work"].values()).count("pending") == 1


@pytest.mark.parametrize("empty", [False, True])
def test_terminal_and_empty_pages_finalize_once(trial, empty):
    Adapter.pages = [([], True)] if empty else [([rec("1")], True)]
    claim = trial.claim()
    trial.execute(claim)
    saved = state(trial)
    assert saved["run"] == "succeeded" and saved["pages"] == 1 and saved["coverage"] == "complete"
    assert saved["counts"]["discovered"] == (0 if empty else 1)
    assert saved["last_sync"] is not None and list(saved["work"].values()) == ["succeeded"]
    with transaction() as s:
        queue.enqueue(s, pipeline.PAGE_JOB, "duplicates", "terminal:" + str(uuid4()), claim[2])
    with transaction() as s:
        item = queue.claim(s, ["duplicates"])
        replay = item.id, item.lease_token, deepcopy(item.payload)
    trial.execute(replay)
    assert state(trial)["pages"] == 1 and state(trial)["last_sync"] == saved["last_sync"]
    assert Adapter.calls == [0]


def test_failure_side_effects_and_work_transition_roll_back_together(trial, monkeypatch):
    claim = trial.claim()
    original = runner.intake.on_permanent_failure
    def fail(*args):
        original(*args)
        raise RuntimeError("callback failure")
    monkeypatch.setattr(runner.intake, "on_permanent_failure", fail)
    with pytest.raises(RuntimeError, match="callback failure"):
        runner._handle_failure(*claim[:2], pipeline.PAGE_JOB, claim[2], 0, AuthInvalidError("bad credential"))
    assert state(trial)["run"] == "running" and state(trial)["work"][claim[0]] == "claimed"
    with transaction() as s:
        assert s.get(ConnectorAccount, trial.account_id).state == "active"


def test_handler_return_does_not_implicitly_mark_success(trial, monkeypatch):
    monkeypatch.setitem(runner.JOBS, pipeline.PAGE_JOB, lambda *_: None)
    assert runner.run_one(["bulk", "sync"])
    saved = state(trial)
    assert saved["run"] == "failed" and list(saved["work"].values()) == ["failed"]
    assert saved["pages"] == 0


def test_forward_checkpoint_is_an_explicit_invariant_failure(trial):
    claim = trial.claim()
    payload = deepcopy(claim[2])
    payload["checkpoint"] = {"cursor": "999"} if trial.executor == "legacy" else {"n": 999}
    payload["input_key"] = positions.input_key(trial.run_id, trial.scope_id, payload["generation"],
                                               payload["checkpoint"], trial.executor)
    with transaction() as s:
        s.get(WorkItem, claim[0]).payload = payload
    with pytest.raises(positions.PageInvariantError):
        trial.execute((claim[0], claim[1], payload))
    assert not Adapter.calls and state(trial)["counts"]["discovered"] == 0


def test_source_retirement_during_fetch_closes_run_atomically(trial):
    def retire(_):
        with transaction() as s:
            s.get(SourceScope, trial.scope_id).state = "retired"
    Adapter.before_return = retire
    trial.execute(trial.claim())
    saved = state(trial)
    assert saved["run"] == "failed" and saved["coverage"] == "failed"
    assert saved["records"] == 0 and list(saved["work"].values()) == ["succeeded"]


@pytest.mark.parametrize("code", ["40001", "40P01", "55P03", "57014", "08006"])
def test_transient_database_failure_retries_without_failing_run(trial, code):
    claim = trial.claim()
    original = type("DatabaseFailure", (Exception,), {"sqlstate": code})("database failure")
    assert runner._handle_failure(*claim[:2], pipeline.PAGE_JOB, claim[2], 0,
        OperationalError(None, None, original)) is True
    assert state(trial)["run"] == "running" and list(state(trial)["work"].values()) == ["retry_wait"]


def test_unknown_database_outcome_does_not_infer_run_failure(trial, monkeypatch):
    claim = trial.claim()
    before = state(trial)
    def unavailable(*_):
        raise OperationalError(None, None, Exception("database offline"), connection_invalidated=True)
    with monkeypatch.context() as m:
        m.setattr(queue, "assert_lease", unavailable)
        assert runner._handle_failure(*claim[:2], pipeline.PAGE_JOB, claim[2], 0, RuntimeError("unknown")) is False
    assert state(trial) == before


def test_completion_proof_cannot_be_reused_in_a_later_transaction(trial):
    claim = trial.claim()
    from backend.db import SessionFactory
    with SessionFactory() as s:
        with s.begin():
            queue.assert_lease(s, claim[0], claim[1])
        with s.begin():
            s.get(WorkItem, claim[0]).lease_until = queue.db_now(s) - timedelta(seconds=1)
        with pytest.raises(queue.LeaseLostError), s.begin():
            queue.complete(s, claim[0], claim[1])


def test_rolled_back_savepoint_cannot_keep_publication_ownership(trial):
    claim = trial.claim()
    from backend.db import SessionFactory
    with SessionFactory.begin() as s:
        nested = s.begin_nested()
        queue.assert_lease(s, claim[0], claim[1])
        nested.rollback()  # PostgreSQL releases the lock acquired in this savepoint.
        expire(claim[0])
        with pytest.raises(queue.LeaseLostError):
            queue.complete(s, claim[0], claim[1])


@pytest.mark.parametrize("boundary", ["before", "after"])
def test_actual_worker_process_death_at_commit_boundary(trial, boundary):
    claim = trial.claim()
    code = '''
import json, os, sys
from uuid import UUID
from sqlalchemy import event
from sqlalchemy.orm import Session
from backend.tests.integration.test_atomic_publication import Adapter, rec
from backend.services.intake import pipeline
from backend.workers import queue
data = json.load(sys.stdin)
Adapter.pages = [([rec("1"), rec("2")], False), ([rec("3")], True)]
pipeline.get_adapter = lambda _: Adapter()
real_complete = queue.complete
completed = False
def complete(*args):
    global completed
    real_complete(*args)
    completed = True
queue.complete = complete
def crash(session):
    if completed:
        os._exit(23)
event.listen(Session, data["boundary"] + "_commit", crash)
pipeline.run_backfill_page(UUID(data["id"]), UUID(data["token"]), data["payload"])
raise RuntimeError("commit crash hook was not reached")
'''
    result = subprocess.run([sys.executable, "-c", code], input=json.dumps({
        "id": str(claim[0]), "token": str(claim[1]), "payload": claim[2], "boundary": boundary}),
        text=True, capture_output=True, timeout=25)
    assert result.returncode == 23, result.stderr
    saved = state(trial)
    if boundary == "before":
        assert saved["pages"] == 0 and saved["records"] == 0
        assert saved["work"][claim[0]] == "claimed" and len(saved["work"]) == 1
        expire(claim[0])
    else:
        assert saved["pages"] == 1 and saved["records"] == 2
        assert saved["work"][claim[0]] == "succeeded" and len(saved["work"]) == 2
    drain()
    final = state(trial)
    assert final["run"] == "succeeded" and final["pages"] == 2 and len(final["work"]) == 2
    assert final["counts"]["discovered"] == 3 and final["counts"]["unchanged"] == 0


def test_crash_recovery_matches_uninterrupted_reference_run(trial, monkeypatch):
    trial.execute(trial.claim())
    second = trial.claim()
    with monkeypatch.context() as m:
        original = queue.complete
        def crash(*args):
            original(*args)
            raise RuntimeError("worker died")
        m.setattr(queue, "complete", crash)
        with pytest.raises(RuntimeError):
            trial.execute(second)
    expire(second[0])
    drain()
    recovered = state(trial)
    with transaction() as s:
        original_scope = s.get(SourceScope, trial.scope_id)
        account = ConnectorAccount(id=uuid4(), provider="slack", provider_account_id="T2",
            expected_identity="T2", credential_ref="SLACK_BOT_TOKEN")
        s.add(account)
        s.flush()
        scope = SourceScope(id=uuid4(), connector_account_id=account.id, kind="channel", external_id="C1",
            name="#reference", state="approved", default_domain="communications", association_mode="dedicated",
            business_id=original_scope.business_id)
        s.add(scope)
        s.flush()
        rid = (pipeline.start_backfill(s, [scope.id], 30)[0] if trial.executor == "legacy"
               else sync.request_run(s, scope.id, "incremental")[0].id)
    reference = Trial(trial.executor, rid, scope.id, account.id)
    drain()
    uninterrupted = state(reference)
    assert recovered["counts"] == uninterrupted["counts"]
    assert recovered["pages"] == uninterrupted["pages"] == 2
    assert recovered["coverage"] == uninterrupted["coverage"] == "complete"


def test_terminal_failure_updates_run_work_and_connector_together(trial):
    claim = trial.claim()
    assert runner._handle_failure(*claim[:2], pipeline.PAGE_JOB, claim[2], 0, AuthInvalidError("invalid")) is True
    saved = state(trial)
    assert saved["run"] == "failed" and saved["coverage"] == "failed"
    assert saved["work"][claim[0]] == "blocked"
    with transaction() as s:
        assert s.get(ConnectorAccount, trial.account_id).state == "blocked"


def test_legacy_page_payload_is_rejected_before_fetch(trial):
    claim = trial.claim()
    old = {"scope_id": str(trial.scope_id), "run_id": str(trial.run_id), "cursor": None}
    with transaction() as s:
        s.get(WorkItem, claim[0]).payload = old
    with pytest.raises(positions.PageInvariantError, match="legacy"):
        trial.execute((claim[0], claim[1], old))
    assert not Adapter.calls


def test_late_failure_from_obsolete_duplicate_cannot_fail_run_or_block_account(trial):
    first = trial.claim()
    with transaction() as s:
        queue.enqueue(s, pipeline.PAGE_JOB, "duplicates", "duplicate:" + str(uuid4()), first[2])
    with transaction() as s:
        item = queue.claim(s, ["duplicates"])
        duplicate = item.id, item.lease_token, deepcopy(item.payload)
    trial.execute(first)
    saved = state(trial)
    assert runner._handle_failure(*duplicate[:2], pipeline.PAGE_JOB, duplicate[2], 0,
                                 AuthInvalidError("late duplicate result")) is False
    after = state(trial)
    assert after["run"] == "running" and after["pages"] == saved["pages"]
    assert after["counts"] == saved["counts"] and after["work"][duplicate[0]] == "succeeded"
    with transaction() as s:
        assert s.get(ConnectorAccount, trial.account_id).state == "active"


def test_empty_nonterminal_page_advances_without_fake_records(trial):
    Adapter.pages = [([], False), ([rec("1")], True)]
    drain()
    saved = state(trial)
    assert saved["pages"] == 2 and saved["counts"]["discovered"] == 1
    assert saved["records"] == 1 and saved["run"] == "succeeded"


def test_heartbeat_database_error_is_contained(monkeypatch):
    beat = runner.Heartbeat(uuid4(), uuid4())
    class Immediate:
        def wait(self, interval):
            return False
    beat.stop = Immediate()
    calls = []
    def renew(*_):
        calls.append(True)
        if len(calls) == 1:
            raise OperationalError(None, None, Exception("database temporarily offline"))
        return False
    monkeypatch.setattr(queue, "renew", renew)
    beat.run()
    assert len(calls) == 2


def test_malformed_job_run_id_fails_work_without_failing_unrelated_run(trial):
    with transaction() as s:
        item = s.execute(select(WorkItem).where(WorkItem.kind == pipeline.PAGE_JOB)).scalar_one()
        payload = dict(item.payload)
        payload["run_id"] = "invalid-run-id"
        item.payload = payload
    assert runner.run_one(["bulk", "sync"])
    with transaction() as s:
        assert s.get(SyncRun, trial.run_id).state == "running"
        assert s.execute(select(WorkItem.state).where(WorkItem.kind == pipeline.PAGE_JOB)).scalar_one() == "failed"
    assert not Adapter.calls
