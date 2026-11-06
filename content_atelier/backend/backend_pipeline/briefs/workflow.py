from datetime import datetime,UTC
from psycopg.types.json import Jsonb
from ..repository import insert,identifier
from ..store import canonical_hash
from ..artifacts import store_for
from ..settings_store import snapshot_refs
from .. import retrieval
from .contracts import WORKFLOW,STAGES,Dossier,QueryPlan,GradeResponse,BriefDocument,EvidenceItem,writer_schema
from .inputs import angle_packet,anchors,assert_packet,verify_evidence
from .runtime import (CONTEXT_CHANGED,CONTEXT_CHANGED_MESSAGE,brand_bundle,call,query_vectors,compact_dossier,execution_contract,
    schema_of,stable_contract,writer_of)
from .contracts_v2 import SCHEMA_V2
from .contracts_v3 import SCHEMA_V3
from .contracts_v4 import SCHEMA_V4

def queue_in_transaction(repo,conn,angle_id,actor,mode='replay',*,revision=None,instructions=None,added_evidence=None,unlock=None,on_failure='record'):
    """Queue a brief inside the caller's transaction.

    Gate 1 approval calls this in its own transaction. A first brief that cannot be
    queued (for example a missing brand bundle) is recorded as a failed run with
    the reason, so the approval still commits. Revisions and on_failure='raise' raise.
    """
    if revision or on_failure=='raise':
        return _queue(repo,conn,angle_id,actor,mode,revision=revision,instructions=instructions,added_evidence=added_evidence,unlock=unlock)
    try:
        with conn.transaction():  # Savepoint: a failure leaves the approval intact.
            return _queue(repo,conn,angle_id,actor,mode)
    except Exception as exc:
        return record_failure(repo,conn,angle_id,actor,mode,exc)

def develop_mode(settings):
    """The mode a developed card's first brief is queued in (4.B1): live wherever live brief generation is switched on, so
    developing a card starts research and writing with no command; replay (saved responses only) stays a test and
    development mode, used only where the live switches are off; synthetic on an isolated test database."""
    if settings.synthetic: return 'synthetic'
    return 'live' if settings.generation_enabled and settings.brief_live_enabled else 'replay'

def record_failure(repo,conn,angle_id,actor,mode,exc):
    reason=f'{type(exc).__name__}: {exc}'[:2000]
    week=conn.execute('SELECT week_id FROM content_angles WHERE angle_id=%s',(angle_id,)).fetchone()
    # A distinct ID keeps the deterministic run ID free for the brief once configuration is fixed.
    rid=identifier('brief_run_unqueued')
    insert(conn,'pipeline_runs',{'run_id':rid,'week_id':week['week_id'],'run_scope':'brief_generation','status':'failed',
        'error_summary':reason,'current_message':'Brief could not be queued; Gate 1 approval was saved',
        'trigger_type':'manual','triggered_by':actor,'finished_at':datetime.now(UTC),
        'input_refs':{'workflow':WORKFLOW,'angle':{'angle_id':angle_id,'week_id':week['week_id']},'mode':mode,
            'synthetic':repo.settings.synthetic,'queued_by':actor,'queue_failure':reason}})
    repo.event(conn,rid,'brief_queue_failed','Brief could not be queued: '+reason,details={'angle_id':angle_id},severity='error')
    return {'run_id':rid,'status':'failed','error':reason}

def _queue(repo,conn,angle_id,actor,mode='replay',*,revision=None,instructions=None,added_evidence=None,unlock=None,regeneration=0,regenerates=None):
    if not repo.settings.brief_enabled: raise ValueError('Brief workflow is not enabled')
    if mode not in {'replay','live','synthetic'}: raise ValueError('Unknown brief execution mode')
    if mode=='synthetic' and not repo.settings.synthetic: raise ValueError('Synthetic briefing requires isolated test database')
    if mode=='live' and not (repo.settings.generation_enabled and repo.settings.brief_live_enabled):
        raise ValueError('External brief generation is disabled')
    if mode=='live':
        from ..settings_store import require_explicit_models
        require_explicit_models(storage=repo.settings,brief=True)  # a live brief names its models (section 4.10)
    packet=angle_packet(conn,angle_id)
    parent=None
    if revision:
        parent=conn.execute('SELECT content_body FROM content_briefs WHERE brief_id=%s',(revision,)).fetchone()
        version=(parent or {}).get('content_body',{}).get('schema_version','brief_document_v1')
    else:
        version=repo.settings.brief_schema
    # Context and attested facts from the gates (5.B7): the brief's own (a refresh) and the card's, frozen with the run. A
    # refresh's are part of its run key; a first brief's are read once its configuration has passed (below).
    from .context import for_writer
    context=for_writer(conn,angle_id,(parent or {}).get('content_body',{}).get('context_items') or []) if revision else None
    bundle=brand_source(repo.settings,version) if revision else None
    # The first brief's run key: the card's approval, and a regeneration counter once a person regenerated it (4.B1, V13);
    # the first run keeps the key it always had. A live run adds its mode (4.B1), so a replay run queued for the same approval
    # never blocks the live start; the same approval in the same mode is still one run, so developing twice makes one brief.
    first=[WORKFLOW,angle_id,packet['approved_hash'],*([{'regeneration':regeneration}] if regeneration else [])]
    intent=canonical_hash(first+([{'mode':'live'}] if mode=='live' else [])) if not revision else canonical_hash(
        [WORKFLOW,angle_id,packet['approved_hash'],revision,instructions,added_evidence,mode,bundle['hash'],
         *([{'unlock':sorted(unlock)}] if unlock else []),*([{'context':[i['id'] for i in context]}] if context else [])])
    rid='brief_run_'+intent[:24]
    existing=conn.execute('SELECT input_refs,status FROM pipeline_runs WHERE run_id=%s',(rid,)).fetchone()
    if existing: return {'run_id':rid,'status':existing['status']}
    if mode=='live' and not revision:
        earlier=_replaced_by_live(repo,conn,'brief_run_'+canonical_hash(first)[:24],rid,actor)
        if earlier: return earlier
    bundle=bundle or brand_source(repo.settings,version)
    if context is None: context=for_writer(conn,angle_id)
    refs={'workflow':WORKFLOW,'angle':packet,'brand':bundle,'mode':mode,'synthetic':repo.settings.synthetic,
        'revision_of':revision,'instructions':instructions,'added_evidence':added_evidence or [],'queued_by':actor,
        **({'regeneration':regeneration,'regenerates':regenerates} if regeneration else {}),
        **({'context_items':context} if context else {})}
    if revision and version in (SCHEMA_V2,SCHEMA_V3,SCHEMA_V4):
        # Interface 1: the lines the refresh keeps, with their values (the writer's `locked_fields`), and those released.
        from . import paths
        from .contracts_v3 import writer_part
        body=parent['content_body']['document']['body']
        keep=paths.revision_locks({'input_refs':{'instructions':instructions,'unlock':unlock or []}},parent)
        from .contracts_v4 import writer_part_v4
        part={SCHEMA_V3:writer_part,SCHEMA_V4:writer_part_v4}.get(version)
        refs.update(locked_fields=paths.locked_values(part(body) if part else body,keep),unlock=sorted(unlock or []))
    # The settings this brief run was queued under and where each came from (0.B8, section 4.10).
    refs.update(snapshot_refs('brief',storage=repo.settings,conn=conn))
    if version in (SCHEMA_V2,SCHEMA_V3,SCHEMA_V4):
        # The contract, channel set and writer are frozen with the run (E.B15 b, E.B22, E.B23); v1 runs keep their original refs.
        refs.update(schema_version=version,channels=list(repo.settings.brief_channels),writer=writer_for(repo.settings,version,revision))
        from ..settings_store import IDENTITY_WRITERS
        if refs['writer'] in IDENTITY_WRITERS:
            # Writer v5.2 (Phase N8): the identity records of the card's calls and the card's account memory, frozen with
            # the run like its context items, so a retry or a replay sends the same request.
            refs.update(identity_refs(conn,packet))
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

def _replaced_by_live(repo,conn,old,rid,actor):
    """A first-brief run queued for the same approval in another mode (replay) before this live start (4.B1). If it made the
    brief, or is still working, it is the card's one brief run and is returned; otherwise it is superseded by the live run
    about to be queued, its unfinished stages closed, and kept as the record."""
    row=conn.execute('SELECT run_id,status,input_refs FROM pipeline_runs WHERE run_id=%s FOR UPDATE',(old,)).fetchone()
    if not row or row['input_refs'].get('superseded_by'): return None
    made=conn.execute("SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND stage='brief_validation' AND status='completed'",(old,)).fetchone()
    if made or row['status'] in ('waiting_for_review','completed') or conn.execute(
            "SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND status='running'",(old,)).fetchone():
        return {'run_id':old,'status':row['status']}
    refs={**row['input_refs'],'superseded_by':{'run_id':rid,'actor':actor,'at':datetime.now(UTC).isoformat(),'reason':'started live'}}
    conn.execute("UPDATE pipeline_runs SET status='cancelled',input_refs=%s,current_message=%s,finished_at=now(),updated_at=now() WHERE run_id=%s",
        (Jsonb(refs),'Superseded by the live brief run '+rid,old))
    conn.execute("""UPDATE pipeline_jobs SET status='failed',error_summary=%s,finished_at=now(),updated_at=now()
        WHERE run_id=%s AND status IN ('queued','waiting','failed')""",('Superseded by the live brief run '+rid,old))
    repo.event(conn,old,'brief_run_superseded','The brief was started live; this '+row['input_refs'].get('mode','replay')+' run is kept as the record',
        details={'run_id':rid,'actor':actor})
    return None

def identity_refs(conn,packet):
    """The identity records of the people and accounts in the card's calls and text, and the card's account memory (the later
    scenes of its accounts, 3.B17)."""
    from .. import accounts, identities
    moments=sorted(packet['moment_hashes'])
    docs=[r['document_id'] for r in conn.execute('SELECT DISTINCT document_id FROM key_moments WHERE moment_id=ANY(%s) AND document_id IS NOT NULL',(moments,))]
    memory=accounts.next_evidence(conn,moments)
    later_docs=[r['document_id'] for r in conn.execute('SELECT DISTINCT document_id FROM key_moments WHERE moment_id=ANY(%s)',
                                                         ([m['moment_id'] for m in memory],))] if memory else []
    card=(packet.get('body') or {}).get('card') or {}
    texts=[str(card.get(k) or '') for k in ('title','core_perspective','point','wia_in_action','guardrail','evidence_points')]
    return {'identities':identities.notes(conn,document_ids=docs+later_docs,texts=texts),'account_memory':memory}

def later_records(conn,memory):
    """The anchor passages of the account memory's later scenes as evidence items (context, not the card's anchors), so the
    writer reads each later fact in its speaker's words and every check holds it to the same rules. Only the anchors: the
    scenes' whole context made the N8 proof brief's research request too large for its preflight (182 items)."""
    from .inputs import evidence_from_passage
    items=[]
    for entry in memory:
        m=conn.execute('SELECT * FROM key_moments WHERE moment_id=%s',(entry['moment_id'],)).fetchone()
        if not m: raise ValueError('An account-memory scene is no longer in the ledger; queue the brief again')
        for ref in (r for r in m['evidence_refs'] if 'anchor' in r['roles']):
            source=conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s',(ref['transcript_id'],)).fetchone()
            passage=next((p for p in (source or {}).get('passage_map') or [] if p['passage_id']==ref['passage_id']),None)
            if source and passage:
                items.append(evidence_from_passage(source,passage,moment=m))
    return list({i.evidence_id:i for i in items}.values())

def writer_for(settings,version,revision=None):
    """The writer prompt a run of this contract is queued with: the setting, which must suit the contract. A revision of
    an older contract's brief keeps that contract and takes its newest writer when the setting names another contract's."""
    from ..settings_store import BRIEF_REVISION_WRITERS,BRIEF_WRITERS_BY_SCHEMA,brief_writer_problem
    writer=settings.brief_writer
    if revision and (readers:=BRIEF_REVISION_WRITERS.get(version)):
        # A refresh with feedback needs a writer that reads the instructions and the locked lines (5.B6, interface 1).
        return writer if writer in readers else readers[-1]
    if revision and brief_writer_problem(version,writer):
        return BRIEF_WRITERS_BY_SCHEMA[version][-1]
    if problem:=brief_writer_problem(version,writer): raise ValueError(problem)
    return writer

# A v2 brief's brand context is the knowledge base (E.B11 f, V3): its version and hashes are frozen in the run's execution
# contract at brief_prepare and pinned on the brief's header; no separate bundle is read or approved.
KNOWLEDGE_BASE_BRAND={'source':'knowledge_base','hash':canonical_hash({'source':'knowledge_base'}),'documents':{}}

def brand_source(settings,version):
    return dict(KNOWLEDGE_BASE_BRAND) if version in (SCHEMA_V2,SCHEMA_V3,SCHEMA_V4) else brand_bundle(settings)

def retry_unqueued(repo,angle_id,actor):
    """Re-queue the first brief of an approved angle whose queueing failed (S.B13).

    Only an approver may retry, and only when the angle's latest brief run is an
    unqueued failure. A configuration that is still broken raises with its reason and
    records nothing more; the original failed run stays as the audit record.
    """
    from .gate_two import authorize
    authorize(repo,actor,'approve')
    with repo.connection() as conn:
        angle=conn.execute('SELECT approval_status FROM content_angles WHERE angle_id=%s FOR UPDATE',(angle_id,)).fetchone()
        if not angle: raise ValueError('Angle not found')
        if angle['approval_status']!='approved': raise ValueError('Only an approved angle can queue its brief')
        latest=conn.execute("""SELECT run_id,status,input_refs FROM pipeline_runs WHERE input_refs->>'workflow'=%s
            AND input_refs->'angle'->>'angle_id'=%s ORDER BY created_at DESC LIMIT 1""",(WORKFLOW,angle_id)).fetchone()
        if not latest or latest['status']!='failed' or not latest['input_refs'].get('queue_failure'):
            raise ValueError('There is no unqueued brief to retry; retry a failed stage from its job instead')
        try:
            with conn.transaction():
                # A retry starts the brief the way developing does now (4.B1), not in the mode the failed attempt had.
                result=queue_in_transaction(repo,conn,angle_id,actor,develop_mode(repo.settings),on_failure='raise')
        except (OSError,ValueError,KeyError,TypeError) as exc:
            # Same wording as the recorded failure, so the screen shows one reason.
            raise ValueError(f'Brief still cannot be queued: {type(exc).__name__}: {exc}'[:2000]) from exc
        repo.event(conn,result['run_id'],'brief_queue_retried','Brief queued after an earlier queueing failure',
            details={'angle_id':angle_id,'failed_run_id':latest['run_id'],'actor':actor})
        return {**result,'retried_run_id':latest['run_id']}

def regenerate(repo,angle_id,actor,mode=None):
    """A fresh first-brief run for the same approved card, when the pinned context changed under the last one (V13).

    A run freezes its execution contract (knowledge-base version, prompts, schemas, models) at its first stage and fails
    when that changes mid-run; its run key is the card's approval, so queueing again only found the failed run. An editor
    or approver regenerates instead: a new run whose key adds the regeneration counter (4.B1), recorded on the run with
    the run it replaces. The old run is kept, marked superseded, and can no longer be retried. Without a mode the new run
    keeps the old run's."""
    from .gate_two import authorize
    authorize(repo,actor)
    with repo.connection() as conn:
        angle=conn.execute('SELECT approval_status FROM content_angles WHERE angle_id=%s FOR UPDATE',(angle_id,)).fetchone()
        if not angle: raise ValueError('Angle not found')
        if angle['approval_status']!='approved': raise ValueError('Only an approved angle can regenerate its brief')
        latest=conn.execute("""SELECT run_id,status,error_summary,input_refs FROM pipeline_runs WHERE run_scope='brief_generation'
            AND input_refs->>'workflow'=%s AND input_refs->'angle'->>'angle_id'=%s ORDER BY created_at DESC LIMIT 1""",(WORKFLOW,angle_id)).fetchone()
        if not latest: raise ValueError('This card has no brief run to regenerate; start its brief instead')
        if latest['input_refs'].get('queue_failure'): raise ValueError('The brief was never queued; retry it instead')
        changed=latest['status']=='failed' and (CONTEXT_CHANGED in (latest['error_summary'] or '') or conn.execute(
            "SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND status='failed' AND position(%s in coalesce(error_summary,''))>0",
            (latest['run_id'],CONTEXT_CHANGED)).fetchone())
        if not changed:
            raise ValueError('Regenerate a brief only when its run failed because its pinned context changed; this run is '+latest['status'])
        count=int(latest['input_refs'].get('regeneration') or 0)+1
        result=_queue(repo,conn,angle_id,actor,mode or latest['input_refs'].get('mode') or 'replay',regeneration=count,regenerates=latest['run_id'])
        refs={**latest['input_refs'],'superseded_by':{'run_id':result['run_id'],'actor':actor,'at':datetime.now(UTC).isoformat(),'reason':'regenerated'}}
        conn.execute('UPDATE pipeline_runs SET input_refs=%s,current_message=%s,updated_at=now() WHERE run_id=%s',
            (Jsonb(refs),'Superseded by a regenerated brief run '+result['run_id'],latest['run_id']))
        repo.event(conn,latest['run_id'],'brief_run_superseded','A person regenerated the brief after its pinned context changed',
            details={'angle_id':angle_id,'run_id':result['run_id'],'regeneration':count,'actor':actor})
        repo.event(conn,result['run_id'],'brief_regenerated','Brief regenerated for the same approved card',
            details={'angle_id':angle_id,'regenerates':latest['run_id'],'regeneration':count,'actor':actor})
        return {**result,'regeneration':count,'regenerates':latest['run_id']}

def queue(repo,angle_id,actor,mode='replay',**kwargs):
    with repo.connection() as conn:
        conn.execute('SELECT angle_id FROM content_angles WHERE angle_id=%s FOR UPDATE',(angle_id,))
        return queue_in_transaction(repo,conn,angle_id,actor,mode,on_failure='raise',**kwargs)

def save(worker,job,run,value,*,status='completed'):
    value=value.model_dump(mode='json') if hasattr(value,'model_dump') else value
    store=store_for(worker.storage)
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
    store=store_for(worker.storage)
    value=store.read_json(data['result_refs']['artifact'])
    if canonical_hash(value)!=data['result_refs']['hash']: raise ValueError('Brief stage artifact integrity failed')
    return value

def progress(worker,job,step,message,completed=None,total=None):
    with worker.repo.connection() as conn:
        worker.repo.guard(conn,job)
        conn.execute('UPDATE pipeline_jobs SET current_step=%s,current_message=%s,completed_units=%s,total_units=%s,updated_at=now() WHERE job_id=%s',
            (step,message,completed,total,job['job_id']))

def repair_graded_ids(grades,delivered):
    """A grade whose evidence id is not delivered, but differs by one character from exactly one delivered id no other grade
    covers, is that item's grade: the model miscopied a 24-character hex id (N2, 23 October: Sonnet wrote
    ev_bf85af6b4cc4878d4aa1c966 for ev_bf85af6b3cc4878d4aa1c966 among 47 ids, and the stage failed after USD 0.30 of correct
    grading). Repaired with the repair recorded, like a near-miss quote; anything else still fails the coverage check."""
    open_ids=[i for i in delivered if i not in {g.evidence_id for g in grades}]
    out=[]; repairs=[]
    for g in grades:
        if g.evidence_id not in delivered:
            near=[i for i in open_ids if len(i)==len(g.evidence_id) and sum(a!=b for a,b in zip(i,g.evidence_id))==1]
            if len(near)==1:
                repairs.append({'written':g.evidence_id,'repaired_to':near[0]}); open_ids.remove(near[0])
                g=g.model_copy(update={'evidence_id':near[0]})
        out.append(g)
    return out,repairs

def settle_grades(grades,delivered):
    """The grades of the delivered items only, one each: a grade for an id never delivered (and not a one-character miscopy,
    repair_graded_ids) is dropped, a second grade of one item is dropped; (grades, missing ids, dropped). NP-7's paid proof
    (25 October): a 52-grade answer that covered the pool unevenly failed the stage, and a retry replayed the same saved
    answer, so it could never pass; the missing items are now graded in a follow-up call instead."""
    seen=set(); kept=[]; dropped=[]
    for g in grades:
        if g.evidence_id not in delivered or g.evidence_id in seen:
            dropped.append(g.evidence_id); continue
        seen.add(g.evidence_id); kept.append(g)
    return kept,[i for i in delivered if i not in seen],dropped

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
        repaired,id_repairs=repair_graded_ids(grade.grades,[e.evidence_id for e in pool])
        if id_repairs: grade=grade.model_copy(update={'grades':repaired})
        settled,missing,dropped=settle_grades(grade.grades,[e.evidence_id for e in pool])
        followup=None
        if dropped or missing:
            grade=grade.model_copy(update={'grades':settled})
        if missing:
            # The items the first answer left ungraded, graded on their own (a new request, so never a replayed answer).
            progress(worker,job,'grading',f'Grading {len(missing)} items the first grading missed')
            rest=[e for e in pool if e.evidence_id in set(missing)]
            more=call(worker,job,run,'brief_grade',GradeResponse,{'angle':run['input_refs']['angle'],
                'evidence':[e.model_dump() for e in rest],'round':round_no,'ungraded_from_first_answer':True})
            fixed,more_repairs=repair_graded_ids(more.grades,missing)
            more_settled,_,more_dropped=settle_grades(fixed,missing)
            grade=grade.model_copy(update={'grades':[*grade.grades,*more_settled]})
            followup={'missing':missing,'id_repairs':more_repairs,'dropped':more_dropped}
        if len(grade.grades)!=len(pool) or {g.evidence_id for g in grade.grades}!={e.evidence_id for e in pool}:
            raise ValueError('Evidence grading must cover each delivered item exactly once')
        for g in grade.grades:
            e=next(e for e in pool if e.evidence_id==g.evidence_id)
            if e.inherited or g.relevant:
                evidence[e.evidence_id]=e if e.inherited else e.model_copy(update={'role':g.role})
        linked={m for e in evidence.values() for m in e.moment_ids}
        for e in pool:
            if set(e.moment_ids)&linked: evidence.setdefault(e.evidence_id,e)
        audit.append({'grades':grade.model_dump(),'ungraded_budget_omissions':sorted(omitted),**({'id_repairs':id_repairs} if id_repairs else {}),
                      **({'dropped_grades':dropped} if dropped else {}),**({'followup_grading':followup} if followup else {})})
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
        'external':'disabled','meeting_dates':'unknown_dates_not_inferred_from_week','as_of':run['created_at'].isoformat(),
        **({'prior_coverage_gaps':prepared['prior_gaps']} if prepared.get('prior_gaps') else {})}
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
        current=execution_contract(worker,schema_of(run),run)
        if frozen is None and job['stage']=='brief_prepare':
            worker.repo.guard(conn,job)
            run['input_refs']['execution_contract']=current
            # The knowledge-base version the writer will use is known only now; the snapshot records it with the settings (0.B8).
            if isinstance(run['input_refs'].get('settings_snapshot'),dict) and (current.get('knowledge_base') or {}).get('version'):
                run['input_refs']['settings_snapshot']['knowledge_base_version']=current['knowledge_base']['version']
            conn.execute('UPDATE pipeline_runs SET input_refs=%s WHERE run_id=%s',(Jsonb(run['input_refs']),run['run_id']))
        elif stable_contract(frozen)!=stable_contract(current): raise ValueError(CONTEXT_CHANGED_MESSAGE)
    stage=job['stage']
    if stage=='brief_prepare':
        with worker.repo.connection() as conn:
            current=worker.repo.guard(conn,job)
            saved=(current['progress_details'] or {}).get('prepared')
            if saved:
                value=store_for(worker.storage).read_json(saved['artifact'])
                if canonical_hash(value)!=saved['hash']: raise ValueError('Prepared input artifact integrity failed')
                verify_evidence(conn,value['evidence']);retrieval.check_archive(conn,value['archive']);retrieval.check_prior(conn,value['prior'])
            else:
                evidence=anchors(conn,run['input_refs']['angle'])
                # Writer v5.2 (3.B17): the card's account memory, frozen with the run, joins the evidence as later records.
                evidence+=later_records(conn,run['input_refs'].get('account_memory') or [])
                extras=[EvidenceItem.model_validate(e) for e in run['input_refs'].get('added_evidence',[])]
                verify_evidence(conn,extras)
                evidence=list({e.evidence_id:e for e in evidence+extras}.values())
                snapshot=retrieval.archive(conn,worker.models,worker.storage.synthetic)
                prior_gaps=[]
                prior=retrieval.previous(conn,run['input_refs']['angle'],evidence,snapshot,worker.models,worker.storage.synthetic,
                                         as_of=run['created_at'],gaps=prior_gaps,revision=bool(run['input_refs'].get('revision_of')))
                value={'evidence':[e.model_dump() for e in evidence],'archive':snapshot,'prior':[p.model_dump(mode='json') for p in prior],
                       **({'prior_gaps':sorted(prior_gaps,key=lambda g:g['angle_id'])} if prior_gaps else {})}
        save(worker,job,run,value)
    elif stage=='brief_research':
        save(worker,job,run,research(worker,job,run,output(worker,run,'brief_prepare')))
    elif stage=='brief_context':
        dossier=Dossier.model_validate(output(worker,run,'brief_research'))
        from .external import enrich
        dossier=enrich(worker,job,run,dossier)
        save(worker,job,run,dossier)
    elif stage=='brief_writing' and schema_of(run)==SCHEMA_V4:
        from .validation_v3 import contract_for
        from .contracts_v4 import writer_part_v4
        # Writer v5.1 answers in its own model and schema (three Reels, NP.B10); v5 sends what it always sent.
        c=contract_for(SCHEMA_V4,writer_of(run))
        from ..settings_store import IDENTITY_WRITERS
        packet=(writer_packet_v52 if writer_of(run) in IDENTITY_WRITERS else writer_packet_v4)(worker,run,output(worker,run,'brief_context'))
        if run['input_refs'].get('revision_of'):
            from .gate_two import get
            parent=get(worker.repo,run['input_refs']['revision_of'])
            if parent['has_replacement']: raise ValueError('Revision parent was superseded')
            packet['current_brief']=writer_part_v4(parent['content_body']['document']['body'])
        body=call(worker,job,run,'brief_write',c.write,packet,c.wire(run['input_refs'].get('channels') or []))
        save(worker,job,run,{'document':body.model_dump(mode='json')})
    elif stage=='brief_validation' and schema_of(run)==SCHEMA_V4:
        from .validation_v3 import contract_for,finalize_v3
        context=output(worker,run,'brief_context')
        finalize_v3(worker,job,run,context,output(worker,run,'brief_writing')['document'],provenance_v4(worker,run,context),
                    contract_for(SCHEMA_V4,writer_of(run)))
    elif stage=='brief_writing' and schema_of(run)==SCHEMA_V3:
        from .contracts_v3 import BriefWriteV3,writer_part,writer_schema_v3
        packet=writer_packet_v3(run,output(worker,run,'brief_context'))
        if run['input_refs'].get('revision_of'):
            from .gate_two import get
            parent=get(worker.repo,run['input_refs']['revision_of'])
            if parent['has_replacement']: raise ValueError('Revision parent was superseded')
            packet['current_brief']=writer_part(parent['content_body']['document']['body'])
        body=call(worker,job,run,'brief_write',BriefWriteV3,packet,writer_schema_v3(run['input_refs'].get('channels') or []))
        save(worker,job,run,{'document':body.model_dump(mode='json')})
    elif stage=='brief_validation' and schema_of(run)==SCHEMA_V3:
        from .validation_v3 import finalize_v3
        context=output(worker,run,'brief_context')
        finalize_v3(worker,job,run,context,output(worker,run,'brief_writing')['document'],provenance_v3(worker,run,context))
    elif stage=='brief_writing' and schema_of(run)==SCHEMA_V2:
        from .contracts_v2 import BriefBodyV2,writer_schema_v2
        dossier=output(worker,run,'brief_context')
        packet=writer_packet_v2(run,dossier)
        if run['input_refs'].get('revision_of'):
            from .gate_two import get
            parent=get(worker.repo,run['input_refs']['revision_of'])
            if parent['has_replacement']: raise ValueError('Revision parent was superseded')
            packet['current_brief']=parent['content_body']['document']['body']
        body=call(worker,job,run,'brief_write',BriefBodyV2,packet,writer_schema_v2(run['input_refs'].get('channels') or []))
        save(worker,job,run,{'document':body.model_dump(mode='json')})
    elif stage=='brief_validation' and schema_of(run)==SCHEMA_V2:
        from .validation_v2 import finalize_v2
        context=output(worker,run,'brief_context')
        finalize_v2(worker,job,run,context,output(worker,run,'brief_writing')['document'],provenance_v2(worker,run,context))
    elif stage=='brief_writing':
        dossier=output(worker,run,'brief_context')
        packet={'dossier':compact_dossier(dossier),'instructions':run['input_refs'].get('instructions')}
        if run['input_refs'].get('revision_of'):
            from .gate_two import get
            parent=get(worker.repo,run['input_refs']['revision_of'])
            if parent['has_replacement']: raise ValueError('Revision parent was superseded')
            packet['current_brief']=parent['content_body']; packet['instructions']=run['input_refs']['instructions']
        document=call(worker,job,run,'brief_write',BriefDocument,packet,writer_schema(p['angle_id'] for p in dossier['prior']))
        save(worker,job,run,{'document':document.model_dump(mode='json')})
    elif stage=='brief_validation':
        from .validation import finalize
        finalize(worker,job,run,output(worker,run,'brief_context'),output(worker,run,'brief_writing')['document'])
    else: raise ValueError('Unsupported brief stage')

def writer_packet_v2(run,dossier):
    """The v2 writer's user message (E.B15 c): the card's fields, the quoted turns and cleared exemplars, never the audit."""
    from .context import writer_view
    angle=run['input_refs']['angle']; body=angle['body']; card=body.get('card') or {}
    from .validation_v2 import person_cta
    brand=(dossier.get('brand') or {}).get('documents') or {}
    return {'approved_angle':{'title':card.get('title') or body['title'],'core_perspective':card.get('core_perspective') or body['argument']},
        'card':{**{k:card.get(k) for k in ('pillar','content_type','audience','why_it_matters','wia_in_action','offer_connection',
                                           'evidence_points','verify_before_publishing','series')},
                # A strategist v7 card (E.B30, E.B32) adds its point, its tests and the guardrail the writer must keep;
                # an earlier card's packet is unchanged, so its saved requests still replay.
                **{k:card[k] for k in WRITER_V7_FIELDS if k in card}} if card else {'audience':body['audience']},
        'gate_one_note':angle.get('steer'),
        'cta':person_cta(angle) or 'Propose one from the CTA catalogue, or no explicit ask; Whitney confirms it at Gate 2',
        'channels':run['input_refs'].get('channels'),
        'evidence':[{'evidence_id':e['evidence_id'],'speaker':e.get('speaker'),'start_ms':e.get('start_ms'),'role':e['role'],
                     'excerpt':e['excerpt'],'qualifications':e.get('qualifications',[])} for e in dossier['evidence']],
        'prior_coverage':[{'angle_id':p['angle_id'],'argument':p['argument']} for p in dossier['prior']],
        'research_gaps':dossier.get('gaps',[]),
        'cleared_exemplars':brand.get('exemplars',[]),
        'instructions':run['input_refs'].get('instructions'),
        # Context and attested facts given at the gates (5.B7); absent when there are none, so earlier requests replay.
        **({'reviewer_context':writer_view(run['input_refs']['context_items'])} if run['input_refs'].get('context_items') else {})}

# The fields of a strategist v7 card the brief writer reads (E.B30, E.B32): the guardrail first among them.
WRITER_V7_FIELDS = ('guardrail','point','reader_takeaway','reader_fit','belief_ref','offer_fit','public_stance')

def writer_packet_v3(run,dossier):
    """The v4 writer's user message (E.B23): v2's packet, with the call's turns given by speaker and time and no evidence
    identifiers, since the writer cites nothing; the ledger binds the copy after writing."""
    packet=writer_packet_v2(run,dossier)
    packet['evidence']=[{k:v for k,v in e.items() if k!='evidence_id'} for e in packet['evidence']]
    return packet

# The card fields writer v5 reads (E.B33): v6's, and strategist v7's point, takeaway, offer fit and guardrail when the card
# has them (E.B30, track E; absent fields are left out, so a v6 card reads as before).
CARD_FIELDS_V5=('pillar','content_type','audience','why_it_matters','wia_in_action','offer_connection','evidence_points',
                'verify_before_publishing','series','point','point_is_about','reader_takeaway','belief_ref','offer_fit',
                'public_stance','guardrail')

def writer_packet_v52(worker,run,dossier):
    """Writer v5.2's user message (Phase N8): v5's, with the people and accounts in the evidence (`people`: who each label is,
    pronouns, a former team member's leaving date and what copy may do with them), "what happened next" from the card's
    account memory (later records of the same account, given as evidence items too, so the ledger binds what the copy says
    about them), and each internal-meeting evidence item marked as team practice."""
    from .. import identities
    packet=writer_packet_v4(worker,run,dossier)
    later={m['moment_id']:m for m in run['input_refs'].get('account_memory') or []}
    with worker.repo.connection() as conn:
        team={r['transcript_id'] for r in conn.execute("SELECT transcript_id FROM transcripts WHERE transcript_id=ANY(%s) "
              "AND call_type='internal'",(sorted({e.get('transcript_id') for e in dossier['evidence'] if e.get('transcript_id')}),))}
    marked=[]
    for e,item in zip(packet['evidence'],dossier['evidence']):
        extra={}
        if item.get('transcript_id') in team: extra['evidence_class']='team_practice'
        dates=[later[m]['date'] for m in item.get('moment_ids') or [] if m in later]
        if dates: extra['later_record']=f"what happened next ({max(dates)}), after the card's call"
        marked.append({**e,**extra})
    packet['evidence']=marked
    packet['people']=identities.writer_view(run['input_refs'].get('identities') or [])
    packet['what_happened_next']=[{'date':m['date'],'what':m['kind'],'from':'an internal meeting' if m['evidence_class']=='team_practice'
                                   else 'a later call with the account'} for m in later.values()]
    return packet

def writer_packet_v4(worker,run,dossier):
    """Writer v5's user message (E.B33): v4's packet, the card's fields including its guardrail, and the knowledge base's
    insider terms and offer descriptors (interface 5), so the first-touch checklist and the offers read the same data the
    checks do."""
    from . import turns
    from .first_touch import pinned_data
    packet=writer_packet_v3(run,dossier)
    # A turn's words without the "Speaker:" its transcript line begins with: the speaker has its own field, and the writer
    # copied the label into the copy ("Steve's iPhone: Okay, got it.", N1 shakedown). Writer v5 only; v3 and v4 replay as sent.
    packet['evidence']=[{**e,'excerpt':turns.words(e.get('excerpt'),e.get('speaker'))} for e in packet['evidence']]
    card=((run['input_refs']['angle'].get('body') or {}).get('card')) or {}
    if card: packet['card']={k:card[k] for k in CARD_FIELDS_V5 if card.get(k) not in (None,'',[])}
    data=pinned_data(worker.models.knowledge_base_root)
    packet['insider_terms']=[{'term':t['term'],'plain':t['plain']} for t in data['insider_terms'].get('terms') or []]
    packet['offer_descriptors']=[{'offer':o['offer'],'descriptors':o['descriptors'],'who_does_what':o.get('who_does_what')}
                                 for o in data['offer_descriptors'].get('offers') or []]
    return packet

def provenance_v4(worker,run,dossier=None):
    """v3's provenance and the first-touch data the checks read (insider terms, offer descriptors), pinned with the brief.
    A brief of writer v5.1 records its writer, so the checks hold it to its three Reels at Gate 2 too (NP.B10); a v5 brief's
    provenance is unchanged."""
    from .first_touch import pinned_data
    from ..settings_store import IDENTITY_WRITERS,PREMISE_WRITERS,THREE_REEL_WRITERS
    writer=writer_of(run)
    return {**provenance_v3(worker,run,dossier),**pinned_data(worker.models.knowledge_base_root),
            **({'writer':writer} if writer in THREE_REEL_WRITERS+PREMISE_WRITERS else {}),
            # Writer v5.2 (Phase N8): the identity records and which evidence is team practice, so the Gate 2 checks
            # re-run the naming, linking and internal-meeting rules without the database.
            **(identity_provenance(worker,run,dossier) if writer in IDENTITY_WRITERS else {})}

def identity_provenance(worker,run,dossier):
    """The run's frozen identity records, the identities its evidence is built on (the speakers and accounts of its calls), and
    the evidence calls that are internal meetings (team practice, D24)."""
    from .. import identities
    ids=sorted({e.get('transcript_id') for e in (dossier or {}).get('evidence',[]) if e.get('transcript_id')})
    found=run['input_refs'].get('identities') or []
    with worker.repo.connection() as conn:
        team=[r['transcript_id'] for r in conn.execute(
            "SELECT transcript_id FROM transcripts WHERE transcript_id=ANY(%s) AND call_type='internal' ORDER BY 1",(ids,))]
        built_on=sorted(identities.ids_for(found,document_ids=ids,conn=conn))
    return {'identities':found,'identity_ids':built_on,'team_practice_transcripts':team}

def provenance_v3(worker,run,dossier=None):
    """v2's provenance and Whitney's belief statements, so the ledger can be rebuilt at Gate 2 without the knowledge base."""
    from .runtime import knowledge
    from ..cycle.verification import BELIEF_DOCUMENT,belief_index
    kb=knowledge(worker,run)
    document=getattr(kb,'document',None)
    return {**provenance_v2(worker,run,dossier),'beliefs':belief_index(document(BELIEF_DOCUMENT)) if document else None}

def provenance_v2(worker,run,dossier=None):
    """Pinned inputs for the header, and what the Gate 2 checks need to re-run without the worker's settings."""
    from .runtime import knowledge
    kb=knowledge(worker,run)
    def doc(key):
        d=kb.document(key)
        return {'key':key,'version':d.entry.version,'sha256':d.sha256} if d else None
    return {'pinned_inputs':{'knowledge_base':{'version':kb.version,'sha256':kb.sha256},'offer_sheet':doc('offer_sheet'),
                             'content_plan':doc('content_plan'),'published_history':'incomplete_legacy_catalogue_missing'},
            'knowledge_base_keys':[d.entry.key for d in kb.documents],
            'roster':[{k:r[k] for k in ('name','role','status','aliases')} for r in kb.roster],
            # Internal figures the Gate 2 checks block in public copy (L.B5).
            'internal_terms':[{'term':t['term'],'item_id':t['item_id']} for t in kb.internal_terms],
            # Clients who may not be named (section 2.4 condition 7), with the dossier's calls that are theirs.
            'clients':unnamed_clients(worker,dossier)}

def unnamed_clients(worker,dossier):
    """The reviewed client list without consent to be named, each with the transcripts in this dossier that are its own
    (an approver's clearance on that evidence allows the name)."""
    repo=getattr(worker,'repo',None)
    if repo is None: return []
    ids=sorted({e.get('transcript_id') for e in (dossier or {}).get('evidence',[]) if e.get('transcript_id')})
    with repo.connection() as conn:
        if not conn.execute("SELECT to_regclass('public.clients') AS t").fetchone()['t']: return []
        owners={r['transcript_id']:r['client_id'] for r in conn.execute(
            'SELECT transcript_id,client_id FROM transcripts WHERE transcript_id=ANY(%s) AND client_id IS NOT NULL',(ids,))}
        return [{'client_id':c['client_id'],'name':c['name'],'aliases':list(c['aliases'] or []),'consent':c['consent'],
                 'transcript_ids':sorted(t for t,o in owners.items() if o==c['client_id'])}
                for c in conn.execute("SELECT client_id,name,aliases,consent FROM clients WHERE consent<>'may_name' ORDER BY client_id")]

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
