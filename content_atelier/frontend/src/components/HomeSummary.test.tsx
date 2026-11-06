import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { CycleOverview } from '../api/schema';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { ME_APPROVER, SUMMARY } from '../testing/fixtures';
import { HomePage } from '../app/HomePage';
import { HomeSummary, packReason, summaryLines } from './HomeSummary';

const summary = SUMMARY as unknown as CycleOverview;
const words = (s: CycleOverview, options = { packs: true, approver: true }) => summaryLines(s, options).map(l => l.text);
const visible = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ');
// What a team screen must not show (the owner, 25 October 2026): ids, figures in USD, raw states, model or version names.
const TECHNICAL = /run_|angle_|pack_|week_\d|USD|\d+\.\d\d|waiting_for_review|wia-kb|strategist_v|America\/Chicago\)|extraction/;

test('6.F2: Home is a few plain lines, each linking to where it is acted on', () => {
  const lines = summaryLines(summary, { packs: true, approver: true });
  assert.deepEqual(lines.map(l => [l.text, l.to ?? null]), [
    ['3 angles waiting for your review', '/studio/angles'],
    ['“Answer the first inquiry within the hour”, held until October 24, is due back for your review', '/studio/angles/week_2026-10-12/angle_held'],
    ['2 briefs waiting for approval', '/studio/briefs'],
    ['2 content packs generated', '/packs?state=generated'],
    ['“The tour that sold itself” is waiting: this week\'s packs budget is spent', '/packs/pack_waiting'],
    ['1 content pack being written', null],
    ['Next cycle: Sunday 1 November at 4:00 a.m. Chicago time', null],
    ['2 problems need attention', '/sources/alerts'],
  ]);
  for (const line of lines.map(l => l.text)) assert.ok(!TECHNICAL.test(line), line);
  assert.ok(!lines.some(l => l.text.includes('spend') || l.text.includes('spending')), 'no spending line on Home: limits are under Alerts and costs');
  assert.ok(!lines.some(l => l.text.startsWith('Latest cycle') || l.key === 'latest'), 'a cycle ready for review is the lines above, not a line of its own');
});

test('6.F2: one week of angles links to that week; no spend line for anyone; the cycle is said only while it is not ready', () => {
  const oneWeek = { ...summary, waiting: { ...summary.waiting, cards_at_gate_1: { count: 1, who: 'an approver', by_week: [{ week_id: 'week_2026-10-19', n: 1 }] } } };
  assert.equal(summaryLines(oneWeek, { packs: true, approver: true })[0].to, '/studio/angles/week_2026-10-19');
  assert.equal(summaryLines(oneWeek, { packs: true, approver: true })[0].text, '1 angle waiting for your review');
  const reached = { ...summary, spend: { ...summary.spend, limits_close: ['content packs'], limits_reached: ['briefs', 'weekly cycle'] } } as CycleOverview;
  for (const approver of [true, false]) assert.ok(!words(reached, { packs: true, approver }).some(t => /spend|limit/.test(t)), `no spend line (approver: ${approver})`);
  const running = { ...summary, latest_cycle: { ...summary.latest_cycle!, status: 'running' } } as CycleOverview;
  const line = summaryLines(running, { packs: true, approver: true }).find(l => l.key === 'latest');
  assert.equal(line?.text, "This week's cycle is in progress");
  assert.equal(line?.to, '/studio/angles/week_2026-10-19');
  for (const status of ['waiting_for_review', 'completed', 'partially_completed']) {
    const ready = { ...summary, latest_cycle: { ...summary.latest_cycle!, status } } as CycleOverview;
    assert.ok(!summaryLines(ready, { packs: true, approver: true }).some(l => l.key === 'latest'), `${status}: no cycle line`);
  }
  const utc = { ...summary, next_cycle: { ...summary.next_cycle, timezone: 'UTC', at: '2026-11-01T10:00:00Z' } } as CycleOverview;
  assert.ok(words(utc).includes('Next cycle: Sunday 1 November at 10:00 a.m. UTC'));
});

test('6.F2: a quiet week says nothing waits; the schedule off says how a cycle starts; packs are left out without their flag', () => {
  const quiet = {
    ...summary,
    waiting: { cards_at_gate_1: { count: 0, who: 'an approver', by_week: [] }, held_cards_due_back: { count: 0, who: 'an approver', cards: [] },
      briefs_at_gate_2: { count: 0, who: 'an approver' }, packs_in_review: { count: 3, who: 'an editor or an approver' }, packs_ready: 0,
      packs_with_the_system: { finishing: 0, waiting: 0, reasons: [] } },
    latest_cycle: { ...summary.latest_cycle!, status: 'partially_completed', started_from: 'app' },
    next_cycle: { enabled: false, at: null, timezone: 'America/Chicago', window: null },
    alerts: { open: 0, errors: 0 },
  } as CycleOverview;
  const lines = words(quiet, { packs: false, approver: false });
  assert.equal(lines[0], 'Nothing is waiting for you');
  assert.ok(!lines.some(t => t.includes('content pack')), 'the packs screens are off');
  assert.ok(!lines.some(t => t.includes('cycle is') || t.includes('started by the schedule')), 'a finished cycle has no line of its own');
  assert.ok(lines.includes('The cycle does not start by itself: an approver starts it from the Weekly Studio'));
  assert.ok(!lines.some(t => t.includes('attention')), 'nothing needs attention: no line about it');
  const stopped = { ...quiet, sources: { ...quiet.sources, connections: [{ ...quiet.sources.connections[0], health: 'error', error_summary: 'HTTP 401 from the provider' }] } };
  assert.ok(words(stopped).includes('Call collection has stopped and needs attention'), 'without the error text');
  assert.ok(words({ ...quiet, latest_cycle: null }, { packs: false, approver: false }).every(t => !t.startsWith("This week's cycle")));
});

test('6.F2: a pack\'s reason is its first sentence; a failed step is said without the failure\'s own text', () => {
  assert.equal(packReason("This week's packs budget is spent. It renews on Monday."), "this week's packs budget is spent");
  assert.equal(packReason('A step failed and can be tried again: HTTPStatusError 502 from the provider'), 'a step failed and can be tried again');
});

test('6.F2: a failed first read offers a retry; an answer of another shape renders nothing from it', () => {
  const props = { onRetry: () => {}, onOpenStudio: () => {}, packs: true, approver: true };
  assert.ok(visible(renderScreen(<HomeSummary summary={undefined} error="Weekly storage is unavailable." {...props} />)).includes('Weekly storage is unavailable. Retry'));
  assert.ok(renderScreen(<HomeSummary summary={[{ week_id: 'w' }]} error="" {...props} />).includes('Loading this week'));
  const html = renderScreen(<HomeSummary summary={summary} error="" {...props} />);
  assert.ok(html.includes('href="/studio/briefs" data-discover="true">Review<span aria-hidden="true"> →</span></a>') && html.includes('Open the Weekly Studio'));
});

test('6.F2: Home reads GET /summary alone (not the weeks, a week and the briefs), and keeps the summary above the calendar when it is on', async t => {
  let flags = { briefs: true, packs: true, calendar: false, context: false };
  const network = stubFetch(url => url.endsWith('/summary') ? json(SUMMARY) : url.endsWith('/flags') ? json(flags) : url.endsWith('/me') ? json(ME_APPROVER)
    : url.includes('/calendar/config') ? json({ enabled: true, display_timezone: 'America/Chicago', worker_ready: true })
    : url.includes('/calendar') ? json({ items: [], next_cursor: null }) : json({ detail: 'Not found' }, 404));
  t.after(network.restore);
  const ui = await mount(<HomePage />, { url: '/home' });
  await ui.settle();
  assert.ok(ui.text().includes('3 angles waiting for your review') && !ui.text().includes('spend'));
  const read = network.calls.map(c => c.url.replace('/api/atelier', '').split('?')[0]);
  assert.ok(read.includes('/summary'));
  for (const old of ['/weeks', '/briefs']) assert.ok(!read.includes(old), `Home no longer composes ${old}`);
  await ui.unmount();

  flags = { ...flags, calendar: true };
  const withCalendar = await mount(<HomePage />, { url: '/home' });
  await withCalendar.settle();
  await withCalendar.settle();
  const html = withCalendar.container.innerHTML;
  assert.ok(html.includes('aria-label="This week"'), 'the summary is still shown');
  const calendar = Math.max(html.indexOf('aria-label="Previous month"'), html.indexOf('Loading saved calendar'), html.indexOf('No scheduled content in this month.'));
  assert.ok(calendar > 0 && html.indexOf('aria-label="This week"') < calendar, 'the summary comes first, the calendar below it');
  await withCalendar.unmount();
});
