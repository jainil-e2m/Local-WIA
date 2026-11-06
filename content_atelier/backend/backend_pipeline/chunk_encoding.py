"""Exact stored-chunk encoding with SQL lineage, bounded batches and cache recovery."""
from datetime import datetime, UTC
from psycopg.types.json import Jsonb

from .config import embedding_contract
from .matching import vector_valid, vector_digest
from .llm import embedding_body, live_provider
from .llm.call import provider_embed
from .llm.runs import LlmRuns
from .repository import insert
from .storage_sources import chunks
from .store import canonical_hash
from .artifacts import store_for

STAGE = 'transcript_chunk_embedding'
VERSION = 'exact-chunk-text-v1'
BATCH_SIZE = 32


def contract(models, *, synthetic=False):
    return canonical_hash({**embedding_contract(models), 'input': VERSION, 'synthetic': synthetic})


def chunk_view(row):
    if canonical_hash({'text': row['chunk_text'], 'passages': row['passage_refs']}) != row['content_hash']:
        raise ValueError('Chunk content integrity failed')
    if not row['chunk_text'].strip() or not row['passage_refs']:
        raise ValueError('Chunk text and original passage references are required')
    # Conservative byte bound: no tokenizer download, truncation, or omitted text.
    if len(row['chunk_text'].encode('utf-8')) > 8191:
        raise ValueError('Chunk exceeds the conservative embedding input limit; review its boundaries')
    return {k: row[k] for k in ('chunk_id', 'transcript_id', 'content_hash')} | {
        'input_hash': canonical_hash(row['chunk_text']),
        'view_hash': canonical_hash([row['chunk_text'], row['passage_refs']])}


def validate_response(raw, count, model):
    if not isinstance(raw, dict) or raw.get('model') not in {model, model.rsplit('/', 1)[-1]}:
        raise ValueError('Embedding response model does not match the requested contract')
    data = raw.get('data')
    if not isinstance(data, list) or len(data) != count:
        raise ValueError('Embedding response batch coverage is incomplete')
    indexed = {}
    for item in data:
        if not isinstance(item, dict):
            raise ValueError('Invalid embedding response item')
        index = item.get('index')
        if type(index) is not int or not 0 <= index < count or index in indexed:
            raise ValueError('Embedding response indices are invalid or duplicated')
        vector = item.get('embedding')
        if not vector_valid(vector):
            raise ValueError('Embedding response has an invalid, zero or non-1536 vector')
        indexed[index] = [float(x) for x in vector]
    return [indexed[i] for i in range(count)]


def provenance(conn, digest):
    proof = {}
    for row in conn.execute("""SELECT result_refs FROM pipeline_jobs
        WHERE stage=%s AND status IN ('completed','running','failed') ORDER BY updated_at,job_id""", (STAGE,)):
        data = row['result_refs'] or {}
        if data.get('contract') == digest:
            for value in data.get('vectors', []):
                proof[value['chunk_id']] = value
    return proof


def queue(repo, models, week_id, mode='cached', actor='local-cli'):
    if mode not in {'cached', 'live'}:
        raise ValueError('Chunk encoding mode must be cached or live')
    if mode == 'live' and not repo.settings.encoding_enabled:
        raise ValueError('External chunk encoding permission is disabled')
    digest = contract(models, synthetic=repo.settings.synthetic)
    with repo.connection() as conn:
        if not conn.execute('SELECT 1 FROM weeks WHERE week_id=%s FOR UPDATE', (week_id,)).fetchone():
            raise ValueError('Week not found')
        sources = repo.frozen_sources(conn, week_id)
        if not sources:
            raise ValueError('No admitted sources for this week')
        rows = conn.execute('SELECT * FROM transcript_chunks WHERE transcript_id=ANY(%s) AND is_current ORDER BY chunk_id',
            ([s['transcript_id'] for s in sources],)).fetchall()
        # Version 1 chunks are recomputed from the source view; version 2 chunks (plan 1.B6) carry their own header and roles,
        # so their text and passage references are checked against their content hash by chunk_view below.
        resegmented = {r['transcript_id'] for r in rows if r['segmentation_version'] != 'v1'}
        expected = {c['chunk_id']: c for s in sources if s['transcript_id'] not in resegmented for c in chunks(s)}
        if not rows or set(expected) != {r['chunk_id'] for r in rows if r['transcript_id'] not in resegmented}:
            raise ValueError('Prepared chunks do not cover the admitted source views')
        for row in rows:
            if row['transcript_id'] not in resegmented and any(row[k] != expected[row['chunk_id']][k] for k in ('chunk_text', 'passage_refs', 'content_hash')):
                raise ValueError('Prepared chunk differs from its original source view')
        refs = {'transcripts': [{'id': s['transcript_id'], 'hash': s['content_hash'],
            'view_hash': canonical_hash([s['original_text'], s['passage_map'], s['source_metadata']])} for s in sources],
            'chunks': [chunk_view(r) for r in rows], 'contract': digest, 'input_version': VERSION,
            'synthetic': repo.settings.synthetic, 'mode': 'synthetic' if repo.settings.synthetic else 'replay',
            'encoding_mode': mode, 'week_index': sources[0]['source_metadata']['week_index']}
        intent = canonical_hash([week_id, refs])
        rid, jid = 'chunk_run_' + intent[:24], 'chunk_job_' + intent[:24]
        from .settings_store import snapshot_refs
        refs = {**refs, **snapshot_refs('encoding', models=models, storage=repo.settings, conn=conn)}  # not part of the intent
        insert(conn, 'pipeline_runs', {'run_id': rid, 'week_id': week_id, 'run_scope': 'transcript_encoding',
            'trigger_type': 'manual', 'triggered_by': actor, 'input_refs': refs}, conflict=True)
        insert(conn, 'pipeline_jobs', {'job_id': jid, 'run_id': rid, 'week_id': week_id, 'stage': STAGE,
            'idempotency_key': 'chunk-encoding:' + intent, 'input_hash': intent,
            'progress_details': {'dependencies': [], 'encoding_mode': mode},
            'total_units': len(rows), 'current_message': 'Stored transcript chunks queued for encoding'}, conflict=True)
        # This auxiliary run must not replace the weekly angle run or its review state.
        return {'run_id': rid, 'job_id': jid, 'chunk_count': len(rows), 'contract': digest}


def frozen_rows(conn, run, *, lock=False):
    expected = run['input_refs']['chunks']
    rows = conn.execute('SELECT * FROM transcript_chunks WHERE chunk_id=ANY(%s) ORDER BY chunk_id' +
        (' FOR UPDATE' if lock else ''), ([e['chunk_id'] for e in expected],)).fetchall()
    if len(rows) != len(expected) or [chunk_view(r) for r in rows] != expected:
        raise ValueError('Frozen chunk inputs changed; create a new encoding intent')
    return rows


def cached_vector(store, path, digest, ih):
    data = store.read_json(path)
    vector = data.get('vector')
    if (data.get('contract') != digest or data.get('input_hash') != ih or not vector_valid(vector)
        or data.get('vector_digest') != vector_digest(vector)):
        raise ValueError('Chunk encoding cache integrity failed')
    return data


def recovered_response(store, job_id, fingerprint, body, model):
    for key in store.attempt_files(f'chunk-encoding-attempts/{job_id}', fingerprint, 'response.raw.json'):
        request = store.read_json(key.rsplit('/', 1)[0] + '/request.json')
        if request.get('body') != body:
            raise ValueError('Saved batch request differs from the frozen embedding input')
        raw = store.read_json(key)
        if raw.get('error'):
            continue
        validate_response(raw, len(body['input']), model)
        return raw, key
    return None


def execute(worker, job, run):
    digest = contract(worker.models, synthetic=worker.storage.synthetic)
    if run['input_refs']['contract'] != digest:
        raise ValueError('Frozen chunk embedding contract changed')
    mode = run['input_refs']['encoding_mode']
    if mode == 'live' and not worker.storage.encoding_enabled:
        raise ValueError('External chunk encoding permission is disabled')
    store = store_for(worker.storage)
    with worker.repo.connection() as conn:
        rows = frozen_rows(conn, run)
        proof = provenance(conn, digest)
        current = worker.repo.guard(conn, job)
        previous = current['result_refs'] or {}
    vectors = {v['chunk_id']: v for v in previous.get('vectors', [])}
    reused = previous.get('cache_reused', 0)
    requests = previous.get('embedding_dispatches', 0)
    for start in range(0, len(rows), BATCH_SIZE):
        group = rows[start:start + BATCH_SIZE]
        prepared, missing = {}, {}
        for row in group:
            view = chunk_view(row)
            ih = view['input_hash']
            key = canonical_hash({'contract': digest, 'input_hash': ih})
            path = f'chunk-encoding/{key}.json'
            p = proof.get(row['chunk_id'], {})
            if row['embedding'] is not None:
                if (not vector_valid(row['embedding']) or any(p.get(k) != view[k] for k in view)
                    or p.get('vector_digest') != vector_digest(row['embedding'])):
                    raise ValueError('Existing chunk vector lacks compatible provenance; explicit re-encoding is required')
                prepared[ih] = {'vector': [float(x) for x in row['embedding']], 'cache': p['cache'],
                    'returned_model': p['returned_model'], 'response_artifact': p['response_artifact']}
            elif store.exists(path):
                data = cached_vector(store, path, digest, ih)
                prepared[ih] = {**data, 'cache': path}
                reused += 1
            else:
                missing[ih] = row['chunk_text']
        if missing:
            if mode != 'live' and not worker.storage.synthetic:
                raise ValueError('Compatible chunk vectors are not cached; live encoding must be explicitly enabled')
            fingerprint = canonical_hash({'contract': digest, 'inputs': list(missing)})
            base = f'chunk-encoding-attempts/{job["job_id"]}/{job["attempt_count"]}/{fingerprint}'
            body = embedding_body(model=worker.models.embedding_model, text=list(missing.values()), dimensions=1536)
            store.write_json(base + '/request.json', {'endpoint': worker.models.embedding_base_url.rstrip('/') + '/embeddings',
                'contract': digest, 'body': body, 'input_hashes': list(missing)})
            recovered = recovered_response(store, job['job_id'], fingerprint, body, worker.models.embedding_model)
            response_path = base + '/response.raw.json'
            if recovered:
                raw, response_path = recovered
                reused += len(missing)
            else:
                provider = worker.provider
                if not worker.storage.synthetic:
                    provider = live_provider(worker.models, storage=worker.storage, chat=False,
                        on_response=lambda _, raw: store.write_json(base + '/response.raw.json', raw))
                if not provider or not callable(getattr(provider, 'embed_many', None)):
                    raise ValueError('A batch embedding provider is required')
                requests += 1
                with worker.repo.connection() as conn:
                    worker.repo.guard(conn, job)
                    worker.check_source_views(conn, run)
                    frozen_rows(conn, run)
                    conn.execute('UPDATE pipeline_jobs SET result_refs=%s,updated_at=now() WHERE job_id=%s',
                        (Jsonb({'contract': digest, 'vectors': list(vectors.values()), 'cache_reused': reused,
                            'embedding_dispatches': requests, 'chunk_count': len(rows), 'input_version': VERSION}), job['job_id']))
                    worker.repo.event(conn, run['run_id'], 'chunk_embedding_dispatch',
                        f'Embedding batch of {len(missing)} exact transcript chunk texts', job=job,
                        details={'fingerprint': fingerprint, 'input_count': len(missing), 'request_artifact': base + '/request.json'})
                raw = provider_embed(provider, LlmRuns.for_storage(worker.storage), model=worker.models.embedding_model, texts=list(missing.values()), fingerprint=fingerprint,
                    context={'run_id': run['run_id']})
                store.write_json(response_path, raw)
            received = validate_response(raw, len(missing), worker.models.embedding_model)
            for ih, vector in zip(missing, received, strict=True):
                path = 'chunk-encoding/' + canonical_hash({'contract': digest, 'input_hash': ih}) + '.json'
                data = {'contract': digest, 'input_hash': ih, 'vector': vector,
                    'vector_digest': vector_digest(vector), 'returned_model': raw['model'],
                    'response_artifact': response_path, 'usage': raw.get('usage'),
                    'created_at': datetime.now(UTC).isoformat()}
                store.write_json(path, data)
                prepared[ih] = {**cached_vector(store, path, digest, ih), 'cache': path}
        with worker.repo.connection() as conn:
            worker.repo.guard(conn, job)
            worker.check_source_views(conn, run)
            fresh = {r['chunk_id']: r for r in frozen_rows(conn, run, lock=True)}
            for row in group:
                view = chunk_view(row)
                data = prepared[view['input_hash']]
                existing = fresh[row['chunk_id']]['embedding']
                if existing is not None and (not vector_valid(existing) or vector_digest(existing) != vector_digest(data['vector'])):
                    raise ValueError('A chunk vector changed concurrently; refusing to overwrite it')
                conn.execute('UPDATE transcript_chunks SET embedding=%s,embedding_model=%s WHERE chunk_id=%s AND content_hash=%s',
                    (data['vector'], worker.models.embedding_model, row['chunk_id'], row['content_hash']))
                vectors[row['chunk_id']] = {**view, 'vector_digest': vector_digest(data['vector']),
                    'cache': data['cache'], 'response_artifact': data['response_artifact'],
                    'returned_model': data['returned_model']}
            result = {'contract': digest, 'input_version': VERSION, 'chunk_count': len(rows),
                'vectors': list(vectors.values()), 'cache_reused': reused, 'embedding_dispatches': requests}
            conn.execute("""UPDATE pipeline_jobs SET result_refs=%s,completed_units=%s,total_units=%s,
                current_step='embedding_chunks',current_message=%s,updated_at=now() WHERE job_id=%s""",
                (Jsonb(result), len(vectors), len(rows), f'{len(vectors)}/{len(rows)} transcript chunks encoded', job['job_id']))
            worker.repo.event(conn, run['run_id'], 'chunk_batch_stored',
                f'{len(vectors)}/{len(rows)} transcript chunk vectors stored', job=job,
                details={'completed': len(vectors), 'total': len(rows), 'contract': digest})
    with worker.repo.connection() as conn:
        worker.check_source_views(conn, run)
        for row in frozen_rows(conn, run):
            p = vectors.get(row['chunk_id'], {})
            if not vector_valid(row['embedding']) or p.get('vector_digest') != vector_digest(row['embedding']):
                raise ValueError('Stored chunk vector verification failed')
        worker.repo.finish(conn, job, result, message=f'All {len(rows)} transcript chunks encoded and verified')
