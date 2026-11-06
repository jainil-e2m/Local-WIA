import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mount } from '../testing/dom';
import { renderScreen } from '../testing/render';
import { BriefGateV4 } from './BriefReaderV4';
import type { BriefVersion, StoredBriefV4 } from '../api/types';

/* E.B33 with 5.F1, 5.B6, 5.F4, 5.F5, 5.B7, 5.F2 (integration): a contract v4 brief goes through the same Gate 2 as v3. Its
   reader sits inside the v2 reader's panels: every v4 field is edited by its path with v4's labels, a refresh carries the
   locked lines (an edited on-screen hook) with what to rewrite, the versions and context are listed and the blockers named. */

const caption = { hook: 'Getting the inquiry is only part of the job.', body: 'We read the reply first.', ending: 'Follow-up is part of the ad.' };
const reel = (kind: 'story' | 'stance' | 'broll_text', extra = {}) => ({ kind, job: `The ${kind} door`, register: kind === 'broll_text' ? 'on_screen' : 'spoken',
  cover_text: `Cover for ${kind}`, on_screen_hook: `Your ads work, then the ${kind} stops`, spoken_opening: kind === 'broll_text' ? null : 'Before we touch your ads',
  script: kind === 'broll_text' ? null : 'Before we touch your ads, we ask one thing.', screens: kind === 'broll_text' ? ['Her inquiries were up.', 'So we started with the reply.'] : null,
  beats: ['a'], personal_lines: [], read_time_seconds: 30, source: 'new_script', caption, offer_descriptor: null, ...extra });
const cta = { choice: 'explicit', track: null, action: 'Reply to this email', offer_connection: null, chosen_by: 'writer' };
const body = {
  approved_angle: { title: 'How we read follow-up', core_perspective: 'Follow-up shapes lead quality.' }, sharpened_point: null,
  central_point: 'The first reply shapes which couples book a tour.',
  strategic_purpose: { pillar: 'WARM', content_type: 'behind_the_scenes', why_now: 'Budget season.', desired_response: 'I want a partner who looks past the click.' },
  intended_shift: { understand: 'u', believe: 'b', do: null }, audience: { who: 'Venue owners', reason_to_care: 'They want tours.' }, point_of_view: 'we',
  wia_perspective: 'We look at what happens after the inquiry.',
  supporting_example: { scene: 'A client call.', wia_move: 'Our strategist asked.', client_contribution: 'The owner explained.', timestamps: ['0:04 the question'],
    details: ['the first reply'], credits: [{ actor: 'our strategist', did: 'asked about the reply' }] },
  narrative_outline: { hooks: [{ style: 'question', text: 'What happens after a couple inquires?' }], problems_desires_symptoms: ['Quiet inquiries'], main_point: 'm', transformation: 't', cta: 'c' },
  cta, cta_why: 'A low barrier.',
  before_publishing: [{ text: 'Confirm the client may be referenced.', kind: 'permission', required: true, answer: null }],
  format_plan: {
    reels: [reel('story'), reel('stance'), reel('broll_text')],
    carousel: { job: 'Go deeper', register: 'written', title: 'When more inquiries are not enough',
      slides: [1, 2, 3, 4, 5, 6, 7].map(n => ({ number: n, job: `Step ${n}`, text: `Slide ${n}: when more inquiries are not enough.` })), caption, offer_descriptor: null },
    email: { job: 'The whole story', register: 'written', send_header: { date: 'Tuesday 27 October', send_time: '9:00', recipients: 'All subscribers' },
      subject_options: ['Why we read the reply before the ads', 'Two'], preview: 'It starts after the inquiry.', opening: 'Hi {{contact.first_name}},', body: 'Body.',
      ending: 'Talk soon, Whitney', offer_descriptor: null },
    stories: null },
  evidence: [], claims: [{ claim_id: 'c1', text: 'Her AI assistant made the changes.', claim_class: 'particular_interaction', status: 'attested', settled_by: 'person',
    field: 'format_plan.reels[0].script', note: null, flag: null, numeric_facts: [], quote: null, public_quote: false, evidence_ids: [], knowledge_base_document: null,
    attested: { kind: 'attested_fact', context_id: 'context_1', by: 'approver@example.invalid', on: '2026-10-23' } }],
};
const HOOK = 'format_plan.reels[0].on_screen_hook';
const brief = {
  brief_id: 'brief_v4', content_hash: 'h4', angle_id: 'a', week_id: 'w', approval_status: 'pending', blockers: [], can_approve: false, can_edit: true, can_review: true,
  schema_version: 'brief_document_v4', locked_fields: [HOOK], anchor: null, selected_evidence: [],
  blocker_items: [{ kind: 'cta_unconfirmed', title: "The call to action is still the writer's suggestion.", action: 'Confirm the call to action.' },
    { kind: 'blocking_finding', title: 'A first-touch line names no concrete subject.', action: 'Edit the line it names.', detail: 'Reel 2: on-screen hook' }],
  context_items: [{ id: 'context_1', kind: 'attested_fact', text: "The client's AI assistant made the changes.", author: 'approver@example.invalid',
    created_at: '2026-10-23T10:00:00Z', gate: 'gate_two', in_brief: true }],
  content_body: { schema_version: 'brief_document_v4', document: { header: { schema_version: 'brief_document_v4', cta, channels: ['reel', 'email', 'carousel', 'caption'], purpose: 'WARM' }, body },
    review: { findings: [], locked_fields: [HOOK] } },
} as unknown as StoredBriefV4;
const versions = [
  { brief_id: 'brief_v4_0', supersedes_id: null, content_hash: 'a', approval_status: 'pending', created_at: '2026-10-23T09:00:00Z', author: 'the system', kind: 'generated', reason: 'Written by the system from the approved card', fields: [] },
  { brief_id: 'brief_v4', supersedes_id: 'brief_v4_0', content_hash: 'h4', approval_status: 'pending', created_at: '2026-10-23T10:00:00Z', author: 'editor@example.invalid', kind: 'edit', reason: 'Edited 1 field', fields: [HOOK] },
] as BriefVersion[];

type Call = [string, string | undefined, unknown];
const recorder = () => {
  const calls: Call[] = [];
  return { calls, perform: async (path: string, method?: string, sent?: unknown) => { calls.push([path, method, sent]); } };
};
const button = (root: HTMLElement, text: string) => [...root.querySelectorAll('button')].find(b => b.textContent?.trim() === text) ?? null;

test('E.B33 at Gate 2: a v4 brief reads in its own layout inside the Gate 2 panels, with v4 labels', () => {
  const html = renderScreen(<BriefGateV4 brief={brief} busy={false} perform={async () => {}} versions={versions} />).replaceAll('&#x27;', "'");
  // The v4 reader, not the v3 one.
  for (const text of ['Strategic purpose and desired response', 'DATE: Tuesday 27 October', 'Format: b-roll with on-screen text', 'Carousel: When more inquiries are not enough'])
    assert.ok(html.includes(text), text);
  assert.ok(!html.includes('>Format plan<'), 'the v3 format plan is not shown for a v4 brief');
  // The Gate 2 panels around it.
  for (const text of ['Edit any field', 'Reel 1: on-screen hook', 'Reel 3: screen 2', 'Carousel title', 'Email DATE (proposed)', 'Beat 1: who',
    'Locked: kept on refresh', 'Refresh with feedback', 'Let the writer rewrite: Reel 1: on-screen hook', 'Call to action not confirmed:',
    'A problem in the copy:', 'Context and attested facts', 'Confirm the CTA', 'Before publishing',
    'attested by approver@example.invalid on 2026-10-23', 'Your decision']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes('Versions (2)') && !html.includes('Whose decision is this?'), 'no version list and no author input on the brief');
  const approved = renderScreen(<BriefGateV4 brief={{ ...brief, approval_status: 'approved' } as StoredBriefV4} busy={false} perform={async () => {}} versions={versions} />).replaceAll('&#x27;', "'");
  assert.ok(approved.includes('Strategic purpose and desired response') && approved.includes('What was said on the call') && approved.includes('Download the brief'));
  for (const removed of ['Refresh with feedback', 'Your decision', 'Edit any field', 'Confirm the CTA', 'Before publishing', 'Context and attested facts', 'Versions (']) {
    assert.ok(!approved.includes(removed), `a decided brief shows its body only: ${removed}`);
  }
});

test('5.F1, 5.B6 on v4: an asset line is edited by its path, and a refresh carries the reviewer\'s words and the lines to release', async t => {
  const { calls, perform } = recorder();
  const ui = await mount(<BriefGateV4 brief={brief} busy={false} perform={perform} versions={versions} />);
  t.after(() => ui.unmount());
  // Edit Reel 2's on-screen hook: its row's Edit button opens its editor, labelled by the v4 map.
  const row = [...ui.container.querySelectorAll('div')].find(d => d.firstElementChild?.querySelector('span')?.textContent === 'Reel 2: on-screen hook'
    && d.firstElementChild?.tagName === 'DIV');
  assert.ok(row, 'Reel 2\'s on-screen hook is a row of the editor');
  await ui.click(button(row as HTMLElement, 'Edit'));
  const input = ui.container.querySelector('input[aria-label="Reel 2: on-screen hook"]') as HTMLInputElement;
  assert.ok(input, 'its editor opens');
  await ui.type(input, 'Your ads are working, and then they stop');
  await ui.click(button(ui.container, 'Save 1 change as a new version'));
  assert.deepEqual(calls.at(-1), ['/briefs/brief_v4', 'PATCH', { expected_hash: 'h4', changes: { 'format_plan.reels[1].on_screen_hook': 'Your ads are working, and then they stop' } }]);

  // Refresh with feedback: live, with the reviewer's words; the locked hook stays unless she releases it.
  const instructions = [...ui.container.querySelectorAll('label')].find(l => l.textContent?.startsWith('What should change?'))?.querySelector('textarea') as HTMLTextAreaElement;
  await ui.type(instructions, 'Make the carousel title about the reader\'s inquiries.');
  await ui.click(button(ui.container, 'Refresh with feedback'));
  assert.deepEqual(calls.at(-1), ['/briefs/brief_v4/revise', 'POST', { expected_hash: 'h4', instructions: 'Make the carousel title about the reader\'s inquiries.',
    mode: 'live', evidence_ids: [], unlock: [] }]);
  const release = [...ui.container.querySelectorAll('label')].find(l => l.textContent === 'Let the writer rewrite: Reel 1: on-screen hook')?.querySelector('input') as HTMLInputElement;
  await ui.tick(release);
  await ui.click(button(ui.container, 'Refresh with feedback'));
  assert.deepEqual((calls.at(-1)?.[2] as { unlock: string[] }).unlock, [HOOK]);

  // An approver's attested fact goes to the brief's context route.
  const panel = ui.container.querySelector('section[aria-label="Context and attested facts"]') as HTMLElement;
  await ui.choose(panel.querySelector('select') as HTMLSelectElement, 'attested_fact');
  await ui.type(panel.querySelector('textarea') as HTMLTextAreaElement, 'Her AI assistant set up the campaign, not her.');
  await ui.click(button(panel, 'Add to this brief (saves a new version)'));
  assert.deepEqual(calls.at(-1), ['/briefs/brief_v4/context', 'POST', { kind: 'attested_fact', text: 'Her AI assistant set up the campaign, not her.' }]);
});
