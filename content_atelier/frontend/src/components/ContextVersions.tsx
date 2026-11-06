import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Layers } from 'lucide-react';
import type { CompileResult, KbVersion, KbVersions, VersionDiff } from '../api/types';
import { useApiQuery, useInvalidate } from '../api/query';
import { storageRequest } from '../utils/weeklyStorage';
import { capitalise, contextError, contextFailure, documentLabel, formatDate } from '../utils/context';
import { paths } from '../app/routes';
import { ConflictNotice, useGuardedAction } from './shared/conflict';
import { LoadingState } from './shared/states';
import { PageHeading } from './PageHeading';
import { ConfirmDialog, DARK_BUTTON, FIELD, HEADER_PRIMARY, LABEL, META, PANEL, Pill, QUIET_BUTTON, StatusLine, type Tone } from './AdminParts';

type DocumentChange = NonNullable<KbVersion['changes']>[string];

/* Knowledge → Versions. Each version is a dated copy of what the system knows; runs use the active one. "Compile a new version"
   asks first, says "Compiling…" while it runs, then says what happened beside the button and brings the new draft into view.
   A draft lists what it changes in plain words; an approver opens its changes and approves it with a note, or discards it (a
   draft that is active, approved or used by a run cannot be discarded). An identity change waits for a benchmark result
   before it becomes the default. */

const STATES: Record<string, { label: string; tone: Tone }> = {
  active: { label: 'Active', tone: 'approved' },
  approved_pending_benchmark: { label: 'Approved, waiting for a benchmark', tone: 'waiting' },
  draft: { label: 'Draft', tone: 'progress' },
  benchmark_failed: { label: 'Benchmark failed', tone: 'alert' },
  'published from files': { label: 'From the original files', tone: 'quiet' },
};
/** The badge a version shows; the one in use is "Active" whatever its recorded state. */
export function stateBadge(v: Pick<KbVersion, 'state' | 'active'>): { label: string; tone: Tone } {
  if (v.active) return STATES.active;
  return STATES[v.state] || { label: capitalise(String(v.state).replaceAll('_', ' ')), tone: 'quiet' };
}

/** A version by its date, never by its name (which carries a fingerprint). */
export function versionTitle(v: Pick<KbVersion, 'version' | 'on'>): string {
  const day = v.on || /(\d{4}-\d{2}-\d{2})/.exec(v.version)?.[1];
  return day ? `Knowledge base of ${formatDate(day)}` : 'Knowledge base from the original files';
}

export const CHANGE_LABELS: Record<Exclude<DocumentChange, 'unchanged'>, string> = {
  operating: 'takes effect when approved',
  identity: 'needs a benchmark first',
};
export function changedDocuments(changes: Record<string, DocumentChange> | null | undefined): { key: string; label: string; change: 'operating' | 'identity' }[] {
  return Object.entries(changes || {}).filter((e): e is [string, 'operating' | 'identity'] => e[1] === 'operating' || e[1] === 'identity')
    .map(([key, change]) => ({ key, label: capitalise(documentLabel(key)), change }));
}
export function pendingLines(pending: Record<string, number> | null | undefined): string[] {
  return Object.entries(pending || {}).filter(([, n]) => n > 0)
    .map(([key, n]) => `${n} ${n === 1 ? 'suggestion' : 'suggestions'} still waiting for review in ${documentLabel(key)}`);
}
const SCOPES: Record<string, string> = { weekly: 'Weekly cycle', weekly_cycle: 'Weekly cycle', brief: 'Brief', strategist: 'Weekly cycle', benchmark: 'Benchmark', smoke: 'Benchmark',
  kb_benchmark: 'Scheduled benchmark' };
export const runLabel = (r: { run_scope: string | null; status: string; created_at: string }) =>
  `${SCOPES[r.run_scope || ''] || capitalise((r.run_scope || 'run').replaceAll('_', ' '))}, ${r.status.replaceAll('_', ' ')}, ${formatDate(r.created_at)}`;

export function compileMessage(r: CompileResult): string {
  if (r.status === 'unchanged') return 'Nothing has changed since the active version, so no new version was made.';
  if (r.status === 'exists') return 'A version with exactly these contents already exists; it is highlighted below.';
  return `A new draft of ${formatDate(/(\d{4}-\d{2}-\d{2})/.exec(r.version)?.[1] ?? '') || 'today'} was made. Open its changes to review and approve it.`;
}

export type DiffLine = { kind: 'add' | 'remove' | 'context' | 'break'; text: string };
/** Unified diff lines as the screen shows them: file headers dropped, hunk headers (line offsets) shown as a break. */
export function diffLines(diff: string): DiffLine[] {
  const out: DiffLine[] = [];
  for (const line of diff.split('\n')) {
    if (line.startsWith('+++') || line.startsWith('---')) continue;
    if (line.startsWith('@@')) { if (out.length) out.push({ kind: 'break', text: '' }); continue; }
    if (line.startsWith('+')) out.push({ kind: 'add', text: line.slice(1) });
    else if (line.startsWith('-')) out.push({ kind: 'remove', text: line.slice(1) });
    else if (line.startsWith('\\')) continue;
    else out.push({ kind: 'context', text: line.startsWith(' ') ? line.slice(1) : line });
  }
  return out;
}

export function approveRequest(v: Pick<KbVersion, 'state' | 'version'>, note: string, diffSeen: boolean): { path: string; body: { note: string } } | { error: string } {
  if (v.state !== 'draft') return { error: 'Only a draft version can be approved.' };
  if (!diffSeen) return { error: 'Open the changes before approving.' };
  if (!note.trim()) return { error: 'Write a note saying why it is ready.' };
  return { path: `/context/versions/${encodeURIComponent(v.version)}/approve`, body: { note: note.trim() } };
}
export function benchmarkRequest(v: Pick<KbVersion, 'state' | 'version'>, passed: '' | 'yes' | 'no', resultRef: string, note: string):
  { path: string; body: { passed: boolean; result_ref: string; note?: string } } | { error: string } {
  if (v.state !== 'approved_pending_benchmark') return { error: 'Only an approved version waiting for its benchmark takes a result.' };
  if (!passed) return { error: 'Say whether the benchmark passed.' };
  if (!resultRef.trim()) return { error: 'Say where the result is, such as its report or file.' };
  return { path: `/context/versions/${encodeURIComponent(v.version)}/benchmark`, body: { passed: passed === 'yes', result_ref: resultRef.trim(), ...(note.trim() ? { note: note.trim() } : {}) } };
}
/** Whether a version may be discarded: a draft that is not active and that no run used (the server checks again). */
export const canDiscard = (v: Pick<KbVersion, 'state' | 'active' | 'runs'>) => v.state === 'draft' && !v.active && !v.runs.length;
export const discardPath = (version: string) => `/context/versions/${encodeURIComponent(version)}/discard`;

/** What the scheduled benchmark found, in words, for the approver who records the verdict. */
export function scheduledLines(v: Pick<KbVersion, 'scheduled_benchmark'>): string[] {
  const s = v.scheduled_benchmark;
  if (!s) return [];
  if (s.state === 'skipped') return [`The scheduled benchmark did not run: ${s.reason ?? 'its inputs are not available here'}. Benchmark this version from a checkout, then record the verdict.`];
  const regressions = s.regressions ?? [];
  const found = regressions.length ? `It found ${regressions.length === 1 ? 'a measure' : `${regressions.length} measures`} that got worse; decide whether it passed.`
    : 'It found no regression on the accuracy measures.';
  return [`The scheduled benchmark ran${s.ran_at ? ` on ${formatDate(s.ran_at)}` : ''} against the version before it. ${found}`, ...regressions, `Report: ${s.result_ref}`];
}
export const diffPath = (version: string) => `/context/versions/${encodeURIComponent(version)}/diff`;

const LINE_STYLES: Record<DiffLine['kind'], string> = {
  add: 'bg-emerald-50 text-emerald-900', remove: 'bg-red-50 text-red-900 line-through decoration-red-300', context: 'text-[#667184]', break: '',
};
export function DiffViewer({ diff }: { diff: VersionDiff }) {
  if (!diff.documents.length) return <p className="text-[13px]">No changes against the version before it.</p>;
  return <div className="space-y-3">{diff.documents.map(d => <section key={d.key} aria-label={`Changes to ${documentLabel(d.key)}`} className="overflow-hidden rounded-xl border border-[#E6E9F0] bg-white">
    <h4 className="border-b border-[#E6E9F0] bg-[#F7F8FB] px-4 py-2 text-[12px] font-semibold text-[#34445F]">{capitalise(documentLabel(d.key))}{d.change && d.change !== 'unchanged' ? ` · ${CHANGE_LABELS[d.change]}` : ''}</h4>
    <pre className="max-h-[28rem] overflow-auto p-2 font-mono text-[12px] leading-relaxed">{diffLines(d.diff).map((l, i) => l.kind === 'break'
      ? <div key={i} className="my-1 border-t border-dashed border-[#E6E9F0]" aria-hidden="true" />
      : <div key={i} data-line={l.kind} className={`whitespace-pre-wrap px-2 ${LINE_STYLES[l.kind]}`}><span aria-hidden="true" className="mr-2 select-none">{l.kind === 'add' ? '+' : l.kind === 'remove' ? '−' : ' '}</span>
        <span className="sr-only">{l.kind === 'add' ? 'Added: ' : l.kind === 'remove' ? 'Removed: ' : ''}</span>{l.text}</div>)}</pre>
  </section>)}</div>;
}

export function VersionCard({ v, diff, diffSeen, busy, highlighted = false, onOpenDiff, onPost, onDiscard }: {
  v: KbVersion; diff: VersionDiff | null; diffSeen: boolean; busy: boolean; highlighted?: boolean; onOpenDiff: () => void;
  onPost: (path: string, body: unknown, done: string) => void; onDiscard?: (v: KbVersion) => void;
}) {
  const [note, setNote] = useState('');
  const [passed, setPassed] = useState<'' | 'yes' | 'no'>('');
  // The scheduled benchmark's report, when it ran; the approver still decides whether it passed.
  const [resultRef, setResultRef] = useState(v.scheduled_benchmark?.result_ref ?? '');
  const [benchNote, setBenchNote] = useState('');
  const [error, setError] = useState('');
  const badge = stateBadge(v);
  const docs = changedDocuments(v.changes);
  const pending = pendingLines(v.pending_candidates);
  const approve = () => {
    const r = approveRequest(v, note, diffSeen);
    if ('error' in r) { setError(r.error); return; }
    setError(''); onPost(r.path, r.body, docs.some(d => d.change === 'identity') ? 'Approved. It becomes the default once its benchmark passes.' : 'Approved. It is now the active version.');
  };
  const bench = () => {
    const r = benchmarkRequest(v, passed, resultRef, benchNote);
    if ('error' in r) { setError(r.error); return; }
    setError(''); onPost(r.path, r.body, r.body.passed ? 'Benchmark recorded. The version is now active.' : 'Benchmark recorded as failed. The version stays out of use.');
  };
  const approvedLine = [v.approved_on ? `Approved on ${formatDate(v.approved_on)}` : v.approved_by ? 'Approved' : '', v.benchmark ? `benchmark ${v.benchmark.passed ? 'passed' : 'failed'}` : ''].filter(Boolean).join(' · ');
  // The new draft brings itself into view once it is on the list.
  const card = useRef<HTMLElement>(null);
  useEffect(() => { if (highlighted) card.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }); }, [highlighted]);
  return <article ref={card} aria-label={versionTitle(v)}
    className={`${PANEL} p-5 space-y-3 text-[13px] text-[#34445F] transition-shadow ${highlighted ? 'ring-2 ring-[#C8A83E] ring-offset-2 ring-offset-[#F6F7FB]' : ''}`}>
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="space-y-1">
        <h3 className="font-editorial text-[22px] leading-tight text-[#1B2433]">{versionTitle(v)}</h3>
        {approvedLine && <p className={META}>{approvedLine}</p>}
      </div>
      <div className="flex items-center gap-2">{highlighted && <Pill tone="waiting">New</Pill>}<Pill tone={badge.tone}>{badge.label}</Pill></div>
    </header>
    {docs.length > 0 ? <ul className="space-y-1" aria-label="What it changes">{docs.map(d => <li key={d.key} className="flex gap-2">
      <span aria-hidden="true" className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#C6A56A]" /><span><span className="text-[#1B2433]">{d.label}</span><span className="text-[#8B93A3]"> · {CHANGE_LABELS[d.change]}</span></span></li>)}</ul>
      : v.state !== 'published from files' && <p className="text-[#8B93A3]">No changes recorded.</p>}
    {pending.length > 0 && <ul className="space-y-0.5 rounded-xl bg-[#FFF8E9] p-3 text-[12px] text-[#947021]">{pending.map(p => <li key={p}>{p}</li>)}</ul>}
    {v.runs.length > 0 && <details><summary className="cursor-pointer text-[12px] text-[#8B93A3]">Used by {v.runs.length} {v.runs.length === 1 ? 'run' : 'runs'}</summary>
      <ul className="mt-1 ml-5 list-disc text-[12px] text-[#8B93A3]">{v.runs.map(r => <li key={r.run_id}>{runLabel(r)}</li>)}</ul></details>}
    {v.state !== 'published from files' && <div className="flex flex-wrap items-center gap-2 pt-1">
      <button type="button" className={QUIET_BUTTON} disabled={busy} onClick={onOpenDiff}>{diff ? 'Hide the changes' : 'See what changed'}</button>
      {onDiscard && canDiscard(v) && <button type="button" className={`${QUIET_BUTTON} !text-[#B42318]`} disabled={busy} onClick={() => onDiscard(v)}>Discard draft</button>}
    </div>}
    {diff && <DiffViewer diff={diff} />}
    {v.state === 'draft' && !v.active && <div className="space-y-2 border-t border-[#EEF0F4] pt-3">
      <p className="font-semibold text-[#1B2433]">Approve this version</p>
      {!diffSeen && <p className="text-[12px] text-[#8B93A3]">Open the changes first; approval unlocks once you have seen them.</p>}
      <div className="flex flex-wrap items-end gap-2">
        <label className={`${LABEL} grow min-w-64`}>Note (why it is ready)<input className={FIELD} value={note} onChange={e => setNote(e.target.value)} /></label>
        <button type="button" className={DARK_BUTTON} disabled={busy || !diffSeen} onClick={approve}>Approve</button>
      </div>
    </div>}
    {v.state === 'approved_pending_benchmark' && !v.active && <div className="space-y-2 border-t border-[#EEF0F4] pt-3">
      <p className="font-semibold text-[#1B2433]">Record benchmark result</p>
      {v.scheduled_benchmark && <ul aria-label="Scheduled benchmark" className="space-y-0.5 rounded-xl bg-[#EFF3FF] p-3 text-[12px] text-[#34445F]">{scheduledLines(v).map(l => <li key={l}>{l}</li>)}</ul>}
      <div className="flex gap-4"><label className="flex items-center gap-1.5"><input type="radio" checked={passed === 'yes'} onChange={() => setPassed('yes')} />Passed</label>
        <label className="flex items-center gap-1.5"><input type="radio" checked={passed === 'no'} onChange={() => setPassed('no')} />Failed</label></div>
      <label className={LABEL}>Where the result is (its report or file)<input className={FIELD} value={resultRef} onChange={e => setResultRef(e.target.value)} /></label>
      <label className={LABEL}>Note (optional)<input className={FIELD} value={benchNote} onChange={e => setBenchNote(e.target.value)} /></label>
      <button type="button" className={DARK_BUTTON} disabled={busy} onClick={bench}>Record benchmark result</button>
    </div>}
    <StatusLine tone="error">{error}</StatusLine>
  </article>;
}

export function VersionsList({ data, diffs, seen, busy, highlight, onOpenDiff, onPost, onDiscard }: {
  data: KbVersions; diffs: Record<string, VersionDiff>; seen: string[]; busy: boolean; highlight?: string; onOpenDiff: (v: KbVersion) => void;
  onPost: (path: string, body: unknown, done: string) => void; onDiscard?: (v: KbVersion) => void;
}) {
  if (!data.versions.length) return <p className={`${PANEL} p-5 text-[13px]`}>No compiled versions yet.</p>;
  return <div className="space-y-4">{data.versions.map(v => <VersionCard key={v.version} v={v} diff={diffs[v.version] || null} diffSeen={seen.includes(v.version)}
    busy={busy} highlighted={highlight === v.version} onOpenDiff={() => onOpenDiff(v)} onPost={onPost} onDiscard={onDiscard} />)}</div>;
}

export function ContextVersions() {
  const { version } = useParams();
  const navigate = useNavigate();
  const invalidate = useInvalidate();
  const versions = useApiQuery('/context/versions');
  // Approval unlocks only after the approver opened that version's changes in this session.
  const [seen, setSeen] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  const [highlight, setHighlight] = useState('');
  const [compiling, setCompiling] = useState(false);
  const [asking, setAsking] = useState(false);
  const [discarding, setDiscarding] = useState<KbVersion | null>(null);
  const guard = useGuardedAction(() => versions.refetch(), contextFailure);
  // The version in the URL has its changes open; the list is `/knowledge/versions`.
  const diff = useApiQuery('/context/versions/{version}/diff', { path: { version: version ?? '' } }, { enabled: !!version, staleTime: 60_000 });
  useEffect(() => {
    if (version && diff.data) setSeen(s => s.includes(version) ? s : [...s, version]);
  }, [version, diff.data]);
  const diffs: Record<string, VersionDiff> = version && diff.data ? { [version]: diff.data } : {};
  const toggleDiff = (v: KbVersion) => navigate(version === v.version ? paths.versions : paths.version(v.version));
  const refresh = () => invalidate('/context/versions', '/context/versions/{version}/diff', '/context/summary');
  const post = (path: string, body: unknown, done: string) => {
    setNotice('');
    return guard.run(async () => {
      await storageRequest(path, 'POST', body);
      setNotice(done);
      await refresh();
    });
  };
  const compile = async () => {
    setAsking(false); setNotice(''); setHighlight(''); setCompiling(true);
    const r = await guard.run(() => storageRequest<CompileResult>('/context/versions', 'POST', {}));
    setCompiling(false);
    if (!r) return;
    setNotice(compileMessage(r));
    if (r.status !== 'unchanged') setHighlight(r.version);
    await refresh();
  };
  const discard = async (v: KbVersion) => {
    setDiscarding(null); setNotice(''); setHighlight('');
    const done = await guard.run(async () => { await storageRequest(discardPath(v.version), 'POST', {}); return true; });
    if (!done) return;
    setNotice(`The draft ${versionTitle(v).replace(/^Knowledge base /, '')} was discarded.`);
    if (version === v.version) navigate(paths.versions);
    await refresh();
  };
  const error = guard.error || (versions.error ? contextError(versions.error).message : '') || (diff.error ? contextError(diff.error).message : '');
  const active = versions.data?.versions.find(v => v.active);
  return <section className="space-y-5" aria-label="Versions">
    <PageHeading title="Knowledge" subtitle={active ? `In use: the version of ${versionTitle(active).replace(/^Knowledge base of /, '')}` : 'Dated copies of what the system knows'}
      actions={<>
        <div className="max-w-xs text-right"><StatusLine tone="error">{error}</StatusLine><StatusLine>{notice}</StatusLine></div>
        <button type="button" className={HEADER_PRIMARY} disabled={guard.busy} onClick={() => setAsking(true)}>
          <Layers aria-hidden="true" className="h-3.5 w-3.5" />{compiling ? 'Compiling…' : 'Compile a new version'}</button>
      </>} />
    <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
    {versions.isPending && !versions.error && <LoadingState>Loading versions…</LoadingState>}
    {versions.data && <VersionsList data={versions.data} diffs={diffs} seen={seen} busy={guard.busy} highlight={highlight} onOpenDiff={toggleDiff}
      onPost={(p, b, d) => void post(p, b, d)} onDiscard={setDiscarding} />}
    {asking && <ConfirmDialog title="Compile a new version?" confirm="Compile" onCancel={() => setAsking(false)} onConfirm={() => void compile()}>
      <p>This makes a dated draft from what the system knows now: the confirmed facts, rules and published pieces.</p>
      <p>Runs keep using the active version until a draft is approved. A draft you do not want can be discarded.</p>
    </ConfirmDialog>}
    {discarding && <ConfirmDialog title="Discard this draft?" confirm="Discard draft" danger onCancel={() => setDiscarding(null)} onConfirm={() => void discard(discarding)}>
      <p>The draft {versionTitle(discarding).replace(/^Knowledge base /, '')} is removed for good. The active version is not affected, and you can compile again at any time.</p>
    </ConfirmDialog>}
  </section>;
}
