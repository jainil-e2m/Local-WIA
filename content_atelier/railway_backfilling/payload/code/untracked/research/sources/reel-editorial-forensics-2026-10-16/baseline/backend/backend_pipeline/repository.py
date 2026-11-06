from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from .angle_workflow import LEGACY, STAGES, WORKFLOW
from .database import connect
from .storage_sources import capture, chunks
from .store import JsonStore, canonical_hash


def identifier(prefix):
    return prefix + '_' + uuid4().hex


def json_value(value):
    return Jsonb(value) if isinstance(value, (dict, list)) else value


def insert(conn, table, record, *, conflict=False):
    keys = list(record)
    conn.execute(sql.SQL('INSERT INTO {} ({}) VALUES ({}) {}').format(
        sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, keys)),
        sql.SQL(',').join(sql.Placeholder() for _ in keys),
        sql.SQL('ON CONFLICT DO NOTHING' if conflict else '')),
        [record[k] if k=='embedding' else json_value(record[k]) for k in keys])


class ContentRepository:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def connection(self):
        with connect(self.settings.database_url) as conn:
            if self.settings.synthetic and not conn.info.dbname.endswith('_test'):
                raise RuntimeError('Synthetic operation requires a dedicated database ending in _test')
            yield conn

    def event(self, conn, run_id, kind, message, *, job=None, details=None, severity='info'):
        insert(conn, 'pipeline_events', {'event_id': identifier('event'), 'run_id': run_id,
                'job_id': job['job_id'] if job else None, 'event_type': kind, 'message': message,
                'severity': severity, 'attempt_number': job['attempt_count'] if job and job['attempt_count'] else None,
                'details': details or {}})

    def admit(self, directory, start: date, week_index: int, *, selected_paths=None):
        from pathlib import Path
        root = Path(directory).resolve()
        paths = (sorted(Path(p).resolve() for p in selected_paths) if selected_paths is not None else
                 sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in {'.txt','.vtt','.webvtt'}))
        if any(not p.is_relative_to(root) or not p.is_file() for p in paths) or len(set(paths)) != len(paths):
            raise ValueError('Admission paths must be unique files inside the selected week folder')
        if not paths:
            raise ValueError('No transcript inputs')
        records = [capture(p, week_index, i) for i,p in enumerate(paths,1)]
        from zoneinfo import ZoneInfo
        for record in records:
            if record['source_type'] == 'fathom':
                occurred = record['occurred_at'].astimezone(ZoneInfo('Asia/Kolkata')).date()
                if not start <= occurred <= start + timedelta(days=6):
                    raise ValueError('Fathom occurrence is outside the assigned IST week')
        import hashlib
        archive = JsonStore(self.settings.artifact_root)
        for path,record in zip(paths,records,strict=True):
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=record['content_hash']:
                raise ValueError('Source changed during admission')
            archive.write_bytes(f"source-originals/{record['content_hash']}.original",raw)
        week_id = 'week_' + start.isoformat()
        with self.connection() as conn:
            insert(conn, 'weeks', {'week_id':week_id,'week_start':start,'week_end':start+timedelta(days=6)}, conflict=True)
            for record in records:
                existing = conn.execute('SELECT week_id,content_hash,original_text,passage_map FROM transcripts WHERE transcript_id=%s', (record['transcript_id'],)).fetchone()
                if existing and existing['week_id'] != week_id:
                    raise ValueError('Captured source already belongs to another week')
                if existing and (existing['original_text']!=record['original_text'] or existing['passage_map']!=record['passage_map']):
                    raise ValueError('Reader view differs from an immutable admitted source; an explicit migration is required')
                insert(conn, 'transcripts', {**record, 'week_id':week_id, 'processing_status':'admitted'}, conflict=True)
                for chunk in chunks(record):
                    insert(conn, 'transcript_chunks', {**chunk, 'transcript_id':record['transcript_id']}, conflict=True)
            kinds = {r['source_type'] for r in records}
            metadata_status = ('meeting_dates_unknown' if kinds == {'zoom'} else
                               'verified_fathom_dates' if kinds == {'fathom'} else 'mixed_source_date_coverage')
            conn.execute("UPDATE weeks SET coverage_notes=COALESCE(coverage_notes,'{}'::jsonb)||%s WHERE week_id=%s",
                         (Jsonb({'metadata_status':metadata_status, 'assigned_calendar_range':True}),week_id))
            refs = {'transcripts':[{'id':r['transcript_id'],'hash':r['content_hash']} for r in records],
                    'week_index':week_index,'mode':'replay','synthetic':self.settings.synthetic}
            preparation = 'preparation_' + canonical_hash({'week_id':week_id,'input_refs':refs})[:24]
            exists = conn.execute('SELECT 1 FROM pipeline_runs WHERE run_id=%s',(preparation,)).fetchone()
            insert(conn,'pipeline_runs',{'run_id':preparation,'week_id':week_id,'run_scope':'source_preparation',
                   'status':'completed','trigger_type':'manual','input_refs':refs,'current_message':'Sources and transcript chunks prepared',
                   'started_at':datetime.now(UTC),'finished_at':datetime.now(UTC)},conflict=True)
            self.job(conn,preparation,'source_admission',{'transcript_ids':[r['transcript_id'] for r in records],
                       'source_count':len(records),'passage_count':sum(len(r['passage_map']) for r in records)})
            prepared_chunks = [r['chunk_id'] for r in conn.execute('SELECT chunk_id FROM transcript_chunks WHERE transcript_id=ANY(%s) ORDER BY chunk_id',([r['transcript_id'] for r in records],))]
            self.job(conn,preparation,'transcript_chunk_preparation',{'chunk_ids':prepared_chunks,'chunk_count':len(prepared_chunks),'encoding':'not_requested'})
            if not exists:
                self.event(conn,preparation,'sources_prepared','Originals, passage maps and chunks admitted without inference',
                           details={'source_count':len(records),'chunk_count':len(prepared_chunks)})
            conn.execute("UPDATE weeks SET active_run_id=COALESCE(active_run_id,%s),status=CASE WHEN status='pending' THEN 'prepared' ELSE status END WHERE week_id=%s",(preparation,week_id))
        return {'week_id':week_id,'transcripts':len(records),'passages':sum(len(r['passage_map']) for r in records)}

    def frozen_sources(self, conn, week_id):
        rows = conn.execute("""SELECT * FROM transcripts WHERE week_id=%s
            ORDER BY (source_metadata->>'file_order')::int,transcript_id""", (week_id,)).fetchall()
        # Later captures replace processing inputs, never overwrite cited originals.
        newest = {}
        for row in rows:
            key = row['upstream_id'] or row['transcript_id']
            if key not in newest or row['ingested_at'] > newest[key]['ingested_at']:
                newest[key] = row
        return sorted(newest.values(), key=lambda r:(r['source_metadata']['file_order'],r['transcript_id']))

    def submit(self, week_id, mode='replay', *, actor='local-cli', scope='weekly_angles', workflow=LEGACY):
        if workflow not in {LEGACY,WORKFLOW}:
            raise ValueError('Unknown workflow contract')
        if mode not in {'replay','live','synthetic'}:
            raise ValueError('mode must be replay, live or synthetic')
        if mode == 'live' and not self.settings.generation_enabled:
            raise ValueError('SQL generation permission is disabled')
        if mode == 'synthetic' and not self.settings.synthetic:
            raise ValueError('Synthetic providers require a separate synthetic database')
        with self.connection() as conn:
            week = conn.execute('SELECT * FROM weeks WHERE week_id=%s FOR UPDATE', (week_id,)).fetchone()
            if not week:
                raise ValueError('Week not found')
            if conn.execute("SELECT 1 FROM pipeline_runs WHERE week_id=%s AND run_scope IN ('weekly_angles','angle_reassessment','comparison_reassessment') AND status IN ('queued','running')", (week_id,)).fetchone():
                raise ValueError('This week already has an active run')
            records = self.frozen_sources(conn, week_id)
            if not records:
                raise ValueError('No admitted transcripts')
            run_id = identifier('run')
            refs = {'transcripts':[{'id':r['transcript_id'],'hash':r['content_hash']} for r in records],
                    'week_index':records[0]['source_metadata']['week_index'], 'mode':mode,
                    'synthetic':self.settings.synthetic, 'coverage':'complete_request', 'workflow':workflow}
            if workflow==WORKFLOW:
                for frozen,r in zip(refs['transcripts'],records):
                    frozen['view_hash'] = canonical_hash([r['original_text'],r['passage_map'],r['source_metadata']])
            insert(conn,'pipeline_runs',{'run_id':run_id,'week_id':week_id,'run_scope':scope,
                   'trigger_type':'manual','triggered_by':actor,'input_refs':refs})
            previous = None
            for stage in STAGES if workflow==WORKFLOW else ('moment_extraction','angle_generation','angle_embedding','angle_matching'):
                job = {'job_id':identifier('job'),'run_id':run_id,'week_id':week_id,'stage':stage,
                       'idempotency_key':f'{run_id}:{stage}', 'input_hash':canonical_hash(refs),
                       'progress_details':{'dependencies':[previous] if previous else []}}
                insert(conn,'pipeline_jobs',job)
                previous = job['job_id']
            conn.execute("UPDATE weeks SET active_run_id=%s,status='queued' WHERE week_id=%s", (run_id,week_id))
            self.event(conn,run_id,'submitted','Weekly angle pipeline queued; no provider was called')
            return {'run_id':run_id,'status':'queued'}

    def job(self, conn, run_id, stage, result, *, status='completed'):
        job_id = 'job_' + canonical_hash([run_id,stage])[:24]
        units = result.get('source_count',result.get('chunk_count'))
        insert(conn,'pipeline_jobs',{'job_id':job_id,'run_id':run_id,
               'week_id':conn.execute('SELECT week_id FROM pipeline_runs WHERE run_id=%s',(run_id,)).fetchone()['week_id'],
               'stage':stage,'status':status,'idempotency_key':f'{run_id}:{stage}', 'result_refs':result,
               'completed_units':units,'total_units':units,'current_message':f'{units} units prepared' if units is not None else None,
               'finished_at':datetime.now(UTC) if status=='completed' else None}, conflict=True)
        return job_id

    def claim(self, *, run_id=None):
        with self.connection() as conn:
            # Expiration means uncertain execution. An explicit retry is needed;
            # never automatically dispatch an expensive request after a lost response.
            expired = conn.execute("""UPDATE pipeline_jobs SET status='failed',lease_token=NULL,lease_expires_at=NULL,
                error_summary='Worker lease expired; review artifacts and explicitly retry',updated_at=now()
                WHERE COALESCE(to_jsonb(pipeline_jobs)->>'executor','postgres')='postgres'
                AND status='running' AND lease_expires_at<now()
                AND (%s::text IS NULL OR run_id=%s) RETURNING *""",(run_id,run_id)).fetchall()
            for j in expired:
                self.event(conn,j['run_id'],'lease_expired',j['error_summary'],job=j,severity='warning')
                conn.execute("UPDATE pipeline_runs SET status='failed',error_summary=%s,updated_at=now() WHERE run_id=%s", (j['error_summary'],j['run_id']))
            j = conn.execute("""SELECT j.* FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
                WHERE COALESCE(to_jsonb(j)->>'executor','postgres')='postgres'
                AND j.status='queued' AND r.status IN ('queued','running')
                AND (%s::text IS NULL OR r.run_id=%s) AND NOT EXISTS (
                  SELECT 1 FROM jsonb_array_elements_text(COALESCE(j.progress_details->'dependencies','[]')) dep
                  JOIN pipeline_jobs d ON d.job_id=dep.value WHERE d.status<>'completed')
                ORDER BY j.created_at,j.job_id FOR UPDATE OF j SKIP LOCKED LIMIT 1""",(run_id,run_id)).fetchone()
            if not j:
                return None
            j = conn.execute("""UPDATE pipeline_jobs SET status='running',attempt_count=attempt_count+1,
                lease_token=%s,lease_expires_at=now()+%s*interval '1 second', heartbeat_at=now(),
                started_at=COALESCE(started_at,now()),updated_at=now(),current_message='Processing',completed_units=NULL,total_units=NULL
                WHERE job_id=%s RETURNING *""",(uuid4().hex,self.settings.lease_seconds,j['job_id'])).fetchone()
            conn.execute("UPDATE pipeline_runs SET status='running',started_at=COALESCE(started_at,now()),updated_at=now(),current_message=%s WHERE run_id=%s",(j['stage'],j['run_id']))
            self.event(conn,j['run_id'],'stage_started',j['stage'],job=j)
            return j

    def guard(self, conn, job):
        row = conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s FOR UPDATE',(job['job_id'],)).fetchone()
        if row['lease_token'] != job['lease_token'] or row['status']!='running' or row['lease_expires_at'] < datetime.now(UTC):
            raise RuntimeError('Worker lost its lease; output was not committed')
        return row

    def heartbeat(self, job):
        with self.connection() as conn:
            return conn.execute("""UPDATE pipeline_jobs SET heartbeat_at=now(),lease_expires_at=now()+%s*interval '1 second',updated_at=now()
                WHERE job_id=%s AND status='running' AND lease_token=%s AND lease_expires_at>now()""",
                (self.settings.lease_seconds,job['job_id'],job['lease_token'])).rowcount == 1

    def finish(self, conn, job, result, *, status='completed', message=None):
        self.guard(conn,job)
        conn.execute("""UPDATE pipeline_jobs SET status=%s,result_refs=%s,current_message=%s,finished_at=now(),
            updated_at=now(),lease_token=NULL,lease_expires_at=NULL WHERE job_id=%s""",
            (status,Jsonb(result),message or status,job['job_id']))
        self.event(conn,job['run_id'],'stage_'+status,message or job['stage'],job=job,details=result)
        scope=conn.execute('SELECT run_scope FROM pipeline_runs WHERE run_id=%s',(job['run_id'],)).fetchone()['run_scope']
        if scope=='source_intake':
            conn.execute("UPDATE pipeline_runs SET status='completed',current_message=%s,finished_at=now(),updated_at=now() WHERE run_id=%s", (message or 'Intake completed',job['run_id']))
            return
        if scope in {'brief_generation','brief_revision'}:
            if job['stage']=='brief_validation' and status=='completed':
                conn.execute("UPDATE pipeline_runs SET status='waiting_for_review',current_message='Brief ready for Gate 2; production is separate',finished_at=now(),updated_at=now() WHERE run_id=%s",(job['run_id'],))
            elif status=='waiting':
                conn.execute("UPDATE pipeline_runs SET status='partially_completed',current_message=%s,updated_at=now() WHERE run_id=%s",(message,job['run_id']))
            return
        if status == 'waiting':
            conn.execute("UPDATE pipeline_runs SET status='partially_completed',current_message=%s,updated_at=now() WHERE run_id=%s",(message,job['run_id']))
            conn.execute("UPDATE weeks SET status='awaiting_embeddings' WHERE week_id=%s",(job['week_id'],))
        elif job['stage']=='angle_matching':
            conn.execute("UPDATE pipeline_runs SET status='waiting_for_review',current_message='Angles ready for Gate 1',finished_at=now(),updated_at=now() WHERE run_id=%s",(job['run_id'],))
            conn.execute("UPDATE weeks SET status='review' WHERE week_id=%s",(job['week_id'],))
        elif job['stage']=='angle_final_assessment' and status=='completed':
            conn.execute("UPDATE pipeline_runs SET status='completed',current_message='Comparison complete; threshold selection pending. Gate 1 approval disabled.',finished_at=now(),updated_at=now() WHERE run_id=%s",(job['run_id'],))
            conn.execute("UPDATE weeks SET status='comparison_review' WHERE week_id=%s",(job['week_id'],))
        elif status=='completed' and not conn.execute("SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND status<>'completed' LIMIT 1",(job['run_id'],)).fetchone():
            # An imported baseline has no generation dependencies left to run.
            # Finish this requested scope while retaining its partial-coverage fact.
            conn.execute("""UPDATE pipeline_runs SET status=CASE WHEN has_partial_failures THEN 'partially_completed' ELSE 'completed' END,
                current_message=%s,finished_at=now(),updated_at=now() WHERE run_id=%s""",(message or 'Requested work completed',job['run_id']))
            if job['stage']=='angle_embedding':
                conn.execute("UPDATE weeks SET status='awaiting_matching' WHERE week_id=%s",(job['week_id'],))

    def fail(self, job, error):
        with self.connection() as conn:
            self.guard(conn,job)
            conn.execute("UPDATE pipeline_jobs SET status='failed',error_summary=%s,finished_at=now(),updated_at=now(),lease_token=NULL,lease_expires_at=NULL WHERE job_id=%s",(error[:2000],job['job_id']))
            conn.execute("UPDATE pipeline_runs SET status='failed',error_summary=%s,updated_at=now() WHERE run_id=%s",(error[:2000],job['run_id']))
            self.event(conn,job['run_id'],'stage_failed',error[:2000],job=job,severity='error')

    def retry(self, job_id, actor):
        with self.connection() as conn:
            j = conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s FOR UPDATE',(job_id,)).fetchone()
            if not j or j['status'] not in {'failed','waiting'}:
                raise ValueError('Only failed or waiting jobs can be retried')
            scope=conn.execute('SELECT run_scope FROM pipeline_runs WHERE run_id=%s',(j['run_id'],)).fetchone()['run_scope']
            if scope=='source_intake':
                raise PermissionError('Use the administrator intake retry endpoint')
            if scope in {'brief_generation','brief_revision'}:
                from .briefs.gate_two import authorize
                authorize(self,actor)
            conn.execute("UPDATE pipeline_jobs SET status='queued',error_summary=NULL,finished_at=NULL,updated_at=now() WHERE job_id=%s",(job_id,))
            conn.execute("UPDATE pipeline_runs SET status='queued',error_summary=NULL,updated_at=now() WHERE run_id=%s",(j['run_id'],))
            self.event(conn,j['run_id'],'retry_requested','Retry requested',details={'job_id':job_id,'actor':actor})

    def evidence(self, conn, moment, records):
        locations = {p['passage_id']:(r,p) for r in records for p in r['passage_map']}
        refs = []
        for ref in moment.context_span_ids:
            record,p = locations[ref]
            refs.append({'transcript_id':record['transcript_id'],'passage_id':ref,'start':p['start'],'end':p['end'],
                         'roles':['anchor','context'] if ref in moment.anchor_span_ids else ['context']})
        if not any(moment.quote in r['original_text'][p['start']:p['end']] for r,p in (locations[x] for x in moment.anchor_span_ids)):
            raise ValueError('Quote does not resolve into admitted originals')
        return refs

    def save_moments(self, conn, run_id, week_id, moments, records):
        for m in moments:
            body = m.model_dump(mode='json',exclude={'moment_id','source_ids','anchor_span_ids','context_span_ids'})
            refs = self.evidence(conn,m,records)
            old = conn.execute('SELECT moment_body,evidence_refs FROM key_moments WHERE moment_id=%s',(m.moment_id,)).fetchone()
            if old and (old['moment_body'] != body or old['evidence_refs'] != refs):
                raise ValueError('Moment identity conflicts with preserved evidence')
            insert(conn,'key_moments',{'moment_id':m.moment_id,'week_id':week_id,'run_id':run_id,'moment_body':body,'evidence_refs':refs},conflict=True)

    def save_angles(self, conn, week_id, angles, *, parents=None):
        for a in angles:
            body = a.model_dump(mode='json',include={'title','argument','audience','tension','take','mechanism','reader_decision','source_assertions','inference','qualifiers','risks'})
            if a.strategy:
                body.update(strategy=a.strategy.model_dump(mode='json'), source_family_id=a.source_family_id)
            digest = canonical_hash({'body':body,'moments':a.moment_ids})
            old = conn.execute('SELECT content_body,first_generated_at,supersedes_id FROM content_angles WHERE angle_id=%s',(a.angle_id,)).fetchone()
            previous_moments = {r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s',(a.angle_id,))} if old else set()
            # The current content hash can legitimately include a later selected
            # CTA. Reuse validates generation content/evidence/age and preserves
            # current review fields; it never rewrites an approval from the cache.
            if old and (old['content_body']!=body or previous_moments!=set(a.moment_ids) or old['first_generated_at']!=a.generated_at):
                raise ValueError('Angle identity conflicts with original content or age')
            parent = (parents or {}).get(a.angle_id)
            if old and old['supersedes_id']!=parent:
                raise ValueError('Cached replacement family changed')
            insert(conn,'content_angles',{'angle_id':a.angle_id,'week_id':week_id,'run_id':a.run_id,
                   'supersedes_id':parent,
                   'content_body':body,'content_hash':digest,'quality_scores':a.quality.model_dump(mode='json'),
                   'base_score':a.quality.score(),'first_generated_at':a.generated_at},conflict=True)
            for moment_id in a.moment_ids:
                insert(conn,'angle_moments',{'angle_id':a.angle_id,'moment_id':moment_id,'evidence_role':'supports_argument'},conflict=True)

    def review(self, week_id, actor=None):
        with self.connection() as conn:
            week = conn.execute('SELECT * FROM weeks WHERE week_id=%s',(week_id,)).fetchone()
            if not week:
                raise ValueError('Week not found')
            comparisons = conn.execute("""SELECT r.run_id,r.status,j.result_refs FROM pipeline_runs r
                LEFT JOIN pipeline_jobs j ON j.run_id=r.run_id AND j.stage='angle_final_assessment'
                WHERE r.week_id=%s AND r.input_refs->>'workflow'=%s ORDER BY r.created_at DESC""",(week_id,WORKFLOW)).fetchall()
            explicit_ids = list({mid for c in comparisons for mid in (c['result_refs'] or {}).get('candidate_ids',[])})
            for j in conn.execute("""SELECT j.result_refs FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
                WHERE r.week_id=%s AND r.input_refs->>'workflow'=%s AND j.status='completed'
                AND j.stage IN ('angle_generation','angle_refinement')""",(week_id,WORKFLOW)):
                explicit_ids.extend((j['result_refs'] or {}).get('angle_ids',[]))
            angles = conn.execute("""SELECT angle_id,run_id,supersedes_id,content_body,content_hash,quality_scores,base_score,
                adjusted_score,selection_status,matching_result,first_generated_at,approval_status,selected_cta,review_note,
                (SELECT input_refs->>'workflow' FROM pipeline_runs r WHERE r.run_id=content_angles.run_id) AS workflow,
                EXISTS(SELECT 1 FROM content_angles n WHERE n.supersedes_id=content_angles.angle_id) AS has_replacement
                FROM content_angles WHERE week_id=%s AND (angle_id=ANY(%s) OR NOT EXISTS (SELECT 1 FROM content_angles n WHERE n.supersedes_id=content_angles.angle_id))
                ORDER BY first_generated_at,angle_id""",(week_id,explicit_ids)).fetchall()
            for a in angles:
                a['moment_ids'] = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(a['angle_id'],))]
                matching=a['matching_result'] or {}
                comparison=matching.get('workflow')==WORKFLOW or a['workflow']==WORKFLOW
                selected=not comparison
                if comparison and self.settings.angle_approval_cutoff in {.78,.85,.90}:
                    selected=any(a['angle_id'] in s['selected_ids'] for c in comparisons for s in (c['result_refs'] or {}).get('scenarios',[]) if s['cutoff']==self.settings.angle_approval_cutoff)
                a['can_approve']=selected and a['approval_status']!='approved' and matching.get('status')==('comparison_complete' if comparison else 'complete') and (comparison or a['selection_status']=='visible') and (not self.settings.brief_enabled and not comparison or actor in self.settings.brief_approvers)
            history_ids = {h['angle_id'] for a in angles for h in (a['matching_result'] or {}).get('history',[])}
            prior = {p['angle_id']:p for p in conn.execute("""SELECT a.angle_id,a.content_body->>'title' AS title,
                a.content_body->>'argument' AS argument,a.approval_status,w.week_start FROM content_angles a
                JOIN weeks w USING(week_id) WHERE a.angle_id=ANY(%s)""",(list(history_ids),))}
            for a in angles:
                if a['matching_result']:
                    for h in a['matching_result'].get('history',[]):
                        if h['angle_id'] in prior:
                            h.update(prior[h['angle_id']])
            runs = conn.execute('SELECT * FROM pipeline_runs WHERE week_id=%s ORDER BY created_at DESC',(week_id,)).fetchall()
            jobs = conn.execute("SELECT job_id,run_id,stage,status,current_message,completed_units,total_units,attempt_count,result_refs,error_summary,heartbeat_at FROM pipeline_jobs WHERE week_id=%s ORDER BY created_at,job_id",(week_id,)).fetchall()
            events = conn.execute("SELECT e.* FROM pipeline_events e JOIN pipeline_runs r USING(run_id) WHERE r.week_id=%s ORDER BY e.created_at,e.event_id",(week_id,)).fetchall()
            transcripts = conn.execute('SELECT transcript_id,title,source_url,occurred_at,processing_status FROM transcripts WHERE week_id=%s ORDER BY title',(week_id,)).fetchall()
            return {'week':week,'angles':angles,'runs':runs,'jobs':jobs,'events':events,'transcripts':transcripts,
                    'approval_cutoff':self.settings.angle_approval_cutoff,
                    'comparisons':[{'run_id':c['run_id'],'run_status':c['status'],
                                    'completion_state':(c['result_refs'] or {}).get('status','pending'),
                                    'report':c['result_refs'] if (c['result_refs'] or {}).get('status')=='comparison_complete' else None} for c in comparisons]}

    def comparison_report(self, run_id):
        with self.connection() as conn:
            run = conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(run_id,)).fetchone()
            if not run or run['input_refs'].get('workflow')!=WORKFLOW:
                raise ValueError('Comparison run not found')
            job = conn.execute("SELECT result_refs,status FROM pipeline_jobs WHERE run_id=%s AND stage='angle_final_assessment'",(run_id,)).fetchone()
            report = (job or {}).get('result_refs') or {}
            candidates = conn.execute('SELECT angle_id,content_body,content_hash,quality_scores,base_score,adjusted_score,supersedes_id,first_generated_at FROM content_angles WHERE angle_id=ANY(%s)',(report.get('candidate_ids',[]),)).fetchall()
            for candidate in candidates:
                candidate['moment_ids'] = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(candidate['angle_id'],))]
                candidate['assessed_metrics'] = report.get('assessments',{}).get(candidate['angle_id'])
                if candidate['assessed_metrics']:
                    candidate['quality_scores'] = candidate['assessed_metrics']['quality_scores']
                    candidate['base_score'] = candidate['assessed_metrics']['base_score']
                    candidate['adjusted_score'] = candidate['assessed_metrics']['adjusted_score']
            return {'run_id':run_id,'run_status':run['status'],'completion_state':report.get('status','pending'),
                    'threshold_selection_pending':True,'report':report,'candidates':candidates}

    def moment_context(self, moment_id):
        with self.connection() as conn:
            m = conn.execute('SELECT * FROM key_moments WHERE moment_id=%s',(moment_id,)).fetchone()
            if not m:
                raise ValueError('Moment not found')
            import hashlib
            ids = sorted({ref['transcript_id'] for ref in m['evidence_refs']})
            originals = {t['transcript_id']:t for t in conn.execute('SELECT transcript_id,title,original_text,passage_map,content_hash,source_url,source_metadata FROM transcripts WHERE transcript_id=ANY(%s)',(ids,))}
            locations = {}
            for t in originals.values():
                if hashlib.sha256(t['original_text'].encode()).hexdigest()!=t['source_metadata']['normalized_sha256']:
                    raise ValueError('Original evidence failed its admitted integrity hash')
                locations[t['transcript_id']] = {p['passage_id']:p for p in t['passage_map']}
            passages = []
            for ref in m['evidence_refs']:
                t = originals.get(ref['transcript_id'])
                p = locations.get(ref['transcript_id'],{}).get(ref['passage_id'])
                if not t or not p:
                    raise ValueError('Referenced original evidence is unavailable')
                if (ref['start'],ref['end']) != (p['start'],p['end']):
                    raise ValueError('Evidence offset integrity failure')
                passages.append({**ref,'text':t['original_text'][ref['start']:ref['end']], 'title':t['title'],
                                 'source_url':t['source_url'],'source_hash':t['content_hash'],
                                 'speaker':p['speaker'],'start_ms':p['start_ms'],'end_ms':p['end_ms']})
            if not any(m['moment_body']['quote'] in p['text'] for p in passages if 'anchor' in p['roles']):
                raise ValueError('Saved quote does not resolve into its original anchor')
            return {'moment':m,'passages':passages}

    def transcript_original(self, transcript_id):
        with self.connection() as conn:
            row = conn.execute("SELECT transcript_id,title,source_url,occurred_at,original_text,source_metadata->>'normalized_sha256' AS integrity_hash FROM transcripts WHERE transcript_id=%s",(transcript_id,)).fetchone()
            if not row:
                raise ValueError('Transcript not found')
            import hashlib
            if hashlib.sha256(row['original_text'].encode()).hexdigest()!=row.pop('integrity_hash'):
                raise ValueError('Original transcript failed its admitted integrity hash')
            return row
