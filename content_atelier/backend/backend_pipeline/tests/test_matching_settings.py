"""0.B8: the SQL weekly path scores with matching.related, matching.close, matching.half_life_days,
matching.max_recency_penalty and scoring.visible_threshold, frozen into the assessment snapshot."""
from datetime import UTC, datetime, timedelta

import pytest

from backend_pipeline.config import Settings
from backend_pipeline.matching import FIXED, assess, frozen_scoring, risk, scoring
from backend_pipeline.settings_store import default
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_config import encoding_contract
from backend_pipeline.tests.test_sql_storage import URL, NonemptyProvider, drain, setup  # noqa: F401 (fixture)

LENIENT = {'similarity_threshold':.5,'close_similarity_threshold':.95,'recency_half_life_days':1000.,
           'max_recency_penalty':.2,'visible_threshold':60.}


def test_the_fixed_values_are_the_settings_defaults():
    assert FIXED == {'related':default('matching.related'),'close':default('matching.close'),
                     'half_life_days':default('matching.half_life_days'),
                     'max_recency_penalty':default('matching.max_recency_penalty'),
                     'visible_threshold':default('scoring.visible_threshold')}
    assert frozen_scoring({}) == FIXED, 'a snapshot frozen before 0.B8 scores with the fixed values'


def test_a_run_freezes_what_its_settings_snapshot_recorded_else_the_workers_settings():
    models = Settings(**LENIENT)
    assert scoring(None, models) == {'related':.5,'close':.95,'half_life_days':1000.,'max_recency_penalty':.2,'visible_threshold':60.}
    run = {'input_refs':{'settings_snapshot':{'values':{'matching.related':{'value':.8,'source':'table'},
                                                        'scoring.visible_threshold':{'value':75,'source':'env'}}}}}
    assert scoring(run, models) == {'related':.8,'close':.95,'half_life_days':1000.,'max_recency_penalty':.2,'visible_threshold':75.}
    assert scoring(run) == {**FIXED,'related':.8,'visible_threshold':75.}


def test_risk_follows_the_related_cosine_and_the_half_life():
    now = datetime.now(UTC)
    assert risk(.78,now,now)['risk'] == 0 and risk(.89,now,now)['risk'] == pytest.approx(.5)
    assert risk(.75,now,now,.5)['risk'] == pytest.approx(.5)
    assert risk(1,now-timedelta(days=10),now,.78,10.)['risk'] == pytest.approx(.5)
    assert risk(1,now,now,1.)['risk'] == 1 and risk(.99,now,now,1.)['risk'] == 0


@pytest.mark.skipif(not URL,reason='Set isolated ATELIER_TEST_DATABASE_URL to run PostgreSQL integration tests')
def test_matching_scores_with_the_values_it_froze(setup):  # noqa: F811
    repo,models,_ = setup; p = NonemptyProvider()
    repo.submit('week_2026-06-01','synthetic'); drain(SQLWorker(repo.settings,models,provider=p))
    lenient = models.model_copy(update=LENIENT)
    repo.submit('week_2026-06-08','synthetic'); drain(SQLWorker(repo.settings,lenient,provider=p))
    angles = {a['content_body']['title']:a for a in repo.review('week_2026-06-08')['angles']}
    repeated = angles['Repeated']; result = repeated['matching_result']
    assert result['snapshot']['scoring'] == scoring(None,lenient)
    assert result['history'][0]['cosine'] == pytest.approx(1.) and result['historical_risk'] == pytest.approx(1.,abs=1e-3)
    # The default run suppresses the repeat at half its score; the lenient penalty keeps it above the lenient bar.
    base = result['base_score']
    assert float(repeated['adjusted_score']) == pytest.approx(base*(1-.2*result['historical_risk']))
    assert repeated['adjusted_score'] > 60 and repeated['selection_status'] == 'visible'
    assert [f['angle_id'] for f in result['current_batch_flags']] == [angles['Repeated variation']['angle_id']]
    # A re-check scores from the snapshot, whatever the worker's settings are now; a snapshot without values used the fixed ones.
    contract = encoding_contract(models,synthetic=True)
    with repo.connection() as c:
        again = next(a for a in assess(c,result['snapshot'],contract)['angles'] if a['angle_id']==repeated['angle_id'])
        assert again['adjusted_score'] == pytest.approx(float(repeated['adjusted_score']))
        old = {k:v for k,v in result['snapshot'].items() if k!='scoring'}
        before = next(a for a in assess(c,old,contract)['angles'] if a['angle_id']==repeated['angle_id'])
        assert before['adjusted_score'] == pytest.approx(base*(1-.5*before['historical_risk']))
        c.rollback()
    strict = models.model_copy(update={'close_similarity_threshold':1.,'visible_threshold':99.})
    repo.submit('week_2026-06-08','synthetic'); drain(SQLWorker(repo.settings,strict,provider=p))
    angles = {a['content_body']['title']:a for a in repo.review('week_2026-06-08')['angles']}
    assert all(a['selection_status']=='suppressed' for a in angles.values())
    assert angles['Repeated']['matching_result']['snapshot']['scoring']['visible_threshold'] == 99.
