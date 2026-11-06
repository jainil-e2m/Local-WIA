"""Three-cutoff workflow with nonempty offline responses and actual pgvector."""
import copy
import json
import math
import os
from datetime import UTC, datetime, timedelta

import pytest
from psycopg.types.json import Jsonb
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend_pipeline.tests.test_sql_storage import setup, NonemptyProvider, drain, URL
from backend_pipeline.angle_workflow import WORKFLOW, scenarios, diagnoses
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.repository import insert
from backend_pipeline.storage_api import router
from backend_pipeline import gate_one
from backend_pipeline.store import canonical_hash
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.matching import history
from backend_pipeline.tests.strategic_fixtures import strategic_angle


class SeedProvider(NonemptyProvider):
    def json_call(self, **kwargs):
        output,meta = super().json_call(**kwargs)
        if kwargs['stage']=='angle_generation':
            output['angles'] = output['angles'][:1]
        return output,meta


class ComparisonProvider(NonemptyProvider):
    def __init__(self, *, empty=False, no_targets=False, invalid=None):
        super().__init__(); self.empty=empty; self.no_targets=no_targets; self.invalid=invalid; self.packets=[]
    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage=='moment_extraction':
            output,meta = super().json_call(stage=stage,system=system,user=user,schema=schema,fingerprint=fingerprint)
            other = copy.deepcopy(output['moments'][0])
            other.update(local_key='unused', anchor_span_ids=['m1.t0002'],context_first_span_id='m1.t0002',
                         context_last_span_id='m1.t0002',quote='It was an observation, not a measured result.',
                         proposition='Avoid treating observations as measured outcomes', sensitivity='internal_only')
            output['moments'].append(other)
            return output,meta
        self.calls.append(stage)
        packet = json.loads(user); self.packets.append((stage,packet))
        mids = [m['moment_id'] for m in packet['moments']]
        def draft(label,score=5.,mid=None):
            mid = mid or mids[0]
            return strategic_angle({'local_key':label,'title':label,'argument':label+' supported decision','audience':'Owners',
                    'tension':'A choice in follow-up','take':'Respect the evidence','mechanism':label+' mechanism',
                    'reader_decision':label+' decision','moment_ids':[mid],
                    'source_assertions':[f'[{mid}] An observation was reported.'],'inference':None,
                    'qualifiers':[],'risks':[], 'quality':{n:score for n in
                    ('grounding','source_relevance','audience_fit','specificity','editorial_usefulness')} | {'reasons':['Synthetic rubric assessment']}})
        if stage=='angle_generation':
            angles=[] if self.empty else [draft(f'A{i}',3. if i in (1,5) and not self.no_targets else 5.) for i in range(8)]
            return {'angles':angles,'internal_insights':[],'processed_moment_ids':mids,'coverage_notes':['No supported proposals'] if self.empty else []},{'fake':True}
        assert stage=='angle_refinement'
        outcomes=[]
        for target in packet['targets']:
            label = target['original']['title']; i=int(label[1:])
            outcomes.append({'original_id':target['original_id'],
                             'outcome':'no_supported_alternative' if i==4 else 'replacement',
                             'replacement':None if i==4 else draft(f'R{i}',3. if i in (3,5) else 5.,mids[1]),
                             'explanation':'Different supported reader decision' if i!=4 else 'No supported alternative in current evidence'})
        if self.invalid=='duplicate': outcomes.append(copy.deepcopy(outcomes[0]))
        if self.invalid=='historical_moment': outcomes[0]['replacement']['moment_ids']=['moment_historical']
        if self.invalid=='envelope': return {'outcomes':outcomes}, {'fake':True}
        return {'outcomes':outcomes,'processed_moment_ids':mids,'coverage_notes':['All current moments delivered']},{'fake':True}
    def embed(self, *, text, fingerprint):
        self.embeddings.append(text)
        label=text.split('Argument: ')[1].split()[0]
        mapping={'A0':(.80,1),'A1':(.10,2),'A2':(.86,3),'A3':(.88,5),'A4':(.79,4),
                 'A5':(.20,6),'A6':(.40,7),'A7':(.60,7),'R0':(.70,8),'R1':(.20,9),
                 'R2':(.86,4),'R3':(.20,10),'R5':(.10,11)}
        cosine,axis=mapping[label]
        if self.no_targets: cosine,axis=.1,int(label[1:])+1
        vector=[0.]*1536; vector[0]=cosine; vector[axis]=math.sqrt(1-cosine*cosine)
        return vector,{'fake':True}


@pytest.fixture
def comparison_setup(setup):
    repo,models,tmp=setup
    seed=SeedProvider(); worker=SQLWorker(repo.settings,models,provider=seed)
    first=repo.submit('week_2026-06-01','synthetic'); drain(worker)
    with repo.connection() as conn:
        prior=conn.execute('SELECT * FROM content_angles').fetchone()
        encoding=conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_embedding'",(first['run_id'],)).fetchone()['result_refs']
        generation=conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation'",(first['run_id'],)).fetchone()['result_refs']
        for i in range(6):
            aid=f'angle_extra_{i}'
            insert(conn,'content_angles',{**prior,'angle_id':aid,'first_generated_at':datetime.now(UTC)-timedelta(days=100+i)})
            encoding['vectors'].append({**encoding['vectors'][0],'angle_id':aid})
            generation['angle_ids'].append(aid)
        conn.execute("UPDATE pipeline_jobs SET result_refs=%s WHERE run_id=%s AND stage='angle_embedding'",(Jsonb(encoding),first['run_id']))
        conn.execute("UPDATE pipeline_jobs SET result_refs=%s WHERE run_id=%s AND stage='angle_generation'",(Jsonb(generation),first['run_id']))
    return repo,models,tmp


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_eight_proposals_six_targets_one_refinement_three_reports(comparison_setup):
    repo,models,_=comparison_setup; provider=ComparisonProvider(); worker=SQLWorker(repo.settings,models,provider=provider)
    run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW); drain(worker,12)
    result=repo.comparison_report(run['run_id'])
    assert result['completion_state']=='comparison_complete',repo.review('week_2026-06-08')['jobs']
    assert provider.calls==['moment_extraction','angle_generation','angle_refinement']
    assert len(provider.packets[1][1]['targets'])==6 and len(provider.packets[0][1]['historical_archive'])==7
    assert len(provider.packets[0][1]['evidence_by_id'])==2  # Shared context delivered once.
    report=result['report']; counts=[s['counts']['final_qualified'] for s in report['scenarios']]
    assert counts==[4,5,7]
    assert [s['counts']['current_batch_flagged'] for s in report['scenarios']]==[2,2,4]
    assert len(report['families'])==8 and len(report['candidate_ids'])==13
    candidates={c['content_body']['title']:c for c in result['candidates']}
    assert candidates['R0']['moment_ids']!=candidates['A0']['moment_ids']  # Previously unused evidence.
    assert candidates['R0']['first_generated_at']==candidates['A0']['first_generated_at']
    assert 'Not measured' in candidates['R0']['content_body']['qualifiers']
    assert any('internal_only' in x for x in candidates['R0']['content_body']['risks'])
    initial = next(j for j in repo.review('week_2026-06-08')['jobs'] if j['stage']=='angle_initial_assessment')['result_refs']
    generation = next(j for j in repo.review('week_2026-06-08')['jobs'] if j['stage']=='angle_generation')['result_refs']
    assert initial['assessment_snapshot']['as_of']==generation['evaluation_as_of']
    assert report['assessment_snapshot']['as_of']==initial['assessment_snapshot']['as_of']
    assert report['assessment_snapshot']['history']==initial['assessment_snapshot']['history']
    for scenario in report['scenarios']:
        selected=set(scenario['selected_ids'])
        assert candidates['R0']['angle_id'] in selected and candidates['R1']['angle_id'] in selected
        assert candidates['R3']['angle_id'] not in selected and candidates['R5']['angle_id'] not in selected
        assert len(selected)==scenario['counts']['final_qualified']
    assert candidates['A4']['angle_id'] in report['scenarios'][1]['selected_ids']
    assert candidates['A3']['angle_id'] in report['scenarios'][2]['selected_ids']  # Invalid-quality replacement cannot evict qualifying original.
    review=repo.review('week_2026-06-08')
    assert len(review['angles'])==13 and all(a['selection_status']=='candidate' and a['approval_status']=='pending' for a in review['angles'])
    assert next(r for r in review['runs'] if r['run_id']==run['run_id'])['status']=='completed'
    app=FastAPI();app.include_router(router(repo.settings));client=TestClient(app)
    headers={'Authorization':'Bearer test-secret','X-Atelier-Actor':'verified'}
    assert client.get(f"/storage/runs/{run['run_id']}/comparison").status_code==401
    assert client.get(f"/storage/runs/{run['run_id']}/comparison",headers=headers).json()['report']['scenarios']==json.loads(json.dumps(report,default=str))['scenarios']
    csv=client.get(f"/storage/runs/{run['run_id']}/comparison.csv",headers=headers)
    assert csv.status_code==200 and csv.headers['content-type'].startswith('text/csv')
    assert 'original_quality' in csv.text and csv.text.count(run['run_id'])==24
    angle=candidates['A6']
    deny=client.post(f"/storage/angles/{angle['angle_id']}/decision",headers=headers,json={'expected_hash':angle['content_hash'],'decision':'approved','cta':{'text':'Discuss'}})
    assert deny.status_code==409 and 'threshold' in deny.json()['detail']
    # Display/export is read-only and reproducible.
    before=len(provider.calls),len(provider.embeddings)
    assert repo.comparison_report(run['run_id'])['report']==report
    assert before==(len(provider.calls),len(provider.embeddings))
    if os.getenv('ATELIER_WRITE_VERIFICATION')=='true':
        folder=BACKEND_ROOT/'.storage-artifacts'/'verification'/'comparison'
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'synthetic-comparison.json').write_text(json.dumps({'synthetic':True,'external_calls':0,
            **client.get(f"/storage/runs/{run['run_id']}/comparison",headers=headers).json()},indent=2),encoding='utf-8')
        (folder/'synthetic-comparison.csv').write_text(csv.text,encoding='utf-8')


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
@pytest.mark.parametrize('empty,no_targets',[(True,False),(False,True)])
def test_empty_and_no_targets_are_valid_explained_results(comparison_setup,empty,no_targets):
    repo,models,_=comparison_setup; provider=ComparisonProvider(empty=empty,no_targets=no_targets)
    run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW); drain(SQLWorker(repo.settings,models,provider=provider),12)
    report=repo.comparison_report(run['run_id'])['report']
    assert report['status']=='comparison_complete'
    assert provider.calls==['moment_extraction','angle_generation']
    assert all(s['counts']['final_qualified']==(0 if empty else 8) for s in report['scenarios'])


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_missing_hidden_vector_pauses_before_refinement(comparison_setup):
    repo,models,_=comparison_setup
    with repo.connection() as conn:
        conn.execute("UPDATE content_angles SET embedding=NULL,embedding_input_hash=NULL WHERE angle_id='angle_extra_5'")
    provider=ComparisonProvider();run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW)
    drain(SQLWorker(repo.settings,models,provider=provider),12)
    assert provider.calls==['moment_extraction','angle_generation']
    jobs=[j for j in repo.review('week_2026-06-08')['jobs'] if j['run_id']==run['run_id']]
    initial=next(j for j in jobs if j['stage']=='angle_initial_assessment')
    assert initial['status']=='waiting' and initial['result_refs']['scenarios'] is None
    assert 'angle_extra_5' in initial['result_refs']['problems']
    assert next(j for j in jobs if j['stage']=='angle_refinement')['status']=='queued'


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
@pytest.mark.parametrize('invalid',['envelope','duplicate','historical_moment'])
def test_invalid_refinement_is_operational_failure_preserving_originals(comparison_setup,invalid):
    repo,models,_=comparison_setup;provider=ComparisonProvider(invalid=invalid)
    run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW);drain(SQLWorker(repo.settings,models,provider=provider),12)
    review=repo.review('week_2026-06-08');job=next(j for j in review['jobs'] if j['stage']=='angle_refinement')
    assert job['status']=='failed' and len(review['angles'])==8
    assert all(a['selection_status']=='candidate' for a in review['angles'])
    assert len(provider.calls)==3 and repo.comparison_report(run['run_id'])['completion_state']=='pending'


def test_unrounded_strict_boundaries_and_independent_baseline_gate():
    for cutoff in (.78,.85,.90):
        metric={'angle_id':'original','grounding_valid':True,'coverage_complete':True,'base_score':70.,'max_historical_cosine':cutoff}
        assert diagnoses(metric,cutoff)==['quality','historical_overlap']
        assert not diagnoses({**metric,'base_score':70.0000001,'max_historical_cosine':cutoff-1e-12},cutoff)
    original={'angle_id':'original','grounding_valid':True,'coverage_complete':True,'base_score':90.,'max_historical_cosine':.84,'adjusted_score':20.}
    replacement={**original,'angle_id':'replacement','base_score':60.,'max_historical_cosine':.1}
    output=scenarios([{'original_id':'original','replacement_id':'replacement','targeted':True}],{'original':original,'replacement':replacement})
    assert output[0]['selected_ids']==[] and output[1]['selected_ids']==['original']


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_response_cache_recovers_after_sql_failure_without_second_dispatch(comparison_setup,monkeypatch):
    repo,models,_=comparison_setup;provider=ComparisonProvider();worker=SQLWorker(repo.settings,models,provider=provider)
    run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW)
    for _ in range(5): worker.once()
    before=repo.review('week_2026-06-08')['angles']
    original_save=worker.repo.save_angles
    def fail_after_response(*args,**kwargs):
        if kwargs.get('parents'): raise RuntimeError('Synthetic SQL write failure after validated response')
        return original_save(*args,**kwargs)
    monkeypatch.setattr(worker.repo,'save_angles',fail_after_response)
    worker.once()
    assert len(provider.calls)==3
    review=repo.review('week_2026-06-08'); job=next(j for j in review['jobs'] if j['stage']=='angle_refinement')
    assert job['status']=='failed' and review['angles']==before
    monkeypatch.setattr(worker.repo,'save_angles',original_save)
    repo.retry(job['job_id'],'editor');worker.once()
    pending=repo.review('week_2026-06-08')
    assert len(pending['angles'])==13  # Parents remain inspectable before final assessment.
    drain(worker,6)
    assert repo.comparison_report(run['run_id'])['completion_state']=='comparison_complete'
    assert len(provider.calls)==3
    saved=next(j for j in repo.review('week_2026-06-08')['jobs'] if j['stage']=='angle_refinement')
    assert saved['attempt_count']==2 and saved['result_refs']['cache_reused'] and not saved['result_refs']['dispatched']


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
@pytest.mark.parametrize('change',['history_content','quality','age','vector','contract','source','moment'])
def test_changed_frozen_inputs_cannot_produce_semantic_rejection(comparison_setup,change):
    repo,models,_=comparison_setup;provider=ComparisonProvider();worker=SQLWorker(repo.settings,models,provider=provider)
    run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW)
    for _ in range(5): worker.once()
    with repo.connection() as conn:
        if change=='history_content':
            conn.execute("UPDATE content_angles SET content_body=jsonb_set(content_body,'{argument}','\"Changed argument\"') WHERE angle_id='angle_extra_5'")
        elif change=='quality': conn.execute("UPDATE content_angles SET base_score=90 WHERE angle_id='angle_extra_5'")
        elif change=='age': conn.execute("UPDATE content_angles SET first_generated_at=first_generated_at-interval '1 day' WHERE angle_id='angle_extra_5'")
        elif change=='vector': conn.execute("UPDATE content_angles SET embedding=%s WHERE angle_id='angle_extra_5'",([0.,1.]+[0.]*1534,))
        elif change=='contract': conn.execute("UPDATE pipeline_jobs SET result_refs=jsonb_set(result_refs,'{contract}','\"incompatible\"') WHERE stage='angle_embedding'")
        elif change=='source': conn.execute("UPDATE transcripts SET original_text=original_text||'changed' WHERE week_id='week_2026-06-08'")
        elif change=='moment': conn.execute("UPDATE key_moments SET moment_body=jsonb_set(moment_body,'{proposition}','\"Changed proposition\"') WHERE week_id='week_2026-06-08'")
    worker.once()
    review=repo.review('week_2026-06-08'); job=next(j for j in review['jobs'] if j['stage']=='angle_refinement')
    assert job['status'] in {'waiting','failed'}
    assert provider.calls==['moment_extraction','angle_generation']
    assert repo.comparison_report(run['run_id'])['completion_state']=='pending'
    assert all(a['selection_status']=='candidate' for a in review['angles'])


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_edit_rescore_reassessment_keeps_comparison_and_approval_denied(comparison_setup):
    repo,models,_=comparison_setup;provider=ComparisonProvider();worker=SQLWorker(repo.settings,models,provider=provider)
    run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW);drain(worker,12)
    original=next(a for a in repo.review('week_2026-06-08')['angles'] if a['content_body']['title']=='A6')
    edited=gate_one.edit(repo,original['angle_id'],original['content_hash'],{'title':'Reviewed title'},'editor')
    scores={n:5. for n in ('grounding','strategic_fit','distinctiveness','audience_resonance','source_strength')} | {'reasons':['Source-grounded review']}
    gate_one.rescore(repo,edited['angle_id'],edited['content_hash'],scores,'editor')
    with pytest.raises(ValueError,match='threshold'):
        gate_one.decide(repo,edited['angle_id'],edited['content_hash'],'approved',{'text':'Discuss'},True,'Reviewed','editor')
    before=len(provider.calls)
    reassessed=gate_one.reassess(repo,'week_2026-06-08','editor');drain(worker,8)
    assert reassessed['workflow']==WORKFLOW and len(provider.calls)==before
    assert repo.comparison_report(reassessed['run_id'])['completion_state']=='comparison_complete'
    with pytest.raises(ValueError,match='threshold'):
        gate_one.decide(repo,edited['angle_id'],edited['content_hash'],'approved',{'text':'Discuss'},True,'Reviewed','editor')


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_zero_qualified_with_no_supported_alternatives_is_valid(comparison_setup):
    class LowProvider(ComparisonProvider):
        def json_call(self,**kwargs):
            output,meta=super().json_call(**kwargs)
            if kwargs['stage']=='angle_generation':
                for angle in output['angles']:
                    angle['quality'].update({n:3. for n in ('grounding','strategic_fit','distinctiveness','audience_resonance','source_strength')})
            if kwargs['stage']=='angle_refinement':
                for outcome in output['outcomes']:
                    outcome.update(outcome='no_supported_alternative',replacement=None,explanation='No stronger supported argument')
            return output,meta
    repo,models,_=comparison_setup;provider=LowProvider();run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW)
    drain(SQLWorker(repo.settings,models,provider=provider),12)
    result=repo.comparison_report(run['run_id'])
    assert result['completion_state']=='comparison_complete'
    assert all(s['counts']['final_qualified']==0 and s['counts']['no_supported_alternative']==8 for s in result['report']['scenarios'])


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_replay_cache_only_never_dispatches_provider(comparison_setup):
    repo,models,_=comparison_setup;provider=ComparisonProvider()
    run=repo.submit('week_2026-06-08','replay',workflow=WORKFLOW)
    drain(SQLWorker(repo.settings,models,provider=provider),12)
    assert provider.calls==[] and provider.embeddings==[]
    jobs=repo.review('week_2026-06-08')['jobs']
    assert next(j for j in jobs if j['run_id']==run['run_id'] and j['stage']=='moment_extraction')['status']=='failed'


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_replay_encoding_miss_never_falls_back_to_injected_provider(comparison_setup):
    repo,models,_=comparison_setup;provider=ComparisonProvider();worker=SQLWorker(repo.settings,models,provider=provider)
    run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW)
    for _ in range(3):worker.once()
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_runs SET input_refs=jsonb_set(input_refs,'{mode}','\"replay\"') WHERE run_id=%s",(run['run_id'],))
    worker.once()
    assert provider.embeddings==[] and provider.calls==['moment_extraction','angle_generation']
    job=next(j for j in repo.review('week_2026-06-08')['jobs'] if j['stage']=='angle_initial_embedding')
    assert job['status']=='waiting'


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_refinement_has_an_independent_default_false_capability(comparison_setup):
    repo,models,_=comparison_setup;provider=ComparisonProvider();worker=SQLWorker(repo.settings,models,provider=provider)
    run=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW)
    for _ in range(5):worker.once()
    assert not repo.settings.refinement_enabled
    # Only isolated synthetic objects change. HTTP remains guarded; no env files change.
    worker.storage.generation_enabled=True
    worker.models=worker.models.model_copy(update={'live_enabled':True,'openrouter_moments_key':'dummy-only','openrouter_angles_key':'dummy-only'})
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_runs SET input_refs=jsonb_set(input_refs,'{mode}','\"live\"') WHERE run_id=%s",(run['run_id'],))
    worker.once()
    job=next(j for j in repo.review('week_2026-06-08')['jobs'] if j['stage']=='angle_refinement')
    assert job['status']=='failed' and 'refinement permission' in job['error_summary']
    assert provider.calls==['moment_extraction','angle_generation']


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_new_history_requires_completed_workflow_and_one_valid_representative(comparison_setup):
    repo,models,_=comparison_setup
    with repo.connection() as conn:
        prior=conn.execute('SELECT * FROM content_angles LIMIT 1').fetchone()
        insert(conn,'pipeline_runs',{'run_id':'unfinished','week_id':prior['week_id'],'run_scope':'weekly_angles',
               'trigger_type':'manual','status':'running','input_refs':{'synthetic':True,'workflow':WORKFLOW,'transcripts':[]}})
        insert(conn,'content_angles',{**prior,'angle_id':'angle_unfinished','run_id':'unfinished'})
        repo.job(conn,'unfinished','angle_generation',{'angle_ids':['angle_unfinished']})
    provider=ComparisonProvider();current=repo.submit('week_2026-06-08','synthetic',workflow=WORKFLOW)
    with repo.connection() as conn:
        run=conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s',(current['run_id'],)).fetchone()
        assert len(history(conn,run,[]))==7
        repo.job(conn,'unfinished','angle_final_assessment',{'status':'comparison_complete','angle_ids':['angle_unfinished']})
        assert len(history(conn,run,[]))==7  # A completed job alone is not a completed workflow.
        conn.execute("UPDATE pipeline_runs SET status='completed' WHERE run_id='unfinished'")
        assert len(history(conn,run,[]))==8
        # Current family excludes that family regardless of which member would match.
        row=conn.execute("SELECT * FROM content_angles WHERE angle_id='angle_unfinished'").fetchone()
        assert len(history(conn,run,[row]))==7


@pytest.mark.skipif(not URL,reason='Requires isolated atelier_test')
def test_legacy_partial_quality_retains_other_successful_assessments(setup):
    repo,models,_=setup;provider=NonemptyProvider();worker=SQLWorker(repo.settings,models,provider=provider)
    repo.submit('week_2026-06-01','synthetic');worker.once();worker.once()
    with repo.connection() as conn:
        conn.execute("UPDATE content_angles SET base_score=NULL,quality_scores=NULL WHERE content_body->>'title'='Different'")
    drain(worker)
    angles=repo.review('week_2026-06-01')['angles']
    assert len([a for a in angles if a['selection_status']=='visible'])==2
    pending=next(a for a in angles if a['content_body']['title']=='Different')
    assert pending['selection_status']=='candidate' and pending['matching_result'] is None
