import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { useLocation } from 'react-router-dom';
import { renderScreen, CLIENT } from '../testing/render';
import { json, mount, stubFetch } from '../testing/dom';
import { seed } from '../testing/fixtures';
import {
  MOMENT, MOMENT_DNU, MOMENT_FACETS, MOMENT_INTERNAL, MOMENT_LIST, MOMENT_STAFF, MOMENT_UNVERIFIED, SEARCH_RESPONSE, TOPICS,
} from '../testing/momentFixtures';
import { MomentsLedger, MomentsShell, MomentsView } from './MomentsLedger';
import { NO_MOMENT_FILTERS, facetQuery, readMomentFilters } from '../utils/moments';
import { createQueryClient } from '../api/query';

const visible = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');
const seeds = [seed('/moments/facets', {}, MOMENT_FACETS), seed('/topics', { query: { status: 'active', limit: 200 } }, TOPICS)];
const ledger = (url = '/moments', data: unknown = MOMENT_LIST, query: Record<string, unknown> = { limit: 25, offset: 0 }) =>
  renderScreen(<MomentsView />, { url, seed: [seed('/moments', query, data), ...seeds] });

function Where() { const { pathname, search } = useLocation(); return <output id="where">{pathname + search}</output>; }
const urlOf = (ui: { container: HTMLElement }) => new URL(ui.container.querySelector('#where')!.textContent!, 'http://x');
const path = (url: string) => new URL(url, 'http://x');
const field = (ui: { container: HTMLElement }, label: string) => (label === 'Search the moments'
  ? ui.container.querySelector('input[aria-label="Search the moments"]')
  : [...ui.container.querySelectorAll('label')].find(l => l.querySelector('.sr-only')?.textContent === label
    || [...l.childNodes].some(node => node.nodeType === 3 && node.textContent === label))!.querySelector('select, input'))! as HTMLSelectElement & HTMLInputElement;
const button = (ui: { container: HTMLElement }, label: RegExp | string) => [...ui.container.querySelectorAll('button')].find(b => typeof label === 'string' ? b.textContent === label : label.test(b.textContent ?? '')) ?? null;

/** The API as the screen meets it: the list, the counts, the topics and the search. */
function api(answer: (route: string, params: URLSearchParams, options?: RequestInit) => unknown = () => undefined) {
  return stubFetch((url, options) => {
    const parsed = path(url), route = parsed.pathname.replace('/api/atelier', '');
    const custom = answer(route, parsed.searchParams, options);
    if (custom instanceof Response) return custom;
    if (custom !== undefined) return json(custom);
    if (route === '/moments/facets') return json(MOMENT_FACETS);
    if (route === '/moments') return json({ ...MOMENT_LIST, offset: Number(parsed.searchParams.get('offset')) });
    if (route === '/topics') return json(TOPICS);
    if (route === '/search') return json(SEARCH_RESPONSE);
    return json({ detail: 'Not found' }, 404);
  });
}
const listCalls = (network: { calls: { url: string }[] }) => network.calls.filter(call => path(call.url).pathname === '/api/atelier/moments');

test('2.F1: a moment card is the quote, "speaker · date · client", the consent and "Read the moment", nothing more', () => {
  const html = ledger();
  const text = visible(html);
  for (const expected of ['“We reply to every inquiry within five minutes and our bookings doubled.”', 'Sam Maple · 4 Mar 2026 · Maple Venue', 'Cleared for naming',
    'Anonymise', 'Date not recorded', 'Showing 1 to 2 of 40', '40 moments from calls and threads']) assert.ok(text.includes(expected), expected);
  assert.match(html, /href="\/moments\/m_reply"[^>]*>Read the moment/);
  for (const hidden of ['Maple Venue answers every inquiry within five minutes', 'The scene', 'Topics:', 'Open the call', 'Client:', '(Client)', 'Human line'])
    assert.ok(!text.includes(hidden), `no ${hidden} on a card`);
  assert.ok(!/passage|offset|extractor|embedding|pipeline/i.test(text), 'no pipeline words on the surface');
});

test('2.F1: the real ledger reads the API, not the built-in examples', () => {
  for (const file of ['MomentsLedger.tsx', 'MomentDetail.tsx', 'ExtractionHealth.tsx']) {
    const source = readFileSync(new URL(`./${file}`, import.meta.url), 'utf8');
    assert.ok(!/from '\.\.\/(data\/|types\/atelier|testing\/)/.test(source), `${file} imports no fixtures`);
  }
  assert.ok(!visible(ledger()).includes('Sample data'));
  assert.ok(!visible(ledger()).includes('Elena Rostova'), 'none of the built-in examples');
});

test('2.F1: the consent of a moment is named in plain words for every status, with what it asks of the person', () => {
  const all = { items: [MOMENT, MOMENT_STAFF, MOMENT_INTERNAL, MOMENT_DNU], total: 4, limit: 25, offset: 0 };
  const html = ledger('/moments?consent_status=all', all, { consent_status: 'cleared,anonymise,internal_only,do_not_use', limit: 25, offset: 0 });
  const text = visible(html);
  for (const expected of ['Cleared for naming', 'Anonymise', 'Internal only', 'Do not use']) assert.ok(text.includes(expected), expected);
  for (const [status, hint] of [['cleared', 'The client can be named alongside this quote.'], ['anonymise', 'Use it without naming the client or their business.'],
    ['internal_only', 'For the team only. It is not for public content.'], ['do_not_use', 'Nothing from this client may be used.']]) {
    assert.match(html, new RegExp(`data-consent-badge="${status}"[^>]*title="${hint.replace('.', '\\.')}"|title="${hint.replace('.', '\\.')}"[^>]*data-consent-badge="${status}"`), status);
  }
  assert.match(html, /data-consent="do_not_use"/);
  assert.match(text, /Shown because you asked for it\. Nothing from this client may be used\./);
  assert.ok(!visible(ledger()).includes('Shown because you asked for it'), 'a list the reviewer did not widen has no do-not-use mark');
});

test('2.F1: the consent shown is the backend\'s: the screen does not recompute it from the quote or the speaker', () => {
  // A staff-spoken line marked cleared, and a client line marked do not use, are shown exactly as the API says.
  const odd = { items: [{ ...MOMENT_STAFF, consent_status: 'cleared' }, { ...MOMENT, moment_id: 'm_odd', consent_status: 'do_not_use' }], total: 2, limit: 25, offset: 0 };
  const html = ledger('/moments', odd);
  assert.match(html, /data-consent="cleared"/);
  assert.match(html, /data-consent="do_not_use"/);
});

test('2.F1: the search, type, client and consent are in view and the rest under More filters, all set from the URL, with no count clouds', () => {
  const url = '/moments?q=reply&unverified=1&client_id=client_maple&source_type=zoom&call_type=client_1to1&speaker_role=client&moment_type=result&consent_status=cleared&topic_id=topic_followup&from=2026-01-01&to=2026-03-31&limit=50&offset=50';
  const html = renderScreen(<MomentsView />, { url, seed: [seed('/moments/facets', facetQuery(readMomentFilters(new URL(url, 'http://x').searchParams)), MOMENT_FACETS), seeds[1]] });
  const [inView, folded] = html.split('More filters');
  for (const label of ['Type', 'Client', 'Consent']) assert.ok(visible(inView).includes(label), `${label} in view`);
  assert.ok(inView.includes('aria-label="Search the moments"'));
  for (const label of ['Who spoke', 'Source', 'Call type', 'Topic', 'From', 'To', 'Per page', 'Show quotes not matched to the call']) assert.ok(visible(folded).includes(label), `${label} under More filters`);
  assert.match(html, /value="reply"/);
  assert.match(html, /<option value="client_maple" selected="">Maple Venue<\/option>/);
  assert.match(html, /<option value="zoom" selected="">Zoom<\/option>/);
  assert.match(html, /<option value="client_1to1" selected="">Client 1:1<\/option>/);
  assert.match(html, /<option value="client" selected="">Client<\/option>/);
  assert.match(html, /<option value="cleared" selected="">Cleared for naming<\/option>/);
  assert.match(html, /<option value="topic_followup" selected="">Inquiry follow-up speed<\/option>/);
  assert.match(html, /<option value="result" selected="">Result<\/option>/);
  assert.match(html, /value="2026-01-01"/);
  assert.match(html, /<option value="50" selected="">50/);
  assert.match(html, /type="checkbox" checked=""/);
  assert.match(visible(html), /Clear 11 filters/);
  // All twelve moment types are offered.
  for (const type of ['Result', 'Testimonial', 'Story', 'Objection', 'Decision', 'Tension', 'How it works', 'Observation', 'Teaching', 'Soundbite', 'Data point', 'Question']) assert.ok(html.includes(`>${type}</option>`), type);
});

test('2.F1: no facet-count cloud: the choices carry no counts', () => {
  const text = visible(ledger());
  for (const chip of ['Result 12', 'Maple Venue (25)', 'Cleared for naming (12)']) assert.ok(!text.includes(chip), chip);
});

test('2.F1: changing a filter or the page changes the URL and asks the API for that page', async t => {
  const network = api();
  t.after(network.restore);
  const ui = await mount(<><MomentsView /><Where /></>, { url: '/moments' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.deepEqual(listCalls(network).map(call => call.url), ['/api/atelier/moments?limit=25&offset=0']);
  assert.ok(network.calls.some(call => call.url === '/api/atelier/moments/facets'), 'the counts are read');
  assert.ok(network.calls.some(call => call.url.startsWith('/api/atelier/topics?')), 'the topics are read');
  const lastList = () => Object.fromEntries(path(listCalls(network).at(-1)!.url).searchParams);

  await ui.choose(field(ui, 'Client'), 'client_maple');
  await ui.settle();
  assert.equal(urlOf(ui).search, '?client_id=client_maple');
  assert.deepEqual(lastList(), { client_id: 'client_maple', limit: '25', offset: '0' });

  await ui.choose(field(ui, 'Type'), 'result');
  await ui.choose(field(ui, 'Who spoke'), 'client');
  await ui.choose(field(ui, 'Source'), 'zoom');
  await ui.choose(field(ui, 'Call type'), 'client_1to1');
  await ui.choose(field(ui, 'Topic'), 'topic_followup');
  await ui.choose(field(ui, 'Consent'), 'do_not_use');
  await ui.type(field(ui, 'From'), '2026-01-01');
  await ui.type(field(ui, 'To'), '2026-03-31');
  await ui.settle();
  assert.deepEqual(Object.fromEntries(urlOf(ui).searchParams), {
    client_id: 'client_maple', moment_type: 'result', speaker_role: 'client', source_type: 'zoom', call_type: 'client_1to1', topic_id: 'topic_followup', consent_status: 'do_not_use',
    from: '2026-01-01', to: '2026-03-31',
  });
  assert.deepEqual(lastList(), {
    client_id: 'client_maple', source_type: 'zoom', call_type: 'client_1to1', speaker_role: 'client', moment_type: 'result', consent_status: 'do_not_use', topic_id: 'topic_followup',
    from: '2026-01-01T00:00:00Z', to: '2026-04-01T00:00:00Z', limit: '25', offset: '0',
  });
  // The counts follow the same filters (without a page).
  const facetCall = path(network.calls.filter(call => path(call.url).pathname === '/api/atelier/moments/facets').at(-1)!.url).searchParams;
  assert.equal(facetCall.get('client_id'), 'client_maple');
  assert.equal(facetCall.get('limit'), null);

  await ui.choose(field(ui, 'Consent'), 'all');
  await ui.settle();
  assert.equal(lastList().consent_status, 'cleared,anonymise,internal_only,do_not_use');

  await ui.click(button(ui, 'Next'));
  await ui.settle();
  assert.equal(urlOf(ui).searchParams.get('offset'), '25');
  assert.equal(lastList().offset, '25');
  assert.equal(lastList().moment_type, 'result', 'moving between pages keeps the filter');
  // A new filter starts again from the first page.
  await ui.choose(field(ui, 'Source'), 'fathom');
  await ui.settle();
  assert.equal(urlOf(ui).searchParams.get('offset'), null);
  assert.equal(lastList().offset, '0');
  // Choosing every type again clears it.
  await ui.choose(field(ui, 'Type'), '');
  await ui.settle();
  assert.equal(urlOf(ui).searchParams.get('moment_type'), null);
  await ui.click(button(ui, /^Clear \d+ filters?$/));
  await ui.settle();
  assert.equal(urlOf(ui).pathname + urlOf(ui).search, '/moments');
});

test('2.F1: with no words, moments are listed by date from the API and nothing is searched', async t => {
  const network = api();
  t.after(network.restore);
  const ui = await mount(<MomentsView />, { url: '/moments' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.ok(!network.calls.some(call => call.url.endsWith('/search')), 'no search request');
  assert.ok(listCalls(network).length >= 1);
});

test('2.F1: words are searched by wording and meaning with the same filters, and each match says why it was found', async t => {
  const network = api();
  t.after(network.restore);
  const ui = await mount(<><MomentsView /><Where /></>, { url: '/moments?client_id=client_maple&moment_type=result&consent_status=cleared&from=2026-01-01&to=2026-03-31' });
  t.after(() => ui.unmount());
  await ui.settle();
  const listBefore = listCalls(network).length;
  await ui.type(field(ui, 'Search the moments'), 'how fast should we reply');
  await ui.click(button(ui, 'Search'));
  await ui.settle();
  assert.equal(urlOf(ui).searchParams.get('q'), 'how fast should we reply');
  const searches = network.calls.filter(call => call.url === '/api/atelier/search');
  assert.equal(searches.length, 1);
  assert.equal(searches[0].options?.method, 'POST');
  assert.deepEqual(JSON.parse(String(searches[0].options?.body)), {
    text: 'how fast should we reply', k: 50, scope: 'moments',
    filters: { client_id: 'client_maple', moment_type: ['result'], consent_status: ['cleared'], date_from: '2026-01-01T00:00:00Z', date_to: '2026-04-01T00:00:00Z' },
  });
  assert.equal(listCalls(network).length, listBefore, 'the list is not read while words are searched');
  const text = ui.text();
  assert.ok(!/Matches your words and their meaning|Close in meaning/.test(text), 'no matching detail on the cards');
  assert.match(text, /Best 2 matches for “how fast should we reply”/);
  assert.match(text, /We reply to every inquiry within five minutes/);
  // The counts leave the words out, so they are the ledger's under the other filters.
  const facets = path(network.calls.filter(call => path(call.url).pathname === '/api/atelier/moments/facets').at(-1)!.url).searchParams;
  assert.equal(facets.get('q'), null);
});

test('2.F1: a search that could not use meaning, or withheld a match, says so', async t => {
  const network = api(route => route === '/search' ? { ...SEARCH_RESPONSE, query_embedding_status: 'unavailable', query_embedding_detail: 'no key', hits_withheld: 2 } : undefined);
  t.after(network.restore);
  const ui = await mount(<MomentsView />, { url: '/moments?q=reply' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Matching by meaning is not available right now, so this search looked for your words only\./);
  assert.match(ui.text(), /2 matches were left out because the quote could not be checked against the call\./);
  assert.ok(!ui.text().includes('no key'), 'the reason code is not on the surface');
});

test('2.F1: a search is paged from its best matches, and its pages keep the words in the URL', async t => {
  const many = { ...SEARCH_RESPONSE, hits: Array.from({ length: 12 }, (_, i) => ({ ...SEARCH_RESPONSE.hits[0], moment: { ...MOMENT, moment_id: `m_${i}`, quote: `Quote number ${i}` } })) };
  const network = api(route => route === '/search' ? many : undefined);
  t.after(network.restore);
  const ui = await mount(<><MomentsView /><Where /></>, { url: '/moments?q=reply&limit=10' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Showing 1 to 10 of 12/);
  assert.ok(!ui.text().includes('Quote number 10'));
  await ui.click(button(ui, 'Next'));
  await ui.settle();
  assert.match(ui.text(), /Showing 11 to 12 of 12/);
  assert.match(ui.text(), /Quote number 10/);
  assert.equal(urlOf(ui).search, '?q=reply&limit=10&offset=10');
  assert.equal(network.calls.filter(call => call.url === '/api/atelier/search').length, 1, 'paging does not search again');
});

test('2.F1: unverified quotes are hidden unless asked for; asking adds them to the list, marked, and finds them by their words', async t => {
  const network = api((route, params) => route === '/moments' && params.get('quote_verified') === 'any'
    ? { items: [MOMENT, MOMENT_UNVERIFIED], total: 2, limit: 25, offset: 0 } : undefined);
  t.after(network.restore);
  const ui = await mount(<><MomentsView /><Where /></>, { url: '/moments' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.equal(path(listCalls(network).at(-1)!.url).searchParams.get('quote_verified'), null, 'the default asks for verified quotes only');
  assert.ok(!ui.text().includes('I think we said something like three weeks.'));
  assert.ok(!ui.text().includes('Quote not verified'));
  assert.equal((field(ui, 'Show quotes not matched to the call') as HTMLInputElement).checked, false);

  await ui.click(field(ui, 'Show quotes not matched to the call'));
  await ui.settle();
  assert.equal(urlOf(ui).search, '?unverified=1');
  assert.equal(path(listCalls(network).at(-1)!.url).searchParams.get('quote_verified'), 'any');
  assert.ok(ui.text().includes('I think we said something like three weeks.'));
  assert.match(ui.text(), /Quote not verified/);

  // With words as well, unverified quotes are found by their words in the list (search only covers verified ones).
  const before = network.calls.filter(call => call.url === '/api/atelier/search').length;
  await ui.type(field(ui, 'Search the moments'), 'weeks');
  await ui.click(button(ui, 'Search'));
  await ui.settle();
  assert.equal(network.calls.filter(call => call.url === '/api/atelier/search').length, before);
  const params = path(listCalls(network).at(-1)!.url).searchParams;
  assert.equal(params.get('q'), 'weeks');
  assert.equal(params.get('quote_verified'), 'any');
});

test('2.F1: do not use moments are not requested unless the reviewer chooses them', async t => {
  const network = api();
  t.after(network.restore);
  const ui = await mount(<MomentsView />, { url: '/moments' });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.equal(path(listCalls(network).at(-1)!.url).searchParams.get('consent_status'), null, 'the API\'s default leaves them out');
  assert.ok([...field(ui, 'Consent').options].some(option => option.text === 'All except do not use'), 'the default choice says so');
  assert.ok([...field(ui, 'Consent').options].some(option => option.text === 'Everything, including do not use'));
});

test('2.F1: an empty ledger says so, with and without a filter', () => {
  const none = { ...MOMENT_LIST, items: [], total: 0 };
  assert.match(visible(ledger('/moments', none)), /No moments have been found yet/);
  const filtered = visible(ledger('/moments?client_id=client_maple', none, { client_id: 'client_maple', limit: 25, offset: 0 }));
  assert.match(filtered, /No moments match these filters\./);
});

test('2.F1: while the first answer is awaited the screen says it is loading, and a search says it is searching', () => {
  assert.match(visible(renderScreen(<MomentsView />, { url: '/moments' })), /Loading the moments…/);
  assert.match(visible(renderScreen(<MomentsView />, { url: '/moments?q=reply' })), /Searching the moments…/);
});

test('2.F1: a failed read shows the error with a retry, and reading again recovers', async t => {
  let fail = true;
  const network = api((route) => route === '/moments' && fail ? json({ detail: 'Storage schema is not ready; apply the explicit migration' }, 503) : undefined);
  t.after(network.restore);
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  const ui = await mount(<MomentsLedger filters={NO_MOMENT_FILTERS} onChange={() => {}} />, { client });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Storage schema is not ready/);
  assert.ok(ui.container.querySelector('[role="alert"]'));
  assert.ok(!ui.text().includes('Showing'), 'a failed list keeps no rows');
  fail = false;
  await ui.click(button(ui, 'Retry'));
  await ui.settle();
  assert.match(ui.text(), /We reply to every inquiry within five minutes/);
  assert.ok(!ui.container.querySelector('[role="alert"]'));
});

test('2.F1: a failed search shows the error, not an empty result', async t => {
  const network = api(route => route === '/search' ? json({ detail: 'Search is unavailable' }, 503) : undefined);
  t.after(network.restore);
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  const ui = await mount(<MomentsLedger filters={{ ...NO_MOMENT_FILTERS, q: 'reply' }} onChange={() => {}} />, { client });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Search is unavailable/);
  assert.ok(!ui.text().includes('No moments'));
});

test('2.F1: the page is the team\'s: another session sees a notice and makes no request', async t => {
  const network = api();
  t.after(network.restore);
  const client = await mount(<MomentsShell><MomentsView /></MomentsShell>, { url: '/moments', auth: CLIENT });
  t.after(() => client.unmount());
  await client.settle();
  assert.match(client.text(), /Moments are available to the internal team/);
  assert.equal(network.calls.length, 0, "no request was made");
  const team = await mount(<MomentsShell><MomentsView /></MomentsShell>, { url: '/moments' });
  t.after(() => team.unmount());
  await team.settle();
  assert.match(team.text(), /We reply to every inquiry within five minutes/);
  assert.ok(network.calls.length >= 3);
});
