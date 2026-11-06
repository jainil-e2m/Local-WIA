"""Read-only real-corpus audit; writes only a private verification report."""
from collections import Counter, defaultdict
from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path

import httpx
from backend_pipeline.config import Settings
from backend_pipeline.database import connect, check
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.storage_sources import capture, chunks, reconstruct
from backend_pipeline.store import canonical_hash


def deny_outbound(*args, **kwargs):
    raise AssertionError('External HTTP is forbidden during this read-only audit')


httpx.HTTPTransport.handle_request = deny_outbound
httpx.AsyncHTTPTransport.handle_async_request = deny_outbound
storage = StorageSettings.from_env()
models = Settings.from_env()
assert not storage.synthetic
assert not any((storage.generation_enabled, storage.encoding_enabled,
                storage.refinement_enabled, models.live_enabled, models.embeddings_enabled))
report = {'verified_at_utc': datetime.now(UTC).isoformat(), 'database': 'atelier',
          'database_read_only': True, 'external_calls': 0, 'weeks': [], 'errors': [],
          'persistent_external_switches': {'generation': storage.generation_enabled,
              'encoding': storage.encoding_enabled, 'refinement': storage.refinement_enabled,
              'legacy_live': models.live_enabled, 'legacy_embeddings': models.embeddings_enabled}}


def require(condition, message):
    if not condition:
        report['errors'].append(message)


with connect(storage.database_url) as conn:
    assert conn.info.dbname == 'atelier' and conn.info.host == '127.0.0.1' and conn.info.port == 15432
    conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
    assert conn.execute("SELECT current_setting('transaction_read_only') AS value").fetchone()['value'] == 'on'
    report['schema'] = check(conn)
    report['extensions'] = conn.execute('SELECT extname, extversion FROM pg_extension ORDER BY extname').fetchall()
    report['chunk_indexes'] = conn.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='transcript_chunks' ORDER BY indexname").fetchall()
    report['chunk_columns'] = [r['column_name'] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='transcript_chunks' ORDER BY ordinal_position")]
    all_chunks = conn.execute('SELECT * FROM transcript_chunks ORDER BY transcript_id,chunk_id').fetchall()
    chunks_by_source = defaultdict(list)
    for row in all_chunks:
        chunks_by_source[row['transcript_id']].append(row)
    report['global_chunks'] = len(all_chunks)
    report['global_embedded_chunks'] = sum(c['embedding'] is not None for c in all_chunks)
    report['orphan_chunks'] = conn.execute('SELECT count(*) AS n FROM transcript_chunks c LEFT JOIN transcripts t USING(transcript_id) WHERE t.transcript_id IS NULL').fetchone()['n']
    require(report['orphan_chunks'] == 0, 'Orphan transcript chunks exist')

    for week_index, week_id, expected_sources in ((1, 'week_2026-06-01', 9), (2, 'week_2026-06-08', 11)):
        week = conn.execute('SELECT week_id,week_start,week_end,status FROM weeks WHERE week_id=%s', (week_id,)).fetchone()
        assert week is not None, f'Missing admitted week {week_id}'
        sources = conn.execute("SELECT * FROM transcripts WHERE week_id=%s ORDER BY (source_metadata->>'file_order')::int,transcript_id", (week_id,)).fetchall()
        paths = sorted(p for p in (models.transcript_root / f'week{week_index}').rglob('*') if p.is_file() and p.suffix.lower() in {'.txt', '.vtt', '.webvtt'})
        require(len(sources) == expected_sources, f'{week_id}: unexpected stored source count')
        require(len(paths) == len(sources), f'{week_id}: on-disk corpus size differs')
        captured = {r['transcript_id']: r for r in (capture(p, week_index, i) for i, p in enumerate(paths, 1))}
        require(set(captured) == {s['transcript_id'] for s in sources}, f'{week_id}: on-disk and admitted source IDs differ')
        details = []
        for source in sources:
            sid = source['transcript_id']
            stored = chunks_by_source[sid]
            local = captured.get(sid)
            require(local is not None, f'{sid}: source file missing or changed')
            if local is not None:
                for field in ('source_type', 'upstream_id', 'title', 'original_text', 'content_hash', 'passage_map', 'source_metadata'):
                    require(source[field] == local[field], f'{sid}: source field mismatch: {field}')
            archive_path = storage.artifact_root / 'source-originals' / (source['content_hash'] + '.original')
            require(archive_path.is_file(), f'{sid}: original byte archive missing')
            if archive_path.is_file():
                raw = archive_path.read_bytes()
                require(hashlib.sha256(raw).hexdigest() == source['content_hash'], f'{sid}: archived raw hash mismatch')
                normalized = raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
                require(normalized == source['original_text'], f'{sid}: SQL original differs from archived original')
            expected_chunks = {c['chunk_id']: c for c in chunks(source)}
            require(set(expected_chunks) == {c['chunk_id'] for c in stored}, f'{sid}: missing or extra chunks')
            require(bool(stored), f'{sid}: no chunks')
            passages = {p['passage_id']: p for p in source['passage_map']}
            require(len(passages) == len(source['passage_map']), f'{sid}: duplicate original passage IDs')
            coverage = Counter()
            body_sizes = []
            long_whole_turns = 0
            for chunk in stored:
                cid = chunk['chunk_id']
                expected = expected_chunks.get(cid)
                if expected is not None:
                    for field in ('chunk_text', 'passage_refs', 'content_hash'):
                        require(chunk[field] == expected[field], f'{cid}: deterministic chunk mismatch: {field}')
                require(canonical_hash({'text': chunk['chunk_text'], 'passages': chunk['passage_refs']}) == chunk['content_hash'], f'{cid}: content hash mismatch')
                require(bool(chunk['passage_refs']), f'{cid}: empty passage references')
                ordinals = []
                body = []
                for ref in chunk['passage_refs']:
                    p = passages.get(ref['passage_id'])
                    require(p is not None, f'{cid}: reference outside parent transcript')
                    if p is None:
                        continue
                    coverage[ref['passage_id']] += 1
                    ordinals.append(p['ordinal'])
                    require(ref['start'] == p['start'] and ref['end'] == p['end'], f'{cid}: original passage range mismatch')
                    require(0 <= ref['start'] < ref['end'] <= len(source['original_text']), f'{cid}: invalid range')
                    body.append(source['original_text'][ref['start']:ref['end']])
                require(not ordinals or ordinals == list(range(ordinals[0], ordinals[0] + len(ordinals))), f'{cid}: non-consecutive or unordered passages')
                expected_text = 'Source: ' + source['title'] + '\n' + '\n'.join(body)
                require(chunk['chunk_text'] == expected_text, f'{cid}: text does not round-trip to originals')
                body_size = sum(len(p) for p in body)
                body_sizes.append(body_size)
                if body_size > 2400:
                    long_whole_turns += 1
                    require(len(body) == 1, f'{cid}: oversized chunk is not a single whole turn')
            require(set(coverage) == set(passages), f'{sid}: original passage coverage incomplete')
            require(all(n == 1 for n in coverage.values()), f'{sid}: duplicate passage coverage')
            embedded = [c for c in stored if c['embedding'] is not None]
            dims = Counter(len(c['embedding']) for c in embedded)
            details.append({'transcript_id': sid, 'title': source['title'], 'passages': len(passages),
                'chunks': len(stored), 'embedded_chunks': len(embedded), 'embedding_dimensions': dict(dims),
                'passages_referenced': len(coverage), 'passage_reference_count': sum(coverage.values()),
                'chunk_body_characters_min': min(body_sizes, default=0), 'chunk_body_characters_max': max(body_sizes, default=0),
                'long_single_turn_chunks': long_whole_turns, 'occurrence_date_known': source['occurred_at'] is not None})
        # Revalidate the calibrated reader's entire original passage view, without a provider call.
        _, packet, reference_map = reconstruct(sources)
        angles = conn.execute("SELECT angle_id,embedding_input_hash,vector_dims(embedding) AS dimensions FROM content_angles WHERE week_id=%s ORDER BY angle_id", (week_id,)).fetchall()
        jobs = conn.execute("SELECT job_id,stage,status,current_message,result_refs FROM pipeline_jobs WHERE week_id=%s AND (stage ILIKE '%%chunk%%' OR stage ILIKE '%%segment%%') ORDER BY created_at", (week_id,)).fetchall()
        report['weeks'].append({**week, 'week_index': week_index, 'transcripts': len(sources),
            'passages': sum(s['passages'] for s in details), 'chunks': sum(s['chunks'] for s in details),
            'embedded_chunks': sum(s['embedded_chunks'] for s in details),
            'unembedded_chunks': sum(s['chunks'] - s['embedded_chunks'] for s in details),
            'all_sources_chunked': all(s['chunks'] > 0 for s in details),
            'originals_and_chunks_hash': canonical_hash([[{k: s[k] for k in ('transcript_id', 'original_text', 'passage_map', 'content_hash', 'source_metadata')} for s in sources], [{k: c[k] for k in ('chunk_id', 'transcript_id', 'chunk_text', 'passage_refs', 'content_hash')} for s in sources for c in chunks_by_source[s['transcript_id']]]]),
            'reconstructed_packet_utf8_bytes': len(packet.encode('utf-8')), 'reconstructed_passages': len(reference_map),
            'angle_count': len(angles), 'embedded_angles': sum(a['dimensions'] is not None for a in angles),
            'angle_embedding_dimensions': dict(Counter(a['dimensions'] for a in angles if a['dimensions'] is not None)),
            'chunk_jobs': jobs, 'transcript_details': details})
    report['downstream_counts'] = {t: conn.execute('SELECT count(*) AS n FROM ' + t).fetchone()['n'] for t in ('content_briefs', 'content_packs', 'content_assets', 'calendar_entries')}

report['source_chunk_integrity_passed'] = not report['errors']
report['brief_semantic_retrieval_ready'] = bool(all(w['embedded_chunks'] == w['chunks'] and w['chunks'] > 0 for w in report['weeks'])) and not report['errors']
report['chunking_policy_observed'] = {'body_target_characters': 2400, 'gap_split_milliseconds': 90000,
    'whole_turns': True, 'single_oversize_turn_preserved': True, 'inter_chunk_overlap': False,
    'context_header': 'Source: <original filename>', 'fixed_token_windows': False}
path = storage.artifact_root / 'verification' / 'week1-week2-transcript-chunk-readiness.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print(json.dumps({'report': str(path), 'source_chunk_integrity_passed': report['source_chunk_integrity_passed'],
    'brief_semantic_retrieval_ready': report['brief_semantic_retrieval_ready'], 'external_calls': 0,
    'weeks': [{k: w[k] for k in ('week_id', 'transcripts', 'passages', 'chunks', 'embedded_chunks', 'unembedded_chunks', 'embedded_angles', 'angle_embedding_dimensions')} for w in report['weeks']],
    'errors': report['errors']}, indent=2))
assert not report['errors'], 'Source/chunk integrity audit failed; see report'
