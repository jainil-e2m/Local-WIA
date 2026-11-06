"""Durable legacy and historical-comparison workflows with explicit capabilities."""
from __future__ import annotations

import logging
import threading
from datetime import UTC, date, datetime

from psycopg.types.json import Jsonb

from .angle_profiles import uses_cards
from .angle_workflow import WORKFLOW
from .citation_adapter import VERSION as CITATION_VERSION
from .citation_adapter import adapt_angle_response
from .comparison import check_history, evaluate, freeze_assessment, history_context, validate_moments
from .config import Settings, frozen_models
from .gate_one import queue_deferred_checks
from .jobs import policy
from .settings_store import refresh
from .contracts import signature_from_fields
from .matching import assess, freeze, match, pause_message, scoring, vector_digest, vector_provenance, vector_valid
from .models import Moment, RunManifest
from .pipeline import Pipeline
from .prompts import angle_prompt, sql_angle_prompt, sql_refinement_prompt, weekly_moment_prompt
from .llm import live_provider
from .llm.call import provider_embed
from .llm.runs import LlmRuns
from .llm.stage import OVERSIZED_WEEK
from .refinement import parse_refinement
from .repository import ContentRepository, insert
from .storage_config import encoding_contract
from .storage_sources import reconstruct
from .store import JsonStore, canonical_hash
from .artifacts import backend_for, store_for
from .strategy_contracts import StrategicAngleResponse, StrategicCompactMomentResponse, StrategicRefinementResponse
from .moment_validation import resolve_moment_references_partial
from .moments.types import SCENE_V2_PROFILE, SCENE_V3_PROFILE, SCENE_V4_PROFILE
from .weekly import LIVE_COMPACT_VERSION, meeting_inventory
from .cycle.window import scene_coverage

log = logging.getLogger(__name__)


class CacheStore(JsonStore):
    def __init__(self, root, legacy_root):
        super().__init__(root)
        self.legacy = JsonStore(legacy_root)

    def find_artifact(self, fingerprint):
        return super().find_artifact(fingerprint) or self.legacy.find_artifact(fingerprint)

    def saved_attempts(self, fingerprint):
        return super().saved_attempts(fingerprint) + self.legacy.saved_attempts(fingerprint)


class SQLWorker:
    def __init__(self, storage_settings, model_settings=None, *, provider=None):
        self.storage = storage_settings
        self.models = model_settings or Settings.from_env()
        self.repo = ContentRepository(storage_settings)
        self.provider = provider
        if provider and not storage_settings.synthetic:
            raise ValueError('Injected providers require an isolated synthetic database')
        if self.models.embedding_dimensions!=1536:
            raise ValueError('Approved schema requires 1536-dimensional vectors')

    def once(self, *, run_id=None):
        """Run the next ready job inline (the command line, the backfill, the tests). Same handlers and same claim
        as the queue workers (jobs/executor.py); only the way the job is picked differs."""
        # Settings loaded from the table change without a restart: each job starts under the current ones (0.B8).
        self.storage, self.models = refresh(self.storage), refresh(self.models)
        job = self.repo.claim(run_id=run_id)
        if not job:
            return None
        return self.run_claimed(job)

    def run(self, job_id):
        """Run one named job, the way a queue worker does (jobs/executor.py). None when it is no longer runnable."""
        self.storage, self.models = refresh(self.storage), refresh(self.models)
        job = self.repo.claim(job_id=job_id)
        if not job:
            return None
        return self.run_claimed(job)

    def run_claimed(self, job):
        stop = threading.Event()
        def keep_alive():
            while not stop.wait(max(1,self.storage.lease_seconds/3)):
                if not self.repo.heartbeat(job):
                    return
        thread = threading.Thread(target=keep_alive,daemon=True)
        thread.start()
        from .llm import standing
        try:
            # The purpose this job's paid calls spend from the standing weekly budgets (6.B3): a brief revision is a refresh.
            with self.repo.connection() as conn:
                scope = (conn.execute('SELECT run_scope FROM pipeline_runs WHERE run_id=%s',(job['run_id'],)).fetchone() or {}).get('run_scope')
            with standing.purpose(standing.purpose_for_job(scope,job['stage'])):
                self.execute(job)
        except Exception as error:
            # A call refused by a spent standing budget waits for the budget, with its reason shown; anything else fails.
            if refused := standing.refusal(error):
                standing.wait_for_budget(self.repo,job,refused)
            else:
                # A provider's refusal (out of credit, 402) is said in words first; the error follows for the team.
                from .llm import failures
                self.repo.fail(job,failures.message(error))
        finally:
            stop.set(); thread.join(timeout=2)
        return job['job_id']

    def inputs(self, job):
        with self.repo.connection() as conn:
            run = conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(job['run_id'],)).fetchone()
            expected = run['input_refs']['transcripts']
            rows = {r['transcript_id']:r for r in conn.execute('SELECT * FROM transcripts WHERE transcript_id=ANY(%s)',([e['id'] for e in expected],))}
            records = []
            for e in expected:
                row = rows.get(e['id'])
                if not row or row['content_hash']!=e['hash'] or (row['week_id']!=run['week_id'] and not run['input_refs'].get('selected_by')):
                    raise ValueError('Frozen source identity or ownership changed')
                if e.get('view_hash') and e['view_hash']!=canonical_hash([row['original_text'],row['passage_map'],row['source_metadata']]):
                    raise ValueError('Frozen source view changed; create a new assessment intent')
                records.append(row)
            angle_hashes = run['input_refs'].get('angle_hashes')
            if angle_hashes:
                actual = {a['angle_id']:a['content_hash'] for a in conn.execute('SELECT angle_id,content_hash FROM content_angles WHERE angle_id=ANY(%s)',(list(angle_hashes),))}
                if actual!=angle_hashes:
                    raise ValueError('Frozen angle input changed; create a new reassessment')
            return run,records

    def stage_output(self, conn, run_id, stage):
        row = conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage=%s AND status='completed'",(run_id,stage)).fetchone()
        if not row:
            run = conn.execute('SELECT input_refs FROM pipeline_runs WHERE run_id=%s',(run_id,)).fetchone()
            if stage=='angle_generation' and run['input_refs'].get('angle_ids'):
                return {'angle_ids':run['input_refs']['angle_ids']}
            raise ValueError('Stage dependency is not complete')
        return row['result_refs']

    def check_source_views(self, conn, run):
        expected = run['input_refs']['transcripts']
        rows = {r['transcript_id']:r for r in conn.execute('SELECT * FROM transcripts WHERE transcript_id=ANY(%s) FOR SHARE',([e['id'] for e in expected],))}
        for e in expected:
            r = rows.get(e['id'])
            if not r or (r['week_id']!=run['week_id'] and not run['input_refs'].get('selected_by')) or r['content_hash']!=e['hash'] or e.get('view_hash') and e['view_hash']!=canonical_hash([r['original_text'],r['passage_map'],r['source_metadata']]):
                raise ValueError('Frozen source view changed before commit; create a new assessment intent')

    def adapter(self, run, transcripts, refs):
        mode = run['input_refs']['mode']
        if mode=='live' and not self.storage.generation_enabled:
            raise ValueError('SQL generation is disabled')
        if mode=='live':
            self.models.require_explicit_models()  # section 4.10: a paid stage names its model
        if mode=='synthetic' and not self.storage.synthetic:
            raise ValueError('Synthetic run in a real database')
        settings = self.models.model_copy(update={'data_root':self.storage.artifact_root,'embeddings_enabled':False})
        # Every call of the SQL path is an llm_runs row in the database (0.B4), never a line in a file on the worker's disk.
        p = Pipeline(settings,self.provider,runs=LlmRuns.for_storage(self.storage))
        p.store = CacheStore(backend_for(self.storage.artifact_root),self.models.data_root)
        p._compact_refs = refs
        p._select_provider('fake' if mode=='synthetic' else mode)
        # Context comes from the assembly service, dated by the run so a retry sees the same items (L.B5).
        p.context_connection = self.repo.connection
        if hasattr(p.provider, 'input_set_hash'):
            p.provider.input_set_hash = run_input_set_hash(run)
        p.context_date = run['created_at'].date() if run.get('created_at') else None
        manifest = RunManifest(run_id=run['run_id'],week_index=run['input_refs']['week_index'],source_root='sql',
            source_ids=[t.source_id for t in transcripts],prompt_profile=LIVE_COMPACT_VERSION,
            model_id=settings.model_for('angle_generation'),embedding_profile=f'{settings.embedding_model}:1536',
            mode='fake' if mode=='synthetic' else mode,execution_scope='generation_only')
        return p,manifest

    @staticmethod
    def stable_contract(contract):
        """A retry may see operating facts confirmed since the first attempt; the profile, model, version and
        identity documents stay frozen (S.B2 review)."""
        from .knowledge.assembly import stable_refs
        return {**contract, 'knowledge_base': stable_refs(contract.get('knowledge_base'))} if contract else contract

    def freeze_angle_contract(self, job, run, contract):
        """Bind the run to one angle profile, model and knowledge-base version, like transcripts are bound."""
        with self.repo.connection() as conn:
            self.repo.guard(conn,job)
            refs = conn.execute('SELECT input_refs FROM pipeline_runs WHERE run_id=%s FOR UPDATE',(run['run_id'],)).fetchone()['input_refs']
            frozen = refs.get('angle_contract')
            if frozen is None:
                refs['angle_contract'] = contract
                conn.execute('UPDATE pipeline_runs SET input_refs=%s WHERE run_id=%s',(Jsonb(refs),run['run_id']))
            elif self.stable_contract(frozen)!=self.stable_contract(contract):
                raise ValueError('Frozen angle profile, model or knowledge base changed; restore it or create a new run')

    def origin(self, conn, artifact, run):
        if artifact.run_id==run['run_id']:
            return
        existing = conn.execute('SELECT week_id,run_scope,input_refs FROM pipeline_runs WHERE run_id=%s',(artifact.run_id,)).fetchone()
        # A document's own extraction (2.B2) is week-less: its saved answer serves whichever cycle reads that document (the
        # order Phase N2 runs: the window extracted by document, then its cycle; found by the N1 shakedown).
        week_less = existing and existing['week_id'] is None and existing['run_scope'] in policy.PER_DOCUMENT_SCOPES
        if existing and existing['week_id']!=run['week_id'] and not week_less:
            raise ValueError('Cached origin run belongs to another week')
        insert(conn,'pipeline_runs',{'run_id':artifact.run_id,'week_id':run['week_id'],
               'run_scope':'artifact_origin','status':'completed','trigger_type':'manual',
               'input_refs':run['input_refs'],'created_at':artifact.created_at},conflict=True)

    def execute(self, job):
        from .search.jobs import STAGES as SEARCH_STAGES
        if job['stage'] in SEARCH_STAGES:  # moment embeddings and topic assignment (2.B5, 2.B7)
            from .search.jobs import execute
            execute(self, job)
            return
        if job['stage']=='moment_extraction' and job.get('transcript_id'):
            # One document's own extraction (2.B2); the weekly per-run extraction below is unchanged.
            from .moments.jobs import execute
            execute(self,job)

            return
        if job['stage']=='evaluation_run':
            # The scheduled benchmark of an approved identity change (L.B11), under a standing run plan.
            from .knowledge.benchmarking import execute
            execute(self, job)
            return
        from .documents.jobs import DOCUMENT_STAGES
        if job['stage'] in DOCUMENT_STAGES:
            from .documents.jobs import execute
            execute(self, job)
            return
        if job['stage']=='card_refresh':
            # Gate 1's refresh with feedback (3.B7): one model call, a new card version.
            from .cycle.refresh import execute
            execute(self, job)
            return
        if job['stage'].startswith('pack_'):
            from .packs.workflow import execute
            execute(self, job)
            return
        from .briefs.contracts import STAGES as BRIEF_STAGES
        if job['stage'] in BRIEF_STAGES:
            from .briefs.workflow import execute
            execute(self,job)
            return
        run,records = self.inputs(job)
        if job['stage']=='transcript_chunk_embedding':
            from .chunk_encoding import execute
            execute(self,job,run)
            return
        comparison = run['input_refs'].get('workflow')==WORKFLOW
        if job['stage'] in {'angle_embedding','angle_initial_embedding','angle_refined_embedding'}:
            self.encode(job,run); return
        if job['stage']=='history_context':
            with self.repo.connection() as conn:
                conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                self.repo.guard(conn,job)
                ids = run['input_refs'].get('moment_ids')
                if ids is None:
                    ids = self.stage_output(conn,run['run_id'],'moment_extraction')['moment_ids']
                context = history_context(self.repo,conn,job,run,ids,encoding_contract(self.models,synthetic=self.storage.synthetic))
                self.repo.finish(conn,job,context,message=f"Frozen {len(context['history'])} historical arguments")
            return
        if job['stage'] in {'angle_initial_assessment','angle_final_assessment'}:
            self.compare(job,run); return
        if job['stage']=='angle_matching':
            with self.repo.connection() as conn:
                ids = self.stage_output(conn,run['run_id'],'angle_generation')['angle_ids']
            snapshot = freeze(self.repo,job,ids,encoding_contract(self.models,synthetic=self.storage.synthetic),scoring(run,self.models))
            with self.repo.connection() as conn:
                self.repo.guard(conn,job)
                result = match(conn,snapshot,encoding_contract(self.models,synthetic=self.storage.synthetic))
                self.repo.finish(conn,job,result,status='completed' if result['status']=='complete' else 'waiting',
                                 message='Matching complete' if result['status']=='complete'
                                 else pause_message(result,'Matching incomplete: vectors or quality unavailable'))
                # A card version saved while this run worked waits for it; its check is queued now (E.B16, E.B20).
                queue_deferred_checks(self.repo,conn,run['week_id'])
            return
        transcripts,packet,refs = reconstruct(records)
        p,manifest = self.adapter(run,transcripts,refs)
        run_dir = f'experiments/sql/runs/{run["run_id"]}'
        if job['stage']=='moment_extraction' and self.frozen_extraction(run) in (SCENE_V2_PROFILE,SCENE_V3_PROFILE,SCENE_V4_PROFILE):
            self.frozen_profile(run)
            p.knowledge_base(manifest.mode)
            # The ledger's per-document scenes, under the profile frozen with the run (v3: E.B31's two scene types).
            self.document_scenes(job,run,p,manifest,records,profile=self.frozen_extraction(run))
        elif job['stage']=='moment_extraction' and self.frozen_extraction(run)=='2026-10-18.scenes.v1':
            self.frozen_profile(run)
            p.knowledge_base(manifest.mode)
            self.scenes(job,run,p,manifest,run_dir,records)
        elif job['stage']=='moment_extraction':
            # A changed profile, or a missing or placeholder knowledge base, must fail before extraction is paid for.
            self.frozen_profile(run)
            p.knowledge_base(manifest.mode)
            system,user = weekly_moment_prompt(packet,meeting_inventory(refs))
            input_hash = canonical_hash({'system':system,'user':user,'source':[{'source_id':t.source_id,'revision':t.content_hash} for t in transcripts]})
            def partition(out,run_id):
                # Per-moment (E.B12a): only a schema or coverage failure fails the week.
                resolved,unresolved = resolve_moment_references_partial(out,refs)
                return p._partition_moments(resolved,run_id,transcripts,unresolved=unresolved)
            artifact = p._call_json('moment_extraction',manifest,run_dir,system,user,input_hash,
                StrategicCompactMomentResponse.model_json_schema(),validate=lambda out:partition(out,run['run_id']))
            result = partition(artifact.output,artifact.run_id)
            moments = result.moments
            p.store.write_json(f'{run_dir}/moment_validation.json',result.summary(),overwrite=True)
            with self.repo.connection() as conn:
                self.repo.guard(conn,job); self.origin(conn,artifact,run)
                # One ledger writer for every path (2.B2): document, speaker, role, consent and checks are filled the same way.
                # The weekly path still keeps its unverified moments in the job's result_refs (E.B12a, as before); the per-document
                # extraction stores them as rows. Passing `unverified=result.unverified` here would store them too.
                self.repo.save_moments(conn,artifact.run_id,run['week_id'],moments,records,extractor_version=self.models.extraction_profile,
                                       repairs=result.repairs)
                self.repo.finish(conn,job,{'moment_ids':[m.moment_id for m in moments],'artifact_id':artifact.artifact_id,
                     'dispatched':artifact.request_fingerprint in p._dispatched,'cache_reused':artifact.request_fingerprint not in p._dispatched,
                     'request_fingerprint':artifact.request_fingerprint,'coverage':'complete_delivery_acknowledged',
                     'coverage_notes':artifact.output['coverage_notes'],
                     'revalidated_from_attempt':artifact.metadata.get('revalidated_from_attempt'),
                     **result.summary(),
                     'coverage_is_comprehension_proof':False},
                     message=f'Saved {len(moments)} source-validated moments'+(f'; {len(result.repairs)} quotes repaired' if result.repairs else '')
                             +(f'; {len(result.unverified)} unverified, not used as proof' if result.unverified else ''))
        elif job['stage'] in {'angle_generation','angle_refinement'}:
            with self.repo.connection() as conn:
                context = self.stage_output(conn,run['run_id'],'history_context') if comparison else None
                if context:
                    check_history(conn,context); validate_moments(conn,context,run['week_id'])
                ids = context['moment_ids'] if comparison else self.stage_output(conn,run['run_id'],'moment_extraction')['moment_ids']
                saved = {r['moment_id']:r for r in conn.execute('SELECT * FROM key_moments WHERE moment_id=ANY(%s)',(ids,))}
            if not ids and job['stage']=='angle_generation':
                # E.B12a keeps unverified moments out of proof; with none bound, a strategist call would be paid for
                # cards with no evidence (the file runner fails the week the same way).
                raise ValueError('No moment bound to its source this week (every extracted quote is unverified), so the '
                                 'strategist was not called; check the transcripts or re-run extraction')
            spans = {s.span_id:s for t in transcripts for s in t.spans}
            # Consent (E.B16 f, R40): a do_not_use scene never reaches a model; an internal_only one is internal.
            bodies,dropped = consented(saved,ids)
            if dropped and not bodies and job['stage']=='angle_generation':
                raise ValueError('Every bound moment this week belongs to a client who asked not to be used, so the '
                                 'strategist was not called')
            ids = [mid for mid in ids if mid in bodies]
            moments = []
            for mid in ids:
                row = saved[mid]; evidence = row['evidence_refs']
                context_refs = [r['passage_id'] for r in evidence if 'context' in r['roles']]
                anchors = [r['passage_id'] for r in evidence if 'anchor' in r['roles']]
                moments.append(Moment(moment_id=mid,source_ids=sorted({spans[x].source_id for x in anchors}),
                                      anchor_span_ids=anchors,context_span_ids=context_refs,**bodies[mid]))
            if comparison:
                with self.repo.connection() as conn:
                    frozen = self.stage_output(conn,run['run_id'],'history_context')
                manifest.prompt_profile = WORKFLOW
            if job['stage']=='angle_refinement':
                self.refine(job,run,records,p,manifest,run_dir,moments,transcripts,frozen); return
            profile = self.frozen_profile(run)
            if uses_cards(profile):
                try:
                    self.cards(job,run,p,manifest,run_dir,moments,transcripts,ids,comparison=frozen if comparison else None,
                               consent_dropped=dropped)
                except RuntimeError as error:
                    # A week too large for one call leaves out its internal_only scenes (internal insight, never a public
                    # card's proof) rather than stopping the cycle; the scene coverage says which were not sent. A week that
                    # still does not fit fails as before: a public-eligible scene is never left out (2 November 2026).
                    if job['stage']!='angle_generation' or not str(error).startswith(OVERSIZED_WEEK):
                        raise
                    internal = {mid for mid in ids if saved[mid].get('consent_status')=='internal_only'
                                or bodies[mid].get('sensitivity')=='internal_only'}
                    if not internal or len(internal)==len(ids):
                        raise
                    log.warning('Week %s is too large for one strategist call: %d internal_only scenes left out',
                                run['week_id'],len(internal))
                    self.cards(job,run,p,manifest,run_dir,[m for m in moments if m.moment_id not in internal],transcripts,
                               [mid for mid in ids if mid not in internal],comparison=frozen if comparison else None,
                               consent_dropped=dropped,size_dropped=sorted(internal))
                return
            system,user = sql_angle_prompt(p._moment_packet(moments,transcripts),frozen['historical_packet'],profile) if comparison else angle_prompt(p._moment_packet(moments,transcripts),[],profile)
            input_hash = canonical_hash({'system':system,'user':user,'moment_ids':ids,
                                         **({'workflow':WORKFLOW,'sources':run['input_refs']['transcripts']} if comparison else {})})
            artifact = p._call_json('angle_generation',manifest,run_dir,system,user,input_hash,
                StrategicAngleResponse.model_json_schema(),validate=lambda out:p._parse_angles(adapt_angle_response(out,moments)[0] if comparison else out,run['run_id'],moments),
                prompt_version=profile)
            interpreted,citation_changes = adapt_angle_response(artifact.output,moments) if comparison else (artifact.output,[])
            angles = p._parse_angles(interpreted,run['run_id'],moments,artifact=artifact)
            p._write_discovery_outputs(run_dir, interpreted, angles)
            clock = {}
            if comparison:
                clock_path = f"intents/{job['job_id']}/evaluation-clock.json"
                p.store.write_json(clock_path,{'evaluation_as_of':datetime.now(UTC).isoformat()})
                clock = p.store.read_json(clock_path)
            with self.repo.connection() as conn:
                self.repo.guard(conn,job); self.origin(conn,artifact,run)
                if comparison:
                    self.check_source_views(conn,run)
                    check_history(conn,frozen); validate_moments(conn,frozen,run['week_id'])
                self.repo.save_angles(conn,run['week_id'],angles)
                self.repo.finish(conn,job,{'angle_ids':[a.angle_id for a in angles],'moment_ids':ids,
                     'citation_adapter':CITATION_VERSION if comparison else None,'citation_adaptations':citation_changes,
                     'dispatched':artifact.request_fingerprint in p._dispatched,'cache_reused':artifact.request_fingerprint not in p._dispatched,
                     **clock,
                     'artifact_id':artifact.artifact_id,'request_fingerprint':artifact.request_fingerprint,
                     'internal_insights':artifact.output.get('internal_insights',[]),
                     'research_required_angle_ids':[a.angle_id for a in angles if a.strategy and a.strategy.evidence_readiness=='research_required'],
                     'consent_dropped':dropped,
                     'coverage':'complete_generation','coverage_notes':artifact.output['coverage_notes']},message=f'Saved {len(angles)} valid angle candidates')
        else:
            raise ValueError('Unsupported stage')

    def frozen_extraction(self, run):
        frozen = run['input_refs'].get('extraction_profile','2026-10-13.weekly.v3')
        if frozen!=self.models.extraction_profile:
            raise ValueError('The extraction profile frozen at submit differs from the worker configuration; restore it or create a new run')
        return frozen

    def document_scenes(self, job, run, p, manifest, records, *, profile=SCENE_V2_PROFILE):
        """E.B12: the week's scenes are the moments ledger's, from each document's own extraction (2.B2).

        A document already extracted under this profile and knowledge base (by the backfill, a document job or an earlier
        cycle: the same extraction key) is reused with no provider call; any other is extracted here, through the same
        function a document's job runs (`moments.jobs.extract_document`: the scene prompt, `partition_scenes` with its repair
        and rebind rules, the one ledger writer), under this run's mode and plan, and stays in the ledger for later cycles.
        The week reads the verified scenes; unverified records stay rows that are never proof (E.B12a)."""
        from .knowledge.assembly import stable_refs
        from .moments import queue as extraction_queue
        from .moments.jobs import already_extracted, extract_document
        kb = p.context('extraction', manifest.mode)
        kb_refs = stable_refs(kb.refs())
        with self.repo.connection() as conn:
            terms = conn.execute("SELECT term,kind,variants FROM glossary_terms WHERE status='active'").fetchall()
        moment_ids, unverified_ids, documents, failed, failed_ids, dispatched = [], [], [], [], [], False
        for record in sorted(records, key=lambda r: r['transcript_id']):
            key = extraction_queue.extraction_key(record, profile, kb_refs)
            with self.repo.connection() as conn:
                done = already_extracted(conn, record['transcript_id'], key, job['job_id'])
            if done is not None:
                moment_ids += done['moment_ids']; unverified_ids += done['unverified_ids']
                documents.append({'transcript_id': record['transcript_id'], 'extraction_key': key,
                                  'reused_from_job': done['job_id'], 'provider_calls': 0})
                continue
            reconstructed = reconstruct([record])
            pd, md = self.adapter(run, reconstructed[0], reconstructed[2])
            try:
                saved, result, artifact = extract_document(self, run, job, record, profile=profile, key=key, terms=terms, p=pd,
                                                           manifest=md, kb=kb, reconstructed=reconstructed)
            except ValueError as error:  # a schema failure after its repair is one (SchemaViolation)
                # One failed document affects no other (2.B2): the rest are still extracted and kept in the ledger, so a
                # retry of the week sends only the documents that failed. The week itself fails below (E.B12a).
                failed.append(f"{record.get('title') or record['transcript_id']}: {error}")
                failed_ids.append(record['transcript_id'])
                dispatched = dispatched or bool(pd._dispatched)
                continue
            moment_ids += saved['moment_ids']; unverified_ids += saved['unverified_ids']
            dispatched = dispatched or artifact.request_fingerprint in pd._dispatched
            # A document whose scenes are saved is extracted, whatever happens to the week's other documents (N8 shakedown: one
            # free model's timeout on one call marked all eleven calls of the week failed).
            with self.repo.connection() as conn:
                conn.execute("UPDATE transcripts SET extraction_status='completed' WHERE transcript_id=%s AND included",
                             (record['transcript_id'],))
            documents.append({'transcript_id': record['transcript_id'], 'extraction_key': key, 'artifact_id': artifact.artifact_id,
                              'request_fingerprint': artifact.request_fingerprint, **result.summary()})
        if failed and (not moment_ids or len(failed) * 2 > len(records)):
            raise ValueError(f"{len(failed)} of {len(records)} documents failed scene extraction; the others are in the moments "
                             "ledger and a retry sends only these: " + "; ".join(failed))
        if failed:
            # The cycle runs unattended: a minority of calls whose scenes could not be extracted no longer stops the week
            # (production, 4 November: one provider error on one call would have). The week goes on with the others' scenes;
            # these calls show with no scenes in the coverage, and the job and an event name them.
            log.warning('Week %s goes on without %d of %d documents: %s', run['week_id'], len(failed), len(records), '; '.join(failed))
            with self.repo.connection() as conn:
                self.repo.event(conn, run['run_id'], 'documents_not_extracted',
                                f"{len(failed)} of {len(records)} calls could not be read for scenes; the week goes on without them",
                                job=job, details={'failed': failed}, severity='warning')
        reused = sum(1 for d in documents if 'reused_from_job' in d)
        with self.repo.connection() as conn:
            self.repo.guard(conn, job)
            self.repo.finish(conn, job, {'moment_ids': moment_ids, 'unverified_ids': unverified_ids, 'extraction_profile': profile,
                 'documents': documents, 'dispatched': dispatched,
                 **({'failed_documents': failed, 'coverage': 'partial_documents_failed'} if failed
                    else {'coverage': 'complete_delivery_acknowledged'}),
                 'unverified_count': len(unverified_ids), 'unverified_usable_as_proof': False,
                 'coverage_is_comprehension_proof': False, 'extraction_knowledge_base': kb.refs()},
                 message=f'{len(moment_ids)} verified scenes from {len(documents)} documents ({reused} already in the ledger)'
                         + (f'; {len(unverified_ids)} unverified, not used as proof' if unverified_ids else '')
                         + (f'; {len(failed)} could not be read and are left out' if failed else ''))
            if failed_ids:
                # Finishing marked every document of the week extracted; the ones left out stay failed, so a later cycle
                # over them sends only these.
                conn.execute("UPDATE transcripts SET extraction_status='failed' WHERE transcript_id=ANY(%s) AND included",
                             (failed_ids,))

    def scenes(self, job, run, p, manifest, run_dir, records):
        """E.B12: one scene call per document, each validated scene by scene with E.B12a's repair rule."""
        from .moment_validation import MomentPartition, resolve_moment_references_partial
        from .moments.scenes import SCENE_PROFILE, scene_prompt, schema, sensitivity_tags, to_compact
        kb = p.context('extraction', manifest.mode)
        combined, artifacts, notes = MomentPartition(), [], []
        for record in records:
            transcripts,packet,refs = reconstruct([record])
            system,user = scene_prompt(packet,meeting_inventory(refs),kb.text,sensitivity_tags(record))
            input_hash = canonical_hash({'system':system,'user':user,'source':[{'source_id':t.source_id,'revision':t.content_hash} for t in transcripts]})
            def partition(out,run_id,refs=refs,transcripts=transcripts):
                resolved,unresolved = resolve_moment_references_partial(to_compact(out),refs)
                return p._partition_moments(resolved,run_id,transcripts,unresolved=unresolved)
            artifact = p._call_json('moment_extraction',manifest,run_dir,system,user,input_hash,schema(),
                validate=lambda out,partition=partition:partition(out,run['run_id']),prompt_version='2026-10-18.scenes.v1')
            result = partition(artifact.output,artifact.run_id)
            combined.moments += result.moments; combined.repairs += result.repairs; combined.unverified += result.unverified
            artifacts.append(artifact); notes += artifact.output['coverage_notes']
        p.store.write_json(f'{run_dir}/moment_validation.json',combined.summary(),overwrite=True)
        with self.repo.connection() as conn:
            self.repo.guard(conn,job)
            for artifact in artifacts:
                self.origin(conn,artifact,run)
            self.repo.save_moments(conn,run['run_id'],run['week_id'],combined.moments,records,extractor_version=SCENE_PROFILE,
                                   repairs=combined.repairs,roster=kb.roster)
            self.repo.finish(conn,job,{'moment_ids':[m.moment_id for m in combined.moments],'extraction_profile':'2026-10-18.scenes.v1',
                 'artifact_ids':[a.artifact_id for a in artifacts],'request_fingerprints':[a.request_fingerprint for a in artifacts],
                 'dispatched':any(a.request_fingerprint in p._dispatched for a in artifacts),'coverage':'complete_delivery_acknowledged',
                 'coverage_notes':notes,**combined.summary(),'coverage_is_comprehension_proof':False,
                 'extraction_knowledge_base':kb.refs()},
                 message=f'Saved {len(combined.moments)} scenes from {len(artifacts)} documents'
                         +(f'; {len(combined.repairs)} quotes repaired' if combined.repairs else '')
                         +(f'; {len(combined.unverified)} unverified, not used as proof' if combined.unverified else ''))

    def frozen_profile(self, run):
        """The angle profile frozen at submit (E.B16 d). Runs submitted before the freeze use the worker's profile."""
        frozen = run['input_refs'].get('angle_prompt_profile')
        if frozen is not None and frozen!=self.models.angle_prompt_profile:
            raise ValueError('The angle profile frozen at submit differs from the worker configuration; restore it or create a new run')
        models = run['input_refs'].get('models')
        if models is not None and models!=frozen_models(self.models):
            raise ValueError('The models frozen at submit differ from the worker configuration ('+', '.join(
                f'{k}: {v} at submit, {frozen_models(self.models)[k]} now' for k,v in models.items() if v!=frozen_models(self.models).get(k))
                +'); restore them or create a new run')
        profile = frozen or self.models.angle_prompt_profile
        # Submit checks this when it is given the models; a live run queued without them is checked here (E.B17).
        from .angle_profiles import check_live_profile
        check_live_profile(profile, run['input_refs'].get('mode'))
        return profile

    def evidence_classes(self, ids, identities):
        """The scenes from internal meetings (team practice, D24) and, for each scene, the identities of its call: the people
        who speak in it and its account. Empty before migration 010 and for a run frozen without identity records."""
        if identities is None:
            return set(), {}  # a profile that reads neither (strategist v7 and earlier): its requests stay as they were
        from .moments.store import has_ledger
        with self.repo.connection() as conn:
            if not ids or not has_ledger(conn) or not conn.execute(
                    "SELECT 1 FROM information_schema.columns WHERE table_name='key_moments' AND column_name='evidence_class'").fetchone():
                return set(), {}
            rows = conn.execute("""SELECT m.moment_id,m.evidence_class,t.client_id,t.speaker_map FROM key_moments m
                LEFT JOIN transcripts t ON t.transcript_id=m.document_id WHERE m.moment_id=ANY(%s)""",(ids,)).fetchall()
        team = {r['moment_id'] for r in rows if r['evidence_class']=='team_practice'}
        known = {i['id'] for i in identities or []}
        by_moment = {r['moment_id']:sorted(({r['client_id']} | {a.get('person_id') for a in (r['speaker_map'] or {}).values()}) & known)
                     for r in rows} if known else {}
        return team, by_moment

    def cards(self, job, run, p, manifest, run_dir, moments, transcripts, ids, *, comparison=None, consent_dropped=(),
              size_dropped=()):
        """Strategist cards on either runner. On the comparison runner the evidence and history stay frozen,
        and refinement is skipped for cards (they are ranked, not self-scored)."""
        knowledge_base = p.knowledge_base(manifest.mode)
        contract = p.angle_input_refs(knowledge_base)
        self.freeze_angle_contract(job,run,contract)
        extra = {'workflow':WORKFLOW,'sources':run['input_refs']['transcripts']} if comparison else None
        from .cycle import seeds as founder_seeds
        frozen_seeds = run['input_refs'].get('seeds')
        # The window's strategy brief, frozen with the run at submit (E.B28): strategist v7 reads it, and every card is checked
        # against its offer calendar.
        brief = run['input_refs'].get('strategy_brief')
        # Phase N8: the identity records frozen with a strategist v8 run, and which scenes come from internal meetings (D24).
        identities = run['input_refs'].get('identities')
        team, identity_ids = self.evidence_classes(ids, identities)
        artifact,output,angles,repair = p.generate_cards(manifest,run_dir,moments,transcripts,knowledge_base,extra_input=extra,
            seeds=founder_seeds.prompt_seeds(frozen_seeds) if frozen_seeds is not None else None,strategy_brief=brief,
            team_practice=team,identities=identities)
        # E.B10: the evidence ledger, built before the transaction (the model pass, when configured, is a paid call).
        # It runs before the selection is taken: a card the critic's reframe repaired replaces the original in `angles`.
        ledgers = p.verify_cards(manifest,run_dir,angles,moments,transcripts,strategy_brief=brief,team_practice=team,
                                 identities=identities,identity_ids=identity_ids)
        # 3.B5: a card repeating a point WIA published inside the repetition window ranks below the new points (D23).
        from .cycle import recency
        with self.repo.connection() as conn:
            windows = recency.windows(conn)
        angles,output,recent_repeats = recency.apply(angles,ledgers,output,getattr(p,'context_date',None) or date.today(),*windows)
        selection = founder_seeds.resolve_pairings(p.card_selection(output,angles,moments),frozen_seeds or [])
        p._write_discovery_outputs(run_dir,output,angles,moments)
        clock = {}
        if comparison:
            clock_path = f"intents/{job['job_id']}/evaluation-clock.json"
            p.store.write_json(clock_path,{'evaluation_as_of':datetime.now(UTC).isoformat()})
            clock = p.store.read_json(clock_path)
        dispatched = [a for a in ([repair['first_request_fingerprint']] if repair else [])+[artifact.request_fingerprint] if a in p._dispatched]
        with self.repo.connection() as conn:
            self.repo.guard(conn,job); self.origin(conn,artifact,run)
            if comparison:
                self.check_source_views(conn,run)
                check_history(conn,comparison); validate_moments(conn,comparison,run['week_id'])
            self.repo.save_angles(conn,run['week_id'],angles)
            from .cycle.verification import attach
            verification = attach(conn,ledgers)
            # A card that undercuts an offer in force is held until the offer's window ends, the offer named (E.B28).
            from .cycle.strategy_brief import hold_for
            held = {}
            for angle_id,ledger in ledgers.items():
                if hold := hold_for(ledger['flags']):
                    conn.execute("UPDATE content_angles SET content_body=content_body||jsonb_build_object('gate_one_hold',%s::jsonb) "
                                 "WHERE angle_id=%s",(Jsonb(hold),angle_id))
                    held[angle_id] = hold
            # A stale or missing content plan is said in the week summary (L.B10); the next monthly entry clears it.
            from .knowledge.staleness import plan_warning
            plan = plan_warning(conn)
            self.repo.finish(conn,job,{'angle_ids':[a.angle_id for a in angles],'moment_ids':ids,
                 'verification':verification,
                 'angle_prompt_profile':contract['angle_prompt_profile'],'angle_model':contract['angle_model'],
                 'knowledge_base_sha256':contract['knowledge_base']['sha256'],
                 'dispatched':bool(dispatched),'cache_reused':not dispatched,
                 'artifact_id':artifact.artifact_id,'request_fingerprint':artifact.request_fingerprint,
                 'reference_repair':repair,**clock,
                 **({'strategy_brief_hash':brief.get('brief_hash'),'held_by_strategy_brief':held} if brief else {}),
                 **({'same_point_recency':recent_repeats} if recent_repeats else {}),
                 'verifier_knowledge_base':getattr(p,'verifier_context',None),
                 # Scenes kept from the strategist because their client asked not to be used (E.B16 f).
                 'consent_dropped':list(consent_dropped),
                 # internal_only scenes left out because the whole week did not fit one call (shown as not sent).
                 **({'size_dropped':list(size_dropped)} if size_dropped else {}),
                 # The scenes the strategist saw, document by document (3.B3): every verified scene of each selected call.
                 'scene_coverage':scene_coverage(conn,run,sent=ids,dropped=consent_dropped),
                 **({'workflow':WORKFLOW,'refinement':'skipped_for_cards'} if comparison else {}),
                 **selection,
                 **({'seed_ids':[s['seed_id'] for s in frozen_seeds]} if frozen_seeds is not None else {}),
                 **({'plan_warning':plan} if plan else {}),
                 'coverage':'complete_generation'},message=f'Saved {len(angles)} ranked angle cards')
            if frozen_seeds:
                founder_seeds.mark_used(conn,frozen_seeds,run['run_id'],selection)

    def compare(self, job, run):
        final = job['stage']=='angle_final_assessment'
        manual = bool(run['input_refs'].get('comparison_reassessment'))
        with self.repo.connection() as conn:
            context = self.stage_output(conn,run['run_id'],'history_context')
            generation = self.stage_output(conn,run['run_id'],'angle_generation')
            originals = generation['angle_ids']
            initial = self.stage_output(conn,run['run_id'],'angle_initial_assessment') if final and not manual else None
            refinement = self.stage_output(conn,run['run_id'],'angle_refinement') if final and not manual else None
        families = None
        candidate_ids = originals
        if final:
            if manual:
                families = run['input_refs']['families']
            else:
                outcomes = {f['original_id']:f for f in refinement['dispositions']}
                families = [outcomes.get(mid,{'original_id':mid,'replacement_id':None,'targeted':False,
                                              'disposition':'unchanged','explanation':'No refinement required'}) for mid in originals]
                candidate_ids = originals + refinement['angle_ids']
        contract = encoding_contract(self.models,synthetic=self.storage.synthetic)
        snapshot = freeze_assessment(self.repo,job,candidate_ids,context,prior=initial['assessment_snapshot'] if initial else None,
                                     as_of=generation.get('evaluation_as_of'),contract=contract,scoring_values=scoring(run,self.models))
        with self.repo.connection() as conn:
            self.repo.guard(conn,job)
            self.check_source_views(conn,run)
            result = evaluate(self.repo,conn,job,snapshot,contract,context,families=families)
            self.repo.finish(conn,job,result,status='waiting' if result['status']=='incomplete' else 'completed',
                             message=pause_message(result,'Comparison paused: compatible vectors or quality unavailable') if result['status']=='incomplete'
                             else 'Cards ranked and collapsed; ready for Gate 1' if final and result.get('selection_basis')=='card_rank'
                             else 'Comparison complete; threshold selection pending' if final else f"Initial assessment complete; {len(result['targets'])} refinement targets")
            if final:
                # A card version saved while this run worked waits for it; its check is queued now (E.B16, E.B20).
                queue_deferred_checks(self.repo,conn,run['week_id'])

    def refine(self, job, run, records, p, manifest, run_dir, moments, transcripts, context):
        contract = encoding_contract(self.models,synthetic=self.storage.synthetic)
        with self.repo.connection() as conn:
            if self.stage_output(conn,run['run_id'],'angle_generation').get('refinement')=='skipped_for_cards':
                self.repo.finish(conn,job,{'workflow':WORKFLOW,'angle_ids':[],'dispositions':[],'target_ids':[],
                                         'completion':'skipped_for_cards','dispatched':False},
                                 message='Cards are ranked, not refined; Call 3 skipped')
                return
            initial = self.stage_output(conn,run['run_id'],'angle_initial_assessment')
            original_ids = self.stage_output(conn,run['run_id'],'angle_generation')['angle_ids']
            originals = {a['angle_id']:a for a in conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s)',(original_ids,))}
            if assess(conn,initial['assessment_snapshot'],contract)['status']!='complete':
                self.repo.finish(conn,job,{'status':'incomplete','workflow':WORKFLOW},status='waiting',message='Refinement paused: matching coverage changed')
                return
        targets = initial['targets']
        if not targets:
            with self.repo.connection() as conn:
                self.repo.finish(conn,job,{'workflow':WORKFLOW,'angle_ids':[],'dispositions':[],
                                         'target_ids':[],'completion':'no_targets','dispatched':False},message='No refinement targets; Call 3 skipped')
            return
        if run['input_refs']['mode']=='live' and not self.storage.refinement_enabled:
            raise ValueError('External refinement permission is disabled; replay is available')
        target_map = {t['original_id']:originals[t['original_id']] for t in targets}
        with self.repo.connection() as conn:
            if conn.execute('SELECT 1 FROM content_angles WHERE supersedes_id=ANY(%s) LIMIT 1',(list(target_map),)).fetchone():
                raise ValueError('A targeted family already has a replacement; use saved-angle comparison reassessment')
            proposals = [{'angle_id':a['angle_id'],'content_body':a['content_body'],
                          'moment_ids':[r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s',(a['angle_id'],))]}
                         for a in originals.values()]
        target_packet = [{**t,'original':originals[t['original_id']]['content_body'],
                          'assessment':initial['assessments'][t['original_id']]} for t in targets]
        # Avoid shipping nested storage snapshots redundantly in each target.
        for target in target_packet:
            target['assessment'] = {k:v for k,v in target['assessment'].items() if k not in {'snapshot','history'}}
        profile = self.frozen_profile(run)
        system,user = sql_refinement_prompt(p._moment_packet(moments,transcripts),target_packet,proposals,context['historical_packet'],profile)
        input_hash = canonical_hash({'system':system,'user':user,'workflow':WORKFLOW,
                                     'sources':run['input_refs']['transcripts'],'snapshot':initial['assessment_snapshot'],
                                     'target_ids':sorted(target_map)})
        def validate(out):
            return parse_refinement(p,out,run['run_id'],moments,target_map)
        artifact = p._call_json('angle_refinement',manifest,run_dir,system,user,input_hash,
                               StrategicRefinementResponse.model_json_schema(),validate=validate,prompt_version=profile)
        angles,parents,dispositions = parse_refinement(p,artifact.output,run['run_id'],moments,target_map,artifact=artifact)
        with self.repo.connection() as conn:
            self.repo.guard(conn,job)
            self.check_source_views(conn,run)
            check_history(conn,context); validate_moments(conn,context,run['week_id'])
            if assess(conn,initial['assessment_snapshot'],contract)['status']!='complete':
                raise ValueError('Frozen vectors changed after refinement; create a new assessment intent')
            self.origin(conn,artifact,run)
            for parent in parents.values():
                existing = conn.execute('SELECT angle_id FROM content_angles WHERE supersedes_id=%s FOR UPDATE',(parent,)).fetchall()
                if any(e['angle_id'] not in parents for e in existing):
                    raise ValueError('Refinement family changed during execution')
            self.repo.save_angles(conn,run['week_id'],angles,parents=parents)
            self.repo.finish(conn,job,{'workflow':WORKFLOW,'target_ids':sorted(target_map),
                 'angle_ids':[a.angle_id for a in angles],'dispositions':dispositions,
                 'artifact_id':artifact.artifact_id,'request_fingerprint':artifact.request_fingerprint,
                 'actual_refined_at':artifact.created_at.isoformat(),'coverage_notes':artifact.output['coverage_notes'],
                 'dispatched':artifact.request_fingerprint in p._dispatched,
                 'cache_reused':artifact.request_fingerprint not in p._dispatched},
                 message=f'Saved {len(angles)} replacements from one refinement pass')

    def encode(self, job, run):
        with self.repo.connection() as conn:
            data = self.stage_output(conn,run['run_id'],'angle_refinement' if job['stage']=='angle_refined_embedding' else 'angle_generation')
            rows = conn.execute('SELECT * FROM content_angles WHERE angle_id=ANY(%s) ORDER BY angle_id',(data['angle_ids'],)).fetchall()
            current = conn.execute('SELECT progress_details FROM pipeline_jobs WHERE job_id=%s',(job['job_id'],)).fetchone()
        mode = (current['progress_details'] or {}).get('encoding_mode','cached')
        if mode=='live' and not self.storage.encoding_enabled:
            raise ValueError('SQL external encoding permission is disabled')
        contract = encoding_contract(self.models,synthetic=self.storage.synthetic)
        store = store_for(self.storage)
        with self.repo.connection() as conn:
            provenance = vector_provenance(conn,contract)
        provider = self.provider
        if mode=='live':
            provider = live_provider(self.models,storage=self.storage,chat=False,
                on_response=lambda fingerprint,raw:store.write_json(
                    f"encoding-attempts/{fingerprint}/{job['job_id']}.{job['attempt_count']}/response.raw.json",raw))
        vectors, missing, reused = [], [], 0
        for a in rows:
            signature = signature_from_fields(a['content_body'])
            ih = canonical_hash(signature)
            key = canonical_hash({'contract':contract,'input_hash':ih})
            path = f'encoding/{key}.json'
            proof = provenance.get((a['angle_id'],ih))
            if a['embedding_input_hash']==ih and vector_valid(a['embedding']) and proof and proof.get('vector_digest')==vector_digest(a['embedding']):
                reused += 1
                vector = [float(x) for x in a['embedding']]
            elif store.exists(path):
                reused += 1
                cached = store.read_json(path)
                vector = cached['vector']
                if cached['contract']!=contract or cached['input_hash']!=ih or cached['vector_hash']!=canonical_hash(vector):
                    raise ValueError('Encoding cache integrity failure')
            elif provider and (self.storage.synthetic and run['input_refs']['mode']=='synthetic' or mode=='live'):
                # Archive actual received values before validation/SQL writes.
                attempt = f"encoding-attempts/{key}/{job['job_id']}.{job['attempt_count']}"
                store.write_json(attempt+'/request.json',{'contract':contract,'input_hash':ih,
                    'endpoint':self.models.embedding_base_url,'model':self.models.embedding_model,
                    'dimensions':1536,'input':signature})
                vector, metadata = provider_embed(provider,LlmRuns.for_storage(self.storage),model=self.models.embedding_model,
                                                   text=signature,fingerprint=key,context={'run_id':run['run_id']})
                store.write_json(attempt+'/embedding.received.json',{'vector':vector,'metadata':metadata})
                if not vector_valid(vector):
                    raise ValueError('Encoding returned invalid, zero or non-1536 vector')
                vector = [float(x) for x in vector]
                store.write_json(path,{'contract':contract,'input_hash':ih,'vector':vector,
                                      'vector_hash':canonical_hash(vector),'metadata':metadata})
            else:
                missing.append(a['angle_id']); continue
            if not vector_valid(vector):
                raise ValueError('Encoding returned invalid, zero or non-1536 vector')
            with self.repo.connection() as conn:
                self.repo.guard(conn,job)
                current_angle = conn.execute('SELECT content_hash FROM content_angles WHERE angle_id=%s FOR UPDATE',(a['angle_id'],)).fetchone()
                if current_angle['content_hash']!=a['content_hash']:
                    raise ValueError('Angle changed during encoding')
                conn.execute('UPDATE content_angles SET embedding=%s,embedding_input_hash=%s WHERE angle_id=%s',
                             (vector,ih,a['angle_id']))
                conn.execute('UPDATE pipeline_jobs SET completed_units=%s,total_units=%s WHERE job_id=%s',
                             (len(vectors)+1,len(rows),job['job_id']))
            vectors.append({'angle_id':a['angle_id'],'input_hash':ih,'content_hash':a['content_hash'],
                            'vector_hash':canonical_hash(vector),'vector_digest':vector_digest(vector)})
        with self.repo.connection() as conn:
            self.repo.finish(conn,job,{'contract':contract,'vectors':vectors,'missing':missing,'cache_reused':reused,'encoded':len(vectors)-reused},
                status='waiting' if missing else 'completed',message='Awaiting compatible angle embeddings' if missing else 'Angle embeddings ready')


CONSENT_DROP_REASON = "The client asked not to be used (consent: do_not_use); the scene never reaches a model"


def consented(saved, ids):
    """The moment bodies a generation call may see, by ID, and the moments it may not (E.B16 f, R40).

    `saved` maps moment IDs to key_moments rows. Consent (moments/checks.py, key_moments.consent_status) can be stricter
    than the extractor's sensitivity, and changes when a client's consent does: a do_not_use moment is dropped and
    recorded with the reason; an internal_only one is handled as internal (internal insights only), however the
    extractor labelled it."""
    bodies, dropped = {}, []
    for mid in ids:
        row = saved[mid]
        consent = row.get('consent_status')
        if consent == 'do_not_use':
            dropped.append({'moment_id': mid, 'reason': CONSENT_DROP_REASON})
            continue
        body = dict(row['moment_body'])
        if consent == 'internal_only':
            body['sensitivity'] = 'internal_only'
        bodies[mid] = body
    return bodies, dropped


def run_input_set_hash(run):
    """The input set a weekly run's paid calls are for: its frozen transcripts. `storage_cli plan input-hash` prints
    it, so a plan can be approved for exactly this run (S.B2 review)."""
    return 'sha256:'+canonical_hash(run['input_refs']['transcripts'])


def queue_encoding(repo,run_id,mode='cached',actor='local-cli'):
    if mode not in {'cached','live'} or mode=='live' and not repo.settings.encoding_enabled:
        raise ValueError('External encoding is disabled or mode invalid')
    with repo.connection() as conn:
        j = conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s AND stage IN ('angle_embedding','angle_initial_embedding','angle_refined_embedding') AND status IN ('waiting','failed') ORDER BY created_at,job_id LIMIT 1 FOR UPDATE",(run_id,)).fetchone()
        if not j or j['status'] not in {'waiting','failed'}:
            raise ValueError('No waiting or failed embedding stage')
        conn.execute("UPDATE pipeline_jobs SET progress_details=%s,status='queued',finished_at=NULL,error_summary=NULL WHERE job_id=%s",
                     (Jsonb({**(j['progress_details'] or {}),'encoding_mode':mode}),j['job_id']))
        conn.execute("UPDATE pipeline_runs SET status='queued' WHERE run_id=%s",(run_id,))
        repo.event(conn,run_id,'encoding_queued','Independent encoding requested',details={'mode':mode,'actor':actor})
        return {'job_id':j['job_id']}
