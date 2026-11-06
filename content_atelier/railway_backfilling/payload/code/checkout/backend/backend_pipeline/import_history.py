"""Explicitly admitted partial Luna baseline. No inference and no artifact rewrites."""
from __future__ import annotations

import json
from psycopg.types.json import Jsonb
from .models import RunManifest, StageArtifact, Moment, Angle
from .pipeline import Pipeline
from .store import JsonStore, canonical_hash
from .storage_sources import reconstruct
from .weekly import resolve_moment_references
from .repository import insert

LUNA_RUN = 'week1-gpt6-luna-partial-angle-diagnostic-20261008-a4'


def import_luna(repo, settings, week_id, *, actor='local-cli'):
    original = JsonStore(settings.data_root)
    prefix = f'experiments/default/runs/{LUNA_RUN}'
    manifest = RunManifest.model_validate(original.read_json(prefix+'/manifest.json'))
    diagnostic = original.read_json(prefix+'/moment_diagnostic.json')
    source_prefix = 'experiments/default/runs/' + diagnostic['source_run_id']
    source_manifest = RunManifest.model_validate(original.read_json(source_prefix+'/manifest.json'))
    failed = original.read_json(source_prefix+'/moment_extraction.failed.json')
    received = original.read_json(diagnostic['received_attempt_directory']+'/output.received.json')
    artifact = StageArtifact.model_validate(original.read_json(prefix+'/angle_generation.json'))
    cached = original.find_artifact(artifact.request_fingerprint)
    if not cached or cached['output_hash'] != artifact.output_hash or canonical_hash(artifact.output)!=artifact.output_hash:
        raise ValueError('Angle artifact integrity verification failed')
    with repo.connection() as conn:
        records = repo.frozen_sources(conn,week_id)
        transcripts,_,refs = reconstruct(records)
        original_packet = original.read_json(source_prefix+'/weekly_packet.json')['artifact_directory']
        original_sources = [original.read_json(str(p.relative_to(original.root))) for p in original.path(original_packet+'/sources').glob('*.json')]
        if {s['source_id']:s['raw_sha256'] for s in original_sources} != {t.source_id:t.content_hash for t in transcripts}:
            raise ValueError('Admitted sources differ from original generation evidence')
        validator = Pipeline(settings)
        accepted, rejected = [], []
        for draft in received['moments']:
            try:
                resolved = resolve_moment_references({**received,'moments':[draft]},refs)
                accepted.extend(validator._parse_moments(resolved,diagnostic['source_run_id'],transcripts))
            except ValueError as error:
                rejected.append(str(error))
        saved_moments = [Moment.model_validate(m) for m in original.read_json(prefix+'/moments.json')]
        if accepted != saved_moments or len(accepted)!=7 or len(rejected)!=2:
            raise ValueError('Partial moment pool failed original-source revalidation')
        angles = validator._parse_angles(artifact.output,LUNA_RUN,accepted,artifact=artifact)
        saved = [Angle.model_validate(a) for a in original.read_json(prefix+'/candidates.json')]
        if angles != saved or len(angles)!=6 or manifest.status!='partial':
            raise ValueError('Expected exactly the six original partial Luna candidates')
        frozen = {'transcripts':[{'id':r['transcript_id'],'hash':r['content_hash']} for r in records],
                  'synthetic':False,'coverage':'accepted_partial_baseline','week_index':1,'mode':'replay'}
        insert(conn,'pipeline_runs',{'run_id':diagnostic['source_run_id'],'week_id':week_id,
               'run_scope':'original_extraction','status':'failed','trigger_type':'manual','input_refs':frozen,
               'created_at':source_manifest.created_at,'has_partial_failures':True,'error_summary':'Original extraction failed two exact quotation checks'},conflict=True)
        conn.execute("UPDATE pipeline_runs SET created_at=%s WHERE run_id=%s AND run_scope='original_extraction'",
                     (source_manifest.created_at,diagnostic['source_run_id']))
        insert(conn,'pipeline_runs',{'run_id':LUNA_RUN,'week_id':week_id,'run_scope':'accepted_partial_baseline',
               'status':'partially_completed','trigger_type':'manual','triggered_by':actor,'input_refs':frozen,
               'created_at':manifest.created_at,'has_partial_failures':True,
               'current_message':'Six accepted partial candidates; awaiting embeddings'},conflict=True)
        already = conn.execute("SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND stage='history_admission'",(LUNA_RUN,)).fetchone()
        repo.save_moments(conn,diagnostic['source_run_id'],week_id,accepted,records)
        repo.save_angles(conn,week_id,angles)
        repo.job(conn,diagnostic['source_run_id'],'moment_extraction',{'accepted_moment_ids':[m.moment_id for m in accepted],
                 'rejected_count':2,'request_fingerprint':failed['request_fingerprint']},status='failed')
        repo.job(conn,LUNA_RUN,'angle_generation',{'angle_ids':[a.angle_id for a in angles],
                 'moment_ids':[m.moment_id for m in accepted],'coverage':'accepted_partial_baseline',
                 'artifact_id':artifact.artifact_id,'request_fingerprint':artifact.request_fingerprint})
        repo.job(conn,LUNA_RUN,'history_admission',{'angle_ids':[a.angle_id for a in angles],
                 'actor':actor,'partial':True,'full_week_extraction':False,'rejected_moments':2})
        repo.job(conn,LUNA_RUN,'angle_embedding',{'angle_ids':[a.angle_id for a in angles]},status='waiting')
        if not already:
            repo.event(conn,LUNA_RUN,'accepted_partial_baseline','User selected six Luna candidates for historical matching',
                       details={'accepted_moments':7,'rejected_moments':2,'angle_count':6,'actor':actor})
        conn.execute("""UPDATE weeks SET active_run_id=CASE WHEN %s THEN %s ELSE active_run_id END,
            status=CASE WHEN %s THEN 'awaiting_embeddings' ELSE status END,
            coverage_notes=COALESCE(coverage_notes,'{}'::jsonb)||%s WHERE week_id=%s""",
                     (not already,LUNA_RUN,not already,Jsonb({'accepted_partial_baseline':True,'accepted_moments':7,'rejected_moments':2}),week_id))
    return {'run_id':LUNA_RUN,'moments':7,'angles':6,'embedding_requests':0,'partial':True}
