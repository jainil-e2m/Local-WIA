import React, { useState } from 'react';
import type { Alert, AlertList, CostGroup, CostSummary, PackCost } from '../api/schema';
import { apiPost } from '../api/routes';
import { useApiQuery, useInvalidate } from '../api/query';
import { seesDetails, useMe } from '../utils/me';
import { ActionError, ConflictNotice, useGuardedAction } from './shared/conflict';
import { useWriteFeedback } from './shared/a11y';
import { EmptyState, ErrorState, LoadingState } from './shared/states';
import { PageHeading } from './PageHeading';
import { HEADING, PANEL, Pill, QUIET_BUTTON, plainReason } from './AdminParts';
import { stageName as plainStage } from './IntakeView';

/* The Sources screen's alerts and costs (6.F5). The alerts are the backend's failure alerts (6.B4: a failed job, a stuck
   queue, a stopped collection, a refused budget, a missed schedule, a missing backup, a low accepted share, a silent
   scheduler), open ones first, each by its severity and kind in words; an editor or an approver dismisses the ones the backend
   lets them (a stored alert, not the scheduler's silence, which is read live; a viewer reads them). Nothing is emailed: the app
   is the channel. The technical material is for an approver or an administrator only, folded away (the owner, 25 October
   2026): an alert's own message and when and how often it was seen, under its Details, and the costs (the recorded cost of
   model and embedding calls, 6.B7, this week and the recent budget weeks by purpose, stage and model, in USD) in a section
   read only when opened. */

const SEVERITY: Record<Alert['severity'], string> = { error: 'Error', warning: 'Warning' };
const KIND: Record<string, string> = {
  job_failed: 'A job failed', job_stuck: 'Work is stuck', intake_stopped: 'Collection stopped', budget_refused: 'Waiting for budget',
  schedule_missed: 'A scheduled run did not happen', backup_missing: 'No recent backup', restore_check_failed: 'Restore check',
  accepted_share_low: 'Few cards accepted', scheduler_silent: 'The scheduler is silent',
};
const when = (iso: string | null | undefined) => {
  const date = iso ? new Date(iso) : null;
  return date && !Number.isNaN(date.getTime()) ? date.toLocaleString('en-US', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'not recorded';
};
const times = (n: number) => n === 1 ? 'once' : `${n} times`;

/** Whether the backend lets a person dismiss this alert: a stored one that is still open. */
export const canDismiss = (alert: Pick<Alert, 'alert_id' | 'resolved_at'>) => !!alert.alert_id && !alert.resolved_at;

/** Who may dismiss, as the backend decides (alerts.py: an editor or an approver; a viewer reads). The server checks again. */
export const mayDismiss = (me: { can: { edit_cards: boolean; decide: boolean } }) => me.can.edit_cards || me.can.decide;

/** Open alerts first (the backend's order), then those resolved in the last 14 days. */
export function splitAlerts(list: Pick<AlertList, 'alerts'>): { open: Alert[]; resolved: Alert[] } {
  return { open: list.alerts.filter(a => !a.resolved_at), resolved: list.alerts.filter(a => !!a.resolved_at) };
}

const kindWords = (alert: Pick<Alert, 'kind'>) => KIND[alert.kind] ?? alert.kind.replaceAll('_', ' ');

/** One alert: its severity and kind in words, with Dismiss where allowed; `details` (an approver or an administrator) adds
    its own message and when and how often it was seen, folded under Details. */
export function AlertItem({ alert, busy, onDismiss, details = false }: { alert: Alert; busy: boolean; onDismiss?: (alert: Alert) => void; details?: boolean }) {
  return <li className="border-b border-[#EEF0F4] py-3 last:border-b-0 space-y-1">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="flex items-center gap-2 text-[13px]"><Pill tone={alert.severity === 'error' && !alert.resolved_at ? 'alert' : alert.resolved_at ? 'quiet' : 'waiting'}>{SEVERITY[alert.severity] ?? alert.severity}</Pill><span className="sr-only"> · </span><span className="font-medium text-[#1B2433]">{kindWords(alert)}</span></p>
      {onDismiss && canDismiss(alert) && <button type="button" className={QUIET_BUTTON} disabled={busy} onClick={() => onDismiss(alert)}
        aria-label={`Dismiss: ${kindWords(alert)}, last seen ${when(alert.last_seen_at)}`}>Dismiss</button>}
    </div>
    {alert.resolved_at && <p className="text-[12px] text-[#8B93A3]">Resolved {when(alert.resolved_at)}: {alert.resolution === 'dismissed' ? `dismissed by ${alert.resolved_by || 'a person'}` : 'it cleared by itself'}</p>}
    {details && <details className="text-[13px]"><summary className="cursor-pointer text-[12px] font-medium text-[#5070FF]">Details</summary>
      <p className="mt-1 text-[#1B2433]">{plainReason(alert.message)}</p>
      <p className="text-[12px] text-[#8B93A3]">First seen {when(alert.first_seen_at)} · last seen {when(alert.last_seen_at)} · seen {times(alert.occurrences)}</p>
      {!alert.alert_id && <p className="text-[12px] text-[#8B93A3]">Read live: it clears by itself when the scheduler runs again.</p>}
    </details>}
  </li>;
}

export function AlertsPanel() {
  const [showResolved, setShowResolved] = useState(false);
  const alerts = useApiQuery('/alerts', showResolved ? { query: { resolved: true } } : undefined, { refetchInterval: 60_000 });
  const invalidate = useInvalidate();
  const guard = useGuardedAction(() => alerts.refetch());
  const feedback = useWriteFeedback();
  const { me } = useMe();
  const allowed = mayDismiss(me), details = seesDetails(me);
  const dismiss = (alert: Alert) => void guard.run(async () => {
    await apiPost('/alerts/{alert_id}/dismiss', { path: { alert_id: alert.alert_id! }, body: {} });
    await invalidate('/alerts', '/summary');
    // The dismissed alert leaves the list, and its button with it: focus goes to the panel's heading.
    feedback.announce('Alert dismissed.', '#alerts-heading');
  });
  const data = alerts.data && Array.isArray(alerts.data.alerts) ? alerts.data : undefined;
  const { open, resolved } = data ? splitAlerts(data) : { open: [], resolved: [] };
  return <section aria-labelledby="alerts-heading" className={`${PANEL} p-5 space-y-3`}>
    {feedback.region}
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 id="alerts-heading" tabIndex={-1} className={HEADING}>Alerts{data ? ` (${open.length} open)` : ''}</h2>
      <label className="flex items-center gap-2 text-[12px] text-[#667184]"><input type="checkbox" checked={showResolved} onChange={e => setShowResolved(e.target.checked)} />
        Show those resolved in the last 14 days</label>
    </div>
    <p className="text-[12px] text-[#8B93A3]">Alerts show here and on the bell. None are emailed.</p>
    <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
    <ActionError message={guard.error} />
    {!data && (alerts.error ? <ErrorState message={alerts.error.message} onRetry={() => void alerts.refetch()} /> : <LoadingState>Loading the alerts…</LoadingState>)}
    {data && alerts.error && <ErrorState message={alerts.error.message} onRetry={() => void alerts.refetch()} />}
    {data && (open.length ? <ul aria-label="Open alerts">{open.map(a => <AlertItem key={a.alert_id ?? a.kind} alert={a} busy={guard.busy} onDismiss={allowed ? dismiss : undefined} details={details} />)}</ul>
      : <EmptyState>No open alerts: nothing is wrong.</EmptyState>)}
    {data && showResolved && <div className="space-y-1 pt-2">
      <h3 className="text-[13px] font-semibold text-[#34445F]">Resolved in the last 14 days</h3>
      {resolved.length ? <ul aria-label="Resolved alerts">{resolved.map(a => <AlertItem key={a.alert_id ?? a.kind} alert={a} busy={guard.busy} details={details} />)}</ul>
        : <p className="text-[13px] text-[#8B93A3]">None.</p>}
    </div>}
  </section>;
}

// ---- costs ---------------------------------------------------------------------------------------------------------------

/** A recorded cost in USD: cents for most amounts, four places for the fractions of a cent a single call costs. */
export const usd = (value: number) => `USD ${value !== 0 && Math.abs(value) < 0.1 ? value.toFixed(4) : value.toFixed(2)}`;
const weekOf = (iso: string) => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString('en-US', { timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric' });
};
const calls = (n: number) => `${n} ${n === 1 ? 'call' : 'calls'}`;

function CostTable({ caption, groups, name }: { caption: string; groups: CostGroup[]; name: (group: CostGroup) => string }) {
  return <table className="w-full text-[13px]">
    <caption className="pb-1 text-left text-[12px] font-semibold text-[#34445F]">{caption}</caption>
    <thead><tr className="text-left text-[11px] text-[#8B93A3]"><th scope="col" className="py-1 pr-3 font-normal">Name</th><th scope="col" className="py-1 pr-3 font-normal text-right">Calls</th><th scope="col" className="py-1 font-normal text-right">Cost</th></tr></thead>
    <tbody>{groups.length ? groups.map((g, i) => <tr key={i} className="border-t border-[#EEF0F4]">
      <td className="py-1 pr-3">{name(g)}{g.unknown_cost_calls ? <span className="text-amber-800"> ({g.unknown_cost_calls} with no recorded cost)</span> : null}</td>
      <td className="py-1 pr-3 text-right tabular-nums">{g.calls}</td><td className="py-1 text-right tabular-nums">{usd(g.usd)}</td></tr>)
      : <tr><td colSpan={3} className="py-1 text-[#8B93A3]">Nothing spent.</td></tr>}</tbody>
  </table>;
}

const purposeName = (g: CostGroup) => g.label || g.purpose || 'other';
const stageName = (g: CostGroup) => g.stage ? plainStage(g.stage) : 'Other';
const modelName = (g: CostGroup) => `${g.model || 'unknown model'}${g.provider ? ` (${g.provider})` : ''}`;

// "week_2026-10-18" -> "Week of Oct 18"
const weekName = (weekId: string | null | undefined) => {
  const day = weekId?.match(/(\d{4}-\d{2}-\d{2})$/)?.[1];
  return day ? `Week of ${new Date(`${day}T00:00:00Z`).toLocaleDateString('en-US', { timeZone: 'UTC', day: 'numeric', month: 'short' })}` : '';
};
const dayOf = (iso: string) => new Date(iso).toLocaleDateString('en-US', { timeZone: 'UTC', day: 'numeric', month: 'short' });

function Total({ label, value, note }: { label: string; value: string; note?: string }) {
  return <div className="rounded-xl bg-[#F6F7FA] p-4">
    <p className="text-[12px] text-[#667184]">{label}</p>
    <p className="text-[22px] font-semibold tabular-nums text-[#1B2433]">{value}</p>
    {note && <p className="text-[11px] text-[#8B93A3]">{note}</p>}
  </div>;
}

/** A pack's cost cell: what its run was charged, or why nothing was. */
function packCost(p: PackCost): string {
  if (p.calls > 0) return usd(p.usd) + (p.unknown_cost_calls ? ` + ${p.unknown_cost_calls} with no recorded cost` : '');
  if (p.reused_calls > 0) return `No new charge (made from answers that cost ${usd(p.reused_original_usd)} when first written)`;
  return 'No calls recorded';
}

/** Every content pack run, newest first, with the cost the model provider reported for each of its calls. */
export function PackCosts({ packs }: { packs: PackCost[] }) {
  const total = packs.reduce((sum, p) => sum + p.usd, 0);
  if (!packs.length) return <div className="text-[13px]">
    <p className="font-semibold text-[#34445F]">Cost of each content pack</p>
    <p className="text-[#8B93A3]">No content pack has been made yet. Each one shows here with what it cost.</p>
  </div>;
  return <table className="w-full text-[13px]">
    <caption className="pb-1 text-left"><span className="text-[13px] font-semibold text-[#34445F]">Cost of each content pack: {usd(total)} in all</span>
      <span className="block text-[12px] font-normal text-[#8B93A3]">What the model provider charged for each call, as it reported it. Finishing a pack again is a new row.</span></caption>
    <thead><tr className="text-left text-[11px] text-[#8B93A3]"><th scope="col" className="py-1 pr-3 font-normal">Pack</th><th scope="col" className="py-1 pr-3 font-normal">Week</th>
      <th scope="col" className="py-1 pr-3 font-normal">Made</th><th scope="col" className="py-1 font-normal text-right">Cost</th></tr></thead>
    <tbody>{packs.map(p => <tr key={p.run_id} className="border-t border-[#EEF0F4] align-top">
      <td className="py-1.5 pr-3">{p.title || 'A content pack'}{p.made_again && <span className="text-[#8B93A3]"> · made again</span>}{p.status === 'failed' && <span className="text-amber-800"> · stopped</span>}</td>
      <td className="py-1.5 pr-3 whitespace-nowrap">{weekName(p.week_id)}</td>
      <td className="py-1.5 pr-3 whitespace-nowrap">{dayOf(p.made_at)}</td>
      <td className="py-1.5 text-right tabular-nums">{packCost(p)}</td></tr>)}</tbody>
  </table>;
}

export function CostsView({ costs }: { costs: CostSummary }) {
  // The backend lists the window's weeks oldest first; the last is this week.
  const weeks = [...costs.weeks].reverse();
  const current = weeks[0];
  const packs = costs.packs ?? [];
  return <div className="space-y-5">
    <div className="grid gap-3 sm:grid-cols-2">
      <Total label={costs.since ? `Spent since ${weekOf(costs.since.start)}` : `Spent in the last ${weeks.length} weeks`}
        value={usd(costs.since ? costs.since.usd : costs.total_usd)}
        note={costs.since?.unknown_cost_calls ? `${costs.since.unknown_cost_calls} calls with no recorded cost` : undefined} />
      {current && <Total label="This week" value={usd(current.usd + current.external_usd)} note={`From ${weekOf(current.week_start)}`} />}
    </div>
    <PackCosts packs={packs} />
    <details className="text-[13px]"><summary className="cursor-pointer text-[12px] font-medium text-[#5070FF]">By week, purpose, stage and model</summary>
    <div className="mt-3 space-y-4">
    {current && <div className="space-y-3">
      <p className="text-[13px]"><span className="font-medium">This week</span> (from {weekOf(current.week_start)}): {usd(current.usd + current.external_usd)} over {calls(current.calls)}
        {current.unknown_cost_calls ? `, ${current.unknown_cost_calls} with no recorded cost` : ''}.</p>
      <div className="grid gap-4 lg:grid-cols-3">
        <CostTable caption="By purpose" groups={current.by_purpose} name={purposeName} />
        <CostTable caption="By stage" groups={current.by_stage} name={stageName} />
        <CostTable caption="By model" groups={current.by_model} name={modelName} />
      </div>
    </div>}
    <table className="w-full text-[13px]">
      <caption className="pb-1 text-left text-[12px] font-semibold text-[#34445F]">The last {weeks.length} weeks: {usd(costs.total_usd)} in all</caption>
      <thead><tr className="text-left text-[11px] text-[#8B93A3]"><th scope="col" className="py-1 pr-3 font-normal">Week from</th><th scope="col" className="py-1 pr-3 font-normal text-right">Calls</th>
        <th scope="col" className="py-1 pr-3 font-normal text-right">Cost</th><th scope="col" className="py-1 font-normal">Biggest purposes</th></tr></thead>
      <tbody>{weeks.map(w => <tr key={w.week_start} className="border-t border-[#EEF0F4]">
        <td className="py-1 pr-3">{weekOf(w.week_start)}</td><td className="py-1 pr-3 text-right tabular-nums">{w.calls}</td>
        <td className="py-1 pr-3 text-right tabular-nums">{usd(w.usd + w.external_usd)}</td>
        <td className="py-1">{w.by_purpose.filter(p => p.usd > 0).slice(0, 3).map(p => `${purposeName(p)} ${usd(p.usd)}`).join(', ') || 'nothing spent'}</td></tr>)}</tbody>
    </table>
    <details className="text-[13px]"><summary className="cursor-pointer text-[12px] font-medium text-[#5070FF]">The whole window by purpose, stage and model</summary>
      <div className="mt-2 grid gap-4 lg:grid-cols-3">
        <CostTable caption="By purpose" groups={costs.models.by_purpose} name={purposeName} />
        <CostTable caption="By stage" groups={costs.models.by_stage} name={stageName} />
        <CostTable caption="By model" groups={costs.models.by_model} name={modelName} />
      </div>
    </details>
    {costs.external.calls > 0 && <p className="text-[13px]">Other paid services: {usd(costs.external.usd)} over {calls(costs.external.calls)}
      ({costs.external.by_service.map(s => `${s.service} ${s.operation} ${usd(s.usd)}`).join(', ')}).</p>}
    </div></details>
    <p className="text-[12px] text-[#8B93A3]">Recorded cost only. Weeks start on Monday at 00:00 UTC.</p>
  </div>;
}

function CostsBody() {
  const costs = useApiQuery('/costs', undefined, { staleTime: 60_000, refetchInterval: 5 * 60_000 });
  const data = costs.data && Array.isArray(costs.data.weeks) ? costs.data : undefined;
  return <div className="mt-3 space-y-3">
    {!data && (costs.error ? <ErrorState message={costs.error.message} onRetry={() => void costs.refetch()} /> : <LoadingState>Loading the costs…</LoadingState>)}
    {data && costs.error && <ErrorState message={costs.error.message} onRetry={() => void costs.refetch()} />}
    {data && <CostsView costs={data} />}
  </div>;
}

/** The costs, for an approver or an administrator: the totals at a glance, each pack's cost, the breakdown folded away. */
export function CostsPanel() {
  return <section aria-labelledby="costs-heading" className={`${PANEL} p-5`}>
    <h2 id="costs-heading" className={HEADING}>Costs</h2>
    <CostsBody />
  </section>;
}

/** The Sources tab: the alerts, and the costs for an approver or an administrator. */
export function AlertsAndCosts() {
  const { me } = useMe();
  return <div className="space-y-6"><PageHeading title="Sources" subtitle="Alerts and costs" /><AlertsPanel />{seesDetails(me) && <CostsPanel />}</div>;
}
