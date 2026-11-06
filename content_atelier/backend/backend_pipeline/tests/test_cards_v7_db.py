"""Strategist v7 through the product path on PostgreSQL (E.B28, E.B30, E.B32, E.B29 change): the strategy brief frozen with
the cycle and shown at Gate 1, one public card per conversation, the undercut hold with the offer named, and the stance
confirmation the develop path requires (D31). Synthetic fixtures and fake providers only; needs an isolated atelier_test."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one
from backend_pipeline.angle_profiles import STRATEGIST_V7_PROFILE
from backend_pipeline.cycle import window
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, CardSQLProvider, ranked
from backend_pipeline.tests.test_sql_storage import URL, drain, setup  # noqa: F401 (fixture)
from backend_pipeline.tests.test_strategist_v7 import v7_card, v7_output
from backend_pipeline.tests.test_strategy_brief import constructed

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated atelier_test')
STANCE = 'Ads tools can set up campaigns; they cannot decide what a business stands for.'


class V7SQLProvider(CardSQLProvider):
    """Two v7 cards on the week's one call, twice: the repair is asked for, and the later-ranked card is demoted."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage != 'angle_generation':
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        self.calls.append(stage)
        self.card_users.append(user)
        first = v7_card('S1', 1, point='We tell owners a one-off audit is not enough, and we show them what comes next.',
                        public_stance={'takes_stance': True, 'stance': STANCE})
        second = v7_card('S1', 2, title='How we read follow-up before ads, idea 2', point='We read the follow-up before we touch the ads.')
        return v7_output([first, second], publishing_order=[1, 2],
                         internal_insights=[{'moment_ids': ['S2'], 'insight': 'A caution about measurement.', 'use': 'Sales.'}]), {'fake': True}


@pytest.fixture
def v7_setup(setup):
    repo, models, tmp = setup
    repo.settings.brief_enabled = True
    v7_models = models.model_copy(update={'angle_prompt_profile': STRATEGIST_V7_PROFILE, 'knowledge_base_root': constructed(tmp)})
    provider = V7SQLProvider()
    return repo, v7_models, provider, SQLWorker(repo.settings, v7_models, provider=provider)


def test_a_v7_cycle_freezes_its_brief_keeps_one_card_per_call_and_holds_an_undercutting_card(v7_setup):
    repo, models, provider, worker = v7_setup
    run = repo.submit(W1, 'synthetic', models=models)
    drain(worker)
    review = repo.review(W1, 'tester')
    refs = next(r for r in review['runs'] if r['run_id'] == run['run_id'])['input_refs']
    brief = refs['strategy_brief']
    assert refs['strategy_brief_hash'] == brief['brief_hash'] and review['strategy_brief'] == brief
    assert {o['offer'] for o in brief['live_offers']} >= {'Audit Offer', 'Retainer Offer'}
    # The strategist read the brief, and was asked once to repair the slate.
    assert len(provider.card_users) == 2 and "This window's strategy brief" in provider.card_users[0]
    assert 'same conversation' in provider.card_users[1]
    angles = ranked(review)
    assert len(angles) == 1, 'one public card per client conversation'
    (card,) = angles
    assert card['content_body']['card']['point'].startswith('We tell owners a one-off audit')
    assert 'How we read follow-up before ads, idea 2' in [i['idea'] for i in review['selection']['considered_not_selected']]
    # Held until the offer's window ends, the offer named, with a blocking flag at Gate 1.
    assert card['hold']['offers'] == ['Audit Offer'] and card['hold']['until'] == '2026-11-09'
    undercut = [f for f in card['content_body']['ledger']['flags'] if f['kind'] == 'offer_undercut']
    assert len(undercut) == 1 and 'Undercuts Audit Offer' in undercut[0]['message']
    job = next(j for j in review['jobs'] if j['run_id'] == run['run_id'] and j['stage'] == 'angle_generation')
    assert job['result_refs']['strategy_brief_hash'] == brief['brief_hash']
    assert list(job['result_refs']['held_by_strategy_brief']) == [card['angle_id']]
    assert job['result_refs']['reference_repair']['demoted_same_conversation'][0]['rank'] == 2


def test_a_public_stance_card_is_developed_only_after_an_approver_confirms_it(v7_setup):
    repo, models, provider, worker = v7_setup
    repo.submit(W1, 'synthetic', models=models)
    drain(worker)
    (card,) = ranked(repo.review(W1, 'tester'))
    body = card['content_body']
    verified = body['card']['verify_before_publishing'] + [f['id'] for f in body['ledger']['flags'] if f['severity'] == 'block']
    with pytest.raises(ValueError, match='public stance'):
        gate_one.decide(repo, card['angle_id'], card['content_hash'], 'approved', DECIDE, False, 'Checked against the call.',
                        'tester', verified=verified)
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)
    repo.settings.brief_approvers = ('tester', 'tester@example.invalid')
    repo.settings.brief_editors = ('editor', 'editor@example.invalid')
    headers = {'Authorization': 'Bearer test-secret', 'X-Atelier-Actor': 'editor', 'X-Atelier-Email': 'editor@example.invalid'}
    path = f"/storage/angles/{card['angle_id']}/stance"
    assert client.post(path, headers=headers, json={'expected_hash': card['content_hash']}).status_code == 403, 'an approver confirms'
    headers.update({'X-Atelier-Actor': 'tester', 'X-Atelier-Email': 'tester@example.invalid'})
    assert client.post(path, headers=headers, json={'expected_hash': 'stale'}).status_code == 409
    confirmed = client.post(path, headers=headers, json={'expected_hash': card['content_hash'], 'note': 'Whitney agreed on the call.'})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['stance_confirmation']['stance'] == STANCE and confirmed.json()['content_hash'] == card['content_hash']
    week = client.get(f'/storage/weeks/{W1}', headers=headers).json()
    shown = next(a for a in week['angles'] if a['angle_id'] == card['angle_id'])
    assert shown['stance_confirmation']['by'] == 'tester@example.invalid' and week['strategy_brief']['brief_hash']
    result = gate_one.decide(repo, card['angle_id'], card['content_hash'], 'approved', DECIDE, False, 'Checked against the call.',
                             'tester', verified=verified)
    assert result['approval_status'] == 'approved'


def test_a_rejected_card_stays_internal_and_its_reason_is_on_the_review(v7_setup):
    repo, models, provider, worker = v7_setup

    class Rejected(V7SQLProvider):
        def json_call(self, *, stage, system, user, schema, fingerprint):
            if stage != 'angle_generation':
                return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
            self.card_users.append(user)
            return v7_output([v7_card('S1', 1, reader_takeaway='Check your own budget settings tonight.')]), {'fake': True}
    worker = SQLWorker(repo.settings, models, provider=Rejected())
    repo.submit(W1, 'synthetic', models=models)
    drain(worker)
    (card,) = ranked(repo.review(W1, 'tester'))
    assert card['public_use']['kinds'] == ['takeaway_instructs'] and card['public_use']['reasons'][0].startswith('Rejected for public use')
    verified = card['content_body']['card']['verify_before_publishing'] + [
        f['id'] for f in card['content_body']['ledger']['flags'] if f['severity'] == 'block']
    with pytest.raises(ValueError, match='mark it internal'):
        gate_one.decide(repo, card['angle_id'], card['content_hash'], 'approved', DECIDE, False, 'Checked.', 'tester', verified=verified)
    from backend_pipeline.gates import decisions
    kept = decisions.dispose(repo, card['angle_id'], card['content_hash'], 'internal', 'tester', reason_code='internal_use',
                             note='A tactic for our own playbook.')
    assert kept['disposition'] == 'internal'


def test_the_cycle_routes_show_the_brief(v7_setup):
    repo, models, provider, worker = v7_setup
    with repo.connection() as conn:
        documents = repo.frozen_sources(conn, W1)
    run = repo.submit(W1, 'synthetic', models=models, documents=documents, selected_by='window')
    detail = window.detail(repo, run['run_id'])
    assert detail['strategy_brief']['brief_hash'] == detail['strategy_brief_hash']
    assert window.listing(repo)[0]['strategy_brief_hash'] == detail['strategy_brief_hash']
    preview = window.brief_preview(repo, models)
    assert preview['beliefs_to_prove'] and preview['version'] == 'strategy-brief.v1'
