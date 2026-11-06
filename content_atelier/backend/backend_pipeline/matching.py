from __future__ import annotations

import math
import hashlib
import struct
from numbers import Real
from datetime import datetime, UTC
from psycopg.types.json import Jsonb
from .contracts import signature_from_fields
from .store import canonical_hash
from .settings_store import default


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


# The numbers an assessment scores with (0.B8): matching.related, matching.close, matching.half_life_days,
# matching.max_recency_penalty and scoring.visible_threshold, frozen with the snapshot so a resumed, re-checked or
# approved assessment scores as it was frozen. A snapshot frozen before they were recorded used these fixed values.
FIXED = {'related':.78,'close':.90,'half_life_days':28.,'max_recency_penalty':.50,'visible_threshold':70.}
SCORING = {'related':('matching.related','similarity_threshold'),'close':('matching.close','close_similarity_threshold'),
           'half_life_days':('matching.half_life_days','recency_half_life_days'),
           'max_recency_penalty':('matching.max_recency_penalty','max_recency_penalty'),
           'visible_threshold':('scoring.visible_threshold','visible_threshold')}


def scoring(run, models=None):
    """The values to freeze: those the run's settings snapshot recorded (what the run says it used), else the worker's
    settings, else the fixed values."""
    recorded = (((run or {}).get('input_refs') or {}).get('settings_snapshot') or {}).get('values') or {}
    return {name:float(recorded[key]['value']) if key in recorded else float(getattr(models,field)) if models is not None
            else FIXED[name] for name,(key,field) in SCORING.items()}


def frozen_scoring(snapshot):
    return {**FIXED,**(snapshot.get('scoring') or {})}


def risk(cosine, generated, as_of, related=.78, half_life=28.):
    if generated.tzinfo is None or as_of.tzinfo is None or generated>as_of:
        raise ValueError('Generation age must be known, timezone aware and not in the future')
    if not math.isfinite(float(cosine)):
        raise ValueError('Cosine comparison is not finite; matching cannot complete')
    age = (as_of-generated).total_seconds()/86400
    cosine = max(-1.,min(1.,float(cosine)))
    overlap = max(0.,min(1.,(cosine-related)/(1-related))) if related<1 else float(cosine>=1)
    recency = 2**(-age/half_life)
    return {'cosine':cosine,'overlap':overlap,'age_days':age,'recency':recency,'risk':overlap*recency}


# Within one cohort, a pair this close is the same argument (the existing current-batch flag).
DUPLICATE_COSINE = default('matching.duplicate')


def duplicate_cosine(conn=None):
    """The card collapse cutoff (E.B16 l): the matching.duplicate setting (a row, else ATELIER_DUPLICATE_COSINE, else 0.86).

    E.B6 calibrated the value from labelled pairs (0.90 had let the Week 2 buying-research pair through, K6). The value must lie between
    0.5 and 1.0. Pass the caller's connection to read the settings table in its transaction.
    """
    from .settings_store import value
    return value('matching.duplicate', conn)


def is_card(body):
    return bool((body or {}).get('card'))


def encoded(angle, provenance):
    """True when an encoding job under this contract ever recorded a vector for the angle's current signature."""
    return (angle['angle_id'],canonical_hash(signature_from_fields(angle['content_body']))) in provenance


def split_history(conn, rows, contract):
    """History usable for vector matching, and the gaps: earlier angles never encoded under this contract (E.B16 e).

    A generation-only run, or one encoded with another model, is admitted to history without a compatible vector;
    it is skipped and recorded, not fatal. An angle that was encoded but has since lost or changed its vector is
    an integrity problem, so it stays in history and matching still pauses on it.
    """
    if contract is None:
        return rows,[]
    provenance = vector_provenance(conn,contract)
    usable = [a for a in rows if encoded(a,provenance)]
    gaps = [{'id':a['angle_id'],'reason':'no_compatible_vector'} for a in rows if not encoded(a,provenance)]
    return usable,gaps


def card_visibility(cards, pairs, superseded=(), cutoff=None):
    """Selection for strategist cards: rank plus the duplicate check, no score threshold (E.B16 a).

    cards: [{'angle_id','rank'}]; pairs: {angle_id: [{'angle_id','cosine'}]} within the cohort;
    superseded: angle IDs replaced by an edit. A card is collapsed into a better-ranked visible card when the
    pair is at least the duplicate cutoff similar; every other card is visible, in rank order.
    """
    cutoff = duplicate_cosine() if cutoff is None else cutoff
    result, visible = {}, []
    for card in sorted(cards,key=lambda c:(c['rank'],c['angle_id'])):
        aid = card['angle_id']
        if aid in superseded:
            result[aid] = {'selection_status':'suppressed','reason':'superseded_by_edit'}; continue
        close = {p['angle_id']:p['cosine'] for p in pairs.get(aid,[]) if p['cosine']>=cutoff}
        twin = next((v for v in visible if v in close),None)
        if twin:
            result[aid] = {'selection_status':'suppressed','reason':'duplicate','duplicate_of':twin,'cosine':close[twin]}
        else:
            visible.append(aid)
            result[aid] = {'selection_status':'visible','reason':'ranked','display_rank':len(visible)}
    return result


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
            def cohort(refs):
                return sorted((t['id'],t['hash']) for t in refs.get('transcripts',[]))
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


def freeze(repo, job, candidate_ids, contract=None, scoring_values=None):
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
        rows,gaps = split_history(conn,history(conn,run,candidates),contract)
        snapshot = {'as_of':datetime.now(UTC).isoformat(),
                    'candidates':[{'id':a['angle_id'],'hash':a['content_hash'],'input_hash':canonical_hash(signature_from_fields(a['content_body'])),
                                   'generated_at':a['first_generated_at'].isoformat(),
                                   'base_score':float(a['base_score']) if a['base_score'] is not None else None,
                                   'quality_hash':canonical_hash(a['quality_scores'])} for a in candidates],
                    'history':[{'id':a['angle_id'],'hash':a['content_hash'],'input_hash':canonical_hash(signature_from_fields(a['content_body'])),
                                'generated_at':a['first_generated_at'].isoformat(),'partial':a['partial']} for a in rows],
                    'scoring':scoring_values or dict(FIXED),
                    **({'history_gaps':gaps} if gaps else {})}
        conn.execute('UPDATE pipeline_jobs SET progress_details=%s WHERE job_id=%s',(Jsonb({**details,'snapshot':snapshot}),job['job_id']))
        repo.event(conn,job['run_id'],'history_frozen','Matching universe and clock frozen',job=job,
                   details={'history_count':len(rows),'history_gaps':len(gaps),'as_of':snapshot['as_of']})
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
    p = frozen_scoring(snapshot)
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
        card = is_card(a['content_body'])
        if a['base_score'] is None and not card:
            results.append({'angle_id':a['angle_id'],'status':'awaiting_quality'}); continue
        matches = []
        # Exact pgvector scan of the entire frozen universe. LIMIT/top-k never
        # determines a penalty; initial UI display is separately five rows.
        for r in conn.execute("SELECT angle_id,1-(embedding <=> %s) AS cosine FROM content_angles WHERE angle_id=ANY(%s)",
                              (a['embedding'],[h['id'] for h in snapshot['history']])):
            prior = rows[r['angle_id']]
            metrics = risk(r['cosine'],prior['first_generated_at'],as_of,p['related'],p['half_life_days'])
            matches.append({'angle_id':r['angle_id'],'content_hash':prior['content_hash'],**metrics})
        matches.sort(key=lambda m:(-m['risk'],-m['cosine'],m['angle_id']))
        pairs = []
        # Cards collapse at the configured cutoff; legacy angles keep the frozen matching.close current-batch flag.
        cutoff = duplicate_cosine(conn) if card else None
        threshold = min(cutoff, p['close']) if card else p['close']
        for r in conn.execute("SELECT angle_id,1-(embedding <=> %s) AS cosine FROM content_angles WHERE angle_id=ANY(%s) AND angle_id<>%s",
                              (a['embedding'],[c['id'] for c in snapshot['candidates']],a['angle_id'])):
            if r['cosine']>=threshold:
                pairs.append({'angle_id':r['angle_id'],'cosine':float(r['cosine'])})
        maximum = matches[0]['risk'] if matches else 0.
        # Cards are ranked, not self-scored: no base or adjusted score and no score threshold (E.B16 a).
        adjusted = None if card else float(a['base_score'])*(1-p['max_recency_penalty']*maximum)
        card_fields = {'selection_basis':'card_rank','rank':a['content_body']['card']['rank'],'duplicate_cosine':cutoff,
                       'historical_duplicates':[m for m in matches if m['cosine']>=cutoff]} if card else {}
        result = {'status':'complete','candidate_hash':a['content_hash'],'base_score':None if card else float(a['base_score']),'as_of':snapshot['as_of'],
                  **card_fields,**({'history_gaps':snapshot['history_gaps']} if snapshot.get('history_gaps') else {}),
                  'evidence_readiness':(a['content_body'].get('strategy') or {}).get('evidence_readiness','supported'),
                  'historical_risk':maximum,'history_count':len(matches),'history':matches,
                  'current_batch_flags':sorted(pairs,key=lambda p:p['angle_id']),
                  'partial_history_ids':[h['id'] for h in snapshot['history'] if h['partial']],
                  'contract':contract,'snapshot':snapshot,'quality_is_model_self_score':not card and a['angle_id'] not in editor_assessed}
        results.append({'angle_id':a['angle_id'],'adjusted_score':adjusted,
                        'max_historical_cosine':max((m['cosine'] for m in matches), default=-1.),
                        'grounding_valid':True,'coverage_complete':True, **result})
    return {'status':'complete' if all(r.get('status')!='awaiting_quality' for r in results) else 'incomplete','angles':results}


def pause_message(result, fallback):
    """Say which angle stopped matching and how to resume (E.B16 o), instead of a generic pause."""
    problems = [p for p in (result or {}).get('problems') or [] if isinstance(p, str)]
    future = [p.split(':', 1)[0] for p in problems if p.endswith(':future_generation')]
    vectors = [p for p in problems if ':' not in p]
    parts = []
    if vectors:
        parts.append('Matching paused: the recorded vector of ' + ', '.join(vectors) + ' is missing or no longer matches '
                     'its signature under the current embedding contract. Re-encode the run that produced it '
                     '(`storage_cli encode --run-id <run> --mode live`, or "Encode" on the run) under a run plan, '
                     'then reassess the week')
    if future:
        parts.append('history includes ' + ', '.join(future) + ', generated after this assessment date; create a new reassessment')
    return '; '.join(parts) if parts else fallback


def match(conn, snapshot, contract):
    """Legacy two-call selection, deliberately preserving its freshness score gate."""
    assessment = assess(conn,snapshot,contract)
    if assessment.get('problems'):
        for e in snapshot['candidates']:
            conn.execute("UPDATE content_angles SET adjusted_score=NULL,selection_status='candidate',matching_result=%s,approval_status=CASE WHEN approval_status='approved' THEN 'pending' ELSE approval_status END,approved_hash=NULL,approved_by=NULL,approved_at=NULL WHERE angle_id=%s",
                         (Jsonb({'status':'incomplete','missing_or_incompatible':assessment.get('problems',[]),'snapshot':snapshot}),e['id']))
        return assessment
    results = []
    visible = frozen_scoring(snapshot)['visible_threshold']
    cards = [m for m in assessment['angles'] if m.get('selection_basis')=='card_rank']
    visibility = card_visibility([{'angle_id':m['angle_id'],'rank':m['rank']} for m in cards],
                                 {m['angle_id']:m['current_batch_flags'] for m in cards})
    for metric in assessment['angles']:
        a = conn.execute('SELECT * FROM content_angles WHERE angle_id=%s',(metric['angle_id'],)).fetchone()
        if metric['angle_id'] in visibility:
            choice = visibility[metric['angle_id']]
            result = {k:v for k,v in metric.items() if k not in {'angle_id','adjusted_score','max_historical_cosine','grounding_valid','coverage_complete'}}
            result['selection'] = choice
            # A visible card has no visible twin; its collapsed twins need no overlap acknowledgement.
            result['current_batch_flags'] = [] if choice['selection_status']=='visible' else [
                f for f in metric['current_batch_flags'] if visibility.get(f['angle_id'],{}).get('selection_status')=='visible']
            old = (a['matching_result'] or {}).get('selection') or {}
            if choice['selection_status']!='visible' or old.get('selection_status')!='visible':
                conn.execute("UPDATE content_angles SET approval_status=CASE WHEN approval_status='approved' THEN 'pending' ELSE approval_status END,approved_hash=NULL,approved_by=NULL,approved_at=NULL WHERE angle_id=%s",(a['angle_id'],))
            conn.execute("UPDATE content_angles SET adjusted_score=NULL,selection_status=%s,matching_result=%s,updated_at=now() WHERE angle_id=%s",
                         (choice['selection_status'],Jsonb(result),a['angle_id']))
            results.append({'angle_id':a['angle_id'],'selection':choice})
            continue
        if metric.get('status')=='awaiting_quality':
            conn.execute("UPDATE content_angles SET adjusted_score=NULL,selection_status='candidate',matching_result=NULL,approval_status=CASE WHEN approval_status='approved' THEN 'pending' ELSE approval_status END,approved_hash=NULL,approved_by=NULL,approved_at=NULL WHERE angle_id=%s",(a['angle_id'],))
            results.append({'angle_id':a['angle_id'],'status':'awaiting_quality'})
            continue
        adjusted = metric['adjusted_score']
        result = {k:v for k,v in metric.items() if k not in {'angle_id','adjusted_score','max_historical_cosine','grounding_valid','coverage_complete'}}
        pairs = result['current_batch_flags']
        old_pairs = {p['angle_id'] for p in (a['matching_result'] or {}).get('current_batch_flags',[])}
        ready = result.get('evidence_readiness','supported')=='supported'
        if not ready or adjusted<=visible or old_pairs!={p['angle_id'] for p in pairs}:
            conn.execute("UPDATE content_angles SET approval_status=CASE WHEN approval_status='approved' THEN 'pending' ELSE approval_status END,approved_hash=NULL,approved_by=NULL,approved_at=NULL WHERE angle_id=%s",(a['angle_id'],))
        conn.execute("UPDATE content_angles SET adjusted_score=%s,selection_status=%s,matching_result=%s,updated_at=now() WHERE angle_id=%s",
                     (adjusted,'visible' if ready and adjusted>visible else 'suppressed',Jsonb(result),a['angle_id']))
        results.append({'angle_id':a['angle_id'],'adjusted_score':adjusted})
    return {'status':assessment['status'],'angles':results}
