import '../../testing/setupDom';
import React, { act } from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Route, Routes } from 'react-router-dom';
import { json, mount, stubFetch } from '../../testing/dom';
import { renderScreen } from '../../testing/render';
import { createQueryClient, queryKey } from '../../api/query';
import { ME_APPROVER, REVIEW, WEEK, seed, shell } from '../../testing/fixtures';
import { BRIEF_V4, SUMMARY as PACK_SUMMARY } from '../../testing/packFixtures';
import type { Card, PackSummaryV2, StoredAngle, StoredBrief } from '../../api/types';
import { BackendStudio } from '../BackendStudio';
import { SQLWeeklyAngles } from '../SQLWeeklyAngles';
import { PreviousConcepts } from '../PreviousConcepts';
import { HomePage } from '../../app/HomePage';
import { AngleCard } from './AngleCard';
import { BriefCard, whatIsLeft } from './BriefCard';
import { CardRationale, nextStep } from './CardRationale';
import { PackCard, packLeft } from './PackCard';
import { matches, offerName, personName } from './parts';
import { cardGroup, stageCounts, stagePath, weekBriefsArgs, weekInUrl, weekPacksArgs } from './studioWeek';

/* The Weekly Studio, Previous Concepts, Content Packs and Home realigned with the 20 October mockup: the cards and the stepper,
   the develop decision from a card with the card screen's confirmations, the brief card that offers approval only when
   nothing blocks it, the packs in plain words, and no internal labels on the client's screens. Every text is synthetic. */

const card = {
  rank: 1, title: 'Why we read the reply first', pillar: 'WARM', content_type: 'behind_the_scenes', series: 'Watch Us Build an Ad Strategy',
  audience: 'Venue owners who already run ads', point: 'The first reply decides which couples book a tour.', point_is_about: 'wia_belief',
  surprise_for_experienced_advertiser: { surprising: true, reason: 'They tune the ads first.' }, reader_takeaway: 'I want a team that reads the whole path.',
  reader_fit: { buyer: 'elevate', buyer_statement: 'Owners who want leads that book.', why: 'Lead quality is their pain.' }, belief_ref: 'B3',
  why_it_matters: 'Fit beats volume.', wia_in_action: 'The strategist asks to see the first reply.', evidence_points: ['The strategist asks to see the first reply. (12:01–12:40)'],
  guardrail: 'Keep the venue unnamed. Say "reset", never "fixed".', offer_fit: { offer: 'ELEVATE', cta_slot: 'soft_invitation', calendar_note: 'Open this window.' },
  public_stance: { takes_stance: false, stance: null }, recurrence: null, moment_ids: [], verify_before_publishing: ['Confirm the client may be referenced.'],
  why_selected: 'Shows the WIA move.', core_perspective: '', offer_connection: null,
} as unknown as Card;
const angle = (patch: Partial<StoredAngle> = {}) => ({
  angle_id: 'angle_card', run_id: 'run_1', content_hash: 'hash_card', moment_ids: [], has_replacement: false, workflow: null, supersedes_id: null,
  content_body: { card, title: card.title }, base_score: null, adjusted_score: null, selection_status: 'visible', approval_status: 'pending',
  first_generated_at: '2026-10-20T10:00:00Z', selected_cta: null, matching_result: { status: 'complete', current_batch_flags: [] }, disposition: null, hold: null,
  can_approve: true, can_edit: true, can_reject: true, ...patch,
}) as unknown as StoredAngle;
const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
const INTERNAL = ['What the point is about', 'Would it surprise', 'Who the reader is', 'The belief it proves', 'B3', 'point_is_about', 'Why it was chosen', 'Idea 1'];

test('the angle card summarises: title, status, date and offer, the pillar and type, the point, why it matters, and two buttons', () => {
  const html = renderScreen(<AngleCard angle={angle()} card={card} week="week_1" roster={[]} canDecide busy={false} perform={async () => true} onReview={() => {}} />);
  const words = text(html);
  for (const expected of ['Why we read the reply first', 'Awaiting approval', '20 Oct 2026 · Elevate', 'WARM', 'Behind the scenes',
    'The first reply decides which couples book a tour.', 'Why it matters: Fit beats volume.', 'Review angle', 'Approve & create brief']) {
    assert.ok(words.includes(expected), expected);
  }
  for (const removed of ['Topic & editorial rationale', 'Audience:', 'WIA’s expertise or process:', 'Evidence in the referenced call:', 'Editorial guardrail / next step:',
    'Keep the venue unnamed.', 'The strategist asks to see the first reply.', 'Source moment', 'Approved', ' by ']) {
    assert.ok(!words.includes(removed), `the full rationale is the dialog's, not the card's: ${removed}`);
  }
  for (const label of INTERNAL) assert.ok(!words.includes(label), `no internal label on the card: ${label}`);
  assert.ok(!/\d+\/100/.test(words), 'no invented score');
});

test('an approved card says where it went next in its footer: its pack, else its brief', () => {
  const approved = angle({ approval_status: 'approved', disposition: { disposition: 'develop', author: 'Avery Lane', created_at: '2026-10-25T10:00:00Z', reason_code: null, note: null } } as never);
  const withPack = renderScreen(<AngleCard angle={approved} card={card} week="week_1" roster={[]} brief={brief({ angle_id: 'angle_card', approval_status: 'approved' })}
    pack={PACK_SUMMARY as unknown as PackSummaryV2} canDecide busy={false} perform={async () => true} onReview={() => {}} />);
  assert.ok(text(withPack).includes('Open pack →') && withPack.includes(`href="/studio/packs/${PACK_SUMMARY.pack_id}"`));
  assert.ok(!text(withPack).includes('Approve & create brief') && !text(withPack).includes('Avery Lane'), 'no decision or decider on the card');
  const withBrief = text(renderScreen(<AngleCard angle={approved} card={card} week="week_1" roster={[]} brief={brief({ angle_id: 'angle_card' })} canDecide busy={false}
    perform={async () => true} onReview={() => {}} />));
  assert.ok(withBrief.includes('Open brief →') && withBrief.includes('Approved'));
});

test('the full rationale in the dialog keeps the call times of the evidence', () => {
  const words = text(renderScreen(<CardRationale card={card} full />));
  assert.ok(words.includes('(12:01–12:40)'));
  assert.equal(nextStep({ ...card, offer_fit: null, offer_connection: 'LeadLock invitation' } as unknown as Card), 'LeadLock invitation');
});

test('"Approve & create brief" asks for the card\'s confirmations first, and sends the develop decision with them', async t => {
  const calls: [string, string | undefined, unknown, unknown][] = [];
  const perform = async (path: string, method?: string, body?: unknown, options?: unknown) => { calls.push([path, method, body, options]); return true; };
  const ui = await mount(<AngleCard angle={angle()} card={card} week="week_1" roster={[]} canDecide busy={false} perform={perform} onReview={() => {}} />);
  t.after(() => ui.unmount());
  const approve = [...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Approve & create brief')!;
  await ui.click(approve);
  const dialog = document.querySelector('[role="dialog"]') as HTMLElement;
  assert.ok(dialog, 'the confirmations open first');
  const confirm = [...dialog.querySelectorAll('button')].find(b => b.textContent === 'Approve & create brief')!;
  await ui.click(confirm);
  assert.match(dialog.textContent ?? '', /Tick every "verify before publishing" item first/);
  assert.equal(calls.length, 0, 'nothing is sent until every item is ticked');
  await ui.tick([...dialog.querySelectorAll('label')].find(l => l.textContent?.includes('Confirm the client may be referenced.'))!.querySelector('input')!);
  await ui.click(confirm);
  await ui.settle();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], '/angles/angle_card/decision');
  assert.deepEqual(calls[0][2], { expected_hash: 'hash_card', disposition: 'develop', note: null, author: null, reason_code: null,
    cta: { choice: 'decide_in_development' }, verify_acknowledged: ['Confirm the client may be referenced.'], overlap_acknowledged: false });
  assert.deepEqual(calls[0][3], { target: 'card:angle_card', message: 'Approved. Its brief is being written, which takes 15 to 30 minutes.' }, 'focus returns to the card, and the result is said');
});

test('a card that cannot be developed says why in one plain line, and the approve button stays off', () => {
  const stance = { ...card, public_stance: { takes_stance: true, stance: 'Ads are not the first fix.' } } as unknown as Card;
  const words = text(renderScreen(<AngleCard angle={angle({ content_body: { card: stance, title: card.title } } as never)} card={stance} week="week_1" roster={[]} canDecide busy={false}
    perform={async () => true} onReview={() => {}} />));
  assert.match(words, /takes a public stance/);
  assert.match(renderScreen(<AngleCard angle={angle()} card={stance} week="week_1" roster={[]} canDecide busy={false} perform={async () => true} onReview={() => {}} />),
    /disabled="">.*Approve &amp; create brief/s);
  assert.ok(!text(renderScreen(<AngleCard angle={angle()} card={card} week="week_1" roster={[]} canDecide={false} busy={false} perform={async () => true} onReview={() => {}} />)).includes('Approve & create brief'),
    'a person who may not decide is not offered it');
});

test('a card\'s place on the step, and the stepper\'s counts in the mockup\'s exclusive sense', () => {
  assert.equal(cardGroup(angle()), 'waiting');
  assert.equal(cardGroup(angle({ approval_status: 'approved' })), 'approved');
  assert.equal(cardGroup(angle({ hold: { until: '2026-11-01', author: 'a', note: null, reason_code: 'timing' } } as never)), 'other');
  assert.equal(cardGroup(angle({ approval_status: 'rejected' })), 'other');
  const review = { angles: [angle(), angle({ angle_id: 'b', approval_status: 'approved' }), angle({ angle_id: 'c', approval_status: 'approved' }), angle({ angle_id: 'old', has_replacement: true })] };
  const packs = [{ ...PACK_SUMMARY, state: 'ready_to_publish', pieces: PACK_SUMMARY.pieces.map((p, i) => ({ ...p, published: i === 0 })) }] as unknown as PackSummaryV2[];
  assert.deepEqual(stageCounts(review as never, [{ approval_status: 'pending' }, { approval_status: 'approved' }], packs),
    { waiting: 1, approved: 1, generated: 1, briefsWaiting: 1, awaitingPublication: 1, published: 1, concepts: 3, cards: 3 });
  assert.equal(weekInUrl('/studio/angles/week_2026-10-19/angle_1', new URLSearchParams()), 'week_2026-10-19');
  assert.equal(weekInUrl('/studio/briefs', new URLSearchParams('week=week_2026-10-19')), 'week_2026-10-19');
  assert.equal(weekInUrl('/studio/briefs', new URLSearchParams('week=../x')), '');
  assert.equal(stagePath('briefs', 'week_1'), '/studio/briefs?week=week_1');
  assert.equal(stagePath('angles', 'week_1'), '/studio/angles/week_1');
});

test('awaiting-publication counts include unapproved generated packs and exclude complete or unfinished packs', () => {
  const pack = { ...PACK_SUMMARY, state: 'in_review' } as PackSummaryV2;
  assert.equal(stageCounts(undefined, undefined, [pack]).awaitingPublication, 1);
  const complete = { ...pack, pieces: pack.pieces.map(piece => ({ ...piece, published: true })) };
  assert.equal(stageCounts(undefined, undefined, [complete]).awaitingPublication, 0);
  assert.equal(stageCounts(undefined, undefined, [{ ...pack, state: 'finishing' }]).awaitingPublication, 0);
});

test('the offer filter and the search match by the offer\'s name; a person is named, never an address', () => {
  assert.equal(offerName('ELEVATE, our full-service advertising management program'), 'Elevate');
  assert.equal(offerName('LeadLock and The Foolproof Follow-Up Advantage'), 'LeadLock');
  assert.equal(offerName('Google Search Accelerator'), 'Accelerators');
  assert.ok(matches('Why we read the reply first', 'ELEVATE', 'reply first', 'elevate'));
  assert.ok(!matches('Why we read the reply first', 'ELEVATE', '', 'leadlock'));
  assert.equal(personName('Whitney Hodges'), 'Whitney Hodges');
  assert.equal(personName('team@example.invalid (delegated, D12)'), '');
});

const weekSeeds = (review: unknown) => [...shell({ packs: true }), seed('/weeks/{week_id}', { path: { week_id: WEEK.week_id } }, review),
  seed('/briefs', weekBriefsArgs(WEEK.week_id), { items: [], total: 0, limit: 50, offset: 0 }), seed('/packs', weekPacksArgs(WEEK.week_id), { items: [], total: 0 }),
  seed('/seeds', { query: { status: 'open' } }, [])];

test('the Weekly Studio is the mockup\'s: the title and its subtitle, Download review, the four-step stepper, the week\'s filter, then the sections', () => {
  const review = { ...REVIEW, angles: [angle()], roster: [], rubric: null };
  const html = renderScreen(<Routes><Route path="/studio" element={<BackendStudio flags={{ briefs: true, packs: true, calendar: false, context: false }} />}>
    <Route path="angles/:weekId" element={<SQLWeeklyAngles />} /></Route></Routes>, { url: `/studio/angles/${WEEK.week_id}`, seed: weekSeeds(review) });
  const words = text(html);
  for (const expected of ['Weekly Studio', '5 Oct – 11 Oct, 2026 · Latest week', 'Download review', 'Previous Concepts', 'Flag idea', 'Content Angle',
    '1 waiting · 0 approved · 0 generated', 'Content Briefing', '0 waiting · 0 generated', 'Content Packs', 'Scheduled Content', 'All offers', 'Awaiting approval',
    'Approved', 'Approved angles will be retained here.']) {
    assert.ok(words.includes(expected), expected);
  }
  assert.match(html, /aria-current="page"[^>]*class="editorial-pipeline-step is-selected"/);
  assert.ok(html.includes(`href="/api/atelier/weeks/${WEEK.week_id}/review.docx"`), 'Download review is a direct link to the Word file');
  for (const removed of ['concepts across all stages', 'Review document (Markdown)', 'Showing only', 'Cycle details', 'Why these ideas', 'every verified scene reached the strategist', 'USD',
    'Monday–Sunday weeks']) {
    assert.ok(!words.includes(removed), `${removed} is gone from the Studio`);
  }
});

test('a content pack\'s page in the Studio is shown without the Studio\'s frame', () => {
  const html = renderScreen(<Routes><Route path="/studio" element={<BackendStudio flags={{ briefs: true, packs: true, calendar: false, context: false }} />}>
    <Route path="packs/:packId" element={<p>The pack page</p>} /></Route></Routes>, { url: '/studio/packs/pack_1', seed: weekSeeds({ ...REVIEW, angles: [], roster: [], rubric: null }) });
  const words = text(html);
  assert.ok(words.includes('The pack page'));
  for (const frame of ['Weekly Studio', 'Content Angle', 'Download review', 'All offers']) assert.ok(!words.includes(frame), `no Studio frame: ${frame}`);
});

test('a card\'s own URL opens its full card screen in the review dialog', () => {
  const review = { ...REVIEW, angles: [angle()], roster: [], rubric: null };
  const html = renderScreen(<SQLWeeklyAngles />, { url: `/studio/angles/${WEEK.week_id}/angle_card`, pattern: '/studio/angles/:weekId/:angleId', seed: weekSeeds(review) });
  assert.match(html, /role="dialog"[^>]*aria-label="Review angle: Why we read the reply first"/);
  const dialog = text(html.slice(html.indexOf('role="dialog"')));
  for (const expected of ['Content Angle', 'Content Brief', 'Content Pack', 'Schedule', 'Topic & editorial rationale', 'What was said on the call', 'Your decision',
    'Verify before publishing', 'Recorded: 20 Oct 2026']) {
    assert.ok(dialog.includes(expected), expected);
  }
  for (const removed of ['Details', 'What the point is about', 'Decision:', 'Whose decision is this?']) assert.ok(!dialog.includes(removed), `not in the dialog: ${removed}`);
});

const brief = (patch: Record<string, unknown> = {}) => ({ ...BRIEF_V4, ...patch }) as unknown as StoredBrief;

test('the brief card summarises the brief and offers "Approve & generate pack" only when nothing blocks it', () => {
  const ok = text(renderScreen(<BriefCard brief={brief()} week="week_1" packsOn busy={false} onApprove={() => {}} fullBriefHref="/studio/briefs/brief_v4" />));
  for (const expected of ['Awaiting approval', 'WARM', 'Behind the scenes', 'The first reply shapes which couples book a tour.', '1 Email · 1 Carousel · 2 Reels',
    'Read full brief', 'Approve & generate pack']) assert.ok(ok.includes(expected), expected);
  for (const removed of ['Content brief', 'Strategic purpose:', 'Audience and reason to care:', 'WIA perspective:', 'CTA and essential boundaries:', 'View source angle', 'Approved']) {
    assert.ok(!ok.includes(removed), `the full brief is one click away, not on the card: ${removed}`);
  }
  const blocked = brief({ can_approve: false, blockers: ['x'], blocker_items: [{ kind: 'blocking_finding', title: 'Answer every required item under "Before publishing".', action: '', detail: null }] });
  assert.equal(whatIsLeft(blocked), 'Before approval: Answer every required item under "Before publishing".');
  const html = renderScreen(<BriefCard brief={blocked} week="week_1" packsOn busy={false} onApprove={() => {}} fullBriefHref="/studio/briefs/brief_v4" />);
  assert.match(html, /disabled=""[^>]*>.*Approve &amp; generate pack/s);
  assert.ok(text(html).includes('Before approval: Answer every required item'));
  const approvedHtml = renderScreen(<BriefCard brief={brief({ approval_status: 'approved' })} week="week_1" pack={PACK_SUMMARY as unknown as PackSummaryV2} packsOn busy={false}
    onApprove={() => {}} fullBriefHref="/studio/briefs/brief_v4" />);
  const approved = text(approvedHtml);
  assert.ok(approved.includes('Approved') && approved.includes('Read full brief') && approved.includes('Open pack →') && !approved.includes('Approve & generate pack'));
  assert.ok(approvedHtml.includes(`href="/studio/packs/${PACK_SUMMARY.pack_id}"`));
  assert.ok(!approved.includes('Pack generated') && !/Approved .* by /.test(approved), 'no pack box and no decider on the card');
});

test('a content pack is said in plain words: its state, the pieces it holds, what is published', () => {
  const pack = PACK_SUMMARY as unknown as PackSummaryV2;
  assert.equal(packLeft(pack), '');
  assert.equal(packLeft({ ...pack, state: 'finishing' }), 'Being written from the approved brief. This takes 5 to 10 minutes.');
  assert.equal(packLeft({ ...pack, state: 'waiting', state_reason: 'This week\'s packs budget is spent. It renews on Monday.' }), 'Waiting: this week\'s packs budget is spent.');
  assert.equal(packLeft({ ...pack, state: 'waiting', state_reason: null }), 'Waiting to continue.');
  assert.equal(packLeft({ ...pack, pieces: pack.pieces.map((p, i) => ({ ...p, published: i < 2 })) }), '2 of 5 pieces published.');
  assert.equal(packLeft({ ...pack, pieces: pack.pieces.map(p => ({ ...p, published: true })) }), 'Every piece is published.');
  const html = renderScreen(<PackCard pack={pack} base="/packs" showWeek />);
  const words = text(html);
  for (const expected of ['WARM', 'Generated', pack.title, '1 Email', '1 Carousel', '3 Reels', 'Open pack →']) assert.ok(words.includes(expected), expected);
  assert.ok(html.includes('href="/packs/pack_1"'));
  assert.ok(text(renderScreen(<PackCard pack={{ ...pack, state: 'finishing' }} base="/packs" />)).includes('Being written'));
  assert.ok(!/open finding|notes? to check|before-publishing notes open|\d\/\d published|Made /.test(words));
});

test('Previous Concepts lists the earlier weeks, and a week opened shows its concepts in the same cards', async t => {
  const earlier = { ...WEEK, week_id: 'week_0', week_start: '2026-09-28', week_end: '2026-10-04' };
  // A prepared week has no concepts yet: it is not listed.
  const prepared = { ...WEEK, week_id: 'week_p', week_start: '2026-09-21', week_end: '2026-09-27', status: 'prepared' } as never;
  const review = { ...REVIEW, week: earlier, angles: [angle()], roster: [], rubric: null };
  const network = stubFetch(url => url.includes('/weeks/week_0') ? json(review) : url.includes('/briefs') ? json({ items: [], total: 0, limit: 50, offset: 0 })
    : url.includes('/packs') ? json({ items: [], total: 0 }) : url.endsWith('/weeks') ? json([WEEK, earlier, prepared]) : url.includes('/me') ? json(ME_APPROVER) : json({ detail: 'Not found' }, 404));
  t.after(network.restore);
  const client = createQueryClient();
  for (const [route, args, data] of [...shell({ packs: true }), seed('/weeks', undefined, [WEEK, earlier, prepared])]) client.setQueryData(queryKey(route as never, args), data);
  const ui = await mount(<PreviousConcepts />, { url: '/previous', client });
  t.after(() => ui.unmount());
  await ui.settle();
  assert.match(ui.text(), /1 previous week/);
  assert.ok(!ui.text().includes('5 Oct – 11 Oct'), 'the latest week is the Weekly Studio\'s');
  assert.ok(!ui.text().includes('21 Sep'), 'a prepared week is not listed');
  assert.ok(!ui.text().includes('Show archived weeks'), 'no archived toggle');
  assert.ok(ui.container.querySelector('a[href="/studio"]')?.textContent?.includes('Weekly Studio'), 'the header leads back to the Weekly Studio');
  const row = ui.container.querySelector('details') as HTMLDetailsElement;
  await act(async () => { row.open = true; row.dispatchEvent(new window.Event('toggle')); });
  await ui.settle(); await ui.settle();
  assert.ok(ui.text().includes('Why we read the reply first') && ui.text().includes('Approve & create brief'), 'the week\'s cards, with the decisions that exist');
});

test('Home: the greeting by first name, the gold line, "Flag idea" for an editor, then the summary', () => {
  const html = renderScreen(<HomePage />, { url: '/home', seed: shell({ packs: true }) });
  const words = text(html);
  assert.ok(words.includes('Good ') && words.includes('Fixture'));
  assert.ok(words.includes('What is waiting for you this week, and what happens next'));
  assert.ok(words.includes('Flag idea'));
  assert.match(html, /aria-label="This week"/);
  assert.ok(!words.includes('Search the publishing calendar'), 'the search filters the calendar, so it is shown with the calendar only');
});
