"""Offline contract/recovery tests and actual pgvector storage in atelier_test only."""
import copy
import json
from datetime import date

import pytest
from backend_pipeline.tests.test_sql_storage import setup, URL
from backend_pipeline.chunk_encoding import queue, validate_response, provenance, contract, chunk_view
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.provider import FakeProvider
from backend_pipeline.matching import vector_digest, vector_valid
from backend_pipeline.store import canonical_hash


MODEL = 'text-embedding-3-small'
WEEK = 'week_2026-06-01'
sql_test = pytest.mark.skipif(not URL, reason='Requires isolated atelier_test database')


def response():
    return {'model': MODEL, 'data': [
        {'index': 1, 'embedding': [0., 1.] + [0.] * 1534},
        {'index': 0, 'embedding': [1.] + [0.] * 1535}]}


def test_response_preserves_input_order():
    vectors = validate_response(response(), 2, 'openai/' + MODEL)
    assert vectors[0][0] == 1 and vectors[1][1] == 1


@pytest.mark.parametrize('fault', ['model', 'missing', 'duplicate', 'boolean_index', 'outside', 'dimensions', 'zero', 'nan'])
def test_response_rejects_incompatible_or_incomplete_batches(fault):
    raw = response()
    if fault == 'model': raw['model'] = 'different-model'
    elif fault == 'missing': raw['data'].pop()
    elif fault == 'duplicate': raw['data'][0]['index'] = 0
    elif fault == 'boolean_index': raw['data'][0]['index'] = True
    elif fault == 'outside': raw['data'][0]['index'] = 2
    elif fault == 'dimensions': raw['data'][0]['embedding'] = [1.]
    elif fault == 'zero': raw['data'][0]['embedding'] = [0.] * 1536
    else: raw['data'][0]['embedding'][0] = float('nan')
    with pytest.raises(ValueError):
        validate_response(raw, 2, MODEL)


def test_chunk_input_is_exact_and_never_truncated():
    row = {'chunk_id': 'chunk', 'transcript_id': 'source', 'chunk_text': 'Exact original.\n',
           'passage_refs': [{'passage_id': 'p', 'start': 0, 'end': 16}]}
    row['content_hash'] = canonical_hash({'text': row['chunk_text'], 'passages': row['passage_refs']})
    assert chunk_view(row)['input_hash'] == canonical_hash(row['chunk_text'])
    row['chunk_text'] = 'a' * 8192
    row['content_hash'] = canonical_hash({'text': row['chunk_text'], 'passages': row['passage_refs']})
    with pytest.raises(ValueError, match='limit'):
        chunk_view(row)


class BatchProvider(FakeProvider):
    def __init__(self):
        super().__init__()
        self.calls = []

    def embed_many(self, *, texts, fingerprint):
        self.calls.append(texts)
        return {'model': MODEL, 'usage': {'prompt_tokens': len(texts)}, 'data': [
            {'index': i, 'embedding': self.embed(text=text, fingerprint=fingerprint)[0]}
            for i, text in reversed(list(enumerate(texts)))]}


@sql_test
def test_bounded_encoding_all_chunks_and_idempotent_reuse(setup):
    repo, models, folder = setup
    large = folder / 'week1' / 'large.vtt'
    large.write_text('WEBVTT\n\n' + '\n\n'.join(
        f'{i+1}\n00:{i//60:02}:{i%60:02}.000 --> 00:{(i+1)//60:02}:{(i+1)%60:02}.000\nAlice: Evidence {i}. ' + 'meaning ' * 250
        for i in range(65)), encoding='utf-8')
    repo.admit(folder / 'week1', date(2026, 6, 1), 1)
    with repo.connection() as conn:
        before = conn.execute('SELECT to_jsonb(w) AS body FROM weeks w ORDER BY week_id').fetchall()
    provider = BatchProvider()
    worker = SQLWorker(repo.settings, models, provider=provider)
    queued = queue(repo, models, WEEK)
    assert queue(repo, models, WEEK) == queued
    worker.once(run_id=queued['run_id'])
    assert [len(c) for c in provider.calls] == [32, 32, 2]
    with repo.connection() as conn:
        job = conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s', (queued['job_id'],)).fetchone()
        assert job['status'] == 'completed'
        assert job['completed_units'] == job['total_units'] == 66
        rows = conn.execute('SELECT c.* FROM transcript_chunks c JOIN transcripts t USING(transcript_id) WHERE t.week_id=%s', (WEEK,)).fetchall()
        proof = provenance(conn, contract(models, synthetic=True))
        assert all(vector_valid(r['embedding']) and vector_digest(r['embedding']) == proof[r['chunk_id']]['vector_digest'] for r in rows)
        assert conn.execute('SELECT to_jsonb(w) AS body FROM weeks w ORDER BY week_id').fetchall() == before
        assert conn.execute('SELECT count(*) AS n FROM content_angles').fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) AS n FROM content_briefs').fetchone()['n'] == 0
    assert worker.once(run_id=queued['run_id']) is None
    another = queue(repo, models, WEEK, 'live') if repo.settings.encoding_enabled else None
    assert another is None
    repo.settings.encoding_enabled = True
    another = queue(repo, models, WEEK, 'live')
    worker.once(run_id=another['run_id'])
    assert len(provider.calls) == 3


@sql_test
@pytest.mark.parametrize('remove_cache', [False, True])
def test_post_response_sql_failure_recovers_without_paid_redispatch(setup, monkeypatch, remove_cache):
    repo, models, folder = setup
    provider = BatchProvider()
    worker = SQLWorker(repo.settings, models, provider=provider)
    queued = queue(repo, models, WEEK)
    check = worker.check_source_views
    checks = 0
    def fail_commit(conn, run):
        nonlocal checks
        checks += 1
        if checks == 2:
            raise ValueError('Injected failure after received vector and before SQL commit')
        return check(conn, run)
    monkeypatch.setattr(worker, 'check_source_views', fail_commit)
    worker.once(run_id=queued['run_id'])
    with repo.connection() as conn:
        assert conn.execute('SELECT status FROM pipeline_jobs WHERE job_id=%s', (queued['job_id'],)).fetchone()['status'] == 'failed'
        assert conn.execute('SELECT count(*) AS n FROM transcript_chunks WHERE embedding IS NOT NULL').fetchone()['n'] == 0
    if remove_cache:
        for path in repo.settings.artifact_root.joinpath('chunk-encoding').glob('*.json'):
            path.unlink()
    monkeypatch.setattr(worker, 'check_source_views', check)
    repo.retry(queued['job_id'], 'offline-test')
    worker.once(run_id=queued['run_id'])
    assert len(provider.calls) == 1
    with repo.connection() as conn:
        job = conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s', (queued['job_id'],)).fetchone()
        assert job['status'] == 'completed'
        assert job['result_refs']['embedding_dispatches'] == 1
        assert job['result_refs']['cache_reused'] == 1


@sql_test
def test_changed_chunk_or_contract_fails_without_provider_dispatch(setup):
    repo, models, _ = setup
    queued = queue(repo, models, WEEK)
    changed = models.model_copy(update={'embedding_model': 'different-model'})
    provider = BatchProvider()
    SQLWorker(repo.settings, changed, provider=provider).once(run_id=queued['run_id'])
    assert provider.calls == []
    repo.retry(queued['job_id'], 'offline-test')
    with repo.connection() as conn:
        conn.execute("UPDATE transcript_chunks SET chunk_text='changed' WHERE transcript_id IN (SELECT transcript_id FROM transcripts WHERE week_id=%s)", (WEEK,))
    SQLWorker(repo.settings, models, provider=provider).once(run_id=queued['run_id'])
    assert provider.calls == []
    with repo.connection() as conn:
        assert conn.execute('SELECT status FROM pipeline_jobs WHERE job_id=%s', (queued['job_id'],)).fetchone()['status'] == 'failed'


@sql_test
def test_existing_unproven_vector_is_not_silently_overwritten(setup):
    repo, models, _ = setup
    with repo.connection() as conn:
        conn.execute('UPDATE transcript_chunks SET embedding=%s', ([1.] + [0.] * 1535,))
    queued = queue(repo, models, WEEK)
    provider = BatchProvider()
    SQLWorker(repo.settings, models, provider=provider).once(run_id=queued['run_id'])
    assert provider.calls == []
    with repo.connection() as conn:
        job = conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s', (queued['job_id'],)).fetchone()
        assert job['status'] == 'failed' and 'provenance' in job['error_summary']
