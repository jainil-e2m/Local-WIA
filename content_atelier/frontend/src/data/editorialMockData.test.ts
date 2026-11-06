import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EDITORIAL_MOCK_IDEAS, mergeEditorialMocks } from './editorialMockData';
import { INITIAL_IDEAS } from './mockData';
import { editorialWeeks, editorialWeekFor } from '../utils/editorialWeeks';
import { advanceEditorialItem } from '../utils/editorialWorkflow';

test('three sourced concepts and 48 archived demos populate weeks with no more than four total', () => {
  assert.equal(EDITORIAL_MOCK_IDEAS.length, 51);
  assert.equal(new Set(EDITORIAL_MOCK_IDEAS.map(i => i.title)).size, 51);
  assert.equal(new Set(EDITORIAL_MOCK_IDEAS.map(i => i.brief.coreInsight)).size, 51);
  const weeks = editorialWeeks(EDITORIAL_MOCK_IDEAS);
  assert.equal(weeks.length, 17);
  assert.equal(weeks[0], '2026-10-19');
  for (const week of weeks) {
    const items = EDITORIAL_MOCK_IDEAS.filter(i => i.editorialWeek === week);
    assert.ok(items.length >= 1 && items.length <= 4);
    for (const idea of items) {
      assert.equal(editorialWeekFor(idea.createdAt!), week);
      assert.equal(idea.isMock, true);
      if (!idea.editorialContext) assert.ok(idea.brief.claimsRequiringConsent[0].includes('fictional'));
    }
  }
  assert.deepEqual([...new Set(weeks.map(week => EDITORIAL_MOCK_IDEAS.filter(i => i.editorialWeek === week).length))].sort(), [1, 2, 3, 4]);
  const current = EDITORIAL_MOCK_IDEAS.filter(i => i.editorialWeek === weeks[0]);
  assert.equal(current.filter(i => i.gate === 'gate1_angle').length, 3);
  assert.equal(current.filter(i => i.editorialContext).length, 3);
  assert.equal(current.filter(i => i.gate === 'gate2_brief').length, 0);
  assert.equal(current.filter(i => i.pack).length, 0);
});

test('generated demo packs have distinct, topic-specific deliverables', () => {
  const items = EDITORIAL_MOCK_IDEAS.filter(i => i.pack);
  assert.ok(items.length > 0);
  assert.equal(new Set(items.map(i => i.pack!.email.body)).size, items.length);
  for (const idea of items) {
    assert.ok(idea.pack!.email.body.includes(idea.title));
    assert.equal(idea.pack!.carousel.title, idea.title);
    assert.equal(idea.pack!.carousel.slides.length, 8);
    assert.equal(idea.pack!.reels.length, 3);
    assert.ok(idea.pack!.captions.linkedIn.includes(idea.title));
    assert.ok(idea.angleApprovedAt && idea.briefApprovedAt);
  }
});

test('seeding removes older mock records and preserves the current saved approvals', () => {
  const seeded = mergeEditorialMocks(INITIAL_IDEAS);
  assert.equal(seeded.length, 3);
  const changed = { ...EDITORIAL_MOCK_IDEAS[0], gate: 'gate2_brief' as const, angleApprovedAt: '2026-10-05T10:00:00Z' };
  const saved = seeded.map(i => i.id === changed.id ? changed : i);
  const reloaded = mergeEditorialMocks(saved);
  assert.deepEqual(reloaded, saved);
  assert.equal(reloaded.find(i => i.id === changed.id), changed);
  for (const idea of INITIAL_IDEAS) assert.equal(reloaded.find(i => i.id === idea.id), undefined);
  for (const week of editorialWeeks(reloaded)) assert.ok(reloaded.filter(i => (i.editorialWeek || editorialWeekFor('2026-10-03T06:30:00Z')) === week).length <= 4);
});

test('cached pre-October mocks are removed without changing current progress or user-created records', () => {
  const current = { ...EDITORIAL_MOCK_IDEAS[0], gate: 'gate2_brief' as const, angleApprovedAt: '2026-10-20T10:00:00.000Z' };
  const user = { ...INITIAL_IDEAS[0], id: 'user-saved-note', isMock: false, editorialWeek: '2026-09-21', createdAt: '2026-09-22T12:00:00Z' };
  const old = EDITORIAL_MOCK_IDEAS.filter(idea => !idea.editorialContext);
  const migrated = mergeEditorialMocks([...INITIAL_IDEAS, ...old, current, user]);
  assert.equal(migrated.length, 4);
  assert.equal(migrated.find(idea => idea.id === current.id), current);
  assert.equal(migrated.find(idea => idea.id === user.id), user);
  assert.ok(!migrated.some(idea => idea.isMock && idea.editorialWeek! < '2026-10-01'));
  assert.deepEqual(mergeEditorialMocks(migrated), migrated);
});
test('the replaced four proposals are removed from cached libraries while current edits and archives remain', () => {
  const library = mergeEditorialMocks(INITIAL_IDEAS);
  const retired = ['fair-comparison', 'buyer-stage', 'human-automation', 'existing-footage'].map(name => ({ ...EDITORIAL_MOCK_IDEAS[0], id: 'mock-fathom-2026-10-05-' + name }));
  const edited = library.map(idea => idea.id === EDITORIAL_MOCK_IDEAS[0].id ? { ...idea, title: 'Saved editorial edit' } : idea);
  const migrated = mergeEditorialMocks([...edited, ...retired]);
  assert.deepEqual(migrated, edited);
  assert.equal(migrated.filter(idea => idea.editorialWeek === '2026-10-19').length, 3);
  assert.ok(!migrated.some(idea => idea.id.startsWith('mock-fathom-2026-10-05-')));
});