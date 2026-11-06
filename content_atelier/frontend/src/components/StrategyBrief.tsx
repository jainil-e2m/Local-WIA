import React from 'react';
import type { StrategyBrief } from '../api/types';

/* The window's strategy brief (E.B28), shown at Gate 1 and on a cycle: the beliefs this window's content should prove, each
   with its offer and the recent pieces not to repeat; the offers in force and what not to undercut; the season. It is
   assembled by the system from the knowledge base with no model call (R58), and the strategist was given exactly this. */

const STATUS: Record<string, string> = { open: 'open', waitlist: 'waitlist', delivering: 'delivering', closed: 'closed' };

/** The strategy brief as a reviewer reads it; `compact` leaves out the content plan and the do-not-repeat pieces. */
export function StrategyBriefPanel({ brief, compact = false }: { brief: StrategyBrief; compact?: boolean }) {
  const offers = brief.live_offers ?? [];
  return <section className="rounded-xl border bg-white p-4 space-y-3 text-sm" aria-label="This window's strategy brief">
    <div><h2 className="font-medium">This window’s strategy brief</h2>
      <p className="text-slate-600">Made by the system from the knowledge base{brief.on ? ` on ${brief.on.slice(0, 10)}` : ''}; the strategist was given exactly this.
        {brief.season?.label ? ` Season: ${brief.season.label}.` : ''}</p></div>
    {!!brief.warnings?.length && <ul className="ml-6 list-disc text-amber-800">{brief.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
    <div><p className="font-medium">Beliefs to prove</p>
      {brief.beliefs_to_prove.length ? <ol className="ml-6 list-decimal space-y-1">{brief.beliefs_to_prove.map(b => <li key={b.id}>
        <span>{b.belief}</span> <span className="text-slate-600">({b.stage}{b.offer ? ` · offer: ${b.offer}` : ''}{b.last_proved ? ` · last proved ${b.last_proved.slice(0, 10)}` : ''})</span>
        {!compact && !!b.do_not_repeat?.length && <p className="text-slate-600">Do not repeat: {b.do_not_repeat.map(p => p.title || p.key_message).join('; ')}</p>}
      </li>)}</ol> : <p className="text-slate-600">None this window.</p>}</div>
    <div><p className="font-medium">Offers in force</p>
      {offers.length ? <ul className="ml-6 list-disc">{offers.map(o => <li key={o.offer}>{o.offer} · {STATUS[o.status] ?? o.status}{o.sellable ? '' : ' (not for sale now)'}
        {o.ends ? ` · until ${o.ends.slice(0, 10)}` : ''}{o.do_not_undercut?.length ? `. Do not undercut: ${o.do_not_undercut.join('; ')}` : ''}</li>)}</ul>
        : <p className="text-slate-600">No offer is live this window.</p>}</div>
    {!compact && !!brief.recent_central_points?.length && <details><summary className="cursor-pointer">Recent central points ({brief.recent_central_points.length})</summary>
      <ul className="ml-6 list-disc">{brief.recent_central_points.map((p, i) => <li key={i}>{p.published_on?.slice(0, 10)}: {p.key_message}</li>)}</ul></details>}
  </section>;
}

/** Whether an API value is a well-formed strategy brief (a cycle preview may carry a partial one). */
export const isStrategyBrief = (value: unknown): value is StrategyBrief =>
  !!value && typeof value === 'object' && Array.isArray((value as StrategyBrief).beliefs_to_prove);
