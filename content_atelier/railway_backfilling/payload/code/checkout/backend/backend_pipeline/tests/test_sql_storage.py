"""Real PostgreSQL/pgvector mechanics, synthetic semantics, zero external requests."""
from datetime import date, datetime, UTC, timedelta
import json
import re
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.types.json import Jsonb
from backend_pipeline.config import Settings
from backend_pipeline.storage_config import StorageSettings, encoding_contract
from backend_pipeline.repository import ContentRepository
from backend_pipeline.database import check, initialize, TABLES
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline import gate_one
from backend_pipeline.matching import risk, match, vector_valid
from backend_pipeline.storage_sources import capture, chunks, reconstruct
from backend_pipeline.store import canonical_hash
from backend_pipeline.tests.strategic_fixtures import strategic_output

URL = os.getenv('ATELIER_TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL,reason='Set isolated ATELIER_TEST_DATABASE_URL to run PostgreSQL integration tests')


@pytest.fixture
def setup(tmp_path):
    s = StorageSettings(database_url=URL,artifact_root=tmp_path/'artifacts',synthetic=True,api_secret='test-secret')
    repo = ContentRepository(s)
    with repo.connection() as c:
        if c.info.dbname!='atelier_test':
            raise RuntimeError('Tests refuse any database except atelier_test')
        check(c)
        c.execute(sql.SQL('TRUNCATE {} CASCADE').format(sql.SQL(',').join(map(sql.Identifier,sorted(TABLES)))))
    models=Settings(data_root=tmp_path/'legacy',llm_payload_format='compact_weekly')
    for i,d in [(1,date(2026,6,1)),(2,date(2026,6,8))]:
        folder=tmp_path/f'week{i}';folder.mkdir()
        (folder/'meeting.vtt').write_text('WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\nAlice: We improved the follow-up.\n\n2\n00:00:04.000 --> 00:00:09.000\nAlice: It was an observation, not a measured result.\n',encoding='utf-8')
        repo.admit(folder,d,i)
    return repo,models,tmp_path


class NonemptyProvider:
    def __init__(self): self.calls=[]; self.embeddings=[]
    def json_call(self,*,stage,system,user,schema,fingerprint):
        self.calls.append(stage)
        if stage=='moment_extraction':
            return strategic_output({'moments':[{'local_key':'one','anchor_span_ids':['m1.t0001'],
                'context_first_span_id':'m1.t0001','context_last_span_id':'m1.t0002',
                'quote':'We improved the follow-up.','context_summary':'Reported follow-up improvement with an explicit limitation.',
                'moment_type':'observation','proposition':'Follow-up quality matters','audience_relevance':'Owners reviewing inquiries',
                'qualifications':['Not measured'],'claim_status':'reported','sensitivity':'unknown','strength':4.,'reasons':['Exact source quote']}],
                'processed_meetings':[{'meeting_ref':'m1','first_span_id':'m1.t0001','last_span_id':'m1.t0002','span_count':2}],
                'coverage_notes':[]}, schema), {'fake':True}
        mid=re.search(r'"moment_id": "(moment_[a-f0-9]+)"',user).group(1)
        drafts=[]
        for label in ('Repeated','Different','Repeated variation'):
            drafts.append({'local_key':label,'title':label,'argument':label+' follow-up decision','audience':'Wedding business owners',
                'tension':'Uncertain next action','take':'Review the evidence','mechanism':label+' mechanism',
                'reader_decision':label+' decision','moment_ids':[mid],'source_assertions':[f'[{mid}] An improvement was reported.'],
                'inference':None,'qualifiers':['Not measured'],'risks':['Unverified public use'],
                'quality':{'grounding':5.,'source_relevance':5.,'audience_fit':5.,'specificity':5.,'editorial_usefulness':5.,'reasons':['Synthetic quality fixture']}})
        return strategic_output({'angles':drafts,'processed_moment_ids':[mid],'coverage_notes':[]}, schema),{'fake':True}
    def embed(self,*,text,fingerprint):
        self.embeddings.append(text)
        v=[0.]*1536;v[1 if 'Argument: Different' in text else 0]=1.
        return v,{'fake':True}


def drain(worker,limit=8):
    for _ in range(limit):
        if not worker.once(): break


def test_two_week_pipeline_exact_matching_and_current_batch(setup):
    repo,models,_=setup; p=NonemptyProvider(); w=SQLWorker(repo.settings,models,provider=p)
    first=repo.submit('week_2026-06-01','synthetic');drain(w)
    one=repo.review('week_2026-06-01')
    assert len(one['angles'])==3 and len([j for j in one['jobs'] if j['run_id']==first['run_id']])==4
    assert len([j for j in one['jobs'] if j['stage'] in {'source_admission','transcript_chunk_preparation'}])==2
    assert all(a['matching_result']['history_count']==0 for a in one['angles'])
    second=repo.submit('week_2026-06-08','synthetic');drain(w)
    two=repo.review('week_2026-06-08')
    assert all(a['matching_result']['history_count']==3 for a in two['angles'])
    assert all(a['selection_status']=='suppressed' for a in two['angles'])
    repeated=next(a for a in two['angles'] if a['content_body']['title']=='Repeated')
    assert repeated['matching_result']['history'][0]['cosine']==pytest.approx(1.)
    assert repeated['matching_result']['current_batch_flags']
    assert len(p.calls)==4
    assert len(p.embeddings)==3  # Same semantic inputs reuse cached vectors in Week 2.
    for a in two['angles']:
        evidence=repo.moment_context(a['moment_ids'][0])
        assert any(evidence['moment']['moment_body']['quote'] in p['text'] for p in evidence['passages'])
    with repo.connection() as c:
        assert c.execute('SELECT count(*) n FROM content_briefs').fetchone()['n']==0
        assert c.execute('SELECT count(*) n FROM content_packs').fetchone()['n']==0


def test_disabled_encoding_never_means_zero_risk(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic')
    w.once();w.once()
    # Provider disconnected after generation: a separately configured worker can use cache only.
    w.provider=None;w.once()
    review=repo.review('week_2026-06-01')
    assert any(j['status']=='waiting' for j in review['jobs'])
    assert all(a['adjusted_score'] is None and a['selection_status']=='candidate' for a in review['angles'])
    assert w.once() is None
    assert p.embeddings==[]


def test_cache_reuse_preserves_ids_age_and_relations(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic');drain(w)
    before=repo.review('week_2026-06-01')['angles']
    repo.submit('week_2026-06-01','synthetic');drain(w)
    after=repo.review('week_2026-06-01')['angles']
    assert [a['angle_id'] for a in before]==[a['angle_id'] for a in after]
    assert [a['first_generated_at'] for a in before]==[a['first_generated_at'] for a in after]
    assert len(p.calls)==2


def test_gate_edit_stale_hash_overlap_cta_and_no_brief(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic');drain(w)
    angles=repo.review('week_2026-06-01')['angles'];a=next(a for a in angles if a['content_body']['title']=='Repeated')
    with pytest.raises(ValueError,match='acknowledgement'):
        gate_one.decide(repo,a['angle_id'],a['content_hash'],'approved',{'text':'Discuss follow-up'},False,None,'team-user')
    gate_one.decide(repo,a['angle_id'],a['content_hash'],'approved',{'text':'Discuss follow-up'},True,'Different reader treatment reviewed','team-user')
    approved=next(x for x in repo.review('week_2026-06-01')['angles'] if x['angle_id']==a['angle_id'])
    with pytest.raises(ValueError,match='refresh'):
        gate_one.edit(repo,a['angle_id'],a['content_hash'],{'core_perspective':'Changed'},'team-user')
    replacement=gate_one.edit(repo,a['angle_id'],approved['content_hash'],{'core_perspective':'Distinct revised argument'},'team-user')
    edited=next(x for x in repo.review('week_2026-06-01')['angles'] if x['angle_id']==replacement['angle_id'])
    assert edited['first_generated_at']==a['first_generated_at']
    assert edited['matching_result'] is None and edited['base_score'] is None
    with repo.connection() as c:
        assert c.execute('SELECT embedding FROM content_angles WHERE angle_id=%s',(edited['angle_id'],)).fetchone()['embedding'] is None
        assert c.execute('SELECT count(*) n FROM content_briefs').fetchone()['n']==0


def test_lease_recovery_requires_explicit_retry(setup):
    repo,models,_=setup;repo.submit('week_2026-06-01','synthetic')
    j=repo.claim()
    with repo.connection() as c:
        c.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 second' WHERE job_id=%s",(j['job_id'],))
    assert not repo.heartbeat(j)
    assert repo.claim() is None
    with repo.connection() as c:
        with pytest.raises(RuntimeError,match='lease'): repo.guard(c,j)
    repo.retry(j['job_id'],'team-user');new=repo.claim()
    assert new['job_id']==j['job_id'] and new['attempt_count']==2 and new['lease_token']!=j['lease_token']


def test_api_requires_backend_secret_and_expected_hash(setup):
    repo,models,_=setup
    app=FastAPI();app.include_router(router(repo.settings));client=TestClient(app)
    assert client.get('/storage/weeks').status_code==401
    assert client.get('/storage/weeks',headers={'Authorization':'Bearer wrong','X-Atelier-Actor':'spoof'}).status_code==401
    headers={'Authorization':'Bearer test-secret','X-Atelier-Actor':'verified-team'}
    assert len(client.get('/storage/weeks',headers=headers).json())==2
    tid=repo.review('week_2026-06-08')['transcripts'][0]['transcript_id']
    assert client.get('/storage/transcripts/'+tid).status_code==401
    original=client.get('/storage/transcripts/'+tid,headers=headers).json()
    assert original['original_text'].startswith('WEBVTT') and 'follow-up' in original['original_text']
    assert client.post('/storage/weeks/week_2026-06-08/runs',headers=headers,json={'mode':'live'}).status_code==409


def test_baseline_guard_and_source_revision_admission(setup):
    repo,models,tmp=setup
    assert initialize(repo.settings.database_url)['tables'] in {13,14}
    with repo.connection() as c:
        c.execute('ALTER TABLE weeks ADD COLUMN unexpected text')
        with pytest.raises(RuntimeError,match='differs'): check(c)
        c.rollback()
    original=repo.review('week_2026-06-01')['transcripts'][0]['transcript_id']
    folder=tmp/'week1';p=folder/'meeting.vtt';p.write_text(p.read_text()+'\nVerified correction.\n')
    repo.admit(folder,date(2026,6,1),1)
    review=repo.review('week_2026-06-01')
    assert len(review['transcripts'])==2 and original in [r['transcript_id'] for r in review['transcripts']]
    repo.admit(folder,date(2026,6,1),1)
    assert len(repo.review('week_2026-06-01')['transcripts'])==2


def test_sql_packet_preserves_calibrated_header_order_and_exact_text(setup):
    from backend_pipeline.prepare import read_source,packet_for
    repo,models,tmp=setup
    _,source=read_source(tmp/'week1'/'meeting.vtt',week=1,meeting_ref='m1',first_ref=1)
    for turn in source['turns']:
        turn['ref']=f"m1.t{turn['ordinal']+1:04d}"
    with repo.connection() as c:
        records=repo.frozen_sources(c,'week_2026-06-01')
    transcripts,packet,refs=reconstruct(records)
    assert packet==packet_for([source])
    assert list(transcripts[0].source_metadata)==list(source['metadata'])


def test_math_and_invalid_vectors():
    now=datetime(2026,10,9,tzinfo=UTC)
    assert risk(.78,now,now)['risk']==0
    assert risk(1,now-timedelta(days=28),now)['risk']==pytest.approx(.5)
    with pytest.raises(ValueError): risk(1,now+timedelta(seconds=1),now)
    assert not vector_valid([0.]*1536)
    assert not vector_valid([float('nan')]+[1.]*1535)
    assert not vector_valid([1.,0.])
    assert not vector_valid([True]+[0.]*1535)
    assert not vector_valid(['0.1']*1536)
    assert not vector_valid([1e-100]*1536)  # Becomes zero in float32 storage.
    with pytest.raises(ValueError): risk(float('nan'),now,now)


def test_frozen_history_is_complete_and_missing_one_vector_blocks_all(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic');drain(w)
    repo.submit('week_2026-06-08','synthetic');drain(w)
    review=repo.review('week_2026-06-08')
    snapshot=review['angles'][0]['matching_result']['snapshot']
    prior=snapshot['history'][0]['id']
    with repo.connection() as c:
        c.execute('UPDATE content_angles SET embedding=NULL,embedding_input_hash=NULL WHERE angle_id=%s',(prior,))
        result=match(c,snapshot,encoding_contract(models,synthetic=True))
        assert result['status']=='incomplete' and prior in result['problems']
    assert all(a['adjusted_score'] is None for a in repo.review('week_2026-06-08')['angles'])


def test_post_response_database_failure_recovers_without_new_call(setup,monkeypatch):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    submission=repo.submit('week_2026-06-01','synthetic')
    save=w.repo.save_moments
    def interrupted(*args,**kwargs): raise RuntimeError('Simulated failure after validated response')
    monkeypatch.setattr(w.repo,'save_moments',interrupted)
    w.once()
    review=repo.review('week_2026-06-01')
    failed=next(j for j in review['jobs'] if j['status']=='failed')
    assert len(p.calls)==1 and not review['angles']
    monkeypatch.setattr(w.repo,'save_moments',save)
    repo.retry(failed['job_id'],'team-user');drain(w)
    assert len(p.calls)==2  # One extraction plus one generation, no extraction retry call.
    assert len(repo.review('week_2026-06-01')['angles'])==3


def test_edit_rescore_and_reassessment_only_encodes_then_matches(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic');drain(w)
    original=next(a for a in repo.review('week_2026-06-01')['angles'] if a['content_body']['title']=='Different')
    edited=gate_one.edit(repo,original['angle_id'],original['content_hash'],{'core_perspective':'A new supported perspective'},'editor')
    quality={n:5. for n in ('grounding','strategic_fit','distinctiveness','audience_resonance','source_strength')};quality['reasons']=['Reviewed against source limitations']
    gate_one.rescore(repo,edited['angle_id'],edited['content_hash'],quality,'editor')
    assessment=gate_one.reassess(repo,'week_2026-06-01','editor');drain(w)
    reviewed=repo.review('week_2026-06-01')
    assert len(p.calls)==2
    assert len([j for j in reviewed['jobs'] if j['run_id']==assessment['run_id']])==2
    new=next(a for a in reviewed['angles'] if a['angle_id']==edited['angle_id'])
    assert new['matching_result']['status']=='complete'
    assert original['angle_id'] not in [h['angle_id'] for h in new['matching_result']['history']]


def test_generation_replay_preserves_later_cta_approval(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic');drain(w)
    a=next(a for a in repo.review('week_2026-06-01')['angles'] if a['content_body']['title']=='Different')
    gate_one.decide(repo,a['angle_id'],a['content_hash'],'approved',{'text':'Discuss the evidence'},False,'Reviewed','editor')
    approved=next(x for x in repo.review('week_2026-06-01')['angles'] if x['angle_id']==a['angle_id'])
    repo.submit('week_2026-06-01','synthetic');drain(w)
    replay=next(x for x in repo.review('week_2026-06-01')['angles'] if x['angle_id']==a['angle_id'])
    assert replay['approval_status']=='approved'
    assert replay['content_hash']==approved['content_hash'] and replay['selected_cta']==approved['selected_cta']
    assert len(p.calls)==2


def test_encoding_only_baseline_finishes_scope_without_erasing_partial_coverage(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    submitted=repo.submit('week_2026-06-01','synthetic')
    w.once();w.once()
    # Simulate the imported baseline's already completed generation/admission,
    # followed by its independent encoding scope. No subsequent matching intent.
    with repo.connection() as c:
        c.execute("DELETE FROM pipeline_jobs WHERE run_id=%s AND stage='angle_matching'",(submitted['run_id'],))
        c.execute("UPDATE pipeline_runs SET run_scope='accepted_partial_baseline',has_partial_failures=true WHERE run_id=%s",(submitted['run_id'],))
    w.once()
    review=repo.review('week_2026-06-01')
    run=next(r for r in review['runs'] if r['run_id']==submitted['run_id'])
    assert run['status']=='partially_completed' and run['finished_at'] is not None
    assert review['week']['status']=='awaiting_matching'


def test_all_history_is_checked_beyond_the_five_display_rows(setup):
    from backend_pipeline.repository import insert
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    first=repo.submit('week_2026-06-01','synthetic');drain(w)
    with repo.connection() as c:
        source=c.execute("SELECT * FROM content_angles WHERE content_body->>'title'='Repeated'").fetchone()
        encoding=c.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_embedding'",(first['run_id'],)).fetchone()['result_refs']
        proof=next(v for v in encoding['vectors'] if v['angle_id']==source['angle_id'])
        extra=[]
        for i in range(6):
            key='angle_extra_'+str(i)
            insert(c,'content_angles',{**source,'angle_id':key,'first_generated_at':datetime.now(UTC)-timedelta(days=100+i)})
            extra.append(key)
            encoding['vectors'].append({**proof,'angle_id':key})
        generation=c.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation'",(first['run_id'],)).fetchone()['result_refs']
        generation['angle_ids']+=extra
        c.execute("UPDATE pipeline_jobs SET result_refs=%s WHERE run_id=%s AND stage='angle_generation'",(Jsonb(generation),first['run_id']))
        c.execute("UPDATE pipeline_jobs SET result_refs=%s WHERE run_id=%s AND stage='angle_embedding'",(Jsonb(encoding),first['run_id']))
    repo.submit('week_2026-06-08','synthetic');drain(w)
    review=repo.review('week_2026-06-08')
    repeated=next(a for a in review['angles'] if a['content_body']['title']=='Repeated')
    result=repeated['matching_result']
    assert result['history_count']==9 and len(result['history'])==9
    hidden=[h for h in result['history'][5:] if h['angle_id'] in extra]
    assert hidden  # An old low-risk comparison is beyond the initial display.
    last=hidden[-1]['angle_id']
    with repo.connection() as c:
        c.execute('UPDATE content_angles SET embedding=NULL,embedding_input_hash=NULL WHERE angle_id=%s',(last,))
        assert match(c,result['snapshot'],encoding_contract(models,synthetic=True))['status']=='incomplete'


def test_visibility_uses_the_unrounded_strict_seventy_boundary(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic');w.once();w.once()
    rows=repo.review('week_2026-06-01')['angles']
    for a,score in zip(rows,[3.5,3.500001,5.]):
        q={n:score for n in ('grounding','strategic_fit','distinctiveness','audience_resonance','source_strength')}
        gate_one.rescore(repo,a['angle_id'],a['content_hash'],{**q,'reasons':['Synthetic threshold boundary']},'editor')
    drain(w)
    reviewed={a['angle_id']:a for a in repo.review('week_2026-06-01')['angles']}
    assert reviewed[rows[0]['angle_id']]['adjusted_score']==70
    assert reviewed[rows[0]['angle_id']]['selection_status']=='suppressed'
    assert reviewed[rows[1]['angle_id']]['selection_status']=='visible'


def test_frozen_matching_rejects_later_quality_changes(setup):
    repo,models,_=setup;p=NonemptyProvider();w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic');drain(w)
    a=repo.review('week_2026-06-01')['angles'][0]
    snapshot=a['matching_result']['snapshot']
    q={n:4. for n in ('grounding','strategic_fit','distinctiveness','audience_resonance','source_strength')}
    gate_one.rescore(repo,a['angle_id'],a['content_hash'],{**q,'reasons':['Changed assessment']},'editor')
    with repo.connection() as c:
        with pytest.raises(ValueError,match='quality assessment changed'):
            match(c,snapshot,encoding_contract(models,synthetic=True))


def test_run_scoped_worker_never_claims_another_weeks_job(setup):
    repo,models,_=setup;p=NonemptyProvider();worker=SQLWorker(repo.settings,models,provider=p)
    first=repo.submit('week_2026-06-01','synthetic')
    second=repo.submit('week_2026-06-08','synthetic')
    worker.once(run_id=second['run_id'])
    one=[j for j in repo.review('week_2026-06-01')['jobs'] if j['run_id']==first['run_id']]
    two=[j for j in repo.review('week_2026-06-08')['jobs'] if j['run_id']==second['run_id']]
    assert all(j['status']=='queued' for j in one)
    assert next(j for j in two if j['stage']=='moment_extraction')['status']=='completed'
    assert p.calls==['moment_extraction']
