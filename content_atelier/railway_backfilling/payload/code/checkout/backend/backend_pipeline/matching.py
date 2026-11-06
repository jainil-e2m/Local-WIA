from __future__ import annotations

import math
import hashlib
import struct
from numbers import Real
from datetime import datetime, UTC
from psycopg.types.json import Jsonb
from .contracts import signature_from_fields
from .store import canonical_hash


def vector_valid(vector):
    if vector is None or len(vector)!=1536:
        return False
    if any(isinstance(x,bool) or not isinstance(x,Real) or not math.isfinite(float(x)) for x in vector):
        return False
    try:
        stored = struct.unpack('!1536f',struct.pack('!1536f',*(float(x) for x in vector)))
    except (OverflowError,struct.error):
        return False
    return all(math.isfinite(x) for x in stored) and math.fsum(x*x for x in stored)>0


def vector_digest(vector):
    # pgvector stores float32. Hash its actual representation, not provider doubles.
    return hashlib.sha256(struct.pack('!1536f',*(float(x) for x in vector))).hexdigest()


def risk(cosine, generated, as_of):
    if generated.tzinfo is None or as_of.tzinfo is None or generated>as_of:
        raise ValueError('Generation age must be known, timezone aware and not in the future')
    if not math.isfinite(float(cosine)):
        raise ValueError('Cosine comparison is not finite; matching cannot complete')
    age = (as_of-generated).total_seconds()/86400
    cosine = max(-1.,min(1.,float(cosine)))
    overlap = max(0.,min(1.,(cosine-.78)/.22))
    recency = 2**(-age/28.)
    return {'cosine':cosine,'overlap':overlap,'age_days':age,'recency':recency,'risk':overlap*recency}


def vector_provenance(conn, contract):
    result = {}
    for j in conn.execute("SELECT result_refs FROM pipeline_jobs WHERE stage IN ('angle_embedding','angle_initial_embedding','angle_refined_embedding') AND status='completed' ORDER BY finished_at,job_id"):
        data = j['result_refs'] or {}
        if data.get('contract')==contract:
            for v in data.get('vectors',[]):
                result[(v['angle_id'],v['input_hash'])] = v
    return result


def history(conn, run, candidates):
    # Provenance-based admission includes valid suppressed arguments and the explicit
    # bootstrap exception. An incomplete original extraction is never full success.
    admitted = {}
    for j in conn.execute("""SELECT j.result_refs,r.input_refs,w.week_start,r.created_at,r.status AS run_status
          FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id) JOIN weeks w ON w.week_id=r.week_id
          WHERE j.stage IN ('angle_generation','history_admission','angle_editor_validation','angle_final_assessment') AND j.status='completed'
          AND r.created_at<=%s AND w.week_start<=(SELECT week_start FROM weeks WHERE week_id=%s)""",(run['created_at'],run['week_id'])):
        data = j['result_refs'] or {}
        if run['input_refs'].get('workflow')=='historical_comparison_v1':
            cohort = lambda refs:sorted((t['id'],t['hash']) for t in refs.get('transcripts',[]))
            if cohort(run['input_refs']) and cohort(run['input_refs'])==cohort(j['input_refs']):
                # Same captured evidence is a replay/current cohort, even when a
                # changed history prompt would otherwise produce different IDs.
                continue
        if j['input_refs'].get('workflow') == 'historical_comparison_v1' and (data.get('status') != 'comparison_complete' or j['run_status']!='completed'):
            # A successful Call 2/editor job is insufficient to admit an unfinished
            # comparison workflow. Final results admit one source-valid family rep.
            continue
        synthetic = bool(j['input_refs'].get('synthetic'))
        if synthetic != bool(run['input_refs'].get('synthetic')):
            continue
        for angle_id in data.get('angle_ids',[]):
            admitted[angle_id] = {'partial':j['input_refs'].get('coverage')=='accepted_partial_baseline'}
    if not admitted:
        return []
    rows = conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s)',(list(admitted),)).fetchall()
    all_rows = conn.execute('SELECT angle_id,supersedes_id FROM content_angles').fetchall()
    parent = {r['angle_id']:r['supersedes_id'] for r in all_rows}
    def family(angle_id):
        seen = set()
        while parent.get(angle_id):
            if angle_id in seen:
                raise ValueError('Angle replacement cycle')
            seen.add(angle_id); angle_id=parent[angle_id]
        return angle_id
    current_families = {family(a['angle_id']) for a in candidates}
    representatives = {}
    for a in rows:
        f = family(a['angle_id'])
        if f in current_families or a['angle_id'] in {c['angle_id'] for c in candidates}:
            continue
        a['partial'] = admitted[a['angle_id']]['partial']
        if f not in representatives or (a['created_at'],a['angle_id']) > (representatives[f]['created_at'],representatives[f]['angle_id']):
            representatives[f]=a
    return sorted(representatives.values(),key=lambda a:a['angle_id'])


def freeze(repo, job, candidate_ids):
    with repo.connection() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        j = repo.guard(conn,job)
        details = j['progress_details'] or {}
        if 'snapshot' in details:
            return details['snapshot']
        run = conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(job['run_id'],)).fetchone()
        candidates = conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s)',(candidate_ids,)).fetchall()
        if len(candidates)!=len(set(candidate_ids)):
            raise ValueError('Candidate set is incomplete; refusing partial matching')
        rows = history(conn,run,candidates)
        snapshot = {'as_of':datetime.now(UTC).isoformat(),
                    'candidates':[{'id':a['angle_id'],'hash':a['content_hash'],'input_hash':canonical_hash(signature_from_fields(a['content_body'])),
                                   'generated_at':a['first_generated_at'].isoformat(),
                                   'base_score':float(a['base_score']) if a['base_score'] is not None else None,
                                   'quality_hash':canonical_hash(a['quality_scores'])} for a in candidates],
                    'history':[{'id':a['angle_id'],'hash':a['content_hash'],'input_hash':canonical_hash(signature_from_fields(a['content_body'])),
                                'generated_at':a['first_generated_at'].isoformat(),'partial':a['partial']} for a in rows]}
        conn.execute('UPDATE pipeline_jobs SET progress_details=%s WHERE job_id=%s',(Jsonb({**details,'snapshot':snapshot}),job['job_id']))
        repo.event(conn,job['run_id'],'history_frozen','Matching universe and clock frozen',job=job,
                   details={'history_count':len(rows),'as_of':snapshot['as_of']})
        return snapshot


def assess(conn, snapshot, contract):
    """Validate the frozen universe and calculate metrics without selecting or writing."""
    if snapshot.get('contract',contract)!=contract:
        raise ValueError('Frozen embedding contract changed; create a new assessment intent')
    provenance = vector_provenance(conn,contract)
    entries = snapshot['candidates'] + snapshot['history']
    ids = [e['id'] for e in entries]
    rows = {r['angle_id']:r for r in conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s) FOR UPDATE',(ids,))}
    editor_assessed = {r['angle_id'] for r in conn.execute("SELECT angle_id FROM pipeline_jobs WHERE stage='angle_editor_validation' AND status='completed' AND angle_id=ANY(%s)",(ids,))}
    problems = []
    as_of = datetime.fromisoformat(snapshot['as_of'])
    for e in entries:
        a = rows.get(e['id'])
        if not a or a['content_hash']!=e['hash']:
            raise ValueError('Frozen matching input changed; create a new reassessment')
        if e.get('body_hash') and canonical_hash(a['content_body'])!=e['body_hash']:
            raise ValueError('Frozen content body changed; create a new assessment intent')
        if 'moment_ids' in e:
            refs = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(a['angle_id'],))]
            if refs!=e['moment_ids'] or any(not any(s.startswith(f'[{m}] ') for m in refs) for s in a['content_body']['source_assertions']):
                raise ValueError('Frozen angle grounding references changed; create a new assessment intent')
        if e.get('generated_at') and a['first_generated_at'].isoformat()!=e['generated_at']:
            raise ValueError('Frozen generation age changed; create a new reassessment')
        if 'quality_hash' in e and (canonical_hash(a['quality_scores'])!=e['quality_hash'] or (float(a['base_score']) if a['base_score'] is not None else None)!=e['base_score']):
            raise ValueError('Frozen quality assessment changed; create a new reassessment')
        ih = canonical_hash(signature_from_fields(a['content_body']))
        proof = provenance.get((a['angle_id'],ih))
        if ih!=e['input_hash'] or a['embedding_input_hash']!=ih or not vector_valid(a['embedding']) or not proof or proof.get('vector_digest')!=vector_digest(a['embedding']):
            problems.append(a['angle_id'])
        if e.get('vector_digest') and (not vector_valid(a['embedding']) or vector_digest(a['embedding'])!=e['vector_digest']):
            raise ValueError('Frozen vector provenance changed; create a new reassessment')
        if a['first_generated_at']>as_of:
            problems.append(a['angle_id']+':future_generation')
    if problems:
        return {'status':'incomplete','problems':problems,'angles':[]}
    results = []
    for e in snapshot['candidates']:
        a = rows[e['id']]
        if a['base_score'] is None:
            results.append({'angle_id':a['angle_id'],'status':'awaiting_quality'}); continue
        matches = []
        # Exact pgvector scan of the entire frozen universe. LIMIT/top-k never
        # determines a penalty; initial UI display is separately five rows.
        for r in conn.execute("SELECT angle_id,1-(embedding <=> %s) AS cosine FROM content_angles WHERE angle_id=ANY(%s)",
                              (a['embedding'],[h['id'] for h in snapshot['history']])):
            prior = rows[r['angle_id']]
            metrics = risk(r['cosine'],prior['first_generated_at'],as_of)
            matches.append({'angle_id':r['angle_id'],'content_hash':prior['content_hash'],**metrics})
        matches.sort(key=lambda m:(-m['risk'],-m['cosine'],m['angle_id']))
        pairs = []
        for r in conn.execute("SELECT angle_id,1-(embedding <=> %s) AS cosine FROM content_angles WHERE angle_id=ANY(%s) AND angle_id<>%s",
                              (a['embedding'],[c['id'] for c in snapshot['candidates']],a['angle_id'])):
            if r['cosine']>=.90:
                pairs.append({'angle_id':r['angle_id'],'cosine':float(r['cosine'])})
        maximum = matches[0]['risk'] if matches else 0.
        adjusted = float(a['base_score'])*(1-.50*maximum)
        result = {'status':'complete','candidate_hash':a['content_hash'],'base_score':float(a['base_score']),'as_of':snapshot['as_of'],
                  'evidence_readiness':(a['content_body'].get('strategy') or {}).get('evidence_readiness','supported'),
                  'historical_risk':maximum,'history_count':len(matches),'history':matches,
                  'current_batch_flags':sorted(pairs,key=lambda p:p['angle_id']),
                  'partial_history_ids':[h['id'] for h in snapshot['history'] if h['partial']],
                  'contract':contract,'snapshot':snapshot,'quality_is_model_self_score':a['angle_id'] not in editor_assessed}
        results.append({'angle_id':a['angle_id'],'adjusted_score':adjusted,
                        'max_historical_cosine':max((m['cosine'] for m in matches), default=-1.),
                        'grounding_valid':True,'coverage_complete':True, **result})
    return {'status':'complete' if all(r.get('status')!='awaiting_quality' for r in results) else 'incomplete','angles':results}


def match(conn, snapshot, contract):
    """Legacy two-call selection, deliberately preserving its freshness score gate."""
    assessment = assess(conn,snapshot,contract)
    if assessment.get('problems'):
        for e in snapshot['candidates']:
            conn.execute("UPDATE content_angles SET adjusted_score=NULL,selection_status='candidate',matching_result=%s,approval_status=CASE WHEN approval_status='approved' THEN 'pending' ELSE approval_status END,approved_hash=NULL,approved_by=NULL,approved_at=NULL WHERE angle_id=%s",
                         (Jsonb({'status':'incomplete','missing_or_incompatible':assessment.get('problems',[]),'snapshot':snapshot}),e['id']))
        return assessment
    results = []
    for metric in assessment['angles']:
        a = conn.execute('SELECT * FROM content_angles WHERE angle_id=%s',(metric['angle_id'],)).fetchone()
        if metric.get('status')=='awaiting_quality':
            conn.execute("UPDATE content_angles SET adjusted_score=NULL,selection_status='candidate',matching_result=NULL,approval_status=CASE WHEN approval_status='approved' THEN 'pending' ELSE approval_status END,approved_hash=NULL,approved_by=NULL,approved_at=NULL WHERE angle_id=%s",(a['angle_id'],))
            results.append({'angle_id':a['angle_id'],'status':'awaiting_quality'})
            continue
        adjusted = metric['adjusted_score']
        result = {k:v for k,v in metric.items() if k not in {'angle_id','adjusted_score','max_historical_cosine','grounding_valid','coverage_complete'}}
        pairs = result['current_batch_flags']
        old_pairs = {p['angle_id'] for p in (a['matching_result'] or {}).get('current_batch_flags',[])}
        ready = result.get('evidence_readiness','supported')=='supported'
        if not ready or adjusted<=70. or old_pairs!={p['angle_id'] for p in pairs}:
            conn.execute("UPDATE content_angles SET approval_status=CASE WHEN approval_status='approved' THEN 'pending' ELSE approval_status END,approved_hash=NULL,approved_by=NULL,approved_at=NULL WHERE angle_id=%s",(a['angle_id'],))
        conn.execute("UPDATE content_angles SET adjusted_score=%s,selection_status=%s,matching_result=%s,updated_at=now() WHERE angle_id=%s",
                     (adjusted,'visible' if ready and adjusted>70. else 'suppressed',Jsonb(result),a['angle_id']))
        results.append({'angle_id':a['angle_id'],'adjusted_score':adjusted})
    return {'status':assessment['status'],'angles':results}
