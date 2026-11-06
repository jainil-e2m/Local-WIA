from ..publications import confirmed
from ..gates.roles import access_for
import copy
import re
from datetime import datetime,UTC
from ..repository import insert,identifier
from ..store import canonical_hash
from ..artifacts import store_for
from .contracts import BriefDocument,Dossier,EvidenceItem,WORKFLOW
from .inputs import assert_packet,verify_evidence,source_allowed
from .validation import checks,hash_brief
from .contracts_v2 import SCHEMA_V2,EDITABLE_V2,BriefBodyV2
from .contracts_v3 import SCHEMA_V3,EDITABLE_V3
from .contracts_v4 import SCHEMA_V4,EDITABLE_V4

def version_of(row):
    return (row.get('content_body') or {}).get('schema_version') or 'brief_document_v1'

def is_v2(row):
    """A brief of the v2 family: contract v2, v3 (E.B23) or v4 (E.B33), which share v2's ledger checks, CTA,
    before-publishing answers and Gate 2 routes. Only the parts that read the body's shape ask is_v3 or is_v4."""
    return version_of(row) in (SCHEMA_V2,SCHEMA_V3,SCHEMA_V4)

def is_v3(row):
    """A brief whose ledger is built after writing: contract v3, or v4, which shares it (validation_v3.contract_for)."""
    return version_of(row) in (SCHEMA_V3,SCHEMA_V4)

def is_v4(row):
    return version_of(row)==SCHEMA_V4

def findings_v2(row,clearances=None,conn=None):
    """The checks of a v2-family brief: v2's, or v3's on the ledger built after writing. The rules and lint patterns are
    those of the knowledge-base version the brief pins (briefs/rules.py), never the version in force or today's files."""
    from .validation_v2 import checks_v2
    from .validation_v3 import checks_v3
    from .rules import pinned_rules
    body=row['content_body']
    checks_for=checks_v3 if is_v3(row) else checks_v2
    week={}
    if is_v4(row):
        # Contract v4's checks (E.B33, E.B34, E.B24), with the cycle's other current briefs for the week checks.
        from .validation_v4 import checks_v4
        from .asset_checks import week_siblings
        checks_for=checks_v4
        week={'siblings':week_siblings(conn,row)} if conn is not None else {}
    rules,problem=pinned_rules(conn,body['provenance'])
    found=checks_for(body['document'],dossier(row),body['provenance'],clearances if clearances is not None else body['review'].get('clearances'),rules,**week)
    if problem: found.append({'severity':'blocking','claim_id':None,'gate':False,'section':'style','message':problem})
    return found

def reviewed_hash(row):
    if is_v2(row):
        from .validation_v2 import semantic_hash_v2
        return semantic_hash_v2(row['content_body']['document'])
    return semantic_hash(row['content_body']['document'])

def claims_of(row):
    document=row['content_body']['document']
    return document['body']['claims'] if is_v2(row) else document['claims']

def authorize(repo,actor,action='edit'):
    # Approve, clearance and review need the approver role; everything else the editor role (gates/roles.py, 0.B9).
    if not actor or not access_for(repo.settings,actor).can('decide' if action in {'approve','clearance','review'} else 'edit'):
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

def blocker_list(conn,row):
    """What stops approval, each as (kind, the check's own message). The kinds are the ones Gate 2 names in plain words
    (5.F2, plain_blocker): removed_material, open_question, cta_unconfirmed, blocking_finding, stale, claims_check."""
    reasons=[]
    # Built on material removed at a client's request (6.B12): marked, never approved or consumed again.
    from ..removal import mark_of
    removed=mark_of(conn,'brief',row['brief_id'])
    if removed: reasons.append(('removed_material',removed['note']))
    if row['approval_status']=='approved' and (row['approved_hash']!=row['content_hash'] or not row['approved_by'] or not row['approved_at']):
        reasons.append(('stale','Brief approval is not bound to the current content and verified actor/time'))
    try:
        if hash_brief(row)!=row['content_hash']: raise ValueError('Brief content hash changed')
        assert_packet(conn,row['content_body']['provenance']['angle'])
        verify_evidence(conn,row['selected_evidence'])
    except ValueError as error: reasons.append(('stale',str(error)))
    if conn.execute('SELECT 1 FROM content_briefs WHERE supersedes_id=%s',(row['brief_id'],)).fetchone(): reasons.append(('stale','A replacement brief exists'))
    review=row['content_body'].get('review',{})
    if is_v2(row):
        # Version 2 (E.B15 b): the v2 ledger checks, which include the CTA and before-publishing answers.
        for f in findings_v2(row,conn=conn):
            if f['severity']!='blocking': continue
            kind=('cta_unconfirmed' if f.get('section')=='cta' else 'open_question') if f.get('gate') else 'blocking_finding'
            reasons.append((kind,f['message']))
    else:
        reasons.extend(('blocking_finding',f['message']) for f in checks(row['content_body']['document'],dossier(row),review.get('clearances')) if f['severity']=='blocking')
        reasons.extend(('blocking_finding',f['message']) for f in review.get('findings',[]) if f['severity']=='blocking')
    if review.get('support_reviewed_document_hash')!=reviewed_hash(row):
        reasons.append(('claims_check','Changed document requires a scoped grounding/differentiation review'))
    if not is_v2(row) and any(q['required'] and not (q['answer'] or '').strip() for q in row['content_body']['document']['open_questions']):
        reasons.append(('open_question','Required questions remain unanswered'))
    if not review.get('history_acknowledged'): reasons.append(('claims_check','Acknowledge the admitted-archive/legacy-history limitation'))
    if review.get('history_state') and review['history_state']!=prior_state(conn,row): reasons.append(('stale','Related prior use changed; review the current coverage'))
    return list(dict.fromkeys(reasons))

# With gates.one_click only these stop an approval and a pack; the rest of the list stays on record as reminders.
HARD_BLOCKERS=('removed_material','stale')

def blockers(conn,row,found=None):
    from ..settings_store import value as setting
    found=blocker_list(conn,row) if found is None else found
    if setting('gates.one_click',conn): found=[(kind,message) for kind,message in found if kind in HARD_BLOCKERS]
    return list(dict.fromkeys(message for _,message in found))

# Gate 2's blockers in the words a non-technical reviewer reads (5.F2, R50): what is wrong and what to do, by kind. A
# blocking finding keeps the check's own sentence, which names the line; identifiers never reach the screen.
_PLAIN={
    'removed_material':("This brief is built on material removed at a client's request.",
                        'Do not approve or publish it; develop a new card from other calls.'),
    'open_question':('A required question has no answer yet.','Answer each required item under "Before publishing".'),
    'cta_unconfirmed':("The call to action is still the writer's suggestion.",'Confirm the call to action, or choose no explicit ask.'),
    'claims_check':('Nobody has recorded a check of the claims in this version yet.','Read the claims and record your check.'),
    'role':('Only an approver can approve this brief.','You can edit it, add context and refresh it; ask an approver to approve it.'),
}
_STALE=[
    ('A replacement brief exists','A newer version of this brief exists.','Open the newest version from the versions list.'),
    ('Brief content hash changed','This version changed after it was saved.','Reload the brief.'),
    ('Related prior use changed','Earlier content on this point changed since your check.','Check the claims again, then approve.'),
    ('approval is not bound','The approval no longer matches this version.','Review and approve this version again.'),
]

def plain_blocker(kind,message):
    """One blocker as the screen shows it: {kind, title, action, detail}."""
    import re as _re
    detail=_re.sub(r'\b(?:ev|evidence|passage|moment|claim|transcript|brief|angle)_[A-Za-z0-9_]+\b','an earlier item',message)
    if kind in _PLAIN:
        title,action=_PLAIN[kind]
    elif kind=='stale':
        title,action=next(((t,a) for key,t,a in _STALE if key in message),
                          ('The approved card or the call excerpts changed since this brief was written.','Refresh the brief so it is written from the current card.'))
    else:
        title,action='The copy has a problem to fix.','Edit the line it names, or refresh the brief with feedback.'
    return {'kind':kind,'title':title,'action':action,'detail':detail if kind=='blocking_finding' else None}

def blocker_items(conn,row,access,found=None):
    """The screen's list: the brief's blockers and, for a person who may not approve, the role (5.F2)."""
    items=[plain_blocker(kind,message) for kind,message in (blocker_list(conn,row) if found is None else found)]
    if row['approval_status']=='pending' and not access.can('decide'): items.append(plain_blocker('role',''))
    return list({(i['kind'],i['title'],i['detail']):i for i in items}.values())

def get(repo,brief_id,actor=None):
    with repo.connection() as conn:
        return _get(repo,conn,brief_id,actor)

def _get(repo,conn,brief_id,actor):
    row=conn.execute('SELECT * FROM content_briefs WHERE brief_id=%s',(brief_id,)).fetchone()
    if not row: raise ValueError('Brief not found')
    # The checks read every passage the brief cites: once a read, for both of the lists made from them.
    found=blocker_list(conn,row)
    reasons=blockers(conn,row,found)
    row['blocker_items']=blocker_items(conn,row,access_for(repo.settings,actor),found)
    row['has_replacement']=bool(conn.execute('SELECT 1 FROM content_briefs WHERE supersedes_id=%s',(brief_id,)).fetchone())
    access=access_for(repo.settings,actor)
    row['can_approve']=not reasons and access.can('decide') and row['approval_status']=='pending'
    row['can_edit']=access.can('edit') and not row['has_replacement']
    row['can_review']=access.can('decide') and not row['has_replacement']
    # A published final is recorded against the approved content only (L.B9, knowledge/capture.py).
    row['can_record_published']=access.can('edit') and row['approval_status']=='approved' and row['approved_hash']==row['content_hash']
    # Whether production may consume this brief, through the hand-off view (E.B23, briefs/handoff.py): an approved brief of
    # any contract version with no blocker. Computed on every read, never stored (plan section 1.9.7). A v4 brief gets a
    # content pack (packs/queue.py, NP.B2); a v1 brief keeps the v1 pack path; v2 and v3 briefs are told to re-develop as v4.
    row['blockers']=reasons; row['can_consume']=row['approval_status']=='approved' and not reasons
    row['schema_version']=row['content_body'].get('schema_version','brief_document_v1')
    # The anchor piece and the pieces a person may choose from at Gate 2 (E.B23).
    from .handoff import anchor_of
    row['anchor']=anchor_of(row)
    # Context and attested facts (5.B7): this version's, then the card's given since, which the next refresh carries.
    from .context import view as context_view
    row['context_items']=context_view(conn,row)
    row['locked_fields']=row['content_body'].get('review',{}).get('locked_fields',[])
    # Review rubric 2.3a as the decision form shows it (E.X9: WIA rates briefs as well as cards, gates/rubric.py).
    from ..gates.rubric import form
    row['rubric']=form() if row['approval_status']=='pending' else None
    # The account the brief's card is about, with its current state and what happened next (3.B17, D25), for the approver.
    from ..repository import account_memory
    moments=[r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(row['angle_id'],))]
    row['account_memory']=account_memory(conn,moments)
    from ..removal import mark_of
    row['removed_material']=mark_of(conn,'brief',brief_id)
    return row

def handoff(repo,brief_id,actor=None):
    """The version-independent production hand-off of a brief (E.B23, briefs/handoff.py)."""
    from .handoff import view
    with repo.connection() as conn:
        return view(conn,_get(repo,conn,brief_id,actor))

def handoff_v2(repo,brief_id,actor=None):
    """Hand-off version 2 (Phase NP, NP.B1): what the content pack reads (briefs/handoff.py view_v2)."""
    from .handoff import view_v2
    with repo.connection() as conn:
        return view_v2(conn,_get(repo,conn,brief_id,actor),repo.settings)

def versions(repo,brief_id):
    with repo.connection() as conn:
        row=conn.execute('SELECT brief_id,supersedes_id FROM content_briefs WHERE brief_id=%s',(brief_id,)).fetchone()
        if not row: raise ValueError('Brief not found')
        seen=set()
        while row['supersedes_id']:
            if row['brief_id'] in seen: raise ValueError('Brief version cycle')
            seen.add(row['brief_id']); row=conn.execute('SELECT brief_id,supersedes_id FROM content_briefs WHERE brief_id=%s',(row['supersedes_id'],)).fetchone()
        root=row['brief_id']
        # In lineage order (a version's depth from the first), which is the order they were made.
        rows=conn.execute("""WITH RECURSIVE chain AS (SELECT brief_id,supersedes_id,content_hash,approval_status,created_at,updated_by,content_body,0 AS depth FROM content_briefs WHERE brief_id=%s
            UNION ALL SELECT b.brief_id,b.supersedes_id,b.content_hash,b.approval_status,b.created_at,b.updated_by,b.content_body,c.depth+1 FROM content_briefs b JOIN chain c ON b.supersedes_id=c.brief_id)
            SELECT chain.*,r.input_refs AS run_refs,r.triggered_by FROM chain LEFT JOIN pipeline_runs r ON r.run_id=chain.content_body->'provenance'->>'run_id'
            ORDER BY chain.depth,chain.created_at,chain.brief_id""",(root,)).fetchall()
        return [version_view(r) for r in rows]

# Why each version exists, in the reviewer's words (5.F5 d).
_CHANGES={'edit':'Edited by hand','answers':'Answered the before-publishing items','check':'Recorded the check of the claims',
          'permission':"Recorded a client's permission",'cta':'Confirmed the call to action','anchor':'Chose the piece written first',
          'context':'Added context','refresh':'Refreshed with feedback','decision':'Decided'}
_CONTEXT_KINDS={'context':'context','attested_fact':'an attested fact','paraphrase':"a paraphrase of the client's words"}

def version_view(r):
    """One version for the versions list: who made it and why. Versions saved before 22 October carry no change record;
    their reason is read from the run that wrote them."""
    change=(r['content_body'] or {}).get('change') or {}
    refs=r.get('run_refs') or {}
    kind=change.get('kind')
    if not kind:
        if not r['supersedes_id']: kind='generated'
        elif refs.get('revision_of')==r['supersedes_id']: kind='refresh'
        else: kind='update'
    author=change.get('by') or change.get('author') if kind!='context' else change.get('author') or change.get('by')
    if kind=='generated':
        reason='Written by the system from the approved card'; author=refs.get('queued_by') or r.get('triggered_by')
    elif kind=='refresh':
        instructions=change.get('instructions') if change else refs.get('instructions')
        reason='Refreshed with feedback'+(f': {instructions}' if instructions else '')
        author=change.get('by') or refs.get('queued_by') or r.get('triggered_by')
    elif kind=='context':
        reason=f"Added {_CONTEXT_KINDS.get(change.get('context_kind'),'context')}: {change.get('text','')}"
    elif kind=='edit':
        fields=change.get('fields') or []
        reason='Edited '+(f"{len(fields)} field{'s' if len(fields)!=1 else ''}" if fields else 'the brief')
    else:
        reason=_CHANGES.get(kind,'Saved a new version (no reason recorded)')
    return {'brief_id':r['brief_id'],'supersedes_id':r['supersedes_id'],'content_hash':r['content_hash'],'approval_status':r['approval_status'],
            'created_at':r['created_at'],'updated_by':r['updated_by'],'author':author or r['updated_by'],'kind':kind,'reason':reason,
            'fields':change.get('fields') or [],'unlocked':change.get('unlocked') or []}

def replace(repo,conn,row,actor,change=None):
    """A new version of the brief. `change` says why (the versions list, 5.F5 d): its kind and details; who and when are
    added here."""
    new={k:copy.deepcopy(row[k]) for k in ('week_id','angle_id','angle_input_hash','content_body','selected_evidence','prior_content_context','research_gaps')}
    new['content_body']['change']={'kind':'update',**(change or {}),'by':str(actor),'at':datetime.now(UTC).isoformat()}
    new.update({'brief_id':identifier('brief'),'supersedes_id':row['brief_id'],'updated_by':actor})
    new['content_hash']=hash_brief(new)
    insert(conn,'content_briefs',new)
    run_id=row['content_body']['provenance']['run_id']
    repo.event(conn,run_id,'brief_version_created','Brief replacement saved',details={'brief_id':new['brief_id'],'supersedes_id':row['brief_id'],'actor':actor})
    return {'brief_id':new['brief_id'],'content_hash':new['content_hash']}

EDITABLE={'title','reader_promise','positioning','why_now','core_insight','message_spine','audience_pain','narrative','evidence_boundaries',
    'claims','differentiation','prior_differences','voice','email','carousel_reader_job','carousel','reels',
    'creative_direction','accessibility','distribution','evaluation_signals','similarity_review','claims_requiring_consent','handoff_checklist'}

def weakens_checks(before,after):
    """Whether a v2 edit answers a before-publishing item, or lowers or drops a required one."""
    kept={i['text']:i for i in after}
    lowered=any(i['required'] and not (kept.get(i['text']) or {}).get('required') for i in before)
    answers={i['text']:(i.get('answer') or '').strip() for i in before}
    return lowered or any((i.get('answer') or '').strip() and (i.get('answer') or '').strip()!=answers.get(i['text'],'') for i in after)

def edit_v2(repo,conn,row,changes,actor):
    """A section edit of a v2 or v3 brief (E.F4, E.B23); the approved angle and the CTA have their own routes. `anchor`
    is a person's choice of the piece production writes first (briefs/handoff.py): a piece key, or null for the rule."""
    from .handoff import KEEP,choose_anchor
    from . import paths
    editable=EDITABLE_V4 if is_v4(row) else EDITABLE_V3 if is_v3(row) else EDITABLE_V2
    fields={k:v for k,v in (changes or {}).items() if k!='anchor'}
    # A change names a section or any field inside one by its path (5.F1, 5.F4: format_plan.email.subject_options[0]).
    if not changes or any(paths.section(k) not in editable for k in fields):
        raise ValueError(f"Editable v{4 if is_v4(row) else 3 if is_v3(row) else 2} sections (or any field inside one, by its path): "+', '.join(sorted(editable|{'anchor'})))
    assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
    document=row['content_body']['document']
    review=row['content_body']['review']
    changed=[]
    if fields:
        before=document['body']['before_publishing']
        edited,changed=paths.apply(document['body'],fields,editable)
        if not changed: raise ValueError('Nothing changed: every field already has that text')
        sections={paths.section(p):edited[paths.section(p)] for p in changed}
        if is_v3(row):
            # The writer's sections only; the ledger is rebuilt from them with no model call, keeping the verdicts of
            # unchanged statements. Only the lines the person changed are theirs (5.F5).
            from .validation_v3 import rebuild
            document['body']=rebuild(row,sections,person_fields=changed)
        else:
            document['body']=BriefBodyV2.model_validate({**document['body'],**sections}).model_dump(mode='json')
        if 'before_publishing' in sections and weakens_checks(before,document['body']['before_publishing']):
            # Answering an item, making a required one optional or dropping it is the approver's (S.B3): the
            # /answers route records who answered. An editor may still add or reword a check.
            authorize(repo,actor,'approve')
            review['answer_provenance']={'actor':actor,'at':datetime.now(UTC).isoformat(),'kind':'section_edit'}
        document['header']['point_of_view']=document['body']['point_of_view']
        document['header']['intended_shift']=document['body']['intended_shift']
        # A person's edit locks the lines it changed, never the whole section (5.F5): a refresh keeps them verbatim.
        review['locked_fields']=paths.merge_locks(review['locked_fields'],changed)
    # The anchor is not part of the reviewed document (semantic_hash_v2), so choosing it needs no new check of the claims.
    choose_anchor(row,changes['anchor'] if 'anchor' in changes else KEEP,actor)
    review['findings']=findings_v2(row,conn=conn)
    return replace(repo,conn,row,actor,change={'kind':'edit','fields':changed} if changed else {'kind':'anchor'})

def edit(repo,brief_id,expected_hash,changes,actor):
    authorize(repo,actor)
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        if is_v2(row):
            return edit_v2(repo,conn,row,changes,actor)
        if not changes or set(changes)-EDITABLE: raise ValueError('Invalid brief editable fields')
        assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
        document=BriefDocument.model_validate({**row['content_body']['document'],**changes}).model_dump(mode='json')
        row['content_body']['document']=document
        review=row['content_body']['review']
        review['locked_fields']=sorted(set(review['locked_fields'])|set(changes))
        review['findings']=checks(document,dossier(row),review.get('clearances'))
        return replace(repo,conn,row,actor,change={'kind':'edit','fields':sorted(changes)})

def answers(repo,brief_id,expected_hash,answers,actor):
    authorize(repo,actor,'approve')
    if not answers or any(not isinstance(a,str) or not a.strip() for a in answers.values()): raise ValueError('Answers must be meaningful text')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        if is_v2(row):
            # Before-publishing items are answered by position: P1, P2, ...
            items=row['content_body']['document']['body']['before_publishing']
            ids={f'P{i}':item for i,item in enumerate(items,1)}
            if not set(answers).issubset(ids): raise ValueError('Unknown before-publishing item; use P1 to P'+str(len(items)))
            assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
            for key,value in answers.items(): ids[key]['answer']=value
            row['content_body']['review']['answer_provenance']={'actor':actor,'at':datetime.now(UTC).isoformat(),'kind':'editor_context_not_source_proof'}
            row['content_body']['review']['findings']=findings_v2(row,conn=conn)
            return replace(repo,conn,row,actor,change={'kind':'answers'})
        questions=row['content_body']['document']['open_questions']
        assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
        if not set(answers).issubset(q['question_id'] for q in questions): raise ValueError('Unknown question identifier')
        for q in questions:
            if q['question_id'] in answers: q['answer']=answers[q['question_id']]
        row['content_body']['review']['answer_provenance']={'actor':actor,'at':datetime.now(UTC).isoformat(),'kind':'editor_context_not_source_proof'}
        return replace(repo,conn,row,actor,change={'kind':'answers'})

def review(repo,brief_id,expected_hash,claim_ids,reason,history_ack,actor):
    authorize(repo,actor,'review')
    if not reason.strip() or not history_ack: raise ValueError('A scoped review reason and history coverage acknowledgement are required')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        doc=row['content_body']['document']; claims=claims_of(row)
        if len(claim_ids)!=len(claims) or set(claim_ids)!={c['claim_id'] for c in claims}:
            raise ValueError('Human review must cover every current claim exactly once')
        assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
        if is_v2(row):
            findings=findings_v2(row,conn=conn)
            # The CTA and before-publishing answers are settled at Gate 2 itself, not waived here.
            if any(f['severity']=='blocking' and not f.get('gate') for f in findings): raise ValueError('Deterministic source/use/claim blockers cannot be waived')
        else:
            findings=checks(doc,dossier(row),row['content_body']['review'].get('clearances'))
            if any(f['severity']=='blocking' for f in findings): raise ValueError('Deterministic source/use/claim blockers cannot be waived')
        state=row['content_body']['review']
        state.update({'findings':findings,'support_reviewed_document_hash':reviewed_hash(row),'history_acknowledged':True,
            'history_state':prior_state(conn,row),'human_review':{'actor':actor,'reason':reason,'at':datetime.now(UTC).isoformat()}})
        return replace(repo,conn,row,actor,change={'kind':'check'})

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
        state['findings']=findings_v2(row,state['clearances'],conn=conn) if is_v2(row) else checks(row['content_body']['document'],dossier(row),state['clearances'])
        return replace(repo,conn,row,actor,change={'kind':'permission'})

def confirm_cta(repo,brief_id,expected_hash,cta,actor):
    """A person confirms the v2 brief's CTA, or no explicit ask (R46; the first slice of 5.B2 and 4.B8's CTA check)."""
    authorize(repo,actor,'approve')
    from .contracts_v2 import BriefCTA
    choice=cta.get('choice')
    if choice not in {'explicit','no_explicit_ask'}: raise ValueError('Confirm an explicit CTA or no explicit ask')
    confirmed=BriefCTA.model_validate({'choice':choice,'track':cta.get('track'),'action':cta.get('action') if choice=='explicit' else None,
        'offer_connection':cta.get('offer_connection'),'chosen_by':'person'}).model_dump(mode='json')
    if re.search(r'\$\s?\d',confirmed['action'] or ''): raise ValueError('A CTA never states a price')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        if not is_v2(row): raise ValueError('CTA confirmation applies to version 2, 3 and 4 briefs')
        assert_packet(conn,row['content_body']['provenance']['angle']); verify_evidence(conn,row['selected_evidence'])
        from .validation_v2 import person_cta
        chosen=person_cta(row['content_body']['provenance']['angle'])
        if chosen and confirmed['action']!=chosen['action']: raise ValueError('A person chose this CTA at Gate 1; reframe the card to change it')
        document=row['content_body']['document']
        document['header']['cta']=document['body']['cta']=confirmed
        row['content_body']['review']['cta_confirmation']={'actor':actor,'at':datetime.now(UTC).isoformat()}
        row['content_body']['review']['findings']=findings_v2(row,conn=conn)
        return replace(repo,conn,row,actor,change={'kind':'cta'})

def record_decision(conn,row,decision,note,actor,*,reason_code=None,author=None,settings=None,rubric_ratings=None):
    """One decision and one label per Gate 2 decision (R45), once migration 005 is applied; the reviewer's ratings on
    rubric 2.3a go on the label when given (E.X9)."""
    if not conn.execute("SELECT to_regclass('public.decisions') AS t").fetchone()['t']:
        return None
    from ..gates.decisions import REASON_CODES,record
    if reason_code is not None and reason_code not in REASON_CODES: raise ValueError('Unknown reason code; use one of: '+', '.join(REASON_CODES))
    return record(conn,item_kind='brief',item_id=row['brief_id'],week_id=row['week_id'],
        disposition='approve' if decision=='approved' else 'reject',action='gate_two_'+decision,actor=actor,
        author=(author or '').strip() or actor,reason_code=reason_code,note=(note or '').strip() or None,
        expected_hash=row['content_hash'],details={'schema_version':row['content_body'].get('schema_version','brief_document_v1'),
        'angle_id':row['angle_id'],'run_id':row['content_body']['provenance']['run_id']},settings=settings,
        rubric_ratings=rubric_ratings)

def decide(repo,brief_id,expected_hash,decision,note,actor,*,reason_code=None,author=None,rubric_ratings=None,rubric_version=None):
    authorize(repo,actor,'approve')
    from ..gates.rubric import ratings
    rated=ratings(rubric_ratings,rubric_version)
    if decision not in {'approved','rejected'} or decision=='rejected' and not (note or '').strip(): raise ValueError('Invalid brief decision or missing rejection reason')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        if row['approval_status']!='pending': raise ValueError('Brief version has already been decided')
        reasons=blockers(conn,row)
        if decision=='approved' and reasons: raise ValueError('; '.join(reasons))
        conn.execute('UPDATE content_briefs SET approval_status=%s,approved_hash=%s,approved_by=%s,approved_at=%s,review_note=%s,updated_at=now() WHERE brief_id=%s',
            (decision,expected_hash if decision=='approved' else None,actor if decision=='approved' else None,
                datetime.now(UTC) if decision=='approved' else None,note,brief_id))
        decision_id=record_decision(conn,row,decision,note,actor,reason_code=reason_code,author=author,settings=repo.settings,
                                    rubric_ratings=rated)
        rid=row['content_body']['provenance']['run_id']
        # Approving a v4 brief starts its content pack in this transaction (NP.B2, D43c), through a savepoint: a pack that
        # cannot start is recorded as a failed run and the approval still commits. The approval itself authorises the start.
        pack,pack_note=None,None
        if decision=='approved':
            if not repo.settings.packs_enabled: pack_note='Content packs are off'
            elif not is_v4(row): pack_note='Re-develop this brief as a v4 brief to get a content pack'
            else:
                from ..packs.queue import start_in_transaction
                pack=start_in_transaction(repo,conn,row,actor)
        said=('; content pack queued' if pack and pack['status']!='failed' else '; the content pack could not be started' if pack
              else f'; no content pack: {pack_note}' if pack_note else '')
        repo.event(conn,rid,'gate_two_'+decision,'Gate 2 decision recorded'+said,
            details={'brief_id':brief_id,'actor':actor,'note':note,**({'pack_run':pack} if pack else {})})
        conn.execute('UPDATE pipeline_runs SET status=%s,current_message=%s,finished_at=now(),updated_at=now() WHERE run_id=%s',
            ('completed','Gate 2 '+decision+said,rid))
        return {'brief_id':brief_id,'approval_status':decision,**({'decision_id':decision_id} if decision_id else {}),
            **({'pack_run':pack} if pack else {}),**({'pack_note':pack_note} if pack_note else {})}

def revise(repo,brief_id,expected_hash,instructions,actor,mode='replay',added_evidence=None,unlock=None):
    """Refresh with feedback (5.B6): a revision run from the reviewer's instructions, live from the screen (replay is a
    test mode). The lines a person edited stay locked (5.F5) unless `unlock` releases them for this refresh."""
    authorize(repo,actor)
    if not instructions.strip(): raise ValueError('Revision instructions are required')
    with repo.connection() as conn:
        row=locked(conn,brief_id,expected_hash)
        from . import paths
        locks={paths.canonical(p) for p in row['content_body'].get('review',{}).get('locked_fields',[])}
        released=sorted({paths.canonical(p) for p in unlock or []})
        if set(released)-locks: raise ValueError('Only a locked line can be unlocked: '+', '.join(sorted(set(released)-locks)))
        from .workflow import queue_in_transaction
        items=[]
        if added_evidence:
            items=[EvidenceItem.model_validate(e) for e in added_evidence]
            verify_evidence(conn,items)
        result=queue_in_transaction(repo,conn,row['angle_id'],actor,mode,revision=brief_id,instructions=instructions,
            added_evidence=[e.model_dump(mode='json') for e in items],unlock=released)
        return result

def research(repo,angle_id):
    with repo.connection() as conn:
        if not conn.execute('SELECT 1 FROM content_angles WHERE angle_id=%s',(angle_id,)).fetchone(): raise ValueError('Angle not found')
        run=conn.execute("SELECT * FROM pipeline_runs WHERE input_refs->>'workflow'=%s AND input_refs->'angle'->>'angle_id'=%s ORDER BY created_at DESC LIMIT 1",(WORKFLOW,angle_id)).fetchone()
        # The angle's current brief version, for the link from card to brief (S.F4).
        latest=conn.execute("""SELECT b.brief_id FROM content_briefs b WHERE b.angle_id=%s AND NOT EXISTS
            (SELECT 1 FROM content_briefs n WHERE n.supersedes_id=b.brief_id) ORDER BY b.created_at DESC,b.brief_id LIMIT 1""",(angle_id,)).fetchone()
        brief_id=latest['brief_id'] if latest else None
        if not run: return {'status':'not_started','jobs':[],'dossier':None,'brief_id':brief_id}
        jobs=conn.execute('SELECT job_id,stage,status,current_step,current_message,completed_units,total_units,error_summary,result_refs,progress_details FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,job_id',(run['run_id'],)).fetchall()
        # A stage refused by a spent standing budget waits with the reason in words (6.B3), shown on the card (4.B1).
        waiting=next(((j['progress_details'] or {}).get('budget_reason') for j in jobs if j['status']=='waiting'
                      and (j['progress_details'] or {}).get('waiting_for')=='budget'),None)
        for j in jobs: j.pop('progress_details')
        item=next((j for j in jobs if j['stage']=='brief_context' and j['status']=='completed'),None) or next((j for j in jobs if j['stage']=='brief_research' and j['status']=='completed'),None)
    value=None
    if item:
        value=store_for(repo.settings).read_json(item['result_refs']['artifact'])
        if canonical_hash(value)!=item['result_refs']['hash']: raise ValueError('Research artifact integrity failed')
        with repo.connection() as conn: verify_evidence(conn,value['evidence'])
    store=store_for(repo.settings); cost_path=f'brief-runs/{run["run_id"]}/cost_summary.json'
    return {'status':run['status'],'run_id':run['run_id'],'input_hash':canonical_hash(run['input_refs']),'jobs':jobs,'dossier':value,
        'brief_id':brief_id,'mode':run['input_refs'].get('mode'),'waiting_reason':waiting,
        'error_summary':run['error_summary'],
        'costs':store.read_json(cost_path) if store.exists(cost_path) else None}

def markdown_v2(row):
    """The v2 or v3 brief as Whitney reads it: the WIA perspective first, then how the piece makes the point (E.F4). A v3
    brief has its Reel scripts, the caption's and the email's bodies, an optional reader decision and the ledger's status."""
    doc=row['content_body']['document']; h=doc['header']; b=doc['body']; a=b['approved_angle']
    lines=['# '+a['title'],'',a['core_perspective'],'']
    if b.get('sharpened_point'): lines+=['Sharper point (proposed): '+b['sharpened_point']['text'],'Why: '+b['sharpened_point']['reason'],'']
    lines+=['## WIA perspective','',b['wia_perspective'],'','## Supporting example','',b['supporting_example']['scene'],'',
        'What WIA did: '+b['supporting_example']['wia_move'],'','What the client contributed: '+b['supporting_example']['client_contribution'],'',
        '## Strategic purpose','',f"{b['strategic_purpose']['pillar']} · {b['strategic_purpose']['content_type'].replace('_',' ')}",'',b['strategic_purpose']['why_now'],'',
        '## Audience','',b['audience']['who'],'',b['audience']['reason_to_care'],'',
        '## Intended shift','','- Understand: '+b['intended_shift']['understand'],'- Believe: '+b['intended_shift']['believe'],*(['- Do: '+b['intended_shift']['do']] if b['intended_shift'].get('do') else []),'',
        '## Narrative outline','']
    lines+=['- Hook ('+x['style'].replace('_',' ')+'): '+x['text'] for x in b['narrative_outline']['hooks']]
    lines+=['- Problems, desires or symptoms: '+'; '.join(b['narrative_outline']['problems_desires_symptoms']),
        '- Main point: '+b['narrative_outline']['main_point'],'- Transformation: '+b['narrative_outline']['transformation'],'- CTA: '+b['narrative_outline']['cta'],'',
        '## Format plan','']
    plan=b['format_plan']
    for i,r in enumerate(plan['reels'],1):
        lines+=[f'### Reel {i}: {r["job"]}','','Cover: '+r['cover_text'],'Opening: '+r['spoken_opening'],f'Read time: about {r["read_time_seconds"]} seconds ({r["source"].replace("_"," ")})']+['- '+x for x in r['beats']]+['']
        if r.get('script'): lines+=['Script:','',r['script'],'']
    if plan.get('carousel'):
        lines+=['### Carousel: '+plan['carousel']['job'],'']+[f"{s['number']}. {s['job']}: {s['text']}" for s in plan['carousel']['slides']]+['']
    if plan.get('email'):
        e=plan['email']; middle=[e['body']] if 'body' in e else [e['argument'],'',e['transformation']]
        lines+=['### Email','','Subject options: '+' | '.join(e['subject_options']),'Preview: '+e['preview'],'',e['opening'],'',*middle,'',e['ending'],'']
    if plan.get('caption'):
        c=plan['caption']
        lines+=(['### Caption','',c['hook'],'',c['body'],'',c['ending'],''] if 'body' in c else
                ['### Caption','','Hook: '+c['hook'],'Adds: '+c['adds'],'Ending: '+c['ending'],''])
    if plan.get('stories'): lines+=['### Stories','']+['- '+x for x in plan['stories']['frames']]+['']
    cta=h['cta']
    who='confirmed by a person' if cta['chosen_by']=='person' else 'proposed by the writer; confirm it at Gate 2'
    lines+=['## CTA','',(cta['action'] or 'No explicit ask')+f' ({who})','',b['cta_why'],'','## Before publishing','']
    lines+=[f"- P{i}{' (required)' if x['required'] else ''}: {x['text']} — {x['answer'] or 'Unanswered'}" for i,x in enumerate(b['before_publishing'],1)]
    lines+=['','## Evidence','']
    for x in b['evidence']:
        at='' if x['start_ms'] is None else f" at {x['start_ms']//60000}:{(x['start_ms']//1000)%60:02d}"
        lines+=[f"- {x['speaker'] or 'Unknown speaker'}{at}: \"{x['quote']}\""]
    status={'bound':'bound to the call','supported':'checked by the verifier','unsupported':'not supported',
            'unchecked':'not checked','kept_by_person':'kept by a person','attested':'attested by a person'}
    def settled(c):
        a=c.get('attested')
        return f"attested by {a['by']} on {a['on']}" if a else status.get(c['status'],c['status'])
    lines+=['','## Claims','']+[f"- {c['text']} ({c['claim_class'].replace('_',' ')}"+(f"; {settled(c)}" if c.get('status') else '')+')'
                                for c in b['claims']]
    lines+=['','## Prior coverage','']+prior_coverage_lines(row)
    lines+=['','## Checks','']+['- '+f['severity']+': '+f['message'] for f in row['content_body']['review']['findings']]
    return '\n'.join(lines)+'\n'

def prior_coverage_lines(row):
    """Section 2.4 condition 9 in words: the overlapping earlier pieces, or none, and how complete the comparison was."""
    def plural(n,word): return f"{n} {word}{'' if n==1 else 's'}"
    lines=[]
    for p in row.get('prior_content_context') or []:
        approved=sum(x.get('approval_status')=='approved' for x in p.get('briefs') or [])
        published=len(p.get('publications') or [])
        lines.append(f"- {p['argument']} ({p.get('approval_status','unknown')} idea; {plural(approved,'approved brief')}; "
                     +(f"{plural(published,'publication')})" if published else 'not published)'))
    if not lines: lines.append('- No earlier idea or brief on this point was found in the comparison set.')
    coverage=(row.get('research_gaps') or {}).get('coverage') or {}
    if str(coverage.get('published_archive','')).startswith('incomplete'):
        lines.append('- The comparison covers earlier ideas and briefs; published content is not yet part of the comparison, so an earlier published piece may be missing.')
    if gaps:=coverage.get('prior_coverage_gaps'):
        lines.append(f"- {plural(len(gaps),'earlier idea')} could not be compared (never encoded for comparison).")
    return lines

def markdown(row):
    if is_v4(row):
        from .render_v4 import markdown_v4
        return markdown_v4(row)
    if is_v2(row): return markdown_v2(row)
    d=row['content_body']['document']; lines=['# '+d['title'],'',d['angle_statement'],'','Audience: '+d['audience'],'','## Core insight','',d['core_insight'],'','## Message spine','']
    lines+=['- '+v for v in d['message_spine']]
    for label,key in [('Reader promise','reader_promise'),('Positioning','positioning'),('Audience pain','audience_pain'),('Why now','why_now'),('Reader decision','reader_decision'),('Differentiation','differentiation'),('Similarity review','similarity_review')]: lines+=['','## '+label,'',d[key] or 'Not supplied']
    for label,key in [('Narrative','narrative'),('Evidence boundaries','evidence_boundaries'),('Voice','voice'),('Creative direction','creative_direction'),('Accessibility','accessibility'),('Distribution','distribution'),('Evaluation','evaluation_signals'),('Handoff','handoff_checklist')]:
        lines+=['','## '+label,'']+['- '+v for v in d[key]]
    lines+=['','## Claims','']+['- '+c['text']+' ['+', '.join(c['evidence_ids'])+'] · '+c['kind']+' · '+c['source_status']+' · '+'; '.join(c['qualifications']) for c in d['claims']]
    lines+=['','## Email','',d['email']['reader_job'],d['email']['direction']]+['- '+v for v in d['email']['outline']]
    lines+=['','## Carousel','',d['carousel_reader_job']]+[str(s['number'])+'. '+s['direction'] for s in d['carousel']]
    for i,r in enumerate(d['reels'],1): lines+=['',f'## Reel {i}','',r['reader_job'],r['direction']]+['- '+v for v in r['outline']]
    cta=d['cta'].get('text') or ('Decide in development (not yet confirmed by a person)' if d['cta'].get('choice')=='decide_in_development' else 'Not set')
    lines+=['','## CTA','',cta,'','## Source passages','']
    for e in row['selected_evidence']: lines+=['### '+e['evidence_id']+' · '+e['title'],'',e['excerpt'],'','Qualifications: '+'; '.join(e['qualifications']),'']
    lines+=['','## Prior coverage','']+[p['angle_id']+': '+p['argument']+' — '+d['prior_differences'].get(p['angle_id'],'') for p in row['prior_content_context']]
    lines+=['','## Open questions','']+[q['text']+' — '+(q['answer'] or 'Unanswered') for q in d['open_questions']]
    lines+=['','## Consent requirements','']+['- '+v for v in d['claims_requiring_consent']]
    lines+=['','## Validation and coverage','']+['- '+f['severity']+': '+f['message'] for f in row['content_body']['review']['findings']]
    lines+=['- '+v for v in row['research_gaps']['items']]
    return '\n'.join(lines)+'\n'
