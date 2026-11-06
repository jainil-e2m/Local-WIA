"""Selected saved-artifact admission and existing SQL/brief worker orchestration."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.stdout.reconfigure(encoding='utf-8')
from psycopg.types.json import Jsonb
from backend_pipeline.config import Settings
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.repository import ContentRepository,insert
from backend_pipeline.models import RunManifest,StageArtifact,Moment,Angle
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.sql_pipeline import SQLWorker,queue_encoding
from backend_pipeline.storage_sources import reconstruct
from backend_pipeline.weekly import resolve_moment_references
from backend_pipeline.store import JsonStore,canonical_hash
from backend_pipeline import gate_one
from backend_pipeline.briefs import gate_two
from backend_pipeline.briefs.workflow import activate_live,output

ANGLE='angle_1d20dd133d5492c950608290'
ORIGIN='week2-luna-pro-strategic-angles-20261013-a2'
WEEK='week_2026-06-08'
ACTOR='local-cli'
CTA='Want your ads to speak to what actually makes couples choose you? DM us **ADS** to learn how we help wedding pros turn those insights into stronger ad copy and landing page messaging.'
base=StorageSettings.from_env()
assert not base.synthetic
assert not any(getattr(base,k) for k in ('generation_enabled','encoding_enabled','refinement_enabled','brief_enabled','brief_live_enabled','brief_web_enabled'))
store=JsonStore(base.artifact_root)
bundle=store.path('brief-brand-bundles/buying-research-user-approved-hierarchy.json')
storage=base.model_copy(update={'brief_enabled':True,'brief_live_enabled':True,'generation_enabled':True,'encoding_enabled':True,
    'brief_brand_path':bundle,'brief_approvers':(ACTOR,),'brief_editors':(ACTOR,),'brief_max_characters':300000})
models=Settings.from_env().model_copy(update={'request_timeout_seconds':600.0})
assert storage.brief_model=='openai/gpt-6.1-sol'
repo=ContentRepository(storage)
state_path='verification/buying-research-brief-state.json'
if store.path(state_path).exists():
    chosen=store.read_json(state_path).get('authoritative_cutoff')
    if chosen is not None:
        assert chosen in {.78,.85,.90}
        storage.angle_approval_cutoff=chosen

def status(rid):
    with repo.connection() as c:
        run=c.execute('SELECT run_id,status,current_message,error_summary FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()
        jobs=c.execute('SELECT job_id,stage,status,attempt_count,current_message,error_summary,result_refs FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,job_id',(rid,)).fetchall()
        dispatches=c.execute("SELECT event_type,details FROM pipeline_events WHERE run_id=%s AND event_type IN ('brief_provider_dispatch','brief_query_dispatch','brief_cache_reused') ORDER BY created_at",(rid,)).fetchall()
    return {'run':run,'jobs':jobs,'dispatches':dispatches}

def immutable(c):
    result={}
    for t,k in [('transcripts','transcript_id'),('transcript_chunks','chunk_id'),('content_angles','angle_id'),
        ('content_briefs','brief_id'),('content_packs','pack_id'),('content_assets','asset_id'),('calendar_entries','calendar_entry_id')]:
        rows=c.execute(f'SELECT to_jsonb(t) body FROM {t} t ORDER BY {k}').fetchall()
        if t=='content_angles': rows=[r for r in rows if r['body']['angle_id']!=ANGLE]
        if t=='content_briefs': rows=[r for r in rows if r['body']['angle_id']!=ANGLE]
        result[t]={'count':len(rows),'hash':canonical_hash(rows)}
    return result

def compact_status(info):
    return {'run':info['run'],'stages':[{k:j[k] for k in ('stage','status','current_message','error_summary')} for j in info['jobs']],
        'chat_dispatches':sum(v['event_type']=='brief_provider_dispatch' for v in info['dispatches']),
        'query_embedding_batches':sum(v['event_type']=='brief_query_dispatch' for v in info['dispatches'])}

def validated(c):
    original=JsonStore(models.data_root);prefix='experiments/default/runs/'+ORIGIN
    manifest=RunManifest.model_validate(original.read_json(prefix+'/manifest.json'))
    artifact=StageArtifact.model_validate(original.read_json(prefix+'/angle_generation.json'))
    diag=original.read_json(prefix+'/moment_diagnostic.json')
    assert artifact.output_hash==canonical_hash(artifact.output)
    records=repo.frozen_sources(c,WEEK);transcripts,packet,refs=reconstruct(records)
    source_prefix='experiments/default/runs/'+diag['source_run_id']
    directory=original.read_json(source_prefix+'/weekly_packet.json')['artifact_directory']
    raw=[original.read_json(str(p.relative_to(original.root))) for p in original.path(directory+'/sources').glob('*.json')]
    assert {r['source_id']:r['raw_sha256'] for r in raw}=={t.source_id:t.content_hash for t in transcripts}
    received=original.read_json(diag['received_attempt_directory']+'/output.received.json')
    p=Pipeline(models);accepted=[];rejected=[]
    for draft in received['moments']:
        try:
            accepted.extend(p._parse_moments(resolve_moment_references({**received,'moments':[draft]},refs),diag['source_run_id'],transcripts))
        except ValueError as e: rejected.append(str(e))
    assert accepted==[Moment.model_validate(m) for m in original.read_json(prefix+'/moments.json')]
    angles=p._parse_angles(artifact.output,ORIGIN,accepted,artifact=artifact)
    assert angles==[Angle.model_validate(a) for a in original.read_json(prefix+'/candidates.json')]
    a=next(a for a in angles if a.angle_id==ANGLE)
    assert a.title=='Reviews and buying research answer different questions' and a.reader_decision is None
    parent=RunManifest.model_validate(original.read_json(source_prefix+'/manifest.json'))
    assert parent.status=='failed' and manifest.status=='partial' and len(accepted)==5 and len(rejected)==2
    return records,manifest,artifact,diag,parent,a,[m for m in accepted if m.moment_id in a.moment_ids]

action=sys.argv[1]
if action=='admit':
    assert not store.path(state_path).exists(),'Resume existing pilot explicitly'
    with repo.connection() as c:
        before=immutable(c)
        records,manifest,artifact,diag,parent,a,moments=validated(c)
        refs={'transcripts':[{'id':r['transcript_id'],'hash':r['content_hash']} for r in records],
            'synthetic':False,'week_index':2,'mode':'replay','coverage':'accepted_partial_baseline',
            'selected_candidate_only':ANGLE,'file_backed_origin':ORIGIN,'original_extraction_failed':True,
            'validated_partial_moments':5,'rejected_partial_moments':2}
        insert(c,'pipeline_runs',{'run_id':parent.run_id,'week_id':WEEK,'run_scope':'original_extraction','status':'failed',
            'trigger_type':'manual','input_refs':refs,'created_at':parent.created_at,'has_partial_failures':True,
            'error_summary':'Preserved original partial extraction: two quotation failures'},conflict=True)
        insert(c,'pipeline_runs',{'run_id':ORIGIN,'week_id':WEEK,'run_scope':'selected_partial_candidate','status':'queued',
            'trigger_type':'manual','triggered_by':ACTOR,'input_refs':refs,'created_at':manifest.created_at,'has_partial_failures':True,
            'current_message':'User-selected source-valid file candidate; extraction remains partial'},conflict=True)
        repo.save_moments(c,parent.run_id,WEEK,moments,records)
        repo.save_angles(c,WEEK,[a])
        repo.job(c,parent.run_id,'moment_extraction',{'stored_valid_moment_ids':[m.moment_id for m in moments],
            'validated_in_original_file':5,'rejected_count':2,'original_failed_parent':parent.run_id},status='failed')
        repo.job(c,ORIGIN,'angle_generation',{'angle_ids':[ANGLE],'moment_ids':a.moment_ids,
            'artifact_id':artifact.artifact_id,'request_fingerprint':artifact.request_fingerprint,'selected_only':True,
            'validated_original_candidate_count':4,'partial_extraction':True})
        repo.job(c,ORIGIN,'history_admission',{'angle_ids':[ANGLE],'partial':True,'full_week_extraction':False,'actor':ACTOR})
        repo.job(c,ORIGIN,'angle_embedding',{'angle_ids':[ANGLE]},status='waiting')
        repo.event(c,ORIGIN,'selected_file_candidate_admitted','Human selected one source-valid strategic angle for briefing',
            details={'angle_id':ANGLE,'origin_artifact':str(JsonStore(models.data_root).path('experiments/default/runs/'+ORIGIN+'/angle_generation.json')),'original_failed_parent':parent.run_id,'admitted_moment_ids':a.moment_ids})
    state={'angle_id':ANGLE,'origin_run_id':ORIGIN,'cta':CTA,'source_transfer_approved':True,
        'approval_client_date':'2026-10-13','human_reply':'Approve this buying-research brief pipeline',
        'writer_model':storage.brief_model,'research_review_model':models.openrouter_angles_model,
        'limits':{'angle_embedding_requests':1,'query_embedding_batches':3,'queries':12,'chat_calls':10},
        'protected_before':before,'source_valid_partial_candidate':True,'permanent_external_switches':False}
    store.write_json(state_path,state)
    queue_encoding(repo,ORIGIN,'live')
    print(json.dumps({'admitted_angle_id':ANGLE,'origin_run_id':ORIGIN,'next':'encode','partial_parent_preserved':True},indent=2))
elif action=='queue_encode':
    with repo.connection() as c:
        assert c.execute('SELECT 1 FROM content_angles WHERE angle_id=%s AND run_id=%s',(ANGLE,ORIGIN)).fetchone()
        repo.job(c,ORIGIN,'angle_embedding',{'angle_ids':[ANGLE]},status='waiting')
    print(json.dumps(queue_encoding(repo,ORIGIN,'live')))
elif action=='encode':
    state=store.read_json(state_path);w=SQLWorker(storage,models);jid=w.once(run_id=ORIGIN)
    info=status(ORIGIN);print(json.dumps({'job_id':jid,**info},indent=2,default=str))
elif action=='match':
    with repo.connection() as c:
        assert c.execute("SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND stage='angle_embedding' AND status='completed'",(ORIGIN,)).fetchone()
        c.execute("UPDATE pipeline_runs SET status='queued' WHERE run_id=%s",(ORIGIN,))
        repo.job(c,ORIGIN,'angle_matching',{},status='queued')
    w=SQLWorker(storage,models);jid=w.once(run_id=ORIGIN)
    with repo.connection() as c:
        a=c.execute('SELECT selection_status,base_score,adjusted_score,matching_result FROM content_angles WHERE angle_id=%s',(ANGLE,)).fetchone()
    store.write_json('verification/buying-research-angle-matching.json',a,overwrite=True)
    print(json.dumps({'job_id':jid,'selection_status':a['selection_status'],'base_score':a['base_score'],'adjusted_score':a['adjusted_score'],
        'matches':a['matching_result']['history'],'current_batch_flags':a['matching_result']['current_batch_flags']},indent=2,default=str))
elif action=='compare_prepare':
    state=store.read_json(state_path)
    assert not state.get('comparison_run_id'),'Resume existing comparison'
    from backend_pipeline.gate_one import queue_comparison_reassessment
    with repo.connection() as c:
        origin=c.execute('SELECT input_refs FROM pipeline_runs WHERE run_id=%s FOR UPDATE',(ORIGIN,)).fetchone()
        refs={**origin['input_refs'],'workflow':'historical_comparison_v1',
            'generation_contract':'2026-10-13.wia-strategic-discovery.v1','generation_source':'verified_file_partial_pool',
            'upstream_generation_had_historical_prompt':False,'approval_assessment':'separate_comparison_reassessment'}
        c.execute('UPDATE pipeline_runs SET input_refs=%s,updated_at=now() WHERE run_id=%s',(Jsonb(refs),ORIGIN))
        repo.event(c,ORIGIN,'selected_candidate_comparison_policy','Selected file candidate enters current comparison approval policy; original generation artifact is unchanged',
            details={'angle_id':ANGLE,'legacy_matching_preserved':'verification/buying-research-angle-matching.json',
                'authoritative_cutoff':None,'prior_external_generation_has_historical_prompt':False})
        rows=c.execute('SELECT angle_id,content_hash FROM content_angles WHERE angle_id=%s',(ANGLE,)).fetchall()
        queued=queue_comparison_reassessment(repo,c,WEEK,ACTOR,rows)
    state['comparison_run_id']=queued['run_id'];state['approval_workflow']='historical_comparison_v1'
    store.write_json(state_path,state,overwrite=True)
    print(json.dumps(queued,indent=2))
elif action=='compare_stage':
    state=store.read_json(state_path);rid=state['comparison_run_id']
    assert not any(j['status']=='failed' for j in status(rid)['jobs'])
    SQLWorker(storage,models).once(run_id=rid)
    info=status(rid);store.write_json('verification/buying-research-comparison-progress.json',info,overwrite=True)
    final=next((j['result_refs'] for j in info['jobs'] if j['stage']=='angle_final_assessment' and j['status']=='completed'),None)
    print(json.dumps({**compact_status(info),'scenarios':[{'cutoff':s['cutoff'],'counts':s['counts']} for s in (final or {}).get('scenarios',[])],
        'assessment':(final or {}).get('assessments',{}).get(ANGLE)},indent=2,default=str))
elif action=='select_cutoff':
    state=store.read_json(state_path);cutoff=float(sys.argv[2]);assert cutoff in {.78,.85,.90}
    state['authoritative_cutoff']=cutoff;state['cutoff_scope']='This selected brief pilot only; persistent/global policy unchanged'
    state['cutoff_human_reply']=sys.argv[3]
    store.write_json(state_path,state,overwrite=True)
    print(json.dumps({'selected_cutoff':cutoff,'scope':state['cutoff_scope']}))
elif action=='approve_prepare':
    state=store.read_json(state_path)
    assert not state.get('run_id'),'Already queued; resume the existing brief'
    b=json.loads(store.path('brief-brand-bundles/w1-3-user-approved-hierarchy.json').read_text(encoding='utf-8'))
    b['approval_scope']='Human approved reuse of the Founder Voice / Knowledge Base / Savannah hierarchy for this selected buying-research brief on 2026-10-13.'
    bundle.write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf-8')
    with repo.connection() as c: a=c.execute('SELECT content_hash FROM content_angles WHERE angle_id=%s',(ANGLE,)).fetchone()
    approved=gate_one.decide(repo,ANGLE,a['content_hash'],'approved',{'text':CTA},False,
        'Human explicitly selected this WARM thought-shift opportunity and supplied the exact CTA. The client survey/shared spreadsheet workflow is proposed, not delivered/currently offered; no adoption or marketing result is established. Preserve reader_decision=null and the full strategic opportunity. CTA is editorial steer, not evidence of current service scope.',ACTOR)
    rid=approved['brief_run']['run_id'];state['run_id']=rid
    store.write_json(state_path,state,overwrite=True)
    with repo.connection() as c: refs=c.execute('SELECT input_refs FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()['input_refs']
    activate_live(repo,rid,canonical_hash(refs),ACTOR)
    w=SQLWorker(storage,models);w.once(run_id=rid)
    info=status(rid)
    assert next(j for j in info['jobs'] if j['stage']=='brief_prepare')['status']=='completed',info
    with repo.connection() as c: run=c.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()
    data=output(w,run,'brief_prepare')
    print(json.dumps({'run_id':rid,'sources':len(data['archive']['sources']),'chunks':len(data['archive']['chunks']),
        'original_evidence':len(data['evidence']),'prior_angles':len(data['prior']),'writer':storage.brief_model},indent=2))
elif action=='retry_validation':
    state=store.read_json(state_path);rid=state['run_id'];info=status(rid)
    job=next(j for j in info['jobs'] if j['stage']=='brief_validation')
    assert job['status']=='failed' and job['error_summary']=='Grounding review contains unknown claim/evidence IDs'
    with repo.connection() as c:
        repo.event(c,rid,'known_prior_review_reference_fix','Supplied prior-angle IDs accepted only in editorial review findings; factual proof remains original-bound',
            details={'offline_brief_tests_passed':22,'raw_review_unchanged':True,'request_and_schema_contract_unchanged':True,
                'substantive_distinctness_and_permission_findings_preserved':True})
    print(json.dumps(repo.retry(job['job_id'],ACTOR),default=str))
    state['review_reference_recovery']={'failed_job_id':job['job_id'],'offline_tests_passed':22,
        'old_review_raw_preserved':True,'fact_grounding_guard_unchanged':True}
    store.write_json(state_path,state,overwrite=True)
elif action in {'stage','status'}:
    state=store.read_json(state_path);rid=state['run_id']
    if action=='stage':
        assert not any(j['status']=='failed' for j in status(rid)['jobs'])
        SQLWorker(storage,models).once(run_id=rid)
    info=status(rid);store.write_json('verification/buying-research-brief-progress.json',info,overwrite=True)
    print(json.dumps(compact_status(info),indent=2,default=str))
elif action=='export':
    state=store.read_json(state_path);rid=state['run_id'];info=status(rid)
    assert all(j['status']=='completed' for j in info['jobs']),info
    with repo.connection() as c:
        bid=c.execute('SELECT brief_id FROM content_briefs WHERE angle_id=%s ORDER BY created_at DESC LIMIT 1',(ANGLE,)).fetchone()['brief_id']
        after=immutable(c);assert state['protected_before']==after,'Unrelated records changed'
    row=gate_two.get(repo,bid,ACTOR);doc=row['content_body']['document']
    assert row['approval_status']=='pending' and doc['cta']=={'text':CTA} and doc['reader_decision'] is None
    directory=store.path('brief-runs',rid,'exports');directory.mkdir(parents=True,exist_ok=True)
    md=directory/'reviews-and-buying-research-content-brief.md';md.write_text(gate_two.markdown(row),encoding='utf-8')
    store.write_json(f'brief-runs/{rid}/exports/reviews-and-buying-research-content-brief.json',row,overwrite=True)
    costs=store.read_json(f'brief-runs/{rid}/cost_summary.json')
    report={**state,**info,'brief_id':bid,'export':str(md),'blockers':row['blockers'],'findings':row['content_body']['review']['findings'],
        'repair_used':row['content_body']['review']['repair_used'],'retained_evidence':len(row['selected_evidence']),
        'prior_count':len(row['prior_content_context']),'costs':costs,'protected_after':after}
    store.write_json('verification/buying-research-brief-result.json',report,overwrite=True)
    print(json.dumps({k:v for k,v in report.items() if k in {'brief_id','export','blockers','findings','repair_used','retained_evidence','prior_count'}},indent=2,ensure_ascii=False))
    print(json.dumps({'reported_brief_cost_usd':costs['total_new_cost_usd']},indent=2))
else: raise ValueError('Unknown action')
