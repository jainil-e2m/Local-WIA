import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderScreen, CLIENT } from '../testing/render';
import { json, mount, stubFetch } from '../testing/dom';
import { DOCUMENT_LIST, seed } from '../testing/fixtures';
import { EXTRACTION_HEALTH } from '../testing/momentFixtures';
import { createQueryClient, queryKey } from '../api/query';
import { DocumentsOverview, ExtractionHealthBody, ExtractionHealthPanel, waited } from './ExtractionHealth';
import { SourcesView } from './SourcesView';

const visible = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ').replace(/ ,/g, ',');
const health = (data: unknown = EXTRACTION_HEALTH) => renderScreen(<ExtractionHealthPanel />, { seed: [seed('/documents/extraction-health', null, data)] });

test('2.F3: processing health is folded at the bottom and gives the included, read, waiting and failed counts, with no scene or quote figures', () => {
  const html = health();
  const text = visible(html);
  assert.match(html, /<details[^>]*aria-label="Processing health"/);
  assert.ok(!/<details[^>]* open/.test(html), 'folded until opened');
  for (const expected of ['Processing health · 3 failed', 'Documents included 100', 'Read 85', 'Waiting 9', 'Failed 3']) assert.ok(text.includes(expected), expected);
  for (const hidden of ['Quotes matched', 'no scenes', 'moments', '85%', 'Not applicable 3']) assert.ok(!text.includes(hidden), hidden);
});

test('2.F3: the document that has waited longest is named with how long it has waited, and links to it', () => {
  const html = health();
  assert.match(visible(html), /Waiting longest: Office hours in March \(Fathom\), for 9 days\./);
  assert.match(html, /href="\/sources\/documents\/t_11"[^>]*>Office hours in March/);
  assert.match(visible(health({ ...EXTRACTION_HEALTH, oldest_pending: null })), /No document is waiting\./);
});

test('2.F3: failed documents are listed with the reason, the source and when, each linking to its document', () => {
  const html = health();
  const text = visible(html);
  assert.ok(text.includes('3 documents failed'));
  assert.ok(text.includes('Long strategy call · Zoom · failed 18 Oct 2026'));
  assert.ok(text.includes('The model answered with something that was not usable'));
  assert.ok(text.includes('Slack thread about pricing · Slack · date not recorded'));
  assert.ok(text.includes('No reason was recorded.'));
  assert.ok(text.includes('The 2 most recent are listed.'));
  assert.match(html, /href="\/sources\/documents\/t_9"[^>]*>Long strategy call/);
  assert.match(visible(health({ ...EXTRACTION_HEALTH, failed: [], failed_total: 0 })), /No document has failed/);
  const many = { ...EXTRACTION_HEALTH, failed: Array.from({ length: 8 }, (_, i) => ({ ...EXTRACTION_HEALTH.failed[0], document_id: `t_f${i}`, title: `Failing call ${i}` })), failed_total: 8 };
  const crowded = health(many);
  assert.ok(visible(crowded).includes('Show 3 more'));
});

test('2.F3: nothing included yet is said plainly', () => {
  const none = { ...EXTRACTION_HEALTH, totals: { ...EXTRACTION_HEALTH.totals, included_documents: 0 }, by_source_type: [] };
  assert.match(visible(health(none)), /No documents are included yet, so there is nothing to read\./);
});

test('2.F3: how long a document has waited reads in hours and days', () => {
  assert.equal(waited(0.2), 'less than an hour');
  assert.equal(waited(1), '1 hour');
  assert.equal(waited(5.9), '5 hours');
  assert.equal(waited(47.9), '47 hours');
  assert.equal(waited(220.5), '9 days');
});

test('2.F3: loading and a failed read are shown, and a failed read can be retried', async t => {
  assert.match(visible(renderScreen(<ExtractionHealthPanel />)), /Checking processing…/);
  let fail = true;
  const network = stubFetch(() => fail ? json({ detail: 'Storage schema is not ready; apply the explicit migration' }, 503) : json(EXTRACTION_HEALTH));
  t.after(network.restore);
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  const ui = await mount(<ExtractionHealthPanel />, { client });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Storage schema is not ready/);
  assert.ok(ui.container.querySelector('[role="alert"]'));
  fail = false;
  await ui.click([...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Retry') ?? null);
  await ui.settle();
  assert.match(ui.text(), /Documents included/);
  assert.ok(!ui.container.querySelector('[role="alert"]'));
  assert.equal(network.calls[0].url, '/api/atelier/documents/extraction-health');
});

test('2.F3: the health sits on the Sources view below the list of documents, and the list works if the health cannot be shown', async t => {
  const quiet = console.error; console.error = () => {};
  t.after(() => { console.error = quiet; });
  const both = renderScreen(<SourcesView tab="documents"><DocumentsOverview /></SourcesView>, {
    url: '/sources/documents', seed: [seed('/documents/extraction-health', null, EXTRACTION_HEALTH), seed('/documents', { limit: 50, offset: 0 }, DOCUMENT_LIST)],
  });
  const text = visible(both);
  assert.ok(text.includes('Processing health') && text.includes('Client call with Maple Venue'));
  assert.ok(text.indexOf('Processing health') > text.indexOf('Client call with Maple Venue'), 'the health is below the list');
});

test('2.F3: a health answer the screen cannot read leaves the list of documents working', async t => {
  const quiet = console.error; console.error = () => {};
  t.after(() => { console.error = quiet; });
  const network = stubFetch(() => json({ nonsense: true }));
  t.after(network.restore);
  const client = createQueryClient();
  client.setQueryData(queryKey('/documents/extraction-health', null), { nonsense: true });
  client.setQueryData(queryKey('/documents', { limit: 50, offset: 0 }), DOCUMENT_LIST);
  const ui = await mount(<DocumentsOverview />, { url: '/sources/documents', client });
  t.after(() => ui.unmount());
  assert.match(ui.text(), /Processing health could not be shown/);
  assert.match(ui.text(), /Client call with Maple Venue/);
});

test('2.F3, S.F3: a session that is not a team session does not load the extraction health', async t => {
  const network = stubFetch(url => url.includes('extraction-health') ? json(EXTRACTION_HEALTH) : json(DOCUMENT_LIST));
  t.after(network.restore);
  const client = await mount(<SourcesView tab="documents"><DocumentsOverview /></SourcesView>, { url: '/sources/documents', auth: CLIENT });
  t.after(() => client.unmount());
  await client.settle();
  assert.match(client.text(), /Sources are available to the internal team/);
  assert.equal(network.calls.length, 0, "no request was made");
  const team = await mount(<SourcesView tab="documents"><DocumentsOverview /></SourcesView>, { url: '/sources/documents' });
  t.after(() => team.unmount());
  await team.settle();
  assert.match(team.text(), /Documents included/);
  assert.ok(network.calls.some(call => call.url === '/api/atelier/documents/extraction-health'));
});

test('2.F3: the body renders from the API answer alone', () => {
  assert.ok(visible(renderScreen(<ExtractionHealthBody health={EXTRACTION_HEALTH as never} />)).includes('Documents included 100'));
});
