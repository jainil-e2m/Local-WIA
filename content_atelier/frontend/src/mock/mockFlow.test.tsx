import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { mergeEditorialMocks } from '../data/editorialMockData';
import { advanceEditorialItem } from '../utils/editorialWorkflow';
import { resetStudioForDeployment } from '../utils/studioDeployment';
import { approvePackForScheduling, schedulePack } from './utils/publishingSchedule';
import { EditorialHub } from './components/EditorialHub';
import { ContentCalendar, octoberDemoPosts } from './components/ContentCalendar';

const callbacks = { onReview() {}, onUpdateGate() {}, onSwitchSection() {}, onAddAngle() {}, onApprovePack() {}, onSchedule() {} };
const show = (ideas: ReturnType<typeof mergeEditorialMocks>, initialTab: 'angles' | 'briefs' | 'packs' | 'scheduled') => renderToStaticMarkup(<EditorialHub {...callbacks} ideas={ideas} initialTab={initialTab} mode="weekly" />);

test('deployable mock studio advances three supplied concepts through briefs, packs and calendar without backend storage', () => {
  const initial = resetStudioForDeployment(mergeEditorialMocks([]), 'test-deployment');
  assert.equal(initial.length, 3);
  assert.equal((show(initial, 'angles').match(/Awaiting approval<\/span>/g) ?? []).length, 3);
  const briefs = initial.map(idea => advanceEditorialItem(idea, 'gate2_brief', '2026-10-20T06:00:00Z'));
  assert.ok(briefs.every(idea => idea.gate === 'gate2_brief'));
  assert.ok(show(briefs, 'briefs').includes('Budget should follow proof'));
  const packs = briefs.map(idea => advanceEditorialItem(idea, 'gate3_pack', '2026-10-20T06:01:00Z'));
  assert.ok(packs.every(idea => idea.pack?.suppliedCopy?.email && idea.pack?.suppliedCopy?.carousel));
  assert.ok(show(packs, 'packs').includes('Content Packs'));
  const approved = packs.map(idea => approvePackForScheduling(idea, '2026-10-20T06:02:00Z'));
  const scheduled = approved.map(idea => schedulePack(idea, '2026-10-24', '09:00', Date.parse('2026-10-20T06:02:00Z')));
  assert.equal((show(scheduled, 'scheduled').match(/Review pack/g) ?? []).length, 3);
  assert.deepEqual(octoberDemoPosts(scheduled), []);
  const calendar = renderToStaticMarkup(<ContentCalendar ideas={scheduled} onSelectIdea={() => {}} />);
  assert.ok(calendar.includes('14 more'));
  assert.deepEqual(resetStudioForDeployment(JSON.parse(JSON.stringify(scheduled)), 'test-deployment'), JSON.parse(JSON.stringify(scheduled)));
});
