import React from 'react';
import { Link } from 'react-router-dom';
import type { CycleOverview } from '../api/schema';
import { paths } from '../app/routes';
import { nextCycleWords } from '../utils/nextRun';
import { plainMessage } from '../utils/plainText';
import { isCycleOverview } from '../utils/workspace';
import { ErrorState, LoadingState } from './shared/states';

/* Home's cycle summary (6.F2, GET /summary), in a few plain lines, each with a link to where it is acted on: what needs a
   person, what is ready, what happens next. No ids, figures or technical states (the owner, 25 October 2026): those are on
   Sources and Settings, for an approver or an administrator. */

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const day = (iso: string) => {
  const date = new Date(`${iso.slice(0, 10)}T12:00:00Z`);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString('en-US', { timeZone: 'UTC', day: 'numeric', month: 'long' });
};
// A cycle's state as a person says it.
const CYCLE: Record<string, string> = {
  queued: 'starting', running: 'in progress', waiting: 'waiting to continue', waiting_for_review: 'ready for review', completed: 'done',
  partially_completed: 'done, though some calls could not be read in full', failed: 'stopped with a problem', cancelled: 'cancelled',
};
/** Why a pack waits, in its first sentence; a failed step is said without the failure's own text, which the pack shows. */
export const packReason = (reason: string) => reason.startsWith('A step failed') ? 'a step failed and can be tried again'
  : (plainMessage(reason).split(/(?<=\.)\s/)[0] ?? reason).replace(/\.$/, '').replace(/^./, c => c.toLowerCase());
const HELD_SHOWN = 3;

export interface SummaryLine { key: string; text: string; to?: string; action?: string }

/** Home's lines for an answer of the right shape. `packs` is the content packs flag (without it the pack lines, whose screens
    are off, are left out); `administration` (the people who see the Administration screens) adds the line on problems that
    need attention, which links there. Spending limits are an administrator's, under Alerts and costs. */
export function summaryLines(summary: CycleOverview, { packs, administration = true }: { packs: boolean; approver?: boolean; administration?: boolean }): SummaryLine[] {
  const { waiting, latest_cycle: latest, next_cycle: next, sources, alerts } = summary;
  const lines: SummaryLine[] = [];
  const cards = waiting.cards_at_gate_1;
  if (cards.count) lines.push({ key: 'cards', text: `${plural(cards.count, 'angle')} waiting for your review`, action: 'Review',
    to: cards.by_week.length === 1 ? paths.week(cards.by_week[0].week_id) : paths.angles });
  for (const c of waiting.held_cards_due_back.cards.slice(0, HELD_SHOWN)) {
    lines.push({ key: `held-${c.angle_id}`, text: `“${c.title || 'A held angle'}”, held until ${day(c.hold_until)}, is due back for your review`, action: 'Open', to: paths.angle(c.week_id, c.angle_id) });
  }
  const moreHeld = waiting.held_cards_due_back.count - Math.min(HELD_SHOWN, waiting.held_cards_due_back.cards.length);
  if (moreHeld > 0) lines.push({ key: 'held-more', text: `${plural(moreHeld, 'more held angle')} due back`, action: 'Open', to: paths.angles });
  if (waiting.briefs_at_gate_2.count) lines.push({ key: 'briefs', text: `${plural(waiting.briefs_at_gate_2.count, 'brief')} waiting for approval`, action: 'Review', to: paths.briefs });
  if (packs) {
    const generated = waiting.packs_in_review.count + waiting.packs_ready;
    if (generated) lines.push({ key: 'packs-generated', text: `${plural(generated, 'content pack')} generated`, action: 'Open', to: `${paths.packs}?state=generated` });
    for (const r of waiting.packs_with_the_system.reasons) lines.push({ key: `pack-${r.pack_id}`, text: `“${r.title || 'A content pack'}” is waiting: ${packReason(r.reason)}`, action: 'Open', to: paths.pack(r.pack_id) });
    if (waiting.packs_with_the_system.finishing) lines.push({ key: 'packs-finishing', text: `${plural(waiting.packs_with_the_system.finishing, 'content pack')} being written` });
  }
  if (!lines.length) lines.push({ key: 'nothing', text: 'Nothing is waiting for you' });
  // The latest cycle is said only while it is still running or stopped: once it is ready, its angles are the lines above.
  if (latest && !['waiting_for_review', 'completed', 'partially_completed'].includes(latest.status)) lines.push({ key: 'latest',
    text: `This week's cycle is ${CYCLE[latest.status] ?? 'in progress'}`, action: 'Open the week', to: paths.week(latest.week_id) });
  const nextWords = nextCycleWords(next);
  lines.push(nextWords ? { key: 'next', text: `Next cycle: ${nextWords}` }
    : { key: 'next', text: 'The cycle does not start by itself: an approver starts it from the Weekly Studio', action: 'Schedule settings', to: paths.settings });
  const stopped = sources.connections.some(c => c.health === 'error');
  if (administration && (stopped || alerts.open)) lines.push({ key: 'attention', text: stopped ? 'Call collection has stopped and needs attention' : `${plural(alerts.open, 'problem')} ${alerts.open === 1 ? 'needs' : 'need'} attention`, action: 'Open Sources', to: paths.alerts });
  return lines;
}

/** Home's summary with its loading and failure states, as a card in the mockup's style. A refresh that fails after a good
    answer keeps the answer on screen. */
export function HomeSummary({ summary, error, onRetry, packs, administration = true }: {
  summary: unknown; error: string; onRetry: () => void; packs: boolean; approver?: boolean; administration?: boolean;
  /** Kept for earlier callers; the card links to the Weekly Studio itself. */
  onOpenStudio?: () => void;
}) {
  const shaped = isCycleOverview(summary) ? summary : null;
  if (!shaped) return error ? <ErrorState message={error} onRetry={onRetry} /> : <LoadingState>Loading this week…</LoadingState>;
  return <section aria-label="This week" className="rounded-[24px] bg-white border border-[#E6E9F0] shadow-[0_10px_35px_rgba(28,49,76,0.06)] px-5 py-5 sm:px-7 sm:py-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="font-editorial text-[24px] leading-tight text-[#173354]">This week</h2>
      <Link to={paths.studio} className="text-[12px] font-medium text-[#5070FF] hover:underline">Open the Weekly Studio <span aria-hidden="true">→</span></Link>
    </div>
    {error && <div className="mt-3"><ErrorState message={error} onRetry={onRetry} /></div>}
    <ul className="mt-3 divide-y divide-[#EEF0F4]">{summaryLines(shaped, { packs, administration }).map(line => <li key={line.key}
      className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3 text-[13px] leading-relaxed text-[#34445F]">
      <span className="flex min-w-0 items-baseline gap-3"><span aria-hidden="true" className="h-1.5 w-1.5 shrink-0 translate-y-[-2px] rounded-full bg-[#C6A56A]" /><span>{line.text}.</span></span>
      {line.to && line.action && <Link className="shrink-0 text-[12px] font-medium text-[#5070FF] hover:underline" to={line.to}>{line.action}<span aria-hidden="true"> →</span></Link>}</li>)}</ul>
  </section>;
}
