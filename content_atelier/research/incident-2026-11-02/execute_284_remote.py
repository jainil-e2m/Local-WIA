"""One explicitly approved recovery. Executed via Railway-resolved SSH, never installed as application code.

CONFIG is injected by the local controller. Inspect/status are read-only. Apply is exactly-once and transactional.
A separate temporary watchdog restores the original extraction result when this one generation attempt ends.
"""
from __future__ import annotations
import copy
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, os.getcwd())
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from backend_pipeline.artifacts import backend_for
from backend_pipeline.config import Settings
from backend_pipeline.repository import ContentRepository
from backend_pipeline.sql_pipeline import SQLWorker, consented
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.store import JsonStore, canonical_hash

PROJECT='3409333b-1844-456c-93f9-f572ba92eb92'
ENVIRONMENT='28239d73-fe52-4d23-bf80-94a8064c5eb5'
COMMIT='9b50c9d047a2d1005b19fbd80fea5f9e2476a32b'
RUN='run_113a8c5a0b384cfba61e6fc7b59367ee'
GEN='job_6f34d2bb0a994017bb711a1e752194ca'
EXT='job_a5e66b8c652945d2a856deafc65d17c5'
RECOVERY='approved284-20261102-0c5b22851f7f'
BASE=f'experiments/sql/runs/{RUN}/recovery/{RECOVERY}'
ACTOR='ai@weddingindustryads.com: user-approved single 284-scene recovery'


def now(): return datetime.now(UTC).isoformat()

def normalize(value): return json.loads(json.dumps(value,default=str))

def assert_environment():
    assert os.environ['RAILWAY_PROJECT_ID']==PROJECT
    assert os.environ['RAILWAY_ENVIRONMENT_ID']==ENVIRONMENT
    assert os.environ['RAILWAY_SERVICE_NAME']=='scheduler'
    assert os.environ['RAILWAY_GIT_COMMIT_SHA']==COMMIT
    assert CONFIG['run_id']==RUN and CONFIG['generation_job_id']==GEN and CONFIG['extraction_job_id']==EXT
    assert canonical_hash(CONFIG['selected_ids'])=='0c5b22851f7f8f0f868d73443bb5b0d6a3775309103c862b51130bbc2195bb2d'

@contextmanager
def connection(*, write=False):
    options='-c statement_timeout=20000 -c lock_timeout=5000'
    if not write: options+=' -c default_transaction_read_only=on'
    with psycopg.connect(os.environ['ATELIER_DATABASE_URL'],row_factory=dict_row,connect_timeout=15,options=options) as conn:
        yield conn

def store(): return JsonStore(backend_for('/unused-recovery-root'))

def event_exists(conn,kind):
    return conn.execute("SELECT event_id,details FROM pipeline_events WHERE run_id=%s AND event_type=%s AND details->>'recovery_id'=%s ORDER BY created_at DESC LIMIT 1",(RUN,kind,RECOVERY)).fetchone()

def moment_signature(row):
    return canonical_hash({k:row.get(k) for k in CONFIG['moment_hash_fields']})

def validate_baseline(conn,*,locked=False):
    run=conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s'+(' FOR UPDATE' if locked else ''),(RUN,)).fetchone()
    assert run and run['status']=='failed' and run['run_scope']=='weekly_angles', 'Run is no longer the expected failed weekly cycle'
    assert canonical_hash(run['input_refs'])==CONFIG['input_refs_sha256'], 'Frozen input refs changed'
    jobs=conn.execute('SELECT * FROM pipeline_jobs WHERE run_id=%s ORDER BY job_id'+(' FOR UPDATE' if locked else ''),(RUN,)).fetchall()
    byid={j['job_id']:j for j in jobs}
    assert set(byid)==set(CONFIG['job_statuses']), 'Run job set changed'
    assert all(byid[k]['status']==v for k,v in CONFIG['job_statuses'].items()), 'A job status changed'
    ext,gen=byid[EXT],byid[GEN]
    assert ext['status']=='completed' and gen['status']=='failed'
    assert gen['attempt_count']==CONFIG['generation_attempt_count'] and not gen['lease_token']
    assert gen['error_summary']==CONFIG['generation_error'], 'Original generation error changed'
    assert canonical_hash(ext['result_refs'])==CONFIG['original_extraction_result_sha256'], 'Extraction result changed'
    assert ext['result_refs']==CONFIG['original_result_refs']
    assert not event_exists(conn,'one_run_selection_applied'), 'This recovery has already been applied; no second retry allowed'
    assert not conn.execute('SELECT 1 FROM content_angles WHERE run_id=%s LIMIT 1',(RUN,)).fetchone(), 'Cards already exist'
    calls=conn.execute("SELECT count(*) AS n FROM llm_runs WHERE details->>'run_id'=%s",(RUN,)).fetchone()['n']
    assert calls==CONFIG['baseline_model_call_count'], 'Model-call history changed'
    claim=conn.execute('SELECT value FROM settings WHERE key=%s',('schedule.weekly_cycle.2026-11-01',)).fetchone()
    assert claim and claim['value']==CONFIG['schedule_value'] and claim['value']['state']=='done', 'Schedule claim changed'
    ids=ext['result_refs']['moment_ids']; selected=CONFIG['selected_ids']
    assert len(ids)==291 and len(set(selected))==len(selected)==284
    assert [mid for mid in ids if mid not in set(CONFIG['omitted_ids'])]==selected
    rows={r['moment_id']:r for r in conn.execute('SELECT * FROM key_moments WHERE moment_id=ANY(%s)',(ids,))}
    assert len(rows)==291
    for mid in ids:
        assert rows[mid]['quote_verified'] and moment_signature(rows[mid])==CONFIG['moment_hashes'][mid], 'Moment or consent changed'
    assert all(rows[mid]['consent_status']=='internal_only' for mid in CONFIG['omitted_ids'])
    bodies,dropped=consented(rows,ids)
    assert not dropped
    public={mid for mid,b in bodies.items() if b['sensitivity']!='internal_only'}
    assert len(public)==169 and public<=set(selected)
    assert len({rows[mid]['document_id'] for mid in selected})==16
    return run,ext,gen,rows


def current_preflight(conn):
    """Real current context assembly and request builder, without a provider or any business writes."""
    from backend_pipeline.angle_profiles import order_packet, strategist_angle_prompt, card_schema
    from backend_pipeline.cycle.seeds import prompt_seeds
    from backend_pipeline.models import Moment
    from backend_pipeline.pipeline import Pipeline
    from backend_pipeline.storage_sources import reconstruct
    from backend_pipeline.llm.request import stage_body,stage_fingerprint
    from backend_pipeline.token_budget import preflight
    run,ext,gen,rows=validate_baseline(conn)
    storage=StorageSettings.from_env(conn=conn)
    models=Settings.from_env(conn=conn)
    assert storage.generation_enabled and models.llm_input_limits_enabled and models.llm_payload_format=='compact_weekly'
    worker=SQLWorker(storage,models)
    worker.repo.connection=connection
    assert worker.frozen_profile(run)==CONFIG['profile']
    actual_run,records=worker.inputs(gen)
    assert actual_run['input_refs']==run['input_refs']
    transcripts,_,_=reconstruct(records)
    spans={s.span_id:s for t in transcripts for s in t.spans}
    selected=CONFIG['selected_ids']
    bodies,dropped=consented(rows,selected)
    assert not dropped
    moments=[]
    for mid in selected:
        evidence=rows[mid]['evidence_refs']
        anchors=[r['passage_id'] for r in evidence if 'anchor' in r['roles']]
        context=[r['passage_id'] for r in evidence if 'context' in r['roles']]
        moments.append(Moment(moment_id=mid,source_ids=sorted({spans[a].source_id for a in anchors}),
                              anchor_span_ids=anchors,context_span_ids=context,**bodies[mid]))
    p=Pipeline(models)
    p.context_connection=connection
    p.context_date=run['created_at'].date()
    kb=p.knowledge_base('live')
    contract=p.angle_input_refs(kb)
    assert worker.stable_contract(contract)==worker.stable_contract(run['input_refs']['angle_contract']), 'Frozen knowledge contract changed'
    team,_=worker.evidence_classes(selected,run['input_refs'].get('identities'))
    system,user=strategist_angle_prompt(order_packet(p._moment_packet(moments,transcripts)),kb,models.angle_prompt_profile,
        prompt_seeds(run['input_refs'].get('seeds') or []),run['input_refs'].get('strategy_brief'),
        team_practice=team,identities=run['input_refs'].get('identities'))
    if getattr(kb,'situational',None): user+='\n\n'+kb.situational
    schema=card_schema(models.angle_prompt_profile)
    request=stage_body(models,'angle_generation',system,user,schema)
    assert request['model']=='openai/gpt-6.1-sol' and request['max_tokens']==32000
    report=preflight(request,store())
    assert report['fits'], 'Current request still exceeds limits; no retry performed'
    ih=canonical_hash({'system':system,'user':user,'moment_ids':selected,'knowledge_base':kb.refs()})
    fp=stage_fingerprint(mode='live',stage='angle_generation',endpoint=models.openrouter_base_url.rstrip('/'),request=request,input_hash=ih)
    assert fp!=CONFIG['original_request_fingerprint']
    return {'at':now(),'preflight':report,'request_sha256':canonical_hash(request),'request_fingerprint':fp,
            'selected':len(selected),'public_consideration_preserved':169,'documents':16,
            'original_result_sha256':canonical_hash(ext['result_refs'])},storage,ext,gen


def atomic_apply(conn,storage,details):
    """Call the existing retry method on this already-locked transaction; no separate connection or partial commit."""
    run,ext,gen,_=validate_baseline(conn,locked=True)
    reduced=copy.deepcopy(ext['result_refs']); reduced['moment_ids']=CONFIG['selected_ids']
    repo=ContentRepository(storage)
    @contextmanager
    def borrowed_transaction(): yield conn
    repo.connection=borrowed_transaction
    changed=conn.execute("UPDATE pipeline_jobs SET result_refs=%s,updated_at=now() WHERE job_id=%s AND status='completed' AND result_refs=%s",
                         (Jsonb(reduced),EXT,Jsonb(ext['result_refs']))).rowcount
    assert changed==1
    repo.event(conn,RUN,'one_run_selection_applied','User-approved recovery: 284 scenes selected; 7 internal-only scenes intentionally omitted',
               details={'recovery_id':RECOVERY,'actor':ACTOR,'selected_ids':CONFIG['selected_ids'],
                        'omitted_ids':CONFIG['omitted_ids'],'original_count':291,'sent_count':284,
                        'original_result_sha256':CONFIG['original_extraction_result_sha256'],'backup':BASE+'/before.json',
                        'preflight':details['preflight'],'expected_request_fingerprint':details['request_fingerprint']})
    repo.retry(GEN,ACTOR)
    return {'at':now(),'recovery_id':RECOVERY,'changed':True,'retry_requested':True,'generation_job_id':GEN,
            'selected':284,'omitted':7,'schedule_reset':False,'preflight':details['preflight'],
            'expected_request_fingerprint':details['request_fingerprint']}


def restore_if_terminal():
    from backend_pipeline.cycle.window import scene_coverage
    with connection(write=True) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(RECOVERY,))
        applied=event_exists(conn,'one_run_selection_applied')
        if not applied: return {'restored':False,'reason':'not_applied'}
        if event_exists(conn,'one_run_selection_restored'): return {'restored':True,'reason':'already_restored'}
        gen=conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s FOR UPDATE',(GEN,)).fetchone()
        if gen['status'] not in ('completed','failed','waiting','cancelled') or gen['attempt_count']<=CONFIG['generation_attempt_count']:
            return {'restored':False,'reason':'attempt_not_terminal','generation_status':gen['status']}
        ext=conn.execute('SELECT * FROM pipeline_jobs WHERE job_id=%s FOR UPDATE',(EXT,)).fetchone()
        original=CONFIG['original_result_refs']
        reduced=copy.deepcopy(original); reduced['moment_ids']=CONFIG['selected_ids']
        assert ext['status']=='completed' and ext['result_refs']==reduced, 'Refusing to restore over unexpected extraction changes'
        if gen['status']=='completed':
            assert gen['result_refs']['moment_ids']==CONFIG['selected_ids'], 'Completed generation used unexpected IDs'
        changed=conn.execute('UPDATE pipeline_jobs SET result_refs=%s,updated_at=now() WHERE job_id=%s AND result_refs=%s',
                             (Jsonb(original),EXT,Jsonb(reduced))).rowcount
        assert changed==1
        run=conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(RUN,)).fetchone()
        coverage=None
        if gen['status']=='completed':
            coverage=scene_coverage(conn,run,sent=CONFIG['selected_ids'],dropped=gen['result_refs'].get('consent_dropped',[]))
            assert coverage['verified']==291 and coverage['sent']==284 and len(coverage['not_sent'])==7
            result={**gen['result_refs'],'scene_coverage':coverage}
            conn.execute('UPDATE pipeline_jobs SET result_refs=%s,updated_at=now() WHERE job_id=%s AND result_refs=%s',
                         (Jsonb(result),GEN,Jsonb(gen['result_refs'])))
        storage=StorageSettings.from_env(conn=conn)
        repo=ContentRepository(storage)
        receipt={'at':now(),'recovery_id':RECOVERY,'restored':True,'generation_status':gen['status'],
                 'actual_sent_count':284 if gen['status']=='completed' else None,'original_verified_count':291,
                 'original_result_sha256':canonical_hash(original),'omitted_ids':CONFIG['omitted_ids'],'coverage':coverage}
        repo.event(conn,RUN,'one_run_selection_restored','Original 291-scene extraction result restored after the approved generation attempt',details=receipt)
    store().write_json(BASE+'/restored.json',receipt)
    return receipt


def status():
    with connection() as conn:
        run=conn.execute("SELECT run_id,status,current_message,error_summary,input_refs->'review_document' AS review_document FROM pipeline_runs WHERE run_id=%s",(RUN,)).fetchone()
        jobs=conn.execute('SELECT job_id,stage,status,current_message,error_summary,attempt_count,heartbeat_at,started_at,finished_at,result_refs FROM pipeline_jobs WHERE run_id=%s ORDER BY stage',(RUN,)).fetchall()
        ext=next(j for j in jobs if j['job_id']==EXT); gen=next(j for j in jobs if j['job_id']==GEN)
        calls=conn.execute("SELECT stage,model,status,input_tokens,output_tokens,cost_usd,created_at,error,details FROM llm_runs "
                           "WHERE details->>'run_id'=%s OR request_fingerprint=(SELECT details->>'expected_request_fingerprint' "
                           "FROM pipeline_events WHERE run_id=%s AND event_type='one_run_selection_applied' AND details->>'recovery_id'=%s "
                           "ORDER BY created_at DESC LIMIT 1) ORDER BY created_at",(RUN,RUN,RECOVERY)).fetchall()
        cards=conn.execute("SELECT angle_id,content_body->>'title' AS title,content_body->'card' AS card FROM content_angles WHERE run_id=%s ORDER BY created_at,angle_id",(RUN,)).fetchall()
        applied=event_exists(conn,'one_run_selection_applied'); restored=event_exists(conn,'one_run_selection_restored')
        schedule=conn.execute('SELECT value FROM settings WHERE key=%s',('schedule.weekly_cycle.2026-11-01',)).fetchone()
        data={'at':now(),'run':run,'jobs':[{k:v for k,v in j.items() if k!='result_refs'} for j in jobs],
              'extraction_count':len(ext['result_refs']['moment_ids']),'generation_result':gen['result_refs'],
              'calls':calls,'cards':cards,'applied':bool(applied),'restored':bool(restored),'schedule':schedule['value']}
    if applied:
        import re
        fp=applied['details']['expected_request_fingerprint']
        artifacts=store()
        prefix=f'service_calls/{fp}/attempts'
        attempts=[]
        for name in artifacts.names(prefix):
            base=f'{prefix}/{name}'
            item={'attempt':name}
            if artifacts.exists(base+'/request.json'):
                req=artifacts.read_json(base+'/request.json')['request']
                item.update(model=req['model'],request_sha256=canonical_hash(req),
                            scene_count=sum(len(re.findall(r'^## Scene S\d+ ',m['content'],re.M)) for m in req['messages']))
            if artifacts.exists(base+'/preflight.json'):
                item['preflight']=artifacts.read_json(base+'/preflight.json')
            item['raw_response_saved']=artifacts.exists(base+'/response.raw.json')
            attempts.append(item)
        data['generation_attempt_artifacts']=attempts
        data['watchdog_error']=artifacts.read_json(BASE+'/watchdog-error.json') if artifacts.exists(BASE+'/watchdog-error.json') else None
    return normalize(data)


def watchdog():
    try:
        for _ in range(360):
            result=restore_if_terminal()
            if result.get('restored'):
                store().write_json(BASE+'/watchdog-finished.json',{'at':now(),'result':result})
                return
            time.sleep(5)
        store().write_json(BASE+'/watchdog-timeout.json',{'at':now(),'note':'No additional retry or unsafe restoration performed; inspect this one job.'})
    except Exception as error:
        store().write_json(BASE+'/watchdog-error.json',{'at':now(),'error_type':type(error).__name__,'message':str(error)[:1000]})
        raise
    finally:
        own=Path(__file__).resolve()
        if own.parent==Path('/tmp') and own.name==RECOVERY+'.py': own.unlink(missing_ok=True)


def main():
    assert_environment()
    action=CONFIG['action']
    if action=='messages':
        # Strictly read-only inspection of the exact generated card mentioned by the user.
        angle_id='angle_c0663bcb1c2a8aff60bf8e44'
        with connection() as conn:
            read_only=conn.execute('SHOW transaction_read_only').fetchone()
            row=conn.execute("SELECT angle_id,run_id,approval_status,updated_at,content_hash,"
                "content_body->>'title' AS title,content_body#>'{card,public_stance}' AS public_stance,"
                "content_body#>'{card,verify_before_publishing}' AS verify_before_publishing,"
                "content_body#>'{card,evidence_points}' AS evidence_points,"
                "content_body#>'{card,moment_ids}' AS moment_ids,"
                "content_body->'stance_confirmation' AS stance_confirmation,content_body "
                "FROM content_angles WHERE angle_id=%s AND run_id=%s",(angle_id,RUN)).fetchone()
            assert row is not None, 'The referenced card was not found in the expected run'
            body=row.pop('content_body')
            phrases=["Repeated, helpful follow-up gives an interested couple more opportunities to decide and is part of serving that couple.",
                     "Review permission to use the photographer's anonymised words.",
                     "Confirm Whitney's public stance on helpful repetition before developing the piece.",
                     "This card takes a public stance:","Whitney confirms a public stance before the card is developed.",
                     "Note (optional; e.g.","Confirmed with Whitney on the call","Confirm this public stance", 
                     "What was said on the call","Verify before publishing"]
            serialized=json.dumps(body,ensure_ascii=False)
            matches={phrase:phrase in serialized for phrase in phrases}
            events=conn.execute("SELECT event_type,message,details,created_at FROM pipeline_events WHERE run_id=%s "
                "AND event_type='gate_one_stance_confirmed' AND details->>'angle_id'=%s ORDER BY created_at DESC",(RUN,angle_id)).fetchall()
            evidence=[]
            mids=row['moment_ids'] or []
            if mids:
                evidence=conn.execute('SELECT moment_id,quote_verified,evidence_refs FROM key_moments WHERE moment_id=ANY(%s)',(mids,)).fetchall()
        print(json.dumps({'database_verification':{'at':now(),'transaction':read_only,'project_id':PROJECT,'environment_id':ENVIRONMENT,
            'card':normalize(row),'literal_presence_in_card_json':matches,'stance_confirmation_events':normalize(events),
            'source_evidence_records':normalize(evidence),'database_changes':False}},default=str),flush=True)
    elif action=='inspect':
        with connection() as conn:
            info,_,_,_=current_preflight(conn)
        print(json.dumps({'inspection':info,'status':status()},default=str),flush=True)
    elif action=='apply':
        assert CONFIG.get('user_authorized_execution') is True
        with connection() as conn:
            info,storage,ext,gen=current_preflight(conn)
        journal=store()
        assert not journal.exists(BASE+'/applied.json'), 'Recovery receipt already exists; no second retry'
        before={'at':now(),'recovery_id':RECOVERY,'original_extraction_job':normalize(ext),'original_generation_job':normalize(gen),
                'selected_ids':CONFIG['selected_ids'],'omitted_ids':CONFIG['omitted_ids'],'inspection':info}
        journal.write_json(BASE+'/before.json',before)
        assert journal.read_json(BASE+'/before.json')['original_extraction_job']['result_refs']==CONFIG['original_result_refs']
        # Independent terminal-state restoration continues even if the operator's SSH connection is interrupted.
        helper=Path('/tmp')/(RECOVERY+'.py')
        assert not helper.exists(), 'A recovery watchdog already exists'
        watchdog_config={**CONFIG,'action':'watchdog'}
        helper.write_text('CONFIG='+repr(watchdog_config)+'\nexec(compile('+repr(REMOTE_SOURCE)+",'<approved284-watchdog>','exec'))\n",encoding='utf-8')
        helper.chmod(0o600)
        with (Path('/tmp')/(RECOVERY+'.log')).open('ab') as log:
            proc=subprocess.Popen([sys.executable,str(helper)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                                  start_new_session=True,cwd=os.getcwd())
        time.sleep(0.3)
        assert proc.poll() is None, 'Restoration watchdog did not start'
        with connection(write=True) as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(RECOVERY,))
            receipt=atomic_apply(conn,storage,info)
        journal.write_json(BASE+'/applied.json',{**receipt,'watchdog_pid':proc.pid})
        print(json.dumps({'application':receipt,'watchdog_pid':proc.pid,'status':status()},default=str),flush=True)
    elif action=='status':
        restored=restore_if_terminal()
        print(json.dumps({'restoration':restored,'status':status()},default=str),flush=True)
    elif action=='finalize':
        import base64
        import hashlib
        data=status()
        assert data['run']['status']=='waiting_for_review' and data['restored']
        assert len(data['cards'])==5 and all(j['status']=='completed' for j in data['jobs'])
        with connection() as conn:
            ext=conn.execute('SELECT result_refs FROM pipeline_jobs WHERE job_id=%s',(EXT,)).fetchone()['result_refs']
            gen=conn.execute('SELECT result_refs FROM pipeline_jobs WHERE job_id=%s',(GEN,)).fetchone()['result_refs']
            assert ext==CONFIG['original_result_refs']
            assert gen['moment_ids']==CONFIG['selected_ids']
            coverage=gen['scene_coverage']
            assert coverage['verified']==291 and coverage['sent']==284 and set(coverage['not_sent'])==set(CONFIG['omitted_ids'])
            moments=conn.execute('SELECT * FROM key_moments WHERE moment_id=ANY(%s)',(ext['moment_ids'],)).fetchall()
            assert len(moments)==291 and all(moment_signature(m)==CONFIG['moment_hashes'][m['moment_id']] for m in moments)
            run=conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(RUN,)).fetchone()
            expected={**run['input_refs']}; expected.pop('review_document',None)
            assert canonical_hash(expected)==CONFIG['input_refs_sha256'], 'Unexpected run input mutation'
            # Same SQL reader checks the source revision/view hashes without making any model call.
            storage=StorageSettings.from_env(conn=conn); models=Settings.from_env(conn=conn)
            worker=SQLWorker(storage,models); worker.repo.connection=connection
            worker.inputs({'run_id':RUN})
            assert data['schedule']==CONFIG['schedule_value']
            applied_count=conn.execute("SELECT count(*) AS n FROM pipeline_events WHERE run_id=%s AND event_type='one_run_selection_applied' AND details->>'recovery_id'=%s",(RUN,RECOVERY)).fetchone()['n']
            retry_count=conn.execute("SELECT count(*) AS n FROM pipeline_events WHERE run_id=%s AND event_type='retry_requested' AND details->>'actor'=%s",(RUN,ACTOR)).fetchone()['n']
            assert applied_count==retry_count==1
        artifacts=store()
        documents=[]
        for kind in ('markdown','docx'):
            key=data['run']['review_document'][kind]
            raw=artifacts.read_bytes(key)
            assert raw and (kind!='docx' or raw[:2]==b'PK')
            documents.append({'kind':kind,'key':key,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                              'base64':base64.b64encode(raw).decode()})
        assert artifacts.exists(BASE+'/watchdog-finished.json')
        assert not (Path('/tmp')/(RECOVERY+'.py')).exists()
        log=Path('/tmp')/(RECOVERY+'.log')
        if log.exists():
            assert log.parent==Path('/tmp') and log.name==RECOVERY+'.log'
            assert log.stat().st_size==0, 'Nonempty watchdog log retained for inspection'
            log.unlink()
        final={'at':now(),'original_extraction_restored':True,'all_verified_moment_records_unchanged':True,
               'frozen_source_views_unchanged':True,'run_inputs_only_added_review_document':True,'schedule_unchanged':True,
               'exactly_one_recovery_retry':True,'generation_sent_approved_284_ids':True,
               'coverage':coverage,'temporary_watchdog_removed':True,
               'review_documents_verified':[{k:v for k,v in d.items() if k!='base64'} for d in documents]}
        artifacts.write_json(BASE+'/final-integrity.json',final)
        print(json.dumps({'integrity':final,'documents':documents,'status':data},default=str),flush=True)
    elif action=='watchdog': watchdog()
    else: raise RuntimeError('Unsupported recovery action')


if __name__=='__main__':
    main()
