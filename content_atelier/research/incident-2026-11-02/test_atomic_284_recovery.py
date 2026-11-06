"""Focused loopback-only test of the exact production transaction/restoration helper; no Railway calls."""
import copy
import json
from contextlib import contextmanager
from unittest.mock import patch

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from backend_pipeline import database, settings_store
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.store import JsonStore
import execute_284_remote as remote
from railway_284_controller import payload,OUT
from test_reduced_selection_local import temporary_database,import_rows,digest


def main():
    snap=json.loads((OUT/'production-snapshot.json').read_text(encoding='utf-8'))
    remote.CONFIG=payload('apply')
    inspection=json.loads(sorted(OUT.glob('production-284-inspect-*.json'))[-1].read_text())['inspection']
    checks=[]
    with temporary_database() as url:
        real_connect=psycopg.connect
        def local_connect(conninfo='',*args,**kwargs):
            from psycopg.conninfo import conninfo_to_dict
            d=conninfo_to_dict(conninfo)
            assert d.get('host')=='127.0.0.1' and d.get('dbname')=='atelier_reduced_run_test'
            return real_connect(conninfo,*args,**kwargs)
        @contextmanager
        def local_connection(*,write=False):
            with psycopg.connect(url,row_factory=dict_row) as conn:
                yield conn
        with patch.object(psycopg,'connect',local_connect),patch.object(database,'register_vector',lambda conn:None),patch.object(settings_store,'env_files',lambda:[]):
            with local_connection() as conn:
                for table,records in [('pipeline_runs',[snap['run']]),('pipeline_jobs',snap['jobs']),('transcripts',snap['transcripts']),
                                      ('key_moments',snap['moments']),('pipeline_events',snap['events'])]:
                    import_rows(conn,table,records)
                conn.execute('CREATE TABLE settings (key text,value jsonb)')
                conn.execute('INSERT INTO settings VALUES (%s,%s)',('schedule.weekly_cycle.2026-11-01',Jsonb(snap['schedule']['value'])))
                conn.execute('CREATE TABLE content_angles (run_id text)')
                conn.execute('CREATE TABLE llm_runs (details jsonb)')
                for _ in snap['model_calls']: conn.execute('INSERT INTO llm_runs VALUES (%s)',(Jsonb({'run_id':remote.RUN}),))
            storage=StorageSettings(database_url=url,artifact_root=OUT/'atomic-rehearsal-artifacts',synthetic=True)
            def state():
                with local_connection() as conn:
                    return {t:conn.execute(f'SELECT * FROM {t} ORDER BY 1').fetchall() for t in ('pipeline_runs','pipeline_jobs','pipeline_events','key_moments','transcripts')}
            original=state()
            def refusal(*args,**kwargs): raise RuntimeError('Injected local retry failure')
            try:
                with patch.object(remote.ContentRepository,'retry',refusal):
                    with local_connection(write=True) as conn: remote.atomic_apply(conn,storage,inspection)
            except RuntimeError as error:
                assert str(error)=='Injected local retry failure'
            else: raise AssertionError('Expected rollback test failure')
            assert digest(original)==digest(state())
            checks.append('A failure in the existing retry method rolls back the extraction edit and audit event atomically')
            with local_connection(write=True) as conn:
                receipt=remote.atomic_apply(conn,storage,inspection)
                assert receipt['retry_requested']
            applied=state()
            jobs={j['job_id']:j for j in applied['pipeline_jobs']}
            assert jobs[remote.GEN]['status']=='queued' and jobs[remote.EXT]['result_refs']['moment_ids']==remote.CONFIG['selected_ids']
            assert digest(original['key_moments'])==digest(applied['key_moments']) and digest(original['transcripts'])==digest(applied['transcripts'])
            checks.append('Exact atomic helper applies only 284 IDs and queues only the approved generation job')
            try:
                with local_connection(write=True) as conn: remote.atomic_apply(conn,storage,inspection)
            except AssertionError: pass
            else: raise AssertionError('A second application must be refused')
            assert digest(applied)==digest(state())
            checks.append('A duplicate application cannot issue a second retry')
            with patch.object(remote,'connection',local_connection),patch.object(remote.StorageSettings,'from_env',lambda **kwargs:storage),patch.object(remote,'store',lambda:JsonStore(storage.artifact_root)):
                assert remote.restore_if_terminal()['reason']=='attempt_not_terminal'
                assert digest(applied)==digest(state())
                checks.append('Restoration refuses to alter extraction while generation is queued/running')
                with local_connection(write=True) as conn:
                    conn.execute("UPDATE pipeline_jobs SET status='completed',attempt_count=attempt_count+1,result_refs=%s WHERE job_id=%s",
                                 (Jsonb({'moment_ids':remote.CONFIG['selected_ids'],'consent_dropped':[]}),remote.GEN))
                restored=remote.restore_if_terminal()
                assert restored['restored'] and restored['coverage']['verified']==291 and restored['coverage']['sent']==284 and len(restored['coverage']['not_sent'])==7
                final=state(); final_jobs={j['job_id']:j for j in final['pipeline_jobs']}
                assert final_jobs[remote.EXT]['result_refs']==remote.CONFIG['original_result_refs']
                assert final_jobs[remote.GEN]['result_refs']['moment_ids']==remote.CONFIG['selected_ids']
                assert final_jobs[remote.GEN]['result_refs']['scene_coverage']==restored['coverage']
                checks.append('Terminal restoration recovers original result and reconciles saved coverage without changing actual sent IDs')
                assert remote.restore_if_terminal()['reason']=='already_restored'
                assert digest(final)==digest(state())
                checks.append('Duplicate restoration is idempotent')
    report={'passed':True,'checks':checks,'production_connections':0,'model_calls':0,'temporary_database_removed':True}
    (OUT/'atomic-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
