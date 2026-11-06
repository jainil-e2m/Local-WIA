import { plainMessage } from '../utils/plainText';
import React, { useState } from 'react';
import type { CycleDetail, CyclePreview, CycleSummary, StandingBudgets, WeekMeasures } from '../api/schema';
import { apiGet, apiPost } from '../api/routes';
import { useApiQuery, useInvalidate } from '../api/query';
import { ActionError, ConflictNotice, useGuardedAction } from './shared/conflict';
import { ErrorState, LoadingState } from './shared/states';
import { StrategyBriefPanel, isStrategyBrief } from './StrategyBrief';
import { FailureText } from './shared/JobProgress';
import { REASON_CODES } from './CardReview';
import { DateInput } from './DateInput';

/* A cycle over a date window, from the app (3.B2/3.B3): an approver picks the window, sees what the cycle would read and what
   it would cost (the documents, the calls that arrived after their own window's cycle, the undated ones to add by hand, the
   estimate and this week's standing budgets), then starts it. The cycles list says what each read and whether every verified
   scene reached the strategist. The week's review document (5.B14) downloads from the Weekly Studio's header, and the
   week's editorial monitoring (6.B13) says how the cycle went: the accepted share against the bar, why cards were skipped,
   the cards whose evidence was flagged, what the cycle ran on and cost, and whether the schedule started it. */

const button = 'rounded-full border border-[#E6E9F0] bg-white px-3.5 py-2 text-[12px] font-medium text-[#34445F] hover:bg-[#F7F8FB] disabled:opacity-40';
const usd = (value: number | null | undefined) => value == null ? 'unknown' : `USD ${value.toFixed(2)}`;
const day = (iso: string | null | undefined) => iso ? iso.slice(0, 10) : 'undated';

/** The default window: the seven days before today, as calendar dates. */
export function defaultWindow(now: Date = new Date()): { from: string; to: string } {
  const to = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const from = new Date(to.getTime() - 7 * 86_400_000);
  return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) };
}

/** A calendar date as the start of that day in UTC, as the API takes a window. */
export const windowInstant = (date: string) => `${date}T00:00:00Z`;

const BECAUSE: Record<string, string> = {
  window: 'in the window', late_arrival: 'arrived after its own window’s cycle', undated: 'undated', added_by_person: 'added by hand',
};

const COVERAGE: Record<string, string> = {
  not_extracted: 'the calls are not read yet', extracted: 'the calls are read; the ideas are not drawn yet',
  complete: 'every call was read in full', incomplete: 'some calls were not read in full',
};

export function coverageWords(cycle: Pick<CycleSummary, 'coverage_state' | 'scenes_sent' | 'scenes_verified'>): string {
  return COVERAGE[cycle.coverage_state] ?? cycle.coverage_state.replaceAll('_', ' ');
}
// A cycle's state as a person says it.
const STATUS: Record<string, string> = {
  queued: 'starting', running: 'in progress', waiting: 'waiting to continue', waiting_for_review: 'ready for review', completed: 'done',
  partially_completed: 'done', failed: 'stopped with a problem', cancelled: 'cancelled',
};
const weekWindow = (start: string, end: string) => {
  const date = (value: string) => new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
  // The window's end is the next week's first day; the week shown ends the day before.
  return `${date(start)} – ${date(new Date(new Date(end).getTime() - 86_400_000).toISOString())}, ${new Date(start).getUTCFullYear()}`;
};

export function BudgetSummary({ budgets }: { budgets: StandingBudgets }) {
  return <div className="text-sm">
    <p className="font-medium">This week’s spending · {usd(budgets.total_spent_usd)}{budgets.uncapped ? ' · no weekly limits' : ` of ${usd(budgets.total_cap_usd)}`}</p>
    {!budgets.enabled && <p className="text-amber-800">Weekly spending limits are switched off, so no paid work starts by itself.</p>}
    <ul className="mt-1 grid gap-1 md:grid-cols-3">{budgets.budgets.map(b => <li key={b.purpose}>
      {b.label}: {budgets.uncapped ? `${usd(b.spent_usd)} spent` : b.cap_usd == null ? 'no budget set' : `${usd(b.left_usd)} left of ${usd(b.cap_usd)}`}
      {b.waiting_jobs ? <span className="text-amber-800"> · {b.waiting_jobs} waiting</span> : null}
    </li>)}</ul>
  </div>;
}

export function CyclePreviewView({ preview, include, onToggle }: { preview: CyclePreview; include: string[]; onToggle: (id: string) => void }) {
  const estimate = preview.estimate;
  return <div className="space-y-3 text-sm">
    <p className="font-medium">{preview.document_count} {preview.document_count === 1 ? 'call' : 'calls'} from {day(preview.window.start)} to {day(preview.window.end)}</p>
    <ul className="ml-5 list-disc">{[...preview.documents, ...preview.late_arrivals].map(d => <li key={d.transcript_id}>
      {d.title || d.transcript_id} · {day(d.occurred_at)} · {BECAUSE[d.selected_because] ?? d.selected_because}
    </li>)}</ul>
    {!!preview.late_arrivals.length && <p>{preview.late_arrivals.length} arrived after their own window’s cycle had run, so this cycle reads them.</p>}
    {/* Folded: the archive holds about 160 undated calls, and the open list pushed the estimate and Start a screen away. */}
    {!!preview.undated.length && <details className="rounded-lg border p-3">
      <summary className="cursor-pointer">Undated calls no window can reach ({preview.undated.length}){include.length ? ` · ${include.length} added to this cycle` : ''}: add one by hand</summary>
      <fieldset className="mt-2 max-h-64 overflow-y-auto"><legend className="sr-only">Undated calls to add to this cycle</legend>
        {preview.undated.map(d => <label key={d.transcript_id} className="flex gap-2"><input type="checkbox" checked={include.includes(d.transcript_id)} onChange={() => onToggle(d.transcript_id)} />
          Add {d.title || d.transcript_id} to this cycle</label>)}
      </fieldset>
    </details>}
    {!!preview.earlier_cycles.length && <p className="text-amber-800">{preview.earlier_cycles.length} earlier {preview.earlier_cycles.length === 1 ? 'cycle' : 'cycles'} already covered part of this window.</p>}
    {estimate ? <div className="rounded-lg bg-slate-50 p-3">
      <p className="font-medium">Estimated cost: {usd(estimate.total_usd)} (nothing is sent until you start)</p>
      <ul className="ml-5 list-disc">{estimate.components.map(c => <li key={c.stage}>{c.stage}: {c.calls} {c.calls === 1 ? 'call' : 'calls'}, {usd(c.usd)}</li>)}</ul>
      <p className="text-xs text-slate-600">{estimate.note} Assumes {estimate.assumptions}.</p>
      {estimate.notes.map((n, i) => <p key={i} className="text-xs text-amber-800">{n}</p>)}
    </div> : <p>No call falls in this window.</p>}
    {isStrategyBrief(preview.strategy_brief) && <StrategyBriefPanel brief={preview.strategy_brief} compact />}
    {!preview.within_budget && <p role="alert" className="text-amber-800">The estimate is more than this week’s cycle and extraction budgets have left. The cycle can start; a call that would pass a budget waits, and says so, until the budget is raised or renews.</p>}
  </div>;
}

export function CycleList({ cycles, onOpen }: { cycles: CycleSummary[]; onOpen: (runId: string) => void }) {
  if (!cycles.length) return <p className="text-sm">No cycle has been started from a window yet.</p>;
  return <ul className="space-y-2 text-sm">{cycles.map(c => <li key={c.run_id} className="border-t border-[#EEF0F4] pt-2">
    <button type="button" className="font-medium text-[#5070FF] hover:underline" onClick={() => onOpen(c.run_id)}>{c.window ? weekWindow(c.window.start, c.window.end) : c.week_id}</button>
    {' '}· {c.document_count} calls · {STATUS[c.status] ?? c.status.replaceAll('_', ' ')} · {coverageWords(c)}
  </li>)}</ul>;
}

/** A cycle's stages; a failed or waiting one can be retried here by an approver (it said "a retry sends only these" with
    no control beside it until the N1 shakedown). */
export function CycleDetailView({ cycle, onRetry, busy = false }: { cycle: CycleDetail; onRetry?: (jobId: string) => void; busy?: boolean }) {
  return <div className="space-y-2 text-[13px] rounded-xl bg-[#F7F8FB] p-4">
    {cycle.waiting_reason && <p role="status" className="text-amber-800">Waiting: {cycle.waiting_reason}</p>}
    {cycle.error_summary && <div role="alert" className="text-red-800"><FailureText summary={cycle.error_summary} /></div>}
    <p>{coverageWords(cycle)}{cycle.estimate ? ` · started on an estimate of ${usd(cycle.estimate.total_usd)}` : ''}</p>
    <ul className="ml-5 list-disc">{cycle.documents.map(d => {
      const seen = cycle.scene_coverage.documents.find(x => x.transcript_id === d.transcript_id);
      return <li key={d.transcript_id}>{d.title || 'A call'} · {day(d.occurred_at)} · {BECAUSE[d.selected_because] ?? d.selected_because}
        {seen?.held_for_consent ? ` · ${seen.held_for_consent} ${seen.held_for_consent === 1 ? 'passage' : 'passages'} held back for consent` : ''}</li>;
    })}</ul>
    <ul>{cycle.stages.map(s => <li key={s.job_id}>{stageName(s.stage)}: {STATUS[s.status] ?? s.status.replaceAll('_', ' ')}{s.current_message ? ` · ${plainMessage(s.current_message)}` : ''}
      {onRetry && ['failed', 'waiting'].includes(s.status) && <button type="button" className={`${button} ml-3`} disabled={busy} onClick={() => onRetry(s.job_id)}>Retry this step</button>}</li>)}</ul>
    {isStrategyBrief(cycle.strategy_brief) && <StrategyBriefPanel brief={cycle.strategy_brief} compact />}
  </div>;
}

const STAGES: Record<string, string> = {
  moment_extraction: 'Reading the calls', moment_embedding: 'Preparing the calls for search', angle_generation: 'Drawing the ideas',
  card_verification: 'Checking the ideas', strategy_brief: 'The week’s plan', matching: 'Comparing with earlier content',
};
const stageName = (stage: string) => STAGES[stage] ?? stage.replaceAll('_', ' ').replace(/^./, c => c.toUpperCase());
const percent = (share: number) => `${Math.round(share * 100)}%`;
const reasonWords = (code: string | null | undefined) => code ? REASON_CODES.find(([value]) => value === code)?.[1] ?? code.replaceAll('_', ' ') : 'No reason given';

/** Whether an answer has the monitoring's shape (a screen test may stub other routes). */
const isMeasures = (value: unknown): value is WeekMeasures => !!(value as WeekMeasures | undefined)?.monitoring?.cycle && !!(value as WeekMeasures).cards;

/** The week's editorial monitoring (6.B13). Everyone reads, in words, how many cards were taken forward at Gate 1 against the
    aim (judged once Gate 1 is done, by the backend's rule, the one its low-share alert uses: at least four cards decided) and
    whether the schedule started the week. The rest (why cards were skipped, the evidence flags, the knowledge base and
    strategist the cycle ran on, what it cost) is folded under Details for an approver (the owner, 25 October 2026). */
export function MonitoringView({ measures, details = false }: { measures: WeekMeasures; details?: boolean }) {
  const m = measures.monitoring;
  const slate = measures.cards.slate;
  const chose = measures.cards.developed_or_reframed_keeping_the_point.all;
  const share = m.accepted_share;
  const aim = m.bar === 0.5 ? 'at least half' : `at least ${percent(m.bar)}`;
  return <div className="space-y-1 text-sm" aria-label="How this week went" role="group">
    <p>{!slate ? 'No angles this week yet.' : `${chose} of ${slate} angles approved${m.gate_1_done && share != null && share < m.bar ? `, below the aim of ${aim}` : ''}.`}</p>
    <p>{!m.cycle.run_id ? 'No cycle has run for this week.' : m.cycle.started_from === 'schedule' ? 'This week was started by the schedule.' : 'This week was started from the app.'}</p>
    {details && <details><summary className="cursor-pointer text-slate-600">Details</summary>
      <div className="mt-1 space-y-1">
        {m.skip_reasons.length ? <div><p>Skipped ({m.skip_reasons.length}):</p><ul className="ml-5 list-disc">{m.skip_reasons.map((s, i) => <li key={i}>
          {s.title || 'An angle'}: {reasonWords(s.reason_code)}{s.note ? `. ${s.note}` : ''}</li>)}</ul></div> : <p>No angle was skipped.</p>}
        <p>{m.cards_with_evidence_flags ? `${m.cards_with_evidence_flags} ${m.cards_with_evidence_flags === 1 ? 'angle had' : 'angles had'} a point to check against the call.` : 'No angle had a point to check against the call.'}</p>
        {m.cycle.run_id && <p>The cycle cost {usd(m.cycle.cost_usd)} over {m.cycle.model_calls} model {m.cycle.model_calls === 1 ? 'call' : 'calls'}.</p>}
      </div>
    </details>}
  </div>;
}

/** The cycle panel of the week screen (folded under "Cycle details"): budgets, the cycles, the week's monitoring, and for an
    approver, "Run cycle". */
export function CyclePanel({ weekId, canDecide }: { weekId: string; canDecide: boolean }) {
  const invalidate = useInvalidate();
  const cycles = useApiQuery('/cycles', {}, { refetchInterval: data => Array.isArray(data) && data.some(c => ['queued', 'running'].includes(c.status)) ? 8_000 : 30_000 });
  const budgets = useApiQuery('/budgets');
  // The week's measures read every decision of two weeks: read once a minute at most.
  const measures = useApiQuery('/weeks/{week_id}/measures', { path: { week_id: weekId } }, { enabled: !!weekId, staleTime: 60_000, refetchInterval: 60_000 });
  const [open, setOpen] = useState<string | null>(null);
  const detail = useApiQuery('/cycles/{run_id}', { path: { run_id: open ?? '' } }, { enabled: !!open });
  const [range, setRange] = useState(defaultWindow());
  const [preview, setPreview] = useState<CyclePreview | null>(null);
  const [include, setInclude] = useState<string[]>([]);
  const guard = useGuardedAction();
  const look = () => guard.run(async () => {
    setPreview(null); setInclude([]);
    setPreview(await apiGet('/cycles/preview', { query: { from: windowInstant(range.from), to: windowInstant(range.to) } }, { timeoutMs: 60_000 }));
  });
  const start = () => preview && guard.run(async () => {
    const started = await apiPost('/cycles', { body: { window_start: preview.window.start, window_end: preview.window.end, selection_hash: preview.selection_hash, mode: 'live', include_undated: include } });
    setPreview(null);
    await invalidate('/cycles', '/budgets', '/weeks', '/weeks/{week_id}');
    const runId = (started as { run_id?: string }).run_id;
    if (runId) setOpen(runId);
  });
  return <section className="rounded-2xl border border-[#E6E9F0] bg-white p-6 space-y-5 text-[13px] text-[#34445F] shadow-[0_3px_18px_rgba(28,36,52,0.035)]" aria-label="Cycles">
    {/* The week's review document downloads from the Weekly Studio's header ("Download review"). */}
    <h2 className="font-editorial text-[22px] text-[#1B2433]">Weekly cycles</h2>
    {/* Shown only once a well-formed answer arrives (a screen test may stub other routes). */}
    {/* With no weekly limits (budgets.uncapped) there is nothing to show here; the costs are under Alerts and costs. */}
    {Array.isArray(budgets.data?.budgets) && !budgets.data.uncapped && <BudgetSummary budgets={budgets.data} />}
    {budgets.error && <ErrorState message={budgets.error.message} onRetry={() => void budgets.refetch()} />}
    {isMeasures(measures.data) && <MonitoringView measures={measures.data} details={canDecide} />}
    {measures.error && !measures.data && <ErrorState message={`The week's monitoring could not be read: ${measures.error.message}`} onRetry={() => void measures.refetch()} />}
    <ConflictNotice conflict={guard.conflict} onReload={() => void look()} onDismiss={guard.clear} />
    <ActionError message={guard.error} />
    {canDecide ? <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label>From <DateInput className="ml-1 h-9 rounded-full border border-[#E6E9F0] bg-white px-3 text-[12px]" value={range.from} onChange={e => { setRange({ ...range, from: e.target.value }); setPreview(null); }} /></label>
        <label>To (not included) <DateInput className="ml-1 h-9 rounded-full border border-[#E6E9F0] bg-white px-3 text-[12px]" value={range.to} onChange={e => { setRange({ ...range, to: e.target.value }); setPreview(null); }} /></label>
        <button type="button" className={button} disabled={guard.busy || !range.from || !range.to} onClick={() => void look()}>Run cycle</button>
      </div>
      {preview && <>
        <CyclePreviewView preview={preview} include={include} onToggle={id => setInclude(include.includes(id) ? include.filter(x => x !== id) : [...include, id])} />
        <div className="flex gap-3">
          <button type="button" className={button} disabled={guard.busy || (!preview.document_count && !include.length)} onClick={() => void start()}>Start the cycle</button>
          <button type="button" className={button} disabled={guard.busy} onClick={() => setPreview(null)}>Cancel</button>
        </div>
      </>}
    </div> : <p className="text-sm text-slate-600">Starting a cycle needs the approver role.</p>}
    {cycles.isPending && !cycles.error && <LoadingState>Loading cycles…</LoadingState>}
    {cycles.error && <ErrorState message={cycles.error.message} onRetry={() => void cycles.refetch()} />}
    {Array.isArray(cycles.data) && <CycleList cycles={cycles.data} onOpen={id => setOpen(open === id ? null : id)} />}
    {open && detail.data?.scene_coverage && <CycleDetailView cycle={detail.data} busy={guard.busy}
      onRetry={canDecide ? jobId => void guard.run(async () => {
        await apiPost('/jobs/{job_id}/retry', { path: { job_id: jobId }, body: {} });
        await invalidate('/cycles', '/cycles/{run_id}');
      }) : undefined} />}
  </section>;
}
