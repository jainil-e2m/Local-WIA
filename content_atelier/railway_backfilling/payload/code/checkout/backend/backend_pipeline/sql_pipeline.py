"""Durable legacy and historical-comparison workflows with explicit capabilities."""
from __future__ import annotations

import threading
from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from .angle_workflow import WORKFLOW
from .citation_adapter import VERSION as CITATION_VERSION
from .citation_adapter import adapt_angle_response
from .comparison import check_history, evaluate, freeze_assessment, history_context, validate_moments
from .config import Settings
from .contracts import signature_from_fields
from .matching import assess, freeze, match, vector_digest, vector_provenance, vector_valid
from .models import Moment, RunManifest
from .pipeline import Pipeline
from .prompts import ANGLE_PROMPT_VERSION, angle_prompt, sql_angle_prompt, sql_refinement_prompt, weekly_moment_prompt
from .provider import LiveProvider
from .refinement import parse_refinement
from .repository import ContentRepository, insert
from .storage_config import encoding_contract
from .storage_sources import reconstruct
from .store import JsonStore, canonical_hash
from .strategy_contracts import StrategicAngleResponse, StrategicCompactMomentResponse, StrategicRefinementResponse
from .weekly import LIVE_COMPACT_VERSION, meeting_inventory, resolve_moment_references


class CacheStore(JsonStore):
    def __init__(self, root, legacy_root):
        super().__init__(root)
        self.legacy = JsonStore(legacy_root)

    def find_artifact(self, fingerprint):
        return super().find_artifact(fingerprint) or self.legacy.find_artifact(fingerprint)


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
        from .worker_status import heartbeat
        heartbeat(self.storage)
        job = self.repo.claim(run_id=run_id)
        if not job:
            return None
        stop = threading.Event()
        def keep_alive():
            while not stop.wait(max(1,self.storage.lease_seconds/3)):
                heartbeat(self.storage)
                if not self.repo.heartbeat(job):
                    return
        thread = threading.Thread(target=keep_alive,daemon=True)
        thread.start()
        try:
            self.execute(job)
        except Exception as error:
            self.repo.fail(job,str(error))
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
                if not row or row['content_hash']!=e['hash'] or row['week_id']!=run['week_id']:
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
            if not r or r['week_id']!=run['week_id'] or r['content_hash']!=e['hash'] or e.get('view_hash') and e['view_hash']!=canonical_hash([r['original_text'],r['passage_map'],r['source_metadata']]):
                raise ValueError('Frozen source view changed before commit; create a new assessment intent')

    def adapter(self, run, transcripts, refs):
        mode = run['input_refs']['mode']
        if mode=='live' and not self.storage.generation_enabled:
            raise ValueError('SQL generation is disabled')
        if mode=='synthetic' and not self.storage.synthetic:
            raise ValueError('Synthetic run in a real database')
        settings = self.models.model_copy(update={'data_root':self.storage.artifact_root,'embeddings_enabled':False})
        p = Pipeline(settings,self.provider)
        p.store = CacheStore(self.storage.artifact_root,self.models.data_root)
        p._compact_refs = refs
        p._select_provider('fake' if mode=='synthetic' else mode)
        manifest = RunManifest(run_id=run['run_id'],week_index=run['input_refs']['week_index'],source_root='sql',
            source_ids=[t.source_id for t in transcripts],prompt_profile=LIVE_COMPACT_VERSION,
            model_id=settings.openrouter_angles_model,embedding_profile=f'{settings.embedding_model}:1536',
            mode='fake' if mode=='synthetic' else mode,execution_scope='generation_only')
        return p,manifest

    def origin(self, conn, artifact, run):
        if artifact.run_id==run['run_id']:
            return
        existing = conn.execute('SELECT week_id,input_refs FROM pipeline_runs WHERE run_id=%s',(artifact.run_id,)).fetchone()
        if existing and existing['week_id']!=run['week_id']:
            raise ValueError('Cached origin run belongs to another week')
        insert(conn,'pipeline_runs',{'run_id':artifact.run_id,'week_id':run['week_id'],
               'run_scope':'artifact_origin','status':'completed','trigger_type':'manual',
               'input_refs':run['input_refs'],'created_at':artifact.created_at},conflict=True)

    def execute(self, job):
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
                context = history_context(self.repo,conn,job,run,ids)
                self.repo.finish(conn,job,context,message=f"Frozen {len(context['history'])} historical arguments")
            return
        if job['stage'] in {'angle_initial_assessment','angle_final_assessment'}:
            self.compare(job,run); return
        if job['stage']=='angle_matching':
            with self.repo.connection() as conn:
                ids = self.stage_output(conn,run['run_id'],'angle_generation')['angle_ids']
            snapshot = freeze(self.repo,job,ids)
            with self.repo.connection() as conn:
                self.repo.guard(conn,job)
                result = match(conn,snapshot,encoding_contract(self.models,synthetic=self.storage.synthetic))
                self.repo.finish(conn,job,result,status='completed' if result['status']=='complete' else 'waiting',
                                 message='Matching complete' if result['status']=='complete' else 'Matching incomplete: vectors or quality unavailable')
            return
        transcripts,packet,refs = reconstruct(records)
        p,manifest = self.adapter(run,transcripts,refs)
        run_dir = f'experiments/sql/runs/{run["run_id"]}'
        if job['stage']=='moment_extraction':
            system,user = weekly_moment_prompt(packet,meeting_inventory(refs))
            input_hash = canonical_hash({'system':system,'user':user,'source':[{'source_id':t.source_id,'revision':t.content_hash} for t in transcripts]})
            resolve = lambda out:resolve_moment_references(out,refs)
            artifact = p._call_json('moment_extraction',manifest,run_dir,system,user,input_hash,
                StrategicCompactMomentResponse.model_json_schema(),validate=lambda out:p._parse_moments(resolve(out),run['run_id'],transcripts))
            moments = p._parse_moments(resolve(artifact.output),artifact.run_id,transcripts)
            with self.repo.connection() as conn:
                self.repo.guard(conn,job); self.origin(conn,artifact,run)
                self.repo.save_moments(conn,artifact.run_id,run['week_id'],moments,records)
                self.repo.finish(conn,job,{'moment_ids':[m.moment_id for m in moments],'artifact_id':artifact.artifact_id,
                     'dispatched':artifact.request_fingerprint in p._dispatched,'cache_reused':artifact.request_fingerprint not in p._dispatched,
                     'request_fingerprint':artifact.request_fingerprint,'coverage':'complete_delivery_acknowledged',
                     'coverage_notes':artifact.output['coverage_notes'],
                     'coverage_is_comprehension_proof':False},message=f'Saved {len(moments)} source-validated moments')
        elif job['stage'] in {'angle_generation','angle_refinement'}:
            with self.repo.connection() as conn:
                context = self.stage_output(conn,run['run_id'],'history_context') if comparison else None
                if context:
                    check_history(conn,context); validate_moments(conn,context,run['week_id'])
                ids = context['moment_ids'] if comparison else self.stage_output(conn,run['run_id'],'moment_extraction')['moment_ids']
                saved = {r['moment_id']:r for r in conn.execute('SELECT * FROM key_moments WHERE moment_id=ANY(%s)',(ids,))}
            spans = {s.span_id:s for t in transcripts for s in t.spans}
            moments = []
            for mid in ids:
                row = saved[mid]; evidence = row['evidence_refs']
                context_refs = [r['passage_id'] for r in evidence if 'context' in r['roles']]
                anchors = [r['passage_id'] for r in evidence if 'anchor' in r['roles']]
                moments.append(Moment(moment_id=mid,source_ids=sorted({spans[x].source_id for x in anchors}),
                                      anchor_span_ids=anchors,context_span_ids=context_refs,**row['moment_body']))
            if comparison:
                with self.repo.connection() as conn:
                    frozen = self.stage_output(conn,run['run_id'],'history_context')
                manifest.prompt_profile = WORKFLOW
            if job['stage']=='angle_refinement':
                self.refine(job,run,records,p,manifest,run_dir,moments,transcripts,frozen); return
            system,user = sql_angle_prompt(p._moment_packet(moments,transcripts),frozen['historical_packet']) if comparison else angle_prompt(p._moment_packet(moments,transcripts),[])
            input_hash = canonical_hash({'system':system,'user':user,'moment_ids':ids,
                                         **({'workflow':WORKFLOW,'sources':run['input_refs']['transcripts']} if comparison else {})})
            artifact = p._call_json('angle_generation',manifest,run_dir,system,user,input_hash,
                StrategicAngleResponse.model_json_schema(),validate=lambda out:p._parse_angles(adapt_angle_response(out,moments)[0] if comparison else out,run['run_id'],moments),
                prompt_version=ANGLE_PROMPT_VERSION)
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
                     'coverage':'complete_generation','coverage_notes':artifact.output['coverage_notes']},message=f'Saved {len(angles)} valid angle candidates')
        else:
            raise ValueError('Unsupported stage')

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
                                     as_of=generation.get('evaluation_as_of'),contract=contract)
        with self.repo.connection() as conn:
            self.repo.guard(conn,job)
            self.check_source_views(conn,run)
            result = evaluate(self.repo,conn,job,snapshot,contract,context,families=families)
            self.repo.finish(conn,job,result,status='waiting' if result['status']=='incomplete' else 'completed',
                             message='Comparison paused: compatible vectors or quality unavailable' if result['status']=='incomplete'
                             else 'Comparison complete; threshold selection pending' if final else f"Initial assessment complete; {len(result['targets'])} refinement targets")

    def refine(self, job, run, records, p, manifest, run_dir, moments, transcripts, context):
        contract = encoding_contract(self.models,synthetic=self.storage.synthetic)
        with self.repo.connection() as conn:
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
        system,user = sql_refinement_prompt(p._moment_packet(moments,transcripts),target_packet,proposals,context['historical_packet'])
        input_hash = canonical_hash({'system':system,'user':user,'workflow':WORKFLOW,
                                     'sources':run['input_refs']['transcripts'],'snapshot':initial['assessment_snapshot'],
                                     'target_ids':sorted(target_map)})
        validate = lambda out:parse_refinement(p,out,run['run_id'],moments,target_map)
        artifact = p._call_json('angle_refinement',manifest,run_dir,system,user,input_hash,
                               StrategicRefinementResponse.model_json_schema(),validate=validate,prompt_version=ANGLE_PROMPT_VERSION)
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
        store = JsonStore(self.storage.artifact_root)
        with self.repo.connection() as conn:
            provenance = vector_provenance(conn,contract)
        provider = self.provider
        if mode=='live':
            provider = LiveProvider(llm_base_url=self.models.openrouter_base_url,
                moments_model=self.models.openrouter_moments_model,angles_model=self.models.openrouter_angles_model,
                moments_key=None,angles_key=None,embedding_base_url=self.models.embedding_base_url,
                embedding_model=self.models.embedding_model,embedding_key=self.models.embedding_api_key,
                dimensions=1536,timeout=self.models.request_timeout_seconds,
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
            elif store.path(path).is_file():
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
                vector, metadata = provider.embed(text=signature,fingerprint=key)
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
