from ..publications import confirmed
import copy
from datetime import datetime,UTC
from psycopg.types.json import Jsonb
from ..repository import insert,identifier
from ..store import canonical_hash,JsonStore
from .contracts import BriefDocument,Dossier,EvidenceItem,WORKFLOW
from .inputs import assert_packet,verify_evidence,source_allowed
from .validation import checks,hash_brief

def authorize(repo,actor,action='edit'):
    allowed=repo.settings.brief_approvers if action in {'approve','clearance','review'} else tuple(set(repo.settings.brief_approvers+repo.settings.brief_editors))
    if not actor or actor not in allowed:
        raise PermissionError('Configured brief capability is required')

def locked(conn,brief_id,expected_hash):
    row=conn.execute('SELECT * FROM content_briefs WHERE brief_id=%s FOR UPDATE',(brief_id,)).fetchone()
    if not row or row['content_hash']!=expected_hash: raise ValueError('Brief changed; refresh before saving')
    if conn.execute('SELECT 1 FROM content_briefs WHERE supersedes_id=%s',(brief_id,)).fetchone():
        raise ValueError('Brief was superseded; refresh before saving')
    if hash_brief(row)!=row['content_hash']: raise ValueError('Stored brief content integrity failed')
    return row

def dossier(row):
    return Dossier.model_validate({'angle':row['content_body']['provenance']['angle'],'evidence':row['selected_evidence'],
        'prior':row['prior_content_context'],'queries':[],'audit':[],
        'coverage':(row['research_gaps'] or {}).get('coverage',{}),'gaps':(row['research_gaps'] or {}).get('items',[]),
        'brand':{'hash':row['content_body']['provenance']['brand_hash']}})

def semantic_hash(document):
    value=copy.deepcopy(document)
    for question in value.get('open_questions',[]): question['answer']=None
    return canonical_hash(value)

def prior_state(conn,row):
    result=[]
    for item in row['prior_content_context']:
        a=conn.execute('SELECT content_hash,approval_status FROM content_angles WHERE angle_id=%s',(item['angle_id'],)).fetchone()
        if not a: result.append({'angle_id':item['angle_id'],'missing':True}); continue
        publications=confirmed(conn,item['angle_id'])
        briefs=[r for r in conn.execute("SELECT brief_id,content_hash,approval_status FROM content_briefs WHERE angle_id=%s AND approval_status='approved' AND brief_id<>%s ORDER BY brief_id",(item['angle_id'],row['brief_id']))]
        result.append({'angle_id':item['angle_id'],**a,'publications':publications,'approved_briefs':briefs})
    return canonical_hash(result)

def blockers(conn,row):
    reasons=[]
    if row['approval_status']=='approved' and (row['approved_hash']!=row['content_hash'] or not row['approved_by'] or not row['approved_at']):
        reasons.append('Brief approval is not bound to the current content and verified actor/time')
    try:
        if hash_brief(row)!=row['content_hash']: raise ValueError('Brief content hash changed')
        assert_packet(conn,row['content_body']['provenance']['angle'])
        verify_evidence(conn,row['selected_evidence'])
    except ValueError as error: reasons.append(str(error))
    if conn.execute('SELECT 1 FROM content_briefs WHERE supersedes_id=%s',(row['brief_id'],)).fetchone(): reasons.append('A replacement brief exists')
    review=row['content_body'].get('review',{})
    reasons.extend(f['message'] for f in checks(row['content_body']['document'],dossier(row),review.get('clearances')) if f['severity']=='blocking')
    reasons.extend(f['message'] for f in review.get('findings',[]) if f['severity']=='blocking')
    if review.get('support_reviewed_document_hash')!=semantic_hash(row['content_body']['document']):
        reasons.append('Changed document requires a scoped grounding/differentiation review')
    if any(q['required'] and not (q['answer'] or '').strip() for q in row['content_body']['document']['open_questions']):
        reasons.append('Required questions remain unanswered')
    if not review.get('history_acknowledged'): reasons.append('Acknowledge the admitted-archive/legacy-history limitation')
    if review.get('history_state') and review['history_state']!=prior_state(conn,row): reasons.append('Related prior use changed; review the current coverage')
    return list(dict.fromkeys(reasons))

def get(repo,brief_id,actor=None):
    with repo.connection() as conn:
        row=conn.execute('SELECT * FROM content_briefs WHERE brief_id=%s',(brief_id,)).fetchone()
        if not row: raise ValueError('Brief not found')
        reasons=blockers(conn,row)
        row['has_replacement']=bool(conn.execute('SELECT 1 FROM content_briefs WHERE supersedes_id=%s',(brief_id,)).fetchone())
        row['can_approve']=not reasons and actor in repo.settings.brief_approvers and row['approval_status']=='pending'
        row['can_edit']=actor in set(repo.settings.brief_approvers+repo.settings.brief_editors) and not row['has_replacement']
        row['can_review']=actor in repo.settings.brief_approvers and not row['has_replacement']
        row['blockers']=reasons; row['can_consume']=row['approval_status']=='approved' and not reasons
        return row

def versions(repo,brief_id):
    with repo.connection() as conn:
        row=conn.execute('SELECT brief_id,supersedes_id FROM content_briefs WHERE brief_id=%s',(brief_id,)).fetchone()
        if not row: raise ValueError('Brief not found')
        seen=set()
        while row['supersedes_id']:
            if row['brief_id'] in seen: raise ValueError('Brief version cycle')
            seen.add(row['brief_id']); row=conn.execute('SELECT brief_id,supersedes_id FROM content_briefs WHERE brief_id=%s',(row['supersedes_id'],)).fetchone()
        root=row['brief_id']
        return conn.execute("""WITH RECURSIVE chain AS (SELECT brief_id,supersedes_id,content_hash,approval_status,created_at,updated_by FROM content_briefs WHERE brief_id=%s
            UNION ALL SELECT b.brief_id,b.supersedes_id,b.content_hash,b.approval_status,b.created_at,b.updated_by FROM content_briefs b JOIN chain c ON b.supersedes_id=c.brief_id)
            SELECT * FROM chain ORDER BY created_at,brief_id""",(root,)).fetchall()

def replace(repo,conn,row,actor):
    new={k:copy.deepcopy(row[k]) for k in ('week_id','angle_id','angle_input_hash','content_body','selected_evidence','prior_content_context','research_gaps')}
    new.update({'brief_id':identifier('brief'),'supersedes_id':row['brief_id'],'updated_by':actor})
    new['content_hash']=hash_brief(new)
    insert(conn,'content_briefs',new)
    run_id=row['content_body']['provenance']['run_id']
    repo.event(conn,run_id,'brief_version_created','Brief replacement saved',details={'brief_id':new['brief_id'],'supersedes_id':row['brief_id'],'actor':actor})
    return {'brief_id':new['brief_id'],'content_hash':new['content_hash']}

EDITABLE={'title','reader_promise','positioning','why_now','core_insight','message_spine','audience_pain','narrative','evidence_boundaries',
    'claims','differentiation','prior_differences','voice','email','carousel_reader_job','carousel','reels',
    'creative_direction','accessibility','distribution','evaluation_signals','similarity_review','claims_requiring_consent','handoff_checklist'}

def edit(repo,brief_id,expected_hash,changes,actor):
    authorize(repo,actor)
    if not changes or set(changes)-EDITABLE: raise ValueError('Invalid brief editable fields')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
        document=BriefDocument.model_validate({**row['content_body']['document'],**changes}).model_dump(mode='json')
        row['content_body']['document']=document
        review=row['content_body']['review']
        review['locked_fields']=sorted(set(review['locked_fields'])|set(changes))
        review['findings']=checks(document,dossier(row),review.get('clearances'))
        return replace(repo,conn,row,actor)

def answers(repo,brief_id,expected_hash,answers,actor):
    authorize(repo,actor,'approve')
    if not answers or any(not isinstance(a,str) or not a.strip() for a in answers.values()): raise ValueError('Answers must be meaningful text')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        questions=row['content_body']['document']['open_questions']
        assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
        if not set(answers).issubset(q['question_id'] for q in questions): raise ValueError('Unknown question identifier')
        for q in questions:
            if q['question_id'] in answers: q['answer']=answers[q['question_id']]
        row['content_body']['review']['answer_provenance']={'actor':actor,'at':datetime.now(UTC).isoformat(),'kind':'editor_context_not_source_proof'}
        return replace(repo,conn,row,actor)

def review(repo,brief_id,expected_hash,claim_ids,reason,history_ack,actor):
    authorize(repo,actor,'review')
    if not reason.strip() or not history_ack: raise ValueError('A scoped review reason and history coverage acknowledgement are required')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        doc=row['content_body']['document']
        if len(claim_ids)!=len(doc['claims']) or set(claim_ids)!={c['claim_id'] for c in doc['claims']}:
            raise ValueError('Human review must cover every current claim exactly once')
        assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
        findings=checks(doc,dossier(row),row['content_body']['review'].get('clearances'))
        if any(f['severity']=='blocking' for f in findings): raise ValueError('Deterministic source/use/claim blockers cannot be waived')
        state=row['content_body']['review']
        state.update({'findings':findings,'support_reviewed_document_hash':semantic_hash(doc),'history_acknowledged':True,
            'history_state':prior_state(conn,row),'human_review':{'actor':actor,'reason':reason,'at':datetime.now(UTC).isoformat()}})
        return replace(repo,conn,row,actor)

def clearance(repo,brief_id,expected_hash,evidence_id,permission_reference,attribution_reference,actor):
    authorize(repo,actor,'clearance')
    if not permission_reference.strip() or not attribution_reference.strip(): raise ValueError('Actual permission and attribution references are required')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        evidence=next((e for e in row['selected_evidence'] if e['evidence_id']==evidence_id),None)
        assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
        if not evidence or not evidence['transcript_id']: raise ValueError('Unknown internal evidence clearance target')
        s=conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s',(evidence['transcript_id'],)).fetchone()
        if not source_allowed(s) or (s['use_restrictions'] or {}).get('public_use') is False:
            raise ValueError('Upstream source restriction cannot be overridden by a brief')
        state=row['content_body']['review']
        state.setdefault('clearances',{})[evidence_id]={'permission_reference':permission_reference,
            'attribution_reference':attribution_reference,'actor':actor,'at':datetime.now(UTC).isoformat()}
        state['findings']=checks(row['content_body']['document'],dossier(row),state['clearances'])
        return replace(repo,conn,row,actor)

def decide(repo,brief_id,expected_hash,decision,note,actor):
    authorize(repo,actor,'approve')
    if decision not in {'approved','rejected'} or decision=='rejected' and not (note or '').strip(): raise ValueError('Invalid brief decision or missing rejection reason')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        if row['approval_status']!='pending': raise ValueError('Brief version has already been decided')
        reasons=blockers(conn,row)
        if decision=='approved' and reasons: raise ValueError('; '.join(reasons))
        conn.execute('UPDATE content_briefs SET approval_status=%s,approved_hash=%s,approved_by=%s,approved_at=%s,review_note=%s,updated_at=now() WHERE brief_id=%s',
            (decision,expected_hash if decision=='approved' else None,actor if decision=='approved' else None,
                datetime.now(UTC) if decision=='approved' else None,note,brief_id))
        rid=row['content_body']['provenance']['run_id']
        repo.event(conn,rid,'gate_two_'+decision,'Gate 2 decision recorded; no production jobs queued',details={'brief_id':brief_id,'actor':actor,'note':note})
        conn.execute('UPDATE pipeline_runs SET status=%s,current_message=%s,finished_at=now(),updated_at=now() WHERE run_id=%s',
            ('completed','Gate 2 '+decision+'; production remains separate',rid))
        return {'brief_id':brief_id,'approval_status':decision}

def revise(repo,brief_id,expected_hash,instructions,actor,mode='replay',added_evidence=None):
    authorize(repo,actor)
    if not instructions.strip(): raise ValueError('Revision instructions are required')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        from .workflow import queue_in_transaction
        items=[]
        if added_evidence:
            items=[EvidenceItem.model_validate(e) for e in added_evidence]
            verify_evidence(conn,items)
        result=queue_in_transaction(repo,conn,row['angle_id'],actor,mode,revision=brief_id,instructions=instructions,
            added_evidence=[e.model_dump(mode='json') for e in items])
        return result

def research(repo,angle_id):
    with repo.connection() as conn:
        if not conn.execute('SELECT 1 FROM content_angles WHERE angle_id=%s',(angle_id,)).fetchone(): raise ValueError('Angle not found')
        run=conn.execute("SELECT * FROM pipeline_runs WHERE input_refs->>'workflow'=%s AND input_refs->'angle'->>'angle_id'=%s ORDER BY created_at DESC LIMIT 1",(WORKFLOW,angle_id)).fetchone()
        if not run: return {'status':'not_started','jobs':[],'dossier':None}
        jobs=conn.execute('SELECT job_id,stage,status,current_step,current_message,completed_units,total_units,error_summary,result_refs FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,job_id',(run['run_id'],)).fetchall()
        item=next((j for j in jobs if j['stage']=='brief_context' and j['status']=='completed'),None) or next((j for j in jobs if j['stage']=='brief_research' and j['status']=='completed'),None)
    value=None
    if item:
        value=JsonStore(repo.settings.artifact_root).read_json(item['result_refs']['artifact'])
        if canonical_hash(value)!=item['result_refs']['hash']: raise ValueError('Research artifact integrity failed')
        with repo.connection() as conn: verify_evidence(conn,value['evidence'])
    store=JsonStore(repo.settings.artifact_root); cost_path=f'brief-runs/{run["run_id"]}/cost_summary.json'
    return {'status':run['status'],'run_id':run['run_id'],'input_hash':canonical_hash(run['input_refs']),'jobs':jobs,'dossier':value,
        'costs':store.read_json(cost_path) if store.path(cost_path).is_file() else None}

def markdown(row):
    d=row['content_body']['document']; lines=['# '+d['title'],'',d['angle_statement'],'','Audience: '+d['audience'],'','## Core insight','',d['core_insight'],'','## Message spine','']
    lines+=['- '+v for v in d['message_spine']]
    for label,key in [('Reader promise','reader_promise'),('Positioning','positioning'),('Audience pain','audience_pain'),('Why now','why_now'),('Reader decision','reader_decision'),('Differentiation','differentiation'),('Similarity review','similarity_review')]: lines+=['','## '+label,'',d[key] or 'Not supplied']
    for label,key in [('Narrative','narrative'),('Evidence boundaries','evidence_boundaries'),('Voice','voice'),('Creative direction','creative_direction'),('Accessibility','accessibility'),('Distribution','distribution'),('Evaluation','evaluation_signals'),('Handoff','handoff_checklist')]:
        lines+=['','## '+label,'']+['- '+v for v in d[key]]
    lines+=['','## Claims','']+['- '+c['text']+' ['+', '.join(c['evidence_ids'])+'] · '+c['kind']+' · '+c['source_status']+' · '+'; '.join(c['qualifications']) for c in d['claims']]
    lines+=['','## Email','',d['email']['reader_job'],d['email']['direction']]+['- '+v for v in d['email']['outline']]
    lines+=['','## Carousel','',d['carousel_reader_job']]+[str(s['number'])+'. '+s['direction'] for s in d['carousel']]
    for i,r in enumerate(d['reels'],1): lines+=['',f'## Reel {i}','',r['reader_job'],r['direction']]+['- '+v for v in r['outline']]
    lines+=['','## CTA','',d['cta']['text'],'','## Source passages','']
    for e in row['selected_evidence']: lines+=['### '+e['evidence_id']+' · '+e['title'],'',e['excerpt'],'','Qualifications: '+'; '.join(e['qualifications']),'']
    lines+=['','## Prior coverage','']+[p['angle_id']+': '+p['argument']+' — '+d['prior_differences'].get(p['angle_id'],'') for p in row['prior_content_context']]
    lines+=['','## Open questions','']+[q['text']+' — '+(q['answer'] or 'Unanswered') for q in d['open_questions']]
    lines+=['','## Consent requirements','']+['- '+v for v in d['claims_requiring_consent']]
    lines+=['','## Validation and coverage','']+['- '+f['severity']+': '+f['message'] for f in row['content_body']['review']['findings']]
    lines+=['- '+v for v in row['research_gaps']['items']]
    return '\n'.join(lines)+'\n'
