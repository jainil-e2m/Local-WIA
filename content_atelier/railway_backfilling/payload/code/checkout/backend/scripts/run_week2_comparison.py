"""Bounded Week 2 live test. Default is read-only preparation; --execute dispatches.

Existing admitted June 8-14 corpus only, OpenRouter Luna generation and Small vectors.
At most one dispatch per generative stage. No automatic retries or downstream briefs.
Permissions are process-local; saved env switches/credentials are never edited.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from psycopg import sql
from psycopg.types.json import Jsonb
import httpx

from backend_pipeline.config import Settings
from backend_pipeline.storage_config import StorageSettings, encoding_contract
from backend_pipeline.repository import ContentRepository
from backend_pipeline.database import check
from backend_pipeline.storage_sources import reconstruct
from backend_pipeline.matching import history, vector_valid, vector_digest, vector_provenance
from backend_pipeline.prompts import weekly_moment_prompt
from backend_pipeline.weekly import meeting_inventory
from backend_pipeline.contracts import CompactMomentResponse, signature_from_fields
from backend_pipeline.provider import chat_body
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.angle_workflow import WORKFLOW, STAGES
from backend_pipeline.store import JsonStore, canonical_hash

WEEK = 'week_2026-06-08'


def protected_state(conn):
    state = {}
    for table in ('transcripts','transcript_chunks','content_briefs','content_packs','content_assets','calendar_entries'):
        rows = [r['body'] for r in conn.execute(sql.SQL('SELECT to_jsonb(t) AS body FROM {} t').format(sql.Identifier(table)))]
        state[table] = canonical_hash(sorted(rows,key=canonical_hash))
    for table in ('weeks','key_moments','content_angles'):
        rows = [r['body'] for r in conn.execute(sql.SQL("SELECT to_jsonb(t) AS body FROM {} t WHERE week_id='week_2026-06-01'").format(sql.Identifier(table)))]
        state['week1_'+table] = canonical_hash(sorted(rows,key=canonical_hash))
    rows = [r['body'] for r in conn.execute("SELECT to_jsonb(am) AS body FROM angle_moments am JOIN content_angles a USING(angle_id) WHERE a.week_id='week_2026-06-01'")]
    state['week1_angle_moments'] = canonical_hash(sorted(rows,key=canonical_hash))
    return state


def export_review(repo, storage, run_id, folder):
    # Exercise the protected export contract locally; no HTTP server or provider call.
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend_pipeline.storage_api import router
    app = FastAPI(); app.include_router(router(storage))
    with TestClient(app) as client:
        headers = {'Authorization':'Bearer '+storage.api_secret,'X-Atelier-Actor':'user-authorized-week2-test'}
        json_response = client.get(f'/storage/runs/{run_id}/comparison',headers=headers)
        csv_response = client.get(f'/storage/runs/{run_id}/comparison.csv',headers=headers)
        assert json_response.status_code==200 and csv_response.status_code==200
        data = json_response.json()
    (folder/'comparison.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    (folder/'comparison.csv').write_text(csv_response.text,encoding='utf-8')
    report = data['report']
    candidates = {a['angle_id']:a for a in data['candidates']}
    lines = ['# Week 2 live angle comparison', '', f'Run: `{run_id}`', '',
             'Provisional comparison results. No authoritative cutoff or Gate 1 approval. Quality is a model self-assessment.', '',
             '| Historical cosine cutoff | Initial qualified | Final qualified | Recovered | Original fallbacks | Candidates with batch flags |',
             '|---|---:|---:|---:|---:|---:|']
    for scenario in report['scenarios']:
        c = scenario['counts']
        lines.append(f"| < {scenario['cutoff']:.2f} | {c['initial_qualified']} | {c['final_qualified']} | {c['recovered']} | {c['retained_original_fallbacks']} | {c['current_batch_flagged']} |")
    for number,family in enumerate(report['families'],1):
        lines.extend(['',f"## {number}. {candidates[family['original_id']]['content_body']['title']}", '',family['explanation']])
        for label,mid in [('Original',family['original_id']),('Refinement',family.get('replacement_id'))]:
            if not mid: continue
            a = candidates[mid]; m = report['assessments'][mid]; b = a['content_body']
            lines.extend(['',f'### {label}',f'ID: `{mid}`',
                          f"Baseline quality: {m['base_score']:.2f}; maximum historical cosine: {m['max_historical_cosine']:.6f}; ranking score: {m['adjusted_score']:.2f}."])
            for field in ('audience','tension','argument','take','mechanism','reader_decision'):
                lines.extend(['',f"**{field.replace('_',' ').capitalize()}:** {b[field]}"])
            lines.extend(['',f"Qualifications: {'; '.join(b['qualifiers']) or 'None recorded'}",f"Handling: {'; '.join(b['risks'])}",
                          f"Moment IDs: {', '.join(a['moment_ids'])}"])
        for scenario in report['scenarios']:
            selected = next(f for f in scenario['families'] if f['original_id']==family['original_id'])
            lines.append(f"Cutoff {scenario['cutoff']:.2f}: selected `{selected['selected_id'] or 'none'}`; original reasons {selected['original_reasons']}; refinement reasons {selected['replacement_reasons']}.")
    (folder/'review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--resume-run',help='Resume a known run with completed stages and dispatch limits preserved')
    args = parser.parse_args()
    persistent = StorageSettings.from_env(); models = Settings.from_env()
    assert not persistent.synthetic and persistent.api_secret
    assert not persistent.generation_enabled and not persistent.encoding_enabled and not persistent.refinement_enabled
    assert models.openrouter_base_url.rstrip('/')=='https://openrouter.ai/api/v1'
    assert models.embedding_base_url.rstrip('/')=='https://openrouter.ai/api/v1'
    assert models.openrouter_moments_model==models.openrouter_angles_model=='openai/gpt-6-luna'
    assert models.embedding_model=='openai/text-embedding-3-small' and models.embedding_dimensions==1536
    assert models.openrouter_moments_key and models.openrouter_angles_key and models.embedding_api_key
    repo = ContentRepository(persistent); store = JsonStore(persistent.artifact_root)
    with repo.connection() as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        assert conn.info.dbname=='atelier'
        schema = check(conn)
        records = repo.frozen_sources(conn,WEEK)
        assert len(records)==11 and all(r['source_metadata']['week_index']==2 for r in records)
        before = protected_state(conn)
        archive = history(conn,{'created_at':datetime.now(UTC),'week_id':WEEK,
                                'input_refs':{'synthetic':False,'workflow':WORKFLOW,'transcripts':[{'id':r['transcript_id'],'hash':r['content_hash']} for r in records]}},[])
        assert len(archive)==6 and all(a['week_id']=='week_2026-06-01' for a in archive)
        proof = vector_provenance(conn,encoding_contract(models,synthetic=False))
        assert all(vector_valid(a['embedding']) and a['embedding_input_hash']==canonical_hash(signature_from_fields(a['content_body']))
                   and proof.get((a['angle_id'],a['embedding_input_hash']),{}).get('vector_digest')==vector_digest(a['embedding']) for a in archive)
    transcripts,packet,refs = reconstruct(records)
    system,user = weekly_moment_prompt(packet,meeting_inventory(refs))
    request = chat_body(model=models.openrouter_moments_model,system=system,user=user,schema=CompactMomentResponse.model_json_schema(),
                        max_tokens=models.llm_completion_tokens,reasoning_effort=models.llm_reasoning_effort,response_format=models.llm_response_format)
    preflight = {'week_id':WEEK,'workflow':WORKFLOW,'source_count':11,'passage_count':sum(len(t.spans) for t in transcripts),
                 'packet_utf8_bytes':len(packet.encode()),'request_message_utf8_bytes':sum(len(m['content'].encode()) for m in request['messages']),
                 'local_input_limits_enabled':models.llm_input_limits_enabled,'request_output_cap':models.llm_completion_tokens,
                 'history_vectors':6,'history_ids':[a['angle_id'] for a in archive],
                 'chat_endpoint':models.openrouter_base_url.rstrip('/')+'/chat/completions',
                 'embedding_endpoint':models.embedding_base_url.rstrip('/')+'/embeddings',
                 'chat_model':models.openrouter_angles_model,'embedding_model':models.embedding_model,'dimensions':1536,
                 'schema':schema,'persistent_switches':{'generation':False,'encoding':False,'refinement':False},'external_calls':0}
    store.write_json('verification/week2-live-preflight.json',preflight,overwrite=True)
    print(json.dumps(preflight),flush=True)
    if not args.execute: return
    storage = persistent.model_copy(update={'generation_enabled':True,'encoding_enabled':True,'refinement_enabled':True})
    models = models.model_copy(update={'live_enabled':True})
    repo = ContentRepository(storage); worker = SQLWorker(storage,models)
    if args.resume_run:
        with repo.connection() as conn:
            run=conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(args.resume_run,)).fetchone()
            assert run and run['week_id']==WEEK and run['input_refs'].get('workflow')==WORKFLOW and run['input_refs']['mode']=='live'
        run_id=args.resume_run
    else:
        run = repo.submit(WEEK,'live',actor='user-authorized-week2-test',workflow=WORKFLOW)
        run_id = run['run_id']
    relative = f'experiments/sql/runs/{run_id}'
    folder = store.path(relative); folder.mkdir(parents=True,exist_ok=True)
    store.write_json(relative+'/operator-preflight.json',{'prepared_at':datetime.now(UTC).isoformat(),**preflight,'protected_state':before})
    if args.resume_run:
        original_preflight=store.read_json(relative+'/operator-preflight.json')
        assert original_preflight['protected_state']==before
        before=original_preflight['protected_state']
    store.write_json('verification/week2-live-latest.json',{'run_id':run_id,'artifact_directory':relative},overwrite=True)
    with repo.connection() as conn:
        for job in conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s AND stage IN ('angle_initial_embedding','angle_refined_embedding') FOR UPDATE",(run_id,)):
            conn.execute('UPDATE pipeline_jobs SET progress_details=%s WHERE job_id=%s',(Jsonb({**job['progress_details'],'encoding_mode':'live'}),job['job_id']))
        repo.event(conn,run_id,'bounded_live_test_resumed' if args.resume_run else 'bounded_live_test','User authorized Week 2 generation, encoding and one optional refinement; comparison only',
                   details={'workflow':WORKFLOW,'generation_model':models.openrouter_angles_model,'embedding_model':models.embedding_model})
    state = {'stage':None,'embedding_inputs':set()}; calls = []; chat_counts = Counter()
    if args.resume_run:
        previous=store.read_json(relative+'/outbound-dispatches.json')
        calls=list(previous['calls']);chat_counts.update(previous['chat_dispatches'])
        assert chat_counts['moment_extraction']==1 and chat_counts['angle_generation']==1
        with repo.connection() as conn:
            failed_jobs=conn.execute("SELECT job_id,stage,status FROM pipeline_jobs WHERE run_id=%s AND status IN ('failed','waiting')",(run_id,)).fetchall()
        for failed_job in failed_jobs:
            assert failed_job['stage']=='angle_generation' and failed_job['status']=='failed'
            recovered=store.read_json(relative+'/citation-recovery/report.json')
            cached=store.find_artifact(recovered['request_fingerprint'])
            assert cached and cached['artifact_id']==recovered['recovered_artifact_id']
            repo.retry(failed_job['job_id'],'user-authorized-week2-cached-citation-retry')
    handle = httpx.HTTPTransport.handle_request
    def guarded(transport, request):
        assert request.method=='POST'
        payload = json.loads(request.content); stage = state['stage']; url = str(request.url)
        if url==preflight['chat_endpoint']:
            assert stage in {'moment_extraction','angle_generation','angle_refinement'}
            assert payload['model']==(models.openrouter_moments_model if stage=='moment_extraction' else models.openrouter_angles_model)
            assert chat_counts[stage]==0, 'No automatic second dispatch of a generative stage'
            chat_counts[stage]+=1
        elif url==preflight['embedding_endpoint']:
            assert stage in {'angle_initial_embedding','angle_refined_embedding'}
            assert payload['model']==models.embedding_model and payload['dimensions']==1536
            assert payload['input'] in state['embedding_inputs'], 'Embedding input is outside this run cohort'
        else:
            raise AssertionError('Unapproved outbound destination')
        calls.append({'stage':stage,'endpoint':url,'model':payload['model'],'dispatched_at':datetime.now(UTC).isoformat()})
        print(json.dumps({'dispatch':len(calls),'stage':stage,'model':payload['model']}),flush=True)
        return handle(transport,request)
    httpx.HTTPTransport.handle_request = guarded
    try:
        for stage in STAGES:
            state['stage']=stage
            with repo.connection() as conn:
                existing=conn.execute('SELECT status FROM pipeline_jobs WHERE run_id=%s AND stage=%s',(run_id,stage)).fetchone()
            if existing['status']=='completed':
                print(json.dumps({'stage_reused':stage,'run_id':run_id}),flush=True)
                continue
            if stage in {'angle_initial_embedding','angle_refined_embedding'}:
                with repo.connection() as conn:
                    source_stage = 'angle_generation' if stage=='angle_initial_embedding' else 'angle_refinement'
                    ids = worker.stage_output(conn,run_id,source_stage)['angle_ids']
                    state['embedding_inputs'] = {signature_from_fields(a['content_body']) for a in conn.execute('SELECT content_body FROM content_angles WHERE angle_id=ANY(%s)',(ids,))}
            print(json.dumps({'stage_started':stage,'run_id':run_id}),flush=True)
            assert worker.once(run_id=run_id), 'No claimable stage; inspect persisted job state'
            with repo.connection() as conn:
                job = conn.execute('SELECT job_id,status,current_message,error_summary FROM pipeline_jobs WHERE run_id=%s AND stage=%s',(run_id,stage)).fetchone()
            print(json.dumps({'stage_finished':stage,**job}),flush=True)
            if job['status']!='completed':
                raise RuntimeError(f"{stage}: {job['error_summary'] or job['current_message']}")
        data = export_review(repo,storage,run_id,folder)
        with repo.connection() as conn:
            assert protected_state(conn)==before, 'Protected Week 1/source/downstream records changed'
            check(conn)
            jobs = conn.execute('SELECT stage,status,result_refs FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,job_id',(run_id,)).fetchall()
            assert all(j['status']=='completed' for j in jobs)
            ids = data['report']['candidate_ids']
            candidates = conn.execute('SELECT selection_status,approval_status FROM content_angles WHERE angle_id=ANY(%s)',(ids,)).fetchall()
            assert all(a['selection_status']=='candidate' and a['approval_status']!='approved' for a in candidates)
        summary = {'run_id':run_id,'status':'comparison_complete','workflow':WORKFLOW,'real_data':True,
                   'initial_angles':len(data['report']['families']),'refinements':sum(bool(f.get('replacement_id')) for f in data['report']['families']),
                   'refinement_targets':sum(bool(f.get('targeted')) for f in data['report']['families']),
                   'scenarios':[{'cutoff':s['cutoff'],'counts':s['counts']} for s in data['report']['scenarios']],
                   'chat_dispatches':dict(chat_counts),'embedding_dispatches':sum(c['endpoint']==preflight['embedding_endpoint'] for c in calls),
                   'protected_records_unchanged':True,'approval_disabled':True,'briefs_generated':0,'persistent_switches':preflight['persistent_switches']}
        store.write_json(relative+'/live-summary.json',summary)
        print(json.dumps(summary),flush=True)
    finally:
        httpx.HTTPTransport.handle_request = handle
        store.write_json(relative+'/outbound-dispatches.json',{'run_id':run_id,'calls':calls,'chat_dispatches':dict(chat_counts)},overwrite=True)


if __name__=='__main__':
    main()
