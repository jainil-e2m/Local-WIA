"""L.B10: a cycle whose content plan entry is older than 30 days says so in its week summary; a new monthly entry
clears it. Synthetic providers only; needs an isolated atelier_test database."""
from datetime import date, timedelta

import pytest

from backend_pipeline.knowledge import review
from backend_pipeline.knowledge.staleness import plan_warning
from backend_pipeline.tests.test_cards_sql import W1, W2, cards_setup  # noqa: F401 (fixture)
from backend_pipeline.tests.test_sql_storage import URL, drain, setup  # noqa: F401 (fixture)

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated atelier_test')


def enter(repo, month):
    with repo.connection() as conn:
        return review.enter(conn, repo.settings, 'tester', kind='content_plan_entry', name=f'{month} plan',
                            body={'topic': f'Promote the Meta Ads Accelerator in {month}', 'purpose': 'convert'},
                            reason='The review owner enters the monthly plan')


def test_a_stale_plan_warns_in_the_week_summary_and_a_new_monthly_entry_clears_it(cards_setup):  # noqa: F811
    repo, models, provider, worker = cards_setup
    with repo.connection() as conn:
        # The setup fixture does not empty the context store: earlier runs on this database leave plan entries behind.
        conn.execute("DELETE FROM brand_kit_items WHERE kind='content_plan_entry'")
        assert plan_warning(conn).startswith('No content plan entry is recorded')
    old = enter(repo, 'August')
    entered = date.today() - timedelta(days=40)
    with repo.connection() as conn:
        conn.execute("UPDATE brand_kit_items SET reviewed_at=%s,created_at=%s WHERE item_id=%s", (entered, entered, old['item_id']))
        assert plan_warning(conn, entered + timedelta(days=30)) is None and plan_warning(conn, entered + timedelta(days=31))
    first = repo.submit(W1, 'synthetic', models=models); drain(worker)
    summary = repo.review(W1)['selection']
    assert summary['run_id'] == first['run_id'] and summary['week_summary']
    assert summary['plan_warning'] == (f'The content plan was last updated on {entered.isoformat()}, 40 days ago, so strategic fit '
                                       "ranks against nothing current. Add this month's plan under What the system knows.")
    snapshot = next(r for r in repo.review(W1)['runs'] if r['run_id'] == first['run_id'])['input_refs']['settings_snapshot']
    assert snapshot['values']['context.plan_max_age_days'] == {'value': 30, 'source': 'default'}
    enter(repo, 'October')
    repo.submit(W2, 'synthetic', models=models); drain(worker)
    assert repo.review(W2)['selection']['plan_warning'] is None
    # The earlier cycle keeps the warning it ran with.
    assert repo.review(W1)['selection']['plan_warning'] == summary['plan_warning']
