"""Strategist cards through the product path on real PostgreSQL/pgvector (E.B16), and per-moment extraction (E.B12a).

Synthetic fixtures and fake providers only; zero external requests. Needs an isolated atelier_test database.
"""
import copy
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one
from backend_pipeline.angle_profiles import STRATEGIST_V4_PROFILE
from backend_pipeline.angle_workflow import WORKFLOW
from backend_pipeline.briefs.workflow import output as brief_output
from backend_pipeline.chunk_encoding import queue as encode_chunks
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.test_briefs import BriefProvider
from backend_pipeline.tests.test_sql_storage import URL, NonemptyProvider, drain, setup  # noqa: F401 (fixture)
from backend_pipeline.tests.test_strategist_profile import card, write_kb

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated atelier_test')
DECIDE = {'choice': 'decide_in_development'}
W1, W2 = 'week_2026-06-01', 'week_2026-06-08'


class CardSQLProvider(BriefProvider):
    """Extraction with one public and one internal-only scene; three ranked cards, rank 3 a near-twin of rank 1."""

    def __init__(self):
        super().__init__()
        self.card_users = []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == 'moment_extraction':
            output, meta = NonemptyProvider.json_call(self, stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
            other = copy.deepcopy(output['moments'][0])
            other.update(local_key='internal', anchor_span_ids=['m1.t0002'], context_first_span_id='m1.t0002',
                         context_last_span_id='m1.t0002', quote='It was an observation, not a measured result.',
                         sensitivity='internal_only', qualifications=[])
            output['moments'].append(other)
            return output, meta
        if stage != 'angle_generation':
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        self.calls.append(stage)
        self.card_users.append(user)
        assert re.findall(r'^## Scene (S\d+) ', user, re.MULTILINE) == ['S1', 'S2']
        return {'week_summary': 'One call shows how WIA reviews follow-up.',
                'angles': [card('S1', 2), card('S1', 1), card('S1', 3)],
                'internal_insights': [{'moment_ids': ['S2'], 'insight': 'A caution about measurement.', 'use': 'Sales.'}],
                'considered_not_selected': [{'moment_ids': ['S1'], 'idea': 'Generic tips.', 'reason': 'Too narrow.'}]}, {'fake': True}

    def embed(self, *, text, fingerprint):
        self.embeddings.append(text)
        found = re.search(r'idea (\d)', text)
        vector = [0.] * 1536
        vector[{'1': 2, '2': 3, '3': 2}[found.group(1)] if found else 0] = 1.
        return vector, {'fake': True}


@pytest.fixture
def cards_setup(setup):
    repo, models, tmp = setup
    repo.settings.brief_enabled = True
    repo.settings.brief_approvers = ('tester',)
    repo.settings.brief_editors = ('editor',)
    card_models = models.model_copy(update={'angle_prompt_profile': STRATEGIST_V4_PROFILE, 'knowledge_base_root': write_kb(tmp / 'kb')})
    provider = CardSQLProvider()
    return repo, card_models, provider, SQLWorker(repo.settings, card_models, provider=provider)


def ranked(review):
    return [a for a in review['angles'] if a['content_body'].get('card')]


def test_cards_on_the_legacy_runner_are_selected_by_rank_and_duplicate_check(cards_setup):
    repo, models, provider, worker = cards_setup
    run = repo.submit(W1, 'synthetic', models=models)
    drain(worker)
    review = repo.review(W1, 'tester')
    angles = ranked(review)
    assert [a['content_body']['card']['rank'] for a in angles] == [1, 2, 3]
    assert [a['selection_status'] for a in angles] == ['visible', 'visible', 'suppressed']
    assert angles[2]['matching_result']['selection'] == {'selection_status': 'suppressed', 'reason': 'duplicate',
                                                        'duplicate_of': angles[0]['angle_id'], 'cosine': pytest.approx(1.)}
    assert all(a['base_score'] is None and a['adjusted_score'] is None for a in angles)
    assert all(a['matching_result']['status'] == 'complete' for a in angles)
    assert [a['can_approve'] for a in angles] == [True, True, False] and not any(a['can_rescore'] for a in angles)
    assert next(r for r in review['runs'] if r['run_id'] == run['run_id'])['input_refs']['angle_prompt_profile'] == STRATEGIST_V4_PROFILE
    selection = review['selection']
    assert selection['week_summary'].startswith('One call') and [r['current_angle_id'] for r in selection['ranking']] == [
        a['angle_id'] for a in angles]
    assert selection['internal_insights'][0]['moment_ids'][0].startswith('moment_')
    top = angles[0]
    approval = gate_one.decide(repo, top['angle_id'], top['content_hash'], 'approved', {'text': 'Talk to us'}, False, None, 'tester',
                               verified=top['content_body']['card']['verify_before_publishing'])
    assert approval['approval_status'] == 'approved' and approval['brief_run']


def test_strategist_cards_run_on_the_comparison_workflow_through_gate_one_to_brief_preparation(cards_setup):
    repo, models, provider, worker = cards_setup
    # An earlier week whose cards were never encoded, like a generation-only run.
    repo.submit(W1, 'synthetic', models=models)
    worker.once(); worker.once()
    with repo.connection() as conn:
        earlier = [r['angle_id'] for r in conn.execute('SELECT angle_id FROM content_angles WHERE week_id=%s', (W1,))]
        conn.execute("UPDATE pipeline_runs SET status='failed' WHERE week_id=%s AND run_scope='weekly_angles'", (W1,))
        conn.execute("UPDATE pipeline_jobs SET status='failed' WHERE week_id=%s AND status='queued'", (W1,))
    assert len(earlier) == 3
    run = repo.submit(W2, 'synthetic', workflow=WORKFLOW, models=models)
    drain(worker, 12)
    report = repo.comparison_report(run['run_id'])
    assert report['completion_state'] == 'comparison_complete', repo.review(W2)['jobs']
    assert report['report']['selection_basis'] == 'card_rank' and report['report']['scenarios'] == []
    assert 'angle_refinement' not in provider.calls
    review = repo.review(W2, 'tester')
    angles = ranked(review)
    assert [a['content_body']['card']['rank'] for a in angles] == [1, 2, 3]
    assert [a['selection_status'] for a in angles] == ['visible', 'visible', 'suppressed']
    assert {g['id'] for g in angles[0]['matching_result']['history_gaps']} == set(earlier)
    assert [a['can_approve'] for a in angles] == [True, True, False]
    assert review['week']['status'] == 'review'
    top, second, twin = angles

    with pytest.raises(ValueError, match='ranked, not scored'):
        gate_one.rescore(repo, top['angle_id'], top['content_hash'], {'grounding': 5., 'source_relevance': 5., 'audience_fit': 5.,
                         'specificity': 5., 'editorial_usefulness': 5., 'reasons': ['r']}, 'tester')
    with pytest.raises(ValueError, match='collapsed'):
        gate_one.decide(repo, twin['angle_id'], twin['content_hash'], 'approved', DECIDE, True, 'n', 'tester',
                        verified=twin['content_body']['card']['verify_before_publishing'])
    with pytest.raises(ValueError, match='Acknowledge every'):
        gate_one.decide(repo, second['angle_id'], second['content_hash'], 'approved', DECIDE, False, None, 'tester', verified=[])

    # Edit the top card: a new version supersedes it and must be matched again before approval.
    edited = gate_one.edit(repo, top['angle_id'], top['content_hash'], {'core_perspective': 'A sharper take on idea 1.'}, 'editor')
    with pytest.raises(ValueError, match='replacement already exists'):
        gate_one.decide(repo, top['angle_id'], top['content_hash'], 'approved', DECIDE, False, None, 'tester',
                        verified=top['content_body']['card']['verify_before_publishing'])
    # The edit queued the new version's comparison check itself; the worker runs it.
    assert edited['check']['status'] == 'queued'
    drain(worker, 8)
    review = repo.review(W2, 'tester')
    current = next(a for a in review['angles'] if a['angle_id'] == edited['angle_id'])
    assert current['selection_status'] == 'visible' and current['can_approve']
    assert current['content_body']['card']['core_perspective'] == 'A sharper take on idea 1.'
    assert review['selection']['ranking'][0]['current_angle_id'] == edited['angle_id']

    for week in (W1, W2):
        encode_chunks(repo, models, week)
    drain(worker)
    approval = gate_one.decide(repo, edited['angle_id'], current['content_hash'], 'approved', DECIDE, False, None, 'tester',
                               verified=current['content_body']['card']['verify_before_publishing'])
    with repo.connection() as conn:
        row = conn.execute('SELECT selected_cta,matching_result FROM content_angles WHERE angle_id=%s', (edited['angle_id'],)).fetchone()
        brief_run = conn.execute('SELECT * FROM pipeline_runs WHERE run_id=%s', (approval['brief_run']['run_id'],)).fetchone()
    assert row['selected_cta'] == DECIDE and row['matching_result']['approval_policy']['rule'] == 'card_rank_v1'
    assert row['matching_result']['verification_acknowledged'] == current['content_body']['card']['verify_before_publishing']
    assert brief_run['input_refs']['angle']['cta'] == DECIDE
    worker.once(run_id=brief_run['run_id'])
    prepared = brief_output(worker, brief_run, 'brief_prepare')
    assert prepared['evidence'] and {g['angle_id'] for g in prepared['prior_gaps']} >= set(earlier)


def test_api_returns_the_selection_block_and_accepts_card_approval(cards_setup):
    repo, models, provider, worker = cards_setup
    repo.settings.api_secret = 'test-secret'
    repo.submit(W1, 'synthetic', models=models)
    drain(worker)
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)
    repo.settings.brief_approvers = ('tester', 'tester@example.invalid')
    headers = {'Authorization': 'Bearer test-secret', 'X-Atelier-Actor': 'tester', 'X-Atelier-Email': 'tester@example.invalid'}
    week = client.get(f'/storage/weeks/{W1}', headers=headers).json()
    angles = [a for a in week['angles'] if a['content_body'].get('card')]
    assert [a['content_body']['card']['rank'] for a in angles] == [1, 2, 3]
    assert [r['rank'] for r in week['selection']['ranking']] == [1, 2, 3]
    assert week['selection']['considered_not_selected'][0]['reason'] == 'Too narrow.'
    second = angles[1]
    body = {'expected_hash': second['content_hash'], 'decision': 'approved', 'cta': DECIDE}
    assert client.post(f"/storage/angles/{second['angle_id']}/decision", headers=headers, json=body).status_code == 409
    body['verify_acknowledged'] = second['content_body']['card']['verify_before_publishing']
    accepted = client.post(f"/storage/angles/{second['angle_id']}/decision", headers=headers, json=body)
    assert accepted.status_code == 200 and accepted.json()['approval_status'] == 'approved'


def test_profile_is_frozen_at_submit_and_checked_before_extraction(cards_setup, tmp_path):
    repo, models, provider, _worker = cards_setup
    with pytest.raises((ValueError, FileNotFoundError)):
        repo.submit(W1, 'replay', models=models.model_copy(update={'knowledge_base_root': tmp_path / 'missing'}))
    with repo.connection() as conn:
        assert not conn.execute("SELECT 1 FROM pipeline_runs WHERE run_scope='weekly_angles'").fetchone()
    run = repo.submit(W1, 'synthetic', workflow=WORKFLOW, models=models)
    legacy = SQLWorker(repo.settings, models.model_copy(update={'angle_prompt_profile': '2026-10-16.reel-editorial.v1'}), provider=provider)
    legacy.once()
    job = next(j for j in repo.review(W1)['jobs'] if j['run_id'] == run['run_id'] and j['stage'] == 'moment_extraction')
    assert job['status'] == 'failed' and 'frozen at submit' in job['error_summary']
    assert provider.calls == []


class PartialQuoteProvider(NonemptyProvider):
    """One exact moment, one near-miss quote and one quote that does not bind."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        output, meta = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        if stage == 'moment_extraction':
            near = copy.deepcopy(output['moments'][0])
            near.update(local_key='near', anchor_span_ids=['m1.t0002'], context_first_span_id='m1.t0002',
                        context_last_span_id='m1.t0002', quote='It was an observation not a measured result')
            wrong = copy.deepcopy(near)
            wrong.update(local_key='wrong', quote='It was a measured result.')
            output['moments'] += [near, wrong]
        else:
            # Acknowledge every moment that survived validation.
            output['processed_moment_ids'] = list(dict.fromkeys(re.findall(r'"moment_id": "(moment_[a-f0-9]+)"', user)))
        return output, meta


def test_weekly_extraction_keeps_binding_moments_when_one_quote_fails(setup):
    repo, models, _tmp = setup
    provider = PartialQuoteProvider()
    worker = SQLWorker(repo.settings, models, provider=provider)
    repo.submit(W1, 'synthetic')
    drain(worker)
    review = repo.review(W1)
    extraction = next(j for j in review['jobs'] if j['stage'] == 'moment_extraction' and j['status'] == 'completed')['result_refs']
    assert len(extraction['moment_ids']) == 2
    assert [r['repaired_quote'] for r in extraction['quote_repairs']] == ['It was an observation, not a measured result']
    assert [u['local_key'] for u in extraction['unverified_moments']] == ['wrong']
    assert extraction['unverified_usable_as_proof'] is False
    with repo.connection() as conn:
        saved = conn.execute('SELECT moment_id,moment_body FROM key_moments').fetchall()
    assert {m['moment_id'] for m in saved} == set(extraction['moment_ids'])
    assert all(m['moment_body']['quote'] != 'It was a measured result.' for m in saved)
    for moment_id in extraction['moment_ids']:
        repo.moment_context(moment_id)  # Every saved quote resolves into its original anchor.
    assert review['angles'] and provider.calls == ['moment_extraction', 'angle_generation']


class UnboundProvider(CardSQLProvider):
    """Every extracted quote fails to bind: the week keeps no moment as proof (E.B12a)."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        output, meta = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        if stage == 'moment_extraction':
            for moment in output['moments']:
                moment['quote'] = 'Words nobody said on this call at all.'
        return output, meta


def test_a_week_with_no_bound_moment_never_pays_for_a_strategist_call(cards_setup):
    """E.B12a keeps unverified moments out of proof; with none left, the angle stage stops before the paid call."""
    repo, models, _, _ = cards_setup
    provider = UnboundProvider()
    worker = SQLWorker(repo.settings, models, provider=provider)
    run = repo.submit(W1, 'synthetic', models=models)
    drain(worker)
    assert 'angle_generation' not in provider.calls
    with repo.connection() as conn:
        job = conn.execute("SELECT status,error_summary FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation'",
                           (run['run_id'],)).fetchone()
    assert job['status'] == 'failed' and 'No moment' in job['error_summary']


class ConsentProvider(CardSQLProvider):
    """Records what the strategist is shown; its cards cite only the first scene."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage != 'angle_generation':
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        self.calls.append(stage)
        self.card_users.append(user)
        return {'week_summary': 'One call.', 'angles': [card('S1', 1)], 'internal_insights': [],
                'considered_not_selected': []}, {'fake': True}


@pytest.mark.skipif(not URL, reason='Requires isolated atelier_test')
def test_a_do_not_use_scene_never_reaches_the_strategist_and_blocks_a_card_that_cites_it(cards_setup):
    """E.B16 f, R40: consent can be stricter than the extractor's label. A scene whose client asked not to be used is
    dropped before the strategist call and recorded with the reason; a card citing such a scene cannot be developed."""
    repo, models, _, _ = cards_setup
    provider = ConsentProvider()
    worker = SQLWorker(repo.settings, models, provider=provider)
    run = repo.submit(W1, 'synthetic', models=models)
    drain(worker, 1)  # extraction only
    with repo.connection() as conn:
        rows = conn.execute("SELECT moment_id,moment_body FROM key_moments WHERE run_id=%s ORDER BY moment_id", (run['run_id'],)).fetchall()
        blocked = next(r['moment_id'] for r in rows if r['moment_body']['sensitivity'] == 'internal_only')
        kept = next(r['moment_id'] for r in rows if r['moment_id'] != blocked)
        conn.execute("UPDATE key_moments SET consent_status='do_not_use' WHERE moment_id=%s", (blocked,))
    drain(worker)
    user = provider.card_users[-1]
    # Only the first scene is shown (its context turns overlap the dropped scene's turn, which is its own matter).
    assert re.findall(r'^## Scene (S\d+) ', user, re.MULTILINE) == ['S1'] and 'Handling: internal only' not in user
    with repo.connection() as conn:
        refs = conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation'",
                            (run['run_id'],)).fetchone()['result_refs']
    assert [d['moment_id'] for d in refs['consent_dropped']] == [blocked] and 'do_not_use' in refs['consent_dropped'][0]['reason']
    assert refs['moment_ids'] == [kept]
    # A client who withdraws consent later: the card citing the scene can no longer be developed.
    top = ranked(repo.review(W1, 'tester'))[0]
    with repo.connection() as conn:
        conn.execute("UPDATE key_moments SET consent_status='do_not_use' WHERE moment_id=%s", (kept,))
    with pytest.raises(ValueError, match='asked not to be used'):
        gate_one.decide(repo, top['angle_id'], top['content_hash'], 'approved', DECIDE, False, 'Checked', 'tester',
                        verified=top['content_body']['card']['verify_before_publishing']
                        + [f['id'] for f in top['content_body']['ledger']['flags'] if f['severity'] == 'block'])



class OversizedProvider(ConsentProvider):
    """Refuses the strategist call while an internal-only scene is in it, as the live preflight refuses a week too large."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == 'angle_generation' and 'Handling: internal only' in user:
            self.calls.append('refused')
            from backend_pipeline.llm.stage import OVERSIZED_WEEK
            raise RuntimeError(f'{OVERSIZED_WEEK}; no request sent. No batching or truncation permitted.')
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


@pytest.mark.skipif(not URL, reason='Requires isolated atelier_test')
def test_a_week_too_large_for_one_call_leaves_out_its_internal_scenes_and_says_so(cards_setup):
    """2 November 2026: the first live week was refused as too large and recovered by hand. Now the internal-only scenes are
    left out and the coverage names them as not sent; a public-eligible scene is never left out."""
    repo, models, _, _ = cards_setup
    provider = OversizedProvider()
    worker = SQLWorker(repo.settings, models, provider=provider)
    run = repo.submit(W1, 'synthetic', models=models)
    drain(worker)
    assert provider.calls.count('refused') == 1 and provider.calls.count('angle_generation') == 1
    with repo.connection() as conn:
        job = conn.execute("SELECT status,result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation'",
                           (run['run_id'],)).fetchone()
        internal = conn.execute("""SELECT moment_id FROM key_moments WHERE run_id=%s AND moment_body->>'sensitivity'='internal_only'""",
                                (run['run_id'],)).fetchone()['moment_id']
    assert job['status'] == 'completed'
    refs = job['result_refs']
    assert refs['size_dropped'] == [internal] and internal not in refs['moment_ids'] and len(refs['moment_ids']) == 1
    assert refs['scene_coverage']['state'] == 'incomplete' and refs['scene_coverage']['not_sent'] == [internal]
    assert ranked(repo.review(W1, 'tester'))
