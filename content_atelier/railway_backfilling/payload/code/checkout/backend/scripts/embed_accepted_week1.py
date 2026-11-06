"""Explicitly authorized embedding of the accepted six Luna angles, and nothing else.

Run from backend with PYTHONPATH=. Only --execute can dispatch embedding requests.
Permissions apply to this process; no credential or capability env file is edited.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from psycopg import sql
import httpx

from backend_pipeline.config import Settings
from backend_pipeline.storage_config import StorageSettings, encoding_contract
from backend_pipeline.repository import ContentRepository
from backend_pipeline.database import check
from backend_pipeline.import_history import LUNA_RUN
from backend_pipeline.contracts import signature_from_fields
from backend_pipeline.matching import vector_valid, vector_digest, vector_provenance, history
from backend_pipeline.sql_pipeline import SQLWorker, queue_encoding
from backend_pipeline.store import JsonStore, canonical_hash


def preserved(conn):
    rows = conn.execute("SELECT (to_jsonb(a)-'embedding'-'embedding_input_hash') AS body FROM content_angles a WHERE week_id='week_2026-06-01' ORDER BY angle_id").fetchall()
    facts = {'angles':canonical_hash([r['body'] for r in rows])}
    for table in ('transcripts','transcript_chunks','key_moments','angle_moments','content_briefs','content_packs','content_assets','calendar_entries'):
        data = [r['body'] for r in conn.execute(sql.SQL('SELECT to_jsonb(t) AS body FROM {} t').format(sql.Identifier(table)))]
        facts[table] = {'count':len(data),'hash':canonical_hash(sorted(data,key=canonical_hash))}
    week2 = conn.execute("SELECT to_jsonb(w) AS body FROM weeks w WHERE week_id='week_2026-06-08'").fetchone()
    facts['week2'] = canonical_hash(week2['body'])
    return facts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    persistent = StorageSettings.from_env()
    models = Settings.from_env()
    assert not persistent.synthetic
    assert not persistent.generation_enabled and not persistent.refinement_enabled
    assert models.embedding_dimensions==1536
    assert models.embedding_base_url.rstrip('/')=='https://openrouter.ai/api/v1'
    assert models.embedding_model=='openai/text-embedding-3-small'
    assert models.embedding_api_key, 'Configured embedding credential is missing'
    # User authorization permits this bounded encoding operation only.
    storage = persistent.model_copy(update={'encoding_enabled':True})
    repo = ContentRepository(storage)
    contract = encoding_contract(models,synthetic=False)
    store = JsonStore(storage.artifact_root)
    with repo.connection() as conn:
        assert conn.info.dbname=='atelier', 'Only the established Atelier database is allowed'
        schema = check(conn)
        run = conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(LUNA_RUN,)).fetchone()
        assert run and run['week_id']=='week_2026-06-01' and run['has_partial_failures']
        assert run['input_refs']['coverage']=='accepted_partial_baseline' and not run['input_refs']['synthetic']
        generation = conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation' AND status='completed'",(LUNA_RUN,)).fetchone()['result_refs']
        admitted = conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='history_admission' AND status='completed'",(LUNA_RUN,)).fetchone()['result_refs']
        expected = set(generation['angle_ids'])
        assert len(expected)==6 and expected==set(admitted['angle_ids'])
        angles = conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s) ORDER BY angle_id',(sorted(expected),)).fetchall()
        assert len(angles)==6 and all(a['week_id']=='week_2026-06-01' for a in angles)
        signatures = {signature_from_fields(a['content_body']) for a in angles}
        assert len(signatures)==6
        before = preserved(conn)
        proof = vector_provenance(conn,contract)
        already_complete = all(vector_valid(a['embedding']) and a['embedding_input_hash']==canonical_hash(signature_from_fields(a['content_body']))
                               and proof.get((a['angle_id'],a['embedding_input_hash']),{}).get('vector_digest')==vector_digest(a['embedding']) for a in angles)
    print(json.dumps({'run_id':LUNA_RUN,'accepted_angles':6,'model':models.embedding_model,'dimensions':1536,
                      'already_complete':already_complete,'execute':args.execute}),flush=True)
    if not args.execute:
        return
    if already_complete:
        print(json.dumps({'status':'already_ready_for_week2_history','verified_angles':6,
                          'embedding_dispatches_this_operation':0}),flush=True)
        return
    store.write_json('verification/week1-embedding-before.json',{'captured_at':datetime.now(UTC).isoformat(),
                     'preserved':before,'angle_ids':sorted(expected),'schema':schema},overwrite=True)
    calls = []
    expected_url = models.embedding_base_url.rstrip('/')+'/embeddings'
    handle = httpx.HTTPTransport.handle_request
    def embedding_only(transport, request):
        assert str(request.url)==expected_url and request.method=='POST', 'Only the authorized embedding endpoint is allowed'
        payload = json.loads(request.content)
        assert payload['input'] in signatures and payload['model']==models.embedding_model and payload['dimensions']==1536
        assert len(calls)<6, 'This operation permits at most six embedding dispatches'
        calls.append({'input_hash':canonical_hash(payload['input']),'dispatched_at':datetime.now(UTC).isoformat()})
        print(json.dumps({'embedding_dispatch':len(calls),'input_hash':calls[-1]['input_hash']}),flush=True)
        return handle(transport,request)
    httpx.HTTPTransport.handle_request = embedding_only
    try:
        if not already_complete:
            queued = queue_encoding(repo,LUNA_RUN,'live','user-authorized-week1-embedding')
            worker = SQLWorker(storage,models)
            assert worker.once(run_id=LUNA_RUN)==queued['job_id']
    finally:
        httpx.HTTPTransport.handle_request = handle
        store.write_json('verification/week1-embedding-dispatches.json',{'run_id':LUNA_RUN,'calls':calls,
                         'generation_dispatches':0,'refinement_dispatches':0},overwrite=True)
    with repo.connection() as conn:
        job = conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s AND stage='angle_embedding'",(LUNA_RUN,)).fetchone()
        assert job['status']=='completed', job['error_summary'] or job['current_message']
        assert not job['result_refs']['missing'] and job['result_refs']['contract']==contract
        rows = conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s) ORDER BY angle_id',(sorted(expected),)).fetchall()
        proof = vector_provenance(conn,contract)
        verified = []
        for a in rows:
            ih = canonical_hash(signature_from_fields(a['content_body']))
            assert a['embedding_input_hash']==ih and vector_valid(a['embedding'])
            digest = vector_digest(a['embedding'])
            assert proof[(a['angle_id'],ih)]['vector_digest']==digest
            cosine = conn.execute('SELECT 1-(embedding <=> embedding) AS cosine FROM content_angles WHERE angle_id=%s',(a['angle_id'],)).fetchone()['cosine']
            assert abs(float(cosine)-1)<1e-6
            verified.append({'angle_id':a['angle_id'],'content_hash':a['content_hash'],'input_hash':ih,'vector_digest':digest,
                             'dimensions':len(a['embedding']),'first_generated_at':a['first_generated_at'].isoformat(),'self_cosine':float(cosine)})
        assert preserved(conn)==before, 'Preserved content/evidence or Week 2 state changed'
        check(conn)
        eligible = history(conn,{'created_at':datetime.now(UTC),'week_id':'week_2026-06-08',
                                 'input_refs':{'synthetic':False,'workflow':'historical_comparison_v1','transcripts':[]}},[])
        assert {a['angle_id'] for a in eligible}==expected
        assert all(a['partial'] for a in eligible)
        week = conn.execute("SELECT status FROM weeks WHERE week_id='week_2026-06-01'").fetchone()
    provenance = []
    for a in verified:
        key=canonical_hash({'contract':contract,'input_hash':a['input_hash']})
        cached=store.read_json(f'encoding/{key}.json')
        raw=cached.get('metadata',{}).get('raw',{})
        assert raw.get('model') in {models.embedding_model,'text-embedding-3-small'}
        provenance.append({'angle_id':a['angle_id'],'returned_model':raw['model'],'usage':raw.get('usage'),
                           'encoding_cache':f'encoding/{key}.json'})
    report = {'completed_at':datetime.now(UTC).isoformat(),'run_id':LUNA_RUN,'job_id':job['job_id'],'status':'ready_for_week2_history',
              'model':models.embedding_model,'endpoint':expected_url,'dimensions':1536,'contract':contract,
              'verified_angles':verified,'provenance':provenance,'embedding_dispatches':len(calls),
              'cache_reused':job['result_refs']['cache_reused'],'generation_dispatches':0,'refinement_dispatches':0,
              'history_eligible':6,'accepted_partial_baseline_preserved':True,'original_content_and_evidence_preserved':True,
              'week2_unchanged':True,'schema':schema,'week1_status':week['status'],
              'persistent_switches':{'generation':persistent.generation_enabled,'encoding':persistent.encoding_enabled,'refinement':persistent.refinement_enabled}}
    store.write_json('verification/week1-embedding-readiness.json',report,overwrite=True)
    print(json.dumps({'status':report['status'],'verified_angles':6,'embedding_dispatches':len(calls),
                     'week1_status':week['status'],'week2_unchanged':True,'persistent_switches':report['persistent_switches']}),flush=True)


if __name__=='__main__':
    main()
