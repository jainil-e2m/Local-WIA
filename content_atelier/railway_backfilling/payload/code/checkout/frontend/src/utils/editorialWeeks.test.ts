import { test } from 'node:test';
import assert from 'node:assert/strict';
import { editorialStageCounts } from './editorialWeeks';
import { INITIAL_IDEAS } from '../data/mockData';
import { advanceEditorialItem } from './editorialWorkflow';
import { editorialWeekFor, editorialWeeks, stampEditorialItem, weekLabel, archiveStageItems, archiveWeekHeading, hasWeeklyCapacity } from './editorialWeeks';

test('week boundaries follow India time, including Sunday-to-Monday rollover', () => {
  assert.equal(editorialWeekFor('2026-10-04T18:29:59Z'), '2026-09-28');
  assert.equal(editorialWeekFor('2026-10-04T18:30:00Z'), '2026-10-05');
  assert.equal(editorialWeekFor('2027-01-01T06:30:00Z'), '2026-12-28');
  assert.match(weekLabel('2026-09-28'), /28 Sept? – 4 Oct, 2026/);
});

test('legacy migration is stable across reloads and retains approval data', () => {
  const first = stampEditorialItem({ ...INITIAL_IDEAS[0], angleApprovedAt: '2026-10-05T00:00:00Z' });
  const reloaded = stampEditorialItem(JSON.parse(JSON.stringify(first)), '2026-11-09T00:00:00Z');
  assert.deepEqual(reloaded, first);
  assert.equal(first.editorialWeek, '2026-09-28');
  assert.equal(first.angleApprovedAt, '2026-10-05T00:00:00Z');
  assert.equal(stampEditorialItem({ ...INITIAL_IDEAS[0], id: 'idea-1791189000000', daysAgo: 'Today' }).editorialWeek, '2026-10-05');
});

test('latest week and previous weeks are disjoint; older approvals keep lineage', () => {
  const old = stampEditorialItem(INITIAL_IDEAS.find(idea => idea.gate === 'gate1_angle')!);
  const newest = stampEditorialItem({ ...old, id: 'new-angle', createdAt: '2026-10-05T06:30:00Z', editorialWeek: undefined });
  const weeks = editorialWeeks([old, newest]);
  assert.deepEqual(weeks, ['2026-10-05', '2026-09-28']);
  const approved = advanceEditorialItem(old, 'gate2_brief', '2026-10-06T06:30:00Z');
  const generated = advanceEditorialItem(approved, 'gate3_pack', '2026-10-07T06:30:00Z');
  assert.equal(generated.editorialWeek, old.editorialWeek);
  assert.equal(generated.createdAt, old.createdAt);
  assert.ok(generated.pack);
  assert.equal([generated, newest].filter(i => i.editorialWeek === weeks[0]).length, 1);
  assert.equal([generated, newest].filter(i => weeks.slice(1).includes(i.editorialWeek!)).length, 1);
});

test('empty libraries have no fabricated previous weeks', () => {
  assert.deepEqual(editorialWeeks([]), []);
});

test('status summaries are exclusive and follow approval transitions', () => {
  const angle = stampEditorialItem(INITIAL_IDEAS.find(i => i.gate === 'gate1_angle')!);
  const brief = advanceEditorialItem(angle, 'gate2_brief', '2026-10-05T10:00:00Z');
  const generated = advanceEditorialItem(brief, 'gate3_pack', '2026-10-05T11:00:00Z');
  const items = [angle, { ...brief, id: 'brief-one' }, { ...brief, id: 'brief-two' }, { ...generated, id: 'pack-one' }];
  assert.deepEqual(editorialStageCounts(items), { waiting: 1, approved: 2, generated: 1 });
  assert.deepEqual(editorialStageCounts([generated]), { waiting: 0, approved: 0, generated: 1 });
  assert.deepEqual(editorialStageCounts([generated, generated]), { waiting: 0, approved: 0, generated: 1 });
});

test('the four-concept cap counts all stages and approval does not free capacity', () => {
  const source = stampEditorialItem(INITIAL_IDEAS.find(i => i.gate === 'gate1_angle')!);
  const library = Array.from({ length: 4 }, (_, index) => ({ ...source, id: `capacity-${index}` }));
  assert.equal(hasWeeklyCapacity(library.slice(0, 3), source.editorialWeek!), true);
  assert.equal(hasWeeklyCapacity(library, source.editorialWeek!), false);
  const progressed = library.map(i => advanceEditorialItem(advanceEditorialItem(i, 'gate2_brief', '2026-10-05T10:00:00Z'), 'gate3_pack', '2026-10-05T11:00:00Z'));
  assert.equal(hasWeeklyCapacity(progressed, source.editorialWeek!), false);
  assert.equal(hasWeeklyCapacity(progressed, '2026-10-05'), true);
});

test('archive approvals move items between queues without duplicating completed stages', () => {
  const angle = stampEditorialItem(INITIAL_IDEAS.find(idea => idea.gate === 'gate1_angle')!);
  const brief = advanceEditorialItem(angle, 'gate2_brief', '2026-10-06T06:30:00Z');
  const pack = advanceEditorialItem(brief, 'gate3_pack', '2026-10-07T06:30:00Z');
  assert.equal(archiveStageItems([angle], 'angles').length, 1);
  assert.equal(archiveStageItems([brief], 'angles').length, 0);
  assert.equal(archiveStageItems([brief], 'briefs').length, 1);
  assert.equal(archiveStageItems([pack], 'briefs').length, 0);
  assert.equal(archiveStageItems([pack], 'packs').length, 1);
  assert.equal(pack.editorialWeek, angle.editorialWeek);
  assert.equal(archiveWeekHeading('2026-09-07'), 'Month Sept · Week 1');
  assert.equal(archiveWeekHeading('2026-09-28'), 'Month Sept · Week 4');
});
