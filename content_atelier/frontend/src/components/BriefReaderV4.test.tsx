import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { BriefBodyV4View, DRAFT_COPY_NOTE, isV4 } from './BriefReaderV4';
import type { BriefBodyV4 } from '../api/types';

const caption = { hook: 'Getting the inquiry is only part of the job.', body: 'We read the reply first.', ending: 'Follow-up is part of the ad.' };
const reel = (kind: 'story' | 'stance' | 'broll_text', extra = {}) => ({ kind, job: `The ${kind} door`, register: kind === 'broll_text' ? 'on_screen' : 'spoken',
  cover_text: `Cover for ${kind}`, on_screen_hook: `Hook for ${kind}`, spoken_opening: null, script: null, screens: null, beats: ['a'], personal_lines: [],
  read_time_seconds: 30, source: 'new_script', caption, offer_descriptor: null, ...extra });
const body = {
  approved_angle: { title: 'How we read follow-up', core_perspective: 'Follow-up shapes lead quality.' }, sharpened_point: null,
  central_point: 'The first reply shapes which couples book a tour.',
  strategic_purpose: { pillar: 'WARM', content_type: 'behind_the_scenes', why_now: 'Budget season.', desired_response: 'I want a partner who looks past the click.' },
  intended_shift: { understand: 'u', believe: 'b', do: null }, audience: { who: 'Venue owners', reason_to_care: 'They want tours.' }, point_of_view: 'we',
  wia_perspective: 'We look at what happens after the inquiry.',
  supporting_example: { scene: 'A client call.', wia_move: 'Our strategist asked.', client_contribution: 'The owner explained.', timestamps: ['0:04 the question'],
    details: ['the first reply'], credits: [{ actor: 'our strategist', did: 'asked about the reply' }] },
  narrative_outline: { hooks: [{ style: 'question', text: 'What happens after a couple inquires?' }], problems_desires_symptoms: ['Quiet inquiries'], main_point: 'm', transformation: 't', cta: 'c' },
  cta: { choice: 'explicit', track: null, action: 'Reply to this email', offer_connection: null, chosen_by: 'writer' }, cta_why: 'A low barrier.',
  before_publishing: [{ text: 'Confirm the client may be referenced.', kind: 'permission', required: true, answer: null }],
  format_plan: {
    reels: [reel('story', { script: 'Before we touch your ads, we ask one thing.' }), reel('broll_text', { screens: ['Her inquiries were up.', 'So we started with the reply.'] })],
    carousel: { job: 'Go deeper', register: 'written', title: 'When more inquiries are not enough', slides: [{ number: 1, job: 'Promise', text: 'When more inquiries are not enough, look at the reply.' }],
      caption, offer_descriptor: null },
    email: { job: 'The whole story', register: 'written', send_header: { date: 'Tuesday', send_time: '9am', recipients: 'All' }, subject_options: ['When more inquiries are not enough', 'Two'],
      preview: 'It starts after the inquiry.', opening: 'Hi {{contact.first_name}},', body: 'Body.', ending: 'Talk soon, Whitney', offer_descriptor: null },
    stories: null },
  evidence: [], claims: [],
} as unknown as BriefBodyV4;

test('E.B33: a v4 brief reads in the 13 October order, then every asset with its v4 fields', () => {
  const html = renderToStaticMarkup(<BriefBodyV4View body={body} />);
  const order = ['Central point', 'Strategic purpose and desired response', 'Audience and reason to care', 'WIA perspective', 'Supporting example',
    'Narrative outline', 'Format and creative approach', 'CTA and essential boundaries', '>Email<', '>Reels<', 'Carousel: When more inquiries are not enough'];
  const at = order.map(h => html.indexOf(h));
  assert.ok(at.every(i => i >= 0), JSON.stringify(at));
  assert.deepEqual([...at].sort((a, b) => a - b), at);
  for (const text of ['DATE: Tuesday', 'On-screen hook: Hook for story', 'Format: b-roll with on-screen text', 'Her inquiries were up.',
    'Desired response: I want a partner', 'A client call.', '0:04 the question', 'Hook: What happens after a couple inquires?', 'Reel 1 (face to camera, story): The story door',
    'Reply to this email', 'Getting the inquiry is only part of the job.']) {
    assert.ok(html.includes(text), text);
  }
  // The body says each thing once, in plain words: no repeated title or core perspective, no sharper point, the example is its
  // scene and its call times, one hook, and the CTA without a "proposed" note or the before-publishing ids.
  for (const removed of ['How we read follow-up', 'Follow-up shapes lead quality.', 'Sharper point', 'Who did what', 'Our strategist asked.', 'The owner explained.',
    'question:', '(proposed', 'P1', 'Confirm the client may be referenced.']) {
    assert.ok(!html.includes(removed), `not in the body: ${removed}`);
  }
  assert.ok(isV4({ content_body: { schema_version: 'brief_document_v4' } }) && !isV4({ content_body: { schema_version: 'brief_document_v3' } }));
});

test('NP.F3: with content packs on, the brief shows its plan and not the draft copy the pack finishes', () => {
  const html = renderToStaticMarkup(<BriefBodyV4View body={body} draftCopy />);
  assert.ok(html.includes('Format and creative approach') && html.includes('Email: The whole story'));
  for (const removed of ['DATE: Tuesday', '>Reels<', 'Carousel: When more inquiries are not enough', 'Before we touch your ads', DRAFT_COPY_NOTE]) {
    assert.ok(!html.includes(removed), `no draft copy: ${removed}`);
  }
});

// ---- the Round 2 writer: Reel 1 the central story, Reels 2 and 3 each a premise of its own, and the premises weighed ----

const premiseReel = (kind: 'central' | 'second' | 'third', production: 'face_to_camera' | 'on_screen_text') => ({
  ...reel(production === 'on_screen_text' ? 'broll_text' : 'story'), kind, production,
  premise: `The ${kind} premise in one sentence.`, takeaway: `What an owner takes from the ${kind} Reel.`, distinct_because: `Why the ${kind} Reel is its own.`,
  timestamps: ['4:12 – the reply'],
});
const r2 = {
  ...body,
  format_plan: {
    ...(body.format_plan as unknown as Record<string, unknown>),
    reels: [premiseReel('central', 'face_to_camera'), premiseReel('second', 'on_screen_text'), premiseReel('third', 'face_to_camera')],
    premise_options: [
      { premise: 'The central premise in one sentence.', type: 'client_story', material: '4:12 the reply', used_for: 'reel_1', why: 'The strongest moment in the call.' },
      { premise: 'Owners answer on weekends too.', type: 'observation', material: '9:30', used_for: null, why: 'Too close to Reel 1.' },
    ],
  },
} as unknown as BriefBodyV4;

test('Round 2: a brief shows each Reel by its premise, takeaway and why it differs, with the premises weighed folded', () => {
  for (const draftCopy of [false, true]) {
    const html = renderToStaticMarkup(<BriefBodyV4View body={r2} draftCopy={draftCopy} />);
    const words = html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ');
    for (const text of ['Reel 1 (Central story · Face to camera): The story door', 'Reel 2 (Own premise · On-screen text): The broll_text door',
      'The second premise in one sentence.', 'Takeaway · What an owner takes from the second Reel.', "Why it's different · Why the third Reel is its own.",
      'Premises considered (2)', 'Became Reel 1 · The strongest moment in the call.', 'Not used · Too close to Reel 1.']) {
      assert.ok(words.includes(text), `${draftCopy ? 'with packs on' : 'with the copy'}: ${text}`);
    }
    assert.ok(html.includes('<details') && !/<details[^>]*\sopen/.test(html), 'the premises are folded');
    assert.ok(!/client_story|used_for|reel_1|premise_options/.test(words), 'no internal words');
  }
  const full = renderToStaticMarkup(<BriefBodyV4View body={r2} />);
  assert.ok(full.includes('Format: Own premise · On-screen text · about 30 seconds'));
});

test('Round 2: Gate 2 edits a new Reel\'s premise, takeaway, why it differs and how it is made; the premises weighed are read, not edited', async () => {
  const { briefFields, optionWords } = await import('./briefFields');
  const fields = briefFields(r2 as unknown as Record<string, unknown>, 'brief_document_v4').flatMap(g => g.fields);
  const field = (path: string) => fields.find(f => f.path === path);
  assert.equal(field('format_plan.reels[1].premise')?.label, 'Reel 2: premise (direction)');
  assert.equal(field('format_plan.reels[1].takeaway')?.label, 'Reel 2: takeaway (direction)');
  assert.equal(field('format_plan.reels[2].distinct_because')?.label, 'Reel 3: why it is different (direction)');
  assert.equal(field('format_plan.reels[0].timestamps[0]')?.label, 'Reel 1: call time 1');
  assert.deepEqual(field('format_plan.reels[1].production')?.options, ['face_to_camera', 'on_screen_text']);
  assert.deepEqual(field('format_plan.reels[1].kind')?.options, ['central', 'second', 'third'], 'a new Reel chooses among the new kinds');
  assert.ok(!fields.some(f => f.path.startsWith('format_plan.premise_options')), 'the premises weighed are not edited');
  assert.deepEqual(['central', 'second', 'on_screen_text', 'broll_text'].map(optionWords), ['Central story', 'Own premise (Reel 2)', 'On-screen text', 'broll text']);
});

test('Round 2: a brief card lists each new Reel by its premise; an earlier Reel by its job', async () => {
  const { BriefOverview } = await import('./studio/BriefCard');
  const card = (b: unknown) => renderToStaticMarkup(<BriefOverview brief={{ content_body: { schema_version: 'brief_document_v4', document: { header: {}, body: b } } } as never} />)
    .replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ');
  const now = card(r2);
  assert.ok(now.includes('Reel 2 (Own premise · On-screen text): The second premise in one sentence.'), now);
  assert.ok(!now.includes('The broll_text door'));
  assert.ok(card(body).includes('Reel 1 (face to camera, story): The story door'));
});
