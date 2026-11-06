from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from .angle_workflow import LEGACY, STAGES, WORKFLOW
from .database import connect
from .gates.roles import access_for, access_in
from .storage_sources import capture, chunks
from .store import canonical_hash
from .artifacts import store_for


def current_versions(lineage):
    """angle_id -> the latest edit in its family, from {angle_id: supersedes_id}."""
    children = {}
    for angle_id,parent in lineage.items():
        if parent:
            children.setdefault(parent,[]).append(angle_id)
    def leaf(angle_id, seen=()):
        if angle_id in seen:
            raise ValueError('Angle replacement cycle')
        nxt = sorted(children.get(angle_id,[]))
        return leaf(nxt[-1],(*seen,angle_id)) if nxt else angle_id
    return {angle_id:leaf(angle_id) for angle_id in lineage}


def card_selection_view(run_id, refs, angles, lineage):
    """The Gate 1 selection block for one strategist run (E.B16 g): why these cards, in rank order.

    refs is the angle_generation result; angles are review rows by ID; lineage maps angle_id to supersedes_id.
    Each ranked card points at its current version, so an edited card keeps its place in the ranking.
    """
    current = current_versions(lineage)
    ranking = []
    for rank,angle_id in enumerate(refs['ranked_angle_ids'],1):
        now = current.get(angle_id,angle_id)
        row = angles.get(now) or {}
        ranking.append({'rank':rank,'angle_id':angle_id,'current_angle_id':now,
                        'title':((row.get('content_body') or {}).get('card') or {}).get('title'),
                        'selection_status':row.get('selection_status'),'approval_status':row.get('approval_status'),
                        'selection':(row.get('matching_result') or {}).get('selection')})
    from .gates.decisions import selection_hash
    return {'run_id':run_id,'week_summary':refs['week_summary'],'ranking':ranking,
            'considered_not_selected':[{**idea,'index':i} for i,idea in enumerate(refs['considered_not_selected'])],
            'internal_insights':refs['internal_insights'],
            'unreferenced_moment_ids':refs.get('unreferenced_moment_ids',[]),'reference_repair':refs.get('reference_repair'),
            # Version 5 (E.B21): the proposed week, pillar coverage and seed pairings, when the run has them.
            **{k:refs[k] for k in ('publishing_order','pillar_notes','seed_pairings') if k in refs},
            # A stale or missing content plan when the run generated (L.B10).
            'plan_warning':refs.get('plan_warning'),
            # Binds considered-idea actions (revive, hold, internal, skip) to this block (E.B20).
            'selection_hash':selection_hash(run_id,refs)}


def context_warnings(conn):
    from .knowledge.staleness import warnings
    return [w['message'] for w in warnings(conn)]


def review_roster(conn=None):
    """Speaker labels for the card screen, from the assembly service's roster (L.B5)."""
    from .cycle.verification import knowledge_root
    from .knowledge.assembly import roster
    return roster(knowledge_root(), conn)


def identifier(prefix):
    return prefix + '_' + uuid4().hex


def account_memory(conn, moment_ids, shared=None):
    """Account memory beside a card (3.B17), or [] before migration 010 (the shared baseline test database)."""
    if not moment_ids or not conn.execute("""SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema()
            AND table_name='key_moments' AND column_name='evidence_class'""").fetchone():
        return []
    from .accounts import for_card
    return for_card(conn, moment_ids, shared)


def json_value(value):
    return Jsonb(value) if isinstance(value, (dict, list)) else value


# Tables whose rows are read in the order they were written, and the columns that group that order: a run is "the latest
# run" of its card, week or window (Gate 2's research panel, the cycle) and bounds the history a week is compared with
# (matching.history); a decision is an item's current disposition (gates.decisions.latest_dispositions) and a line of the
# audit trail and the mined feedback. Such a row is dated now(), or just after the group's latest row when the database
# clock has stepped back since it was written (database.CLOCK_STEP_SECONDS), so created_at order is write order.
DATED_IN_ORDER = {'pipeline_runs': (), 'decisions': ()}


def _dated_in_order(conn, table, record):
    group = DATED_IN_ORDER[table]
    where = sql.SQL(' AND ').join(sql.SQL('{}=%s').format(sql.Identifier(k)) for k in group) if group else sql.SQL('TRUE')
    row = conn.execute(sql.SQL("SELECT GREATEST(now(),max(created_at)+interval '1 microsecond') AS t FROM {} WHERE {}").format(
        sql.Identifier(table), where), [record.get(k) for k in group]).fetchone()
    if row is None:  # a stand-in connection (tests) answers nothing: the column's default dates the row
        return record
    return {**record, 'created_at': row['t'] if isinstance(row, dict) else row[0]}


def insert(conn, table, record, *, conflict=False):
    if table == 'pipeline_jobs' and 'executor' not in record:
        # Every job row names its executor and queue (plan 0.B5): one executor, the queue the stage runs on.
        from .jobs.policy import placement
        record = {**record, **placement(record.get('stage', ''))}
    if table in DATED_IN_ORDER and 'created_at' not in record:
        record = _dated_in_order(conn, table, record)
    keys = list(record)
    conn.execute(sql.SQL('INSERT INTO {} ({}) VALUES ({}) {}').format(
        sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, keys)),
        sql.SQL(',').join(sql.Placeholder() for _ in keys),
        sql.SQL('ON CONFLICT DO NOTHING' if conflict else '')),
        [record[k] if k=='embedding' else json_value(record[k]) for k in keys])


class ContentRepository:
    def __init__(self, settings):
        self._settings = settings

    @property
    def settings(self):
        """The storage settings, current: when they were loaded from the environment and the settings table (0.B8) and a
        row has changed since, the repository sees the change within the cache window, with no restart."""
        refresh = getattr(self._settings, 'refreshed', None)
        if refresh is not None:
            self._settings = refresh()
        return self._settings

    @settings.setter
    def settings(self, value):
        self._settings = value

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
        archive = store_for(self.settings)
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
        # A document a person or the classification excluded (internal, fragment, a duplicate) is not extracted (plan 1.B4).
        rows = conn.execute("""SELECT * FROM transcripts WHERE week_id=%s AND included
            ORDER BY (source_metadata->>'file_order')::int,transcript_id""", (week_id,)).fetchall()
        # Later captures replace processing inputs, never overwrite cited originals.
        newest = {}
        for row in rows:
            key = row['upstream_id'] or row['transcript_id']
            if key not in newest or row['ingested_at'] > newest[key]['ingested_at']:
                newest[key] = row
        return sorted(newest.values(), key=lambda r:(r['source_metadata']['file_order'],r['transcript_id']))

    def week_sources(self, conn, week_id):
        """The calls a week's cards come from: those admitted in the week, or, for a cycle over a date window (3.B2), the
        documents its latest cycle read, which belong to no week. A card check after an edit or a refresh reads these."""
        rows = self.frozen_sources(conn, week_id)
        if rows:
            return rows
        run = conn.execute("""SELECT input_refs FROM pipeline_runs WHERE week_id=%s AND run_scope='weekly_angles'
            ORDER BY created_at DESC LIMIT 1""", (week_id,)).fetchone()
        ids = [t['id'] for t in ((run or {}).get('input_refs') or {}).get('transcripts', [])]
        return conn.execute('SELECT * FROM transcripts WHERE transcript_id=ANY(%s) ORDER BY transcript_id', (ids,)).fetchall() if ids else []

    def submit(self, week_id, mode='replay', *, actor='local-cli', scope='weekly_angles', workflow=LEGACY, models=None,
               documents=None, selected_by='week', extra_refs=None):
        """Queue a weekly run. With model settings, the angle profile is validated and frozen here, before any
        extraction is paid for (E.B16 d); the worker refuses to run it under a different profile.

        `documents` are the rows the run reads when they were chosen by a date window or an explicit set (plan 1.B13,
        `documents.select`) rather than by the week they were admitted in; `week_id` then only names the cycle."""
        if workflow not in {LEGACY,WORKFLOW}:
            raise ValueError('Unknown workflow contract')
        if mode not in {'replay','live','synthetic'}:
            raise ValueError('mode must be replay, live or synthetic')
        profile = knowledge_base_version = kb = None
        if models is not None:
            from .angle_profiles import check_live_profile, uses_cards
            profile = models.angle_prompt_profile
            check_live_profile(profile, mode)
            if mode == 'live':
                # A paid run names its models: never the code default (section 4.10).
                from .settings_store import require_explicit_models
                require_explicit_models(models)
            if uses_cards(profile):
                # Cards run on both workflows; they need a real knowledge base outside synthetic tests.
                from .knowledge import held_out
                from .knowledge.assembly import assemble
                kb = assemble('strategist', root=models.knowledge_base_root, connection=self.connection,
                              allow_placeholders=mode=='synthetic')
                if mode == 'live':
                    held_out.check_live(kb.text)
                knowledge_base_version = kb.refs().get('version')
            else:
                knowledge_base_version = None
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
            records = documents if documents is not None else self.frozen_sources(conn, week_id)
            if not records:
                raise ValueError('No admitted transcripts')
            run_id = identifier('run')
            refs = {'transcripts':[{'id':r['transcript_id'],'hash':r['content_hash']} for r in records],
                    'week_index':records[0]['source_metadata'].get('week_index',0), 'mode':mode,
                    'synthetic':self.settings.synthetic, 'coverage':'complete_request', 'workflow':workflow}
            if documents is not None:
                refs['selected_by'] = selected_by
            # A cycle started from the app records its window, why each document was selected and its estimate (3.B2).
            refs.update(extra_refs or {})
            if profile is not None:
                refs['angle_prompt_profile'] = profile
                from .config import frozen_models
                refs['models'] = frozen_models(models)
                if models.extraction_profile != '2026-10-13.weekly.v3':
                    refs['extraction_profile'] = models.extraction_profile
                # The settings this run was submitted under and where each came from (0.B8, section 4.10); the knowledge-base
                # version it will use is frozen with the run's angle contract.
                from .settings_store import snapshot_refs
                refs.update(snapshot_refs('weekly', models=models, storage=self.settings, conn=conn))
                refs['settings_snapshot']['knowledge_base_version'] = knowledge_base_version
                if kb is not None:
                    # The window's strategy brief (E.B28), assembled with no model call from the knowledge base the run will
                    # use, and frozen with the cycle with its hash: Gate 1 shows it, strategist v7 reads it, and every card
                    # is checked against its offer calendar.
                    from datetime import date
                    from .cycle import strategy_brief
                    refs['strategy_brief'] = strategy_brief.assemble(kb, root=models.knowledge_base_root, on=date.today(), conn=conn)
                    refs['strategy_brief_hash'] = refs['strategy_brief']['brief_hash']
                from .angle_profiles import IDENTITY_PROFILES, KNOWLEDGE_BASE_EXEMPLAR_PROFILES
                if profile in KNOWLEDGE_BASE_EXEMPLAR_PROFILES:
                    # Founder seeds are frozen with the run, so a retry sends the same prompt (E.B19). Founder notes, which
                    # name their call, go only to a profile that reads them (L.B13).
                    from .cycle.seeds import freeze
                    refs['seeds'] = freeze(conn, week_id, founder_notes=profile in IDENTITY_PROFILES)
                if profile in IDENTITY_PROFILES:
                    # The identity records of the people and accounts the selected calls involve (Phase N8), frozen like the
                    # seeds: the strategist reads them and the card checks enforce their naming flags.
                    from .identities import notes
                    refs['identities'] = notes(conn, document_ids=[r['transcript_id'] for r in records])
            if workflow==WORKFLOW:
                for frozen,r in zip(refs['transcripts'],records):
                    frozen['view_hash'] = canonical_hash([r['original_text'],r['passage_map'],r['source_metadata']])
            insert(conn,'pipeline_runs',{'run_id':run_id,'week_id':week_id,'run_scope':scope,
                   'trigger_type':'manual','triggered_by':actor,'input_refs':refs})
            previous = None
            # A cycle an approver runs live embeds its new cards live too, under the cycle's standing budget (6.B3), so its
            # cards reach Gate 1 checked with no command (M1 exit test, 23 October); a live encode stays an approver's action
            # (S.B3). Any other run's embedding reuses saved vectors and waits for `storage_cli encode`, as before.
            live_encoding = mode=='live' and self.settings.encoding_enabled and access_in(conn,self.settings,actor).can('decide')
            for stage in STAGES if workflow==WORKFLOW else ('moment_extraction','angle_generation','angle_embedding','angle_matching'):
                job = {'job_id':identifier('job'),'run_id':run_id,'week_id':week_id,'stage':stage,
                       'idempotency_key':f'{run_id}:{stage}', 'input_hash':canonical_hash(refs),
                       'progress_details':{'dependencies':[previous] if previous else [],
                                           **({'encoding_mode':'live'} if live_encoding and stage=='angle_embedding' else {})}}
                insert(conn,'pipeline_jobs',job)
                previous = job['job_id']
            conn.execute("UPDATE weeks SET active_run_id=%s,status='queued' WHERE week_id=%s", (run_id,week_id))
            conn.execute("UPDATE transcripts SET extraction_status='queued' WHERE transcript_id=ANY(%s) AND extraction_status IN ('pending','failed','completed')",
                         ([r['transcript_id'] for r in records],))
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

    def claim(self, *, run_id=None, job_id=None):
        """Take the next ready editorial job (or the named one) under a lease. One claim for the queue workers and the
        inline runner (plan 0.B5); intake jobs are claimed by their own handler (intake/runtime.py)."""
        from .jobs.recover import recover_expired
        recover_expired(self, run_id=run_id)
        with self.connection() as conn:
            j = conn.execute("""SELECT j.* FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
                WHERE j.executor IN ('rq','postgres') AND r.run_scope<>'source_intake'
                AND j.status='queued' AND r.status IN ('queued','running')
                AND (%s::text IS NULL OR r.run_id=%s) AND (%s::text IS NULL OR j.job_id=%s) AND NOT EXISTS (
                  SELECT 1 FROM jsonb_array_elements_text(COALESCE(j.progress_details->'dependencies','[]')) dep
                  JOIN pipeline_jobs d ON d.job_id=dep.value WHERE d.status<>'completed')
                ORDER BY j.priority DESC,j.created_at,j.job_id FOR UPDATE OF j SKIP LOCKED LIMIT 1""",(run_id,run_id,job_id,job_id)).fetchone()
            if not j:
                return None
            j = conn.execute("""UPDATE pipeline_jobs SET status='running',attempt_count=attempt_count+1,
                lease_token=%s,lease_expires_at=now()+%s*interval '1 second', heartbeat_at=now(),
                started_at=COALESCE(started_at,now()),updated_at=now(),current_message='Processing',completed_units=NULL,total_units=NULL
                WHERE job_id=%s RETURNING *""",(uuid4().hex,self.settings.lease_seconds,j['job_id'])).fetchone()
            conn.execute("UPDATE pipeline_runs SET status='running',started_at=COALESCE(started_at,now()),updated_at=now(),current_message=%s WHERE run_id=%s",(j['stage'],j['run_id']))
            self.event(conn,j['run_id'],'stage_started',j['stage'],job=j)
            if j['stage']=='moment_extraction':
                from .documents.select import mark_extraction
                mark_extraction(conn,j['run_id'],'running',j)
            return j

    def guard(self, conn, job):
        # The run's row first: a commit inserts rows that reference it (events, moments) and a document run is settled under
        # its lock, so two workers committing jobs of one run would each hold a share lock and wait to upgrade it (deadlock).
        conn.execute('SELECT 1 FROM pipeline_runs WHERE run_id=%s FOR UPDATE',(job['run_id'],))
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
        if job['stage']=='moment_extraction' and status=='completed':
            from .documents.select import mark_extraction
            mark_extraction(conn,job['run_id'],'completed',job)
        scope=conn.execute('SELECT run_scope FROM pipeline_runs WHERE run_id=%s',(job['run_id'],)).fetchone()['run_scope']
        if scope=='source_intake':
            conn.execute("UPDATE pipeline_runs SET status='completed',current_message=%s,finished_at=now(),updated_at=now() WHERE run_id=%s", (message or 'Intake completed',job['run_id']))
            return
        from .jobs.policy import PER_DOCUMENT_SCOPES
        if scope in PER_DOCUMENT_SCOPES:
            # One job per document: the run is as finished as its jobs, and one failed document stops no other (2.B2, 0.B5).
            from .moments.queue import settle_run
            settle_run(conn,job['run_id'],done_word=PER_DOCUMENT_SCOPES[scope])
            return
        if scope == 'pack_generation':
            # v1's last stage is pack_assembly; content pack v2's is pack_finalize (Phase NP). Either leaves the pack for review.
            if job['stage'] in ('pack_assembly', 'pack_finalize') and status == 'completed':
                conn.execute("UPDATE pipeline_runs SET status='waiting_for_review',current_message='Pack ready for human review',finished_at=now(),updated_at=now() WHERE run_id=%s", (job['run_id'],))
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
            cards = result.get('selection_basis')=='card_rank'
            conn.execute("UPDATE pipeline_runs SET status='completed',current_message=%s,finished_at=now(),updated_at=now() WHERE run_id=%s",
                         ('Cards ranked and collapsed; ready for Gate 1' if cards else 'Comparison complete; threshold selection pending. Gate 1 approval disabled.',job['run_id']))
            conn.execute("UPDATE weeks SET status=%s WHERE week_id=%s",('review' if cards else 'comparison_review',job['week_id']))
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
            conn.execute("UPDATE pipeline_jobs SET status='failed',error_summary=%s,current_message='Failed',finished_at=now(),updated_at=now(),lease_token=NULL,lease_expires_at=NULL WHERE job_id=%s",(error[:2000],job['job_id']))
            scope=conn.execute('SELECT run_scope FROM pipeline_runs WHERE run_id=%s',(job['run_id'],)).fetchone()['run_scope']
            from .jobs.policy import PER_DOCUMENT_SCOPES
            if scope in PER_DOCUMENT_SCOPES:
                # A failed document fails its job, not the run: the other documents' jobs must still be claimable (2.B2, 0.B5).
                from .moments.queue import settle_run
                settle_run(conn,job['run_id'],done_word=PER_DOCUMENT_SCOPES[scope])
            else:
                conn.execute("UPDATE pipeline_runs SET status='failed',error_summary=%s,updated_at=now() WHERE run_id=%s",(error[:2000],job['run_id']))
            self.event(conn,job['run_id'],'stage_failed',error[:2000],job=job,severity='error')
            if job['stage']=='moment_extraction':
                from .documents.select import mark_extraction
                mark_extraction(conn,job['run_id'],'failed',job)

    def retry(self, job_id, actor):
        with self.connection() as conn:
            j = conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s FOR UPDATE',(job_id,)).fetchone()
            if not j or j['status'] not in {'failed','waiting'}:
                raise ValueError('Only failed or waiting jobs can be retried')
            run=conn.execute('SELECT run_scope,input_refs FROM pipeline_runs WHERE run_id=%s',(j['run_id'],)).fetchone()
            scope=run['run_scope']
            if (run['input_refs'] or {}).get('superseded_by'):
                # A regenerated brief replaced this run (briefs/workflow.regenerate); it stays as the record only.
                raise ValueError('This run was superseded by '+run['input_refs']['superseded_by']['run_id']+'; it cannot be retried')
            if scope=='source_intake':
                raise PermissionError('Use the administrator intake retry endpoint')
            if scope == 'pack_generation':
                from .packs.service import authorize
                authorize(self, actor)
            if scope in {'brief_generation','brief_revision'}:
                from .briefs.gate_two import authorize
                authorize(self,actor)
            from .jobs.recover import RETRY_REQUESTED
            conn.execute("UPDATE pipeline_jobs SET status='queued',error_summary=NULL,current_message=%s,finished_at=NULL,updated_at=now() WHERE job_id=%s",(RETRY_REQUESTED,job_id))
            conn.execute("UPDATE pipeline_runs SET status='queued',error_summary=NULL,updated_at=now() WHERE run_id=%s",(j['run_id'],))
            self.event(conn,j['run_id'],'retry_requested','Retry requested',details={'job_id':job_id,'actor':actor})

    def evidence(self, conn, moment, records):
        from .moments.store import evidence_refs
        return evidence_refs(moment, records)

    def save_moments(self, conn, run_id, week_id, moments, records, *, extractor_version='2026-10-13.weekly.v3', unverified=(),
                     repairs=(), provenance=None, unverified_scope=None, roster=None):
        """Store moments through the one ledger writer (moments/store.py), so every path fills the same columns (2.B2)."""
        from .moments.store import save
        return save(conn,moments,records,run_id=run_id,week_id=week_id,extractor_version=extractor_version,unverified=unverified,
                    repairs=repairs,provenance=provenance,unverified_scope=unverified_scope,roster=roster)

    def save_angles(self, conn, week_id, angles, *, parents=None):
        for a in angles:
            body = a.model_dump(mode='json',include={'title','argument','audience','tension','take','mechanism','reader_decision','source_assertions','inference','qualifiers','risks'})
            if a.strategy:
                body.update(strategy=a.strategy.model_dump(mode='json'), source_family_id=a.source_family_id)
            if a.card:
                body.update(card=a.card.model_dump(mode='json'), source_family_id=a.source_family_id)
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
                   'content_body':body,'content_hash':digest,'quality_scores':a.quality.model_dump(mode='json') if a.quality else None,
                   'base_score':a.quality.score() if a.quality else None,'first_generated_at':a.generated_at},conflict=True)
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
            # Cards in rank order within their generation (E.B16 g); weeks without cards keep the database order.
            if any((a['content_body'] or {}).get('card') for a in angles):
                angles.sort(key=lambda a:(a['first_generated_at'],((a['content_body'] or {}).get('card') or {}).get('rank',0),a['angle_id']))
            access = access_for(self.settings, actor)
            for a in angles:
                a['moment_ids'] = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(a['angle_id'],))]
                # Gate 1 roles (S.B3): the screen offers only what the server will accept from this actor.
                a['can_edit']=access.can('edit') and not a['has_replacement']
                a['can_reject']=access.can('decide') and a['approval_status']=='pending' and not a['has_replacement']
                matching=a['matching_result'] or {}
                comparison=matching.get('workflow')==WORKFLOW or a['workflow']==WORKFLOW
                card=(a['content_body'] or {}).get('card')
                if card:
                    # Cards: matching complete and visible after the duplicate check; no score or scenario cutoff.
                    a['can_rescore']=False
                    a['verify_before_publishing']=card['verify_before_publishing']
                    a['can_approve']=(a['approval_status']!='approved' and not a['has_replacement'] and a['selection_status']=='visible'
                        and matching.get('status')==('comparison_complete' if comparison else 'complete')
                        and access.can('decide'))
                    continue
                selected=not comparison
                if comparison and self.settings.angle_approval_cutoff in {.78,.85,.90}:
                    selected=any(a['angle_id'] in s['selected_ids'] for c in comparisons for s in (c['result_refs'] or {}).get('scenarios',[]) if s['cutoff']==self.settings.angle_approval_cutoff)
                a['can_approve']=selected and a['approval_status']!='approved' and matching.get('status')==('comparison_complete' if comparison else 'complete') and (comparison or a['selection_status']=='visible') and access.can('decide')
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
            latest = conn.execute("""SELECT j.run_id,j.result_refs FROM pipeline_jobs j WHERE j.week_id=%s AND j.stage='angle_generation'
                AND j.status='completed' AND j.result_refs ? 'week_summary' ORDER BY j.finished_at DESC,j.job_id DESC LIMIT 1""",(week_id,)).fetchone()
            selection = None
            if latest:
                lineage = {r['angle_id']:r['supersedes_id'] for r in conn.execute('SELECT angle_id,supersedes_id FROM content_angles WHERE week_id=%s',(week_id,))}
                selection = card_selection_view(latest['run_id'],latest['result_refs'],{a['angle_id']:a for a in angles},lineage)
            # The latest Gate 1 disposition per card and considered idea (E.B20), once migration 005 is applied.
            from .gates.decisions import latest_dispositions
            dispositions = latest_dispositions(conn,week_id)
            from .gate_one import card_check
            from .briefs.context import card_items
            from .cycle.refresh import status_for as refresh_status
            for a in angles:
                a['context_items'] = card_items(conn,a['angle_id'])
                a['disposition'] = dispositions.get(('angle',a['angle_id']))
                a['hold'] = (a['content_body'] or {}).get('gate_one_hold')
                # Where a card version's comparison check stands (a reframe, revive or edit queues one; E.B16, E.B20).
                a['check'] = card_check(a,runs,jobs) if (a['content_body'] or {}).get('card') and not a['has_replacement'] else None
                # A refresh with feedback waiting, being written or failed, with its reason in plain words (3.B7).
                a['refresh'] = refresh_status(a,runs,jobs) if (a['content_body'] or {}).get('card') and not a['has_replacement'] else None
            for idea in (selection or {}).get('considered_not_selected',[]):
                idea['disposition'] = dispositions.get(('considered_idea',f"{selection['run_id']}:{idea['index']}"))
            from .gates import rubric
            # The window's strategy brief the week's latest cycle was given (E.B28), with its hash; None before E.B28.
            brief_run = next((r for r in runs if r['run_scope']=='weekly_angles' and (r['input_refs'] or {}).get('strategy_brief')), None)
            from .removal import marks as removal_marks
            removed = removal_marks(conn,'angle',[a['angle_id'] for a in angles])
            memory_records = {}
            for a in angles:
                # Strategist v7's public-use verdict and stance confirmation, for the card screen (E.B30, D31).
                ledger = (a['content_body'] or {}).get('ledger') or {}
                a['public_use'] = ledger.get('public_use')
                # Built on material removed at a client's request (6.B12): not for public use, and it cannot be developed.
                a['removed_material'] = removed.get(a['angle_id'])
                if a['removed_material']:
                    public = a['public_use'] or {}
                    a['public_use'] = {'allowed': False, 'reasons': [a['removed_material']['note'], *(public.get('reasons') or [])],
                                       'kinds': ['removed_material', *(public.get('kinds') or [])]}
                    a['can_approve'] = False
                a['stance_confirmation'] = (a['content_body'] or {}).get('stance_confirmation')
                # The account a client story card is about, with its current state and what happened next (3.B17, D25).
                a['account_memory'] = account_memory(conn,a.get('moment_ids'),memory_records) if (a['content_body'] or {}).get('card') else []
            return {'week':week,'angles':angles,'selection':selection,
                    'strategy_brief':(brief_run['input_refs'] or {})['strategy_brief'] if brief_run else None,'runs':runs,'jobs':jobs,'events':events,'transcripts':transcripts,
                    # The rubric the card form rates against (E.X7).
                    'rubric':rubric.form() if selection else None,
                    # Speaker names and roles for the card screen (E.F2); anyone else is a client or prospect.
                    'roster':review_roster(conn),
                    # Staleness warnings on the cycle (L.B8): overdue rosters, offer sheets and rules.
                    'context_warnings':context_warnings(conn),
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
