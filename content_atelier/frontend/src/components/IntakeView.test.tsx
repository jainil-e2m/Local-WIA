import '../testing/setupDom';
import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json, mount, stubFetch } from '../testing/dom';
import { INTAKE_OVERVIEW, ME_APPROVER } from '../testing/fixtures';
import { IntakeView, doneText, processingRows, sourceState, stageName } from './IntakeView';

/* Sources → Intake: the connectors, the weekly buckets, what was received, and "Processing", which lists only what is waiting or
   running and the failures of the last seven days, by plain names, never work that was replaced or cancelled. */

const NOW = Date.parse('2026-10-26T12:00:00Z');
const job = (id: string, stage: string, status: string, extra: Record<string, unknown> = {}) =>
  ({ job_id: id, stage, status, run_id: `run_${id}`, updated_at: '2026-10-25T10:00:00Z', ...extra });

test('Intake: Processing shows waiting and running work and the recent failures; replaced, cancelled and steps behind a failure are left out', () => {
  const jobs = [
    job('a', 'pack_check', 'queued', { run_id: 'run_pack' }), job('b', 'pack_finish', 'failed', { run_id: 'run_pack', error_summary: 'The pack could not be finished' }),
    job('c', 'moment_extraction', 'running'), job('d', 'moment_extraction', 'failed', { error_summary: 'Superseded: the backfill runs on another profile (2.B11)' }),
    job('e', 'document_normalise', 'cancelled'), job('f', 'brief_writing', 'failed', { updated_at: '2026-10-10T10:00:00Z', error_summary: 'Out of credit' }),
    job('g', 'intake_fathom', 'waiting', { current_message: 'Waiting for budget' }),
  ];
  const { active, recent, earlier } = processingRows(jobs as never, NOW);
  assert.deepEqual(active.map(j => j.job_id), ['c', 'g'], 'a step waiting behind a failed one in its run is not listed as waiting');
  assert.deepEqual(recent.map(j => j.job_id), ['b']);
  assert.deepEqual(earlier.map(j => j.job_id), ['f'], 'an older failure is behind "Show earlier"');
  assert.equal(stageName('moment_extraction'), 'Scenes from a call');
  assert.equal(stageName('pack_check'), 'Pack check');
  assert.equal(stageName('a_new_stage'), 'A new stage');
});

test('Intake: a pressed button says what happened, and a received source is ready, processing or failed in one word', () => {
  assert.equal(doneText('refresh'), 'Collecting new calls and threads now.');
  assert.equal(doneText('connections/slack/activate'), 'Slack is active. New threads come in from now on.');
  assert.equal(doneText('jobs/job_1/retry'), 'Sent to run again.');
  assert.deepEqual(sourceState({ status: 'ready', indexing_status: 'ready' } as never), { text: 'Ready', tone: 'approved' });
  assert.equal(sourceState({ status: 'received', indexing_status: 'pending' } as never).text, 'Processing');
  assert.equal(sourceState({ status: 'received', extraction_status: 'failed' } as never).text, 'Failed');
});

test('Intake: the page lists processing by plain names with no codes, and activating a connector asks first, then says it is active', async t => {
  const posts: string[] = [];
  const overview = { ...INTAKE_OVERVIEW, jobs: [
    { ...job('x', 'moment_extraction', 'failed', { updated_at: new Date().toISOString(), error_summary: 'The model answered with nothing usable (2.B11)' }) },
    { ...job('y', 'moment_extraction', 'failed', { error_summary: 'Superseded: replaced by a newer run' }) },
  ] };
  const network = stubFetch((url, options) => {
    if (options?.method === 'POST') { posts.push(url); return json({}); }
    if (url.endsWith('/me')) return json({ ...ME_APPROVER, can: { ...ME_APPROVER.can, manage_intake: true } });
    if (url.endsWith('/schedule')) return json({ text: 'Sunday 04:00 America/Chicago' });
    return json(overview);
  });
  t.after(network.restore);
  const ui = await mount(<IntakeView />, { url: '/sources/intake' });
  t.after(() => ui.unmount());
  await ui.settle();
  await ui.settle();
  const text = ui.text();
  assert.ok(text.includes('Scenes from a call') && text.includes('The model answered with nothing usable'), 'a failure by its plain name and reason');
  for (const hidden of ['moment_extraction', '2.B11', 'Superseded']) assert.ok(!text.includes(hidden), `no ${hidden}`);
  const activate = [...ui.container.querySelectorAll('button')].find(b => b.textContent === 'Activate Fathom')!;
  assert.ok(activate, 'an intake administrator is offered Activate');
  await ui.click(activate);
  assert.ok(ui.container.querySelector('[role="dialog"][aria-label="Activate Fathom?"]'), 'it asks first');
  assert.deepEqual(posts, [], 'nothing is sent before the confirmation');
  await ui.click([...ui.container.querySelectorAll('[role="dialog"] button')].find(b => b.textContent === 'Activate Fathom') ?? null);
  await ui.settle();
  assert.deepEqual(posts, ['/api/atelier/intake/connections/fathom/activate']);
  assert.match(ui.text(), /Fathom is active\. New calls come in from now on\./);
});

test('Intake: without the intake role nothing can be activated, collected or retried', async t => {
  const network = stubFetch(url => url.endsWith('/me') ? json(ME_APPROVER) : url.endsWith('/schedule') ? json({ text: 'Sunday 04:00 America/Chicago' })
    : json({ ...INTAKE_OVERVIEW, jobs: [job('z', 'pack_finish', 'failed', { updated_at: new Date().toISOString() })] }));
  t.after(network.restore);
  const ui = await mount(<IntakeView />, { url: '/sources/intake' });
  t.after(() => ui.unmount());
  await ui.settle();
  await ui.settle();
  const buttons = [...ui.container.querySelectorAll('button')].map(b => b.textContent);
  for (const hidden of ['Activate Fathom', 'Collect now', 'Close the current bucket', 'Retry']) assert.ok(!buttons.includes(hidden), `no ${hidden}`);
  assert.match(ui.text(), /Pack finishing/);
});
