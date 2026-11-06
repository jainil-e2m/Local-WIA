import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { StageProgress, stepText, unitShare } from './shared/JobProgress';
import { EmptyState, ErrorState, LoadingState, QueryState } from './shared/states';
import { ConflictNotice } from './shared/conflict';
import { AngleResearchPanel } from './BriefStatus';

test('1.F2: progress is read from the job row\'s unit counts, and a row without counts draws no bar', () => {
  const withUnits = renderToStaticMarkup(<StageProgress job={{ stage: 'angle_generation', status: 'running', current_step: 'Reading call 3', completed_units: 3, total_units: 12, updated_at: '2026-10-18T10:00:00Z' }} />);
  assert.match(withUnits, /<progress[^>]*max="12"[^>]*value="3"|<progress[^>]*value="3"[^>]*max="12"/);
  assert.ok(withUnits.includes('3 of 12') && withUnits.includes('Reading call 3') && withUnits.includes('angle generation') && withUnits.includes('in progress'));
  assert.ok(withUnits.includes('Last update') && withUnits.includes('dateTime="2026-10-18T10:00:00Z"'));
  const withoutUnits = renderToStaticMarkup(<StageProgress job={{ stage: 'angle_generation', status: 'running', current_step: 'Working', completed_units: null, total_units: null }} />);
  assert.ok(!withoutUnits.includes('<progress') && withoutUnits.includes('Working'), 'no counts, no bar: nothing is invented from elapsed time');
  assert.ok(!withoutUnits.includes('Last update'));
});

test('1.F2: the share comes only from the counts; an impossible count is no share', () => {
  assert.equal(unitShare({ completed_units: 3, total_units: 12 }), 0.25);
  assert.equal(unitShare({ completed_units: 15, total_units: 12 }), 1);
  for (const bad of [{ completed_units: 1, total_units: 0 }, { completed_units: -1, total_units: 5 }, { completed_units: null, total_units: 5 }, {}]) assert.equal(unitShare(bad), null);
});

test('1.F2: a failed stage shows its error before its last message, and a retry goes with it', () => {
  assert.equal(stepText({ stage: 's', status: 'failed', error_summary: 'Provider refused', current_message: 'Calling the model' }), 'Provider refused');
  assert.equal(stepText({ stage: 's', status: 'running', error_summary: 'old', current_message: 'Calling the model' }), 'Calling the model');
  const html = renderToStaticMarkup(<AngleResearchPanel data={{ status: 'running', jobs: [{ job_id: 'j1', stage: 'brief_research', status: 'failed', current_message: 'x', error_summary: 'Provider refused' }] }}
    error="" busy={false} canRetry onRetry={() => {}} onRetryStage={() => {}} />);
  assert.ok(html.includes('Gathering evidence from the calls') && html.includes('Provider refused') && html.includes('Try this step again'));
});

test('1.F2: loading, empty and error are the same everywhere', () => {
  assert.match(renderToStaticMarkup(<LoadingState>Loading things…</LoadingState>), /role="status"[^>]*>Loading things…/);
  assert.match(renderToStaticMarkup(<EmptyState>Nothing here.</EmptyState>), /role="status"/);
  const error = renderToStaticMarkup(<ErrorState message="It broke." onRetry={() => {}} />);
  assert.ok(error.includes('role="alert"') && error.includes('It broke.') && error.includes('Retry'));
  const query = (data: string[] | undefined, failure: Error | null) => ({ data, error: failure, isPending: data === undefined && !failure, refetch: () => {} });
  const show = (data: string[] | undefined, failure: Error | null) => renderToStaticMarkup(<QueryState query={query(data, failure)} empty="No rows." isEmpty={rows => !rows.length}>{rows => <p>{rows.join(',')}</p>}</QueryState>);
  assert.match(show(undefined, null), /Loading/);
  assert.match(show(undefined, new Error('Offline')), /role="alert"[^>]*>Offline/);
  assert.match(show([], null), /No rows\./);
  const stale = show(['a'], new Error('Refresh failed'));
  assert.ok(stale.includes('Refresh failed') && stale.includes('<p>a</p>'), 'a failed refresh keeps the answer on screen');
});

test('1.F2: the conflict notice says what happened and that the input is still there', () => {
  assert.equal(renderToStaticMarkup(<ConflictNotice conflict={null} />), '');
  const html = renderToStaticMarkup(<ConflictNotice conflict={{ message: 'Brief content hash changed; refresh before saving' }} onReload={() => {}} onDismiss={() => {}} />);
  assert.ok(html.includes('data-conflict') && html.includes('role="alert"') && html.includes('Brief content hash changed; refresh before saving'));
  assert.ok(html.includes('still in the form') && html.includes('Reload the latest version') && html.includes('Keep editing'));
});
