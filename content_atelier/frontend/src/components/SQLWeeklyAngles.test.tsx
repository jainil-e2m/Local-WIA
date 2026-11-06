import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderScreen as renderToStaticMarkup } from '../testing/render';
import { AngleResearchPanel } from './SQLWeeklyAngles';

test('S.B13: an unqueued brief shows its reason and a retry for an approver', () => {
  const data = { status: 'failed', error_summary: 'FileNotFoundError: brand bundle missing', jobs: [] };
  const html = renderToStaticMarkup(<AngleResearchPanel data={data} error="" busy={false} canRetry onRetry={() => {}} />);
  assert.ok(html.includes('Brief generation failed: FileNotFoundError: brand bundle missing'));
  assert.ok(html.includes('Retry brief generation'));
  const viewer = renderToStaticMarkup(<AngleResearchPanel data={data} error="" busy={false} canRetry={false} onRetry={() => {}} />);
  assert.ok(viewer.includes('Brief generation failed') && !viewer.includes('Retry brief generation'));
});

test('a queued brief shows its stages and no failure', () => {
  const data = { status: 'running', error_summary: null, jobs: [{ stage: 'brief_research', status: 'running', current_message: 'Research query round 1' }] };
  const html = renderToStaticMarkup(<AngleResearchPanel data={data} error="" busy={false} canRetry onRetry={() => {}} />);
  assert.ok(html.includes('Research query round 1') && !html.includes('failed') && !html.includes('Retry brief generation'));
});

import { gateOneActions, parseStudioLink, angleLink, briefLink } from './SQLWeeklyAngles';

const base = { base_score: 4.2, has_replacement: false, approval_status: 'pending', can_approve: true, can_edit: true, can_reject: true };
const legacy = { ...base, content_body: { title: 'T' } } as unknown as Parameters<typeof gateOneActions>[0];
const strategic = { ...base, base_score: null, content_body: { title: 'T', strategy: { evidence_readiness: 'supported' } } } as unknown as Parameters<typeof gateOneActions>[0];
const card = { ...base, base_score: null, content_body: { title: 'T', card: { rank: 1 } } } as unknown as Parameters<typeof gateOneActions>[0];

test('S.F1: the old screen offers no action the server would refuse', () => {
  assert.deepEqual(gateOneActions(legacy), { edit: true, editReason: null, rescore: false, approve: true, approveReason: null, reject: true });
  const s = gateOneActions(strategic);
  assert.equal(s.edit, false); assert.match(s.editReason!, /own fields/); assert.equal(s.rescore, false);
  const c = gateOneActions(card);
  assert.equal(c.edit, false); assert.equal(c.rescore, false); assert.equal(c.approve, false); assert.match(c.approveReason!, /card screen/);
  assert.equal(c.reject, true, 'comparison and card angles can be rejected');
  assert.equal(gateOneActions({ ...legacy, can_edit: false, can_reject: false, can_approve: false }).edit, false);
  assert.equal(gateOneActions({ ...legacy, can_reject: false }).reject, false);
  assert.equal(gateOneActions({ ...legacy, base_score: null }).rescore, true, 'an edited legacy angle still needs its assessment');
});

test('S.F4: card and brief links round-trip', () => {
  assert.deepEqual(parseStudioLink(angleLink('week_2026-06-29', 'angle_abc')), { tab: 'angles', week: 'week_2026-06-29', angle: 'angle_abc' });
  assert.deepEqual(parseStudioLink(briefLink('brief_123')), { tab: 'briefs', brief: 'brief_123' });
  // A link saved before the app had paths (#studio/...) still reads the same way.
  assert.deepEqual(parseStudioLink('#studio/angles/week_2026-06-29/angle_abc'), { tab: 'angles', week: 'week_2026-06-29', angle: 'angle_abc' });
  assert.deepEqual(parseStudioLink('#studio/briefs/brief_123'), { tab: 'briefs', brief: 'brief_123' });
  for (const bad of ['', '#studio/briefs/', '#studio/briefs/a/b', '#studio/angles/w', '#studio/angles/w/a?x=1', '#elsewhere', '/studio/briefs/', '/studio/briefs/a/b', '/studio/angles/w']) assert.equal(parseStudioLink(bad), null, bad);
});

test('S.F4: the research panel links an approved card to its brief', () => {
  const html = renderToStaticMarkup(<AngleResearchPanel data={{ status: 'completed', brief_id: 'brief_123', jobs: [] }} error="" busy={false} canRetry onRetry={() => {}} />);
  assert.ok(html.includes('href="/studio/briefs/brief_123"') && html.includes('Open the brief'));
});
