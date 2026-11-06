import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EDITORIAL_MOCK_IDEAS, mergeEditorialMocks } from './editorialMockData';
import { INITIAL_IDEAS } from './mockData';
import { editorialWeeks, editorialWeekFor } from '../utils/editorialWeeks';
import { advanceEditorialItem } from '../utils/editorialWorkflow';
import { simulateMockStudio } from '../utils/mockStudioSimulation';

test('four sourced concepts and 48 archived demos populate weeks with no more than four total', () => {
  assert.equal(EDITORIAL_MOCK_IDEAS.length, 52);
  assert.equal(new Set(EDITORIAL_MOCK_IDEAS.map(i => i.title)).size, 52);
  assert.equal(new Set(EDITORIAL_MOCK_IDEAS.map(i => i.brief.coreInsight)).size, 52);
  const weeks = editorialWeeks(EDITORIAL_MOCK_IDEAS);
  assert.equal(weeks.length, 17);
  assert.equal(weeks[0], '2026-10-05');
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
  assert.equal(current.filter(i => i.gate === 'gate1_angle').length, 4);
  assert.equal(current.filter(i => i.editorialContext).length, 4);
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

test('seeding is idempotent and preserves original records and saved demo approvals', () => {
  const seeded = mergeEditorialMocks(INITIAL_IDEAS);
  assert.equal(seeded.length, 56);
  const changed = { ...EDITORIAL_MOCK_IDEAS[0], gate: 'gate2_brief' as const, angleApprovedAt: '2026-10-05T10:00:00Z' };
  const saved = seeded.map(i => i.id === changed.id ? changed : i);
  const reloaded = mergeEditorialMocks(saved);
  assert.deepEqual(reloaded, saved);
  assert.equal(reloaded.find(i => i.id === changed.id), changed);
  for (const idea of INITIAL_IDEAS) assert.equal(reloaded.find(i => i.id === idea.id), idea);
  for (const week of editorialWeeks(reloaded)) assert.ok(reloaded.filter(i => (i.editorialWeek || editorialWeekFor('2026-10-03T06:30:00Z')) === week).length <= 4);
});

test('old eight-per-week mock layout is migrated without erasing saved approvals', () => {
  const saved = EDITORIAL_MOCK_IDEAS.map((idea, index) => ({ ...idea, mockLayoutVersion: undefined, editorialWeek: index < 8 ? '2026-10-05' : idea.editorialWeek }));
  saved[4] = { ...saved[4], gate: 'gate2_brief', angleApprovedAt: '2026-10-05T12:00:00.000Z' };
  const migrated = mergeEditorialMocks([...INITIAL_IDEAS, ...saved]);
  assert.equal(migrated.length, 56);
  assert.equal(migrated.find(i => i.id === saved[4].id)!.angleApprovedAt, saved[4].angleApprovedAt);
  assert.equal(migrated.find(i => i.id === saved[4].id)!.gate, 'gate2_brief');
  const mocks = migrated.filter(i => i.isMock);
  for (const week of editorialWeeks(mocks)) assert.ok(mocks.filter(i => i.editorialWeek === week).length <= 4);
  assert.deepEqual(mergeEditorialMocks(migrated), migrated);
});

test('the old replay week resets once to angles while later individual approvals survive reloads', () => {
  const library = mergeEditorialMocks(INITIAL_IDEAS);
  const ids = new Set(EDITORIAL_MOCK_IDEAS.slice(0, 4).map(idea => idea.id));
  const legacy = simulateMockStudio(library, 'scheduled', '2026-10-06T12:00:00Z').map(idea => ids.has(idea.id) ? { ...idea, mockLayoutVersion: 3 } : idea);
  const saved = legacy.find(idea => ids.has(idea.id))!;
  saved.title = 'Saved angle edit';
  saved.pack!.carousel.title = 'Saved pack edit';
  const migrated = mergeEditorialMocks(legacy);
  for (const item of migrated.filter(idea => ids.has(idea.id))) {
    const original = legacy.find(idea => idea.id === item.id)!;
    assert.equal(item.gate, 'gate1_angle');
    assert.equal(item.angleApprovedAt, undefined);
    assert.equal(item.briefApprovedAt, undefined);
    assert.equal(item.publishingApprovedAt, undefined);
    assert.equal(item.scheduledAt, undefined);
    assert.equal(item.pack, undefined);
    assert.equal(item.mockSimulation, undefined);
    assert.equal(item.brief, original.brief);
    assert.equal(item.editorialContext, original.editorialContext);
    assert.equal(item.title, original.title);
    assert.equal(item.mockContentPack, original.pack);
  }
  for (const item of library.filter(idea => !ids.has(idea.id))) assert.equal(migrated.find(idea => idea.id === item.id), item);
  const first = migrated.find(idea => idea.id === saved.id)!;
  const approved = advanceEditorialItem(first, 'gate2_brief', '2026-10-06T14:00:00Z');
  const progressed = migrated.map(idea => idea.id === approved.id ? approved : idea);
  assert.deepEqual(mergeEditorialMocks(JSON.parse(JSON.stringify(progressed))), JSON.parse(JSON.stringify(progressed)));
  assert.equal(progressed.filter(idea => ids.has(idea.id) && idea.gate === 'gate1_angle').length, 3);
});
