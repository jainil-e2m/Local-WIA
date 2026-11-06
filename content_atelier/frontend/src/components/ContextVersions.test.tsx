import React from 'react';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { DiffViewer, VersionCard, VersionsList, approveRequest, benchmarkRequest, canDiscard, changedDocuments, compileMessage, diffLines, diffPath, discardPath, pendingLines,
  runLabel, scheduledLines, stateBadge, versionTitle } from './ContextVersions';
import type { KbVersion, KbVersions, VersionDiff } from '../api/types';

const draft: KbVersion = {
  version: 'wia-kb-2026-10-20.c-1a2b3c4d', active: false, state: 'draft', base_version: 'wia-kb-2026-10-14', on: '2026-10-20',
  changes: { offer_sheet: 'operating', rejection_rules: 'identity', team_roster: 'unchanged' }, pending_candidates: { offer_sheet: 3, rejection_rules: 0, exemplars: 1 },
  runs: [],
};
const pending: KbVersion = { ...draft, version: 'wia-kb-2026-10-18.c-99887766', on: '2026-10-18', state: 'approved_pending_benchmark', approved_by: 'Whitney Hodges', approved_on: '2026-10-18',
  runs: [{ run_id: 'run_abc', run_scope: 'weekly', status: 'completed', created_at: '2026-10-18T10:00:00Z' }] };
const active: KbVersion = { ...draft, version: 'wia-kb-2026-10-14', on: undefined, state: 'published from files', active: true, changes: undefined, pending_candidates: undefined, runs: [] };
const diff: VersionDiff = { version: draft.version, against: 'wia-kb-2026-10-14', state: 'draft', documents: [{ key: 'offer_sheet', change: 'operating',
  diff: '--- wia-kb-2026-10-14\n+++ wia-kb-2026-10-20.c-1a2b3c4d\n@@ -1,2 +1,2 @@\n # Offer sheet\n-ELEVATE: $2,500/month\n+ELEVATE: $2,750/month\n@@ -9 +9 @@\n-Audit: $247\n+Audit: $297' }] };

test('L.F3: state badges and titles use plain words, never the version fingerprint', () => {
  assert.equal(stateBadge(draft).label, 'Draft');
  assert.equal(stateBadge(pending).label, 'Approved, waiting for a benchmark');
  assert.equal(stateBadge(active).label, 'Active');
  assert.equal(stateBadge({ state: 'benchmark_failed', active: false }).label, 'Benchmark failed');
  assert.equal(versionTitle(draft), 'Knowledge base of 20 October 2026');
  assert.equal(versionTitle({ version: 'wia-kb-2026-10-14' }), 'Knowledge base of 14 October 2026');
  assert.equal(versionTitle({ version: 'files' }), 'Knowledge base from the original files');
});

test('L.F3: changed documents, pending candidates and runs in words', () => {
  assert.deepEqual(changedDocuments(draft.changes), [{ key: 'offer_sheet', label: 'The offer sheet', change: 'operating' }, { key: 'rejection_rules', label: 'The rules', change: 'identity' }]);
  assert.deepEqual(pendingLines(draft.pending_candidates), ['3 suggestions still waiting for review in the offer sheet', '1 suggestion still waiting for review in the writing examples']);
  assert.equal(runLabel(pending.runs[0]), 'Weekly cycle, completed, 18 October 2026');
  assert.match(compileMessage({ status: 'unchanged', version: 'v', documents: {}, pending_candidates: {} }), /Nothing has changed/);
  assert.equal(compileMessage({ status: 'compiled', version: 'wia-kb-2026-10-20.c-1a2b3c4d', documents: {}, pending_candidates: {} }), 'A new draft of 20 October 2026 was made. Open its changes to review and approve it.');
  assert.match(compileMessage({ status: 'exists', version: 'v', documents: {}, pending_candidates: {} }), /already exists; it is highlighted below/);
});

test('L.F3: unified diff lines are classified; headers and line offsets never reach the screen', () => {
  assert.deepEqual(diffLines(diff.documents[0].diff), [
    { kind: 'context', text: '# Offer sheet' }, { kind: 'remove', text: 'ELEVATE: $2,500/month' }, { kind: 'add', text: 'ELEVATE: $2,750/month' },
    { kind: 'break', text: '' }, { kind: 'remove', text: 'Audit: $247' }, { kind: 'add', text: 'Audit: $297' }]);
  const out = renderToStaticMarkup(<DiffViewer diff={diff} />);
  assert.ok(out.includes('The offer sheet · takes effect when approved') && out.includes('data-line="add"') && out.includes('data-line="remove"') && out.includes('font-mono'));
  for (const hidden of ['@@', '+++', 'c-1a2b3c4d']) assert.ok(!out.includes(hidden), hidden);
});

test('L.F3: approval needs a draft, the diff opened in this session and a note; benchmark needs a result', () => {
  assert.deepEqual(approveRequest(draft, 'Prices checked', false), { error: 'Open the changes before approving.' });
  assert.match((approveRequest(draft, ' ', true) as { error: string }).error, /note/);
  assert.match((approveRequest(pending, 'x', true) as { error: string }).error, /draft/);
  assert.deepEqual(approveRequest(draft, ' Prices checked ', true), { path: '/context/versions/wia-kb-2026-10-20.c-1a2b3c4d/approve', body: { note: 'Prices checked' } });
  assert.match((benchmarkRequest(draft, 'yes', 'r', '') as { error: string }).error, /waiting/);
  assert.match((benchmarkRequest(pending, '', 'r', '') as { error: string }).error, /passed/);
  assert.match((benchmarkRequest(pending, 'yes', ' ', '') as { error: string }).error, /result/);
  assert.deepEqual(benchmarkRequest(pending, 'no', 'smoke report 18 Oct', ''), { path: '/context/versions/wia-kb-2026-10-18.c-99887766/benchmark', body: { passed: false, result_ref: 'smoke report 18 Oct' } });
  assert.equal(diffPath(draft.version), '/context/versions/wia-kb-2026-10-20.c-1a2b3c4d/diff');
});

test('L.F3: the versions view says each change in plain words and disables Approve until the diff is opened', () => {
  const data: KbVersions = { active: active.version, versions: [draft, pending, active] };
  const out = renderToStaticMarkup(<VersionsList data={data} diffs={{}} seen={[]} busy={false} onOpenDiff={() => {}} onPost={() => {}} />);
  for (const text of ['Knowledge base of 20 October 2026', 'Draft', 'Approved, waiting for a benchmark', 'Active', 'The offer sheet', ' · takes effect when approved',
    'The rules', ' · needs a benchmark first', '3 suggestions still waiting', 'Used by 1 run', 'Weekly cycle, completed, 18 October 2026', 'Approved on 18 October 2026',
    'Record benchmark result', 'See what changed', 'Open the changes first']) assert.ok(out.includes(text), text);
  assert.match(out, /<button type="button" class="[^"]*" disabled="">Approve<\/button>/);
  for (const hidden of ['c-1a2b3c4d', 'run_abc', 'offer_sheet', 'Whitney Hodges', 'operating change', 'identity change', 'Discard draft']) assert.ok(!out.includes(hidden), hidden);
  const opened = renderToStaticMarkup(<VersionCard v={draft} diff={diff} diffSeen busy={false} onOpenDiff={() => {}} onPost={() => {}} />);
  assert.match(opened, /<button type="button" class="[^"]*">Approve<\/button>/);
  assert.ok(opened.includes('Hide the changes') && opened.includes('ELEVATE: $2,750/month'));
});

test('L.B11: the scheduled benchmark is shown for the approver and fills in its report; the approver still decides', () => {
  const scheduled: KbVersion = { ...pending, scheduled_benchmark: { state: 'recorded', result_ref: 'research/benchmark-v1/scheduled/results/2026-10-20-strategist_v5.x.json',
    suggested: 'pass', regressions: [], spent_usd: 0.6, ran_at: '2026-10-20T03:10:00Z' },
  runs: [{ run_id: 'kbbench_1', run_scope: 'kb_benchmark', status: 'completed', created_at: '2026-10-20T03:00:00Z' }] };
  const lines = scheduledLines(scheduled);
  assert.match(lines[0], /found no regression/);
  assert.equal(lines.at(-1), 'Report: research/benchmark-v1/scheduled/results/2026-10-20-strategist_v5.x.json', 'no cost on the page');
  assert.deepEqual(scheduledLines(pending), []);
  const worse = scheduledLines({ scheduled_benchmark: { ...scheduled.scheduled_benchmark!, suggested: 'review', regressions: ['week1: more blocking ledger flags (2 against 1)'] } });
  assert.match(worse[0], /a measure that got worse; decide whether it passed/);
  assert.equal(worse[1], 'week1: more blocking ledger flags (2 against 1)');
  const skipped = scheduledLines({ scheduled_benchmark: { state: 'skipped', regressions: [], reason: "benchmark v1's inputs are not on this machine (research/ is not in the image, R48)", at: '2026-10-22T01:00:00Z' } });
  assert.equal(skipped.length, 1);
  assert.match(skipped[0], /did not run: benchmark v1's inputs are not on this machine/);
  assert.match(skipped[0], /from a checkout, then record the verdict/);
  assert.equal(runLabel(scheduled.runs[0]), 'Scheduled benchmark, completed, 20 October 2026');
  const out = renderToStaticMarkup(<VersionCard v={scheduled} diff={null} diffSeen={false} busy={false} onOpenDiff={() => {}} onPost={() => {}} />);
  assert.ok(out.includes('aria-label="Scheduled benchmark"') && out.includes('value="research/benchmark-v1/scheduled/results/2026-10-20-strategist_v5.x.json"'));
  assert.ok(out.includes('Record benchmark result'), 'the approver records the verdict');
});

test('A draft nobody approved or used can be discarded, after a confirmation; an active, approved or used version cannot', () => {
  assert.equal(canDiscard(draft), true);
  assert.equal(canDiscard({ ...draft, active: true }), false, 'not the one in use');
  assert.equal(canDiscard(pending), false, 'not an approved one');
  assert.equal(canDiscard({ ...draft, runs: pending.runs }), false, 'not one a run used');
  assert.equal(discardPath('wia-kb-2026-10-20.c-1a2b3c4d'), '/context/versions/wia-kb-2026-10-20.c-1a2b3c4d/discard');
  const discarded: string[] = [];
  const data: KbVersions = { active: active.version, versions: [draft, pending, active] };
  const out = renderToStaticMarkup(<VersionsList data={data} diffs={{}} seen={[]} busy={false} highlight={draft.version} onOpenDiff={() => {}} onPost={() => {}}
    onDiscard={v => discarded.push(v.version)} />);
  assert.equal((out.match(/>Discard draft</g) ?? []).length, 1, 'only the draft offers it');
  assert.match(out, /aria-label="Knowledge base of 20 October 2026" class="[^"]*ring-2/, 'the new draft is highlighted');
  assert.ok(!out.includes('c-1a2b3c4d'), 'never the fingerprint');
  assert.ok(out.includes('>New<'));
});
