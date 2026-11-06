"""Current pack scheduling on real PostgreSQL; no providers or production connections."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend_pipeline.calendar import service as calendar
from backend_pipeline.calendar.contracts import Cancel, Reschedule, Schedule, ScheduleItem
from backend_pipeline.packs import model, versions, views
from backend_pipeline.packs.contracts_v2 import PackDecisionV2, PackEdit, PackMarkPublished
from backend_pipeline.production_common import ProductionError
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401
from backend_pipeline.tests.test_brief_v3_db import v3  # noqa: F401
from backend_pipeline.tests.test_brief_v4_db import v4  # noqa: F401
from backend_pipeline.tests.test_packs_v2_service_db import made, ready  # noqa: F401


@pytest.fixture
def scheduled_pack(ready):  # noqa: F811
    repo, brief, client, headers = ready
    pid = made(repo, brief)
    repo.settings.calendar_enabled = True
    repo.settings.calendar_schedulers = (APPROVER,)
    p = views.detail(repo, pid, APPROVER)
    versions.decide(repo, pid, PackDecisionV2(request_id=str(uuid4()), expected_manifest_hash=p['manifest_hash'],
                                             decision='ready_to_publish'), APPROVER)
    return repo, views.detail(repo, pid, APPROVER), client, headers


def request(p, count=1):
    return Schedule(request_id=str(uuid4()), expected_pack_manifest_hash=p['manifest_hash'], whole_pack=count == 5,
        items=[ScheduleItem(asset_id=a['asset_id'], expected_asset_hash=a['content_hash'],
                            scheduled_for=datetime.now(UTC) + timedelta(days=30+i), display_timezone='UTC')
               for i, a in enumerate(p['pieces'][:count])])


def test_v2_schedule_five_distinct_dates_replay_calendar_and_detail(scheduled_pack):
    repo, p, _, _ = scheduled_pack
    req = request(p, 5)
    saved = calendar.schedule(repo, p['pack_id'], req, APPROVER)
    assert len(saved['entries']) == 5
    assert calendar.schedule(repo, p['pack_id'], req, APPROVER) == saved
    page = calendar.listing(repo, datetime.now(UTC), datetime.now(UTC)+timedelta(days=60))
    assert len(page['items']) == 5 and all(e['effective_status'] == 'scheduled' and not e['warnings'] for e in page['items'])
    assert len({e['scheduled_for'] for e in page['items']}) == 5
    assert {e['slot_key'] for e in page['items']} == {'email', 'carousel', 'reel_1', 'reel_2', 'reel_3'}
    assert all(piece['schedule'] for piece in views.detail(repo, p['pack_id'], APPROVER)['pieces'])


def test_a_listing_checks_a_pack_once_for_all_its_entries(scheduled_pack, monkeypatch):
    repo, p, _, _ = scheduled_pack
    calendar.schedule(repo, p['pack_id'], request(p, 5), APPROVER)
    window = datetime.now(UTC), datetime.now(UTC)+timedelta(days=60)
    before = calendar.listing(repo, *window)['items']
    calls = []
    real = calendar.packs.blockers
    monkeypatch.setattr(calendar.packs, 'blockers', lambda *a, **k: calls.append(a[2]['pack_id']) or real(*a, **k))
    page = calendar.listing(repo, *window)['items']
    assert len(page) == 5 and calls == [p['pack_id']]
    assert [e['warnings'] for e in page] == [e['warnings'] for e in before], 'one check, the same warning on every entry'
    page[0]['warnings'].append('another')
    assert 'another' not in page[1]['warnings']


def test_v2_individual_reschedule_cancel_and_revision_conflict(scheduled_pack):
    repo, p, _, _ = scheduled_pack
    entry = calendar.schedule(repo, p['pack_id'], request(p), APPROVER)['entries'][0]
    assert sum(bool(a['schedule']) for a in views.detail(repo, p['pack_id'], APPROVER)['pieces']) == 1
    req = Reschedule(request_id=str(uuid4()), expected_revision=entry['revision'],
                     scheduled_for=datetime.now(UTC)+timedelta(days=45), display_timezone='UTC')
    moved = calendar.reschedule(repo, entry['calendar_entry_id'], req, APPROVER)['entries'][0]
    assert moved['revision'] == entry['revision'] + 1
    with pytest.raises(ProductionError, match='Another scheduler'):
        calendar.reschedule(repo, entry['calendar_entry_id'], req.model_copy(update={'request_id': str(uuid4())}), APPROVER)
    calendar.cancel(repo, moved['calendar_entry_id'], Cancel(request_id=str(uuid4()), expected_revision=moved['revision']), APPROVER)
    assert not any(a['schedule'] for a in views.detail(repo, p['pack_id'], APPROVER)['pieces'])


def test_v2_invalid_batch_rolls_back_and_stale_manifest_is_rejected(scheduled_pack):
    repo, p, _, _ = scheduled_pack
    req = request(p, 5)
    req.items[-1].expected_asset_hash = 'changed'
    with pytest.raises(ProductionError):
        calendar.schedule(repo, p['pack_id'], req, APPROVER)
    assert not any(a['schedule'] for a in views.detail(repo, p['pack_id'], APPROVER)['pieces'])
    with pytest.raises(ProductionError, match='Pack changed'):
        calendar.schedule(repo, p['pack_id'], request(p).model_copy(update={'expected_pack_manifest_hash': 'stale'}), APPROVER)


def test_v2_review_can_be_scheduled_without_approval_and_permissions_are_preserved(scheduled_pack):
    repo, p, _, _ = scheduled_pack
    with pytest.raises(PermissionError):
        calendar.schedule(repo, p['pack_id'], request(p), 'viewer@example.invalid')
    versions.decide(repo, p['pack_id'], PackDecisionV2(request_id=str(uuid4()), expected_manifest_hash=p['manifest_hash'],
                                                     decision='in_review'), APPROVER)
    saved = calendar.schedule(repo, p['pack_id'], request(p), APPROVER)
    assert len(saved['entries']) == 1
    assert saved['entries'][0]['effective_status'] == 'scheduled'
    assert saved['entries'][0]['warnings'] == []
    current = views.detail(repo, p['pack_id'], APPROVER)
    assert current['state'] == 'in_review' and current['approval_status'] == 'pending'
    with repo.connection() as conn:
        row = model.get(conn, p['pack_id'])
        assert row['approved_hash'] is None
    assert current['pieces'][0]['schedule']


def test_v2_review_blockers_do_not_block_planning_written_pieces_but_unwritten_pieces_are_refused(ready):  # noqa: F811
    repo, brief, _, _ = ready
    pid = made(repo, brief, kinds=('story', 'stance'))
    repo.settings.calendar_enabled = True
    repo.settings.calendar_schedulers = (APPROVER,)
    p = views.detail(repo, pid, APPROVER)
    assert p['state'] == 'in_review' and p['ready_blockers']
    saved = calendar.schedule(repo, pid, request(p), APPROVER)
    assert saved['entries'][0]['effective_status'] == 'needs_review'
    assert saved['entries'][0]['warnings']
    assert not any('marked ready' in warning for warning in saved['entries'][0]['warnings'])
    unwritten = next(a for a in p['pieces'] if a['key'] == 'reel_3')
    req = request(p)
    req.items[0].asset_id = unwritten['asset_id']
    req.items[0].expected_asset_hash = unwritten['content_hash']
    with pytest.raises(ProductionError, match='not been written'):
        calendar.schedule(repo, pid, req, APPROVER)


def test_v2_content_edit_flags_original_schedule_without_moving_it(scheduled_pack):
    repo, p, _, _ = scheduled_pack
    original = calendar.schedule(repo, p['pack_id'], request(p), APPROVER)['entries'][0]
    newer = versions.edit(repo, p['pack_id'], 'email', PackEdit(request_id=str(uuid4()), expected_manifest_hash=p['manifest_hash'],
        changes={'preview': 'A revised preview for the next version.'}), APPROVER)
    page = calendar.listing(repo, datetime.now(UTC), datetime.now(UTC)+timedelta(days=60))
    assert page['items'][0]['calendar_entry_id'] == original['calendar_entry_id']
    assert page['items'][0]['effective_status'] == 'needs_review'
    assert not any(a['schedule'] for a in views.detail(repo, newer['pack_id'], APPROVER)['pieces'])
    with repo.connection() as conn:
        old = model.get(conn, p['pack_id'])
        assert old['manifest_hash'] == p['manifest_hash']


def test_v2_published_piece_is_not_rescheduled_and_its_old_plan_can_be_cancelled(scheduled_pack):
    repo, p, _, _ = scheduled_pack
    old = calendar.schedule(repo, p['pack_id'], request(p), APPROVER)['entries'][0]
    versions.published(repo, p['pack_id'], 'email', PackMarkPublished(request_id=str(uuid4()),
        published_on=datetime.now(UTC).date().isoformat(), channel='email', final_text='Synthetic published email for this test.'), APPROVER)
    with pytest.raises(ProductionError, match='already marked published'):
        calendar.schedule(repo, p['pack_id'], request(p), APPROVER)
    window = datetime.now(UTC), datetime.now(UTC)+timedelta(days=60)
    assert not calendar.listing(repo, *window)['items']
    page = calendar.listing(repo, *window, status='published')
    entry = page['items'][0]
    assert entry['effective_status'] == 'published' and entry['publication']['piece'] == 'email'
    assert entry['warnings'] == [] and not entry['overdue']
    assert entry['status'] == 'scheduled' and entry['scheduled_for'] == datetime.fromisoformat(old['scheduled_for'])
    assert calendar.listing(repo, *window, status='all')['items'] == page['items']
    calendar.cancel(repo, old['calendar_entry_id'], Cancel(request_id=str(uuid4()), expected_revision=old['revision']), APPROVER)
    assert not calendar.listing(repo, datetime.now(UTC), datetime.now(UTC)+timedelta(days=60))['items']


def test_publication_filters_before_pagination_and_keeps_unpublished_siblings(scheduled_pack):
    repo, p, client, headers = scheduled_pack
    saved = calendar.schedule(repo, p['pack_id'], request(p, 5), APPROVER)
    # A past planned time must stop being overdue when manually reported as sent.
    past = datetime.now(UTC)-timedelta(days=1)
    with repo.connection() as conn:
        conn.execute("UPDATE calendar_entries SET scheduled_for=%s WHERE calendar_entry_id=%s",
                     (past, next(entry['calendar_entry_id'] for entry in saved['entries'] if entry['slot_key'] == 'email')))
    window = datetime.now(UTC)-timedelta(days=2), datetime.now(UTC)+timedelta(days=60)
    assert calendar.listing(repo, *window, limit=1)['items'][0]['overdue']
    payload = PackMarkPublished(request_id=str(uuid4()), published_on=datetime.now(UTC).date().isoformat(),
                               channel='email', final_text='The actual email that was manually reported as sent.')
    versions.published(repo, p['pack_id'], 'email', payload, APPROVER)
    versions.published(repo, p['pack_id'], 'email', payload, APPROVER)
    active = []
    cursor = 0
    while cursor is not None:
        page = calendar.listing(repo, *window, limit=1, cursor=cursor)
        active.extend(page['items'])
        cursor = page['next_cursor']
    assert len(active) == 4 and all(entry['slot_key'] != 'email' for entry in active)
    published = calendar.listing(repo, *window, status='published', limit=1)
    assert len(published['items']) == 1 and published['next_cursor'] is None
    complete = published['items'][0]
    assert complete['publication']['by'] == APPROVER and complete['publication']['published_on'] == payload.published_on
    assert not complete['overdue'] and complete['scheduled_for'] == past
    response = client.get('/storage/calendar', headers=headers,
                          params={'from': window[0].isoformat(), 'to': window[1].isoformat(), 'status': 'all'})
    assert response.status_code == 200, response.text
    assert len(response.json()['items']) == 5
    assert sum(entry['effective_status'] == 'published' for entry in response.json()['items']) == 1
    assert client.get('/storage/calendar', headers=headers,
                      params={'from': window[0].isoformat(), 'to': window[1].isoformat(), 'status': 'unknown'}).status_code == 422


def test_generated_pack_filter_combines_legacy_states_without_changing_approval(scheduled_pack):
    repo, p, client, headers = scheduled_pack
    for decision, legacy in [('in_review', 'pending'), ('ready_to_publish', 'approved')]:
        versions.decide(repo, p['pack_id'], PackDecisionV2(request_id=str(uuid4()),
                        expected_manifest_hash=p['manifest_hash'], decision=decision), APPROVER)
        response = client.get('/storage/packs', headers=headers, params={'state': 'generated', 'limit': 1})
        assert response.status_code == 200, response.text
        assert response.json()['total'] == 1 and response.json()['items'][0]['pack_id'] == p['pack_id']
        assert views.detail(repo, p['pack_id'], APPROVER)['approval_status'] == legacy


def test_published_history_keeps_content_warnings_without_becoming_overdue(scheduled_pack):
    repo, p, _, _ = scheduled_pack
    original = calendar.schedule(repo, p['pack_id'], request(p), APPROVER)['entries'][0]
    versions.published(repo, p['pack_id'], 'email', PackMarkPublished(request_id=str(uuid4()),
        published_on=datetime.now(UTC).date().isoformat(), channel='email', final_text='The email that actually went out.'), APPROVER)
    versions.edit(repo, p['pack_id'], 'reel_1', PackEdit(request_id=str(uuid4()), expected_manifest_hash=p['manifest_hash'],
                  changes={'cover_text': 'A revised cover for a later version'}), APPROVER)
    entry = calendar.listing(repo, datetime.now(UTC), datetime.now(UTC)+timedelta(days=60), status='published')['items'][0]
    assert entry['effective_status'] == 'published' and not entry['overdue']
    assert 'A replacement pack exists' in entry['warnings']
    assert entry['scheduled_for'] == datetime.fromisoformat(original['scheduled_for']) and entry['publication']['piece'] == 'email'


def test_retiring_pack_approval_keeps_governing_brief_approval_required(scheduled_pack):
    repo, p, _, _ = scheduled_pack
    calendar.schedule(repo, p['pack_id'], request(p), APPROVER)
    with repo.connection() as conn:
        conn.execute("UPDATE content_briefs SET approval_status='pending',approved_hash=NULL WHERE brief_id=%s",
                     (p['source_brief_id'],))
    page = calendar.listing(repo, datetime.now(UTC), datetime.now(UTC)+timedelta(days=60))
    assert page['items'][0]['effective_status'] == 'needs_review'
    assert 'Governing brief approval has changed' in page['items'][0]['warnings']
    with pytest.raises(ProductionError, match='Governing brief approval has changed'):
        calendar.schedule(repo, p['pack_id'], request(p), APPROVER)


def test_unapproved_pack_schedule_slack_and_manual_publication_end_to_end(scheduled_pack):
    import httpx
    from backend_pipeline import settings_store, slack_schedule_notifications as notify
    repo, p, client, headers = scheduled_pack
    versions.decide(repo, p['pack_id'], PackDecisionV2(request_id=str(uuid4()),
                    expected_manifest_hash=p['manifest_hash'], decision='in_review'), APPROVER)
    with repo.connection() as conn:
        for key, value in [(notify.EMAIL, 'C0BQ6RW7C84'), (notify.SOCIAL, 'C063XKRCJ0M'),
                           (notify.ORIGIN, 'https://atelier.example.test')]:
            settings_store.set_value(conn, key, value, actor=APPROVER)
    notices = []
    def transport(request):
        import json
        body = json.loads(request.content)
        notices.append(body)
        return httpx.Response(200, json={'ok': True, 'channel': body['channel'], 'ts': f'123.{len(notices)}'})
    with httpx.Client(transport=httpx.MockTransport(transport)) as slack:
        kwargs = {'client': slack, 'environ': {'ATELIER_SLACK_BOT_TOKEN': 'fake-test-token'}}
        notify.tick(repo.settings, **kwargs)
        req = request(p, 5).model_dump(mode='json')
        response = client.post(f"/storage/packs/{p['pack_id']}/schedule", headers=headers, json=req)
        assert response.status_code == 200, response.text
        assert all(entry['effective_status'] == 'scheduled' for entry in response.json()['entries'])
        assert notify.tick(repo.settings, **kwargs)['sent'] == 2
        assert len(notices) == 2
        assert all('scheduled for publishing' in body['text'] and 'ready to publish' not in body['text'] for body in notices)
        assert sum(body['text'].count('?piece=') for body in notices) == 5
        mark = client.post(f"/storage/packs/{p['pack_id']}/pieces/email/published", headers=headers,
                           json={'request_id': str(uuid4()), 'published_on': datetime.now(UTC).date().isoformat(),
                                 'channel': 'email', 'final_text': 'The actual email that went out.'})
        assert mark.status_code == 200, mark.text
        assert client.post(f"/storage/packs/{p['pack_id']}/schedule", headers=headers, json=req).status_code == 200
        assert notify.tick(repo.settings, **kwargs)['sent'] == 0 and len(notices) == 2
    window = datetime.now(UTC), datetime.now(UTC)+timedelta(days=60)
    assert len(calendar.listing(repo, *window)['items']) == 4
    completed = calendar.listing(repo, *window, status='published')['items']
    assert len(completed) == 1 and completed[0]['publication']['piece'] == 'email'
    assert not completed[0]['overdue']
    current = views.detail(repo, p['pack_id'], APPROVER)
    assert current['approval_status'] == 'pending' and current['approved_by'] is None
