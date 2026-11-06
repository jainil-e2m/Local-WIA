"""Future intake contracts and real SQL integration. No provider traffic."""
from datetime import UTC, datetime, timedelta
import hashlib
import io
import os
import zipfile

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg import sql

from backend_pipeline.database import check, apply_intake, apply_brief_indexes
from backend_pipeline.config import Settings
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.repository import ContentRepository
from backend_pipeline.store import canonical_hash
from backend_pipeline import chunk_encoding, retrieval
from backend_pipeline.intake.config import IntakeSettings
from backend_pipeline.intake.contracts import SlackBatch
from backend_pipeline.intake.normalize import fathom
from backend_pipeline.intake.repository import IntakeRepository
from backend_pipeline.intake.runtime import execute, last_saturday, reconcile, tick
from backend_pipeline.intake.fathom import FathomClient, PendingTranscript, collect
from backend_pipeline.intake.api import routers
from backend_pipeline.intake.extract import extract, UnsupportedAsset

T0 = datetime(2026, 10, 15, 12, tzinfo=UTC)
ADMIN = 'admin@example.test'
URL = os.getenv('INTAKE_TEST_DATABASE_URL')


def message(seconds=10, **changes):
    stamp = T0 + timedelta(seconds=seconds)
    return {'ts': f'{int(stamp.timestamp())}.000001', 'text': 'Wedding inquiry follow-up improved.',
            'updated_at': stamp.isoformat(), 'user': 'U1', **changes}


def batch(request, channel='C082DURRJ2U', messages=None, **changes):
    return SlackBatch.model_validate({'batch_id': 'batch_' + channel, 'request_id': request['request_id'],
        'workspace': 'T03P5A3L1DK', 'channel': channel, 'window_start': request['window_start'],
        'window_end': request['window_end'], 'part': 1, 'total_parts': 1,
        'messages': [message()] if messages is None else messages, **changes})


@pytest.fixture
def repo(tmp_path):
    if not URL:
        pytest.skip('Set INTAKE_TEST_DATABASE_URL to isolated atelier_intake_test')
    storage = StorageSettings(database_url=URL, artifact_root=tmp_path, api_secret='backend-test-secret')
    config = IntakeSettings(slack_token='bot-test-secret', fathom_key='fathom-test-secret', admins=(ADMIN,))
    repo = IntakeRepository(storage, config)
    with repo.connection() as conn:
        if conn.info.dbname != 'atelier_intake_test':
            raise RuntimeError('Intake tests refuse all other databases')
        check(conn)
        tables = [r['tablename'] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'intake_schema_migrations'")]
        conn.execute(sql.SQL('TRUNCATE {} CASCADE').format(sql.SQL(',').join(map(sql.Identifier, tables))))
    return repo


def activate(repo, provider='slack', end=60):
    repo.activate(provider, ADMIN, now=T0)
    receipt = repo.request_collection(cutoff=T0 + timedelta(seconds=end))
    with repo.connection() as conn:
        return conn.execute('SELECT * FROM intake_requests WHERE request_id=%s', (receipt['request_ids'][0],)).fetchone()


def deliver(repo, value):
    return repo.receive(value, value.model_dump_json().encode())


def jobs(repo, stage):
    with repo.connection() as conn:
        return conn.execute('SELECT * FROM pipeline_jobs WHERE stage=%s ORDER BY created_at', (stage,)).fetchall()


def cache_vectors(repo, models=None):
    models = models or Settings()
    digest = chunk_encoding.contract(models)
    with repo.connection() as conn:
        rows = conn.execute('SELECT * FROM transcript_chunks').fetchall()
    for row in rows:
        ih = chunk_encoding.chunk_view(row)['input_hash']
        vector = [1.] + [0.] * 1535
        path = 'chunk-encoding/' + canonical_hash({'contract': digest, 'input_hash': ih}) + '.json'
        repo.store.write_json(path, {'contract': digest, 'input_hash': ih, 'vector': vector,
            'vector_digest': chunk_encoding.vector_digest(vector), 'returned_model': models.embedding_model,
            'response_artifact': 'mock-receipt.json'})


def test_normalizers_keep_exact_offsets():
    data = {'transcript': [{'timestamp': '00:00:01', 'text': 'We improved follow-up.', 'speaker': {'display_name': 'Alice'}},
                           {'timestamp': '00:00:05', 'text': 'It was not measured.', 'speaker': {}}]}
    row = fathom({'title': 'Call'}, data, 's1', 'abc')
    for p in row['passage_map']:
        assert row['original_text'][p['start']:p['end']]
    assert row['passage_map'][0]['start_ms'] == 1000
    assert row['passage_map'][1]['end_ms'] is None
    assert row['passage_map'][1]['locator']['segment'] == 1
    with pytest.raises(ValueError):
        fathom({}, {'transcript': []}, 's1', 'abc')


@pytest.mark.parametrize(('when', 'expected'), [
    ('2026-07-11T09:00:00+00:00', '2026-07-11T09:00:00+00:00'),
    ('2026-12-12T10:00:00+00:00', '2026-12-12T10:00:00+00:00'),
    ('2026-07-11T08:59:00+00:00', '2026-07-04T09:00:00+00:00'),
])
def test_texas_schedule(when, expected):
    assert last_saturday(datetime.fromisoformat(when)) == datetime.fromisoformat(expected)


def test_text_docx_and_unsupported_extraction():
    assert extract(b'One\nTwo', 'text/plain', 'x.txt', IntakeSettings())[1]['locator'] == {'line': 2}
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as z:
        z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Example</w:t></w:r></w:p></w:document>')
    assert extract(data.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'x.docx', IntakeSettings())[0]['text'] == 'Example'
    with pytest.raises(UnsupportedAsset):
        extract(b'x', 'application/octet-stream', 'x.bin', IntakeSettings())


def test_scanned_pdf_resource_handling_and_page_locations(monkeypatch):
    from PIL import Image
    import backend_pipeline.intake.extract as extractor
    data = io.BytesIO()
    Image.new('RGB', (100, 100), 'white').save(data, 'PDF')
    monkeypatch.setattr(extractor, 'ocr_image', lambda image: [{'text': 'Extracted observation', 'extraction_method': 'ocr', 'locator': {'boxes': []}}])
    result = extract(data.getvalue(), 'application/pdf', 'scan.pdf', IntakeSettings())
    assert result[0]['locator']['page'] == 1
    assert result[0]['extraction_method'] == 'ocr'


def test_activation_does_not_adopt_any_history(repo):
    assert repo.overview(ADMIN)['sources'] == []
    request = activate(repo)
    connection = repo.activate('slack', ADMIN, now=T0 - timedelta(days=365))
    assert connection['activated_at'] == T0
    assert request['window_start'] == T0
    assert jobs(repo, 'moment_extraction') == []
    assert jobs(repo, 'angle_generation') == []
    with pytest.raises(PermissionError):
        repo.activate('fathom', 'someone@example.test')


def test_slack_receipt_duplicates_conflicts_and_boundaries(repo):
    request = activate(repo)
    value = batch(request)
    first = deliver(repo, value)
    assert deliver(repo, value)['batch_id'] == first['batch_id']
    assert len(jobs(repo, 'intake_slack')) == 1
    with pytest.raises(ValueError, match='different bytes'):
        deliver(repo, value.model_copy(update={'gaps': ['missing page']}))
    with pytest.raises(ValueError, match='outside'):
        deliver(repo, batch(request, batch_id='old', messages=[message(-10)]))
    with pytest.raises(PermissionError):
        deliver(repo, batch(request, channel='UNSELECTED'))
    assert repo.store.path(f'intake/slack/{hashlib.sha256(value.model_dump_json().encode()).hexdigest()}.json').is_file()


def test_three_channel_coverage_and_empty_results(repo):
    request = activate(repo)
    for channel in repo.intake.channels:
        value = batch(request, channel=channel, messages=[])
        deliver(repo, value)
        repo.process_slack(value.batch_id)
    with repo.connection() as conn:
        assert conn.execute('SELECT status FROM intake_requests').fetchone()['status'] == 'completed'
        assert conn.execute('SELECT checkpoint FROM intake_connections').fetchone()['checkpoint'] == request['window_end']


def test_partial_coverage_blocks_completion(repo):
    request = activate(repo)
    value = batch(request, messages=[], part=1, total_parts=2)
    deliver(repo, value); repo.process_slack(value.batch_id)
    repo.request_collection(cutoff=T0 + timedelta(seconds=90), complete=True)
    assert repo.finalize() is False


def test_worker_separation_and_cached_indexing(repo):
    request = activate(repo)
    value = batch(request)
    deliver(repo, value)
    assert ContentRepository(repo.settings).claim() is None
    execute(jobs(repo, 'intake_slack')[0]['job_id'], repo=repo, models=Settings())
    cache_vectors(repo)
    job = jobs(repo, 'transcript_chunk_embedding')[0]
    execute(job['job_id'], repo=repo, models=Settings())
    execute(job['job_id'], repo=repo, models=Settings())
    with repo.connection() as conn:
        revision = conn.execute('SELECT * FROM intake_revisions').fetchone()
        assert revision['indexing_status'] == 'ready', revision['error_summary']
        assert conn.execute('SELECT count(*) n FROM transcript_chunks WHERE embedding IS NOT NULL').fetchone()['n'] == 1
        assert conn.execute("SELECT attempt_count FROM pipeline_jobs WHERE job_id=%s", (job['job_id'],)).fetchone()['attempt_count'] == 1
        assert conn.execute('SELECT count(*) n FROM weeks').fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) n FROM content_angles').fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) n FROM content_briefs').fetchone()['n'] == 0


def test_ready_archive_survives_new_unindexed_revision(repo):
    request = activate(repo)
    value = batch(request)
    deliver(repo, value); repo.process_slack(value.batch_id)
    cache_vectors(repo)
    execute(jobs(repo, 'transcript_chunk_embedding')[0]['job_id'], repo=repo, models=Settings())
    with repo.connection() as conn:
        snapshot = retrieval.archive(conn, Settings(), False)
        assert len(snapshot['sources']) == 1
    request2 = repo.request_collection(cutoff=T0 + timedelta(seconds=120))
    with repo.connection() as conn:
        request2 = conn.execute('SELECT * FROM intake_requests WHERE request_id=%s', (request2['request_ids'][0],)).fetchone()
    value2 = batch(request2, batch_id='second', messages=[message(80)])
    deliver(repo, value2); repo.process_slack(value2.batch_id)
    with repo.connection() as conn:
        assert retrieval.archive(conn, Settings(), False)['sources'] == snapshot['sources']
        retrieval.check_archive(conn, snapshot)


def test_edit_delete_revisions_do_not_destroy_original(repo):
    request = activate(repo)
    value = batch(request)
    deliver(repo, value); repo.process_slack(value.batch_id)
    edited = message(text='Changed statement', updated_at=(T0 + timedelta(seconds=20)).isoformat())
    value2 = batch(request, batch_id='edited', part=2, total_parts=2, messages=[edited])
    # Use a second request, since the original part count is immutable.
    repo.request_collection(cutoff=T0 + timedelta(seconds=80))
    request2 = repo.requests()[-1]
    value2 = batch(request2, batch_id='edited', messages=[edited])
    deliver(repo, value2); repo.process_slack(value2.batch_id)
    deleted = {**edited, 'deleted': True, 'text': '', 'updated_at': (T0 + timedelta(seconds=30)).isoformat()}
    repo.request_collection(cutoff=T0 + timedelta(seconds=100))
    value3 = batch(repo.requests()[-1], batch_id='deleted', messages=[deleted])
    deliver(repo, value3); repo.process_slack(value3.batch_id)
    with repo.connection() as conn:
        assert conn.execute('SELECT count(*) n FROM intake_sources').fetchone()['n'] == 1
        assert conn.execute('SELECT count(*) n FROM intake_revisions').fetchone()['n'] == 3
        assert conn.execute('SELECT count(*) n FROM transcripts').fetchone()['n'] == 2
        assert conn.execute('SELECT status FROM intake_sources').fetchone()['status'] == 'deleted'


def test_older_parent_is_context_only(repo):
    request = activate(repo)
    parent = message(-3600, context_only=True)
    child = message(20, thread_ts=parent['ts'])
    value = batch(request, messages=[parent, child])
    deliver(repo, value); repo.process_slack(value.batch_id)
    with repo.connection() as conn:
        assert conn.execute('SELECT count(*) n FROM intake_sources').fetchone()['n'] == 1
    with pytest.raises(ValueError, match='Context'):
        deliver(repo, batch(request, batch_id='unrelated', messages=[parent, message(30)]))


def test_attachment_upload_hash_and_local_extraction(repo):
    request = activate(repo)
    content = b'Client reports better inquiry follow-up.'
    asset = {'file_id': 'F1', 'filename': 'notes.txt', 'mime_type': 'text/plain', 'size_bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
    value = batch(request, messages=[message(files=[asset])])
    deliver(repo, value); repo.process_slack(value.batch_id)
    attachment = repo.batch_status(value.batch_id)['assets'][0]
    with pytest.raises(ValueError):
        repo.upload(attachment['asset_id'], b'wrong')
    repo.upload(attachment['asset_id'], content)
    repo.upload(attachment['asset_id'], content)
    assert len(jobs(repo, 'intake_extract')) == 1
    execute(jobs(repo, 'intake_extract')[0]['job_id'], repo=repo, models=Settings())
    with repo.connection() as conn:
        assert conn.execute('SELECT status FROM intake_assets').fetchone()['status'] == 'completed'
        assert conn.execute('SELECT count(*) n FROM intake_sources').fetchone()['n'] == 2


def test_rq_recovers_durable_receipt_and_uses_json(repo):
    import fakeredis
    from rq import Queue
    from rq.serializers import JSONSerializer
    request = activate(repo)
    deliver(repo, batch(request))
    redis = fakeredis.FakeRedis()
    reconcile(repo, redis)
    reconcile(repo, redis)
    queue = Queue('atelier-intake', connection=redis, serializer=JSONSerializer)
    assert len(queue) == 1
    queued = queue.jobs[0]
    assert list(queued.args) == [jobs(repo, 'intake_slack')[0]['job_id']]
    assert queued.func_name == 'backend_pipeline.intake.runtime.execute'


def test_fathom_pagination_activation_and_pending(repo):
    request = activate(repo, provider='fathom')
    calls, ready = [], [False]
    def response(req):
        calls.append(req)
        if req.url.path.endswith('/meetings'):
            assert datetime.fromisoformat(req.url.params['created_after']) >= T0
            if req.url.params.get('cursor'):
                return httpx.Response(200, json={'items': [], 'next_cursor': None})
            return httpx.Response(200, json={'items': [
                {'recording_id': 1, 'created_at': (T0 - timedelta(days=1)).isoformat()},
                {'recording_id': 2, 'created_at': (T0 + timedelta(seconds=5)).isoformat(), 'title': 'New call'}], 'next_cursor': 'page2'})
        if not ready[0]:
            return httpx.Response(404)
        return httpx.Response(200, json={'transcript': [{'text': 'We improved follow-up.', 'timestamp': '00:01:00'}]})
    client = FathomClient(repo.intake, httpx.MockTransport(response))
    with pytest.raises(PendingTranscript):
        collect(repo, request['request_id'], client)
    with repo.connection() as conn:
        assert conn.execute('SELECT upstream_id,status FROM intake_sources').fetchone() == {'upstream_id': '2', 'status': 'pending_transcript'}
    ready[0] = True
    collect(repo, request['request_id'], client)
    collect(repo, request['request_id'], client)
    assert not any('/recordings/1/' in str(c.url) for c in calls)
    with repo.connection() as conn:
        assert conn.execute('SELECT count(*) n FROM intake_revisions').fetchone()['n'] == 1
        assert conn.execute('SELECT status FROM intake_requests').fetchone()['status'] == 'completed'
    client.close()


@pytest.mark.parametrize('status', [401, 429, 503])
def test_fathom_http_failures_propagate_without_checkpoint(repo, status):
    request = activate(repo, provider='fathom')
    client = FathomClient(repo.intake, httpx.MockTransport(lambda _: httpx.Response(status)))
    with pytest.raises(httpx.HTTPStatusError):
        collect(repo, request['request_id'], client)
    with repo.connection() as conn:
        assert conn.execute('SELECT checkpoint FROM intake_connections').fetchone()['checkpoint'] == T0
    client.close()


def test_completed_bucket_immutable_and_late_content_uses_open_bucket(repo):
    activate(repo)
    result = repo.request_collection(cutoff=T0 + timedelta(seconds=120), complete=True)
    with repo.connection() as conn:
        conn.execute("UPDATE intake_requests SET status='completed'")
    assert repo.finalize()
    request = repo.request_collection(cutoff=T0 + timedelta(seconds=180))
    with repo.connection() as conn:
        row = conn.execute('SELECT * FROM intake_requests WHERE request_id=%s', (request['request_ids'][0],)).fetchone()
    value = batch(row, messages=[message(150)])
    deliver(repo, value); repo.process_slack(value.batch_id)
    with repo.connection() as conn:
        assert conn.execute('SELECT count(*) n FROM intake_membership WHERE bucket_id=%s', (result['bucket_id'],)).fetchone()['n'] == 0
        assert conn.execute("SELECT b.status FROM intake_membership m JOIN intake_buckets b USING(bucket_id)").fetchone()['status'] == 'open'


def test_api_service_and_admin_boundaries(repo):
    app = FastAPI()
    for route in routers(repo.settings, repo.intake):
        app.include_router(route)
    client = TestClient(app)
    assert client.get('/intake/v1/requests').status_code == 401
    service_headers = {'authorization': 'Bearer bot-test-secret'}
    assert client.get('/intake/v1/requests', headers=service_headers).status_code == 200
    assert client.get('/storage/intake/overview', headers=service_headers).status_code == 401
    headers = {'authorization': 'Bearer backend-test-secret', 'x-atelier-actor': 'team-id', 'x-atelier-email': 'other@example.test'}
    assert client.post('/storage/intake/connections/slack/activate', headers=headers).status_code == 403
    headers['x-atelier-email'] = ADMIN
    assert client.post('/storage/intake/connections/slack/activate', headers=headers).status_code == 202
    assert client.get('/storage/intake/overview', headers=headers).json()['can_admin'] is True


def test_migrations_idempotent(repo):
    assert apply_intake(URL)['status'] == 'already_applied'
    assert apply_brief_indexes(URL)['status'] == 'already_applied'


def test_overdue_schedule_runs_once_and_keeps_live_refreshing(repo):
    repo.activate('slack', ADMIN, now=T0)
    saturday = datetime(2026, 10, 17, 9, tzinfo=UTC)
    tick(repo, now=saturday)
    tick(repo, now=saturday + timedelta(seconds=1))
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM intake_buckets WHERE status='collecting'").fetchone()['n'] == 1
        assert conn.execute("SELECT starts_at FROM intake_buckets WHERE status='open'").fetchone()['starts_at'] == saturday


def test_complete_covering_window_repairs_old_gaps(repo):
    request = activate(repo)
    old = batch(request, messages=[], gaps=['provider page missing'])
    deliver(repo, old); repo.process_slack(old.batch_id)
    repo.request_collection(cutoff=T0 + timedelta(seconds=120))
    request2 = repo.requests()[-1]
    for channel in repo.intake.channels:
        newer = batch(request2, channel=channel, batch_id='repaired_' + channel, messages=[])
        deliver(repo, newer); repo.process_slack(newer.batch_id)
    with repo.connection() as conn:
        assert conn.execute('SELECT status FROM intake_requests WHERE request_id=%s', (request['request_id'],)).fetchone()['status'] == 'superseded'
        assert conn.execute('SELECT checkpoint FROM intake_connections').fetchone()['checkpoint'] == request2['window_end']


def test_missing_upload_and_failed_indexing_block_completion(repo):
    request = activate(repo)
    value = batch(request, messages=[message(files=[{'file_id': 'F1', 'filename': 'notes.txt', 'mime_type': 'text/plain', 'size_bytes': 5}])])
    deliver(repo, value); repo.process_slack(value.batch_id)
    execute(jobs(repo, 'transcript_chunk_embedding')[0]['job_id'], repo=repo, models=Settings())
    repo.request_collection(cutoff=T0 + timedelta(seconds=120), complete=True)
    with repo.connection() as conn:
        conn.execute("UPDATE intake_requests SET status='completed'")
    assert repo.finalize() is False
    with repo.connection() as conn:
        assert conn.execute('SELECT indexing_status FROM intake_revisions').fetchone()['indexing_status'] == 'failed'
        assert conn.execute('SELECT status FROM intake_assets').fetchone()['status'] == 'awaiting_upload'


def test_video_and_oversized_assets_need_no_upload(repo):
    request = activate(repo)
    files = [{'file_id': 'VIDEO', 'filename': 'clip.mp4', 'mime_type': 'video/mp4', 'size_bytes': 1000},
             {'file_id': 'LARGE', 'filename': 'large.pdf', 'mime_type': 'application/pdf', 'size_bytes': 50 * 1024 * 1024}]
    value = batch(request, messages=[message(text='', files=files)])
    deliver(repo, value); repo.process_slack(value.batch_id)
    assets = repo.batch_status(value.batch_id)['assets']
    assert {a['status'] for a in assets} == {'linked_video', 'oversized'}
    assert not jobs(repo, 'transcript_chunk_embedding')
    for asset in assets:
        with pytest.raises(ValueError, match='metadata only'):
            repo.upload(asset['asset_id'], b'')


def test_slack_adapter_deterministic_outbox_and_service_auth():
    from backend_pipeline.intake.slack_client import SlackDeliveryClient
    request = {'request_id': 'request_1', 'config': {'workspace': 'T03P5A3L1DK'},
               'window_start': T0.isoformat(), 'window_end': (T0 + timedelta(minutes=1)).isoformat()}
    data = SlackDeliveryClient.prepare(request, 'C082DURRJ2U', [message()])
    assert data == SlackDeliveryClient.prepare(request, 'C082DURRJ2U', [message()])
    def transport(req):
        assert req.headers['authorization'] == 'Bearer service-secret'
        assert req.content == data
        return httpx.Response(202, json={'status': 'received'})
    client = SlackDeliveryClient('http://localhost:18000', 'service-secret', transport=httpx.MockTransport(transport))
    assert client.send(data)['status'] == 'received'
    client.close()


def test_expired_embedding_requires_review_and_readonly_jobs_requeue(repo):
    import fakeredis
    request = activate(repo)
    value = batch(request)
    deliver(repo, value); repo.process_slack(value.batch_id)
    with repo.connection() as conn:
        conn.execute("""UPDATE pipeline_jobs SET status='running',lease_token='expired',
            lease_expires_at=now()-interval '1 minute' WHERE executor='rq'""")
    reconcile(repo, fakeredis.FakeRedis())
    with repo.connection() as conn:
        assert conn.execute("SELECT status FROM pipeline_jobs WHERE stage='transcript_chunk_embedding'").fetchone()['status'] == 'failed'
        assert conn.execute("SELECT status FROM pipeline_jobs WHERE stage='intake_slack'").fetchone()['status'] == 'queued'
        assert conn.execute('SELECT indexing_status FROM intake_revisions').fetchone()['indexing_status'] == 'failed'


def test_received_before_cutoff_can_finish_processing_in_collecting_bucket(repo):
    request = activate(repo)
    value = batch(request)
    deliver(repo, value)
    # Capture the actual durable receipt cutoff; processing deliberately happens later.
    cutoff = datetime.now(UTC) + timedelta(milliseconds=1)
    closing = repo.request_collection(cutoff=cutoff, complete=True)
    repo.process_slack(value.batch_id)
    with repo.connection() as conn:
        membership = conn.execute('SELECT bucket_id FROM intake_membership').fetchone()
        assert membership['bucket_id'] == closing['bucket_id']


def test_shared_backend_and_bot_credentials_are_rejected(repo):
    same = repo.intake.model_copy(update={'slack_token': repo.settings.api_secret})
    with pytest.raises(ValueError, match='distinct'):
        routers(repo.settings, same)


def test_mocked_live_indexing_reuses_unchanged_chunk_across_revisions(repo, monkeypatch):
    repo.intake = repo.intake.model_copy(update={'encoding_enabled': True})
    request = activate(repo)
    value = batch(request)
    deliver(repo, value); repo.process_slack(value.batch_id)
    models = Settings(embedding_api_key='test-embedding-key')
    calls = []
    original_client = httpx.Client

    def response(req):
        assert req.url.path == '/v1/embeddings'
        assert req.headers['authorization'] == 'Bearer test-embedding-key'
        calls.append(req)
        import json
        body = json.loads(req.content)
        return httpx.Response(200, json={'model': models.embedding_model,
            'data': [{'index': i, 'embedding': [1.] + [0.] * 1535} for i in range(len(body['input']))]})

    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original_client(transport=httpx.MockTransport(response), **kwargs))
    execute(jobs(repo, 'transcript_chunk_embedding')[0]['job_id'], repo=repo, models=models)
    repo.request_collection(cutoff=T0 + timedelta(seconds=120))
    updated = message(updated_at=(T0 + timedelta(seconds=20)).isoformat())
    value2 = batch(repo.requests()[-1], batch_id='same_text_new_revision', messages=[updated])
    deliver(repo, value2); repo.process_slack(value2.batch_id)
    execute(jobs(repo, 'transcript_chunk_embedding')[-1]['job_id'], repo=repo, models=models)
    assert len(calls) == 1
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM intake_revisions WHERE indexing_status='ready'").fetchone()['n'] == 2
        assert len(retrieval.archive(conn, models, False)['sources']) == 1
