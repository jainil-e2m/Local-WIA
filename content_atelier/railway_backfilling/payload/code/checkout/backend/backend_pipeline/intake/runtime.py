"""SQL-owned intake work dispatched through RQ. No editorial generation calls."""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta, time
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from psycopg.types.json import Jsonb

from ..config import Settings
from ..storage_config import StorageSettings
from .. import chunk_encoding
from ..store import canonical_hash
from .config import IntakeSettings
from .repository import IntakeRepository
from .fathom import FathomClient, PendingTranscript, collect

log = logging.getLogger(__name__)


def repository():
    storage = StorageSettings.from_env()
    return IntakeRepository(storage, IntakeSettings.from_env())


def last_saturday(now):
    local = now.astimezone(ZoneInfo('America/Chicago'))
    day = local.date() - timedelta(days=(local.weekday() - 5) % 7)
    candidate = datetime.combine(day, time(4), ZoneInfo('America/Chicago'))
    if candidate > local:
        candidate -= timedelta(days=7)
    return candidate.astimezone(UTC)


def reconcile(repo, redis_connection=None):
    from redis import Redis
    from rq import Queue
    from rq.job import Job
    from rq.exceptions import NoSuchJobError
    from rq.serializers import JSONSerializer
    redis_connection = redis_connection or Redis.from_url(repo.intake.redis_url)
    with repo.connection() as conn:
        # A lost embedding response needs artifact inspection / explicit retry.
        # Read-only discovery and local extraction can be safely redelivered.
        expired = conn.execute("""UPDATE pipeline_jobs SET
            status=CASE WHEN stage='transcript_chunk_embedding' OR attempt_count>=3 THEN 'failed' ELSE 'queued' END,
            error_summary='Intake worker lease expired; embedding retries require review',
            lease_token=NULL,lease_expires_at=NULL,updated_at=now()
            WHERE executor='rq' AND status='running' AND lease_expires_at<now() RETURNING *""").fetchall()
        for job in expired:
            conn.execute('UPDATE pipeline_runs SET status=%s,error_summary=%s,updated_at=now() WHERE run_id=%s',
                         ('failed' if job['status'] == 'failed' else 'queued', job['error_summary'], job['run_id']))
            if job['status'] == 'failed' and job['stage'] == 'transcript_chunk_embedding':
                conn.execute("""UPDATE intake_revisions SET indexing_status='failed',error_summary=%s
                    WHERE revision_id=(SELECT input_refs->>'revision_id' FROM pipeline_runs WHERE run_id=%s)""",
                             (job['error_summary'], job['run_id']))
        conn.execute("""UPDATE pipeline_jobs SET status='queued',updated_at=now() WHERE executor='rq'
            AND stage='intake_fathom' AND status='waiting' AND
            COALESCE((progress_details->>'retry_at')::timestamptz,updated_at+interval '10 minutes')<=now()""")
        jobs = conn.execute("SELECT job_id,stage,attempt_count FROM pipeline_jobs WHERE executor='rq' AND status='queued' ORDER BY created_at").fetchall()
    for job in jobs:
        # New transport ID for each SQL attempt; SQL remains the duplicate guard.
        transport_id = f'{job["job_id"]}-{job["attempt_count"]}'
        try:
            existing = Job.fetch(transport_id, connection=redis_connection, serializer=JSONSerializer)
            if existing.get_status(refresh=True) in {'queued', 'started', 'deferred', 'scheduled'}:
                continue
            existing.delete()
        except NoSuchJobError:
            pass
        queue = Queue('atelier-media' if job['stage'] == 'intake_extract' else 'atelier-intake',
                      connection=redis_connection, serializer=JSONSerializer)
        queue.enqueue('backend_pipeline.intake.runtime.execute', job['job_id'],
                      job_id=transport_id, job_timeout=1800, result_ttl=3600, failure_ttl=86400)


def tick(repo, *, now=None):
    now = now or datetime.now(UTC)
    with repo.connection() as conn:
        opened = conn.execute("SELECT * FROM intake_buckets WHERE status='open'").fetchone()
        collecting = conn.execute("SELECT 1 FROM intake_buckets WHERE status='collecting'").fetchone()
        last = conn.execute('SELECT max(created_at) t FROM intake_requests').fetchone()['t']
    if not opened:
        return
    scheduled = last_saturday(now)
    if not collecting and scheduled > opened['starts_at']:
        repo.request_collection(cutoff=scheduled, complete=True)
    elif not last or last <= now - timedelta(hours=1):
        repo.request_collection(cutoff=now)
    repo.finalize()


def encode(repo, job, models):
    # Reuse the existing exact-text/cache/response receipt implementation.
    with repo.connection() as conn:
        run = conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s', (job['run_id'],)).fetchone()
        revision_id = run['input_refs']['revision_id']
        rev = conn.execute('SELECT * FROM intake_revisions WHERE revision_id=%s', (revision_id,)).fetchone()
        source = conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s', (rev['transcript_id'],)).fetchone()
        rows = conn.execute('SELECT * FROM transcript_chunks WHERE transcript_id=%s ORDER BY chunk_id', (rev['transcript_id'],)).fetchall()
        refs = run['input_refs']
        if 'contract' not in refs:
            refs = {**refs, 'contract': chunk_encoding.contract(models, synthetic=repo.settings.synthetic),
                    'encoding_mode': 'live' if repo.intake.encoding_enabled else 'cached',
                    'transcripts': [{'id': source['transcript_id'], 'hash': source['content_hash'],
                        'view_hash': canonical_hash([source['original_text'], source['passage_map'], source['source_metadata']])}],
                    'chunks': [chunk_encoding.chunk_view(row) for row in rows]}
            conn.execute('UPDATE pipeline_runs SET input_refs=%s WHERE run_id=%s', (Jsonb(refs), job['run_id']))
        elif repo.intake.encoding_enabled and refs['encoding_mode'] == 'cached':
            refs['encoding_mode'] = 'live'
            conn.execute('UPDATE pipeline_runs SET input_refs=%s WHERE run_id=%s', (Jsonb(refs), job['run_id']))
        run['input_refs'] = refs
        conn.execute("UPDATE intake_revisions SET indexing_status='processing',error_summary=NULL WHERE revision_id=%s", (revision_id,))
    storage = repo.settings.model_copy(update={'encoding_enabled': repo.intake.encoding_enabled})

    def check_sources(conn, frozen):
        for ref in frozen['input_refs']['transcripts']:
            current = conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s', (ref['id'],)).fetchone()
            if not current or canonical_hash([current['original_text'], current['passage_map'], current['source_metadata']]) != ref['view_hash']:
                raise ValueError('Frozen intake source changed')

    worker = SimpleNamespace(repo=repo, models=models, storage=storage, provider=None, check_source_views=check_sources)
    # Serialize cache discovery/dispatch across intake workers too: two distinct
    # revisions with identical chunk text must not both purchase the same vector.
    with repo.connection() as encoding_lock:
        encoding_lock.execute('SELECT pg_advisory_lock(74091215)')
        try:
            chunk_encoding.execute(worker, job, run)
        finally:
            encoding_lock.execute('SELECT pg_advisory_unlock(74091215)')


def execute(job_id, *, repo=None, models=None):
    repo = repo or repository()
    models = models or Settings.from_env()
    # A session advisory lock outlives stage transactions and prevents parallel execution.
    with repo.connection() as session:
        if not session.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0)) acquired', (job_id,)).fetchone()['acquired']:
            return
        try:
            with repo.connection() as conn:
                job = conn.execute("SELECT * FROM pipeline_jobs WHERE job_id=%s AND executor='rq' FOR UPDATE", (job_id,)).fetchone()
                if not job or job['status'] != 'queued':
                    return
                job = conn.execute("""UPDATE pipeline_jobs SET status='running',attempt_count=attempt_count+1,
                    lease_token=%s,lease_expires_at=now()+interval '120 seconds',heartbeat_at=now(),
                    started_at=COALESCE(started_at,now()),updated_at=now() WHERE job_id=%s RETURNING *""", (uuid4().hex, job_id)).fetchone()
                run = conn.execute("UPDATE pipeline_runs SET status='running',started_at=COALESCE(started_at,now()),updated_at=now() WHERE run_id=%s RETURNING *", (job['run_id'],)).fetchone()
                repo.event(conn, job['run_id'], 'intake_started', job['stage'], job=job)
            stopped = threading.Event()

            def heartbeat():
                while not stopped.wait(20):
                    try:
                        if not repo.heartbeat(job):
                            return
                    except Exception:
                        log.exception('Intake heartbeat failed')

            thread = threading.Thread(target=heartbeat, daemon=True)
            thread.start()
            try:
                payload = run['input_refs']
                if job['stage'] == 'intake_slack':
                    repo.process_slack(payload['batch_id'])
                elif job['stage'] == 'intake_fathom':
                    client = FathomClient(repo.intake)
                    try:
                        collect(repo, payload['request_id'], client)
                    finally:
                        client.close()
                elif job['stage'] == 'intake_extract':
                    from .extract import process
                    process(repo, payload['asset_id'])
                elif job['stage'] == 'transcript_chunk_embedding':
                    encode(repo, job, models)
                else:
                    raise ValueError('Unknown intake stage')
                if job['stage'] != 'transcript_chunk_embedding':
                    with repo.connection() as conn:
                        repo.finish(conn, job, {'status': 'completed'}, message='Intake stage completed')
            except Exception as exc:
                readonly_retry = isinstance(exc, (PendingTranscript, httpx.TransportError)) or (
                    isinstance(exc, httpx.HTTPStatusError) and (exc.response.status_code == 429 or exc.response.status_code >= 500))
                waiting = job['stage'] == 'intake_fathom' and readonly_retry
                # Only controlled messages, never response bodies/keys, go into UI errors.
                error = ('Fathom HTTP ' + str(exc.response.status_code)) if isinstance(exc, httpx.HTTPStatusError) else str(exc)[:1000]
                with repo.connection() as conn:
                    repo.guard(conn, job)
                    conn.execute("UPDATE pipeline_jobs SET status=%s,error_summary=%s,lease_token=NULL,lease_expires_at=NULL,updated_at=now() WHERE job_id=%s",
                                 ('waiting' if waiting else 'failed', error, job_id))
                    conn.execute("UPDATE pipeline_runs SET status=%s,error_summary=%s,updated_at=now() WHERE run_id=%s",
                                 ('partially_completed' if waiting else 'failed', error, job['run_id']))
                    if job['stage'] == 'transcript_chunk_embedding':
                        conn.execute("UPDATE intake_revisions SET indexing_status='failed',error_summary=%s WHERE revision_id=%s", (error, payload['revision_id']))
                    if job['stage'] == 'intake_extract':
                        conn.execute("UPDATE intake_assets SET status='failed',metadata=metadata || %s WHERE asset_id=%s", (Jsonb({'error': error}), payload['asset_id']))
                    if job['stage'] == 'intake_fathom':
                        delay = min(3600, 60 * 2 ** min(job['attempt_count'], 6))
                        if isinstance(exc, httpx.HTTPStatusError):
                            retry_after = exc.response.headers.get('retry-after', '')
                            if retry_after.isdigit():
                                delay = max(delay, min(int(retry_after), 86400))
                        conn.execute('UPDATE pipeline_jobs SET progress_details=progress_details || %s WHERE job_id=%s',
                                     (Jsonb({'retry_at': (datetime.now(UTC) + timedelta(seconds=delay)).isoformat()}), job_id))
                        conn.execute("UPDATE intake_connections SET health=%s,error_summary=%s,updated_at=now() WHERE connection_id='fathom'",
                                     ('pending' if waiting else 'error', error))
                    repo.event(conn, job['run_id'], 'intake_waiting' if waiting else 'intake_failed', error, job=job, severity='warning' if waiting else 'error')
            finally:
                stopped.set()
                thread.join(timeout=2)
            repo.finalize()
        finally:
            session.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))', (job_id,))


def main():
    import argparse
    import time as clock
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['scheduler', 'worker', 'media-worker', 'migrate'])
    args = parser.parse_args()
    if args.command == 'migrate':
        from ..database import initialize, apply_intake, apply_brief_indexes
        url = StorageSettings.from_env().database_url
        initialize(url)
        apply_brief_indexes(url)
        print(apply_intake(url))
    elif args.command == 'scheduler':
        while True:
            try:
                repo = repository()
                tick(repo)
                reconcile(repo)
            except Exception:
                log.exception('Intake scheduler iteration failed; retrying')
            clock.sleep(30)
    else:
        from redis import Redis
        from rq import Queue, Worker
        from rq.serializers import JSONSerializer
        config = IntakeSettings.from_env()
        connection = Redis.from_url(config.redis_url)
        queue = Queue('atelier-media' if args.command == 'media-worker' else 'atelier-intake', connection=connection, serializer=JSONSerializer)
        Worker([queue], connection=connection, serializer=JSONSerializer).work()


if __name__ == '__main__':
    main()
