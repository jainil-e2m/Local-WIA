import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import type { CycleDetail, CyclePreview, StandingBudgets, WeekMeasures } from '../api/schema';
import { renderScreen } from '../testing/render';
import { DownloadReview } from './BackendStudio';
import { BudgetSummary, CycleDetailView, CycleList, CyclePanel, CyclePreviewView, MonitoringView, coverageWords, defaultWindow, windowInstant } from './CyclePanel';
import { AngleResearchPanel } from './BriefStatus';

const doc = (id: string, because: string, extra = {}) => ({ transcript_id: id, title: `Call ${id}`, occurred_at: '2026-10-13T15:00:00Z', selected_because: because, ...extra });
const budget = (purpose: string, extra = {}) => ({ purpose, label: purpose, enabled: true, uncapped: false, cap_usd: 1.2, cap_calls: 80, cap_source: 'default', status: 'active', spent_usd: 0.2, calls_used: 3, left_usd: 1.0, waiting_jobs: 0, ...extra });

const preview: CyclePreview = {
  window: { start: '2026-10-12T00:00:00+00:00', end: '2026-10-19T00:00:00+00:00' }, document_count: 3,
  documents: [doc('t1', 'window'), doc('t2', 'window')], late_arrivals: [doc('t0', 'late_arrival')], undated: [doc('t9', 'undated', { occurred_at: null })],
  earlier_cycles: [], budgets: [budget('cycle'), budget('extraction')], within_budget: false, selection_hash: 'abcdef123456',
  estimate: { total_usd: 0.61, documents_to_extract: 2, scenes_in_ledger: 12, notes: [], assumptions: '16000 strategist output tokens', note: 'An estimate, not a charge.',
    components: [{ stage: 'scene extraction', calls: 2, usd: 0.02 }, { stage: 'strategist', calls: 1, usd: 0.59 }] },
};

test('3.B2: the default window is the seven days before today, sent as UTC midnights', () => {
  assert.deepEqual(defaultWindow(new Date('2026-10-24T18:00:00Z')), { from: '2026-10-17', to: '2026-10-24' });
  assert.equal(windowInstant('2026-10-12'), '2026-10-12T00:00:00Z');
});

test('3.B2: the preview shows the calls, the late arrival, the undated call to add, the estimate and the budget warning', () => {
  const html = renderToStaticMarkup(<CyclePreviewView preview={preview} include={[]} onToggle={() => {}} />);
  for (const text of ['3 calls from 2026-10-12 to 2026-10-19', 'Call t1', 'Call t0 · 2026-10-13 · arrived after its own window’s cycle',
    'Add Call t9 to this cycle', 'Estimated cost: USD 0.61 (nothing is sent until you start)', 'strategist: 1 call, USD 0.59',
    'more than this week’s cycle and extraction budgets have left']) assert.ok(html.includes(text), text);
});

test('3.B2: the undated calls are folded under their count, so the estimate and Start stay in view (N1 shakedown)', () => {
  const many = { ...preview, undated: Array.from({ length: 160 }, (_, i) => doc(`u${i}`, 'undated', { occurred_at: null })) } as CyclePreview;
  const html = renderToStaticMarkup(<CyclePreviewView preview={many} include={['u3', 'u7']} onToggle={() => {}} />);
  assert.match(html, /<details[^>]*><summary[^>]*>Undated calls no window can reach \(160\) · 2 added to this cycle: add one by hand<\/summary>/);
  assert.ok(!/<details[^>]* open/.test(html), 'closed until a person opens it');
  assert.ok(html.indexOf('</details>') < html.indexOf('Estimated cost'), 'the estimate follows the folded list');
});

test('3.B3: a cycle lists its calls in plain words, with what was held back for consent; a budget wait is said in words', () => {
  const cycle = {
    run_id: 'run_1', week_id: 'week_2026-10-12', status: 'partially_completed', created_at: '', document_count: 2, coverage_state: 'complete',
    scenes_sent: 7, scenes_verified: 7, window: preview.window, message: null, waiting_reason: "This week's weekly cycle budget is spent.",
    documents: [doc('t1', 'window'), doc('t0', 'late_arrival')], estimate: preview.estimate,
    scene_coverage: { state: 'complete', documents: [{ transcript_id: 't1', verified: 4, sent: 3, held_for_consent: 1, not_sent: [] }, { transcript_id: 't0', verified: 3, sent: 3, not_sent: [] }], not_sent: [] },
    stages: [{ job_id: 'j1', stage: 'angle_generation', status: 'waiting', current_message: "This week's weekly cycle budget is spent." }],
  } as unknown as CycleDetail;
  assert.equal(coverageWords(cycle), 'every call was read in full');
  const html = renderToStaticMarkup(<CycleDetailView cycle={cycle} />);
  for (const text of ['Waiting: This week', '1 passage held back for consent', 'started on an estimate of USD 0.61', 'Drawing the ideas: waiting to continue']) assert.ok(html.includes(text), text);
  for (const hidden of ['scenes', 'strategist', 'angle_generation']) assert.ok(!html.includes(hidden), hidden);
  const list = renderToStaticMarkup(<CycleList cycles={[cycle]} onOpen={() => {}} />);
  assert.ok(list.includes('12 Oct – 18 Oct, 2026') && list.includes('2 calls · done'), list);
  assert.ok(renderToStaticMarkup(<CycleList cycles={[]} onOpen={() => {}} />).includes('No cycle has been started'));
});

test('6.B3: the budgets say what is left and what waits for each purpose', () => {
  const budgets: StandingBudgets = { week_start: '', week_end: '', enabled: true, uncapped: false, total_cap_usd: 3.5, total_spent_usd: 0.4,
    budgets: [budget('briefs', { label: 'briefs', waiting_jobs: 1 }), budget('context_mining', { label: 'context mining', cap_usd: null })] };
  const html = renderToStaticMarkup(<BudgetSummary budgets={budgets} />);
  for (const text of ['spending · USD 0.40 of USD 3.50', 'briefs: USD 1.00 left of USD 1.20', '1 waiting', 'context mining: no budget set']) assert.ok(html.includes(text), text);
});

test('no weekly caps: the budgets show only what each purpose has spent', () => {
  const budgets: StandingBudgets = { week_start: '', week_end: '', enabled: true, uncapped: true, total_cap_usd: 0, total_spent_usd: 4.46,
    budgets: [budget('packs', { label: 'content packs', uncapped: true, cap_usd: null, spent_usd: 4.46 })] };
  const html = renderToStaticMarkup(<BudgetSummary budgets={budgets} />);
  for (const text of ['spending · USD 4.46 · no weekly limits', 'content packs: USD 4.46 spent']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes(' of USD') && !html.includes('left of'), 'no cap is shown');
});

test('4.B1: a developed card whose brief waits for budget shows the reason', () => {
  const html = renderToStaticMarkup(<AngleResearchPanel busy={false} canRetry={false} error="" onRetry={() => {}}
    data={{ status: 'partially_completed', error_summary: null, brief_id: null, mode: 'live', waiting_reason: "This week's briefs budget is spent.", jobs: [] }} />);
  assert.ok(html.includes("The brief is waiting for budget: This week&#x27;s briefs budget is spent."));
});

test('M1 exit: a provider out of credit or a stopped worker shows its reason first, with the detail for the team folded away', () => {
  const credit = 'The model provider refused the request because the account is out of credit, so nothing was written. Retry this step once the team has topped the account up.';
  const summary = `${credit}\nHTTPStatusError: Client error '402 Payment Required' for url 'https://openrouter.ai/api/v1/chat/completions'`;
  const job = { job_id: 'job_1', stage: 'brief_research', status: 'failed', error_summary: summary };
  const html = renderToStaticMarkup(<AngleResearchPanel busy={false} canRetry error="" onRetry={() => {}} onRetryStage={() => {}}
    data={{ status: 'failed', error_summary: summary, brief_id: null, mode: 'live', waiting_reason: null, jobs: [job] }} />);
  assert.ok(html.includes(`Brief generation failed: ${credit}`), 'the reason in words first');
  assert.ok(html.includes('<summary class="cursor-pointer">Details for the team</summary>') && html.includes('402 Payment Required'));
  assert.ok(html.includes(`Gathering evidence from the calls</strong> · failed · ${credit}</p>`), 'the step shows the reason, not the exception');
  assert.ok(html.includes('Try this step again'), 'with the retry');
  const cycle = { run_id: 'run_1', week_id: 'w', status: 'failed', document_count: 1, coverage_state: 'extracted', documents: [], stages: [],
    scene_coverage: { state: 'extracted', documents: [], not_sent: [] }, error_summary: 'Single line reason.' } as unknown as CycleDetail;
  const detail = renderToStaticMarkup(<CycleDetailView cycle={cycle} />);
  assert.ok(detail.includes('Single line reason.') && !detail.includes('Details for the team'), 'a one-line error has nothing folded away');
});


test('3.B3: a failed cycle step offers a retry to an approver only (N1 shakedown)', () => {
  const cycle = {
    run_id: 'run_1', week_id: 'week_2026-10-12', status: 'failed', created_at: '', document_count: 2, coverage_state: 'not_extracted',
    scenes_sent: null, scenes_verified: 0, window: preview.window, message: null, waiting_reason: null, documents: [], estimate: null,
    error_summary: '5 of 7 documents failed scene extraction; the others are in the moments ledger and a retry sends only these',
    scene_coverage: { state: 'not_extracted', documents: [], not_sent: [] },
    stages: [{ job_id: 'j1', stage: 'moment_extraction', status: 'failed', current_message: 'Failed' },
      { job_id: 'j2', stage: 'angle_generation', status: 'queued', current_message: null }],
  } as unknown as CycleDetail;
  const approver = renderToStaticMarkup(<CycleDetailView cycle={cycle} onRetry={() => {}} />);
  assert.equal((approver.match(/Retry this step/g) ?? []).length, 1, 'only the failed step');
  assert.ok(!renderToStaticMarkup(<CycleDetailView cycle={cycle} />).includes('Retry this step'), 'not without the approver role');
});

// GET /weeks/{week_id}/measures, the parts the cycle panel reads (6.B13); synthetic titles and notes.
const side = (all: number) => ({ wia: all, delegated: 0, all });
const measures = (monitoring: Partial<WeekMeasures['monitoring']> = {}, chose = 4, slate = 6) => ({
  week_id: 'week_2026-10-19', week_start: '2026-10-19', week_end: '2026-10-25', rubric: {}, briefs: {}, gate_two_edits: {}, packs: {}, thresholds: [],
  wia_reviewers_configured: true, previous_week_id: null,
  cards: { slate, top_five: Math.min(5, slate), developed_or_reframed_keeping_the_point: side(chose), top_five_developed_or_reframed_keeping_the_point: side(chose) },
  monitoring: { accepted_share: slate ? Math.round((chose / slate) * 100) / 100 : null, bar: 0.5, cards_decided: 6, decided_at_least: 4, gate_1_done: true,
    skip_reasons: [{ reason_code: 'duplicate', note: 'Same point as last week.', title: 'Price the tour first' }, { reason_code: 'timing', note: null, title: null }],
    cards_with_evidence_flags: 1,
    cycle: { run_id: 'run_1', knowledge_base_version: 'wia-kb-2026-10-20.c-1a2b3c4d', strategist_profile: 'strategist_v7', started_from: 'schedule', cost_usd: 0.8123, model_calls: 14 },
    ...monitoring },
}) as WeekMeasures;
const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ');

test('6.B13: the week says how many angles were approved, the aim only when it is missed, and whether the schedule started the week', () => {
  const html = text(renderToStaticMarkup(<MonitoringView measures={measures()} />));
  assert.ok(html.includes('4 of 6 angles approved.'));
  assert.ok(!html.includes('Gate'));
  assert.ok(html.includes('This week was started by the schedule.'));
  // Nothing technical for a person who is not an approver (the owner, 25 October 2026).
  for (const hidden of ['wia-kb', 'strategist_v7', 'USD', 'Duplicate', 'evidence check', 'Details', '67%']) assert.ok(!html.includes(hidden), hidden);
  const under = text(renderToStaticMarkup(<MonitoringView measures={measures({ cycle: { ...measures().monitoring.cycle, started_from: 'app' } }, 2, 6)} />));
  assert.ok(under.includes('2 of 6 angles approved, below the aim of at least half.'), 'status in words, not colour');
  assert.ok(under.includes('This week was started from the app.'));
});

test('6.B13: an approver has the rest folded under Details: the skips, the points to check and the cost; not the knowledge base or profile', () => {
  const html = renderToStaticMarkup(<MonitoringView measures={measures()} details />);
  assert.match(html, /<details><summary[^>]*>Details<\/summary>/);
  assert.ok(!/<details[^>]* open/.test(html), 'folded until opened');
  const folded = text(html.slice(html.indexOf('<details>')));
  for (const words of ['Skipped (2):', 'Price the tour first: Duplicate. Same point as last week.', 'An angle: Timing', '1 angle had a point to check against the call.',
    'The cycle cost USD 0.81 over 14 model calls.']) {
    assert.ok(folded.includes(words), words);
  }
});

test('6.B13: a week part-way through says how many are approved so far, and a week with no cycle says that', () => {
  const waiting = text(renderToStaticMarkup(<MonitoringView measures={measures({ gate_1_done: false, cards_decided: 1, skip_reasons: [], cards_with_evidence_flags: 0 }, 1, 6)} details />));
  assert.ok(waiting.includes('1 of 6 angles approved.') && !waiting.includes('below the aim'));
  assert.ok(waiting.includes('No angle was skipped.') && waiting.includes('No angle had a point to check against the call.'));
  const none = text(renderToStaticMarkup(<MonitoringView measures={measures({ gate_1_done: false, cards_decided: 0, skip_reasons: [], cards_with_evidence_flags: 0,
    cycle: { run_id: null, knowledge_base_version: null, strategist_profile: null, started_from: 'app', cost_usd: 0, model_calls: 0 } }, 0, 0)} details />));
  assert.ok(none.includes('No angles this week yet.') && none.includes('No cycle has run for this week.') && !none.includes('Knowledge base'));
  assert.ok(!none.includes('started from the app') && !none.includes('The cycle cost'));
});

test('5.B14, 6.B13: the cycle panel shows how the week went; the review document downloads from the Weekly Studio header', () => {
  const html = renderScreen(<CyclePanel weekId="week_2026-10-19" canDecide={false} />, {
    seed: [['/weeks/{week_id}/measures', { path: { week_id: 'week_2026-10-19' } }, measures()], ['/cycles', {}, []]],
  });
  assert.ok(!html.includes('review.md'), 'the downloads moved to the header ("Download review")');
  const header = renderScreen(<DownloadReview weekId="week_2026-10-19" />);
  assert.ok(header.includes('href="/api/atelier/weeks/week_2026-10-19/review.docx"') && header.includes('Download review'), 'one direct link to the Word file');
  assert.ok(!header.includes('review.md') && !header.includes('Markdown'), 'no Markdown option');
  assert.ok(html.includes('aria-label="How this week went"') && html.includes('4 of 6 angles approved.'));
  assert.ok(!html.includes('>Details</summary>'), 'no details without the approver role');
  const approver = renderScreen(<CyclePanel weekId="week_2026-10-19" canDecide />, {
    seed: [['/weeks/{week_id}/measures', { path: { week_id: 'week_2026-10-19' } }, measures()], ['/cycles', {}, []]],
  });
  assert.ok(approver.includes('>Details</summary>'));
});
