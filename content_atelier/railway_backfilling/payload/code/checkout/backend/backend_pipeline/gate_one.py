from __future__ import annotations

from datetime import datetime, UTC
from psycopg.types.json import Jsonb
from .contracts import signature_from_fields, AngleDraft
from .strategy_contracts import StrategicAngleDraft, StrategicQuality
from .models import Quality
from .repository import identifier, insert
from .store import canonical_hash
from .angle_workflow import WORKFLOW


def comparison_owned(conn, angle_id):
    # Follow immutable provenance rather than a mutable score/status field. An
    # edit or rescore cannot convert comparison-only content into legacy content.
    return bool(conn.execute("""WITH RECURSIVE lineage AS (
        SELECT angle_id,run_id,supersedes_id FROM content_angles WHERE angle_id=%s
        UNION SELECT a.angle_id,a.run_id,a.supersedes_id FROM content_angles a
        JOIN lineage l ON a.angle_id=l.supersedes_id)
        SELECT 1 FROM lineage l JOIN pipeline_runs r ON r.run_id=l.run_id
        WHERE r.input_refs->>'workflow'=%s LIMIT 1""",(angle_id,WORKFLOW)).fetchone())


def locked(conn, angle_id, expected_hash, allowed_children=()):
    a = conn.execute('SELECT * FROM content_angles WHERE angle_id=%s FOR UPDATE',(angle_id,)).fetchone()
    if not a or a['content_hash']!=expected_hash:
        raise ValueError('Angle changed; refresh before saving')
    if any(r['angle_id'] not in allowed_children for r in conn.execute('SELECT angle_id FROM content_angles WHERE supersedes_id=%s',(angle_id,))):
        raise ValueError('A replacement already exists; refresh before saving')
    return a


def edit(repo, angle_id, expected_hash, changes, actor):
    allowed = {'title','argument','audience','tension','take','mechanism','reader_decision','source_assertions','inference','qualifiers','risks'}
    strategic_fields = set(StrategicAngleDraft.model_fields) - {'local_key', 'moment_ids', 'quality'}
    allowed |= strategic_fields
    if not changes or set(changes)-allowed:
        raise ValueError('Invalid editable fields')
    with repo.connection() as conn:
        a = locked(conn,angle_id,expected_hash)
        body = {**a['content_body'],**changes}
        moments = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(angle_id,))]
        if a['content_body'].get('strategy'):
            if set(changes) - strategic_fields:
                raise ValueError('Edit the strategic perspective fields rather than legacy Argument/Take aliases')
            draft = StrategicAngleDraft.model_validate({**a['content_body']['strategy'], **changes,
                                                        'local_key':'editor', 'moment_ids':moments})
            data = draft.model_dump(mode='json')
            body = {**a['content_body'], 'strategy':data,
                'title':data['title'], 'argument':data['core_perspective'], 'take':data['core_perspective'],
                'audience':data['audience'], 'tension':data['tension'],
                'mechanism':data['wia_expertise_in_action'] or data['core_perspective'],
                **{k:data[k] for k in ('reader_decision','source_assertions','inference','qualifiers','risks')}}
        else:
            if set(changes) - set(AngleDraft.model_fields):
                raise ValueError('Legacy content requires legacy editable fields')
            scores = a['quality_scores'] or {'grounding':0.,'source_relevance':0.,'audience_fit':0.,'specificity':0.,'editorial_usefulness':0.,'reasons':['Pending editor review']}
            AngleDraft.model_validate({**body,'local_key':'editor','moment_ids':moments,
                                      'quality':{k:scores[k] for k in ('grounding','source_relevance','audience_fit','specificity','editorial_usefulness','reasons')}})
        if any(not any(s.startswith(f'[{m}] ') for m in moments) for s in body['source_assertions']):
            raise ValueError('Assertions must retain a referenced moment prefix')
        for row in conn.execute('SELECT moment_body FROM key_moments WHERE moment_id=ANY(%s)',(moments,)):
            if not set(row['moment_body']['qualifications']).issubset(body['qualifiers']):
                raise ValueError('Source qualifications must be retained')
        new_id = identifier('angle')
        same_input = signature_from_fields(body)==signature_from_fields(a['content_body'])
        insert(conn,'content_angles',{'angle_id':new_id,'week_id':a['week_id'],'run_id':a['run_id'],'supersedes_id':angle_id,
               'content_body':body,'content_hash':canonical_hash({'body':body,'moments':moments}),
               'first_generated_at':a['first_generated_at'],'updated_by':actor,
               'embedding':a['embedding'] if same_input else None,
               'embedding_input_hash':a['embedding_input_hash'] if same_input else None})
        for m in moments:
            insert(conn,'angle_moments',{'angle_id':new_id,'moment_id':m,'evidence_role':'supports_argument'})
        repo.event(conn,a['run_id'],'angle_edited','Gate 1 edit saved; quality and matching require reassessment',
                   details={'angle_id':new_id,'supersedes_id':angle_id,'actor':actor})
        return {'angle_id':new_id,'content_hash':canonical_hash({'body':body,'moments':moments})}


def rescore(repo, angle_id, expected_hash, scores, actor):
    if 'strategic_fit' in scores and 'source_relevance' not in scores:
        s = StrategicQuality.model_validate(scores)
        q = Quality(grounding=s.grounding,source_relevance=s.source_strength,audience_fit=s.audience_resonance,
                    specificity=s.distinctiveness,editorial_usefulness=s.strategic_fit,reasons=s.reasons,
                    strategic_fit=s.strategic_fit,distinctiveness=s.distinctiveness,
                    audience_resonance=s.audience_resonance,source_strength=s.source_strength)
    else:
        q = Quality.model_validate(scores)
    if not q.reasons:
        raise ValueError('Editor quality assessment requires a reason')
    with repo.connection() as conn:
        a = locked(conn,angle_id,expected_hash)
        if a['content_body'].get('strategy') and q.strategic_fit is None:
            raise ValueError('Strategic opportunities require a strategic quality assessment')
        if a['approval_status']=='approved':
            raise ValueError('Replace approved content before changing its assessment')
        conn.execute("""UPDATE content_angles SET quality_scores=%s,base_score=%s,adjusted_score=NULL,
            matching_result=NULL,selection_status='candidate',updated_by=%s,updated_at=now() WHERE angle_id=%s""",
            (Jsonb(q.model_dump(mode='json')),q.score(),actor,angle_id))
        repo.event(conn,a['run_id'],'angle_quality_reviewed','Editor quality assessment saved',details={'angle_id':angle_id,'actor':actor,'reasons':q.reasons})
        intent = canonical_hash([angle_id,expected_hash,q.model_dump(mode='json')])
        insert(conn,'pipeline_jobs',{'job_id':'editor_'+intent[:24],'run_id':a['run_id'],'week_id':a['week_id'],
               'angle_id':angle_id,'stage':'angle_editor_validation','status':'completed',
               'idempotency_key':'editor:'+intent,'result_refs':{'angle_ids':[angle_id],'actor':actor},
               'finished_at':datetime.now(UTC)},conflict=True)


def decide(repo,angle_id,expected_hash,decision,cta,overlap_ack,note,actor):
    if decision not in {'approved','rejected'}:
        raise ValueError('Unknown Gate 1 decision')
    with repo.connection() as conn:
        policy=None; scenario=None
        if decision=='approved' and repo.settings.brief_enabled:
            from .briefs.gate_two import authorize
            authorize(repo,actor,'approve')
        if decision=='approved' and comparison_owned(conn,angle_id):
            cutoff=repo.settings.angle_approval_cutoff
            if cutoff not in {.78,.85,.90}:
                raise ValueError('Comparison-only approval is disabled: authoritative threshold selection is pending')
            from .briefs.gate_two import authorize
            authorize(repo,actor,'approve')
            completed=conn.execute("SELECT run_id,result_refs FROM pipeline_jobs WHERE stage='angle_final_assessment' AND status='completed' AND result_refs->'candidate_ids' ? %s ORDER BY updated_at DESC LIMIT 1",(angle_id,)).fetchone()
            if not completed: raise ValueError('Comparison assessment is incomplete')
            report=completed['result_refs']
            scenario=next((s for s in report['scenarios'] if s['cutoff']==cutoff),None)
            if not scenario or angle_id not in scenario['selected_ids']: raise ValueError('Angle is not selected under the authoritative family scenario')
            from .matching import assess
            import copy
            snapshot=report['assessment_snapshot']; approval_view=copy.deepcopy(snapshot)
            # Prior family approvals bind an added CTA hash. Their body, quality,
            # grounding and vectors still have to match the original snapshot.
            for frozen in approval_view['candidates']:
                sibling=conn.execute('SELECT approval_status,matching_result,content_hash FROM content_angles WHERE angle_id=%s',(frozen['id'],)).fetchone()
                if sibling and sibling['approval_status']=='approved':
                    from .briefs.inputs import angle_packet
                    angle_packet(conn,frozen['id'])
                    if (sibling['matching_result'] or {}).get('approval_policy',{}).get('snapshot_hash')!=canonical_hash(snapshot):
                        raise ValueError('Approved cohort member has a different assessment policy')
                    frozen['hash']=sibling['content_hash']
            assessed=assess(conn,approval_view,snapshot['contract'])
            if assessed['status']!='complete': raise ValueError('Current comparison coverage is incomplete')
            family=next(f for f in report['families'] if angle_id in {f['original_id'],f.get('replacement_id')})
            policy={'cutoff':cutoff,'assessment_run_id':completed['run_id'],'snapshot_hash':canonical_hash(snapshot),
                'family_original_id':family['original_id'],'selected_id':angle_id,
                'refinement_children':[family['replacement_id']] if family.get('replacement_id') else []}
        a = locked(conn,angle_id,expected_hash,(policy or {}).get('refinement_children',[]))
        if decision=='approved' and (a['content_body'].get('strategy') or {}).get('evidence_readiness')=='research_required':
            raise ValueError('Source research is required before approving this opportunity for development')
        if a['approval_status']=='approved': raise ValueError('Angle has already been approved')
        if decision=='approved':
            result = a['matching_result'] or {}
            if result.get('status')!=('comparison_complete' if policy else 'complete') or result.get('candidate_hash')!=a['content_hash'] or not policy and a['selection_status']!='visible':
                raise ValueError('Approval requires current complete matching and a visible score')
            if result.get('base_score')!=float(a['base_score']):
                raise ValueError('Quality assessment changed; reassess matching')
            flags=scenario['current_batch_flags'].get(angle_id,[]) if scenario else result.get('current_batch_flags',[])
            if flags and (not overlap_ack or not note or not note.strip()):
                raise ValueError('Current-batch overlap requires an acknowledgement and distinct-treatment note')
            if not isinstance(cta,dict) or not isinstance(cta.get('text'),str) or not cta['text'].strip():
                raise ValueError('A selected CTA is required')
            # Bind CTA to approved content; it does not affect the semantic signature.
            moments = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(angle_id,))]
            digest = canonical_hash({'body':a['content_body'],'moments':moments,'cta':cta})
            result = {**result,'candidate_hash':digest,'overlap_acknowledged':overlap_ack,'distinct_treatment_note':note}
            if policy: result['approval_policy']=policy
            conn.execute("""UPDATE content_angles SET content_hash=%s,selected_cta=%s,approval_status='approved',
                approved_hash=%s,approved_by=%s,approved_at=now(),review_note=%s,matching_result=%s,updated_by=%s,updated_at=now()
                WHERE angle_id=%s""",(digest,Jsonb(cta),digest,actor,note,Jsonb(result),actor,angle_id))
        else:
            conn.execute("UPDATE content_angles SET approval_status='rejected',approved_hash=NULL,approved_by=NULL,approved_at=NULL,review_note=%s,updated_by=%s,updated_at=now() WHERE angle_id=%s",(note,actor,angle_id))
        repo.event(conn,a['run_id'],'gate_one_'+decision,'Gate 1 decision saved',details={'angle_id':angle_id,'actor':actor,'decision':decision})
        response={'angle_id':angle_id,'approval_status':decision}
        if decision=='approved' and repo.settings.brief_enabled:
            from .briefs.workflow import queue_in_transaction
            response['brief_run']=queue_in_transaction(repo,conn,angle_id,actor,'synthetic' if repo.settings.synthetic else 'replay')
        return response


def reassess(repo,week_id,actor):
    with repo.connection() as conn:
        week = conn.execute('SELECT * FROM weeks WHERE week_id=%s FOR UPDATE',(week_id,)).fetchone()
        if not week:
            raise ValueError('Week not found')
        if conn.execute("SELECT 1 FROM pipeline_runs WHERE week_id=%s AND run_scope IN ('weekly_angles','angle_reassessment','comparison_reassessment') AND status IN ('queued','running')",(week_id,)).fetchone():
            raise ValueError('A run is already active for this week')
        rows = conn.execute("""SELECT angle_id,content_hash FROM content_angles a WHERE week_id=%s AND NOT EXISTS
            (SELECT 1 FROM content_angles n WHERE n.supersedes_id=a.angle_id) ORDER BY angle_id""",(week_id,)).fetchall()
        if not rows:
            raise ValueError('No angles to reassess')
        comparison_rows = [a for a in rows if comparison_owned(conn,a['angle_id'])]
        if comparison_rows:
            if len(comparison_rows)!=len(rows):
                raise ValueError('Mixed legacy/comparison cohorts require a separate comparison run')
            return queue_comparison_reassessment(repo,conn,week_id,actor,rows)
        sources = repo.frozen_sources(conn,week_id)
        run_id = identifier('run')
        refs = {'transcripts':[{'id':t['transcript_id'],'hash':t['content_hash']} for t in sources],
                'angle_ids':[a['angle_id'] for a in rows],'angle_hashes':{a['angle_id']:a['content_hash'] for a in rows},
                'synthetic':repo.settings.synthetic,'mode':'synthetic' if repo.settings.synthetic else 'replay',
                'week_index':sources[0]['source_metadata']['week_index']}
        insert(conn,'pipeline_runs',{'run_id':run_id,'week_id':week_id,'run_scope':'angle_reassessment',
               'trigger_type':'manual','triggered_by':actor,'input_refs':refs})
        prev = None
        for stage in ('angle_embedding','angle_matching'):
            job_id = identifier('job')
            insert(conn,'pipeline_jobs',{'job_id':job_id,'run_id':run_id,'week_id':week_id,'stage':stage,
                   'idempotency_key':f'{run_id}:{stage}','progress_details':{'dependencies':[prev] if prev else []}})
            prev=job_id
        conn.execute("UPDATE weeks SET active_run_id=%s,status='queued' WHERE week_id=%s",(run_id,week_id))
        repo.event(conn,run_id,'reassessment_queued','Saved angles queued for encoding/matching; generation will not repeat')
        return {'run_id':run_id}


def queue_comparison_reassessment(repo,conn,week_id,actor,leaves):
    """A new assessment intent only; never issues generation or another Call 3."""
    families = []
    ids = set()
    for leaf in leaves:
        root = conn.execute("""WITH RECURSIVE lineage AS (
            SELECT angle_id,supersedes_id FROM content_angles WHERE angle_id=%s
            UNION SELECT a.angle_id,a.supersedes_id FROM content_angles a JOIN lineage l ON a.angle_id=l.supersedes_id)
            SELECT angle_id FROM lineage WHERE supersedes_id IS NULL""",(leaf['angle_id'],)).fetchone()['angle_id']
        ids.add(root); ids.add(leaf['angle_id'])
        families.append({'original_id':root,'replacement_id':leaf['angle_id'] if root!=leaf['angle_id'] else None,
                         'targeted':root!=leaf['angle_id'],'disposition':'manual_reassessment',
                         'explanation':'Saved family reassessed without another refinement pass'})
    candidates = conn.execute('SELECT angle_id,content_hash FROM content_angles WHERE angle_id=ANY(%s)',(list(ids),)).fetchall()
    moments = [r['moment_id'] for r in conn.execute('SELECT DISTINCT moment_id FROM angle_moments WHERE angle_id=ANY(%s)',(list(ids),))]
    sources = repo.frozen_sources(conn,week_id)
    run_id = identifier('run')
    refs = {'transcripts':[{'id':s['transcript_id'],'hash':s['content_hash'],
                           'view_hash':canonical_hash([s['original_text'],s['passage_map'],s['source_metadata']])} for s in sources],
            'angle_ids':sorted(ids),'angle_hashes':{a['angle_id']:a['content_hash'] for a in candidates},
            'moment_ids':moments,'families':families,'comparison_reassessment':True,'workflow':WORKFLOW,
            'synthetic':repo.settings.synthetic,'mode':'replay','week_index':sources[0]['source_metadata']['week_index']}
    insert(conn,'pipeline_runs',{'run_id':run_id,'week_id':week_id,'run_scope':'comparison_reassessment',
                                'trigger_type':'manual','triggered_by':actor,'input_refs':refs})
    previous = None
    for stage in ('history_context','angle_initial_embedding','angle_final_assessment'):
        jid = identifier('job')
        insert(conn,'pipeline_jobs',{'job_id':jid,'run_id':run_id,'week_id':week_id,'stage':stage,
               'idempotency_key':f'{run_id}:{stage}','progress_details':{'dependencies':[previous] if previous else []}})
        previous = jid
    conn.execute("UPDATE weeks SET active_run_id=%s,status='queued' WHERE week_id=%s",(run_id,week_id))
    repo.event(conn,run_id,'comparison_reassessment_queued','New comparison intent; Gate 1 remains disabled')
    return {'run_id':run_id,'workflow':WORKFLOW}
