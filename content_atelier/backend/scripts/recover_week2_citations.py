"""Validate and cache the saved Call 2 response without any outbound request.

The raw response, request and failed artifact stay immutable. Recovery requires an
exact request fingerprint, unchanged source/history/moments and lossless citation
adaptation through validated current evidence. It queues no job by itself.
"""
import json
from datetime import UTC, datetime
import httpx
from backend_pipeline.config import Settings
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.models import Moment, StageArtifact
from backend_pipeline.storage_sources import reconstruct
from backend_pipeline.prompts import sql_angle_prompt
from backend_pipeline.llm import chat_body
from backend_pipeline.comparison import check_history, validate_moments
from backend_pipeline.citation_adapter import adapt_angle_response, VERSION
from backend_pipeline.store import JsonStore, canonical_hash
from backend_pipeline.angle_workflow import WORKFLOW
from backend_pipeline.contracts import AngleResponse


def forbidden(*args,**kwargs):
    raise AssertionError('Citation recovery must never make an outbound request')


def main():
    httpx.HTTPTransport.handle_request=forbidden
    httpx.AsyncHTTPTransport.handle_async_request=forbidden
    storage=StorageSettings.from_env();models=Settings.from_env();worker=SQLWorker(storage,models)
    store=JsonStore(storage.artifact_root)
    latest=store.read_json('verification/week2-live-latest.json');run_id=latest['run_id'];root=latest['artifact_directory']
    with worker.repo.connection() as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        run=conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(run_id,)).fetchone()
        assert run['week_id']=='week_2026-06-08' and run['input_refs']['workflow']==WORKFLOW
        job=conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation'",(run_id,)).fetchone()
        assert job['status']=='failed' and job['error_summary']=='Every source assertion must start with a referenced [moment_id]'
    frozen_run,records=worker.inputs(job)
    transcripts,_,refs=reconstruct(records)
    with worker.repo.connection() as conn:
        context=worker.stage_output(conn,run_id,'history_context')
        check_history(conn,context);validate_moments(conn,context,run['week_id'])
        rows={m['moment_id']:m for m in conn.execute('SELECT * FROM key_moments WHERE moment_id=ANY(%s)',(context['moment_ids'],))}
    spans={s.span_id:s for t in transcripts for s in t.spans}
    moments=[]
    for mid in context['moment_ids']:
        row=rows[mid];evidence=row['evidence_refs']
        anchors=[r['passage_id'] for r in evidence if 'anchor' in r['roles']]
        nearby=[r['passage_id'] for r in evidence if 'context' in r['roles']]
        moments.append(Moment(moment_id=mid,source_ids=sorted({spans[x].source_id for x in anchors}),
                              anchor_span_ids=anchors,context_span_ids=nearby,**row['moment_body']))
    p,manifest=worker.adapter({**run,'input_refs':{**run['input_refs'],'mode':'replay'}},transcripts,refs)
    manifest.prompt_profile=WORKFLOW
    system,user=sql_angle_prompt(p._moment_packet(moments,transcripts),context['historical_packet'])
    ih=canonical_hash({'system':system,'user':user,'moment_ids':context['moment_ids'],
                       'workflow':WORKFLOW,'sources':run['input_refs']['transcripts']})
    failed=StageArtifact.model_validate(store.read_json(root+'/angle_generation.failed.json'))
    attempt=f'service_calls/{failed.request_fingerprint}/attempts/{failed.artifact_id}'
    received=store.read_json(attempt+'/output.received.json')
    exact_request=store.read_json(attempt+'/request.json')['request']
    expected_request=chat_body(model=models.openrouter_angles_model,system=system,user=user,
                              schema=AngleResponse.model_json_schema(),max_tokens=models.llm_completion_tokens,
                              reasoning_effort=models.llm_reasoning_effort,response_format=models.llm_response_format)
    assert exact_request==expected_request and failed.input_hashes==[ih]
    fp=p._request_key(run=manifest,stage='angle_generation',endpoint=models.openrouter_base_url.rstrip('/'),request=exact_request,input_hash=ih)
    assert fp==failed.request_fingerprint
    raw_content=failed.raw_response['choices'][0]['message']['content']
    assert received==(json.loads(raw_content) if isinstance(raw_content,str) else raw_content)
    interpreted,changes=adapt_angle_response(received,moments)
    angles=p._parse_angles(interpreted,run_id,moments)
    assert len(angles)==6 and len(changes)==18
    recovered=failed.model_copy(update={'artifact_id':'artifact_citations_'+canonical_hash([failed.artifact_id,VERSION])[:16],
        'status':'validated','error':None,'request':exact_request,'output':received,'output_hash':canonical_hash(received),
        'metadata':{**failed.metadata,'recovered_from_artifact_id':failed.artifact_id,'recovery_kind':'lossless_current_evidence_citation_adapter',
                    'citation_adapter':VERSION,'citation_adaptations':changes,'recovered_at':datetime.now(UTC).isoformat(),
                    'new_provider_dispatches':0,'raw_output_hash':canonical_hash(received)}})
    # Fully parse with the original response time before making it reusable.
    p._parse_angles(interpreted,run_id,moments,artifact=recovered)
    destination=f'{root}/citation-recovery/{recovered.artifact_id}.json'
    store.cache_artifact(recovered,destination)
    store.write_json(root+'/citation-recovery/report.json',{'run_id':run_id,'status':'validated_for_cached_retry',
        'original_artifact_id':failed.artifact_id,'recovered_artifact_id':recovered.artifact_id,
        'request_fingerprint':fp,'citation_adapter':VERSION,'adapted_assertions':len(changes),
        'valid_angles':len(angles),'provider_dispatches':0,'original_response_unchanged':True,
        'claims_scores_qualifiers_unchanged':True,'changes':changes})
    print(json.dumps({'run_id':run_id,'valid_angles':6,'adapted_assertions':18,'new_provider_calls':0,
                      'recovered_artifact_id':recovered.artifact_id,'status':'validated_for_cached_retry'}))


if __name__=='__main__':main()
