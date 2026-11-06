import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Route, Routes } from 'react-router-dom';
import { renderScreen } from '../testing/render';
import { json, mount, stubFetch } from '../testing/dom';
import { ME_APPROVER, seed } from '../testing/fixtures';
import { CITATION, MOMENT, MOMENT_DETAIL, MOMENT_FACETS, MOMENT_LIST, TOPICS } from '../testing/momentFixtures';
import { MomentBody, MomentView, backTarget } from './MomentDetail';
import { MomentsView } from './MomentsLedger';

const visible = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');
const PATTERN = '/moments/:momentId';
const detail = (data: unknown = MOMENT_DETAIL, id = 'm_reply') => renderScreen(<MomentView />, {
  url: `/moments/${id}`, pattern: PATTERN, seed: [seed('/moments/{moment_id}', { path: { moment_id: id } }, data), seed('/me', undefined, ME_APPROVER), seed('/topics', { query: { status: 'active', limit: 200 } }, TOPICS)],
});
const VIEWER = { ...ME_APPROVER, role: 'viewer', roles: ['viewer'], can: { ...ME_APPROVER.can, edit_cards: false } };

test('2.F2: a moment opens from its own URL after a refresh: a fresh mount at the path reads that moment from the API', async t => {
  const network = stubFetch(url => url.startsWith('/api/atelier/moments/m_reply') ? json(MOMENT_DETAIL) : url.endsWith('/me') ? json(ME_APPROVER) : json(TOPICS));
  t.after(network.restore);
  const ui = await mount(<MomentView />, { url: '/moments/m_reply', pattern: PATTERN });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.ok(network.calls.some(call => call.url === '/api/atelier/moments/m_reply'), 'the moment is read by the id in the URL');
  const text = ui.text();
  for (const expected of ['Maple Venue', 'The scene', 'Maple Venue answers every inquiry within five minutes', 'Sam describes the change since the follow-up routine began.', 'Said about the spring season only',
    '“We reply to every inquiry within five minutes and our bookings doubled.”', 'Sam Maple', 'Client', '4 Mar 2026, 12:05 into the call', 'Open the recording (at 12:05)']) assert.ok(text.includes(expected), expected);
  assert.equal(ui.container.querySelector('mark')!.textContent, MOMENT.quote, 'the quote is highlighted');
});

test('2.F2: the quote is highlighted inside the passage that holds it, among the passages around it, each with speaker, role and time', () => {
  const html = detail();
  const text = visible(html);
  assert.match(html, /<mark[^>]*>We reply to every inquiry within five minutes and our bookings doubled\.<\/mark>/);
  assert.match(text, /Honestly, We reply to every inquiry/);
  assert.match(text, /It changed the season\./);
  assert.match(text, /Carmen Cruickshank \(WIA team\) · 11:40/);
  assert.match(text, /Sam Maple \(Client\) · 12:05/);
  assert.match(text, /That is a strong result\./);
  assert.equal((html.match(/data-cited="true"/g) ?? []).length, 1, 'only the cited passage is marked');
  assert.equal((html.match(/<mark/g) ?? []).length, 1);
});

test('2.F2: it shows who said it and their role, the document, the recording link, the topics and the cards that cite it', () => {
  const html = detail();
  const text = visible(html);
  for (const expected of ['Said by', 'Sam Maple', 'Client', 'Client call with Maple Venue', 'Zoom, Client 1:1', 'Inquiry follow-up speed', 'Follow-up decides the ad', 'supports the argument', 'Waiting for a decision']) assert.ok(text.includes(expected), expected);
  assert.match(html, /<a[^>]*href="https:\/\/fathom\.video\/share\/abc"[^>]*target="_blank"[^>]*rel="noopener noreferrer"/);
  assert.match(html, /href="\/sources\/documents\/t_1"/);
  assert.match(html, /href="\/studio\/angles\/week_1\/angle_1"[^>]*>Follow-up decides the ad/);
  assert.match(html, /href="\/moments"[^>]*>(?:<svg[^>]*>.*?<\/svg>)?All moments/);
  assert.ok(!text.includes('suggested by the system'), 'who assigned a topic is not on the page');
});

test('2.F2: no passage IDs, offsets or pipeline words are on the surface (R50)', () => {
  const text = visible(detail());
  for (const leaked of ['p_1', 'p_2', 'p_3', 'm_reply', 'passage', 'offset', 'evidence_refs', 'span', 'anchor', 'extractor', 'moment-checks', 'transcript_id', 'job']) assert.ok(!text.toLowerCase().includes(leaked.toLowerCase()), leaked);
});

test('2.F2: consent is named with the reason in words, for every status', () => {
  const cleared = visible(detail());
  for (const expected of ['Can it be used?', 'Cleared for naming', 'The client can be named alongside this quote.', 'The client has agreed to be named.', 'The line looks suitable for public use.', 'It is in the speaker\'s own words.']) assert.ok(cleared.includes(expected), expected);
  const consent = (status: string, client_consent: string | null, sensitivity: string, evidence_kind: string) => ({
    ...MOMENT_DETAIL, summary: { ...MOMENT, consent_status: status }, checks: { ...MOMENT_DETAIL.checks, consent: { status, client_consent, sensitivity, evidence_kind } },
  });
  const anonymise = visible(detail(consent('anonymise', 'anonymise_only', 'public_candidate', 'direct_quote')));
  for (const expected of ['Anonymise', 'Use it without naming the client or their business.', 'The client has agreed to be quoted only without their name.']) assert.ok(anonymise.includes(expected), expected);
  const internal = visible(detail(consent('internal_only', 'may_name', 'internal_only', 'direct_quote')));
  for (const expected of ['Internal only', 'For the team only. It is not for public content.', 'The line was marked as for the team only.']) assert.ok(internal.includes(expected), expected);
  const blocked = detail(consent('do_not_use', 'no_use', 'public_candidate', 'direct_quote'));
  for (const expected of ['Do not use', 'Nothing from this client may be used.', 'The client has asked that nothing from them is used.']) assert.ok(visible(blocked).includes(expected), expected);
  assert.match(blocked, /role="note"[^>]*>.*?Do not use\./);
  const relayed = visible(detail(consent('anonymise', 'may_name', 'public_candidate', 'team_report')));
  assert.ok(relayed.includes('A team member relayed it; the client did not say it themselves.'));
});

test('2.F2: a quote repaired to the transcript\'s wording says so, and shows what changed', () => {
  const html = detail({ ...MOMENT_DETAIL, quote_repair: { rule: 'normalised-whitespace-punctuation.v1', original_quote: 'we reply to every inquiry', repaired_quote: MOMENT.quote, anchor_span_id: 'p_2', moment_id: 'm_reply' } });
  const text = visible(html);
  assert.ok(text.includes('The quote was matched to the transcript\'s own wording.'));
  assert.match(text, /First wording “we reply to every inquiry”/);
  assert.ok(text.includes('Transcript\'s wording “We reply to every inquiry within five minutes and our bookings doubled.”'));
  assert.ok(!visible(detail()).includes('matched to the transcript\'s own wording'), 'nothing is said when nothing was repaired');
});

test('2.F2: the checks that failed are named in plain words', () => {
  const failing = {
    ...MOMENT_DETAIL,
    checks: {
      ...MOMENT_DETAIL.checks,
      numbers: { passed: false, figures: [], absent: ['$14,000'], context_only: ['12'] },
      role_plausibility: { passed: false, speaker_role: 'staff', original_type: 'testimonial', moment_type: 'observation', evidence_kind: 'team_report', reason: 'internal wording' },
    },
  };
  const html = detail(failing);
  const text = visible(html);
  assert.match(html, /aria-label="Checks that failed"/);
  for (const expected of ['The source does not contain the figure $14,000.', 'The figure 12 appears only in the conversation around the quote, not in the line itself.',
    'It was first tagged as a testimonial, but it was said by someone on the WIA team, and that is the client\'s to claim. It is shown as an observation instead.']) assert.ok(text.includes(expected), expected);
  assert.ok(!text.includes('internal wording'), 'the backend\'s own wording is not printed');
  assert.ok(visible(detail()).includes('The checks on the figures and on who said it all passed.'));
  assert.ok(!visible(detail()).includes('Checks that failed'));
  assert.ok(visible(detail({ ...MOMENT_DETAIL, checks: {} })).includes('No checks are recorded for this moment.'));
});

test('2.F2: an unverified quote is marked, with no claim that it is verbatim, and without checks it could not have', () => {
  const unverified = { ...MOMENT_DETAIL, summary: { ...MOMENT, quote_verified: false, consent_status: 'anonymise' }, citation: null, passages: [], surrounding: [], checks: { consent: { status: 'anonymise', client_consent: 'may_name' } }, unverified_reason: 'The quote does not bind to its source' };
  const html = detail(unverified);
  const text = visible(html);
  assert.ok(text.includes('Quote not verified'));
  assert.ok(text.includes('This quote could not be matched to the transcript, so it is not shown as the speaker\'s exact words. Do not treat it as a verbatim quote.'));
  assert.ok(text.includes('No checks could be made without a verified quote.'));
  assert.ok(text.includes('The conversation around this moment is not available.'));
  assert.ok(!text.includes('does not bind'), 'the backend\'s reason code is not printed');
  assert.match(html, /border-dashed/);
});

test('2.F2: a moment with no recording says so instead of linking nowhere', () => {
  const none = { ...MOMENT_DETAIL, citation: { ...CITATION, recording_url: null }, document: { ...MOMENT_DETAIL.document, recording_url: null } };
  const html = detail(none);
  assert.ok(visible(html).includes('This source has no recording to open.'));
  assert.ok(!/Open the recording/.test(html));
  // A link that is not http(s) is never made into one.
  assert.ok(!/javascript:/.test(detail({ ...none, citation: { ...CITATION, recording_url: 'javascript:alert(1)' }, document: { ...none.document, recording_url: 'javascript:alert(1)' } })));
});

test('2.F2: gaps are said plainly: no scene, no topics, no cards, original conversation not fully matched', () => {
  const sparse = { ...MOMENT_DETAIL, summary: { ...MOMENT, record: null, context_summary: null, qualifications: [] }, topics: [], cards: [], evidence_intact: false };
  const text = visible(detail(sparse));
  for (const expected of ['No scene was recorded for this moment.', 'No topic has been assigned yet.', 'No card uses this moment yet.', 'Part of the original conversation could not be matched to this moment']) assert.ok(text.includes(expected), expected);
});

test('2.F2: while the moment is read, the screen says so', () => {
  const text = visible(renderScreen(<MomentView />, { url: '/moments/m_reply', pattern: PATTERN }));
  assert.match(text, /Loading the moment…/);
  assert.ok(!text.includes('The scene'));
});

test('2.F2: a moment that does not exist, and a failed read, show the error with a way to try again', async t => {
  const network = stubFetch(() => json({ detail: 'Moment not found' }, 404));
  t.after(network.restore);
  const ui = await mount(<MomentView />, { url: '/moments/m_gone', pattern: PATTERN });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /Moment not found/);
  assert.ok(ui.container.querySelector('[role="alert"]'));
  assert.ok([...ui.container.querySelectorAll('button')].some(b => b.textContent === 'Retry'));
  assert.ok(ui.container.querySelector('a[href="/moments"]'), 'the way back to the ledger is still offered');
});

test('2.F2: a link back from a moment leads to the same filtered ledger; a fresh mount leads to the plain ledger', async t => {
  const network = stubFetch(url => {
    const route = new URL(url, 'http://x').pathname.replace('/api/atelier', '');
    if (route === '/moments/facets') return json(MOMENT_FACETS);
    if (route === '/moments/m_reply') return json(MOMENT_DETAIL);
    if (route === '/moments') return json(MOMENT_LIST);
    if (route === '/me') return json(ME_APPROVER);
    return json(TOPICS);
  });
  t.after(network.restore);
  const ui = await mount(<Routes><Route path="/moments" element={<MomentsView />} /><Route path={PATTERN} element={<MomentView />} /></Routes>, { url: '/moments?client_id=client_maple&moment_type=result' });
  t.after(() => ui.unmount());
  await ui.settle();
  await ui.click([...ui.container.querySelectorAll('a')].find(a => a.textContent?.startsWith('Read the moment')) ?? null);
  await ui.settle();
  assert.match(ui.text(), /Can it be used\?/);
  assert.equal(ui.container.querySelector('a[href^="/moments?"]')?.getAttribute('href'), '/moments?client_id=client_maple&moment_type=result');
  const fresh = await mount(<MomentView />, { url: '/moments/m_reply', pattern: PATTERN });
  t.after(() => fresh.unmount());
  await fresh.settle();
  assert.equal(fresh.container.querySelector('a[href^="/moments"]')?.getAttribute('href'), '/moments');
});

test('2.F2: a link back is never taken from outside the ledger', () => {
  assert.equal(backTarget({ from: '/moments?client_id=client_maple' }), '/moments?client_id=client_maple');
  assert.equal(backTarget({ from: '/moments' }), '/moments');
  for (const hostile of [{ from: 'https://elsewhere.test/moments' }, { from: '//elsewhere.test/moments' }, { from: '/momentsx' }, { from: '/sources' }, { from: 3 }, {}, null, undefined, 'x']) assert.equal(backTarget(hostile), '/moments');
});

test('2.F2: an editor can add and remove a moment\'s topics; a viewer sees them without controls', async t => {
  const posts: { url: string; body: unknown }[] = [];
  let topics: { topic_id: string; name: string; assigned_by: string; similarity: number | null }[] = MOMENT_DETAIL.topics;
  const network = stubFetch((url, options) => {
    const route = new URL(url, 'http://x').pathname.replace('/api/atelier', '');
    if (options?.method === 'POST') {
      const body = JSON.parse(String(options.body));
      posts.push({ url: route, body });
      topics = body.add?.length ? [...topics, { topic_id: body.add[0], name: 'Raising prices', assigned_by: 'person', similarity: null }] : topics.filter(x => !body.remove.includes(x.topic_id));
      return json({ moment_id: 'm_reply', topics });
    }
    if (route === '/moments/m_reply') return json({ ...MOMENT_DETAIL, topics });
    if (route === '/me') return json(ME_APPROVER);
    return json(TOPICS);
  });
  t.after(network.restore);
  const ui = await mount(<MomentView />, { url: '/moments/m_reply', pattern: PATTERN });
  t.after(() => ui.unmount());
  await ui.settle();
  await ui.settle();
  // The label names the themed dropdown by its id; the native select beside it carries the options and takes the choice.
  const select = ui.container.querySelector('[id^="topic-"][role="combobox"] ~ select') as HTMLSelectElement;
  assert.deepEqual([...select.options].map(option => option.value), ['', 'topic_pricing'], 'a topic the moment has is not offered again');
  await ui.choose(select, 'topic_pricing');
  await ui.click([...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Add') ?? null);
  await ui.settle();
  assert.deepEqual(posts, [{ url: '/moments/m_reply/topics', body: { add: ['topic_pricing'], remove: [] } }]);
  assert.match(ui.text(), /Raising prices/);
  assert.match(ui.text(), /Topic added\./);
  await ui.click(ui.container.querySelector('button[aria-label="Remove the topic Inquiry follow-up speed"]'));
  await ui.settle();
  assert.deepEqual(posts.at(-1), { url: '/moments/m_reply/topics', body: { add: [], remove: ['topic_followup'] } });
  assert.ok(!ui.container.querySelector('button[aria-label="Remove the topic Inquiry follow-up speed"]'), 'the topic is gone from the moment');

  const viewer = stubFetch(url => url.endsWith('/me') ? json(VIEWER) : url.includes('/moments/') ? json(MOMENT_DETAIL) : json(TOPICS));
  t.after(viewer.restore);
  const read = await mount(<MomentView />, { url: '/moments/m_reply', pattern: PATTERN });
  t.after(() => read.unmount());
  await read.settle();
  assert.match(read.text(), /Inquiry follow-up speed/);
  assert.ok(!read.container.querySelector('button[aria-label^="Remove the topic"]'), 'no remove control');
  assert.ok(![...read.container.querySelectorAll('button')].some(b => b.textContent === 'Add'), 'no add control');
  assert.ok(!viewer.calls.some(call => call.url.includes('/topics')), 'the topics are not even read for a viewer');
});

test('2.F2: a refused topic change shows why and leaves the topics as they were', async t => {
  const network = stubFetch((url, options) => options?.method === 'POST' ? json({ detail: 'That topic is blocked' }, 409)
    : url.endsWith('/me') ? json(ME_APPROVER) : url.includes('/moments/') ? json(MOMENT_DETAIL) : json(TOPICS));
  t.after(network.restore);
  const ui = await mount(<MomentView />, { url: '/moments/m_reply', pattern: PATTERN });
  t.after(() => ui.unmount());
  await ui.settle();
  await ui.settle();
  await ui.click(ui.container.querySelector('button[aria-label="Remove the topic Inquiry follow-up speed"]'));
  await ui.settle();
  assert.match(ui.text(), /That topic is blocked/);
  assert.match(ui.text(), /Inquiry follow-up speed/);
});

test('2.F2: the body renders from the API answer alone', () => {
  const text = visible(renderScreen(<MomentBody detail={MOMENT_DETAIL as never} />));
  assert.ok(text.includes('Maple Venue') && text.includes('Can it be used?'));
});
