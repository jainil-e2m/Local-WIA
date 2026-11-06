import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { createQueryClient, queryKey } from '../api/query';
import { ME_APPROVER, WEEK, seed } from '../testing/fixtures';
import { CardReview, contextItemLabel, type CardContextItem } from './CardReview';
import { CARD_FIELDS, cardChanges, editableFields, formValues } from './cardFields';
import { SQLWeeklyAngles } from './SQLWeeklyAngles';
import type { Card, StoredAngle } from '../api/types';

/* 3.B7/3.F2, Gate 1: every card field editable from one field map, refresh with feedback (its wait, refusal and conflict),
   and context with attested facts against interface 2 (POST /angles/{id}/context, the card's context_items), mocked here. */

const card: Card = {
  rank: 1, title: 'How we read your inquiry form first', pillar: 'WARM', content_type: 'behind_the_scenes',
  audience: 'Established planners', core_perspective: 'Lead quality is decided on the form.', why_it_matters: 'Fit beats volume.',
  wia_in_action: 'The strategist asks about the pricing line.', offer_connection: null, moment_ids: ['moment_a'],
  evidence_points: ['The strategist asks about pricing.'], verify_before_publishing: ['Confirm the client may be referenced.'],
  why_selected: 'Shows the WIA move.', series: null,
};
const angle = {
  angle_id: 'angle_one', run_id: 'run_one', content_hash: 'h1', moment_ids: ['moment_a'], has_replacement: false, can_approve: false,
  can_edit: true, content_body: { card, title: card.title }, approval_status: 'pending', selection_status: 'visible',
  matching_result: { status: 'complete', current_batch_flags: [] }, disposition: null, hold: null, refresh: null,
} as unknown as StoredAngle;
const values = card as unknown as Record<string, unknown>;
type Call = [string, string | undefined, unknown];
const recorder = (result: unknown = true) => {
  const calls: Call[] = [];
  return { calls, perform: async (path: string, method?: string, body?: unknown) => { calls.push([path, method, body]); return result; } };
};
const button = (root: HTMLElement, text: string) => [...root.querySelectorAll('button')].find(b => b.textContent === text) ?? null;
const labelled = (root: HTMLElement, start: string) => [...root.querySelectorAll('label')].find(l => l.textContent?.startsWith(start))
  ?.querySelector('input,textarea,select') as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null;

test('3.F2: the field map drives the editor; only the fields a person changed are sent', async () => {
  assert.deepEqual(editableFields(values), ['title', 'pillar', 'content_type', 'series', 'audience', 'core_perspective', 'why_it_matters',
    'wia_in_action', 'offer_connection', 'evidence_points', 'verify_before_publishing', 'why_selected'], 'rank and the cited scenes are fixed');
  const { series: _series, ...v4 } = values;
  assert.ok(!editableFields(v4).includes('series'), 'a version 4 card is never sent version 5\'s series');
  const form = formValues(values);
  assert.equal(form.evidence_points, 'The strategist asks about pricing.');
  assert.deepEqual(cardChanges(values, form), { error: 'Nothing has changed yet.' });
  assert.deepEqual(cardChanges(values, { ...form, title: ' A new title ', evidence_points: 'One\n\n Two ', offer_connection: '' }),
    { changes: { title: 'A new title', evidence_points: ['One', 'Two'] } });
  assert.deepEqual(cardChanges(values, { ...form, why_it_matters: '  ' }), { error: 'Why it matters cannot be empty.' });
  assert.deepEqual(cardChanges(values, { ...form, verify_before_publishing: 'a\nb\nc' }), { error: 'Verify before publishing holds at most 2 items.' });
  assert.deepEqual(cardChanges(values, { ...form, wia_in_action: '' }), { changes: { wia_in_action: null } });
  // A new contract field is shown and edited by one map entry.
  CARD_FIELDS.proof_line = { label: 'Proof line', multiline: true, editable: true };
  try {
    const v7 = { ...values, proof_line: 'Old line.' };
    assert.ok(editableFields(v7).includes('proof_line'));
    assert.deepEqual(cardChanges(v7, { ...formValues(v7), proof_line: 'New line.' }), { changes: { proof_line: 'New line.' } });
    // The card screen no longer lists every stored field ("Details"); the new field is edited in the card's editor.
    const ui = await mount(<CardReview angle={{ ...angle, content_body: { ...angle.content_body, card: v7 } } as unknown as StoredAngle}
      card={v7 as unknown as Card} roster={[]} busy={false} perform={async () => true} />);
    try {
      assert.ok(!ui.text().includes('Old line.'), 'not listed on the card screen');
      await ui.click(button(ui.container, 'Edit this card'));
      assert.equal((labelled(ui.container, 'Proof line') as HTMLTextAreaElement)?.value, 'Old line.');
    } finally { await ui.unmount(); }
  } finally { delete CARD_FIELDS.proof_line; }
});

test('3.B7 (a): any field is edited from the card screen and saved against the hash the reviewer read', async t => {
  const { calls, perform } = recorder();
  const ui = await mount(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={perform} />);
  t.after(() => ui.unmount());
  await ui.click(button(ui.container, 'Edit this card'));
  assert.match(ui.text(), /kept word for word, also when you ask for a refreshed version/);
  await ui.type(labelled(ui.container, 'Title') as HTMLInputElement, 'How we read the form before the ads');
  await ui.choose(labelled(ui.container, 'Pillar') as HTMLSelectElement, 'ATTRACT');
  await ui.type(labelled(ui.container, 'Evidence') as HTMLTextAreaElement, 'The strategist asks about pricing.\nA second point.');
  await ui.click(button(ui.container, 'Save my edits'));
  assert.deepEqual(calls, [['/angles/angle_one', 'PATCH', { expected_hash: 'h1', note: null,
    changes: { title: 'How we read the form before the ads', pillar: 'ATTRACT', evidence_points: ['The strategist asks about pricing.', 'A second point.'] } }]]);
  const viewer = renderScreen(<CardReview angle={{ ...angle, can_edit: false } as StoredAngle} card={card} roster={[]} busy={false} perform={perform} />);
  assert.ok(!viewer.includes('Edit this card') && !viewer.includes('Ask for a refreshed version'), 'nothing the server would refuse is offered');
});

test('3.B7 (b): refresh with feedback names the fields kept, and shows a wait or a refusal in plain words', async t => {
  const { calls, perform } = recorder();
  const edited = { ...angle, content_body: { ...angle.content_body, person_edits: ['title', 'why_it_matters'] } } as unknown as StoredAngle;
  const ui = await mount(<CardReview angle={edited} card={card} roster={[]} busy={false} perform={perform} />);
  t.after(() => ui.unmount());
  assert.match(ui.text(), /Kept word for word because you edited them: Title, Why it matters\./);
  await ui.click(button(ui.container, 'Ask for a refreshed version'));
  assert.match(ui.text(), /Write what the refreshed version should change/);
  assert.equal(calls.length, 0);
  await ui.type(labelled(ui.container, 'What should the refreshed version change?') as HTMLTextAreaElement, 'Lead with the form.');
  assert.ok(!labelled(ui.container, 'Whose decision'),'no author field: the request is recorded as the signed-in person’s');
  await ui.click(button(ui.container, 'Ask for a refreshed version'));
  assert.deepEqual(calls, [['/angles/angle_one/refresh', 'POST', { expected_hash: 'h1', feedback: 'Lead with the form.', author: null }]]);

  const state = (refresh: unknown) => renderScreen(<CardReview angle={{ ...angle, refresh } as unknown as StoredAngle} card={card} roster={[]} busy={false} perform={perform} />);
  const base = { run_id: 'card_refresh_x', feedback: 'Lead with the form.', author: 'W', kept: [] };
  const queued = state({ ...base, status: 'queued', message: null });
  assert.ok(queued.includes('A refreshed version is being written from this feedback') && !queued.includes('>Ask for a refreshed version</button>'));
  const budget = 'This week&#x27;s refreshes budget has USD 0.01 left of USD 2.00, so it was not sent.';
  const waiting = state({ ...base, status: 'waiting', message: "This week's refreshes budget has USD 0.01 left of USD 2.00, so it was not sent." });
  assert.ok(waiting.includes('waiting for budget') && waiting.includes(budget));
  const refused = state({ ...base, status: 'failed', message: 'The model provider refused the request because the account is out of credit, so nothing was written.' });
  assert.ok(refused.includes('could not be written. The model provider refused the request because the account is out of credit'));
  assert.ok(refused.includes('>Lead with the form.</textarea>'), 'the refused feedback is ready to send again');
  for (const html of [queued, waiting, refused]) assert.ok(!html.includes('card_refresh_x'), 'no internal ID on screen (R50)');
});

test('3.B7 (b), R58: a refreshed version says it is new, from which feedback, and what it kept, without naming the model or the system', () => {
  const made = { maker: 'model', feedback: 'Lead with the form.', author: 'Whitney Hodges', requested_by: 'giselle@example.invalid',
    prompt_version: 'card-reframe.feedback.v1', model: 'anthropic/claude-sonnet-5.5', reason: 'r', kept: ['title'],
    changed: ['core_perspective', 'why_it_matters'], run_id: 'card_refresh_x', at: '2026-10-23T10:00:00Z' };
  const html = renderScreen(<CardReview angle={{ ...angle, content_body: { ...angle.content_body, refresh: made } } as unknown as StoredAngle}
    card={card} roster={[]} busy={false} perform={async () => true} />);
  assert.ok(html.includes('A new version, written from your feedback.') && html.includes('Lead with the form.'));
  assert.ok(html.includes('Changed: The point, Why it matters.') && html.includes('Kept word for word as a person wrote it: Title.'));
  for (const removed of ['claude', 'card-reframe', 'core_perspective', 'written by the model', 'the system', 'giselle@example.invalid']) assert.ok(!html.includes(removed), removed);
});

test('5.B7 at Gate 1: context items show with attested facts marked; an approver adds an attested fact', async t => {
  const items: CardContextItem[] = [
    { id: 'ctx_1', kind: 'attested_fact', text: 'The venue doubled its tastings in spring.', author: 'Whitney Hodges', created_at: '2026-10-22T09:00:00Z' },
    { id: 'ctx_2', kind: 'paraphrase', text: 'She said the form scared couples off.', author: 'Giselle', created_at: '2026-10-22T09:05:00Z' },
    { id: 'ctx_3', kind: 'context', text: 'This client is renewing in November.', author: 'Giselle', created_at: '2026-10-22T09:06:00Z' },
  ];
  assert.equal(contextItemLabel(items[0]), 'Attested fact, confirmed by Whitney Hodges on 2026-10-22');
  const withItems = { ...angle, context_items: items } as unknown as StoredAngle;
  // Context sits in the fold "Edit, add context or ask for a new version", which is an editor's or an approver's: a reader
  // (no can_edit) sees the card's rationale without it.
  const reader = renderScreen(<CardReview angle={{ ...withItems, can_edit: false } as StoredAngle} card={card} roster={[]} busy={false} perform={async () => true} canDecide={false} />);
  for (const text of ['Edit, add context or ask for a new version', 'Add context or a fact', 'ctx_1']) assert.ok(!reader.includes(text), text);
  const editor = renderScreen(<CardReview angle={withItems} card={card} roster={[]} busy={false} perform={async () => true} canDecide={false} />);
  for (const text of ['Edit, add context or ask for a new version', 'Attested fact, confirmed by Whitney Hodges on 2026-10-22', 'never quoted as their exact words',
    'Context from Giselle', 'The venue doubled its tastings in spring.']) assert.ok(editor.includes(text), text);
  assert.ok(!editor.includes('ctx_1'));

  const editorOnly = await mount(<CardReview angle={withItems} card={card} roster={[]} busy={false} perform={async () => true} canDecide={false} />);
  await editorOnly.click(button(editorOnly.container, 'Add context or a fact'));
  assert.ok(!editorOnly.text().includes('A fact I confirm is true'), 'an attested fact is an approver\'s (R57)');
  await editorOnly.unmount();

  const { calls, perform } = recorder();
  const ui = await mount(<CardReview angle={withItems} card={card} roster={[]} busy={false} perform={perform} />);
  t.after(() => ui.unmount());
  await ui.click(button(ui.container, 'Add context or a fact'));
  const attested = [...ui.container.querySelectorAll('label')].find(l => l.textContent?.includes('A fact I confirm is true'))?.querySelector('input');
  await ui.tick(attested as HTMLInputElement);
  const box = labelled(ui.container, 'What do you want to add?') as HTMLTextAreaElement;
  await ui.type(box, 'We ran the spring campaign for this venue.');
  await ui.click(button(ui.container, 'Add to this card'));
  assert.deepEqual(calls, [['/angles/angle_one/context', 'POST', { kind: 'attested_fact', text: 'We ran the spring campaign for this venue.' }]]);
  assert.equal(button(ui.container, 'Add to this card'), null, 'the form closes once the context is saved');
});

test('3.B7: a refresh against a stale card shows the conflict handler and keeps the typed feedback', async t => {
  const cardAngle = { ...angle, workflow: 'historical_comparison_v1', first_generated_at: '2026-10-08T11:28:56Z', selected_cta: null,
    base_score: null, adjusted_score: null };
  const review = { week: WEEK, angles: [cardAngle], runs: [], jobs: [], events: [], transcripts: [], selection: null, rubric: null, roster: [] };
  const client = createQueryClient();
  for (const [route, args, data] of [seed('/me', undefined, ME_APPROVER), seed('/weeks', undefined, [WEEK]),
    seed('/weeks/{week_id}', { path: { week_id: WEEK.week_id } }, review), seed('/seeds', undefined, []), seed('/flags', undefined, { briefs: true, packs: false, calendar: false, context: false })]) {
    client.setQueryData(queryKey(route as never, args), data);
  }
  const network = stubFetch((url, options) => {
    if (options?.method === 'POST' && url.endsWith('/angles/angle_one/refresh')) return json({ detail: 'Angle changed; refresh before saving' }, 409);
    if (url.includes('/weeks/')) return json(review);
    if (url.endsWith('/weeks')) return json([WEEK]);
    if (url.endsWith('/me')) return json(ME_APPROVER);
    return json([]);
  });
  t.after(network.restore);
  const ui = await mount(<SQLWeeklyAngles />, { url: `/studio/angles/${WEEK.week_id}/angle_one`, pattern: '/studio/angles/:weekId/:angleId', client });
  t.after(() => ui.unmount());
  await ui.settle();
  const field = labelled(ui.container, 'What should the refreshed version change?') as HTMLTextAreaElement;
  assert.ok(field, 'the refresh form is on the card');
  await ui.type(field, 'Lead with the inquiry form.');
  await ui.click(button(ui.container, 'Ask for a refreshed version'));
  await ui.settle();
  const notice = ui.container.querySelector('[data-conflict]');
  assert.ok(notice, 'the conflict is shown');
  assert.match(notice.textContent ?? '', /Angle changed; refresh before saving/);
  assert.equal((labelled(ui.container, 'What should the refreshed version change?') as HTMLTextAreaElement).value, 'Lead with the inquiry form.',
    'what the reviewer typed is still in the form');
});
