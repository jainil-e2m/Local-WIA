import { test } from 'node:test';
import assert from 'node:assert/strict';
import { INITIAL_IDEAS } from '../data/mockData';
import { advanceEditorialItem, reviveEditorialItem } from './editorialWorkflow';
import { mergeEditorialMocks } from '../data/editorialMockData';

const original = INITIAL_IDEAS.find(idea => idea.gate === 'gate1_angle')!;
const approvedAt = '2026-10-05T12:00:00.000Z';

test('revival moves archived angles and briefs to the same waiting stage, retaining lineage through generation', () => {
  const current = { ...original, id: 'current', editorialWeek: '2026-10-05' };
  for (const gate of ['gate1_angle', 'gate2_brief'] as const) {
    const archived = { ...original, id: `old-${gate}`, gate, editorialWeek: '2026-09-07', pack: undefined };
    const revived = reviveEditorialItem(archived, [current, archived], approvedAt);
    assert.equal(revived.gate, gate);
    assert.equal(revived.editorialWeek, current.editorialWeek);
    assert.equal(revived.originalEditorialWeek, archived.editorialWeek);
    assert.equal(revived.revivedAt, approvedAt);
    assert.equal(revived.pack, undefined);
    assert.equal(revived.brief, archived.brief);
    assert.equal(reviveEditorialItem(revived, [current, revived], approvedAt), revived);
    const brief = gate === 'gate1_angle' ? advanceEditorialItem(revived, 'gate2_brief', approvedAt) : revived;
    const pack = advanceEditorialItem(brief, 'gate3_pack', approvedAt);
    assert.ok(pack.pack);
    assert.equal(pack.originalEditorialWeek, archived.editorialWeek);
    assert.equal(pack.revivedAt, approvedAt);
    assert.equal(mergeEditorialMocks([current, revived]).find(item => item.id === revived.id)?.editorialWeek, current.editorialWeek);
  }
});

test('revival respects the four-concept cap without losing the archived item', () => {
  const current = Array.from({ length: 4 }, (_, index) => ({ ...original, id: `current-${index}`, editorialWeek: '2026-10-05' }));
  const archived = { ...original, editorialWeek: '2026-09-07' };
  assert.throws(() => reviveEditorialItem(archived, [...current, archived], approvedAt), /four concepts/);
  assert.equal(archived.editorialWeek, '2026-09-07');
});

test('approvals preserve the source angle and brief, then generate five linked contents', () => {
  const brief = advanceEditorialItem(original, 'gate2_brief', approvedAt);
  assert.equal(brief.id, original.id);
  assert.equal(brief.title, original.title);
  assert.deepEqual(brief.research, original.research);
  assert.equal(brief.angleApprovedAt, approvedAt);
  assert.equal(brief.pack, undefined);
  const generated = advanceEditorialItem(brief, 'gate3_pack', approvedAt);
  assert.equal(generated.id, original.id);
  assert.deepEqual(generated.brief, brief.brief);
  assert.equal(generated.briefApprovedAt, approvedAt);
  assert.ok(generated.pack?.email.body);
  assert.ok(generated.pack?.carousel.slides.length);
  assert.equal(generated.pack?.reels.length, 3);
  assert.equal(original.gate, 'gate1_angle');
});

test('pack generation cannot bypass angle approval or overwrite an approved pack', () => {
  assert.equal(advanceEditorialItem(original, 'gate3_pack', approvedAt), original);
  const brief = advanceEditorialItem(original, 'gate2_brief', approvedAt);
  const generated = advanceEditorialItem(brief, 'gate3_pack', approvedAt);
  assert.equal(advanceEditorialItem(generated, 'gate3_pack', approvedAt), generated);
  assert.equal(advanceEditorialItem(generated, 'gate2_brief', approvedAt), generated);
});

test('approving one item retains all unused angles and prior library entries', () => {
  const library = INITIAL_IDEAS.map(idea => idea.id === original.id ? advanceEditorialItem(idea, 'gate2_brief', approvedAt) : idea);
  assert.equal(library.length, INITIAL_IDEAS.length);
  for (const idea of INITIAL_IDEAS.filter(idea => idea.id !== original.id)) assert.equal(library.find(item => item.id === idea.id), idea);
  const restored = JSON.parse(JSON.stringify(library));
  assert.deepEqual(restored.map((item: typeof original) => ({ id: item.id, gate: item.gate, brief: item.brief, pack: item.pack, angleApprovedAt: item.angleApprovedAt })), library.map(item => ({ id: item.id, gate: item.gate, brief: item.brief, pack: item.pack, angleApprovedAt: item.angleApprovedAt })));
});
