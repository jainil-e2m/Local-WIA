"""Frozen SQL comparison intents and reports. No inference or encoding here."""
from __future__ import annotations

from datetime import datetime, UTC
from psycopg.types.json import Jsonb
from .angle_workflow import WORKFLOW, diagnoses, scenarios
from .contracts import signature_from_fields
from .matching import history, assess, vector_digest, vector_valid
from .store import canonical_hash


def entry(a):
    return {'id':a['angle_id'], 'hash':a['content_hash'],'body_hash':canonical_hash(a['content_body']),
            'input_hash':canonical_hash(signature_from_fields(a['content_body'])),
            'generated_at':a['first_generated_at'].isoformat(),
            'base_score':float(a['base_score']) if a['base_score'] is not None else None,
            'quality_hash':canonical_hash(a['quality_scores'])}


def history_context(repo, conn, job, run, moment_ids):
    candidates = conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s)',
                              (run['input_refs'].get('angle_ids',[]),)).fetchall()
    archive = history(conn,run,candidates)
    frozen = [{**entry(a), 'partial':a['partial']} for a in archive]
    fields = ('audience','tension','argument','take','mechanism','reader_decision','qualifiers')
    packet = [{'angle_id':a['angle_id'], 'content_hash':a['content_hash'],
               **{k:a['content_body'][k] for k in fields},
               **({'strategy':a['content_body']['strategy']} if a['content_body'].get('strategy') else {})} for a in archive]
    moments = conn.execute('SELECT * FROM key_moments WHERE moment_id=ANY(%s)',(moment_ids,)).fetchall()
    if len(moments)!=len(set(moment_ids)) or any(m['week_id']!=run['week_id'] for m in moments):
        raise ValueError('Current-week moment membership is incomplete')
    return {'workflow':WORKFLOW, 'history':frozen, 'historical_packet':packet,
            'history_hash':canonical_hash(frozen), 'moment_ids':moment_ids,
            'moment_hashes':{m['moment_id']:canonical_hash([m['moment_body'],m['evidence_refs']]) for m in moments}}


def validate_moments(conn, context, week_id):
    rows = conn.execute('SELECT * FROM key_moments WHERE moment_id=ANY(%s) FOR SHARE',(context['moment_ids'],)).fetchall()
    hashes = {m['moment_id']:canonical_hash([m['moment_body'],m['evidence_refs']]) for m in rows if m['week_id']==week_id}
    if hashes!=context['moment_hashes']:
        raise ValueError('Frozen current-week evidence changed; create a new assessment intent')


def check_history(conn, context):
    rows = {a['angle_id']:a for a in conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s) FOR UPDATE',
                                                ([h['id'] for h in context['history']],))}
    for frozen in context['history']:
        a = rows.get(frozen['id'])
        if not a or any(entry(a).get(k)!=v for k,v in frozen.items() if k!='partial'):
            raise ValueError('Frozen historical input changed; create a new assessment intent')


def freeze_assessment(repo, job, candidate_ids, context, *, prior=None, as_of=None, contract=None):
    with repo.connection() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        current = repo.guard(conn,job)
        details = current['progress_details'] or {}
        if details.get('snapshot'):
            return details['snapshot']
        check_history(conn,context)
        validate_moments(conn,context,job['week_id'])
        rows = conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s)',(candidate_ids,)).fetchall()
        if len(rows)!=len(set(candidate_ids)) or any(a['week_id']!=job['week_id'] for a in rows):
            raise ValueError('Frozen candidate membership incomplete')
        previous = {e['id']:e for e in prior['candidates']} if prior else {}
        def pinned(a, frozen):
            return {**frozen, **({'vector_digest':vector_digest(a['embedding'])} if vector_valid(a['embedding']) else {})}
        def candidate_entry(a):
            mids = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(a['angle_id'],))]
            if not mids or not set(mids).issubset(context['moment_ids']):
                raise ValueError('Candidate references evidence outside the validated current-week pool')
            return {**entry(a),'moment_ids':mids}
        history_rows = {a['angle_id']:a for a in conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s)',([h['id'] for h in context['history']],))}
        snapshot = {'as_of':prior['as_of'] if prior else as_of or datetime.now(UTC).isoformat(),
                    'contract':prior['contract'] if prior else contract,
                    'history':prior['history'] if prior else [pinned(history_rows[h['id']],h) for h in context['history']],
                    'candidates':[previous[a['angle_id']] if a['angle_id'] in previous else pinned(a,candidate_entry(a)) for a in rows]}
        conn.execute('UPDATE pipeline_jobs SET progress_details=%s WHERE job_id=%s',
                     (Jsonb({**details,'snapshot':snapshot}),job['job_id']))
        repo.event(conn,job['run_id'],'comparison_snapshot_frozen','Comparison inputs and evaluation clock frozen',
                   job=job,details={'as_of':snapshot['as_of'],'candidate_ids':candidate_ids,'history_hash':context['history_hash']})
        return snapshot


def evaluate(repo, conn, job, snapshot, contract, context, *, families=None):
    validate_moments(conn,context,job['week_id'])
    result = assess(conn,snapshot,contract)
    if result['status']!='complete':
        # An operational wait has no semantic rejection and no qualified counts.
        return {'status':'incomplete','workflow':WORKFLOW,'problems':result.get('problems',[]),
                'assessment_snapshot':snapshot, 'scenarios':None}
    rows = {a['angle_id']:a for a in conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s)',
                                                ([e['id'] for e in snapshot['candidates']+snapshot['history']],))}
    snapshot = {**snapshot, 'candidates':[{**e,'vector_digest':vector_digest(rows[e['id']]['embedding'])} for e in snapshot['candidates']],
                'history':[{**e,'vector_digest':vector_digest(rows[e['id']]['embedding'])} for e in snapshot['history']]}
    metrics = {}
    for metric in result['angles']:
        # Cohort flags are recomputed for each scenario after family selection.
        metric = {**metric,'snapshot':snapshot,'workflow':WORKFLOW,'current_batch_flags':[],
                  'quality_scores':rows[metric['angle_id']]['quality_scores']}
        metrics[metric['angle_id']] = metric
    if families is None:
        targets = [{'original_id':mid,'reasons':diagnoses(m,.78),
                    'historical_matches':[h for h in m['history'] if h['cosine']>=.78]}
                   for mid,m in metrics.items() if diagnoses(m,.78)]
        for mid,m in metrics.items():
            conn.execute("UPDATE content_angles SET matching_result=%s,adjusted_score=%s,selection_status='candidate' WHERE angle_id=%s",
                         (Jsonb({**m,'status':'comparison_initial'}),m['adjusted_score'],mid))
        return {'status':'initial_complete','workflow':WORKFLOW,'targets':targets,
                'assessment_snapshot':snapshot,'assessments':metrics}
    reports = scenarios(families,metrics)
    for scenario in reports:
        flags = {}
        for mid in scenario['selected_ids']:
            pairs = conn.execute('SELECT angle_id,1-(embedding <=> %s) AS cosine FROM content_angles WHERE angle_id=ANY(%s) AND angle_id<>%s',
                                 (rows[mid]['embedding'],scenario['selected_ids'],mid)).fetchall()
            flags[mid] = [{'angle_id':r['angle_id'],'cosine':float(r['cosine'])} for r in pairs if r['cosine']>=.90]
        scenario['current_batch_flags'] = flags
        scenario['counts']['current_batch_flagged'] = sum(bool(p) for p in flags.values())
        scenario['counts']['qualified_without_batch_flags'] = sum(not p for p in flags.values())
    for mid,m in metrics.items():
        conn.execute("""UPDATE content_angles SET matching_result=%s,adjusted_score=%s,selection_status='candidate',
            approval_status='pending',approved_hash=NULL,approved_by=NULL,approved_at=NULL WHERE angle_id=%s""",
                     (Jsonb({**m,'status':'comparison_complete'}),m['adjusted_score'],mid))
    return {'status':'comparison_complete','workflow':WORKFLOW,'threshold_selection_pending':True,
            'assessment_snapshot':snapshot,'families':families,'assessments':metrics,'scenarios':reports,
            'candidate_ids':list(metrics),
            # History admission is independent of experimental cutoff: admit the
            # latest valid source-grounded contribution per completed family.
            'angle_ids':[f.get('replacement_id') or f['original_id'] for f in families]}
