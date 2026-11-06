from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from psycopg.types.json import Jsonb

from ..gates.roles import access_for
from ..jobs.policy import placement
from ..repository import ContentRepository, identifier, insert
from ..settings_store import cycle_schedule_text
from ..store import canonical_hash
from ..artifacts import store_for
from ..documents.intake import queue_normalisation
from ..normalise import NORMALISER_VERSION
from .contracts import SlackBatch, slack_time
from .normalize import slack


def lock(conn):
    # Registry changes and bucket transitions share one short transaction lock.
    conn.execute('SELECT pg_advisory_xact_lock(74091214)')


class IntakeRepository(ContentRepository):
    def __init__(self, storage, intake):
        # The intake administrators are administrators in gates/roles.py (0.B9): one list, whichever settings carry it.
        storage.intake_admins = tuple(dict.fromkeys((*storage.intake_admins, *intake.admins)))
        super().__init__(storage)
        self.intake = intake
        self.store = store_for(storage)

    def authorize(self, actor):
        if not access_for(self.settings, actor).can('manage_intake'):
            raise PermissionError('Intake administrator access required')

    def activate(self, provider, actor, *, now=None):
        self.authorize(actor)
        if provider not in {'slack', 'fathom'}:
            raise ValueError('Unknown provider')
        if provider == 'slack' and (not self.intake.slack_token or not self.intake.channels):
            raise ValueError('Configure the Slack intake token and selected channels first')
        if provider == 'fathom' and not self.intake.fathom_key:
            raise ValueError('Configure the Fathom API key first')
        now = now or datetime.now(UTC)
        with self.connection() as conn:
            lock(conn)
            existing = conn.execute('SELECT * FROM intake_connections WHERE connection_id=%s', (provider,)).fetchone()
            if existing:
                return existing  # Activation can never rewind an existing live checkpoint.
            config = {'workspace': self.intake.workspace, 'channels': list(self.intake.channels)} if provider == 'slack' else {}
            insert(conn, 'intake_connections', {'connection_id': provider, 'provider': provider,
                   'activated_at': now, 'checkpoint': now, 'config': config})
            if not conn.execute("SELECT 1 FROM intake_buckets WHERE status='open'").fetchone():
                insert(conn, 'intake_buckets', {'bucket_id': identifier('bucket'), 'starts_at': now})
            return conn.execute('SELECT * FROM intake_connections WHERE connection_id=%s', (provider,)).fetchone()

    def queue(self, conn, stage, payload, *, intent=None, depends_on=()):
        intent = intent or canonical_hash([stage, payload])
        run_id, job_id = 'intake_run_' + intent[:32], 'intake_job_' + intent[:32]
        insert(conn, 'pipeline_runs', {'run_id': run_id, 'week_id': None, 'run_scope': 'source_intake',
               'trigger_type': 'source_update', 'input_refs': payload}, conflict=True)
        insert(conn, 'pipeline_jobs', {'job_id': job_id, 'run_id': run_id, 'week_id': None,
               **placement(stage, intake=True), 'stage': stage, 'idempotency_key': 'intake:' + intent,
               'input_hash': intent, 'progress_details': {'dependencies': list(depends_on)}}, conflict=True)
        return job_id

    def request_collection(self, *, cutoff=None, complete=False):
        cutoff = cutoff or datetime.now(UTC)
        with self.connection() as conn:
            lock(conn)
            bucket = conn.execute("SELECT * FROM intake_buckets WHERE status='open'").fetchone()
            if not bucket:
                raise ValueError('Activate a connector first')
            if complete:
                previous = conn.execute("SELECT * FROM intake_buckets WHERE status='collecting'").fetchone()
                if previous:
                    return previous
                if cutoff <= bucket['starts_at']:
                    raise ValueError('Completion cutoff must follow the current bucket start')
                conn.execute("UPDATE intake_buckets SET status='collecting',cutoff=%s WHERE bucket_id=%s", (cutoff, bucket['bucket_id']))
                insert(conn, 'intake_buckets', {'bucket_id': identifier('bucket'), 'starts_at': cutoff})
            requests = []
            for connection in conn.execute('SELECT * FROM intake_connections ORDER BY connection_id').fetchall():
                if connection['activated_at'] >= cutoff:
                    continue
                start = max(connection['activated_at'], connection['checkpoint'])
                # If discovery is ahead, an empty coverage request is sufficient.
                start = min(start, cutoff)
                rid = 'request_' + canonical_hash([connection['connection_id'], bucket['bucket_id'], start.isoformat(), cutoff.isoformat()])[:32]
                insert(conn, 'intake_requests', {'request_id': rid, 'connection_id': connection['connection_id'],
                       'bucket_id': bucket['bucket_id'], 'window_start': start, 'window_end': cutoff}, conflict=True)
                if connection['provider'] == 'fathom':
                    self.queue(conn, 'intake_fathom', {'request_id': rid})
                requests.append(rid)
            return {'bucket_id': bucket['bucket_id'], 'request_ids': requests, 'cutoff': cutoff}

    def requests(self):
        with self.connection() as conn:
            return conn.execute("""SELECT r.*,c.config FROM intake_requests r JOIN intake_connections c USING(connection_id)
                WHERE c.provider='slack' AND r.status NOT IN ('completed','superseded')
                ORDER BY r.window_end,r.window_start,r.request_id""").fetchall()

    def receive(self, batch: SlackBatch, raw: bytes):
        digest = hashlib.sha256(raw).hexdigest()
        artifact = f'intake/slack/{digest}.json'
        with self.connection() as conn:
            lock(conn)
            old = conn.execute('SELECT * FROM intake_batches WHERE batch_id=%s', (batch.batch_id,)).fetchone()
            if old:
                if old['content_hash'] != digest:
                    raise ValueError('Batch identifier already contains different bytes')
                return old
            request = conn.execute("""SELECT r.*,c.config,c.activated_at FROM intake_requests r
                JOIN intake_connections c USING(connection_id) WHERE request_id=%s AND c.provider='slack'""", (batch.request_id,)).fetchone()
            if not request or batch.workspace != request['config']['workspace'] or batch.channel not in request['config']['channels']:
                raise PermissionError('Unknown collection request or unconfigured workspace/channel')
            if request['status'] in {'completed', 'superseded'}:
                raise ValueError('Collection request is already complete; use a current request')
            if (batch.window_start, batch.window_end) != (request['window_start'], request['window_end']):
                raise ValueError('Batch window must match its collection request')
            new_threads = {m.thread_ts for m in batch.messages if not m.context_only and m.thread_ts}
            for message in batch.messages:
                event_time = message.updated_at if message.deleted or message.updated_at > slack_time(message.ts) else slack_time(message.ts)
                if message.context_only:
                    if message.ts not in new_threads or message.deleted or message.files:
                        raise ValueError('Context must be a parent of a delivered reply, without attachments or deletion')
                elif not max(request['activated_at'], batch.window_start) <= event_time < batch.window_end:
                    raise ValueError('Message event is outside the activated collection window')
            coverage = request['coverage']
            channel = coverage.setdefault(batch.channel, {'total_parts': batch.total_parts, 'parts': {}})
            if channel['total_parts'] != batch.total_parts or str(batch.part) in channel['parts']:
                raise ValueError('Conflicting channel part; retry with the original batch identifier')
            self.store.write_bytes(artifact, raw)
            insert(conn, 'intake_batches', {'batch_id': batch.batch_id, 'request_id': batch.request_id,
                   'content_hash': digest, 'raw_artifact': artifact})
            channel['parts'][str(batch.part)] = {'batch_id': batch.batch_id, 'gaps': batch.gaps}
            conn.execute('UPDATE intake_requests SET coverage=%s WHERE request_id=%s', (Jsonb(coverage), batch.request_id))
            self.queue(conn, 'intake_slack', {'batch_id': batch.batch_id})
            return {'batch_id': batch.batch_id, 'status': 'received'}

    def source(self, conn, connection, upstream, kind, title, *, metadata=None, occurred_at=None, url=None, received_at=None):
        sid = 'source_' + canonical_hash([connection, upstream])[:32]
        insert(conn, 'intake_sources', {'source_id': sid, 'connection_id': connection,
               'upstream_id': upstream, 'kind': kind, 'title': title, 'metadata': metadata or {},
               'occurred_at': occurred_at, 'source_url': url,
               'received_at': received_at or datetime.now(UTC)}, conflict=True)
        return sid

    def revision(self, conn, source_id, digest, artifact, normalized=None, *, deleted=False, provider_updated_at=None, received_at=None):
        received_at = received_at or datetime.now(UTC)
        rid = 'revision_' + canonical_hash([source_id, digest])[:32]
        old = conn.execute('SELECT * FROM intake_revisions WHERE revision_id=%s', (rid,)).fetchone()
        if old:
            return rid
        source = conn.execute('SELECT * FROM intake_sources WHERE source_id=%s FOR UPDATE', (source_id,)).fetchone()
        transcript_id = normalized['transcript_id'] if normalized and normalized['original_text'] else None
        normalise_job = None
        if transcript_id:
            normalized['source_metadata']['intake'] = {'source_id': source_id, 'revision_id': rid}
            if not conn.execute('SELECT 1 FROM transcripts WHERE transcript_id=%s', (transcript_id,)).fetchone():
                insert(conn, 'transcripts', normalized)
                # A new document is normalised (speakers, call type, date, version 2 chunks) before it is indexed, so the
                # indexing job below waits for it (plan 1.B3, 1.B6): one segmentation, no chunks to throw away.
                queued = queue_normalisation(conn, [transcript_id], actor='intake', version=NORMALISER_VERSION)
                normalise_job = queued['jobs'][0]
            else:
                existing = conn.execute("""SELECT job_id FROM pipeline_jobs WHERE transcript_id=%s AND stage='document_normalise'
                    AND status<>'completed' LIMIT 1""", (transcript_id,)).fetchone()
                normalise_job = existing['job_id'] if existing else None
        insert(conn, 'intake_revisions', {'revision_id': rid, 'source_id': source_id,
               'transcript_id': transcript_id, 'content_hash': digest, 'raw_artifact': artifact,
               'deleted': deleted, 'collection_status': 'received', 'extraction_status': 'completed',
               'indexing_status': 'pending' if transcript_id else 'not_applicable', 'received_at': received_at})
        # Never let an out-of-order Slack update replace a newer current revision.
        if not provider_updated_at or not source['provider_updated_at'] or provider_updated_at >= source['provider_updated_at']:
            conn.execute("UPDATE intake_sources SET latest_revision_id=%s,provider_updated_at=%s,status=%s WHERE source_id=%s",
                         (rid, provider_updated_at, 'deleted' if deleted else 'received', source_id))
        bucket = conn.execute("""SELECT bucket_id FROM intake_buckets WHERE status<>'completed' AND starts_at<=%s
            AND (cutoff IS NULL OR %s<cutoff) ORDER BY starts_at DESC LIMIT 1""", (received_at, received_at)).fetchone()
        if not bucket:
            bucket = conn.execute("SELECT bucket_id FROM intake_buckets WHERE status='open'").fetchone()
        insert(conn, 'intake_membership', {'bucket_id': bucket['bucket_id'], 'revision_id': rid})
        if transcript_id:
            self.queue(conn, 'transcript_chunk_embedding', {'revision_id': rid}, depends_on=[normalise_job] if normalise_job else ())
        return rid

    def process_slack(self, batch_id):
        with self.connection() as conn:
            lock(conn)
            receipt = conn.execute('SELECT * FROM intake_batches WHERE batch_id=%s', (batch_id,)).fetchone()
            if receipt['status'] == 'processed':
                return
            batch = SlackBatch.model_validate(self.store.read_json(receipt['raw_artifact']))
            context = {m.ts: m.model_dump(mode='json') for m in batch.messages if m.context_only}
            for message in batch.messages:
                if message.context_only:
                    continue
                body = message.model_dump(mode='json')
                upstream = f'{batch.workspace}:{batch.channel}:{message.ts}'
                sid = self.source(conn, 'slack', upstream, 'slack', f'Slack #{batch.channel}',
                                  occurred_at=slack_time(message.ts), url=message.permalink, received_at=receipt['received_at'])
                # Stable semantic revision: transport pagination and context do not change identity.
                digest = canonical_hash(body)
                raw_artifact = f'intake/slack-messages/{digest}.json'
                self.store.write_json(raw_artifact, {'message': body, 'parent_context': context.get(message.thread_ts)})
                rid = self.revision(conn, sid, digest, raw_artifact, slack(body, batch.channel, sid, digest),
                                    deleted=message.deleted, provider_updated_at=message.updated_at, received_at=receipt['received_at'])
                for asset in ([] if message.deleted else message.files):
                    aid = 'asset_' + canonical_hash([rid, asset.file_id])[:32]
                    status = 'linked_video' if asset.mime_type.startswith('video/') else 'oversized' if asset.size_bytes > self.intake.max_upload_bytes else 'awaiting_upload'
                    insert(conn, 'intake_assets', {'asset_id': aid, 'revision_id': rid,
                           'provider_file_id': asset.file_id, 'filename': asset.filename, 'mime_type': asset.mime_type,
                           'expected_hash': asset.sha256, 'size_bytes': asset.size_bytes,
                           'status': status, 'metadata': {'permalink': asset.permalink}}, conflict=True)
            conn.execute("UPDATE intake_batches SET status='processed' WHERE batch_id=%s", (batch_id,))
            self.update_slack_coverage(conn, batch.request_id)

    def update_slack_coverage(self, conn, request_id):
        request = conn.execute("""SELECT r.*,c.config FROM intake_requests r JOIN intake_connections c USING(connection_id)
            WHERE request_id=%s""", (request_id,)).fetchone()
        for channel_id in request['config']['channels']:
            coverage = request['coverage'].get(channel_id, {})
            parts = coverage.get('parts', {})
            if len(parts) != coverage.get('total_parts') or any(p['gaps'] for p in parts.values()):
                return
            for part in parts.values():
                row = conn.execute('SELECT status FROM intake_batches WHERE batch_id=%s', (part['batch_id'],)).fetchone()
                if row['status'] != 'processed':
                    return
        conn.execute("UPDATE intake_requests SET status='completed' WHERE request_id=%s", (request_id,))
        # A later complete collection can repair an earlier partial/gapped window.
        # Never discard a batch already accepted but still awaiting processing.
        conn.execute("""UPDATE intake_requests old SET status='superseded'
            WHERE old.connection_id='slack' AND old.request_id<>%s AND old.status NOT IN ('completed','superseded')
              AND old.window_start >= %s AND old.window_end <= %s
              AND NOT EXISTS (SELECT 1 FROM intake_batches b WHERE b.request_id=old.request_id AND b.status<>'processed')""",
                     (request_id, request['window_start'], request['window_end']))
        # Only contiguous coverage may advance the connector checkpoint.
        checkpoint = conn.execute('SELECT checkpoint FROM intake_connections WHERE connection_id=%s', ('slack',)).fetchone()['checkpoint']
        for row in conn.execute("SELECT * FROM intake_requests WHERE connection_id='slack' AND status='completed' ORDER BY window_start,window_end"):
            if row['window_start'] <= checkpoint:
                checkpoint = max(checkpoint, row['window_end'])
        conn.execute("UPDATE intake_connections SET checkpoint=%s,health='ready',error_summary=NULL,updated_at=now() WHERE connection_id='slack'", (checkpoint,))

    def upload(self, asset_id, data):
        digest = hashlib.sha256(data).hexdigest()
        with self.connection() as conn:
            lock(conn)
            asset = conn.execute('SELECT * FROM intake_assets WHERE asset_id=%s FOR UPDATE', (asset_id,)).fetchone()
            if not asset:
                raise ValueError('Unknown attachment')
            if asset['status'] in {'linked_video', 'oversized'}:
                raise ValueError('This attachment accepts metadata only')
            if len(data) != asset['size_bytes'] or len(data) > self.intake.max_upload_bytes:
                raise ValueError('Attachment size differs from declared size or exceeds the upload limit')
            if asset['expected_hash'] and asset['expected_hash'] != digest:
                raise ValueError('Attachment hash differs from the declared hash')
            if asset['content_hash'] and asset['content_hash'] != digest:
                raise ValueError('Attachment bytes are immutable; deliver a new message revision')
            path = f'intake/assets/{digest}'
            self.store.write_bytes(path, data)
            if asset['raw_artifact']:
                return {'asset_id': asset_id, 'status': asset['status']}
            conn.execute("UPDATE intake_assets SET content_hash=%s,raw_artifact=%s,status='received' WHERE asset_id=%s", (digest, path, asset_id))
            self.queue(conn, 'intake_extract', {'asset_id': asset_id})
            return {'asset_id': asset_id, 'status': 'received'}

    def finalize(self):
        with self.connection() as conn:
            lock(conn)
            bucket = conn.execute("SELECT * FROM intake_buckets WHERE status='collecting'").fetchone()
            if not bucket:
                return False
            bid = bucket['bucket_id']
            if conn.execute("SELECT 1 FROM intake_requests WHERE bucket_id=%s AND status NOT IN ('completed','superseded') LIMIT 1", (bid,)).fetchone():
                return False
            if conn.execute("""SELECT 1 FROM intake_revisions r JOIN intake_membership m USING(revision_id)
                WHERE m.bucket_id=%s AND (r.extraction_status<>'completed' OR r.indexing_status NOT IN ('ready','not_applicable')) LIMIT 1""", (bid,)).fetchone():
                return False
            if conn.execute("""SELECT 1 FROM intake_assets a JOIN intake_membership m USING(revision_id)
                WHERE m.bucket_id=%s AND a.status NOT IN ('completed','linked_video','oversized','unsupported') LIMIT 1""", (bid,)).fetchone():
                return False
            conn.execute("UPDATE intake_buckets SET status='completed',completed_at=now() WHERE bucket_id=%s", (bid,))
            return True

    def retry_intake(self, job_id, actor):
        self.authorize(actor)
        with self.connection() as conn:
            lock(conn)
            job = conn.execute("SELECT * FROM pipeline_jobs WHERE job_id=%s AND executor='rq' FOR UPDATE", (job_id,)).fetchone()
            if not job or job['status'] not in {'failed', 'waiting'}:
                raise ValueError('Only failed or waiting intake jobs can be retried')
            conn.execute("UPDATE pipeline_jobs SET status='queued',error_summary=NULL,lease_token=NULL,lease_expires_at=NULL,updated_at=now() WHERE job_id=%s", (job_id,))
            conn.execute("UPDATE pipeline_runs SET status='queued',error_summary=NULL,updated_at=now() WHERE run_id=%s", (job['run_id'],))
            self.event(conn, job['run_id'], 'intake_retry', 'Administrator requested retry', details={'actor': actor})

    def overview(self, actor):
        with self.connection() as conn:
            return {'can_admin': access_for(self.settings, actor).can('manage_intake'),
                    'schedule': cycle_schedule_text(conn),
                    'connections': conn.execute('SELECT * FROM intake_connections ORDER BY connection_id').fetchall(),
                    'buckets': conn.execute('SELECT * FROM intake_buckets ORDER BY starts_at DESC LIMIT 30').fetchall(),
                    'requests': conn.execute("""SELECT * FROM intake_requests WHERE status NOT IN ('completed','superseded')
                        ORDER BY window_end,window_start,request_id LIMIT 100""").fetchall(),
                    'sources': conn.execute("""SELECT s.*,r.revision_id,r.collection_status,r.extraction_status,r.indexing_status,r.error_summary
                        FROM intake_sources s LEFT JOIN intake_revisions r ON r.revision_id=s.latest_revision_id
                        ORDER BY s.received_at DESC,s.source_id LIMIT 200""").fetchall(),
                    'jobs': conn.execute("""SELECT job_id,run_id,stage,status,error_summary,current_message,attempt_count,created_at,updated_at
                        FROM pipeline_jobs WHERE executor='rq' AND status<>'completed' ORDER BY created_at DESC LIMIT 100""").fetchall()}

    def detail(self, source_id):
        with self.connection() as conn:
            source = conn.execute('SELECT * FROM intake_sources WHERE source_id=%s', (source_id,)).fetchone()
            if not source:
                raise ValueError('Source not found')
            revisions = conn.execute("""SELECT r.*,t.original_text,t.passage_map FROM intake_revisions r
                LEFT JOIN transcripts t USING(transcript_id) WHERE r.source_id=%s ORDER BY r.received_at DESC""", (source_id,)).fetchall()
            assets = conn.execute("""SELECT a.* FROM intake_assets a JOIN intake_revisions r USING(revision_id)
                WHERE r.source_id=%s""", (source_id,)).fetchall()
            return {'source': source, 'revisions': revisions, 'assets': assets}

    def bucket_detail(self, bucket_id):
        with self.connection() as conn:
            bucket = conn.execute('SELECT * FROM intake_buckets WHERE bucket_id=%s', (bucket_id,)).fetchone()
            if not bucket:
                raise ValueError('Bucket not found')
            sources = conn.execute("""SELECT s.*,r.revision_id,r.collection_status,r.extraction_status,
                r.indexing_status,r.error_summary,r.received_at FROM intake_membership m
                JOIN intake_revisions r USING(revision_id) JOIN intake_sources s USING(source_id)
                WHERE m.bucket_id=%s ORDER BY r.received_at DESC,r.revision_id""", (bucket_id,)).fetchall()
            return {'bucket': bucket, 'sources': sources}

    def batch_status(self, batch_id):
        with self.connection() as conn:
            receipt = conn.execute('SELECT * FROM intake_batches WHERE batch_id=%s', (batch_id,)).fetchone()
            if not receipt:
                raise ValueError('Batch not found')
            # Asset IDs are the upload handles returned to the bot after normalization.
            batch = SlackBatch.model_validate(self.store.read_json(receipt['raw_artifact']))
            revisions = []
            for message in batch.messages:
                if message.context_only:
                    continue
                upstream = f'{batch.workspace}:{batch.channel}:{message.ts}'
                source_id = 'source_' + canonical_hash(['slack', upstream])[:32]
                digest = canonical_hash(message.model_dump(mode='json'))
                revisions.append('revision_' + canonical_hash([source_id, digest])[:32])
            assets = conn.execute('SELECT * FROM intake_assets WHERE revision_id=ANY(%s)', (revisions,)).fetchall()
            statuses = conn.execute("""SELECT revision_id,collection_status,extraction_status,indexing_status,error_summary
                FROM intake_revisions WHERE revision_id=ANY(%s)""", (revisions,)).fetchall()
            return {**receipt, 'assets': assets, 'revisions': statuses}

    def finish(self, conn, job, result, **kwargs):
        # The vector proof, searchable state and job completion commit together.
        if job['stage'] == 'transcript_chunk_embedding':
            run = conn.execute('SELECT input_refs FROM pipeline_runs WHERE run_id=%s', (job['run_id'],)).fetchone()
            state = 'not_applicable' if (result or {}).get('not_applicable') else 'ready'
            revision = conn.execute("UPDATE intake_revisions SET indexing_status=%s,error_summary=NULL WHERE revision_id=%s RETURNING transcript_id",
                                    (state, run['input_refs']['revision_id'])).fetchone()
            conn.execute("UPDATE transcripts SET processing_status='ready' WHERE transcript_id=%s", (revision['transcript_id'],))
        super().finish(conn, job, result, **kwargs)
