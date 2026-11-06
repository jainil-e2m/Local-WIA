import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Route, Routes } from 'react-router-dom';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { seed, shell } from '../testing/fixtures';
import { PACK, PLAN, SUMMARY } from '../testing/packFixtures';
import { createQueryClient, queryKey } from '../api/query';
import type { WeekPackPlanV2 } from '../api/types';
import { ContentPacks } from './ContentPacks';

/* NP.F4, done when: the view renders GET /weeks/{id}/pack-plan (the allocation with read-only dates, the week's checks, the
   bank, what is published, the export), and marking a piece published moves it out of the plan. The plan is the API's,
   computed on read; the screen shows what the latest read says. */

const texts = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
const WEEK = 'week_2026-10-26';

test('NP.F4: the week view renders the proposed allocation, the week\'s checks, its packs, the bank and the export', () => {
  const html = renderScreen(<ContentPacks base="/studio/packs" />, { url: `/studio/packs/week/${WEEK}`, pattern: '/studio/packs/week/:weekId', seed: [...shell({ packs: true }),
    seed('/weeks/{week_id}/pack-plan', { path: { week_id: WEEK } }, PLAN), seed('/packs', { query: { week_id: WEEK, limit: 100 } }, { items: [SUMMARY], total: 1 })] });
  const visible = texts(html);
  for (const text of ["The week's plan", 'For the publishing week of Nov 2, 2026 to Nov 8, 2026', 'Proposed for the week', 'nothing is scheduled or posted by the system',
    'Monday, Nov 2, 2026', 'Instagram 1', 'Reel 1 · The reply that lost the tour', 'No offer ask', 'Tuesday, Nov 3, 2026', 'Tuesday email', 'Email · Why we read the reply first', 'Reply',
    'Wednesday, Nov 4, 2026', 'Carousel · Inquiry season', 'Friday, Nov 6, 2026', 'Instagram 3', 'Nothing proposed', 'No CONVERT pack this week: choose the strongest piece.', "The week's offer ask",
    'Checks across the week (1)', 'Check: Two covers this week open with the same words.', "This week's packs (2)", 'Generated', 'Inquiry season',
    'The bank (1)', 'Reel 2 · Leads are not the problem', 'suggested in 2 weeks', 'A second Reel from the same pack', 'Published (0)', 'Nothing from this week is marked published yet'])
    assert.ok(visible.includes(text), text);
  // The slots in date order, each linking to its piece on its pack.
  const order = ['instagram_1', 'tuesday_email', 'instagram_2', 'instagram_3'].map(slot => html.indexOf(`data-slot="${slot}"`));
  assert.ok(order.every((at, i) => at > 0 && (i === 0 || at > order[i - 1])), 'Monday, Tuesday, Wednesday, Friday');
  assert.match(html, /href="\/studio\/packs\/pack_1\?piece=reel_1"/);
  // The export downloads the week's pack document through the relay, as Markdown and as a Word file (NP.B12).
  assert.match(html, /<a[^>]*href="\/api\/atelier\/weeks\/week_2026-10-26\/packs\.md"[^>]*download=""|<a[^>]*download=""[^>]*href="\/api\/atelier\/weeks\/week_2026-10-26\/packs\.md"/);
  assert.match(html, /<a[^>]*href="\/api\/atelier\/weeks\/week_2026-10-26\/packs\.docx"[^>]*download=""[^>]*>Download as Word \(\.docx\)<\/a>/);
  assert.ok(!/<input|<textarea|<select/.test(html.slice(html.indexOf('Proposed for the week'), html.indexOf('Checks across the week'))), 'the allocation is read only');
});

test('NP.F4: a piece marked published on its pack leaves the week\'s plan and shows under Published on the next read', async t => {
  let published = false;
  const after: WeekPackPlanV2 = { ...PLAN, slots: PLAN.slots.map(s => s.slot === 'instagram_1'
    ? { ...s, pack_id: 'pack_1', piece: 'reel_2', piece_label: 'Reel 2', title: 'Leads are not the problem' } : s), bank: [] };
  const network = stubFetch((url, options) => {
    if (options?.method === 'POST' && url === '/api/atelier/packs/pack_1/pieces/reel_1/published') { published = true; return json({ pack_id: 'pack_1', piece: 'reel_1', content_id: 'content_1', state: 'in_review' }); }
    if (url === `/api/atelier/weeks/${WEEK}/pack-plan`) return json(published ? after : PLAN);
    if (url.startsWith('/api/atelier/packs?')) return json({ items: [{ ...SUMMARY, pieces: SUMMARY.pieces.map(p => ({ ...p, published: published && p.key === 'reel_1' })) }], total: 1 });
    if (url === '/api/atelier/packs/pack_1') return json(PACK);
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of shell({ packs: true })) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<Routes>
    <Route path="/studio/packs/week/:weekId" element={<ContentPacks base="/studio/packs" />} />
    <Route path="/studio/packs/:packId" element={<ContentPacks base="/studio/packs" />} />
  </Routes>, { url: `/studio/packs/week/${WEEK}`, client });
  t.after(() => ui.unmount());
  await ui.settle();
  const plan = () => ui.container.querySelector('[aria-label="Proposed for the week"]')?.textContent ?? '';
  assert.match(plan(), /Reel 1 · The reply that lost the tour/);
  // Open the piece from the plan, mark it published on its pack, and come back to the week.
  await ui.click(ui.container.querySelector('a[href="/studio/packs/pack_1?piece=reel_1"]'));
  await ui.settle();
  const reel = ui.container.querySelector('#pack-piece-panel-reel_1')!;
  assert.ok(!reel.hasAttribute('hidden'), 'the pack opens at the piece');
  await ui.click([...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Mark as Published') ?? null);
  const dialog = document.querySelector('[role="dialog"]')!;
  await ui.click([...dialog.querySelectorAll('button')].find(b => b.textContent === 'Confirm Published') ?? null);
  await ui.settle();
  const mark = network.calls.find(c => c.options?.method === 'POST')!;
  assert.equal(JSON.parse(String(mark.options!.body)).channel, 'instagram');
  // The pack page no longer links to the week's plan; the plan is opened again at its own address, and read again.
  assert.equal(ui.container.querySelector(`a[href="/studio/packs/week/${WEEK}"]`), null, 'no link to the week\'s plan on the pack page');
  await ui.unmount();
  const fresh = createQueryClient();
  for (const [route, args, data] of shell({ packs: true })) fresh.setQueryData(queryKey(route as never, args), data);
  const week = await mount(<ContentPacks base="/studio/packs" />, { url: `/studio/packs/week/${WEEK}`, pattern: '/studio/packs/week/:weekId', client: fresh });
  t.after(() => week.unmount());
  await week.settle();
  const again = () => week.container.querySelector('[aria-label="Proposed for the week"]')?.textContent ?? '';
  assert.doesNotMatch(again(), /Reel 1 · The reply that lost the tour/, 'the published piece left the plan');
  assert.match(again(), /Reel 2 · Leads are not the problem/);
  assert.match(week.container.querySelector('[aria-label="Published"]')?.textContent ?? '', /Published \(1\).*Why we read the reply first · Reel 1/);
});

test('NP.F4: the plan is read again on Refresh', async t => {
  let reads = 0;
  const network = stubFetch(url => {
    if (url === `/api/atelier/weeks/${WEEK}/pack-plan`) { reads++; return json(PLAN); }
    if (url.startsWith('/api/atelier/packs?')) return json({ items: [], total: 0 });
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of shell({ packs: true })) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<ContentPacks base="/studio/packs" />, { url: `/studio/packs/week/${WEEK}`, pattern: '/studio/packs/week/:weekId', client });
  t.after(() => ui.unmount());
  await ui.settle();
  const before = reads;
  await ui.click([...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Refresh') ?? null);
  await ui.settle();
  assert.ok(reads > before);
});
