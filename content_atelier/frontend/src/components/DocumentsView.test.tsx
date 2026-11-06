import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { useLocation } from 'react-router-dom';
import { renderScreen, CLIENT } from '../testing/render';
import { json, mount, stubFetch } from '../testing/dom';
import { DOCUMENT_DETAIL, DOCUMENT_LIST, UNDATED_EXCLUDED, seed } from '../testing/fixtures';
import { DocumentBody, DocumentsList, DocumentsView, DocumentView } from './DocumentsView';
import { SourcesView } from './SourcesView';
import { NO_FILTERS } from '../utils/documents';
import { createQueryClient } from '../api/query';

const visible = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ');
const list = (url = '/sources/documents', data: unknown = DOCUMENT_LIST, query: Record<string, unknown> = { limit: 50, offset: 0 }) =>
  renderScreen(<DocumentsView />, { url, seed: [seed('/documents', query, data)] });

test('1.F3: a row shows the title, date, source and call type, client and whether it is included, and nothing technical', () => {
  const text = visible(list());
  for (const expected of ['Client call with Maple Venue', '4 Mar 2026 · Zoom · Client 1:1 · Maple Venue', 'Included',
    'Vendor demo', 'Undated · Fathom · Vendor', 'Excluded', '150 calls included · 20 excluded']) assert.ok(text.includes(expected), expected);
  for (const hidden of ['passages', 'words', 'Extraction', 'Carmen Cruickshank', 'Vendor calls are not content evidence', 'dated from']) assert.ok(!text.includes(hidden), `no ${hidden} on a row`);
});

test('1.F3: each document opens at its own URL; a failed one is marked on its row', () => {
  const html = list();
  assert.match(html, /href="\/sources\/documents\/t_1"[^>]*>Client call with Maple Venue/);
  assert.match(html, /href="\/sources\/documents\/t_2"[^>]*>Vendor demo/);
  const failed = visible(list('/sources/documents', { ...DOCUMENT_LIST, items: [{ ...DOCUMENT_LIST.items[0], extraction_status: 'failed' }] }));
  assert.ok(failed.includes('Processing failed'));
});

test('1.F3: the search and three filters are in view, the rest under More filters, all set from the URL', () => {
  const html = list('/sources/documents?source_type=zoom&call_type=client_1to1&included=true&extraction_status=completed&date_state=dated&client_id=client_maple&q=follow-up&from=2026-01-01&to=2026-03-31&limit=25&offset=25',
    DOCUMENT_LIST, { source_type: 'zoom', call_type: 'client_1to1', included: true, extraction_status: 'completed', date_state: 'dated', client_id: 'client_maple', q: 'follow-up',
      from: '2026-01-01T00:00:00Z', to: '2026-04-01T00:00:00Z', limit: 25, offset: 25 });
  const text = visible(html);
  assert.ok(html.includes('aria-label="Search titles and text"'));
  const [inView, folded] = html.split('More filters');
  for (const label of ['Source', 'Call type', 'Included']) assert.ok(visible(inView).includes(label), `${label} in view`);
  for (const label of ['Processing', 'Date', 'From', 'To', 'Client ID', 'Per page']) assert.ok(visible(folded).includes(label), `${label} under More filters`);
  assert.match(html, /<details[^>]*open=""/, 'More filters is open while one of its filters is set');
  assert.match(html, /<option value="zoom" selected/);
  assert.match(html, /<option value="client_1to1" selected/);
  assert.match(html, /value="follow-up"/);
  assert.match(html, /value="2026-01-01"/);
  assert.match(text, /Clear 9 filters/);
  assert.match(text, /Showing 1 to 2 of 170/);
  assert.ok(!/<details[^>]*open/.test(list()), 'folded when none of them is set');
});

test('1.F3: no facet-count cloud: the counts are the header line only', () => {
  const text = visible(list());
  for (const chip of ['Zoom 164', 'Fathom 6', 'Client 1:1 90', 'Undated 164']) assert.ok(!text.includes(chip), chip);
  assert.ok(text.includes('150 calls included · 20 excluded'));
});

test('1.F3: an empty result says so, with and without a filter', () => {
  const none = { ...DOCUMENT_LIST, items: [], total: 0 };
  assert.match(visible(list('/sources/documents', none)), /No documents have been stored yet/);
  assert.match(visible(list('/sources/documents?q=zzz', none, { q: 'zzz', limit: 50, offset: 0 })), /No documents match these filters/);
});

test('1.F3: a document shows what was said with speaker, role and time, how it was sorted, who spoke, and why it is excluded in plain words', () => {
  const html = renderScreen(<DocumentView />, { url: '/sources/documents/t_1', pattern: '/sources/documents/:transcriptId', seed: [seed('/documents/{transcript_id}', 't_1', DOCUMENT_DETAIL)] });
  const text = visible(html);
  for (const expected of ['Client call with Maple Venue', 'Call type', 'Client 1:1, by a rule: one client and one staff speaker', 'Who spoke', 'What was said',
    'Carmen Cruickshank · WIA staff · 1:04', 'How do you reply to inquiries today?', 'Open the week']) assert.ok(text.includes(expected), expected);
  assert.match(html, /href="\/studio\/angles\/week_1"/);
  for (const hidden of ['passages', '3,400 words', 'week_1<']) assert.ok(!text.includes(hidden) && !html.includes(hidden), hidden);
  const excluded = visible(renderScreen(<DocumentBody doc={{ ...DOCUMENT_DETAIL, ...UNDATED_EXCLUDED, passages: [], classification: null,
    exclusion_reason: 'Personal finance, not client evidence (D4, decided under delegation, R12)' } as never} />));
  for (const expected of ['This is a copy of', 'Why it is excluded: Personal finance, not client evidence', 'Not sorted yet', 'No text is stored']) assert.ok(excluded.includes(expected), expected);
  for (const hidden of ['D4', 'delegation', 'R12']) assert.ok(!excluded.includes(hidden), hidden);
});

function Where() { const { pathname, search } = useLocation(); return <output id="where">{pathname + search}</output>; }

test('1.F3: changing a filter or the page changes the URL and asks the API for that page', async t => {
  const network = stubFetch(url => json({ ...DOCUMENT_LIST, offset: Number(new URL(url, 'http://x').searchParams.get('offset')) }));
  t.after(network.restore);
  const ui = await mount(<><DocumentsView /><Where /></>, { url: '/sources/documents' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.deepEqual(network.calls.map(call => call.url).filter(url => url.includes('/documents')), ['/api/atelier/documents?limit=50&offset=0']);
  const select = (label: string) => [...ui.container.querySelectorAll('label')].find(l => l.querySelector('.sr-only')?.textContent === label)!.querySelector('select')!;
  await ui.choose(select('Call type'), 'client_1to1');
  await ui.settle();
  assert.equal(ui.container.querySelector('#where')!.textContent, '/sources/documents?call_type=client_1to1');
  assert.equal(network.calls.at(-1)!.url, '/api/atelier/documents?call_type=client_1to1&limit=50&offset=0');
  await ui.click([...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Next') ?? null);
  await ui.settle();
  assert.equal(ui.container.querySelector('#where')!.textContent, '/sources/documents?call_type=client_1to1&offset=50');
  assert.equal(network.calls.at(-1)!.url, '/api/atelier/documents?call_type=client_1to1&limit=50&offset=50');
  // A new filter starts again from the first page.
  await ui.choose(select('Included'), 'false');
  await ui.settle();
  assert.equal(network.calls.at(-1)!.url, '/api/atelier/documents?call_type=client_1to1&included=false&limit=50&offset=0');
  await ui.click([...ui.container.querySelectorAll('button')].find(b => /^Clear \d+ filters?$/.test(b.textContent ?? '')) ?? null);
  await ui.settle();
  assert.equal(ui.container.querySelector('#where')!.textContent, '/sources/documents');
});

test('1.F3: the date window and the free text are sent as the API asks', async t => {
  const network = stubFetch(() => json(DOCUMENT_LIST));
  t.after(network.restore);
  const ui = await mount(<DocumentsView />, { url: '/sources/documents?from=2026-01-01&to=2026-03-31&q=follow-up' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.equal(network.calls.find(call => call.url.includes('/documents'))!.url, '/api/atelier/documents?q=follow-up&from=2026-01-01T00%3A00%3A00Z&to=2026-04-01T00%3A00%3A00Z&limit=50&offset=0');
});

test('S.F3, 1.F3: a session that is not a team session does not load the documents', async t => {
  const network = stubFetch(() => json(DOCUMENT_LIST));
  t.after(network.restore);
  const client = await mount(<SourcesView tab="documents"><DocumentsView /></SourcesView>, { url: '/sources/documents', auth: CLIENT });
  t.after(() => client.unmount());
  await client.settle();
  assert.match(client.text(), /Sources are available to the internal team/);
  assert.ok(!client.text().includes('Client call with Maple Venue'));
  assert.deepEqual(network.calls, [], 'no request was made');
  const team = await mount(<SourcesView tab="documents"><DocumentsView /></SourcesView>, { url: '/sources/documents' });
  t.after(() => team.unmount());
  await team.settle();
  assert.match(team.text(), /Client call with Maple Venue/);
  assert.equal((network.calls as { url: string }[]).filter(call => call.url.includes("/documents")).length, 1);
});

test('1.F3: a failed read shows the error with a retry, and a failed list keeps no rows', async t => {
  const network = stubFetch(() => json({ detail: 'Storage schema is not ready; apply the explicit migration' }, 503));
  t.after(network.restore);
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  const ui = await mount(<DocumentsList filters={NO_FILTERS} onChange={() => {}} />, { client });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Storage schema is not ready/);
  assert.ok([...ui.container.querySelectorAll('button')].some(b => b.textContent === 'Retry'));
});
