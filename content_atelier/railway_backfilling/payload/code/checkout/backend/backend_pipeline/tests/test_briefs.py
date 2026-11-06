"""Offline approved-angle research, writing and Gate 2 against isolated PostgreSQL."""
import copy
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from test_sql_storage import setup,NonemptyProvider,drain,URL
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.chunk_encoding import queue as encode_chunks
from backend_pipeline import gate_one,retrieval
from backend_pipeline.briefs import gate_two
from backend_pipeline.briefs.workflow import queue
from backend_pipeline.briefs.validation import checks
from backend_pipeline.briefs.contracts import Dossier
from backend_pipeline.storage_api import router
from backend_pipeline.database import apply_brief_indexes,check

pytestmark=pytest.mark.skipif(not URL,reason='Requires exact isolated atelier_test database')

def document(d):
    a=d['angle']; evidence=d['evidence']; ids=[e['evidence_id'] for e in evidence]
    e=next(e for e in evidence if e['role']=='anchor')
    direction={'reader_job':'Understand the decision','direction':'Explain the reported observation with its limitation.',
        'outline':['Name the uncertainty','Explain the mechanism','Ask for a bounded review'],'evidence_ids':[e['evidence_id']]}
    return {'title':'A bounded follow-up review','angle_statement':a['body']['argument'],'audience':a['body']['audience'],
        'reader_decision':a['body']['reader_decision'],'reader_promise':'Understand how to review follow-up without assuming measured improvement.',
        'positioning':None,'why_now':'The admitted observation raises a useful current editorial question; meeting date is unknown.',
        'core_insight':'A reported improvement is a starting point for review, not proof of a measured result.',
        'message_spine':['Inspect the observation','Retain the limitation','Choose a bounded review'],
        'audience_pain':'Uncertainty about the next action','narrative':['Explain the observation without causal certainty.'],
        'evidence_boundaries':['Not measured; speaker identity and public-use permission remain unverified.'],
        'claims':[{'claim_id':'claim_observation','text':'An improvement in follow-up was reported.',
            'kind':'source_assertion','evidence_ids':[e['evidence_id']],'source_status':'reported',
            'qualifications':e['qualifications'],'quote':None,'public_quote':False,'numeric_facts':[]}],
        'differentiation':'Focus on the bounded review decision rather than presenting a general outcome.',
        'prior_differences':{p['angle_id']:'Develop this reader decision while retaining the unmeasured limitation.' for p in d['prior']},
        'voice':['Plain language'],'email':direction,'carousel_reader_job':'Apply a bounded review',
        'carousel':[{'number':i,'direction':'Explain a bounded review step.','evidence_ids':[e['evidence_id']]} for i in range(1,9)],
        'reels':[{**direction,'reader_job':r} for r in ('Recognize uncertainty','Understand the mechanism','Decide the next review')],
        'cta':a['cta'],'creative_direction':['Use a clear flow'],'accessibility':['Provide captions'],
        'distribution':['Use the approved editorial channels'],'evaluation_signals':['Check reader comprehension'],
        'similarity_review':'Review covers the admitted archive; legacy publication coverage is incomplete.',
        'claims_requiring_consent':[],'open_questions':[{'question_id':'distribution','text':'Which channel should lead?', 'required':True,'answer':None}],
        'sources':ids,'handoff_checklist':['Preserve source qualifications','Approve the exact brief before production']}

class BriefProvider(NonemptyProvider):
    def __init__(self): super().__init__(); self.bad_write=False; self.bad_review=False; self.gap_rounds=0; self.query_batches=0; self.review_prior_reference=False
    def json_call(self,*,stage,system,user,schema,fingerprint):
        if not stage.startswith('brief_'): return super().json_call(stage=stage,system=system,user=user,schema=schema,fingerprint=fingerprint)
        self.calls.append(stage); p=json.loads(user)
        if stage=='brief_plan':
            count=6 if p['round']==0 else min(3,p['remaining_queries'])
            out={'queries':[{'text':f'follow-up evidence round {p["round"]} aspect {i}','purpose':'support'} for i in range(count)]}
        elif stage=='brief_grade':
            out={'grades':[{'evidence_id':e['evidence_id'],'relevant':True,'role':'support','reason':'Useful exact source context'} for e in p['evidence']],
                'gaps':['Need additional counterevidence'] if p['round']<self.gap_rounds else []}
        elif stage in {'brief_write','brief_repair'}:
            out=document(p['dossier'])
            if stage=='brief_write' and self.bad_write: out['cta']={'text':'Wrong CTA'}
            if p.get('current_brief'):
                out=copy.deepcopy(p['current_brief']['document']); out['core_insight']='Revised bounded explanation'
                out['prior_differences']={p['angle_id']:'A further bounded treatment of the recorded contribution.' for p in p['dossier']['prior']}
        elif stage=='brief_review':
            out={'reviewed_claim_ids':[c['claim_id'] for c in p['document']['claims']],
                'preserves_approved_direction':True,'distinct_treatment':not self.bad_review,'findings':[]}
            if self.review_prior_reference:
                out['findings'].append({'claim_id':p['document']['claims'][0]['claim_id'],'severity':'warning',
                    'message':'Differentiate this treatment from the supplied prior argument.',
                    'evidence_ids':[p['dossier']['prior'][0]['angle_id']]})
        else: raise AssertionError(stage)
        return out,{'fake':True}
    def embed_many(self,*,texts,fingerprint):
        self.query_batches+=1
        return {'model':'text-embedding-3-small','data':[{'index':i,'embedding':self.embed(text=t,fingerprint=fingerprint)[0]} for i,t in enumerate(texts)]}

def ready(setup,**flags):
    repo,models,_=setup
    later_angles=flags.pop('later_angles',False)
    repo.settings.brief_enabled=True; repo.settings.brief_approvers=('tester',); repo.settings.brief_editors=('editor',)
    p=BriefProvider()
    for k,v in flags.items(): setattr(p,k,v)
    w=SQLWorker(repo.settings,models,provider=p)
    repo.submit('week_2026-06-01','synthetic'); drain(w)
    if later_angles:
        repo.submit('week_2026-06-08','synthetic'); drain(w)
    for week in ('week_2026-06-01','week_2026-06-08'):
        encode_chunks(repo,models,week); drain(w)
    a=next(a for a in repo.review('week_2026-06-01')['angles'] if a['content_body']['title']=='Different')
    approval=gate_one.decide(repo,a['angle_id'],a['content_hash'],'approved',{'text':'Discuss follow-up'},True,'Bounded treatment','tester')
    return repo,models,p,w,a,approval['brief_run']


def test_earlier_week_brief_includes_later_week_content_already_generated(setup):
    from datetime import timedelta
    from backend_pipeline.briefs.workflow import output
    r=ready(setup,later_angles=True);repo,models,p,w,a,run=r
    w.once(run_id=run['run_id'])
    with repo.connection() as c:
        actual=c.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(run['run_id'],)).fetchone()
        later=c.execute('SELECT angle_id FROM content_angles WHERE week_id=%s',('week_2026-06-08',)).fetchall()
        later_run=c.execute("SELECT created_at FROM pipeline_runs WHERE week_id=%s AND run_scope='weekly_angles'",('week_2026-06-08',)).fetchone()
        prepared=output(w,actual,'brief_prepare')
        assert {v['angle_id'] for v in later}<={v['angle_id'] for v in prepared['prior']}
        assert actual['input_refs']['angle']['week_id']=='week_2026-06-01'
        old=retrieval.previous(c,actual['input_refs']['angle'],[],prepared['archive'],models,True,
            as_of=later_run['created_at']-timedelta(microseconds=1))
        assert not {v['angle_id'] for v in later}&{v.angle_id for v in old}

def finish(ready_data):
    repo,models,p,w,a,run=ready_data
    drain(w,20)
    with repo.connection() as c:
        jobs=c.execute('SELECT stage,status,error_summary,result_refs FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at',(run['run_id'],)).fetchall()
        assert all(j['status']=='completed' for j in jobs),jobs
        row=c.execute('SELECT brief_id FROM content_briefs WHERE angle_id=%s ORDER BY created_at DESC LIMIT 1',(a['angle_id'],)).fetchone()
    return gate_two.get(repo,row['brief_id'],'tester')

def test_full_offline_workflow_and_gate_two(setup):
    r=ready(setup);repo,models,p,w,a,run=r; row=finish(r)
    assert p.calls[-4:]==['brief_plan','brief_grade','brief_write','brief_review']
    research=gate_two.research(repo,a['angle_id'])
    assert len(research['dossier']['queries'])==6
    assert len(research['dossier']['evidence'])==4  # both weeks; originals remain separate
    assert research['status']=='waiting_for_review'
    assert not row['can_approve'] and not row['can_consume']
    assert queue(repo,a['angle_id'],'tester','synthetic')['run_id']==run['run_id']
    assert 'unanswered' in ' '.join(row['blockers'])
    with pytest.raises(PermissionError): gate_two.decide(repo,row['brief_id'],row['content_hash'],'approved',None,'editor')
    changed=gate_two.answers(repo,row['brief_id'],row['content_hash'],{'distribution':'Email first'},'tester')
    row=gate_two.get(repo,changed['brief_id'],'tester')
    changed=gate_two.review(repo,row['brief_id'],row['content_hash'],['claim_observation'],'Checked bounded claims and prior coverage',True,'tester')
    row=gate_two.get(repo,changed['brief_id'],'tester')
    assert row['can_approve'],row['blockers']
    gate_two.decide(repo,row['brief_id'],row['content_hash'],'approved','Approved bounded production contract','tester')
    assert gate_two.get(repo,row['brief_id'],'tester')['can_consume']
    with repo.connection() as c:
        assert c.execute('SELECT count(*) n FROM content_packs').fetchone()['n']==0
        assert c.execute('SELECT count(*) n FROM calendar_entries').fetchone()['n']==0
        assert c.execute('SELECT status FROM weeks WHERE week_id=%s',('week_2026-06-01',)).fetchone()['status']=='review'
    assert len(gate_two.versions(repo,row['brief_id']))==3
    assert '## Source passages' in gate_two.markdown(row)
    from backend_pipeline.store import JsonStore
    from backend_pipeline.config import BACKEND_ROOT
    store=JsonStore(repo.settings.artifact_root)
    costs=store.read_json(f'brief-runs/{run["run_id"]}/cost_summary.json')
    assert costs['total_new_cost_usd']==0 and all(not c['real_external_dispatch'] for s in costs['stages'] for c in s['calls'])
    JsonStore(BACKEND_ROOT/'.storage-artifacts').write_json('verification/brief-synthetic-report.json',
        {'synthetic':True,'real_external_calls':0,'brief':gate_two.get(repo,row['brief_id'],'tester'),
         'research':research,'versions':gate_two.versions(repo,row['brief_id']),'costs':costs},overwrite=True)

def test_one_repair_and_failure_is_reviewable_not_angle_rejection(setup):
    r=ready(setup,bad_write=True,bad_review=True); row=finish(r)
    assert r[2].calls.count('brief_repair')==1 and r[2].calls.count('brief_review')==2
    assert row['content_body']['document']['cta']=={'text':'Discuss follow-up'}
    assert any('differentiation' in b for b in row['blockers'])
    with r[0].connection() as c: assert c.execute('SELECT approval_status FROM content_angles WHERE angle_id=%s',(r[4]['angle_id'],)).fetchone()['approval_status']=='approved'


def test_review_can_reference_supplied_prior_but_current_claims_cannot(setup):
    r=ready(setup,review_prior_reference=True);row=finish(r)
    prior_id=row['prior_content_context'][0]['angle_id']
    assert any(f.get('evidence_ids')==[prior_id] for f in row['content_body']['review']['findings'])
    assert not row['content_body']['review']['repair_used']
    changed=copy.deepcopy(row['content_body']['document'])
    changed['claims'][0]['evidence_ids']=[prior_id]
    assert any(f['message']=='Claim references unknown evidence' for f in checks(changed,gate_two.dossier(row)))


def test_review_rejects_unknown_prior_or_claim_ids(setup):
    from backend_pipeline.briefs.contracts import SupportReview,BriefDocument
    from backend_pipeline.briefs.validation import review_findings
    r=ready(setup);row=finish(r);doc=BriefDocument.model_validate(row['content_body']['document'])
    evidence={e['evidence_id'] for e in row['selected_evidence']}
    prior={p['angle_id'] for p in row['prior_content_context']}
    data={'reviewed_claim_ids':[c.claim_id for c in doc.claims],'preserves_approved_direction':True,
        'distinct_treatment':True,'findings':[{'claim_id':doc.claims[0].claim_id,'severity':'warning',
            'message':'Unknown reference must fail operational validation.','evidence_ids':['angle_not_supplied']}]}
    with pytest.raises(ValueError,match='unknown claim/evidence'):
        review_findings(SupportReview.model_validate(data),doc,evidence,prior)
    data['findings'][0].update(claim_id='claim_not_supplied',evidence_ids=[next(iter(prior))])
    with pytest.raises(ValueError,match='unknown claim/evidence'):
        review_findings(SupportReview.model_validate(data),doc,evidence,prior)

def test_missing_vectors_and_changed_sources_fail_closed(setup):
    r=ready(setup);repo,models,p,w,a,run=r
    with repo.connection() as c: c.execute('UPDATE transcript_chunks SET embedding=NULL WHERE chunk_id=(SELECT chunk_id FROM transcript_chunks LIMIT 1)')
    drain(w)
    with repo.connection() as c: assert c.execute('SELECT status FROM pipeline_runs WHERE run_id=%s',(run['run_id'],)).fetchone()['status']=='failed'
    assert not any(s.startswith('brief_') for s in p.calls)

def test_edits_locked_revision_and_stale_approval(setup):
    r=ready(setup);repo,models,p,w,a,run=r; row=finish(r)
    changed=gate_two.edit(repo,row['brief_id'],row['content_hash'],{'title':'An editorially locked title'},'editor')
    with pytest.raises(ValueError,match='superseded'): gate_two.edit(repo,row['brief_id'],row['content_hash'],{'title':'Stale'},'editor')
    row=gate_two.get(repo,changed['brief_id'],'tester')
    assert any('scoped grounding' in b for b in row['blockers'])
    revised=gate_two.revise(repo,row['brief_id'],row['content_hash'],'Develop the core_insight; preserve title','editor','synthetic')
    drain(w,20)
    with repo.connection() as c:
        latest=c.execute('SELECT * FROM content_briefs WHERE supersedes_id=%s',(row['brief_id'],)).fetchone()
        assert latest, c.execute('SELECT stage,status,error_summary FROM pipeline_jobs WHERE run_id=%s',(revised['run_id'],)).fetchall()
    assert latest['content_body']['document']['title']=='An editorially locked title'
    with repo.connection() as c:
        c.execute("UPDATE transcripts SET use_restrictions=%s WHERE transcript_id=%s",(Jsonb({'withdrawn':True}),latest['selected_evidence'][0]['transcript_id']))
    assert any('restricted' in s for s in gate_two.get(repo,latest['brief_id'],'tester')['blockers'])

def test_gaps_batched_queries_and_budgets(setup):
    r=ready(setup,gap_rounds=2); row=finish(r)
    d=gate_two.research(r[0],r[4]['angle_id'])['dossier']
    assert len(d['queries'])==12 and r[2].calls.count('brief_plan')==3
    with r[0].connection() as c:
        assert c.execute("SELECT count(*) n FROM pipeline_events WHERE run_id=%s AND event_type='brief_query_dispatch'",(r[5]['run_id'],)).fetchone()['n']==3

def test_claim_quote_qualification_permission_and_numeric_checks(setup):
    r=ready(setup);row=finish(r);d=gate_two.dossier(row);doc=copy.deepcopy(row['content_body']['document'])
    claim=doc['claims'][0];claim['qualifications']=[];claim['text']='Follow-up improved by 50 percent';claim['quote']='Invented quotation';claim['public_quote']=True
    doc['claims_requiring_consent']=['Unresolved public quotation permission']
    reasons=' '.join(f['message'] for f in checks(doc,d) if f['severity']=='blocking')
    assert all(s in reasons for s in ('qualifications','Numerical','Quotation','clearance','consent requirements'))
    evidence=next(e for e in d.evidence if e.role=='anchor');evidence.public_use=True
    from backend_pipeline.briefs.inputs import verify_evidence
    with r[0].connection() as c:
        with pytest.raises(ValueError,match='public-use'): verify_evidence(c,[evidence])

def test_api_capabilities_exports_and_cache_only_search(setup):
    r=ready(setup);row=finish(r);app=FastAPI();app.include_router(router(r[0].settings));client=TestClient(app)
    h={'authorization':'Bearer test-secret','x-atelier-actor':'tester'}
    assert client.get('/storage/briefs').status_code==401
    result=client.get('/storage/briefs?limit=1',headers=h).json();assert result['total']==1
    assert client.get(f'/storage/briefs/{row["brief_id"]}/export.md',headers=h).status_code==200
    assert client.post('/storage/search/transcripts',headers=h,json={'text':'A query that has never been encoded'}).json()['status']=='awaiting_query_encoding'
    assert client.patch(f'/storage/briefs/{row["brief_id"]}',headers={**h,'x-atelier-actor':'unknown'},json={'expected_hash':row['content_hash'],'changes':{'title':'Changed'}}).status_code==403
    assert client.get('/storage/briefs?limit=101',headers=h).status_code==422

def test_explicit_index_migration_is_idempotent(setup):
    assert apply_brief_indexes(URL)['status'] in {'applied','already_applied'}
    assert apply_brief_indexes(URL)['status']=='already_applied'
    with setup[0].connection() as c: assert check(c)['tables'] in {13,14}

def test_response_to_sql_failure_recovers_without_new_inference(setup,monkeypatch):
    r=ready(setup);repo,models,p,w,a,run=r
    original=repo.finish;fail=[True]
    def finish_once(conn,job,*args,**kwargs):
        if job['stage']=='brief_validation' and fail[0]: fail[0]=False;raise RuntimeError('Simulated SQL failure after validated response')
        return original(conn,job,*args,**kwargs)
    monkeypatch.setattr(repo,'finish',finish_once)
    # Worker owns a separate repository object; patch the class for this guarded test.
    monkeypatch.setattr(w.repo,'finish',finish_once)
    drain(w,20)
    with repo.connection() as c:
        assert c.execute('SELECT count(*) n FROM content_briefs').fetchone()['n']==0
        job=c.execute("SELECT job_id,status FROM pipeline_jobs WHERE run_id=%s AND stage='brief_validation'",(run['run_id'],)).fetchone()
        assert job['status']=='failed'
    before=list(p.calls);repo.retry(job['job_id'],'tester');row=finish(r)
    assert before==p.calls and row['approval_status']=='pending'

@pytest.mark.parametrize('finish_reason',['stop','length'])
def test_raw_received_before_exception_is_recovered(setup,monkeypatch,finish_reason):
    r=ready(setup);repo,models,p,w,a,run=r
    original=p.json_call;failed=[False]
    def received(**kwargs):
        output,meta=original(**kwargs)
        if kwargs['stage']=='brief_write' and not failed[0]:
            failed[0]=True
            from backend_pipeline.store import JsonStore
            store=JsonStore(repo.settings.artifact_root)
            request=next(store.path('brief-attempts').glob(f'*/1/{kwargs["fingerprint"]}/request.json'))
            request.with_name('response.raw.json').write_text(json.dumps({'choices':[{'finish_reason':finish_reason,'message':{'content':json.dumps(output)}}]}),encoding='utf-8')
            raise RuntimeError('Interrupted after received raw body')
        return output,meta
    monkeypatch.setattr(p,'json_call',received);drain(w,20)
    with repo.connection() as c: job=c.execute("SELECT job_id,status FROM pipeline_jobs WHERE run_id=%s AND stage='brief_writing'",(run['run_id'],)).fetchone()
    assert job['status']=='failed'
    with pytest.raises(PermissionError): repo.retry(job['job_id'],'unauthorized')
    repo.retry(job['job_id'],'tester')
    if finish_reason=='length':
        drain(w,20)
        with repo.connection() as c:
            failure=c.execute('SELECT status,error_summary FROM pipeline_jobs WHERE job_id=%s',(job['job_id'],)).fetchone()
            assert failure['status']=='failed' and 'incomplete or refused' in failure['error_summary']
            assert c.execute('SELECT count(*) n FROM content_briefs').fetchone()['n']==0
        assert p.calls.count('brief_write')==1
        return
    row=finish(r)
    assert p.calls.count('brief_write')==1 and not row['content_body']['review']['repair_used']

def test_query_cache_corruption_and_request_preflight_fail_visibly(setup):
    r=ready(setup);repo,models,p,w,a,run=r
    w.once();repo.settings.brief_max_characters=10;w.storage.brief_max_characters=10
    w.once()
    with repo.connection() as c:
        job=c.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s AND stage='brief_research'",(run['run_id'],)).fetchone()
    assert job['status']=='failed' and 'preflight' in job['error_summary']
    assert not any(s.startswith('brief_') for s in p.calls)

def test_unreviewed_source_date_prose_and_unknown_evidence_remain_blocking(setup):
    r=ready(setup);row=finish(r);d=gate_two.dossier(row);doc=copy.deepcopy(row['content_body']['document'])
    doc['narrative']=['Measured improvement of 99 percent'];doc['email']['evidence_ids']=['unknown']
    messages=' '.join(f['message'] for f in checks(doc,d) if f['severity']=='blocking')
    assert 'Numerical prose' in messages and 'references' in messages

from backend_pipeline.tests.test_comparison_workflow import comparison_setup,ComparisonProvider

def test_authoritative_policy_preserves_fallback_family_and_multiple_approvals(comparison_setup):
    repo,models,_=comparison_setup;p=ComparisonProvider();w=SQLWorker(repo.settings,models,provider=p)
    run=repo.submit('week_2026-06-08','synthetic',workflow='historical_comparison_v1');drain(w,15)
    candidates={a['content_body']['title']:a for a in repo.review('week_2026-06-08')['angles']}
    fallback=candidates['A3'];other=candidates['A6']
    with pytest.raises(ValueError,match='threshold'): gate_one.decide(repo,fallback['angle_id'],fallback['content_hash'],'approved',{'text':'Discuss'},True,'Distinct','tester')
    repo.settings.angle_approval_cutoff=.9;repo.settings.brief_approvers=('tester',)
    gate_one.decide(repo,fallback['angle_id'],fallback['content_hash'],'approved',{'text':'Discuss'},True,'Distinct fallback treatment','tester')
    from backend_pipeline.briefs.inputs import angle_packet
    with repo.connection() as c:
        packet=angle_packet(c,fallback['angle_id'])
        assert packet['policy']['refinement_children']==[candidates['R3']['angle_id']]
    gate_one.decide(repo,other['angle_id'],other['content_hash'],'approved',{'text':'Discuss'},True,'Distinct reader decision','tester')
    with pytest.raises(ValueError,match='not selected'):
        child=candidates['R3'];gate_one.decide(repo,child['angle_id'],child['content_hash'],'approved',{'text':'Discuss'},True,'Distinct','tester')

@pytest.mark.parametrize('bad_date',[False,True])
def test_optional_web_framing_uses_only_reviewed_public_packet(setup,bad_date):
    r=ready(setup);repo,models,p,w,a,run=r
    # The queued synthetic brand snapshot is the reviewed input; no real source is sent.
    repo.settings.brief_web_enabled=True;w.storage.brief_web_enabled=True
    with repo.connection() as c:
        refs=c.execute('SELECT input_refs FROM pipeline_runs WHERE run_id=%s',(run['run_id'],)).fetchone()['input_refs']
        refs['brand']['documents']['public_research']={'topic':'Follow-up best practices','questions':['What boundaries should claims preserve?'],'allowed_domains':['example.invalid']}
        from backend_pipeline.store import canonical_hash
        refs['brand']['hash']=canonical_hash(refs['brand']['documents'])
        c.execute('UPDATE pipeline_runs SET input_refs=%s WHERE run_id=%s',(Jsonb(refs),run['run_id']))
    class Web:
        def __init__(self): self.calls=[]
        def research(self,**kwargs):
            self.calls.append(kwargs)
            findings=[{'url':'https://example.invalid/article','title':'A public framing example','published_at':'2026-10-01T00:00:00+00:00','excerpt':'A public explanation of bounded claims.'}]
            if bad_date: findings.append({**findings[0],'url':'https://example.invalid/old','published_at':'2020-01-01T00:00:00+00:00'})
            return {'findings':findings}
    web=Web();w.web_provider=web;row=finish(r)
    assert len(web.calls)==1 and 'Alice' not in json.dumps(web.calls)
    if bad_date:
        assert not any(e['role']=='external_framing' for e in row['selected_evidence'])
        assert row['research_gaps']['coverage']['external']=='unavailable'
        return
    assert any(e['role']=='external_framing' for e in row['selected_evidence'])
    d=gate_two.dossier(row);doc=copy.deepcopy(row['content_body']['document']);doc['claims'][0]['evidence_ids']=[e.evidence_id for e in d.evidence if e.role=='external_framing']
    assert any('External framing' in f['message'] for f in checks(doc,d))

def test_frozen_models_and_prior_context_cannot_change_on_retry(setup):
    r=ready(setup);repo,models,p,w,a,run=r
    w.once();models.embedding_model='incompatible-model';w.once()
    with repo.connection() as c:
        job=c.execute("SELECT stage,status,error_summary FROM pipeline_jobs WHERE run_id=%s AND stage='brief_research'",(run['run_id'],)).fetchone()
    assert job['status']=='failed' and 'contract changed' in job['error_summary']
    assert not any(s.startswith('brief_') for s in p.calls)

def test_permission_clearance_and_current_approval_binding(setup):
    r=ready(setup);repo=r[0];row=finish(r)
    e=next(e for e in row['selected_evidence'] if e['role']=='anchor')
    changed=gate_two.clearance(repo,row['brief_id'],row['content_hash'],e['evidence_id'],'Signed permission reference','Verified speaker reference','tester')
    row=gate_two.get(repo,changed['brief_id'],'tester');assert row['content_body']['review']['clearances'][e['evidence_id']]['actor']=='tester'
    from psycopg.errors import CheckViolation
    with pytest.raises(CheckViolation):
        with repo.connection() as c:
            c.execute("UPDATE content_briefs SET approval_status='approved',approved_hash='wrong' WHERE brief_id=%s",(row['brief_id'],))
    invalid={**row,'approval_status':'approved','approved_hash':'wrong'}
    with repo.connection() as c:
        assert any('actor/time' in s for s in gate_two.blockers(c,invalid))
    assert not gate_two.get(repo,row['brief_id'],'tester')['can_consume']

def test_web_replay_cannot_dispatch_optional_provider(setup):
    r=ready(setup);repo,models,p,w,a,run=r;row=finish(r)
    from backend_pipeline.briefs.external import enrich
    d=gate_two.dossier(row);d.brand['documents']={'public_research':{'topic':'Public topic','questions':[]}}
    w.storage.brief_web_enabled=True
    class Never:
        def research(self,**kwargs): raise AssertionError('Replay must not dispatch external research')
    w.web_provider=Never()
    with repo.connection() as c:
        actual=c.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(run['run_id'],)).fetchone()
        actual['input_refs']['mode']='replay'
    result=enrich(w,{'job_id':'unused','attempt_count':1},actual,d)
    assert result.coverage['external']=='unavailable' and 'replay never' in ' '.join(result.gaps)
