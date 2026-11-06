"""Fenced page execution; all publication and job completion share one transaction."""
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import (ConnectorAccount, Contact, CoverageWindow, DriveNode, ScopeMembership,
    SourceRecord, SourceScope, SyncCursor, SyncRun, SyncStream)
from backend.models.db.base import utcnow
from backend.services.read_models import portfolio
from backend.models.domain.intake import ApprovedContact, ChangeBatch, Gap, IntakeContext
from backend.services.intake.adapters import get_adapter
from backend.services.intake.admission import lookup
from backend.services.intake.persist import IdentityCache, PersistOutcome, persist_record
from backend.services.intake.sync import INCREMENTAL_SECONDS, PAGE_JOB, sync_interval
from backend.services.intake import positions
from backend.services.intake.scoping import is_live, live_contacts, live_scope
from backend.services.shared.errors import AuthInvalidError, CursorExpiredError, NotFoundError, ThrottledError
from backend.workers import queue


def context(s, scope, run, stream):
    from backend.services.people.roster import internal_addresses
    contacts = live_contacts(s)
    aid = scope.connector_account_id
    return IntakeContext(run.window_start, run.window_end, scope.external_id, scope.kind,
        [ApprovedContact(c.business_id, c.email, c.domain) for c in contacts], settings=get_settings(),
        connector_account_id=aid, scope_id=scope.id, association_mode=scope.association_mode,
        business_id=scope.business_id, lookup_records=lambda keys: lookup(aid, keys),
        mode=run.mode, target_external_id=run.target_external_id, stream_cursor=dict(stream.cursor),
        internal_emails=frozenset(internal_addresses(s)) if scope.kind == "recorder" else frozenset())  # Fathom only


def verification_page(adapter, ctx, run_id, state):
    from backend.services.intake.adapters.readers import unavailable
    with transaction() as s:
        q = select(SourceRecord).join(ScopeMembership, ScopeMembership.record_id == SourceRecord.id).where(
            SourceRecord.connector_account_id == ctx.connector_account_id, SourceRecord.admitted_at.is_not(None),
            (ScopeMembership.seen_run_id.is_(None) | (ScopeMembership.seen_run_id != run_id)))
        if adapter.provider != "drive":
            q = q.where(ScopeMembership.scope_id == ctx.scope_id)
        if state.get("after"):
            q = q.where(SourceRecord.id > UUID(state["after"]))
        targets = [(r.id, r.external_id) for r in s.execute(q.order_by(SourceRecord.id).limit(10)).scalars().unique()]
    batch = ChangeBatch([], None, not targets, checkpoint=dict(state), committed_cursor=state.get("commit"))
    for rid, ext in targets:
        if adapter.provider in ("fathom", "calendar"):
            # Full unfiltered enumeration established visibility, not deletion.
            kind = "fathom_recording" if adapter.provider == "fathom" else "calendar_event"
            batch.records.append(unavailable(kind, ext))
            batch.gaps.append(Gap(ext, "not_found"))
        else:
            part = adapter.read_page(replace(ctx, mode="refresh", target_external_id=ext), {})
            batch.records.extend(part.records)
            batch.gaps.extend(part.gaps)
            batch.memberships.extend(part.memberships)
        batch.checkpoint["after"] = str(rid)
    batch.discovered = len(targets)
    if not targets:
        batch.checkpoint = {"completed": True}
    return batch


def run_page(work_id, token, payload, adapter_factory=None):
    run_id, scope_id = UUID(payload["run_id"]), UUID(payload["scope_id"])
    with transaction() as s:
        item = queue.assert_lease(s, work_id, token)
        run = s.get(SyncRun, run_id, with_for_update=True)
        if not positions.validate(s, item, run, payload, "sync"):
            return
        scope = s.get(SourceScope, scope_id)
        stream = s.get(SyncStream, run.stream_id, with_for_update=True)
        account = s.get(ConnectorAccount, scope.connector_account_id, with_for_update=True)
        if not is_live(s, scope):
            stop(s, run, "scope_retired" if scope.state != "approved" else "client_archived")
            queue.complete(s, work_id, token)
            return
        if account.state != "active":
            raise AuthInvalidError("connector account inactive")
        if run.state == "queued":
            other = s.execute(select(SyncRun.id).where(SyncRun.stream_id == stream.id,
                SyncRun.state == "running", SyncRun.id != run.id)).first()
            if other:
                raise ThrottledError("stream busy", retry_after=5)
            run.state = "running"
        if run.generation != stream.generation:
            stop(s, run, "generation_superseded")
            queue.complete(s, work_id, token)
            return
        now = queue.db_now(s)
        if account.lease_until and account.lease_until > now and account.lease_work_id != work_id:
            raise ThrottledError("connector busy", retry_after=2)
        account.lease_token, account.lease_work_id = token, work_id
        account.lease_until = now + timedelta(seconds=get_settings().lease_seconds)
        ctx = context(s, scope, run, stream)
        provider, checkpoint, page = account.provider, dict(run.checkpoint), run.pages
        expected_identity = account.expected_identity
    adapter = None
    try:
        adapter = (adapter_factory or get_adapter)(provider)
        if hasattr(adapter, "identify"):
            identity = adapter.identify()
            if identity.expected_identity_value != expected_identity:
                # Only the runner's ownership-fenced failure transaction may
                # block an account; this HTTP result can arrive after lease loss.
                raise AuthInvalidError("connector identity mismatch")
        try:
            if checkpoint.get("verify"):
                batch = verification_page(adapter, ctx, run_id, checkpoint)
            elif hasattr(adapter, "read_page"):
                batch = adapter.read_page(ctx, checkpoint)
            else:
                batch = adapter.backfill_page(ctx, checkpoint.get("legacy_cursor"))
                batch.checkpoint = {"legacy_cursor": batch.next_cursor}
        except (CursorExpiredError, NotFoundError):
            if provider not in ("calendar", "gmail") or ctx.mode == "refresh":
                raise
            with transaction() as s:
                item = queue.assert_lease(s, work_id, token)
                r = s.get(SyncRun, run_id, with_for_update=True)
                if not positions.validate(s, item, r, payload, "sync"):
                    return
                stream = s.get(SyncStream, r.stream_id, with_for_update=True)
                stream.generation += 1
                r.generation, r.checkpoint, r.mode = stream.generation, {}, "reconcile"
                stream.cursor = {}
                r.pages += 1
                enqueue_next(s, r)
                queue.complete(s, work_id, token)
            return
        publish(work_id, token, run_id, ctx, adapter, page, checkpoint, batch, payload=payload)
    finally:
        if adapter and hasattr(adapter, "http"):
            adapter.http.close()
        with transaction() as s:
            account = s.get(ConnectorAccount, ctx.connector_account_id, with_for_update=True)
            if account.lease_token == token:
                account.lease_token = account.lease_work_id = account.lease_until = None


def publish(work_id, token, run_id, ctx, adapter, page, checkpoint, batch, *, payload=None):
    with transaction() as s:
        item = queue.assert_lease(s, work_id, token)
        run = s.get(SyncRun, run_id, with_for_update=True)
        if not positions.validate(s, item, run, payload if payload is not None else item.payload, "sync"):
            return
        stream = s.get(SyncStream, run.stream_id, with_for_update=True)
        account = s.get(ConnectorAccount, ctx.connector_account_id, with_for_update=True)
        scope = s.get(SourceScope, ctx.scope_id, with_for_update=True)
        if account.lease_token != token or run.generation != stream.generation:
            raise queue.LeaseLostError(str(work_id))
        if not is_live(s, scope) or account.state != "active":
            stop(s, run, "client_archived" if scope.state == "approved" and account.state == "active"
                 else "approval_revoked")
            queue.complete(s, work_id, token)
            return
        coverage = s.execute(select(CoverageWindow).where(CoverageWindow.run_id == run_id).with_for_update()).scalar_one()
        outcome, identities = PersistOutcome(), IdentityCache(s, account.id)
        membership_map = {(m["kind"], m["external_id"]): m for m in batch.memberships}
        store_nodes(s, account.id, batch.memberships)
        for rec in batch.records:
            target_scope, approved_ids = scope, [scope.id]
            membership = membership_map.get((rec.record_kind, rec.external_id))
            if membership:
                listed = [UUID(x) for x in membership["scope_ids"]]
                approved_ids = list(s.execute(select(SourceScope.id).where(
                    SourceScope.id.in_(listed), SourceScope.connector_account_id == account.id,
                    live_scope())).scalars())
                if listed and not approved_ids and s.execute(select(SourceScope.id).where(
                        SourceScope.id.in_(listed), SourceScope.state == "approved")).first():
                    continue  # only archived clients' scopes: paused, not revoked
                if listed and not approved_ids:
                    coverage.gaps = coverage.gaps + [{"external_id": rec.external_id, "reason": "approval_revoked"}]
                    continue
                if approved_ids:
                    target_scope = s.get(SourceScope, approved_ids[0])
            record = persist_record(s, target_scope, ctx, rec, identities, adapter.parser_version, outcome)
            membership_update(s, record, approved_ids, run.id, membership is not None)
        counts = dict(coverage.counts)
        values = {k: getattr(outcome, k) for k in ("stored_content", "stored_metadata", "unchanged",
            "stale_observations", "known_without_contact", "cancellations", "association_conflicts")}
        values.update(discovered=batch.discovered, excluded=batch.excluded)
        for key, value in values.items():
            counts[key] = counts.get(key, 0) + value
        for gap in batch.gaps:
            key = "inaccessible" if gap.reason in ("scope_denied", "not_found") else "failed"
            counts[key] = counts.get(key, 0) + 1
        coverage.counts = counts
        coverage.gaps = coverage.gaps + [{"external_id": g.external_id, "reason": g.reason} for g in batch.gaps]
        run.checkpoint = batch.checkpoint
        # shortcut: LeadLock skips the deletion check; a phase refused by its plan would read as deleted records.
        # Add a verify that ignores gapped phases if deleted leads must leave the counts.
        if (batch.terminal and run.mode in ("backfill", "reconcile") and hasattr(adapter, "read_page")
                and not checkpoint.get("verify") and account.provider != "leadlock"):
            run.checkpoint = {"verify": True, "commit": batch.committed_cursor, "after": None}
            batch.terminal = False
        run.pages += 1
        row = s.execute(select(SyncCursor).where(SyncCursor.scope_id == scope.id, SyncCursor.mode == run.mode)).scalar_one_or_none()
        if row is None:
            s.add(SyncCursor(id=uuid4(), scope_id=scope.id, mode=run.mode, cursor=batch.next_cursor))
        else:
            row.cursor, row.generation = batch.next_cursor, row.generation + 1
        if batch.terminal:
            run.checkpoint = {**run.checkpoint, "completed": True}
            if counts.get("stored_content", 0) + counts.get("stored_metadata", 0) + counts.get("cancellations", 0):
                portfolio.request_refresh(s)
            complete = not coverage.gaps and counts.get("failed", 0) == 0
            coverage.state = "complete" if complete else "partial"
            run.state, run.finished_at = ("succeeded" if complete else "partial"), utcnow()
            # Gaps stay recorded on this run and are retried by the next full re-check. Holding the cursor or
            # the schedule back on them would re-run a source with a permanent gap on every sweep.
            if run.mode != "refresh":
                if batch.committed_cursor is not None:
                    stream.cursor = batch.committed_cursor
                if run.mode in ("reconcile", "backfill"):
                    stream.enabled = True  # its first full copy is done: from now on the scheduler keeps it current
                    stream.last_reconciled_at = run.finished_at
                    stream.next_reconcile_at = run.finished_at + timedelta(seconds=get_settings().reconcile_interval_seconds)
                else:
                    stream.last_incremental_at = run.finished_at
                # After a full copy, sources with a change feed catch up at once on what changed during the copy;
                # a source that re-reads everything every run (LeadLock) just waits its normal interval.
                catch_up = run.mode != "incremental" and account.provider not in INCREMENTAL_SECONDS
                stream.next_sync_at = utcnow() + timedelta(seconds=0 if catch_up else sync_interval(account.provider))
                if complete:
                    scope.last_successful_sync_at = run.window_end
        else:
            if run.checkpoint == checkpoint:
                raise positions.PageInvariantError("nonterminal page did not advance its checkpoint")
            enqueue_next(s, run)
        queue.complete(s, work_id, token)
        account.lease_token = account.lease_work_id = account.lease_until = None


def store_nodes(s, account_id, memberships):
    for m in memberships:
        if "node" in m:
            stmt = insert(DriveNode).values(id=uuid4(), connector_account_id=account_id,
                external_id=m["external_id"], **m["node"])
            s.execute(stmt.on_conflict_do_update(index_elements=["connector_account_id", "external_id"], set_=m["node"]))


def membership_update(s, record, scope_ids, run_id, authoritative):
    old = s.execute(select(ScopeMembership).where(ScopeMembership.record_id == record.id)).scalars().all()
    if authoritative:
        for m in old:
            if m.scope_id not in scope_ids:
                m.state = "out_of_scope"
    for sid in scope_ids:
        values = {"state": "active" if record.availability == "available" else record.availability, "seen_run_id": run_id}
        stmt = insert(ScopeMembership).values(id=uuid4(), record_id=record.id, scope_id=sid, **values)
        s.execute(stmt.on_conflict_do_update(index_elements=["record_id", "scope_id"], set_=values))


def enqueue_next(s, run):
    positions.enqueue_page(s, run, "sync", "bulk" if run.mode in ("backfill", "reconcile") else "sync")


def stop(s, run, error):
    run.state, run.error_class, run.finished_at = "failed", error, utcnow()
    c = s.execute(select(CoverageWindow).where(CoverageWindow.run_id == run.id)).scalar_one()
    c.state = "failed"
