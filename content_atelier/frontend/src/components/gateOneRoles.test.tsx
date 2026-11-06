import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { createQueryClient, queryKey } from '../api/query';
import { ME_APPROVER, REVIEW, WEEK, seed, shell } from '../testing/fixtures';
import { SQLWeeklyAngles } from './SQLWeeklyAngles';
import { CardReview, developBlocker } from './CardReview';
import { renderScreen } from '../testing/render';

/* S.F1, E.F2 (R50): the Gate 1 screen offers a person only what the server will accept from them. Someone who may read
   the week but not decide (a viewer or an editor) sees the cards and why they were chosen, without a decision form that
   the server would refuse with a 403 naming configuration variables. */

const CARD = {
  rank: 1, title: 'Why we read your thank-you emails first', pillar: 'WARM', content_type: 'behind_the_scenes', audience: 'Venue owners',
  core_perspective: 'How WIA learns a business before it advertises it.', why_it_matters: 'Couples book on feeling.', wia_in_action: 'Asked about winter tastings.',
  offer_connection: null, moment_ids: ['moment_a'], evidence_points: ['A question about the calendar.'], verify_before_publishing: ['Confirm the client may be named'],
  why_selected: 'Shows the WIA move.', series: null,
};
const angle = (canDecide: boolean) => ({
  angle_id: 'angle_card', run_id: 'run_1', content_hash: 'hash_card', moment_ids: ['moment_a'], has_replacement: false, workflow: null,
  content_body: { card: CARD, title: CARD.title, argument: '', audience: '', tension: '', take: '', mechanism: '', reader_decision: '', qualifiers: [], risks: [], source_assertions: [], inference: null },
  base_score: null, adjusted_score: null, selection_status: 'visible', approval_status: 'pending', first_generated_at: '2026-10-08T11:28:56Z', selected_cta: null,
  matching_result: { status: 'complete', current_batch_flags: [] }, disposition: null, hold: null,
  can_approve: canDecide, can_edit: canDecide, can_reject: canDecide,
});
const SELECTION = {
  run_id: 'run_1', week_summary: 'One call shows how WIA diagnoses lead quality.', selection_hash: 'sel', ranking: [], unreferenced_moment_ids: [],
  considered_not_selected: [{ index: 0, moment_ids: ['moment_a'], idea: 'Negative keyword tips', reason: 'Too narrow.', disposition: null }],
  internal_insights: [],
};
const ME_VIEWER = { ...ME_APPROVER, role: 'viewer', roles: ['viewer'], can: Object.fromEntries(Object.keys(ME_APPROVER.can).map(name => [name, false])) };

async function open(t: { after: (fn: () => unknown) => void }, me: unknown, canDecide: boolean) {
  const client = createQueryClient();
  const review = { ...REVIEW, angles: [angle(canDecide)], selection: SELECTION, roster: [], runs: [{ run_id: 'run_1', status: 'completed', current_message: null, error_summary: null, has_partial_failures: false }] };
  for (const [route, args, data] of [...shell({}, me), seed('/weeks/{week_id}', { path: { week_id: WEEK.week_id } }, review), seed('/seeds', { query: { status: 'open' } }, [])]) {
    client.setQueryData(queryKey(route as never, args), data);
  }
  const network = stubFetch(url => url.includes('/me') ? json(me) : url.includes('/seeds') ? json([]) : url.endsWith('/weeks') ? json([WEEK]) : json(review));
  t.after(network.restore);
  // The card's full screen, with its decision form, is in the review dialog at the card's own URL.
  const ui = await mount(<SQLWeeklyAngles />, { url: `/studio/angles/${WEEK.week_id}/angle_card`, pattern: '/studio/angles/:weekId/:angleId', client });
  t.after(() => ui.unmount());
  await ui.settle();
  const button = (text: string) => [...ui.container.querySelectorAll('button')].find(b => b.textContent === text) ?? null;
  return { ui, network, button };
}

test('S.F1, E.F2: a person who may not decide sees the cards without a decision form, and is told why', async t => {
  const { ui, network, button } = await open(t, ME_VIEWER, false);
  const text = ui.text();
  assert.ok(text.includes(CARD.title) && text.includes('Other ideas this week (1)') && text.includes('Negative keyword tips'), 'the week, its card and its other ideas are shown');
  assert.ok(!text.includes('Your decision') && !button('Save decision'), 'no decision form');
  assert.ok(!button('Revive as a card') && !button('Record a decision'), 'no action on a dropped idea');
  assert.match(text, /can read these ideas but cannot decide on them/);
  for (const name of ['Reassess saved angles', 'Prepare comparison from saved responses', 'Add a seed']) assert.ok(!button(name), `${name} is not offered`);
  assert.ok(!text.includes('Cycle details'));
  assert.ok(!button('Approve & create brief'), 'no develop decision from the card either');
  const verify = [...ui.container.querySelectorAll('label')].find(l => l.textContent?.includes('Confirm the client may be named'))?.querySelector('input');
  assert.ok(!verify, 'the verify items are a decider\'s, so they are not shown');
  assert.ok(!button('Add context or a fact') && !text.includes('Edit, add context or ask for a new version'), 'no editing for a reader');
  assert.ok(!network.calls.some(call => call.options?.method && call.options.method !== 'GET'), 'nothing was written');
});

test('S.F1, E.F2: an approver gets the decision form, the dropped ideas\' actions and the team tools', async t => {
  const { ui, button } = await open(t, ME_APPROVER, true);
  const text = ui.text();
  assert.ok(text.includes('Your decision') && button('Save decision'), 'the decision form is shown');
  assert.ok(button('Revive as a card') && button('Record a decision'));
  assert.ok(!/cannot decide on them/.test(text));
  assert.ok(text.includes('Verify before publishing') && text.includes('Edit, add context or ask for a new version'));
  assert.ok(button('Approve & create brief'), 'the develop decision from the card');
  // The week's machinery (the cycle panel, the team tools, the seeds) moved to Sources → Weekly cycle, for administrators.
  for (const name of ['Reassess saved angles', 'Add a seed']) assert.ok(!button(name), `${name} is not on the Studio`);
  assert.ok(!text.includes('Cycle details') && !text.includes('Why these ideas'));
});

test('1.F2, E.F2: a decision the server refuses is brought into view, though the message sits above the cards', async t => {
  const scrolled: string[] = [];
  const original = window.Element.prototype.scrollIntoView;
  window.Element.prototype.scrollIntoView = function (this: Element) { scrolled.push(this.textContent ?? ''); };
  t.after(() => { window.Element.prototype.scrollIntoView = original; });
  const { ui, network, button } = await open(t, ME_APPROVER, true);
  network.restore();
  const refusal = stubFetch((_url, options) => options?.method === 'POST' ? json({ error: 'Weekly backend or authentication is unavailable. Retry shortly.' }, 503) : json([]));
  t.after(refusal.restore);
  const verify = [...ui.container.querySelectorAll('label')].find(l => l.textContent?.includes('Confirm the client may be named'))?.querySelector('input');
  await ui.tick(verify as HTMLInputElement);
  await ui.click(button('Save decision'));
  await ui.settle();
  assert.ok(refusal.calls.some(call => call.options?.method === 'POST' && call.url.endsWith('/angles/angle_card/decision')), 'the decision was sent');
  assert.match(ui.text(), /Retry shortly/);
  assert.ok(scrolled.some(text => /Retry shortly/.test(text)), 'the refusal was scrolled into view');
});

test('E.F1, R50: a card marked internal or skipped says so, in words, and never "waiting for your decision"', () => {
  const decision = (disposition: string, reason_code: string) => ({ disposition, reason_code, note: null, author: 'Whitney Hodges', actor: 'whitney@example.invalid',
    hold_until: null, resulting_item_id: null, central_point_kept: null, created_at: '2026-10-12T10:00:00Z' });
  const closed = (disposition: string, reason_code: string) => renderScreen(<CardReview angle={{ ...angle(true), approval_status: 'rejected', can_approve: false, can_reject: false,
    disposition: decision(disposition, reason_code) } as never} card={CARD as never} roster={[]} busy={false} perform={async () => {}} />);
  const skipped = closed('skip', 'distinctiveness');
  assert.ok(!skipped.includes('Waiting for your decision'), 'a skipped card is not waiting');
  assert.ok(skipped.includes('Skipped · 12 Oct 2026'), 'the decision in the screen\'s own words, with its day');
  assert.ok(!skipped.includes('Decision:') && !skipped.includes('Whitney Hodges'), 'no decision line naming its author');
  const internal = closed('internal', 'internal_use');
  assert.ok(!internal.includes('Waiting for your decision') && internal.includes('Kept for internal use'));
  const developed = renderScreen(<CardReview angle={{ ...angle(true), approval_status: 'approved', disposition: decision('develop', 'strong') } as never} card={CARD as never} roster={[]} busy={false} perform={async () => {}} />);
  assert.ok(developed.includes('Approved · 12 Oct 2026') && !developed.includes('Developed') && !developed.includes('Whitney Hodges'));
});

test('E.F2: a card that cannot be developed yet says why in the reviewer\'s words, never that a check is under way when none is', () => {
  assert.equal(developBlocker({ can_approve: true, matching_result: null }), null);
  assert.match(developBlocker({ can_approve: false, matching_result: { status: 'complete', selection: { selection_status: 'suppressed' } } } as never)!, /too close to a better-ranked one/);
  const reframed = developBlocker({ can_approve: false, matching_result: null })!;
  assert.match(reframed, /has not been checked against earlier content yet/);
  assert.match(reframed, /reframe, hold, mark it internal or skip it/);
  assert.ok(!/matching|embedding|reassess/i.test(reframed), 'no pipeline words');
});
