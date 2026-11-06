"""Bounded, human-authorized W1-3 pilot. Never changes persistent switches."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.stdout.reconfigure(encoding='utf-8')
from backend_pipeline.config import Settings
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.repository import ContentRepository
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.store import JsonStore,canonical_hash
from backend_pipeline import gate_one
from backend_pipeline.briefs import gate_two
from backend_pipeline.briefs.workflow import activate_live,output
from backend_pipeline.briefs.runtime import system,compact_dossier
from backend_pipeline.briefs.contracts import BriefDocument,SupportReview
from backend_pipeline.provider import chat_body

ANGLE='angle_ab0db137df928ed4e835dfda'
CTA='Match the landing page per venue for a better client experience.'
ACTOR='local-cli'
base=StorageSettings.from_env()
assert not base.synthetic
assert not any(getattr(base,k) for k in ('generation_enabled','encoding_enabled','refinement_enabled','brief_enabled','brief_live_enabled','brief_web_enabled'))
store=JsonStore(base.artifact_root)
bundle_path=store.path('brief-brand-bundles/w1-3-user-approved-hierarchy.json')
storage=base.model_copy(update={'brief_enabled':True,'brief_live_enabled':True,'generation_enabled':True,
    'encoding_enabled':True,'brief_brand_path':bundle_path,'brief_approvers':(ACTOR,),'brief_editors':(ACTOR,),
    'brief_max_characters':300000})
models=Settings.from_env().model_copy(update={'request_timeout_seconds':600.0})
assert storage.brief_model=='openai/gpt-6.1-sol'
repo=ContentRepository(storage)
state_path='verification/brief-w1-3-pilot-state.json'

def protected(c):
    result={}
    for table,key in [('transcripts','transcript_id'),('transcript_chunks','chunk_id'),('key_moments','moment_id'),
        ('content_angles','angle_id'),('content_packs','pack_id'),('content_assets','asset_id'),('calendar_entries','calendar_entry_id')]:
        rows=c.execute(f'SELECT to_jsonb(t) AS body FROM {table} t ORDER BY {key}').fetchall()
        if table=='content_angles': rows=[r for r in rows if r['body']['angle_id']!=ANGLE]
        result[table]={'count':len(rows),'hash':canonical_hash(rows)}
    return result

def status(rid):
    with repo.connection() as c:
        run=c.execute('SELECT run_id,status,current_message,error_summary FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()
        jobs=c.execute('SELECT job_id,stage,status,current_step,current_message,attempt_count,error_summary,result_refs FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,job_id',(rid,)).fetchall()
        events=c.execute("SELECT event_type,details FROM pipeline_events WHERE run_id=%s AND event_type IN ('brief_provider_dispatch','brief_query_dispatch','brief_cache_reused') ORDER BY created_at",(rid,)).fetchall()
    return {'run':run,'jobs':jobs,'dispatches':events}

action=sys.argv[1]
if action=='prepare':
    assert not store.path(state_path).exists(),'Existing pilot must be resumed explicitly'
    bundle=json.loads(bundle_path.read_text(encoding='utf-8'))
    bundle['approval_scope']='Human approved the guide hierarchy and exact CTA in this chat on 2026-10-12.'
    bundle_path.write_text(json.dumps(bundle,ensure_ascii=False,indent=2),encoding='utf-8')
    with repo.connection() as c:
        before=protected(c)
        a=c.execute('SELECT content_hash,content_body,approval_status FROM content_angles WHERE angle_id=%s',(ANGLE,)).fetchone()
        assert a['content_body']['title']=='Give distinct wedding markets distinct landing-page context'
        assert a['approval_status']=='pending'
        assert c.execute('SELECT count(*) n FROM content_briefs').fetchone()['n']==0
    approved=gate_one.decide(repo,ANGLE,a['content_hash'],'approved',{'text':CTA},False,
        'Human selected W1-3 and approved this exact CTA in chat. Preserve the market-context argument; venue-specific pages are a bounded application, not a measured performance claim.',ACTOR)
    rid=approved['brief_run']['run_id']
    state={'run_id':rid,'angle_id':ANGLE,'cta':CTA,'writer_model':storage.brief_model,'research_review_model':models.openrouter_angles_model,
        'human_authorized':True,'permanent_external_switches':False,'request_character_cap':storage.brief_max_characters,
        'guide_bundle':str(bundle_path),'guide_hash':canonical_hash(bundle),'protected_before':before}
    store.write_json(state_path,state)
    with repo.connection() as c:
        refs=c.execute('SELECT input_refs FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()['input_refs']
    activate_live(repo,rid,canonical_hash(refs),ACTOR)
    worker=SQLWorker(storage,models)
    worker.once(run_id=rid)
    info=status(rid)
    assert next(j for j in info['jobs'] if j['stage']=='brief_prepare')['status']=='completed',info
    with repo.connection() as c: run=c.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()
    prepared=output(worker,run,'brief_prepare')
    state['prepared_counts']={'sources':len(prepared['archive']['sources']),'chunks':len(prepared['archive']['chunks']),
        'original_evidence':len(prepared['evidence']),'prior_angles':len(prepared['prior'])}
    store.write_json(state_path,state,overwrite=True)
    print(json.dumps({'run_id':rid,'prepared':state['prepared_counts'],'writer_model':storage.brief_model,'stage_status':[(j['stage'],j['status']) for j in info['jobs']]},indent=2))
elif action=='stage':
    state=store.read_json(state_path);rid=state['run_id'];before=status(rid)
    assert not any(j['status']=='failed' for j in before['jobs']),before
    worker=SQLWorker(storage,models)
    jid=worker.once(run_id=rid)
    result=status(rid)
    store.write_json('verification/brief-w1-3-pilot-progress.json',result,overwrite=True)
    print(json.dumps({'job_id':jid,**result},ensure_ascii=False,indent=2,default=str))
elif action=='status':
    print(json.dumps(status(store.read_json(state_path)['run_id']),ensure_ascii=False,indent=2,default=str))
elif action=='preflight':
    state=store.read_json(state_path);rid=state['run_id'];worker=SQLWorker(storage,models)
    with repo.connection() as c:
        run=c.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()
        assert state['protected_before']==protected(c)
        a=c.execute('SELECT content_hash,approved_hash,approval_status,selected_cta FROM content_angles WHERE angle_id=%s',(ANGLE,)).fetchone()
        assert a['approval_status']=='approved' and a['content_hash']==a['approved_hash'] and a['selected_cta']=={'text':CTA}
    prepared=output(worker,run,'brief_prepare')
    from backend_pipeline.briefs.contracts import QueryPlan
    from backend_pipeline.briefs.runtime import check_dependencies
    check_dependencies(worker,run)
    packet={'angle':run['input_refs']['angle'],'original_evidence':prepared['evidence'],'gaps':[],
        'existing_queries':[],'remaining_queries':12,'round':0}
    request=chat_body(model=models.openrouter_angles_model,system=system('brief_plan'),
        user=json.dumps(packet,ensure_ascii=False,sort_keys=True,default=str),schema=QueryPlan.model_json_schema(),
        max_tokens=models.llm_completion_tokens,reasoning_effort=models.llm_reasoning_effort,response_format=models.llm_response_format)
    count=len(json.dumps(request,ensure_ascii=False))
    assert count<=storage.brief_max_characters
    lines=['# W1-3 prepared brief input','',run['input_refs']['angle']['body']['title'],'',
        'Approved argument: '+run['input_refs']['angle']['body']['argument'],'','Approved CTA: '+CTA,'',
        'Status: local preparation complete; provider dispatch awaits explicit source-transfer authorization.','',
        'Writer: '+storage.brief_model+'; research and support review: '+models.openrouter_angles_model+'.','',
        'Retrieval archive: 20 stored transcripts / 329 existing compatible vectors; research query vectors are separate.',
        'Prior coverage: eleven other admitted arguments. Their generated state is preserved; none is claimed published.',
        'Guide hierarchy: Founder Voice Guide primary, Knowledge Base supporting, Savannah strategy; exemplars are prepared drafts.',
        'No external web research or Gate 2 approval is enabled for this pilot.','',
        '## Original grounding','']
    for e in prepared['evidence']:
        lines.extend(['### '+e['evidence_id'],'',e['title']+'; original character range '+str(e['start'])+'–'+str(e['end']),
            '',e['excerpt'],'','Qualifications: '+'; '.join(e['qualifications']),''])
    lines.extend(['## Prior arguments',''])
    for p in prepared['prior']:
        lines.extend(['- '+p['angle_id']+': '+p['argument']+' (status: '+p['approval_status']+')'])
    preview=store.path('brief-runs',rid,'exports','w1-3-prepared-input.md');preview.parent.mkdir(parents=True,exist_ok=True)
    preview.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    report={'run_id':rid,'binding_verified':True,'protected_records_unchanged':True,'provider_dispatch_count':len(status(rid)['dispatches']),
        'planner_request_characters':count,'character_cap':storage.brief_max_characters,
        'guide_bundle_characters':len(json.dumps(run['input_refs']['brand'],ensure_ascii=False)),
        'input_preview':str(preview),'full_prepared_artifact':next(j['result_refs']['artifact'] for j in status(rid)['jobs'] if j['stage']=='brief_prepare')}
    store.write_json('verification/brief-w1-3-local-preflight.json',report,overwrite=True)
    print(json.dumps(report,ensure_ascii=False,indent=2))
elif action=='export':
    state=store.read_json(state_path);rid=state['run_id'];info=status(rid)
    assert all(j['status']=='completed' for j in info['jobs']),info
    with repo.connection() as c:
        brief=c.execute('SELECT brief_id FROM content_briefs WHERE angle_id=%s ORDER BY created_at DESC LIMIT 1',(ANGLE,)).fetchone()
        after=protected(c)
        assert state['protected_before']==after,'Unrelated source/content data changed during the pilot'
    row=gate_two.get(repo,brief['brief_id'],ACTOR)
    assert row['approval_status']=='pending'
    assert row['content_body']['document']['cta']=={'text':CTA}
    export_root=store.path('brief-runs',rid,'exports');export_root.mkdir(parents=True,exist_ok=True)
    md=export_root/'w1-3-content-brief.md'
    md.write_text(gate_two.markdown(row),encoding='utf-8')
    store.write_json(f'brief-runs/{rid}/exports/w1-3-content-brief.json',row,overwrite=True)
    costs=store.read_json(f'brief-runs/{rid}/cost_summary.json')
    report={**state,**info,'brief_id':brief['brief_id'],'export_markdown':str(md),'blocking':row['blockers'],
        'review_findings':row['content_body']['review']['findings'],'protected_after':after,'costs':costs,
        'permanent_external_switches':False}
    store.write_json('verification/brief-w1-3-pilot-result.json',report,overwrite=True)
    print(json.dumps({'brief_id':brief['brief_id'],'run_id':rid,'export':str(md),'blockers':row['blockers'],
        'repair_used':row['content_body']['review']['repair_used'],'evidence_count':len(row['selected_evidence']),
        'prior_angles':len(row['prior_content_context']),'costs':costs},ensure_ascii=False,indent=2,default=str))
else:
    raise ValueError('Unknown pilot action')
