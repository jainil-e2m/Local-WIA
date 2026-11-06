"""Focused local PostgreSQL rehearsal. Hardcoded loopback-only server; no production mutation capability.

Minimal copied read-path tables, not a full migrated platform. Vector type registration is omitted because no
vector operation is exercised. The actual SQLWorker reader executes; model/verification boundary is intercepted.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'reduced-run-preview'
sys.path.insert(0,str(ROOT/'backend'))
from backend_pipeline import database, settings_store
from backend_pipeline.config import Settings
from backend_pipeline.cycle.window import scene_coverage
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_config import StorageSettings

PG=Path('C:/Program Files/PostgreSQL/17/bin')

def run_pg(*args):
    # On Windows pg_ctl's child can inherit captured pipes after pg_ctl exits.
    # A file avoids waiting forever for a running server to close those pipes.
    logfile=OUT/'local-pg-utility.log'
    with logfile.open('ab') as output:
        p=subprocess.run([str(PG/args[0]), *map(str,args[1:])],stdout=output,stderr=subprocess.STDOUT,
                         timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:
        raise RuntimeError('Local PostgreSQL utility failed: '+logfile.read_text(encoding='utf-8',errors='replace')[-2000:])
    return p

@contextmanager
def temporary_database():
    base=(OUT/('.local-pg-'+uuid4().hex)).resolve()
    assert base.parent==OUT.resolve()
    data=base/'data'
    base.mkdir()
    started=False
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    try:
        run_pg('initdb.exe','-D',data,'-U','atelier_preview','-A','trust','--encoding=UTF8','--no-locale')
        run_pg('pg_ctl.exe','-D',data,'-l',base/'postgres.log','-w','-t','25','-o',f'-h 127.0.0.1 -p {port} -F','start')
        started=True
        url=f'postgresql://atelier_preview@127.0.0.1:{port}/atelier_reduced_run_test'
        with psycopg.connect(f'postgresql://atelier_preview@127.0.0.1:{port}/postgres',autocommit=True) as conn:
            conn.execute('CREATE DATABASE atelier_reduced_run_test')
        yield url
    finally:
        stopped=not started
        if started:
            run_pg('pg_ctl.exe','-D',data,'-m','fast','-w','-t','20','stop')
            stopped=True
        if stopped:
            target=base.resolve()
            assert target.parent==OUT.resolve() and target.name.startswith('.local-pg-')
            shutil.rmtree(target)
        assert not base.exists(), 'Temporary local database files were not removed'


def import_rows(conn, table, records):
    keys=list(dict.fromkeys(k for r in records for k in r))
    types={}
    for k in keys:
        value=next((r[k] for r in records if r.get(k) is not None),None)
        types[k]=('jsonb' if isinstance(value,(list,dict)) else 'boolean' if isinstance(value,bool)
                  else 'integer' if isinstance(value,int) else 'timestamptz' if k.endswith('_at') else 'text')
    conn.execute(sql.SQL('CREATE TABLE {} ({})').format(sql.Identifier(table),sql.SQL(',').join(
        sql.SQL('{} {}').format(sql.Identifier(k),sql.SQL(t+(' DEFAULT now()' if k=='created_at' else ''))) for k,t in types.items())))
    for row in records:
        conn.execute(sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(sql.Identifier(table),
            sql.SQL(',').join(map(sql.Identifier,row)),sql.SQL(',').join(sql.Placeholder() for _ in row)),
            [Jsonb(v) if types[k]=='jsonb' else v for k,v in row.items()])


def digest(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()


def main():
    snap=json.loads((OUT/'production-snapshot.json').read_text(encoding='utf-8'))
    alternative=sys.argv[1:]==['--alternative']
    if sys.argv[1:] and not alternative:
        raise SystemExit('Use --alternative to rehearse the current 284-scene proposal')
    proposal_name='angle-preserving-alternative.json' if alternative else 'selection-proposal.json'
    proposal=json.loads((OUT/proposal_name).read_text(encoding='utf-8'))
    if not alternative and proposal.get('editorial_review_status','').startswith('WITHDRAWN'):
        raise RuntimeError('The original proposal was withdrawn; use --alternative')
    original=next(j for j in snap['jobs'] if j['stage']=='moment_extraction')
    generation=next(j for j in snap['jobs'] if j['stage']=='angle_generation')
    original_refs=original['result_refs']
    selected=proposal['selected_ids']
    expected_selected=len(selected)
    expected_omitted=len(original_refs['moment_ids'])-expected_selected
    if alternative:
        assert expected_selected==284 and expected_omitted==7
    checks=[]
    with temporary_database() as url:
        real_connect=psycopg.connect
        def local_only(conninfo='', *args, **kwargs):
            from psycopg.conninfo import conninfo_to_dict
            info=conninfo_to_dict(conninfo)
            assert info.get('host')=='127.0.0.1' and info.get('dbname')=='atelier_reduced_run_test', 'Refusing non-test connection'
            return real_connect(conninfo,*args,**kwargs)
        with patch.object(psycopg,'connect',local_only), patch.object(database,'register_vector',lambda conn:None), \
             patch.object(settings_store,'env_files',lambda:[]):
            with psycopg.connect(url,row_factory=dict_row) as conn:
                for table,records in [('pipeline_runs',[snap['run']]),('pipeline_jobs',snap['jobs']),('transcripts',snap['transcripts']),
                                      ('key_moments',snap['moments']),('pipeline_events',snap['events'])]:
                    import_rows(conn,table,records)
            storage=StorageSettings(database_url=url,artifact_root=OUT/'local-test-artifacts',synthetic=True)
            frozen=snap['run']['input_refs']['models']
            models=Settings(angle_prompt_profile=snap['run']['input_refs']['angle_prompt_profile'],
                            openrouter_moments_model=frozen['moment_extraction'],
                            openrouter_angle_generation_model=frozen['angle_generation'],
                            openrouter_verification_model=frozen['card_verification'])
            worker=SQLWorker(storage,models)
            captured=[]
            # No provider, context assembly, output persistence, matching or embedding is invoked.
            worker.adapter=lambda run,transcripts,refs:(None,SimpleNamespace())
            def capture(job,run,p,manifest,run_dir,moments,transcripts,ids,**kwargs):
                spans={span.span_id:span for t in transcripts for span in t.spans}
                from backend_pipeline.pipeline import Pipeline
                for moment in moments:
                    Pipeline._check_moment_structure(moment,spans)
                captured.append({'ids':list(ids),'moments':len(moments),'transcripts':len(transcripts)})
            worker.cards=capture
            def db_state():
                with worker.repo.connection() as conn:
                    return {t:conn.execute(sql.SQL('SELECT * FROM {} ORDER BY 1').format(sql.Identifier(t))).fetchall()
                            for t in ('pipeline_jobs','pipeline_runs','key_moments','transcripts')}
            initial=db_state()
            worker.execute(generation)
            assert captured[-1]['ids']==original_refs['moment_ids'] and captured[-1]['moments']==291
            checks.append('Unmodified worker reads all 291 original verified IDs before any local edit')
            with worker.repo.connection() as conn:
                # Exact-original guard and failed-stage predicate, using only this isolated local copy.
                reduced_refs=copy.deepcopy(original_refs)
                reduced_refs['moment_ids']=selected
                n=conn.execute('UPDATE pipeline_jobs SET result_refs=%s WHERE job_id=%s AND status=%s AND result_refs=%s '
                               'AND EXISTS (SELECT 1 FROM pipeline_jobs WHERE job_id=%s AND status=%s)',
                               (Jsonb(reduced_refs),original['job_id'],'completed',Jsonb(original_refs),generation['job_id'],'failed')).rowcount
                assert n==1
            worker.execute(generation)
            assert captured[-1]['ids']==selected and captured[-1]['moments']==expected_selected and captured[-1]['transcripts']==16
            checks.append(f'Same worker reads exactly {expected_selected} selected scenes, with valid unchanged evidence ranges and all 16 transcripts')
            altered=db_state()
            assert digest(initial['key_moments'])==digest(altered['key_moments']) and len(altered['key_moments'])==297
            assert digest(initial['transcripts'])==digest(altered['transcripts'])
            checks.append('All 297 stored moment rows and all original transcript rows remain byte-equivalent as JSON')
            with worker.repo.connection() as conn:
                assert conn.execute('UPDATE pipeline_jobs SET result_refs=%s WHERE job_id=%s AND result_refs=%s',
                                    (Jsonb(reduced_refs),original['job_id'],Jsonb(original_refs))).rowcount==0
            checks.append('A stale expected-original conditional update is rejected with zero affected rows')
            worker.repo.retry(generation['job_id'],'local-preview-only@example.invalid')
            retried=db_state()
            by_job={j['job_id']:j for j in retried['pipeline_jobs']}
            assert by_job[generation['job_id']]['status']=='queued'
            assert by_job[original['job_id']]['status']=='completed'
            assert by_job[generation['job_id']]['error_summary'] is None
            for before in initial['pipeline_jobs']:
                if before['job_id'] not in (original['job_id'],generation['job_id']):
                    assert before==by_job[before['job_id']]
            checks.append('Existing repository retry queues only generation; extraction and downstream job rows are not restarted')
            with worker.repo.connection() as conn:
                # Simulate output metadata only, not a model result or job execution.
                misleading=scene_coverage(conn,snap['run'],sent=selected,dropped=[])
                assert misleading['verified']==expected_selected and misleading['state']=='complete'
                conn.execute('UPDATE pipeline_jobs SET result_refs=%s WHERE job_id=%s AND result_refs=%s',
                             (Jsonb(original_refs),original['job_id'],Jsonb(reduced_refs)))
                honest=scene_coverage(conn,snap['run'],sent=selected,dropped=[])
                assert honest['verified']==291 and honest['sent']==expected_selected and len(honest['not_sent'])==expected_omitted and honest['state']=='incomplete'
                restored=worker.stage_output(conn,snap['run']['run_id'],'moment_extraction')
                assert restored==original_refs
            checks.append(f'Restoration recovers exact original extraction result and truthfully reports 291 verified, {expected_selected} sent, {expected_omitted} not sent')
            worker.execute(generation)
            assert captured[-1]['ids']==original_refs['moment_ids']
            checks.append('After restoration the unchanged worker returns to its normal full-291-scene behavior')
            final=db_state()
            assert digest(final['key_moments'])==digest(initial['key_moments']) and digest(final['transcripts'])==digest(initial['transcripts'])
    report={'passed':True,'checks':checks,'selection_file':proposal_name,'selected':expected_selected,'omitted':expected_omitted,
            'production_connections':0,'paid_model_calls':0,'production_changes':False,
            'local_postgresql_stopped':True,'temporary_database_files_deleted':True,
            'scope':'Focused real PostgreSQL read/retry/coverage rehearsal using minimal copied tables. Vector registration and model/context/output boundaries are excluded; this is not a full pipeline end-to-end test.'}
    result_name='local-validation-284.json' if alternative else 'local-validation.json'
    (OUT/result_name).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
