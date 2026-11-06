import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch, type Mounted } from '../testing/dom';
import { queryKey } from '../api/query';
import type { SavedSchedule, StoredPackV2 } from '../api/types';
import { PACK } from '../testing/packFixtures';
import { BackendCalendar } from './BackendCalendar';
import { MarkPublishedButton, publicationUnavailable } from './PiecePublication';
import { publishedRequest, today } from './packFields';

const entry: SavedSchedule = {
  calendar_entry_id: 'schedule_carousel', asset_id: 'asset_carousel', asset_content_hash: 'hash_carousel', pack_id: PACK.pack_id,
  pack_manifest_hash: PACK.manifest_hash!, scheduled_for: '2026-11-04T05:30:00Z', status: 'scheduled', effective_status: 'scheduled',
  revision: 1, display_timezone: 'Asia/Kolkata', format: 'carousel', slot_key: 'carousel', title: 'When more inquiries are not enough',
  pack_title: PACK.title, week_id: PACK.week_id, warnings: [], overdue: true,
};
const findButton = (within: ParentNode, name: string) => [...within.querySelectorAll<HTMLButtonElement>('button')]
  .find(button => (button.getAttribute('aria-label') ?? button.textContent?.trim()) === name) ?? null;
async function waitFor(ui: Mounted, check: () => boolean) {
  for (let attempt = 0; attempt < 50; attempt++) {
    if (check()) return;
    await ui.settle();
  }
  assert.ok(check(), 'the expected state appeared after asynchronous calendar and pack reads');
}

test('calendar publication persists through a fresh calendar load, updates the pack cache and never approves the pack', async t => {
  let pack = structuredClone(PACK);
  const network = stubFetch((url, options) => {
    if (url === '/api/atelier/calendar/config') return json({ enabled: true, display_timezone: 'Asia/Kolkata', can_schedule: true });
    if (url.startsWith('/api/atelier/calendar?')) {
      assert.equal(new URL(url, 'http://local.test').searchParams.get('status'), 'all');
      const publication = pack.pieces.find(piece => piece.key === 'carousel')?.published[0] ?? null;
      return json({ items: [{ ...entry, publication, effective_status: publication ? 'published' : 'scheduled', overdue: !publication }], next_cursor: null });
    }
    if (url === `/api/atelier/packs/${PACK.pack_id}`) return json(pack);
    if (url.endsWith('/pieces/carousel/published') && options?.method === 'POST') {
      const body = JSON.parse(String(options.body));
      pack = { ...pack, pieces: pack.pieces.map(piece => piece.key === 'carousel' ? { ...piece, published: [{ content_id: 'published_carousel',
        piece: 'carousel', channel: body.channel, published_on: body.published_on, url: body.url, by: 'fixture@example.invalid', at: new Date().toISOString() }] } : piece) };
      return json({ pack_id: PACK.pack_id, piece: 'carousel', content_id: 'published_carousel', state: 'in_review' });
    }
    return json({ detail: 'Not found' }, 404);
  });
  t.after(network.restore);
  const ui = await mount(<BackendCalendar />, { url: '/calendar?month=2026-11' });
  t.after(() => ui.unmount());
  await waitFor(ui, () => !!findButton(ui.container, `Mark ${entry.title} as published`));
  await ui.click(findButton(ui.container, `Mark ${entry.title} as published`));
  const form = document.querySelector('form[aria-label="Mark Carousel published"]')!;
  assert.ok(form, 'the calendar opens the exact scheduled piece');
  await ui.type(form.querySelector<HTMLInputElement>('input[inputmode="url"]')!, 'https://www.instagram.com/p/example/');
  await ui.click(findButton(form, 'Confirm Published'));
  await waitFor(ui, () => ui.text().includes('Published · Manual'));
  const posts = network.calls.filter(call => call.options?.method === 'POST');
  assert.equal(posts.length, 1);
  assert.equal(posts[0].url, '/api/atelier/packs/pack_1/pieces/carousel/published');
  const body = JSON.parse(String(posts[0].options!.body));
  assert.equal(body.channel, 'instagram');
  assert.equal(body.published_on, today());
  assert.equal(body.url, 'https://www.instagram.com/p/example/');
  assert.match(body.final_text, /Slide 1, line one/);
  assert.ok(body.request_id);
  assert.match(ui.text(), /Published · Manual/);
  assert.equal(findButton(ui.container, `Mark ${entry.title} as published`), null, 'no duplicate mark offered');
  const cached = ui.client.getQueryData<StoredPackV2>(queryKey('/packs/{pack_id}', { path: { pack_id: PACK.pack_id } }));
  assert.equal(cached?.pieces.find(piece => piece.key === 'carousel')?.published.length, 1);
  await ui.unmount();
  const fresh = await mount(<BackendCalendar />, { url: '/calendar?month=2026-11' });
  t.after(() => fresh.unmount());
  await waitFor(fresh, () => fresh.text().includes('Published · Manual'));
  assert.match(fresh.text(), /Published · Manual/, 'the badge comes from persisted data, not local state');
});

test('a refused manual mark preserves the form and retries with the same request ID', async t => {
  let accept = false;
  const network = stubFetch((_url, options) => options?.method === 'POST'
    ? accept ? json({ pack_id: PACK.pack_id, content_id: 'published_1' }) : json({ detail: { code: 'not_recorded', message: 'Recording temporarily unavailable' } }, 409)
    : json(PACK));
  t.after(network.restore);
  let saved = 0;
  const ui = await mount(<MarkPublishedButton pack={PACK} piece={PACK.pieces[1]} onSaved={() => saved++} />);
  t.after(() => ui.unmount());
  await ui.click(findButton(ui.container, 'Mark as Published'));
  const form = document.querySelector('form')!;
  const url = form.querySelector<HTMLInputElement>('input[inputmode="url"]')!;
  await ui.type(url, 'https://www.instagram.com/p/kept/');
  await ui.click(findButton(form, 'Confirm Published'));
  assert.match(form.textContent ?? '', /Recording temporarily unavailable/);
  assert.equal(url.value, 'https://www.instagram.com/p/kept/');
  assert.equal(saved, 0);
  accept = true;
  await ui.click(findButton(form, 'Confirm Published'));
  assert.equal(saved, 1);
  const writes = network.calls.filter(call => call.options?.method === 'POST').map(call => JSON.parse(String(call.options!.body)));
  assert.equal(writes.length, 2);
  assert.equal(writes[0].request_id, writes[1].request_id);
});

test('manual publication respects role/version/run restrictions and rejects impossible or future dates', () => {
  const piece = PACK.pieces[0];
  assert.equal(publicationUnavailable(PACK, piece), '');
  assert.match(publicationUnavailable({ ...PACK, can_mark_published: false }, piece), /role/);
  assert.match(publicationUnavailable({ ...PACK, state: 'superseded' }, piece), /newest version/);
  assert.match(publicationUnavailable({ ...PACK, run_active: true }, piece), /finish/);
  const form = { published_on: '2026-02-30', channel: 'email' as const, final_text: 'Published email text', url: '' };
  assert.match((publishedRequest(form) as { error: string }).error, /valid/);
  assert.match((publishedRequest({ ...form, published_on: '9999-01-01' }) as { error: string }).error, /future/);
});
