import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mount } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { CardReview } from './CardReview';
import { cardChanges, editableFields, formValues } from './cardFields';
import { CycleDetailView } from './CyclePanel';
import { StrategyBriefPanel } from './StrategyBrief';
import type { Card, CycleDetail, StoredAngle, StrategyBrief } from '../api/types';

/* Strategist v7 at Gate 1 (E.B30, E.B32, D31; integration): the v7 fields in Whitney's angle-card order (plan section 4.2),
   their editors (a choice for each enumeration, a tick box with its text for the {bool, text} pairs), the reasons a card is
   not for public content, the stance an approver confirms before developing, and the window's strategy brief (E.B28). */

const card = {
  rank: 1, title: 'How we read a planner’s inquiry form before the ads', pillar: 'WARM', content_type: 'behind_the_scenes', series: null,
  audience: 'Established planners who already run ads', point: 'Lead quality is decided on the form, not in the ad account.',
  point_is_about: 'wia_belief', surprise_for_experienced_advertiser: { surprising: true, reason: 'They tune the ads first.' },
  reader_takeaway: 'I want a team that reads the whole path.', reader_fit: { buyer: 'elevate', buyer_statement: 'Owners who want leads that book.', why: 'Lead quality is their pain.' },
  belief_ref: 'B3', why_it_matters: 'Fit beats volume.', wia_in_action: 'The strategist asks about the pricing line.',
  evidence_points: ['The strategist asks about pricing.'], guardrail: 'Do not name the client; keep the pricing vague.',
  offer_fit: { offer: 'ELEVATE', cta_slot: 'soft_invitation', calendar_note: 'ELEVATE is open this window.' },
  public_stance: { takes_stance: true, stance: 'AI cannot replace the strategy behind your ads.' }, recurrence: 'Came up on two calls.',
  moment_ids: ['moment_a'], verify_before_publishing: [], why_selected: 'Shows the WIA move.',
} as unknown as Card;
const angle = {
  angle_id: 'angle_one', run_id: 'run_one', content_hash: 'h1', moment_ids: ['moment_a'], has_replacement: false, can_approve: true,
  can_edit: true, content_body: { card, title: card.title }, approval_status: 'pending', selection_status: 'visible',
  matching_result: { status: 'complete', current_batch_flags: [] }, disposition: null, hold: null, refresh: null, stance_confirmation: null, public_use: null,
} as unknown as StoredAngle;
const values = card as unknown as Record<string, unknown>;
type Call = [string, string | undefined, unknown];
const recorder = () => {
  const calls: Call[] = [];
  return { calls, perform: async (path: string, method?: string, body?: unknown) => { calls.push([path, method, body]); return true; } };
};
const button = (root: HTMLElement, text: string) => [...root.querySelectorAll('button')].find(b => b.textContent === text) ?? null;
const labelled = (root: HTMLElement, start: string) => [...root.querySelectorAll('label')].find(l => l.textContent?.startsWith(start))
  ?.querySelector('input,textarea,select') as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null;
const fieldset = (root: HTMLElement, legend: string) => [...root.querySelectorAll('fieldset')].find(f => f.querySelector('legend')?.textContent === legend) as HTMLElement;

test('E.B30 integration: a v7 card shows its fields in Whitney’s order, and every v7 field has an editor', () => {
  assert.deepEqual(editableFields(values), ['title', 'pillar', 'content_type', 'series', 'audience', 'point', 'point_is_about',
    'surprise_for_experienced_advertiser', 'reader_takeaway', 'reader_fit', 'belief_ref', 'why_it_matters', 'wia_in_action', 'evidence_points',
    'recurrence', 'guardrail', 'offer_fit', 'public_stance', 'verify_before_publishing', 'why_selected']);
  assert.ok(!editableFields(values).includes('core_perspective'), 'a v7 card has no core perspective to edit');
  // The card screen reads as the rationale in plain words (the mockup's order); the strategist's internal fields are edited in
  // the card's editor but no longer listed on the screen ("Details" is gone).
  const html = renderScreen(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={async () => true} />).replaceAll('&#x27;', "'").replaceAll('&amp;', '&');
  const order = ['Topic & editorial rationale', 'Content pillar / type', 'Audience', 'Why this matters', 'WIA’s expertise or process', 'Evidence in the referenced call',
    'Editorial guardrail / next step', 'This card takes a public stance'];
  const at = order.map(label => html.indexOf(label));
  assert.ok(at.every(i => i >= 0), JSON.stringify(order.filter((_, i) => at[i] < 0)));
  assert.deepEqual([...at].sort((a, b) => a - b), at, 'pillar and type; audience; why; expertise; evidence; guardrail and next step; then the stance');
  for (const text of ['Lead quality is decided on the form, not in the ad account.', 'Next step: A soft invitation · ELEVATE', 'AI cannot replace the strategy behind your ads.']) {
    assert.ok(html.includes(text), text);
  }
  for (const internal of ['What the point is about', 'Would it surprise an owner who already runs ads?', 'Who the reader is', 'The belief it proves', 'B3', '>Details<']) {
    assert.ok(!html.includes(internal), `not listed on the card screen: ${internal}`);
  }
  for (const stored of ['wia_belief', 'soft_invitation', 'point_is_about', 'takes_stance']) assert.ok(!html.includes(stored), `no stored name on screen: ${stored}`);
});

test('E.B30 integration: the structured v7 fields are edited as choices and tick boxes, and only what changed is sent', async t => {
  const form = formValues(values);
  assert.equal(form['surprise_for_experienced_advertiser.surprising'], 'true');
  assert.equal(form['offer_fit.cta_slot'], 'soft_invitation');
  assert.deepEqual(cardChanges(values, form), { error: 'Nothing has changed yet.' });
  // The database keeps a record's keys in its own order: the same value is not a change.
  const reordered = { ...values, reader_fit: { why: 'Lead quality is their pain.', buyer_statement: 'Owners who want leads that book.', buyer: 'elevate' } };
  assert.deepEqual(cardChanges(reordered, formValues(reordered)), { error: 'Nothing has changed yet.' });
  assert.deepEqual(cardChanges(values, { ...form, 'public_stance.takes_stance': 'false', 'public_stance.stance': '' }),
    { changes: { public_stance: { takes_stance: false, stance: null } } });
  assert.deepEqual(cardChanges(values, { ...form, 'public_stance.stance': ' ' }), { error: 'Public stance: the stance cannot be empty.' });
  assert.deepEqual(cardChanges(values, { ...form, 'offer_fit.offer': '' }),
    { changes: { offer_fit: { offer: null, cta_slot: 'soft_invitation', calendar_note: 'ELEVATE is open this window.' } } });
  assert.deepEqual(cardChanges(values, { ...form, 'reader_fit.why': '' }), { error: 'Who the reader is: why it fits cannot be empty.' });

  const { calls, perform } = recorder();
  const ui = await mount(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={perform} />);
  t.after(() => ui.unmount());
  await ui.click(button(ui.container, 'Edit this card'));
  await ui.choose(labelled(ui.container, 'What the point is about') as HTMLSelectElement, 'client_experience');
  const surprise = fieldset(ui.container, 'Would it surprise an owner who already runs ads?');
  await ui.tick(surprise.querySelector('input[type="checkbox"]') as HTMLInputElement);
  await ui.type(surprise.querySelector('textarea') as HTMLTextAreaElement, 'Most of them have heard it before.');
  await ui.choose(fieldset(ui.container, 'Next step: the offer and CTA').querySelector('select') as HTMLSelectElement, 'offer_cta');
  await ui.click(button(ui.container, 'Save my edits'));
  assert.deepEqual(calls, [['/angles/angle_one', 'PATCH', { expected_hash: 'h1', note: null, changes: {
    point_is_about: 'client_experience',
    surprise_for_experienced_advertiser: { surprising: false, reason: 'Most of them have heard it before.' },
    offer_fit: { offer: 'ELEVATE', cta_slot: 'offer_cta', calendar_note: 'ELEVATE is open this window.' } } }]]);
});

test('D31 integration: an approver confirms a public stance before developing; until then develop is held, with the reason', async t => {
  const { calls, perform } = recorder();
  const ui = await mount(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={perform} />);
  t.after(() => ui.unmount());
  assert.match(ui.text(), /This card takes a public stance: “AI cannot replace the strategy behind your ads\.”/);
  assert.match(ui.text(), /an approver confirms the stance above before it can be developed/);
  assert.equal((button(ui.container, 'Save decision') as HTMLButtonElement).disabled, true, 'develop waits for the confirmation');
  await ui.type(ui.container.querySelector('textarea[aria-label="Optional public stance note"]') as HTMLTextAreaElement, 'Confirmed on the call.');
  await ui.click(button(ui.container, 'Confirm this public stance'));
  assert.deepEqual(calls, [['/angles/angle_one/stance', 'POST', { expected_hash: 'h1', note: 'Confirmed on the call.' }]]);

  const confirmed = { ...angle, stance_confirmation: { stance: 'AI cannot replace the strategy behind your ads.', point: 'p', by: 'Whitney Hodges',
    at: '2026-10-23T09:00:00Z', note: null } } as unknown as StoredAngle;
  const after = renderScreen(<CardReview angle={confirmed} card={card} roster={[]} busy={false} perform={perform} />);
  assert.ok(after.includes('Public stance confirmed by Whitney Hodges on 2026-10-23') && !after.includes('Confirm this public stance'));
  assert.ok(!/<button[^>]*disabled=""[^>]*>Save decision<\/button>/.test(after), 'once confirmed, the card can be developed');
  const editor = renderScreen(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={perform} canDecide={false} />);
  assert.ok(editor.includes('An approver confirms it here.') && !editor.includes('Confirm this public stance'), 'only an approver is offered the confirmation');
});

test('E.B30 integration: a card rejected for public use says why in plain words and cannot be developed', () => {
  const reasons = ['Rejected for public use: the point is about a platform or tactic, not a WIA belief.'];
  const rejected = { ...angle, public_use: { allowed: false, reasons, kinds: ['point_is_tactic'] } } as unknown as StoredAngle;
  const html = renderScreen(<CardReview angle={rejected} card={{ ...card, public_stance: { takes_stance: false, stance: null } } as unknown as Card}
    roster={[]} busy={false} perform={async () => true} />);
  assert.ok(html.includes('Not for public content as it stands') && html.includes(reasons[0]) && html.includes('mark it internal'));
  assert.ok(!html.includes('point_is_tactic'), 'the check\'s stored kind is not shown');
  assert.match(html, /<button[^>]*disabled=""[^>]*>Save decision<\/button>/);
});

const strategy = {
  version: 'strategy-brief.v1', made_by: 'system', brief_hash: 'sb1', on: '2026-10-23', publishing_window: { start: '2026-10-26', end: '2026-11-01' },
  season: { name: 'engagement_season_run_up', label: 'Six weeks to engagement season', weeks_to_engagement_season: 6 }, mix: { ATTRACT: 1, WARM: 1, CONVERT: 1 },
  beliefs_to_prove: [{ id: 'b3', ref: 'B3', belief: 'Lead quality is decided before the ad account.', stage: 'WARM', offer: 'ELEVATE', offers: ['ELEVATE'],
    last_proved: '2026-09-29', quotes: [], do_not_repeat: [{ published_on: '2026-10-06', key_message: 'Your form sets the lead quality.', title: 'The form post' }] }],
  live_offers: [{ offer: 'ELEVATE', status: 'open', sellable: true, ends: '2026-11-15', do_not_undercut: ['Never call the strategy session free'], terms: [] }],
  recent_central_points: [{ published_on: '2026-10-06', key_message: 'Your form sets the lead quality.' }], priority_series: [], content_plan: [], warnings: [], inputs: {},
} as unknown as StrategyBrief;

test('E.B28 integration: the window’s strategy brief shows its beliefs to prove and live offers, at Gate 1 and on the cycle', () => {
  const html = renderScreen(<StrategyBriefPanel brief={strategy} />);
  for (const text of ['This window’s strategy brief', 'Made by the system from the knowledge base on 2026-10-23', 'Six weeks to engagement season',
    'Lead quality is decided before the ad account.', '(WARM · offer: ELEVATE · last proved 2026-09-29)', 'Do not repeat: The form post',
    'ELEVATE · open · until 2026-11-15. Do not undercut: Never call the strategy session free', 'Recent central points (1)']) assert.ok(html.includes(text), text);
  const cycle = { run_id: 'run_1', week_id: 'w', status: 'completed', document_count: 1, coverage_state: 'complete', scenes_sent: 2, scenes_verified: 2,
    documents: [], stages: [], scene_coverage: { state: 'complete', documents: [], not_sent: [] }, strategy_brief: strategy } as unknown as CycleDetail;
  const detail = renderScreen(<CycleDetailView cycle={cycle} />);
  assert.ok(detail.includes('Beliefs to prove') && detail.includes('Lead quality is decided before the ad account.') && !detail.includes('Do not repeat'),
    'the cycle shows the compact brief');
  assert.ok(!renderScreen(<CycleDetailView cycle={{ ...cycle, strategy_brief: null } as CycleDetail} />).includes('strategy brief'), 'a cycle before E.B28 has none');
});
