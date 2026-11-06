"""Bounded operator for the authorized 329 existing chunks; --execute is required.

Only existing Week 1/2 chunk texts may leave through OpenRouter embeddings.
No generation, chunk changes, approvals, research or persistent switch changes.
"""
import argparse
import json
import math
from datetime import datetime, UTC

import httpx
from psycopg import sql
from backend_pipeline.config import Settings
from backend_pipeline.database import check
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.chunk_encoding import queue, contract, provenance, chunk_view, cached_vector, BATCH_SIZE
from backend_pipeline.matching import vector_valid, vector_digest
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.store import canonical_hash, JsonStore

WEEKS = {'week_2026-06-01': 136, 'week_2026-06-08': 193}


def preserved(conn, operational_ids=None):
    data = {}
    for table in ('weeks', 'transcripts', 'transcript_chunks', 'key_moments', 'content_angles',
                  'angle_moments', 'content_briefs', 'content_packs', 'content_assets', 'calendar_entries'):
        expression = "to_jsonb(t)-'embedding'" if table == 'transcript_chunks' else 'to_jsonb(t)'
        rows = [r['body'] for r in conn.execute(sql.SQL('SELECT ' + expression + ' AS body FROM {} t').format(sql.Identifier(table)))]
        data[table] = {'count': len(rows), 'hash': canonical_hash(sorted(rows, key=canonical_hash))}
    if operational_ids is None:
        operational_ids = {t: [r['id'] for r in conn.execute(sql.SQL('SELECT {} AS id FROM {}').format(
            sql.Identifier(column), sql.Identifier(t)))] for t, column in (
                ('pipeline_runs', 'run_id'), ('pipeline_jobs', 'job_id'), ('pipeline_events', 'event_id'))}
    for table, column in (('pipeline_runs', 'run_id'), ('pipeline_jobs', 'job_id'), ('pipeline_events', 'event_id')):
        rows = [r['body'] for r in conn.execute(sql.SQL('SELECT to_jsonb(t) AS body FROM {} t WHERE {}=ANY(%s)').format(
            sql.Identifier(table), sql.Identifier(column)), (operational_ids[table],))]
        data[table] = {'count': len(rows), 'hash': canonical_hash(sorted(rows, key=canonical_hash))}
    return {'tables': data, 'operational_ids': operational_ids}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--retry-failed', action='store_true', help='Explicitly resume failed encoding jobs using saved caches/responses')
    args = parser.parse_args()
    persistent, models = StorageSettings.from_env(), Settings.from_env()
    assert not persistent.synthetic
    assert not any((persistent.generation_enabled, persistent.encoding_enabled, persistent.refinement_enabled,
                    models.live_enabled, models.embeddings_enabled)), 'Persistent switches must remain disabled'
    assert models.embedding_base_url.rstrip('/') == 'https://openrouter.ai/api/v1'
    assert models.embedding_model == 'openai/text-embedding-3-small' and models.embedding_dimensions == 1536
    assert models.embedding_api_key, 'Configured embedding credential is required'
    repo = ContentRepository(persistent)
    digest = contract(models)
    with repo.connection() as conn:
        assert conn.info.dbname == 'atelier' and conn.info.host == '127.0.0.1' and conn.info.port == 15432
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        schema = check(conn)
        rows = conn.execute('SELECT c.*,t.week_id FROM transcript_chunks c JOIN transcripts t USING(transcript_id) WHERE t.week_id=ANY(%s) ORDER BY c.chunk_id', (list(WEEKS),)).fetchall()
        for wid, count in WEEKS.items():
            assert sum(r['week_id'] == wid for r in rows) == count, 'The authorized chunk corpus changed'
        views = [chunk_view(r) for r in rows]
        proof = provenance(conn, digest)
        ready = all(vector_valid(r['embedding']) and proof.get(r['chunk_id'], {}).get('vector_digest') == vector_digest(r['embedding'])
            and all(proof.get(r['chunk_id'], {}).get(k) == chunk_view(r)[k] for k in chunk_view(r)) for r in rows)
        before = preserved(conn)
    endpoint = models.embedding_base_url.rstrip('/') + '/embeddings'
    preflight = {'weeks': WEEKS, 'total_chunks': len(rows), 'input_version': 'exact-chunk-text-v1',
        'model': models.embedding_model, 'dimensions': 1536, 'endpoint': endpoint,
        'maximum_input_utf8_bytes': max(len(r['chunk_text'].encode('utf-8')) for r in rows),
        'batch_size': BATCH_SIZE, 'maximum_requests': sum(math.ceil(n / BATCH_SIZE) for n in WEEKS.values()),
        'already_complete': ready, 'execute': args.execute, 'schema': schema}
    print(json.dumps(preflight), flush=True)
    if not args.execute:
        return
    storage = persistent.model_copy(update={'encoding_enabled': True})
    repo = ContentRepository(storage)
    store = JsonStore(storage.artifact_root)
    operation = datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
    base = 'verification/chunk-embedding-operations/' + operation
    store.write_json(base + '/before.json', {'preflight': preflight, 'preserved': before, 'chunk_views': views})
    calls, runs, seen = [], {}, set()
    permitted = {canonical_hash(r['chunk_text']): r['chunk_text'] for r in rows}
    original_transport = httpx.HTTPTransport.handle_request
    def embeddings_only(transport, request):
        assert str(request.url) == endpoint and request.method == 'POST', 'Only authorized OpenRouter embeddings are allowed'
        payload = json.loads(request.content)
        texts = payload['input']
        assert isinstance(texts, list) and 0 < len(texts) <= BATCH_SIZE
        assert payload['model'] == models.embedding_model and payload['dimensions'] == 1536 and payload['encoding_format'] == 'float'
        hashes = [canonical_hash(text) for text in texts]
        assert all(permitted.get(ih) == text for ih, text in zip(hashes, texts, strict=True)), 'Outbound text is outside the frozen 329 chunks'
        assert not seen.intersection(hashes) and len(set(hashes)) == len(hashes), 'Repeated live input is forbidden'
        assert len(calls) < preflight['maximum_requests'], 'Authorized embedding batch count exceeded'
        seen.update(hashes)
        calls.append({'dispatched_at': datetime.now(UTC).isoformat(), 'inputs': len(texts), 'input_hashes': hashes})
        store.write_json(base + '/dispatches.json', {'calls': calls, 'generation_calls': 0}, overwrite=True)
        print(json.dumps({'embedding_batch': len(calls), 'inputs': len(texts)}), flush=True)
        return original_transport(transport, request)
    httpx.HTTPTransport.handle_request = embeddings_only
    try:
        if not ready:
            worker = SQLWorker(storage, models)
            for wid in WEEKS:
                queued = queue(repo, models, wid, 'live', 'user-authorized-week1-week2-chunk-embedding')
                runs[wid] = queued
                with repo.connection() as conn:
                    status = conn.execute('SELECT status FROM pipeline_jobs WHERE job_id=%s', (queued['job_id'],)).fetchone()['status']
                if status == 'failed' and args.retry_failed:
                    repo.retry(queued['job_id'], 'explicit-chunk-encoding-recovery')
                elif status == 'failed':
                    raise ValueError('An earlier chunk job failed; inspect its saved response and explicitly use --retry-failed')
                worker.once(run_id=queued['run_id'])
                with repo.connection() as conn:
                    job = conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s', (queued['job_id'],)).fetchone()
                    assert job['status'] == 'completed', job['error_summary'] or job['current_message']
                print(json.dumps({'week': wid, 'status': 'completed', 'encoded_chunks': queued['chunk_count']}), flush=True)
    finally:
        httpx.HTTPTransport.handle_request = original_transport
        store.write_json(base + '/dispatches.json', {'calls': calls, 'generation_calls': 0}, overwrite=True)
    with repo.connection() as conn:
        check(conn)
        assert preserved(conn, before['operational_ids']) == before, 'Protected corpus, angles, weeks or earlier execution records changed'
        proof = provenance(conn, digest)
        encoded = conn.execute('SELECT c.*,t.week_id FROM transcript_chunks c JOIN transcripts t USING(transcript_id) WHERE t.week_id=ANY(%s) ORDER BY c.chunk_id', (list(WEEKS),)).fetchall()
        verified, responses = [], set()
        for row in encoded:
            view = chunk_view(row)
            p = proof[row['chunk_id']]
            assert all(p[k] == value for k, value in view.items())
            assert vector_valid(row['embedding']) and p['vector_digest'] == vector_digest(row['embedding'])
            cached = cached_vector(store, p['cache'], digest, view['input_hash'])
            assert cached['vector_digest'] == p['vector_digest']
            responses.add(p['response_artifact'])
            verified.append({**view, 'week_id': row['week_id'], 'dimensions': len(row['embedding']),
                'vector_digest': p['vector_digest'], 'returned_model': p['returned_model'], 'cache': p['cache'],
                'response_artifact': p['response_artifact']})
        cosine = conn.execute('SELECT min(1-(c.embedding <=> c.embedding)) AS minimum,max(1-(c.embedding <=> c.embedding)) AS maximum FROM transcript_chunks c JOIN transcripts t USING(transcript_id) WHERE t.week_id=ANY(%s)', (list(WEEKS),)).fetchone()
        assert abs(cosine['minimum'] - 1) < 1e-6 and abs(cosine['maximum'] - 1) < 1e-6
    usage = [store.read_json(path).get('usage', {}) for path in sorted(responses)]
    report = {'completed_at_utc': datetime.now(UTC).isoformat(), 'status': 'all_existing_chunks_embedded_and_verified',
        'model': models.embedding_model, 'endpoint': endpoint, 'dimensions': 1536, 'contract': digest,
        'weeks': [{'week_id': wid, 'encoded_chunks': sum(v['week_id'] == wid for v in verified)} for wid in WEEKS],
        'verified_chunks': verified, 'operation_runs': runs, 'embedding_dispatches_this_operation': len(calls),
        'generation_calls': 0, 'self_cosine': cosine, 'usage_by_response': usage,
        'prompt_tokens': sum(u.get('prompt_tokens', 0) for u in usage),
        'reported_cost_usd': sum(u['cost'] for u in usage) if usage and all(isinstance(u.get('cost'), (int, float)) for u in usage) else None,
        'source_angle_week_and_downstream_records_preserved': True, 'schema': schema,
        'persistent_external_switches': {'generation': persistent.generation_enabled, 'encoding': persistent.encoding_enabled,
            'refinement': persistent.refinement_enabled, 'legacy_live': models.live_enabled, 'legacy_embeddings': models.embeddings_enabled},
        'retrieval_quality_evaluated': False, 'hybrid_brief_retrieval_implemented': False,
        'operation_artifacts': base}
    store.write_json(base + '/completed.json', report)
    store.write_json('verification/week1-week2-chunk-embedding-readiness.json', report, overwrite=True)
    print(json.dumps({k: report[k] for k in ('status', 'weeks', 'dimensions', 'embedding_dispatches_this_operation',
        'generation_calls', 'prompt_tokens', 'reported_cost_usd', 'source_angle_week_and_downstream_records_preserved', 'persistent_external_switches')}), flush=True)


if __name__ == '__main__':
    main()
