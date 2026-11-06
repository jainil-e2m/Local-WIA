import '../../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../../testing/dom';
import { renderScreen } from '../../testing/render';
import { ME_APPROVER, REVIEW, WEEK, seed, shell } from '../../testing/fixtures';
import { ContentPacks } from '../ContentPacks';
import { SQLWeeklyAngles } from '../SQLWeeklyAngles';
import { isArchived, weekOption } from './WeekPicker';

const LIVE = { ...WEEK, week_id: 'week_2026-10-19', week_start: '2026-10-19', week_end: '2026-10-25' };
const ARCHIVED = { ...WEEK, week_id: 'week_2026-10-26', week_start: '2026-10-26', week_end: '2026-11-01', status: 'archived' };
import type { Mounted } from '../../testing/dom';
/** The Week picker's choices: it is the mockup's themed select, so it is opened, read and closed again. */
const options = async (ui: Mounted, name = 'Week') => {
  const box = ui.container.querySelector(`[role="combobox"][aria-label="${name}"]`);
  await ui.click(box);
  const listed = [...document.querySelectorAll('[role="option"]')].map(o => o.textContent ?? '');
  await ui.click(box);
  return listed;
};

test('archived weeks: an archived week is marked as such in a picker', () => {
  assert.equal(isArchived(ARCHIVED), true);
  assert.equal(isArchived(LIVE), false);
  assert.match(weekOption(ARCHIVED), / \(archived\)$/);
  assert.ok(!weekOption(LIVE).includes('archived'));
});

test('archived weeks: the Content Packs library has no week picker and no archived toggle; it groups the packs by week', async t => {
  const network = stubFetch(url => url.includes('/packs') ? json({ items: [], total: 0, limit: 20, offset: 0 }) : json({ detail: 'Not found' }, 404));
  t.after(network.restore);
  const ui = await mount(<ContentPacks base="/packs" />, { url: '/packs' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.equal(ui.container.querySelector('[role="combobox"][aria-label="Week"]'), null, 'no week picker');
  assert.ok(!ui.text().includes('Show archived weeks'), 'no archived toggle');
  assert.ok(!network.calls.some(c => c.url.includes('include_archived')), 'archived weeks are never asked for');
  assert.ok(ui.container.querySelector('[role="combobox"][aria-label="State"]'), 'one state filter');
  assert.ok((await options(ui, 'State')).includes('All packs'));
});

test('archived weeks: the Weekly Studio opens the latest live week, and an archived week opened by its link says it is archived', () => {
  const latest = renderScreen(<SQLWeeklyAngles />, { url: '/studio/angles', pattern: '/studio/angles',
    seed: [...shell(), seed('/weeks', undefined, [LIVE]), seed('/me', undefined, ME_APPROVER),
      seed('/weeks/{week_id}', { path: { week_id: LIVE.week_id } }, { ...REVIEW, week: LIVE })] });
  assert.ok(latest.includes('aria-label="Angles awaiting approval"') && !latest.includes('This week is archived'), 'the latest live week is shown');
  const old = renderScreen(<SQLWeeklyAngles />, { url: `/studio/angles/${ARCHIVED.week_id}`, pattern: '/studio/angles/:weekId',
    seed: [...shell(), seed('/weeks', undefined, [LIVE]), seed('/weeks/{week_id}', { path: { week_id: ARCHIVED.week_id } }, { ...REVIEW, week: ARCHIVED })] });
  assert.ok(old.includes('This week is archived: its work was superseded or did not meet the standard.'));
});
