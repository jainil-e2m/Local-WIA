import React, { useEffect, useRef, useState } from 'react';
import type { StoredPackV2 } from '../api/types';
import { STATE_HINTS, STATE_LABELS, STATE_STYLES, type PackStateName } from './packFields';
import { FailureText } from './shared/JobProgress';

/* Small parts the content pack screens share (NP.F1 to NP.F4): the state chip with its reason in words, the Copy button,
   and the links between the list, a pack and a week. */

const enc = encodeURIComponent;
/** A pack's page under the list it was opened from (`/studio/packs` or `/packs`). */
export const packHref = (base: string, packId: string, piece?: string) => `${base}/${enc(packId)}${piece ? `?piece=${enc(piece)}` : ''}`;
/** A week's packs (the week view) under the same list. */
export const weekHref = (base: string, weekId: string) => `${base}/week/${enc(weekId)}`;

export const button = 'rounded-full border border-[#D8DFE8] bg-white px-4 py-2 text-sm text-[#173354] hover:bg-[#F4F6FA] disabled:opacity-40 disabled:cursor-not-allowed';
export const primary = 'rounded-full bg-[#5070FF] px-4 py-2 text-sm font-semibold text-white hover:bg-[#405FE6] disabled:opacity-40 disabled:cursor-not-allowed';
export const input = 'block w-full rounded-lg border border-[#D8DFE8] p-2 mt-1 text-sm';

/** The pack's state as a chip; with `reason`, the waiting or failure reason in words beside it. */
export function StateChip({ state }: { state: PackStateName }) {
  return <span data-state={state} className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${STATE_STYLES[state] ?? STATE_STYLES.in_review}`}>
    {STATE_LABELS[state] ?? state.replaceAll('_', ' ')}</span>;
}

/** The state and why, in words (R50): the API's reason, or what the state means. A failure's technical detail folds away. */
export function StateLine({ pack }: { pack: Pick<StoredPackV2, 'state' | 'state_reason'> }) {
  const reason = pack.state_reason || STATE_HINTS[pack.state];
  return <div className="flex flex-wrap items-start gap-2 text-sm" aria-label="Pack state">
    <StateChip state={pack.state} />
    <span className={`min-w-0 ${pack.state === 'waiting' ? 'text-amber-900' : 'text-slate-600'}`}>
      {pack.state === 'waiting' && pack.state_reason ? <FailureText summary={pack.state_reason} /> : reason}</span>
  </div>;
}

/** Copies text to the clipboard and says so. The label names what is copied, for screen readers; the result is said in a polite
    live region beside the button, since its label does not change (6.F6). */
export function CopyButton({ text, label, children = 'Copy', className }: { text: string; label: string; children?: React.ReactNode; className?: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setState('copied');
    } catch {
      setState('failed');
    }
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setState('idle'), 2000);
  };
  return <>
    <button type="button" aria-label={`Copy ${label}`} onClick={() => void copy()}
      className={className ?? 'shrink-0 text-xs font-medium text-[#5070FF] hover:underline'}>
      {state === 'copied' ? 'Copied' : state === 'failed' ? 'Could not copy' : children}
    </button>
    <span role="status" className="sr-only">{state === 'copied' ? 'Copied' : state === 'failed' ? 'Could not copy' : ''}</span>
  </>;
}

/** A quiet fold for what sits beside the copy and is read only when wanted (where a Reel's material is in the calls, the
    openings weighed, the editor's notes): one small blue line, closed until opened. */
export function Fold({ summary, children, label }: { summary: React.ReactNode; children: React.ReactNode; label?: string }) {
  return <details className="group text-[12px]" aria-label={label}>
    <summary className="inline-flex cursor-pointer list-none items-center gap-1 font-medium text-[#5070FF] hover:underline [&::-webkit-details-marker]:hidden">
      <span aria-hidden="true" className="inline-block transition-transform group-open:rotate-90">›</span>{summary}
    </summary>
    <div className="mt-2 pl-3 text-[#667184] leading-relaxed">{children}</div>
  </details>;
}

/** A date or time as the reader's own short date. */
export const shortDate = (value: string | null | undefined) => {
  if (!value) return '';
  const date = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
  return Number.isFinite(date.getTime()) ? date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric', ...(value.length === 10 ? { timeZone: 'UTC' } : {}) }) : value;
};
