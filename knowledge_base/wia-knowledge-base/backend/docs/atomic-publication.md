# Atomic page publication (B-02)

## Contract

An intake handler owns its success transition. Records, evidence, coverage,
the run checkpoint, downstream work, finalization, and `work_items.succeeded`
commit in one PostgreSQL transaction. The runner never adds a success transaction.
The registered pipeline and the sync executor use the same queue/position helpers.

Provider fetching remains outside a transaction. A crash before publication can
repeat provider requests; it cannot publish the page's effects twice.

## Ownership and identity

- Claim and heartbeat deadlines use PostgreSQL's actual clock.
- `assert_lease` locks the job and checks state, token, and deadline after waiting.
- `complete` uses ownership proved in that same transaction. Expiry after acquiring
  the publication lock is safe: competing claims skip the locked row.
- A heartbeat cannot revive an expired lease. A heartbeat encountering publication's
  lock retries later; heartbeat database errors do not fail the business run.
- Every page carries a hash of run, scope, generation, executor, and input checkpoint.
  Pre-fetch and pre-publication checks reject contradictory positions and acknowledge
  already-published duplicates without adding counts or another continuation.
- `run.pages` is reporting state. It does not identify a page or authorize replay.
- Lock order starts with work item, then run, then dependent publication rows.

On an exception, the runner reacquires and validates the work claim before changing
retry state, failing a run, or blocking a connector. Those effects commit together.
If success already committed, failure handling does nothing. If the database is
unavailable, persisted state and lease recovery decide the outcome later.

## Tests

Run from the repository root, against a dedicated database named `kb_test`:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://kb:kb@127.0.0.1:5440/kb_test'
python -m pytest backend/tests -q
```

Tests include real PostgreSQL transactions, independent connections, concurrent
duplicate delivery, and worker subprocesses terminated at the actual before/after
commit boundaries. No provider API or production database is contacted.

## Deployment cutover

1. Stop old workers from claiming work and let live transactions finish. Do not run
   old and new page-job formats concurrently.
2. Apply and validate the additive migration; run the full integration suite.
3. Inventory pre-fix jobs and affected runs. This read-only query finds legacy work:

```sql
SELECT payload->>'run_id' AS run_id, state, count(*)
FROM work_items
WHERE kind = 'intake.backfill_page' AND NOT (payload ? 'input_key')
GROUP BY payload->>'run_id', state;
```

4. Preserve affected runs and coverage for audit. Cancel all outstanding jobs for
   each retired run, mark its run/coverage failed with a pre-fix-reconciliation
   reason, and start a fresh backfill/reconciliation. Retire the whole run, including
   any forked continuations; do not convert individual legacy cursors in place.
5. Do not subtract guessed duplicate counts from old coverage or use those numbers
   for sign-off. Use the new run's coverage report.
6. Start new workers. Enable scheduled streams only after provider-specific
   validation. B-02 does not finish or enable the remaining B-05 synchronization work.

Legacy jobs are rejected before fetching. Automatic production scheduling remains
disabled by default. This change does not deploy to Railway or start a production
backfill.
