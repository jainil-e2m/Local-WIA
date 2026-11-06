from datetime import datetime,UTC
from psycopg.types.json import Jsonb
from ..repository import insert,identifier
from ..store import canonical_hash,JsonStore
from .. import retrieval
from .contracts import WORKFLOW,STAGES,Dossier,QueryPlan,GradeResponse,BriefDocument,SupportReview,EvidenceItem
from .inputs import angle_packet,anchors,assert_packet,verify_evidence
from .runtime import brand_bundle,call,query_vectors,compact_dossier,execution_contract

def queue_in_transaction(repo,conn,angle_id,actor,mode='replay',*,revision=None,instructions=None,added_evidence=None):
    if not repo.settings.brief_enabled: raise ValueError('Brief workflow is not enabled')
    if mode not in {'replay','live','synthetic'}: raise ValueError('Unknown brief execution mode')
    if mode=='synthetic' and not repo.settings.synthetic: raise ValueError('Synthetic briefing requires isolated test database')
    if mode=='live' and not (repo.settings.generation_enabled and repo.settings.brief_live_enabled):
        raise ValueError('External brief generation is disabled')
    packet=angle_packet(conn,angle_id)
    bundle=brand_bundle(repo.settings) if revision else None
    intent=canonical_hash([WORKFLOW,angle_id,packet['approved_hash']] if not revision else
        [WORKFLOW,angle_id,packet['approved_hash'],revision,instructions,added_evidence,mode,bundle['hash']])
    rid='brief_run_'+intent[:24]
    existing=conn.execute('SELECT input_refs,status FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()
    if existing: return {'run_id':rid,'status':existing['status']}
    bundle=bundle or brand_bundle(repo.settings)
    refs={'workflow':WORKFLOW,'angle':packet,'brand':bundle,'mode':mode,'synthetic':repo.settings.synthetic,
        'revision_of':revision,'instructions':instructions,'added_evidence':added_evidence or [],'queued_by':actor}
    if revision:
        active=conn.execute("SELECT 1 FROM pipeline_runs WHERE input_refs->>'revision_of'=%s AND status IN ('queued','running')",(revision,)).fetchone()
        if active: raise ValueError('A revision is already active for this brief')
    insert(conn,'pipeline_runs',{'run_id':rid,'week_id':packet['week_id'],'run_scope':'brief_revision' if revision else 'brief_generation',
        'trigger_type':'manual','triggered_by':actor,'input_refs':refs})
    previous=None
    for stage in STAGES:
        jid=identifier('brief_job')
        insert(conn,'pipeline_jobs',{'job_id':jid,'run_id':rid,'week_id':packet['week_id'],'stage':stage,
            **({'brief_id':revision} if revision else {'angle_id':angle_id}),
            'idempotency_key':f'{rid}:{stage}','input_hash':canonical_hash(refs),
            'progress_details':{'dependencies':[previous] if previous else []}})
        previous=jid
    repo.event(conn,rid,'brief_queued','Approved angle queued for research and briefing',details={'angle_id':angle_id,'revision_of':revision})
    return {'run_id':rid,'status':'queued'}

def queue(repo,angle_id,actor,mode='replay',**kwargs):
    with repo.connection() as conn:
        conn.execute('SELECT angle_id FROM content_angles WHERE angle_id=%s FOR UPDATE',(angle_id,))
        return queue_in_transaction(repo,conn,angle_id,actor,mode,**kwargs)

def save(worker,job,run,value,*,status='completed'):
    value=value.model_dump(mode='json') if hasattr(value,'model_dump') else value
    store=JsonStore(worker.storage.artifact_root)
    digest=canonical_hash(value)
    path=f'brief-runs/{run["run_id"]}/{job["stage"]}/{digest}.json'
    store.write_json(path,value)
    if job['stage']=='brief_prepare':
        with worker.repo.connection() as conn:
            current=worker.repo.guard(conn,job)
            conn.execute('UPDATE pipeline_jobs SET progress_details=%s WHERE job_id=%s',
                (Jsonb({**(current['progress_details'] or {}),'prepared':{'artifact':path,'hash':digest}}),job['job_id']))
    with worker.repo.connection() as conn:
        assert_packet(conn,run['input_refs']['angle'])
        if 'evidence' in value: verify_evidence(conn,value['evidence'])
        worker.repo.finish(conn,job,{'artifact':path,'hash':digest},status=status,message=job['stage']+' complete')

def output(worker,run,stage):
    with worker.repo.connection() as conn:
        data=conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage=%s AND status='completed'",(run['run_id'],stage)).fetchone()
        if not data: raise ValueError('Brief stage dependency is incomplete')
    store=JsonStore(worker.storage.artifact_root)
    value=store.read_json(data['result_refs']['artifact'])
    if canonical_hash(value)!=data['result_refs']['hash']: raise ValueError('Brief stage artifact integrity failed')
    return value

def progress(worker,job,step,message,completed=None,total=None):
    with worker.repo.connection() as conn:
        worker.repo.guard(conn,job)
        conn.execute('UPDATE pipeline_jobs SET current_step=%s,current_message=%s,completed_units=%s,total_units=%s,updated_at=now() WHERE job_id=%s',
            (step,message,completed,total,job['job_id']))

def research(worker,job,run,prepared):
    evidence={v['evidence_id']:EvidenceItem.model_validate(v) for v in prepared['evidence']}
    queries=[]; audit=[]; gaps=[]
    snapshot=prepared['archive']
    for round_no in range(3):
        progress(worker,job,'planning',f'Research query round {round_no+1}')
        plan=call(worker,job,run,'brief_plan',QueryPlan,{'angle':run['input_refs']['angle'],
            'original_evidence':prepared['evidence'],'gaps':gaps,'existing_queries':[q.model_dump() for q in queries],
            'remaining_queries':12-len(queries),'round':round_no})
        unique=[]
        for q in plan.queries:
            if q.text not in {q.text for q in queries+unique}: unique.append(q)
        if not unique or len(unique)+len(queries)>12 or (round_no==0 and not 6<=len(unique)<=10):
            raise ValueError('Research query plan violates unique-query budget/coverage')
        candidates={}
        vectors=query_vectors(worker,job,run,[q.text for q in unique])
        for i,q in enumerate(unique,1):
            progress(worker,job,'query_encoding','Resolving a compatible query vector',i-1,len(unique))
            vector=vectors[q.text]
            with worker.repo.connection() as conn:
                hits=retrieval.search(conn,q.text,vector,snapshot)
                # All ranked hits are audited; a bounded inspection set is graded.
                expanded=retrieval.expand(conn,hits[:5],snapshot)
            audit.append({'query':q.model_dump(),'hits':hits,'expanded_ids':[e.evidence_id for e in expanded]})
            for e in expanded:
                if e.evidence_id not in evidence: candidates.setdefault(e.evidence_id,e)
            queries.append(q)
        pool=list(evidence.values()); included=set(evidence)
        for e in candidates.values():
            if e.evidence_id in included: continue
            group=[v for v in candidates.values() if v.evidence_id==e.evidence_id or set(v.moment_ids)&set(e.moment_ids)]
            if len(pool)>=40: break
            # Whole linked moment groups retain their qualifiers even above the soft budget.
            for v in group:
                if v.evidence_id not in included: pool.append(v); included.add(v.evidence_id)
        omitted=set(candidates)-{e.evidence_id for e in pool}
        progress(worker,job,'grading',f'Grading {len(pool)} original-bound evidence items')
        grade=call(worker,job,run,'brief_grade',GradeResponse,{'angle':run['input_refs']['angle'],
            'evidence':[e.model_dump() for e in pool],'round':round_no})
        if len(grade.grades)!=len(pool) or {g.evidence_id for g in grade.grades}!={e.evidence_id for e in pool}:
            raise ValueError('Evidence grading must cover each delivered item exactly once')
        for g in grade.grades:
            e=next(e for e in pool if e.evidence_id==g.evidence_id)
            if e.inherited or g.relevant:
                evidence[e.evidence_id]=e if e.inherited else e.model_copy(update={'role':g.role})
        linked={m for e in evidence.values() for m in e.moment_ids}
        for e in pool:
            if set(e.moment_ids)&linked: evidence.setdefault(e.evidence_id,e)
        audit.append({'grades':grade.model_dump(),'ungraded_budget_omissions':sorted(omitted)})
        gaps=grade.gaps
        if not gaps or len(queries)>=12: break
    from .contracts import PriorItem
    prior=[PriorItem.model_validate(p) for p in prepared['prior']]
    with worker.repo.connection() as conn:
        retrieval.check_prior(conn,prior)
        for item in prior:
            refs=[r for m in conn.execute('SELECT m.evidence_refs FROM key_moments m JOIN angle_moments am USING(moment_id) WHERE am.angle_id=%s',(item.angle_id,)) for r in m['evidence_refs']]
            if any(e.transcript_id==r['transcript_id'] and e.start<r['end'] and r['start']<e.end for e in evidence.values() if e.transcript_id for r in refs):
                item.discovery=list(dict.fromkeys(item.discovery+['passage_overlap']))
    coverage={'original_grounding_complete':True,'semantic_and_lexical':'completed','eligible_chunks':len(snapshot['chunks']),
        'archive_source_ids':list(snapshot['sources']),'prior_argument_count':len(prior),'published_archive':'incomplete_legacy_catalogue_missing',
        'external':'disabled','meeting_dates':'unknown_dates_not_inferred_from_week','as_of':run['created_at'].isoformat()}
    if any(a.get('ungraded_budget_omissions') for a in audit): gaps=list(dict.fromkeys(gaps+['Supplemental candidates omitted from grading under context budget; see audit.']))
    return Dossier(angle=run['input_refs']['angle'],evidence=list(evidence.values()),prior=prior,queries=queries,
        coverage=coverage,gaps=gaps,audit=audit,brand=run['input_refs']['brand'])

def execute(worker,job):
    with worker.repo.connection() as conn:
        run=conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(job['run_id'],)).fetchone()
        if not worker.storage.brief_enabled or run['input_refs'].get('workflow')!=WORKFLOW:
            raise ValueError('Brief workflow is disabled or incompatible')
        assert_packet(conn,run['input_refs']['angle'])
        frozen=run['input_refs'].get('execution_contract')
        current=execution_contract(worker)
        if frozen is None and job['stage']=='brief_prepare':
            worker.repo.guard(conn,job)
            run['input_refs']['execution_contract']=current
            conn.execute('UPDATE pipeline_runs SET input_refs=%s WHERE run_id=%s',(Jsonb(run['input_refs']),run['run_id']))
        elif frozen!=current: raise ValueError('Frozen brief execution contract changed; restore it or create a new intent')
    stage=job['stage']
    if stage=='brief_prepare':
        with worker.repo.connection() as conn:
            current=worker.repo.guard(conn,job)
            saved=(current['progress_details'] or {}).get('prepared')
            if saved:
                value=JsonStore(worker.storage.artifact_root).read_json(saved['artifact'])
                if canonical_hash(value)!=saved['hash']: raise ValueError('Prepared input artifact integrity failed')
                verify_evidence(conn,value['evidence']);retrieval.check_archive(conn,value['archive']);retrieval.check_prior(conn,value['prior'])
            else:
                evidence=anchors(conn,run['input_refs']['angle'])
                extras=[EvidenceItem.model_validate(e) for e in run['input_refs'].get('added_evidence',[])]
                verify_evidence(conn,extras)
                evidence=list({e.evidence_id:e for e in evidence+extras}.values())
                snapshot=retrieval.archive(conn,worker.models,worker.storage.synthetic)
                prior=retrieval.previous(conn,run['input_refs']['angle'],evidence,snapshot,worker.models,worker.storage.synthetic,as_of=run['created_at'])
                value={'evidence':[e.model_dump() for e in evidence],'archive':snapshot,'prior':[p.model_dump(mode='json') for p in prior]}
        save(worker,job,run,value)
    elif stage=='brief_research':
        save(worker,job,run,research(worker,job,run,output(worker,run,'brief_prepare')))
    elif stage=='brief_context':
        dossier=Dossier.model_validate(output(worker,run,'brief_research'))
        from .external import enrich
        dossier=enrich(worker,job,run,dossier)
        save(worker,job,run,dossier)
    elif stage=='brief_writing':
        dossier=output(worker,run,'brief_context')
        packet={'dossier':compact_dossier(dossier),'instructions':run['input_refs'].get('instructions')}
        if run['input_refs'].get('revision_of'):
            from .gate_two import get
            parent=get(worker.repo,run['input_refs']['revision_of'])
            if parent['has_replacement']: raise ValueError('Revision parent was superseded')
            packet['current_brief']=parent['content_body']; packet['instructions']=run['input_refs']['instructions']
        document=call(worker,job,run,'brief_write',BriefDocument,packet)
        save(worker,job,run,{'document':document.model_dump(mode='json')})
    elif stage=='brief_validation':
        from .validation import finalize
        finalize(worker,job,run,output(worker,run,'brief_context'),output(worker,run,'brief_writing')['document'])
    else: raise ValueError('Unsupported brief stage')

def activate_live(repo,run_id,expected_input_hash,actor):
    """Explicit operator action; preparing/reading/retrying never changes mode."""
    from .gate_two import authorize
    authorize(repo,actor)
    if not (repo.settings.generation_enabled and repo.settings.brief_live_enabled): raise ValueError('External brief generation switches are disabled')
    with repo.connection() as conn:
        row=conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s FOR UPDATE',(run_id,)).fetchone()
        if not row or row['run_scope'] not in {'brief_generation','brief_revision'} or row['input_refs'].get('synthetic'):
            raise ValueError('Live activation requires a real brief scope')
        if canonical_hash(row['input_refs'])!=expected_input_hash: raise ValueError('Run inputs changed; refresh before activation')
        assert_packet(conn,row['input_refs']['angle'])
        if conn.execute("SELECT 1 FROM pipeline_events WHERE run_id=%s AND event_type IN ('brief_provider_dispatch','brief_query_dispatch','brief_web_dispatch')",(run_id,)).fetchone():
            raise ValueError('A dispatched run cannot change execution mode')
        row['input_refs']['mode']='live'
        conn.execute('UPDATE pipeline_runs SET input_refs=%s,updated_at=now() WHERE run_id=%s',(Jsonb(row['input_refs']),run_id))
        conn.execute("UPDATE pipeline_jobs SET input_hash=%s WHERE run_id=%s AND status IN ('queued','failed','waiting')",(canonical_hash(row['input_refs']),run_id))
        repo.event(conn,run_id,'brief_live_activated','Explicit live mode selected; no provider was dispatched',details={'actor':actor})
        return {'run_id':run_id,'mode':'live','status':row['status'],'next':'Explicitly retry a failed stage or start the worker'}
