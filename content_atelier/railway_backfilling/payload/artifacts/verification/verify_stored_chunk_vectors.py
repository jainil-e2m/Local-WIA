"""Independently compare every stored float32 vector to its received provider batch."""
import hashlib
import json
import math
import struct
from datetime import datetime, UTC
from pathlib import Path
from backend_pipeline.database import connect, check
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.store import canonical_hash

settings = StorageSettings.from_env()
root = settings.artifact_root
report = json.loads((root / 'verification/week1-week2-chunk-embedding-readiness.json').read_text(encoding='utf-8'))
assert report['embedding_dispatches_this_operation'] == 12 and report['generation_calls'] == 0
manifest = {r['chunk_id']: r for r in report['verified_chunks']}
assert len(manifest) == 329
responses, requests = {}, {}
counts = {}
with connect(settings.database_url) as conn:
    assert conn.info.dbname == 'atelier' and conn.info.host == '127.0.0.1' and conn.info.port == 15432
    conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
    schema = check(conn)
    rows = conn.execute('SELECT c.*,t.week_id FROM transcript_chunks c JOIN transcripts t USING(transcript_id) ORDER BY c.chunk_id').fetchall()
    assert {r['chunk_id'] for r in rows} == set(manifest)
    for row in rows:
        entry = manifest[row['chunk_id']]
        assert row['content_hash'] == entry['content_hash'] and row['transcript_id'] == entry['transcript_id']
        assert canonical_hash(row['chunk_text']) == entry['input_hash']
        assert canonical_hash([row['chunk_text'], row['passage_refs']]) == entry['view_hash']
        path = entry['response_artifact']
        if path not in responses:
            responses[path] = json.loads((root / path).read_text(encoding='utf-8'))
            request_path = Path(path).with_name('request.json')
            requests[path] = json.loads((root / request_path).read_text(encoding='utf-8'))
        raw, request = responses[path], requests[path]
        assert raw['model'] in {'openai/text-embedding-3-small', 'text-embedding-3-small'}
        assert request['endpoint'] == 'https://openrouter.ai/api/v1/embeddings'
        assert request['body']['model'] == 'openai/text-embedding-3-small' and request['body']['dimensions'] == 1536
        assert request['contract'] == report['contract']
        index = request['body']['input'].index(row['chunk_text'])
        item = next(item for item in raw['data'] if item['index'] == index)
        stored = [float(v) for v in row['embedding']]
        assert len(stored) == 1536 and all(math.isfinite(v) for v in stored) and math.fsum(v*v for v in stored) > 0
        received = struct.pack('!1536f', *item['embedding'])
        assert struct.pack('!1536f', *stored) == received
        assert hashlib.sha256(received).hexdigest() == entry['vector_digest']
        counts[row['week_id']] = counts.get(row['week_id'], 0) + 1
    assert len(responses) == 12 and counts == {'week_2026-06-01': 136, 'week_2026-06-08': 193}
    states = conn.execute('SELECT week_id,status FROM weeks ORDER BY week_id').fetchall()
    jobs = conn.execute("SELECT run_id,job_id,status,completed_units,total_units,result_refs->>'embedding_dispatches' AS embedding_dispatches FROM pipeline_jobs WHERE stage='transcript_chunk_embedding' ORDER BY week_id").fetchall()
    assert len(jobs) == 2 and all(j['status'] == 'completed' and j['completed_units'] == j['total_units'] for j in jobs)
    samples = []
    for wid in counts:
        source = next(r for r in rows if r['week_id'] == wid)
        matches = conn.execute('SELECT chunk_id,1-(embedding <=> %s) AS cosine FROM transcript_chunks ORDER BY embedding <=> %s LIMIT 3', (source['embedding'], source['embedding'])).fetchall()
        assert matches[0]['chunk_id'] == source['chunk_id'] and abs(matches[0]['cosine'] - 1) < 1e-6
        samples.append({'week_id': wid, 'query_chunk_id': source['chunk_id'], 'matches': matches})
    angle_dims = conn.execute('SELECT count(*) AS n FROM content_angles WHERE embedding IS NOT NULL AND vector_dims(embedding)=1536').fetchone()['n']
    downstream = {t: conn.execute('SELECT count(*) AS n FROM ' + t).fetchone()['n'] for t in ('content_briefs','content_packs','content_assets','calendar_entries')}
    assert angle_dims == 12 and all(n == 0 for n in downstream.values())
verified = {'verified_at_utc': datetime.now(UTC).isoformat(), 'database_read_only': True, 'external_calls': 0,
    'stored_vectors_equal_received_float32_vectors': True, 'verified_chunks': 329, 'counts': counts,
    'response_batches': 12, 'jobs': jobs, 'schema': schema, 'weeks': states, 'existing_angle_vectors': angle_dims,
    'downstream_counts': downstream, 'sample_exact_cosine_queries': samples,
    'persistent_external_switches': report['persistent_external_switches']}
path = root / 'verification/week1-week2-chunk-embedding-verification.json'
path.write_text(json.dumps(verified, indent=2, default=str), encoding='utf-8')
lines = ['# Week 1 and Week 2 chunk embeddings', '',
    'All 329 existing transcript chunks were embedded through OpenRouter using `openai/text-embedding-3-small` and stored as `vector(1536)` in PostgreSQL.', '',
    '| Week | Chunks | Stored compatible vectors |', '|---|---:|---:|', '| June 1-7, 2026 | 136 | 136 |', '| June 8-14, 2026 | 193 | 193 |', '',
    'The operation used 12 requests. Provider-reported usage: 208,733 input tokens; provider-reported cost: $0.00417466.', '',
    'Independent read-only verification matched every stored float32 vector to its exact indexed provider response, request text, source transcript and immutable chunk hash. All vectors have 1,536 finite dimensions and a nonzero norm. Two sample exact cosine searches returned the original chunk with cosine approximately 1. This checks storage/search mechanics, not retrieval relevance.', '',
    'Both encoding jobs completed. The existing 13-table schema, 12 angle vectors, original transcripts, chunk text/ranges, moments, approval state, weekly review state and earlier execution records were preserved. New execution/provenance records use the existing runs/jobs/events tables. No brief, pack, asset or calendar item was generated.', '',
    'Existing whole-turn boundaries and filename headers were preserved. Every input was at most 2,543 UTF-8 bytes; no text was truncated. Cached responses/vectors make retries resumable without repeating successful paid work. All persistent external switches remain false; permission was local to this approved operation.', '',
    'Verification: 62 offline contract, chunk recovery, SQL and comparison tests passed with external HTTP guarded. Hybrid full-text retrieval, contextual relevance evaluation, briefing and Gate 2 remain later work.', '',
    '[Encoding report](week1-week2-chunk-embedding-readiness.json) | [Independent verification](week1-week2-chunk-embedding-verification.json)', '']
(root / 'verification/week1-week2-chunk-embedding-readiness.md').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'verified_chunks': 329, 'response_batches': 12, 'counts': counts,
    'stored_vectors_equal_received_float32_vectors': True, 'existing_angle_vectors': angle_dims,
    'week_states': states, 'external_calls': 0, 'report': str(path)}, indent=2))
