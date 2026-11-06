import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderScreen, CLIENT, type Seeded } from '../testing/render';
import { BRIEF_V2, DOCUMENT, DOCUMENT_DETAIL, DOCUMENT_LIST, INTAKE_OVERVIEW, KNOWN_ITEMS, seed, shell } from '../testing/fixtures';
import { PACK, PLAN, SUMMARY } from '../testing/packFixtures';
import { EXTRACTION_HEALTH, MOMENT_DETAIL, MOMENT_FACETS, MOMENT_LIST, TOPICS } from '../testing/momentFixtures';
import { AppRoutes } from './AppRoutes';
import { paths } from './routes';
import { weekLabel } from '../utils/editorialWeeks';
import { weekBriefsArgs, weekPacksArgs } from '../components/studio/studioWeek';

/* 1.F1, done when: every view and entity survives a refresh on its own URL. A refresh is a fresh render at the URL with
   nothing but the URL to go on, so each case renders the whole app at one path and looks for what that path names. */

const flagged = { packs: true, calendar: true, context: true };
const page = (url: string, seeds: Seeded[] = [], flags = flagged) => renderScreen(<AppRoutes />, { url, seed: [...shell(flags), ...seeds] });
const texts = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ');

const CASES: { name: string; url: string; seeds?: Seeded[]; expect: (string | RegExp)[]; flags?: typeof flagged }[] = [
  { name: 'the studio (a week)', url: paths.week('week_1'), expect: ['Weekly Studio', 'Awaiting approval', 'Approved', `${weekLabel('2026-10-05')} · Latest week`, 'Content Angle', 'Content Briefing'] },
  { name: 'a card in a week', url: paths.angle('week_1', 'angle_1'), expect: [/id="angle-angle_1"/, 'Follow-up decides the ad'] },
  { name: 'the briefs list', url: paths.briefs, seeds: [seed('/briefs', weekBriefsArgs('week_1'), { items: [BRIEF_V2], total: 1, limit: 50, offset: 0 })], expect: ['Awaiting approval', 'Why we ask about follow-up first', 'Follow-up shapes lead quality.', 'Read full brief'] },
  { name: 'a brief', url: paths.brief('brief_1'), seeds: [
    seed('/briefs', weekBriefsArgs('week_1'), { items: [BRIEF_V2], total: 1, limit: 50, offset: 0 }),
    seed('/briefs/{brief_id}', { path: { brief_id: 'brief_1' } }, BRIEF_V2),
  ], expect: ['WIA perspective', 'We look at what happens after the inquiry.'] },
  // N1 shakedown: a v2 to v4 brief showed only that a refresh was running; a failed refresh vanished on reload.
  { name: 'a brief whose refresh failed', url: paths.brief('brief_1'), seeds: [
    seed('/briefs', weekBriefsArgs('week_1'), { items: [BRIEF_V2], total: 1, limit: 50, offset: 0 }),
    seed('/briefs/{brief_id}', { path: { brief_id: 'brief_1' } }, { ...BRIEF_V2, can_edit: true }),
    seed('/angles/{angle_id}/research', { path: { angle_id: BRIEF_V2.angle_id } }, {
      status: 'failed', run_id: 'run_r', input_hash: 'h', brief_id: 'brief_1', mode: 'live', waiting_reason: null, dossier: null, costs: null,
      error_summary: 'The worker stopped while this step was running, so it is not run again by itself. Retry this step to run it again.',
      jobs: [{ job_id: 'job_w', stage: 'brief_writing', status: 'failed', current_message: 'Stopped: its worker was lost', attempt_count: 1,
               completed_units: null, total_units: null, updated_at: '2026-10-23T07:05:00Z', error_summary: null }] }),
  ], expect: ['The worker stopped while this step was running', 'Try this step again', 'WIA perspective'] },
  // NP.F1: the content packs (contract v2) replace the v1 list and detail, at the same paths.
  { name: 'the packs in the studio', url: paths.studioPacks, seeds: [seed('/packs', weekPacksArgs('week_1'), { items: [SUMMARY], total: 1 })], expect: ['Why we read the reply first', 'Generated content packs', 'Generated', '3 Reels', 'Open pack'] },
  { name: 'a pack', url: paths.studioPack('pack_1'), seeds: [seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, PACK)],
    expect: [/role="tablist"[^>]*aria-label="Content pack pieces"/, 'Copy all', 'Mark each piece published or sent when it goes out.', 'Mark as Published'] },
  { name: 'a piece of a pack', url: `${paths.studioPack('pack_1')}?piece=reel_2`, seeds: [seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, PACK)],
    expect: [/id="pack-piece-tab-reel_2"[^>]*aria-selected="true"/] },
  // NP.F4: a week's plan, the bank and the export, at its own path under either list.
  { name: "a week's content packs", url: `${paths.studioPacks}/week/week_2026-10-26`, seeds: [seed('/weeks/{week_id}/pack-plan', { path: { week_id: 'week_2026-10-26' } }, PLAN)],
    expect: ["The week's plan", 'Proposed for the week', 'The bank (1)', "Download the week's pack document"] },
  { name: "a week's content packs from the sidebar", url: `${paths.packs}/week/week_2026-10-26`, seeds: [seed('/weeks/{week_id}/pack-plan', { path: { week_id: 'week_2026-10-26' } }, PLAN)],
    expect: ["The week's plan"] },
  { name: 'the scheduled content', url: paths.scheduled, expect: ['Scheduled Content', 'Awaiting publication', 'Mark each piece published or sent from its pack or the content calendar when it goes out.'] },
  { name: 'the content packs view', url: paths.packs, seeds: [seed('/packs', { query: { limit: 20, offset: 0 } }, { items: [SUMMARY], total: 1 })], expect: [/Content Packs &amp; Deliverable Scripts/, 'Why we read the reply first', 'Generated'] },
  { name: 'previous concepts', url: paths.previous, expect: ['Previous Concepts', '← Weekly Studio', 'No earlier weeks with concepts yet.'] },
  { name: 'a pack in the content packs view', url: paths.pack('pack_1'), seeds: [seed('/packs/{pack_id}', { path: { pack_id: 'pack_1' } }, PACK)],
    expect: [/role="tablist"/, /href="\/packs"[^>]*><span aria-hidden="true">←\s<\/span>Content packs<\/a>/] },
  { name: 'home, as the cycle summary', url: paths.home, flags: { packs: false, calendar: false, context: false }, expect: ['3 angles waiting for your review', 'Next cycle: Sunday 1 November at 4:00 a.m. Chicago time'] },
  { name: 'the documents list', url: paths.documents, seeds: [seed('/documents', { limit: 50, offset: 0 }, DOCUMENT_LIST)], expect: ['Client call with Maple Venue', 'Vendor demo', 'Showing 1 to 2 of 170'] },
  { name: 'the documents list on its second page with a filter', url: `${paths.documents}?call_type=client_1to1&offset=50`, seeds: [
    seed('/documents', { call_type: 'client_1to1', limit: 50, offset: 50 }, { ...DOCUMENT_LIST, offset: 50, items: [DOCUMENT] })], expect: ['Showing 51 to 51 of 170', 'Clear 1 filter'] },
  { name: 'the documents list, with the processing health folded below it', url: paths.documents, seeds: [seed('/documents', { limit: 50, offset: 0 }, DOCUMENT_LIST), seed('/documents/extraction-health', null, EXTRACTION_HEALTH)],
    expect: ['150 calls included · 20 excluded', 'Upload a transcript', 'Processing health', 'Documents included 100', '3 documents failed', 'Client call with Maple Venue'] },
  { name: 'the moments ledger', url: paths.moments, seeds: [seed('/moments', { limit: 25, offset: 0 }, MOMENT_LIST), seed('/moments/facets', {}, MOMENT_FACETS), seed('/topics', { query: { status: 'active', limit: 200 } }, TOPICS)],
    expect: ['40 moments from calls and threads', /aria-label="Search the moments"/, '“We reply to every inquiry within five minutes and our bookings doubled.”', 'Cleared for naming', 'Showing 1 to 2 of 40', 'More filters'] },
  { name: 'the moments ledger on its second page with a filter', url: `${paths.moments}?moment_type=result&offset=25`, seeds: [
    seed('/moments', { moment_type: 'result', limit: 25, offset: 25 }, { ...MOMENT_LIST, offset: 25 })], expect: ['Showing 26 to 27 of 40', 'Clear 1 filter'] },
  { name: 'a moment', url: paths.moment('m_reply'), seeds: [seed('/moments/{moment_id}', { path: { moment_id: 'm_reply' } }, MOMENT_DETAIL)],
    expect: ['Can it be used?', 'In the conversation', /<mark[^>]*>We reply to every inquiry/, 'Open the recording', 'Follow-up decides the ad'] },
  { name: 'a document', url: paths.document('t_1'), seeds: [seed('/documents/{transcript_id}', 't_1', DOCUMENT_DETAIL)], expect: ['Client call with Maple Venue', 'How do you reply to inquiries today?', 'one client and one staff speaker'] },
  { name: 'the intake', url: paths.intake, seeds: [seed('/intake/overview', undefined, INTAKE_OVERVIEW)], expect: ['Weekly buckets', 'Recently received', 'Fathom call', 'Processing'] },
  { name: 'the weekly cycle', url: paths.cycle, expect: [/aria-current="page"[^>]*>Weekly cycle/] },
  { name: 'a source', url: paths.intakeSource('s1'), seeds: [seed('/intake/overview', undefined, INTAKE_OVERVIEW),
    seed('/intake/sources/{source_id}', { path: { source_id: 's1' } }, { source: INTAKE_OVERVIEW.sources[0], revisions: [], assets: [] })],
    expect: [/aria-label="Source original and revisions"/] },
  { name: 'a bucket', url: paths.intakeBucket('b1'), seeds: [seed('/intake/overview', undefined, INTAKE_OVERVIEW),
    seed('/intake/buckets/{bucket_id}', { path: { bucket_id: 'b1' } }, { bucket: INTAKE_OVERVIEW.buckets[0], sources: INTAKE_OVERVIEW.sources })],
    expect: ['Received in the bucket of', 'All recent sources'] },
  { name: 'the review queue', url: paths.review, expect: ['Review queue'] },
  // 6.F7: what the system runs with, for an editor or an approver (the shell signs in an approver).
  { name: 'the settings', url: paths.settings, seeds: [seed('/settings', undefined, { problems: [], settings: [
    { key: 'cycle.weekday', value: 5, source: 'default', default: 5, type: 'int', description: '' },
    { key: 'models.default', value: 'openai/gpt-6-luna', source: 'default', default: 'openai/gpt-6-luna', type: 'str', description: '' }] })],
    expect: ['Settings', 'Weekly schedule', 'Weekly spending limits', /<form aria-label="Weekly schedule"/] },
  { name: 'a tab of the review queue', url: `${paths.review}?kind=offer`, seeds: [
    seed('/context/summary', undefined, { kinds: { offer: { candidate: 2 } }, candidates: 2, published: { unconfirmed: 0 } }),
    seed('/context/queue', { query: { kind: 'offer', status: 'candidate', limit: 50, offset: 0 } }, { items: [], groups: {}, total: 0, limit: 50, offset: 0, batch_kinds: [] })],
    expect: [/<option value="offer" selected="">Offers \(2\)<\/option>/, 'Nothing waiting here'] },
  { name: 'what the system knows', url: paths.known, seeds: [seed('/context/items', { query: { on: new Date().toISOString().slice(0, 10) } }, KNOWN_ITEMS)], expect: ['What the system knows'] },
  { name: 'an entry history', url: paths.knownItem('item_1'), seeds: [seed('/context/items/{item_id}/history', { path: { item_id: 'item_1' } }, { key: 'offer:a', versions: [], decisions: [] })],
    expect: [/aria-label="History"/, 'No decisions recorded.'] },
  { name: 'the versions', url: paths.versions, expect: ['Compile a new version'] },
  { name: 'the changes of a version', url: paths.version('wia-kb-2026-10-20.c-1a2b3c4d'), seeds: [
    seed('/context/versions', undefined, { active: null, versions: [{ version: 'wia-kb-2026-10-20.c-1a2b3c4d', active: false, state: 'draft', on: '2026-10-20', runs: [] }] }),
    seed('/context/versions/{version}/diff', { path: { version: 'wia-kb-2026-10-20.c-1a2b3c4d' } },
      { version: 'wia-kb-2026-10-20.c-1a2b3c4d', against: null, state: 'draft', documents: [{ key: 'offer_sheet', change: 'operating', diff: '+ A new offer line' }] })],
    expect: [/aria-label="Changes to the offer sheet"/, 'A new offer line', 'Approve this version'] },
];

for (const c of CASES) {
  test(`1.F1: ${c.name} opens on its own URL (${c.url})`, () => {
    const html = page(c.url, c.seeds, c.flags ?? flagged);
    const visible = texts(html);
    for (const expected of c.expect) {
      if (typeof expected === 'string') assert.ok(visible.includes(expected), `${c.url} should show ${expected}`);
      else assert.match(html, expected, `${c.url} should match ${expected}`);
    }
    assert.ok(!visible.includes('This screen hit a problem'), 'no view failed to render');
  });
}

test('1.F1: a path that names nothing says so, in the app frame', () => {
  const html = page('/no/such/page');
  assert.match(texts(html), /This page is not available/);
  assert.match(html, /aria-label="Main navigation"/);
});

test('6.F3: the sample screens are not part of this app: /sample/* names nothing here', () => {
  for (const url of ['/sample/moments', '/sample/ideas', '/sample/packs']) {
    const html = page(url);
    assert.match(texts(html), /This page is not available/, url);
    assert.doesNotMatch(html, /data-sample-data|Sample data/, url);
  }
});

test('1.F1: a switched-off area answers at its own path instead of sending the person elsewhere', () => {
  const html = page(paths.studioPacks, [], { packs: false, calendar: false, context: false });
  assert.match(texts(html), /Content packs is not available/);
  assert.match(texts(page(paths.review, [], { packs: false, calendar: false, context: false })), /Knowledge is not available/);
});

test('S.F3, 1.F1: a client session gets neither the documents nor the intake from the Sources paths', () => {
  const documents = renderScreen(<AppRoutes />, { url: paths.documents, auth: CLIENT, seed: [...shell(flagged), seed('/documents', { limit: 50, offset: 0 }, DOCUMENT_LIST)] });
  assert.match(texts(documents), /Sources are available to the internal team/);
  assert.ok(!texts(documents).includes('Client call with Maple Venue'));
  const intake = renderScreen(<AppRoutes />, { url: paths.intake, auth: CLIENT, seed: [...shell(flagged), seed('/intake/overview', undefined, INTAKE_OVERVIEW)] });
  assert.match(texts(intake), /Sources are available to the internal team/);
  assert.ok(!texts(intake).includes('Fathom call'));
});

test('S.F3, 2.F1: a client session gets neither the ledger nor a moment', () => {
  const ledger = renderScreen(<AppRoutes />, { url: paths.moments, auth: CLIENT, seed: [...shell(flagged), seed('/moments', { limit: 25, offset: 0 }, MOMENT_LIST)] });
  assert.match(texts(ledger), /Moments are available to the internal team/);
  assert.ok(!texts(ledger).includes('We reply to every inquiry'));
  const moment = renderScreen(<AppRoutes />, { url: paths.moment('m_reply'), auth: CLIENT, seed: [...shell(flagged), seed('/moments/{moment_id}', { path: { moment_id: 'm_reply' } }, MOMENT_DETAIL)] });
  assert.match(texts(moment), /Moments are available to the internal team/);
  assert.ok(!texts(moment).includes('The quote'));
  assert.ok(!/href="\/moments"/.test(ledger.replace(/<main[\s\S]*<\/main>/, '')), 'the navigation does not offer it');
});

test('2.F1: the sidebar offers the Moments ledger to the team', () => {
  assert.match(page(paths.home), /<a[^>]*href="\/moments"[^>]*aria-label="Moments"|<a[^>]*aria-label="Moments"[^>]*href="\/moments"/);
});

test('1.F1: the sidebar names the area a path belongs to', () => {
  const current = (url: string) => /aria-current="page"[^>]*aria-label="([^"]+)"|aria-label="([^"]+)"[^>]*aria-current="page"/.exec(page(url))?.slice(1).find(Boolean);
  assert.equal(current(paths.brief('brief_1')), 'Weekly Studio');
  assert.equal(current(paths.document('t_1')), 'Sources');
  assert.equal(current(paths.known), 'Knowledge');
  assert.equal(current(paths.moments), 'Moments');
  assert.equal(current(paths.moment('m_reply')), 'Moments');
  assert.equal(current(paths.home), 'Home');
  assert.equal(current(paths.settings), 'Settings');
});
