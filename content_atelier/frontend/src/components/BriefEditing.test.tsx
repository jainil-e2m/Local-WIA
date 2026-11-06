import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { renderScreen } from '../testing/render';
import { briefFields, fieldChanges, fieldLabel, isLocked, pattern } from './briefFields';
import { BlockerList, VersionList, blockerName, refreshRequest } from './BriefEditing';
import { BriefReaderV2, claimStatus, type StoredBriefV3 } from './BriefReaderV2';
import { contextLine, contextPath, contextRequest, GateContextPanel } from './shared/GateContext';
import type { BriefVersion } from '../api/types';

const plan = {
  reels: [{ job: 'Show the move', cover_text: 'The question we ask', spoken_opening: 'Before we touch your ads', script: 'Before we touch your ads, we ask one thing.',
    beats: ['a', 'b'], read_time_seconds: 30, source: 'new_script' }],
  carousel: { job: 'Walk through it', slides: [1, 2, 3].map(n => ({ number: n, job: `Step ${n}`, text: `Slide ${n} text` })) },
  email: { subject_options: ['One question', 'Before the ads'], preview: 'It starts after the inquiry.', opening: 'Hi {{contact.first_name}},', body: 'The first reply shapes it.', ending: 'Talk soon' },
  caption: { hook: 'Most of the sale happens after the click.', body: 'The reply carries it.', ending: 'Save this.' }, stories: null,
};
const body = {
  approved_angle: { title: 'Why we ask about follow-up first', core_perspective: 'Follow-up shapes lead quality.' }, sharpened_point: null,
  strategic_purpose: { pillar: 'WARM', content_type: 'behind_the_scenes', why_now: 'Budget season.' },
  audience: { who: 'Venue owners', reason_to_care: 'They want tours.' }, intended_shift: { understand: 'u', believe: 'b', do: null },
  point_of_view: 'we', wia_perspective: 'We look at what happens after the inquiry.',
  supporting_example: { scene: 'A client call.', wia_move: 'Our strategist asked about the first reply.', client_contribution: 'The client described it.' },
  narrative_outline: { hooks: [{ style: 'observation', text: 'The first reply decides more than the ad does.' }], problems_desires_symptoms: ['Quiet inquiries'], main_point: 'Follow-up is part of the ad.', transformation: 't', cta: 'Reply' },
  format_plan: plan, cta: { choice: 'explicit', track: null, action: 'Reply to this email', offer_connection: null, chosen_by: 'writer' }, cta_why: 'A low barrier.',
  before_publishing: [{ text: 'Confirm the client may be named.', kind: 'permission', required: true, answer: null }],
  evidence: [], claims: [{ claim_id: 'c1', text: 'Her AI assistant made the changes.', claim_class: 'particular_interaction', status: 'attested', settled_by: 'person',
    field: 'supporting_example.scene', note: null, flag: null, numeric_facts: [], quote: null, public_quote: false, evidence_ids: [], knowledge_base_document: null,
    attested: { kind: 'attested_fact', context_id: 'context_1', by: 'approver@example.invalid', on: '2026-10-22' } }],
};

test('5.F1, 5.F4: the walker lists every asset field of a v3 brief by its path, and the map labels it', () => {
  const fields = briefFields(body as unknown as Record<string, unknown>, 'brief_document_v3').flatMap(g => g.fields);
  const paths = fields.map(f => f.path);
  for (const path of ['format_plan.email.subject_options[0]', 'format_plan.email.subject_options[1]', 'format_plan.email.preview', 'format_plan.email.body',
    'format_plan.reels[0].cover_text', 'format_plan.reels[0].spoken_opening', 'format_plan.reels[0].script', 'format_plan.carousel.slides[2].text',
    'format_plan.caption.hook', 'format_plan.caption.body', 'format_plan.caption.ending', 'wia_perspective', 'supporting_example.scene', 'cta_why',
    'narrative_outline.hooks[0].text', 'intended_shift.do', 'before_publishing[0].text']) assert.ok(paths.includes(path), path);
  for (const path of ['approved_angle.title', 'claims[0].text', 'cta.action', 'format_plan.carousel.slides[0].number', 'before_publishing[0].answer',
    'before_publishing[0].required', 'sharpened_point']) assert.ok(!paths.includes(path), `${path} is not edited here`);
  assert.equal(fieldLabel('format_plan.reels[0].cover_text'), 'Reel 1: cover');
  assert.equal(fieldLabel('format_plan.carousel.slides[2].text'), 'Slide 3');
  assert.equal(fieldLabel('format_plan.email.subject_options[1]'), 'Email subject option 2');
  assert.deepEqual(pattern('format_plan.reels[1].beats[0]'), { key: 'format_plan.reels[].beats[]', indexes: [1, 0] });
  assert.equal(fields.find(f => f.path === 'format_plan.reels[0].read_time_seconds')?.kind, 'number');
  assert.deepEqual(fields.find(f => f.path === 'point_of_view')?.options, ['we', 'I']);
});

test('interface 4: a v4 field the map does not know yet is shown and editable, with a label made from its path', () => {
  const v4 = { ...body, format_plan: { ...plan, reels: [{ ...plan.reels[0], on_screen_hook: 'Your ads work, then they stop' }], email: { ...plan.email, send_header: 'Tuesday 9am' } } };
  const fields = briefFields(v4 as unknown as Record<string, unknown>, 'brief_document_v4').flatMap(g => g.fields);
  const hook = fields.find(f => f.path === 'format_plan.reels[0].on_screen_hook');
  assert.ok(hook && hook.kind === 'text' && hook.label === 'Reel 1: on-screen hook', JSON.stringify(hook));
  assert.equal(fields.find(f => f.path === 'format_plan.email.send_header')?.label, 'Email: send header');
});

test('E.B33: contract v4 is edited in the 13 October order, every asset field labelled', () => {
  const reel = { ...plan.reels[0], kind: 'broll_text', register: 'on_screen', on_screen_hook: 'Her inquiries were up', screens: ['One.', 'Two.'],
    personal_lines: [], caption: { hook: 'h', body: 'b', ending: 'e' }, offer_descriptor: null };
  const v4 = { ...body, central_point: 'The first reply shapes which couples book.',
    strategic_purpose: { ...body.strategic_purpose, desired_response: 'I want a partner who looks past the click.' },
    supporting_example: { ...body.supporting_example, timestamps: ['0:04 the question'], details: ['the first reply'], credits: [{ actor: 'our strategist', did: 'asked' }] },
    format_plan: { reels: [reel], carousel: { ...plan.carousel, title: 'When more inquiries are not enough', register: 'written', caption: { hook: 'h', body: 'b', ending: 'e' }, offer_descriptor: null },
      email: { ...plan.email, job: 'The whole story', register: 'written', send_header: { date: 'Tuesday', send_time: '9am', recipients: 'All' }, offer_descriptor: null }, stories: null } };
  const groups = briefFields(v4 as unknown as Record<string, unknown>, 'brief_document_v4');
  assert.deepEqual(groups.map(g => g.section).slice(0, 3), ['central_point', 'strategic_purpose', 'intended_shift']);
  assert.equal(groups.at(-1)?.section, 'format_plan', 'the brief first, then the copy of every asset');
  const label = (path: string) => groups.flatMap(g => g.fields).find(f => f.path === path)?.label;
  assert.equal(label('format_plan.reels[0].screens[1]'), 'Reel 1: screen 2');
  assert.equal(label('format_plan.reels[0].caption.body'), 'Reel 1: caption body');
  assert.equal(label('format_plan.carousel.title'), 'Carousel title');
  assert.equal(label('format_plan.email.send_header.date'), 'Email DATE (proposed)');
  assert.equal(label('supporting_example.credits[0].actor'), 'Beat 1: who');
  assert.deepEqual(groups.flatMap(g => g.fields).find(f => f.path === 'format_plan.reels[0].kind')?.options, ['story', 'stance', 'broll_text']);
  assert.ok(!groups.flatMap(g => g.fields).some(f => f.path === 'format_plan.email.register'), 'the register of an email is fixed');
});

test('5.F1, 5.F5: only the changed lines are sent, by path, and a lock covers its line and what is inside it', () => {
  const fields = briefFields(body as unknown as Record<string, unknown>, 'brief_document_v3').flatMap(g => g.fields);
  assert.deepEqual(fieldChanges('h', fields, { 'format_plan.email.subject_options[0]': 'Why we ask about the first reply', 'format_plan.email.preview': plan.email.preview }),
    { body: { expected_hash: 'h', changes: { 'format_plan.email.subject_options[0]': 'Why we ask about the first reply' } } });
  assert.deepEqual(fieldChanges('h', fields, {}), { error: 'Nothing changed.' });
  assert.match((fieldChanges('h', fields, { 'format_plan.caption.hook': '  ' }) as { error: string }).error, /cannot be empty/);
  assert.deepEqual(fieldChanges('h', fields, { 'format_plan.reels[0].read_time_seconds': '45', 'intended_shift.do': '' }),
    { body: { expected_hash: 'h', changes: { 'format_plan.reels[0].read_time_seconds': 45 } } });
  assert.ok(isLocked('format_plan.email.subject_options[0]', ['format_plan.email.subject_options[0]']));
  assert.ok(isLocked('format_plan.email.preview', ['format_plan']), 'a lock saved before 22 October covers its whole section');
  assert.ok(!isLocked('format_plan.email.preview', ['format_plan.email.subject_options[0]']));
});

test('5.B6: refresh with feedback is live from the screen and carries the released lines', () => {
  assert.deepEqual(refreshRequest('h', ' Make the preview about the reader. ', ['format_plan.email.subject_options[0]']),
    { body: { expected_hash: 'h', instructions: 'Make the preview about the reader.', mode: 'live', evidence_ids: [], unlock: ['format_plan.email.subject_options[0]'] } });
  assert.deepEqual(refreshRequest('h', ' ', []), { error: 'Say what the refreshed version should change.' });
});

const brief = {
  brief_id: 'brief_1', content_hash: 'h', angle_id: 'a', week_id: 'w', approval_status: 'pending', blockers: [], can_approve: false, can_edit: true, can_review: true,
  schema_version: 'brief_document_v3', locked_fields: ['format_plan.email.subject_options[0]'],
  blocker_items: [
    { kind: 'open_question', title: 'A required question has no answer yet.', action: 'Answer each required item under "Before publishing".' },
    { kind: 'blocking_finding', title: 'The copy has a problem to fix.', action: 'Edit the line it names.', detail: 'The caption says "x": the call does not support it.' },
    { kind: 'stale', title: 'A newer version of this brief exists.', action: 'Open the newest version from the versions list.' },
    { kind: 'cta_unconfirmed', title: "The call to action is still the writer's suggestion.", action: 'Confirm the call to action.' },
    { kind: 'role', title: 'Only an approver can approve this brief.', action: 'Ask an approver to approve it.' }],
  context_items: [{ id: 'context_1', kind: 'attested_fact', text: "The client's AI assistant made the changes.", author: 'approver@example.invalid', created_at: '2026-10-22T10:00:00Z', gate: 'gate_two', in_brief: true },
    { id: 'context_2', kind: 'context', text: 'Keep the first-reply story.', author: 'editor@example.invalid', created_at: '2026-10-22T11:00:00Z', gate: 'gate_one', in_brief: false }],
  content_body: { schema_version: 'brief_document_v3', document: { header: { cta: body.cta, channels: ['reel', 'email', 'carousel', 'caption'], purpose: 'WARM' }, body },
    review: { findings: [], locked_fields: ['format_plan.email.subject_options[0]'] } },
} as unknown as StoredBriefV3;
const versions = [
  { brief_id: 'brief_0', supersedes_id: null, content_hash: 'a', approval_status: 'pending', created_at: '2026-10-22T09:00:00Z', author: 'approver@example.invalid', kind: 'generated', reason: 'Written by the system from the approved card', fields: [] },
  { brief_id: 'brief_1', supersedes_id: 'brief_0', content_hash: 'h', approval_status: 'pending', created_at: '2026-10-22T10:00:00Z', author: 'editor@example.invalid', kind: 'edit', reason: 'Edited 1 field', fields: ['format_plan.email.subject_options[0]'] },
] as BriefVersion[];

test('5.F2: Gate 2 names each blocker in a reviewer\'s words', () => {
  const html = renderToStaticMarkup(<BlockerList items={brief.blocker_items!} />).replaceAll('&#x27;', "'").replaceAll('&quot;', '"');
  for (const [kind, name] of [['open_question', 'Open question'], ['blocking_finding', 'A problem in the copy'], ['stale', 'Out of date'],
    ['cta_unconfirmed', 'Call to action not confirmed'], ['role', 'Your role']]) {
    assert.equal(blockerName(kind), name);
    assert.ok(html.includes(`${name}:`), name);
  }
  assert.ok(html.includes('The caption says "x"') && html.includes("still the writer's suggestion") && html.includes('Only an approver'));
  assert.ok(renderToStaticMarkup(<BlockerList items={[]} />).includes('Nothing stops approval.'));
});

test('5.F1, 5.B7: the v3 reader edits every field, refreshes with locked lines and adds context; the version list is no longer on the reader', () => {
  const html = renderScreen(<BriefReaderV2 brief={brief} busy={false} perform={async () => {}} versions={versions} />).replaceAll('&#x27;', "'");
  for (const text of ['Edit any field', 'Email subject option 1', 'Reel 1: cover', 'Slide 3', 'Caption body', 'Locked: kept on refresh',
    'Refresh with feedback', 'Let the writer rewrite: Email subject option 1', 'Context and attested facts', 'Attested fact, attested by approver@example.invalid on 2026-10-22',
    'Context, from editor@example.invalid on 2026-10-22; the next refresh uses it', 'Add to this brief', 'attested by approver@example.invalid on 2026-10-22',
    'Open question:', 'Your role:']) assert.ok(html.includes(text), text);
  for (const removed of ['Versions (2)', 'Version 2 (this one)', 'Written by the system']) assert.ok(!html.includes(removed), `no version list on the reader: ${removed}`);
  const approved = renderScreen(<BriefReaderV2 brief={{ ...brief, approval_status: 'approved' } as StoredBriefV3} busy={false} perform={async () => {}} />);
  assert.ok(!approved.includes('Refresh with feedback') && !approved.includes('Add to this brief'), 'a decided brief is not refreshed');
  const viewer = renderScreen(<BriefReaderV2 brief={{ ...brief, can_edit: false, can_review: false } as StoredBriefV3} busy={false} perform={async () => {}} />);
  assert.ok(!viewer.includes('>Edit<') && !viewer.includes('Refresh with feedback') && !viewer.includes('Add to this brief'));
  assert.equal(claimStatus({ status: 'attested', attested: { kind: 'paraphrase', by: 'a', on: '2026-10-22' } }), "a paraphrase of the client's words, given by a on 2026-10-22");
  assert.equal(claimStatus({ status: 'unchecked' }), 'check it against the call');
});

test('5.B7: context goes to the card or the brief route; an editor is not offered the attested fact', () => {
  assert.equal(contextPath('angle', 'angle_1'), '/angles/angle_1/context');
  assert.equal(contextPath('brief', 'brief_1'), '/briefs/brief_1/context');
  assert.deepEqual(contextRequest('attested_fact', ' Her AI assistant made the changes. ', ''), { body: { kind: 'attested_fact', text: 'Her AI assistant made the changes.' } });
  assert.deepEqual(contextRequest('paraphrase', 'x', ' Whitney '), { body: { kind: 'paraphrase', text: 'x', author: 'Whitney' } });
  assert.deepEqual(contextRequest('context', '  ', ''), { error: 'Write the context first.' });
  assert.equal(contextLine({ id: 'c', kind: 'paraphrase', text: 't', author: 'e', created_at: '2026-10-22T00:00:00Z' }), "Paraphrase of the client's words, from e on 2026-10-22");
  const editor = renderToStaticMarkup(<GateContextPanel target="angle" id="a" items={[]} canAdd canAttest={false} busy={false} perform={async () => {}} />);
  assert.ok(editor.includes('Add to this card') && !editor.includes('Attested fact') && editor.includes('No context has been added yet.'));
  const approver = renderToStaticMarkup(<GateContextPanel target="brief" id="b" items={[]} canAdd canAttest busy={false} perform={async () => {}} />);
  assert.ok(approver.includes('Attested fact'));
});

test('5.F5 d: the versions list says who made each version and why', () => {
  const html = renderToStaticMarkup(<VersionList versions={versions} current="brief_0" onOpen={() => {}} />);
  assert.ok(html.includes('Version 1 (this one)') && html.includes('editor@example.invalid') && html.includes('Edited 1 field'));
  assert.equal(renderToStaticMarkup(<VersionList versions={[]} current="x" onOpen={() => {}} />), '');
});
