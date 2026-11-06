import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mount } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { createQueryClient, queryKey } from '../api/query';
import { CardReview } from './CardReview';
import { BriefTextEditor, RefreshPanel, editorSections } from './BriefEditing';
import { briefFields } from './briefFields';
import { packLeft } from './studio/PackCard';
import { TAKES, TimeNote } from './studio/GenerationTime';
import { rowsFor } from './studio/parts';
import type { Card, StoredAngle } from '../api/types';

/* The feedback panels with approving on one click (gates.one_click): "Edit the text" swaps the card or the brief for its editor,
   every line already a field; and each thing that takes time says how long, beside what starts it. */

const card: Card = {
  rank: 1, title: 'How we read your inquiry form first', pillar: 'WARM', content_type: 'behind_the_scenes',
  audience: 'Established planners', point: 'Lead quality is decided on the form.', why_it_matters: 'Fit beats volume.',
  wia_in_action: 'The strategist asks about the pricing line.', offer_connection: null, moment_ids: ['moment_a'],
  evidence_points: ['The strategist asks about pricing.'], verify_before_publishing: ['Confirm the client may be referenced.'],
  why_selected: 'Shows the WIA move.', series: null, guardrail: 'Keep to the call.',
  public_stance: { takes_stance: true, stance: 'The form decides.' },
  belief_ref: 'Belief 3',
} as unknown as Card;
const angle = {
  angle_id: 'angle_one', run_id: 'run_one', content_hash: 'h1', moment_ids: ['moment_a'], has_replacement: false, can_approve: true,
  can_edit: true, content_body: { card, title: card.title }, approval_status: 'pending', selection_status: 'visible',
  matching_result: { status: 'complete', current_batch_flags: [] }, disposition: null, hold: null, refresh: null,
} as unknown as StoredAngle;
const FLAGS = ['/flags', undefined, { one_click: true }] as const;
const button = (root: HTMLElement, text: string) => [...root.querySelectorAll('button')].find(b => b.textContent === text) ?? null;
const labelled = (root: HTMLElement, start: string) => [...root.querySelectorAll('label')].find(l => l.textContent?.startsWith(start))
  ?.querySelector('input,textarea,select') as HTMLInputElement | HTMLTextAreaElement | null;
const oneClick = () => { const client = createQueryClient(); client.setQueryData(queryKey('/flags' as never, undefined as never), { one_click: true }); return client; };

const body = {
  central_point: 'The form decides.', wia_perspective: 'We read the form first.',
  supporting_example: { scene: 'A client call.', timestamps: ['12:00'] },
  format_plan: {
    email: { job: 'Open the point', subject_options: ['One question'], body: 'The first reply shapes it.' },
    carousel: { job: 'Walk through it', title: 'The form', slides: [{ number: 1, job: 'Open', text: 'Slide one text' }] },
    reels: [{ job: 'Show it', on_screen_hook: 'Read the form', script: 'We read the form.', read_time_seconds: 30 }, { job: 'Say it', on_screen_hook: 'Second hook' }],
  },
};

test('the card opens on its feedback: "Edit the text" is one button beside approving, and no editor shows until it is pressed', () => {
  const html = renderScreen(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={async () => true} bare />, { seed: [FLAGS] });
  assert.ok(html.includes('Edit the text') && !html.includes('Edit the text yourself') && !html.includes('Edit this card') && !html.includes('Save my edits'));
  assert.ok(html.includes('Approve &amp; create brief') && html.includes('The brief takes 15 to 30 minutes to write.'));
  assert.ok(html.includes('This takes about a minute.'), 'the refresh says how long, beside its button');
  // At the top of the card, without scrolling past it, and beside approving.
  assert.equal(html.match(/>Edit the text<\/button>/g)?.length, 2);
  assert.ok(html.indexOf('Edit the text') < html.indexOf('Topic &amp; editorial rationale'), 'the first is above the card');
});

test('"Edit the text" replaces the card with its fields, ready to type in, and saves only what changed', async t => {
  const calls: unknown[][] = [];
  const ui = await mount(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={async (...args) => { calls.push(args); return true; }} bare />, { client: oneClick() });
  t.after(() => ui.unmount());
  await ui.click(button(ui.container, 'Edit the text'));
  assert.ok(!ui.text().includes('Your feedback') && !ui.text().includes('Approve & create brief'), 'nothing else is asked meanwhile');
  assert.equal(labelled(ui.container, 'Title')?.value, card.title, 'every line is already a field');
  assert.equal(labelled(ui.container, 'The stance')?.value, 'The form decides.');
  assert.match(ui.text(), /Nothing changed yet/);
  assert.equal(ui.container.querySelector('details[open]'), null, "the strategist's own fields stay folded");
  await ui.type(labelled(ui.container, 'Title') as HTMLInputElement, 'A sharper title');
  assert.match(ui.text(), /1 change to save/);
  assert.ok(!labelled(ui.container, 'Why are you changing this'), 'a plain edit asks no reason');
  await ui.click(button(ui.container, 'Save my edits'));
  assert.deepEqual(calls, [['/angles/angle_one', 'PATCH', { expected_hash: 'h1', note: null, changes: { title: 'A sharper title' } }]]);
  assert.ok(button(ui.container, 'Edit the text'), 'a saved edit returns to the card');
});

test('editing asks for a reason only when the server needs one, and Cancel changes nothing', async t => {
  const calls: unknown[][] = [];
  const ui = await mount(<CardReview angle={angle} card={card} roster={[]} busy={false} perform={async (...args) => { calls.push(args); return true; }} bare />, { client: oneClick() });
  t.after(() => ui.unmount());
  await ui.click(button(ui.container, 'Edit the text'));
  await ui.type(labelled(ui.container, 'Verify before publishing') as HTMLTextAreaElement, '');
  assert.ok(labelled(ui.container, 'Why are you changing this'), 'removing an item to verify asks why');
  await ui.click(button(ui.container, 'Cancel'));
  assert.equal(calls.length, 0);
  assert.ok(button(ui.container, 'Edit the text'));
});

test('while a refresh is on its way the card is neither approved nor edited, and says how long', () => {
  const working = { ...angle, refresh: { status: 'running', feedback: 'Lead with the form.', message: null } } as unknown as StoredAngle;
  const html = renderScreen(<CardReview angle={working} card={card} roster={[]} busy={false} perform={async () => true} bare />, { seed: [FLAGS] });
  assert.ok(html.includes('This takes about a minute. You can close this and come back.'));
  assert.match(html, /<button[^>]*disabled=""[^>]*>Approve &amp; create brief/);
  assert.match(html, /<button[^>]*disabled=""[^>]*>Edit the text/);
  assert.ok(!html.includes('The brief takes 15 to 30 minutes to write.'));
});

test('the brief editor has a section per piece, labels without the piece\'s name, and the writer\'s directions folded', () => {
  const sections = editorSections(briefFields(body, 'brief_document_v4'));
  assert.deepEqual(sections.map(s => s.label), ['Central point', 'WIA perspective', 'Supporting example', 'Email', 'Carousel', 'Reel 1', 'Reel 2']);
  const email = sections.find(s => s.label === 'Email')!;
  assert.ok(email.piece && email.fields.some(f => f.label === 'Subject option 1' && f.path === 'format_plan.email.subject_options[0]'));
  const reel = sections.find(s => s.label === 'Reel 1')!;
  assert.ok(reel.fields.some(f => f.label === 'On-screen hook'), 'no "Reel 1:" in the label');
  const html = renderScreen(<BriefTextEditor body={body} schemaVersion="brief_document_v4" locks={['wia_perspective']} expected="h" briefId="b" busy={false} perform={async () => {}} onClose={() => {}} />);
  assert.ok(html.includes('Edit the text') && html.includes('A person wrote this: kept on refresh') && html.includes('Nothing changed yet'));
  assert.ok(!html.includes('Edit any field') && !/>Edit</.test(html), 'no field-by-field Edit links');
  assert.ok(html.includes('More fields: direction and details'), "the writer's directions are folded");
});

test('the brief editor reads in the field map\'s order, whatever order the database keeps a record in', () => {
  const stored = { strategic_purpose: { why_now: 'w', pillar: 'WARM', desired_response: 'd', content_type: 'education' },
    before_publishing: [{ text: 'Check it', required: true, kind: 'fact', answer: null }],
    format_plan: { email: { body: 'b', ending: 'e', opening: 'o', preview: 'p', subject_options: ['s'] } } };
  const sections = editorSections(briefFields(stored, 'brief_document_v4'));
  assert.deepEqual(sections.find(s => s.key === 'strategic_purpose')!.fields.map(f => f.label), ['Pillar', 'Content type', 'Why now', 'Desired response']);
  assert.deepEqual(sections.find(s => s.key === 'email')!.fields.map(f => f.label), ['Subject option 1', 'Preview', 'Opening', 'Body', 'Ending']);
  assert.equal(sections.find(s => s.key === 'before_publishing')!.fields[0].label, 'Item 1', 'no writer\'s numbering');
});

test('the brief editor saves the lines changed together, by their paths', async t => {
  const calls: unknown[][] = [];
  const ui = await mount(<BriefTextEditor body={body} schemaVersion="brief_document_v4" locks={[]} expected="h" briefId="b" busy={false} perform={async (...args) => { calls.push(args); }} onClose={() => {}} />);
  t.after(() => ui.unmount());
  await ui.type(labelled(ui.container, 'WIA perspective') as HTMLTextAreaElement, 'We read it twice.');
  await ui.type(labelled(ui.container, 'Script') as HTMLTextAreaElement, 'New script.');
  assert.match(ui.text(), /2 changes to save/);
  await ui.type(labelled(ui.container, 'Script') as HTMLTextAreaElement, 'We read the form.');
  assert.match(ui.text(), /1 change to save/, 'typing a line back as it was is no change');
  await ui.click(button(ui.container, 'Save my edits'));
  assert.deepEqual(calls, [['/briefs/b', 'PATCH', { expected_hash: 'h', changes: { wia_perspective: 'We read it twice.' } }]]);
});

test('every wait says how long, from one place', () => {
  assert.equal(TAKES.brief, '15 to 30 minutes');
  const idle = renderScreen(<RefreshPanel briefId="b" expected="h" locks={[]} canEdit busy={false} perform={async () => {}} />);
  assert.ok(idle.includes('A new version of the brief takes 15 to 30 minutes.') && idle.includes('Refresh with feedback'));
  const running = renderScreen(<RefreshPanel briefId="b" expected="h" locks={[]} canEdit busy={false} perform={async () => {}} running />);
  assert.ok(running.includes('This takes 15 to 30 minutes. You can close this and come back.') && !running.includes('>Refresh with feedback<'));
  assert.match(packLeft({ state: 'finishing', pieces: [], state_reason: null }), /This takes 5 to 10 minutes\./);
  assert.ok(renderScreen(<TimeNote>Soon</TimeNote>).includes('Soon'));
});

test('a text area opens tall enough for its text', () => {
  assert.equal(rowsFor('short'), 2);
  assert.equal(rowsFor('x'.repeat(440)), 5);
  assert.equal(rowsFor('a\nb\nc\nd'), 4);
  assert.equal(rowsFor('x'.repeat(90_000)), 16, 'with a ceiling');
  assert.equal(rowsFor(null, 3), 3);
});
