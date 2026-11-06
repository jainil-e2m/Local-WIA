import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderScreen } from '../testing/render';
import { BriefReaderV2, anchorLine, anchorRequest, briefDecisionRequest, briefTitle, ctaRequest, isV2, type StoredBriefV2, type StoredBriefV3 } from './BriefReaderV2';

const body = {
  approved_angle: { title: 'Why we ask about follow-up first', core_perspective: 'Follow-up shapes lead quality.' }, sharpened_point: null,
  strategic_purpose: { pillar: 'WARM', content_type: 'behind_the_scenes', why_now: 'Budget season.' },
  audience: { who: 'Venue owners', reason_to_care: 'They want tours.' }, intended_shift: { understand: 'u', believe: 'b', do: 'd' },
  point_of_view: 'we' as const, wia_perspective: 'We look at what happens after the inquiry before we change a single ad.',
  supporting_example: { scene: 'A client call.', wia_move: 'Carmen asked how the first reply was written.', client_contribution: 'The client described it.' },
  narrative_outline: { hooks: [{ style: 'observation', text: 'I had a conversation this week.' }], problems_desires_symptoms: ['Quiet inquiries'], main_point: 'Follow-up is part of the ad.', transformation: 't', cta: 'Reply' },
  format_plan: { reels: [{ job: 'Show the move', cover_text: 'The question we ask', spoken_opening: 'Before we touch your ads', beats: ['a', 'b'], read_time_seconds: 30, source: 'new_script' }], carousel: null, email: null, caption: null, stories: null },
  cta: { choice: 'explicit' as const, track: null, action: 'Reply to this email', offer_connection: null, chosen_by: 'writer' as const }, cta_why: 'A low barrier.',
  before_publishing: [{ text: 'Confirm the client may be named.', kind: 'permission', required: true, answer: null }],
  evidence: [{ evidence_id: 'ev_secret_id', speaker: 'Carmen Cruickshank', start_ms: 64000, quote: 'How do you reply today?' }],
  claims: [{ claim_id: 'c1', text: 'On a call, the team asked about follow-up.', claim_class: 'particular_interaction' }],
};
// The reader reads only part of a stored brief; the fixture carries that part.
const brief = {
  brief_id: 'brief_1', content_hash: 'h', angle_id: 'a', week_id: 'w', approval_status: 'pending', blockers: ['The CTA is the writer’s proposal'],
  can_approve: false, can_edit: true, can_review: true, schema_version: 'brief_document_v2',
  content_body: { schema_version: 'brief_document_v2', document: { header: { cta: body.cta, channels: ['reel', 'email'], purpose: 'WARM' }, body },
    review: { findings: [{ severity: 'warning', message: 'A prevalence claim generalises.' }], locked_fields: [] } },
} as unknown as StoredBriefV2;

test('E.F4: the WIA perspective comes first and no passage IDs or offsets appear', () => {
  const html = renderScreen(<BriefReaderV2 brief={brief} busy={false} perform={async () => {}} />);
  assert.ok(html.indexOf('WIA perspective') < html.indexOf('Supporting example') && html.indexOf('Supporting example') < html.indexOf('Format plan'));
  for (const text of ['Carmen Cruickshank at 1:04', 'How do you reply today?', 'Confirm the CTA', 'No explicit ask', 'Confirm the client may be named. (required)',
    'Check the claims', 'Approve the brief', 'Reject the brief', 'Download the brief', 'A prevalence claim generalises.']) assert.ok(html.includes(text.replaceAll("'", '&#x27;')), text);
  assert.ok(html.includes('href="/api/atelier/briefs/brief_1/export.md"'));
  assert.ok(!html.includes('Whose decision is this?') && !html.includes('Rate this brief'), 'no author input and no rubric on the brief decision');
  assert.ok(!html.includes('ev_secret_id') && !/characters \d/.test(html), 'no evidence IDs or offsets on screen');
  const confirmed = { ...brief, content_body: { ...brief.content_body, document: { ...brief.content_body.document, header: { ...brief.content_body.document.header, cta: { ...body.cta, chosen_by: 'person' as const } } } } };
  assert.ok(!renderScreen(<BriefReaderV2 brief={confirmed} busy={false} perform={async () => {}} />).includes('Confirm the CTA'));
});

test('E.F4: a brief that no longer waits shows its body, what was said on the call and the download only', () => {
  const approved = { ...brief, approval_status: 'approved', blockers: [] } as unknown as StoredBriefV2;
  const html = renderScreen(<BriefReaderV2 brief={approved} busy={false} perform={async () => {}} />).replaceAll('&#x27;', "'");
  for (const text of ['WIA perspective', 'Supporting example', 'What was said on the call', 'How do you reply today?', 'Download the brief']) assert.ok(html.includes(text), text);
  for (const removed of ['Confirm the CTA', 'Before publishing', 'Confirm the client may be named.', 'Checks (', 'A prevalence claim generalises.', 'Check the claims',
    'Client permission', 'Your decision', 'Approve the brief', 'Reject the brief', 'Versions (', 'Account memory']) {
    assert.ok(!html.includes(removed), `only while the brief waits: ${removed}`);
  }
});

test('E.F4: the CTA confirmation and the decision carry what Gate 2 requires', () => {
  assert.deepEqual(ctaRequest('h', 'explicit', ''), { error: 'Write the CTA, or choose no explicit ask.' });
  assert.match((ctaRequest('h', 'explicit', 'Pay $197') as { error: string }).error, /price/);
  assert.deepEqual(ctaRequest('h', 'no_explicit_ask', 'ignored'), { body: { expected_hash: 'h', choice: 'no_explicit_ask', action: null } });
  assert.match((briefDecisionRequest('h', 'rejected', '', '', '') as { error: string }).error, /reason/);
  assert.deepEqual(briefDecisionRequest('h', 'approved', 'strong', ' Ready. ', 'Whitney Hodges'),
    { body: { expected_hash: 'h', decision: 'approved', reason_code: 'strong', note: 'Ready.', author: 'Whitney Hodges' } });
  assert.ok(isV2(brief) && briefTitle(brief) === body.approved_angle.title);
  assert.equal(briefTitle({ content_body: { document: { title: 'A v1 brief' } } }), 'A v1 brief');
});

import { plainBlocker, plainBlockers } from './BriefReaderV2';

test('E.F4, R50: the checks say what to do, with no pipeline words or evidence identifiers', () => {
  assert.equal(plainBlocker('Changed document requires a scoped grounding/differentiation review'), plainBlocker('Acknowledge the admitted-archive/legacy-history limitation'));
  assert.equal(plainBlockers(['Changed document requires a scoped grounding/differentiation review', 'Acknowledge the admitted-archive/legacy-history limitation']).length, 1);
  assert.match(plainBlocker('The CTA is the writer\'s proposal; a person confirms it (or no explicit ask) at Gate 2'), /Confirm the CTA/);
  const evidence = plainBlocker('Evidence ev_9f8a7 is not in the dossier');
  assert.ok(!evidence.includes('ev_9f8a7') && evidence.startsWith('A quoted turn'));
  assert.ok(!plainBlocker('The speaker or time for evidence_abc123 differs from the source').includes('evidence_abc123'));
});

test('E.B15, E.F4: a client figure asks the approver for the permission, and speakers use the roster', () => {
  const consent = { ...brief, blockers: ['"45 inquiries" is a client figure; it needs that client\'s permission, recorded per result, before public use; record the client\'s permission as a clearance on its evidence'],
    selected_evidence: [{ evidence_id: 'ev_b', transcript_id: 't', title: 'Call', excerpt: 'We moved to 45 inquiries a month.', speaker: 'Shannon Lee' }],
    content_body: { ...brief.content_body, provenance: { roster: [{ name: 'Carmen Cruickshank', role: 'Google Ads lead', status: 'current' as const, aliases: ['Carmen Cruickshank', 'Carmen'] }] } } };
  const html = renderScreen(<BriefReaderV2 brief={consent as unknown as StoredBriefV2} busy={false} perform={async () => {}} />);
  const visible = html.replace(/<[^>]+>/g, ' ');
  assert.ok(visible.includes('Client permission') && visible.includes('Record the permission') && !visible.includes('ev_b'), visible);
  assert.ok(html.includes('Carmen Cruickshank (WIA, Google Ads lead) at 1:04'), 'a roster name and role, not the raw transcript label');
});

test('E.B23: a v3 brief shows its script, the email and caption bodies, the ledger status and no empty reader decision', () => {
  const plan = { ...body.format_plan,
    reels: [{ ...body.format_plan.reels[0], script: 'Before we touch your ads, we ask one thing. How do you answer a new inquiry?' }],
    email: { subject_options: ['One question', 'Before the ads'], preview: 'It starts after the inquiry.', opening: 'Hi there,', body: 'The first reply shapes which inquiries become tours.', ending: 'Reply and tell me.' },
    caption: { hook: 'Most of the sale happens after the click.', body: 'The ad starts the conversation. The reply carries it.', ending: 'Save this.' } };
  const claims = [{ ...body.claims[0], status: 'unchecked', settled_by: 'none', field: 'wia_perspective', note: null, flag: null, numeric_facts: [], quote: null, public_quote: false, evidence_ids: [], knowledge_base_document: null }];
  const v3 = { ...brief, schema_version: 'brief_document_v3',
    content_body: { ...brief.content_body, schema_version: 'brief_document_v3',
      document: { ...brief.content_body.document, body: { ...body, intended_shift: { understand: 'u', believe: 'b', do: null }, format_plan: plan, claims } },
      review: { ...brief.content_body.review, ledger: { verifier: { status: 'skipped', reason: 'not configured' } }, repair: { used: true, accepted: false } } } };
  const html = renderScreen(<BriefReaderV2 brief={v3 as unknown as StoredBriefV3} busy={false} perform={async () => {}} />).replaceAll('&#x27;', "'");
  for (const text of ['Script:', 'How do you answer a new inquiry?', 'The first reply shapes which inquiries become tours.', 'The reply carries it.',
    'check it against the call', 'did not run (not configured)', 'it added caveats to the copy']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes('Do: '), 'an optional reader decision left empty is not shown');
  assert.ok(isV2(v3 as unknown as StoredBriefV3) && briefTitle(v3 as unknown as StoredBriefV3) === body.approved_angle.title);
});

test('E.B23: the reader says which piece production writes first, and an editor chooses another through the edit route', () => {
  const rule = 'The first Reel; else the carousel; else the email; else the caption; else the stories';
  const options = [{ key: 'reel_1', label: 'Reel 1' }, { key: 'email', label: 'Email' }];
  const anchored = { ...brief, anchor: { key: 'reel_1', chosen_by: 'rule' as const, rule, note: null, options } } as unknown as StoredBriefV2;
  const html = renderScreen(<BriefReaderV2 brief={anchored} busy={false} perform={async () => {}} />);
  assert.ok(html.includes('Written first in production: Reel 1 (the rule: the first reel;') && html.includes('Make this the anchor'), html);
  assert.ok(!html.includes('Use the rule'), 'the rule already applies');
  const chosen = { ...anchored, anchor: { ...anchored.anchor!, key: 'email', chosen_by: 'person' as const } } as StoredBriefV2;
  assert.equal(anchorLine(chosen.anchor), 'Written first in production: Email (chosen by a person).');
  assert.ok(renderScreen(<BriefReaderV2 brief={chosen} busy={false} perform={async () => {}} />).includes('Use the rule'));
  assert.deepEqual(anchorRequest('h', 'email'), { expected_hash: 'h', changes: { anchor: 'email' } });
  assert.deepEqual(anchorRequest('h', null), { expected_hash: 'h', changes: { anchor: null } });
  const viewer = renderScreen(<BriefReaderV2 brief={{ ...anchored, can_edit: false }} busy={false} perform={async () => {}} />);
  assert.ok(viewer.includes('Written first in production') && !viewer.includes('Make this the anchor'), 'a viewer sees the anchor, not the choice');
  assert.equal(anchorLine(undefined), 'No piece to write first: the format plan is empty.');
});
