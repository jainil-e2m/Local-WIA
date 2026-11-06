"""Read-only independent audit of the completed backfill and provider receipts."""
import json
import hashlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.config import Settings
from backend_pipeline.repository import ContentRepository
from backend_pipeline.backfill import protected_snapshot
from backend_pipeline.storage_sources import chunks
from backend_pipeline.chunk_encoding import contract, provenance, chunk_view, cached_vector, validate_response
from backend_pipeline.matching import vector_valid, vector_digest
from backend_pipeline.store import JsonStore, canonical_hash
from backend_pipeline.database import check

settings=StorageSettings.from_env();models=Settings.from_env();store=JsonStore(settings.artifact_root)
report=store.read_json('verification/transcript-backfill-readiness.json')
assert report['status']=='completed'
baseline=store.read_json(report['operation_artifacts']+'/baseline.json')['protected']
profile=contract(models);receipts={};artifact_paths=set()
with ContentRepository(settings).connection() as conn:
 conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
 assert protected_snapshot(conn,baseline['ids'])==baseline
 schema=check(conn)
 sources=conn.execute('SELECT * FROM transcripts ORDER BY week_id,transcript_id').fetchall()
 rows=conn.execute('SELECT * FROM transcript_chunks ORDER BY chunk_id').fetchall()
 expected={x['chunk_id']:{**x,'transcript_id':s['transcript_id']} for s in sources for x in chunks(s)}
 assert len(sources)==170 and len(rows)==2657 and set(expected)=={x['chunk_id'] for x in rows}
 assert Counter(p['passage_id'] for s in sources for p in s['passage_map'])==Counter(p['passage_id'] for row in rows for p in row['passage_refs'])
 proof=provenance(conn,profile)
 for row in rows:
  v=chunk_view(row);assert v==chunk_view(expected[row['chunk_id']]);p=proof[row['chunk_id']]
  assert all(p[k]==value for k,value in v.items()) and vector_valid(row['embedding'])
  vd=vector_digest(row['embedding']);assert p['vector_digest']==vd
  cache=cached_vector(store,p['cache'],profile,v['input_hash']);assert cache['vector_digest']==vd
  path=p['response_artifact'];artifact_paths.add(path)
  if path not in receipts:
   received=store.read_json(path);request=json.loads(store.path(path).with_name('request.json').read_text(encoding='utf-8'))
   body=request['body'];assert request['endpoint']=='https://openrouter.ai/api/v1/embeddings'
   assert body['model']==models.embedding_model and body['dimensions']==1536 and body['encoding_format']=='float'
   vectors=validate_response(received,len(body['input']),models.embedding_model)
   receipts[path]={'usage':received.get('usage',{}),'by_input':{canonical_hash(t):vector_digest(e) for t,e in zip(body['input'],vectors,strict=True)}}
  assert receipts[path]['by_input'][v['input_hash']]==vd
 for source in sources:
  raw=store.path(f"source-originals/{source['content_hash']}.original").read_bytes();assert hashlib.sha256(raw).hexdigest()==source['content_hash']
  if source['source_type']=='fathom':
   segs=json.loads(raw)['transcript'];assert len(segs)==len(source['passage_map'])
   for seg,p in zip(segs,source['passage_map'],strict=True):
    label=(seg.get('speaker') or {}).get('display_name');text=f"{label}: {seg['text']}" if label else seg['text']
    assert source['original_text'][p['start']:p['end']]==text and p['end_ms'] is None
 weeks=conn.execute('SELECT t.week_id,count(DISTINCT t.transcript_id) transcripts,count(c.chunk_id) chunks,count(c.embedding) embedded FROM transcripts t JOIN transcript_chunks c USING(transcript_id) GROUP BY t.week_id ORDER BY t.week_id').fetchall()
 jobs=conn.execute("SELECT stage,status,count(*) count FROM pipeline_jobs WHERE run_id IN (SELECT run_id FROM pipeline_runs WHERE run_scope='transcript_encoding') GROUP BY stage,status").fetchall()
 active=conn.execute("SELECT count(*) n FROM pipeline_jobs WHERE status IN ('queued','running')").fetchone()['n']
 assert active==0
 new_job_stages=conn.execute("SELECT stage,count(*) count FROM pipeline_jobs WHERE NOT(job_id=ANY(%s)) GROUP BY stage",(baseline['ids']['pipeline_jobs'],)).fetchall()
 assert {r['stage'] for r in new_job_stages}<={'source_admission','transcript_chunk_preparation','transcript_chunk_embedding'}
 originals=json.loads(Path('../research/zoom-local-reconciliation-inventory-2026-10-14.json').read_text(encoding='utf-8'))
 for item in originals:assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
 assert not any((settings.generation_enabled,settings.encoding_enabled,settings.refinement_enabled,models.live_enabled,models.embeddings_enabled))
 usage_new=[receipts[p]['usage'] for p in artifact_paths if p.startswith('chunk-encoding-attempts/') and p not in set(store.read_json('verification/transcript-backfill-preparation.json')['embedding_response_artifacts'])]
 result={'verified_at_utc':datetime.now(UTC).isoformat(),'status':'independent_verification_passed','transcripts':len(sources),'chunks':len(rows),'verified_embeddings':len(rows),'week_count':len(weeks),'weekly_counts':weeks,'original_disk_files_unchanged':len(originals),'source_archive_hashes_verified':len(sources),'native_fathom_sources':sum(s['source_type']=='fathom' for s in sources),'provider_receipts_verified':len(receipts),'new_receipts':len(usage_new),'new_embedding_prompt_tokens':sum(u.get('prompt_tokens',0) for u in usage_new),'new_embedding_provider_reported_cost_usd':sum(u['cost'] for u in usage_new) if all(isinstance(u.get('cost'),(int,float)) for u in usage_new) else None,'protected_counts':{t:baseline['tables'][t]['count'] for t in ['key_moments','content_angles','content_briefs']},'protected_baseline_unchanged':True,'persistent_external_switches_disabled':True,'active_jobs':active,'new_job_stages':new_job_stages,'encoding_jobs':jobs,'schema':schema,'generation_calls':0,'operation_artifacts':report['operation_artifacts']}
store.write_json('verification/transcript-backfill-independent-verification.json',result,overwrite=True)
print(json.dumps(result,default=str),flush=True)
