import { test } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { AngleReview, ComparisonSummary } from '../components/SQLWeeklyAngles';
import { StoredAngle } from '../types/weeklyStorage';
import { storageRequest } from './weeklyStorage';

const angle: StoredAngle = {
  angle_id: 'angle_test', run_id: 'run_test', content_hash: 'hash', moment_ids: ['moment_test'],
  content_body: { title: 'Stored angle', argument: 'A supported argument', audience: 'Owners', tension: 'Uncertainty', take: 'Check evidence', mechanism: 'Follow-up', reader_decision: 'Review', qualifiers: ['Reported only'], risks: ['Identity not verified'], source_assertions: ['[moment_test] A report'], inference: null },
  base_score: 90, adjusted_score: null, selection_status: 'candidate', approval_status: 'pending', first_generated_at: '2026-10-08T11:28:56Z', selected_cta: null, matching_result: null,
};
test('unmatched candidates show their limitations and cannot be approved', () => {
  const html = renderToStaticMarkup(<AngleReview angle={angle} busy={false} perform={async () => {}} />);
  assert.match(html, /awaiting matching/);
  assert.match(html, /Matching is incomplete/);
  assert.match(html, /Reported only/);
  assert.match(html, /disabled="">Approve angle/);
  assert.doesNotMatch(html, /Generate brief|No historical overlap|novel/i);
});
test('storage requests require the same-origin session and surface backend conflicts', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/atelier/angles/angle_test');
    assert.equal(options?.credentials, 'same-origin');
    assert.equal(options?.redirect, 'error');
    return new Response(JSON.stringify({ detail: 'Angle changed; refresh before saving' }), { status: 409, headers: { 'content-type': 'application/json' } });
  };
  await assert.rejects(storageRequest('/angles/angle_test', 'PATCH', { expected_hash: 'hash' }), /refresh/);
});

test('comparison content remains unapprovable even with a visible legacy-looking score', () => {
  const candidate = { ...angle, workflow: 'historical_comparison_v1', selection_status: 'visible', adjusted_score: 95,
    matching_result: { status: 'complete', history_count: 7 } };
  const html = renderToStaticMarkup(<AngleReview angle={candidate} busy={false} perform={async () => {}} />);
  assert.match(html, /Approval awaits threshold selection/);
  assert.match(html, /disabled="">Approve angle/);
  assert.match(html, /disabled="">Reject angle/);
});

test('three scenario summaries expose saved counts, fallbacks and conflicts separately', () => {
  const report = { status: 'comparison_complete', threshold_selection_pending: true, families: [],
    scenarios: [.78, .85, .90].map((cutoff, i) => ({ cutoff, selected_ids: [], families: [], current_batch_flags: {},
      counts: { initial_qualified: 2, final_qualified: 4 + i, recovered: 2, retained_original_fallbacks: i,
        current_batch_flagged: 2, qualified_without_batch_flags: 2 + i, failing_quality: 1, failing_history: 1,
        failing_both: 0, no_supported_alternative: 1 } })) };
  const html = renderToStaticMarkup(<ComparisonSummary report={report} />);
  assert.match(html, /0\.78/); assert.match(html, /0\.85/); assert.match(html, /0\.90/);
  assert.match(html, /quality\/history-qualified families/);
  assert.match(html, /original fallbacks/); assert.match(html, /current-batch conflicts/);
  assert.match(html, /runs no inference or encoding/);
});
