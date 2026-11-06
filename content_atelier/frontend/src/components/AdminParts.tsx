import React from 'react';
import { Link } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import { useModalBehavior } from './useModalBehavior';
import { plainMessage } from '../utils/plainText';
import { Select } from './ThemedSelect';

/* The pieces the administrator screens share (Sources, Moments, Knowledge, Settings), in the 20 October mockup's idiom: white
   rounded cards with a soft shadow, serif headings, pill buttons and quiet grey text. A form used now and then opens in a
   dialog from a button; a change says what happened where it was pressed. */

/** The mockup's card surface. */
export const PANEL = 'rounded-2xl border border-[#E6E9F0] bg-white shadow-[0_3px_18px_rgba(28,36,52,0.035)] [overflow-wrap:anywhere]';
/** A section heading inside a page ("Processing", "Weekly buckets"). */
export const HEADING = 'font-editorial text-[22px] leading-tight text-[#1B2433]';
/** Quiet grey text for a meta line. */
export const META = 'text-[12px] text-[#8B93A3]';
/** The page header's buttons, the height of the top bar's own. */
export const HEADER_QUIET = 'inline-flex h-10 items-center gap-2 rounded-full border border-[#E6E9F0] bg-white px-4 text-[12px] text-[#34445F] hover:bg-[#F7F8FB] disabled:opacity-40 disabled:cursor-not-allowed';
export const HEADER_PRIMARY = 'atelier-page-primary inline-flex h-10 items-center gap-2 rounded-full px-5 text-[12px] disabled:opacity-50 disabled:cursor-not-allowed';
/** Buttons inside a card or a dialog. */
export const QUIET_BUTTON = 'inline-flex items-center gap-1.5 rounded-full border border-[#E6E9F0] bg-white px-3.5 py-2 text-[12px] font-medium text-[#34445F] hover:bg-[#F7F8FB] disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8DA1FD]';
export const DARK_BUTTON = 'inline-flex items-center gap-1.5 rounded-full bg-[#1B2838] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#34445F] disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8DA1FD]';
export const DANGER_BUTTON = 'inline-flex items-center gap-1.5 rounded-full bg-[#B42318] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#912018] disabled:opacity-40 disabled:cursor-not-allowed';
export const TEXT_BUTTON = 'text-[12px] font-medium text-[#5070FF] hover:underline disabled:opacity-40';
/** Form controls. */
export const LABEL = 'block text-[12px] font-medium text-[#667184]';
export const FIELD = 'mt-1.5 block w-full rounded-xl border border-[#E6E9F0] bg-white px-3 py-2 text-[13px] text-[#1B2433] placeholder:text-[#A3AAB8] focus:outline-none focus:border-[#8DA1FD]';
export const SELECT = 'h-9 rounded-full border border-[#E6E9F0] bg-white pl-3.5 pr-3 text-[12px] text-[#34445F] hover:border-[#BCC8ED] focus:outline-none focus:border-[#8DA1FD]';

export type Tone = 'waiting' | 'approved' | 'quiet' | 'alert' | 'progress';
const TONES: Record<Tone, string> = {
  waiting: 'bg-[#FFF8E9] text-[#947021]', approved: 'bg-emerald-50 text-emerald-700', quiet: 'bg-[#F1F3F7] text-[#667184]',
  alert: 'bg-red-50 text-red-800', progress: 'bg-[#EFF3FF] text-[#5070FF]',
};
export function Pill({ tone = 'quiet', children, title }: { tone?: Tone; children: React.ReactNode; title?: string }) {
  return <span title={title} className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-[10px] font-medium ${TONES[tone]}`}>{children}</span>;
}

/** The tabs under a page's header ("All documents · Intake · Weekly cycle · Alerts and costs"). */
export function PageTabs({ label, tabs, current }: { label: string; tabs: readonly (readonly [string, string, string])[]; current: string }) {
  return <nav aria-label={label} className="inline-flex max-w-full flex-wrap items-center gap-1 rounded-full border border-[#E6E9F0] bg-white p-1 text-[12px]">
    {tabs.map(([id, text, to]) => <Link key={id} to={to} aria-current={current === id ? 'page' : undefined}
      className={`rounded-full px-4 py-2 font-medium ${current === id ? 'bg-[#1B2838] text-white' : 'text-[#667184] hover:text-[#1B2433]'}`}>{text}</Link>)}
  </nav>;
}

/** A short line beside the button that was pressed: what happened, or why it did not. */
export function StatusLine({ tone = 'done', children }: { tone?: 'done' | 'error' | 'quiet'; children: React.ReactNode }) {
  if (!children) return null;
  const color = tone === 'error' ? 'text-red-800' : tone === 'quiet' ? 'text-[#667184]' : 'text-emerald-700';
  return <p role={tone === 'error' ? 'alert' : 'status'} className={`text-[12px] ${color}`}>{children}</p>;
}

/** The search box of a list. */
export function SearchBox({ value, onChange, label, placeholder }: { value: string; onChange: (value: string) => void; label: string; placeholder: string }) {
  return <div className="relative min-w-56 grow max-w-xs">
    <Search aria-hidden="true" className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#9AA3B2]" />
    <input type="search" aria-label={label} value={value} maxLength={200} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      className="h-9 w-full rounded-full border border-[#E6E9F0] bg-white pl-9 pr-4 text-[12px] text-[#1B2433] placeholder:text-[#A3AAB8] focus:outline-none focus:border-[#8DA1FD]" />
  </div>;
}

/** A filter dropdown in a list's bar: its label is read by a screen reader and shown as the first choice. */
export function FilterSelect({ label, value, any = 'Any', options, onChange }: {
  label: string; value: string; any?: string; options: readonly { value: string; label: string }[]; onChange: (value: string) => void;
}) {
  return <label className="inline-flex items-center"><span className="sr-only">{label}</span>
    <Select className={`${SELECT} max-w-[15rem]`} value={value} onChange={e => onChange(e.target.value)}>
      <option value="">{any}</option>{options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </Select></label>;
}

/** "More filters": the rarely used filters, folded. The count says how many of them are set. */
export function MoreFilters({ active, children }: { active: number; children: React.ReactNode }) {
  return <details className="group w-full" open={active > 0 || undefined}>
    <summary className="inline-flex cursor-pointer list-none items-center gap-1 text-[12px] font-medium text-[#5070FF] [&::-webkit-details-marker]:hidden">
      <span className="group-open:hidden">More filters</span><span className="hidden group-open:inline">Fewer filters</span>{active > 0 && <span>({active})</span>}
    </summary>
    <div className="mt-3 flex flex-wrap items-end gap-3">{children}</div>
  </details>;
}

/** Previous and Next under a list, with where the page is. */
export function Pager({ range, onPrevious, onNext, hasPrevious, hasNext }: { range: string; onPrevious: () => void; onNext: () => void; hasPrevious: boolean; hasNext: boolean }) {
  return <div className="flex flex-wrap items-center justify-between gap-3 text-[12px] text-[#8B93A3]">
    <span aria-live="polite">{range}</span>
    <div className="flex gap-2"><button type="button" className={QUIET_BUTTON} disabled={!hasPrevious} onClick={onPrevious}>Previous</button>
      <button type="button" className={QUIET_BUTTON} disabled={!hasNext} onClick={onNext}>Next</button></div>
  </div>;
}

/** A dialog for an occasional form or a long text: the serif title, a close button, a scrolling body and its buttons. */
export function Dialog({ title, onClose, children, footer, wide = false, label }: {
  title: string; onClose: () => void; children: React.ReactNode; footer?: React.ReactNode; wide?: boolean; label?: string;
}) {
  const ref = useModalBehavior(onClose);
  return <div data-lenis-prevent className="atelier-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6" onClick={onClose}>
    <div ref={ref} role="dialog" aria-modal="true" aria-label={label ?? title} tabIndex={-1} onClick={e => e.stopPropagation()}
      className={`atelier-modal flex max-h-[90dvh] w-full flex-col overflow-hidden border bg-white ${wide ? 'max-w-3xl' : 'max-w-xl'}`}>
      <div className="flex items-start justify-between gap-3 border-b border-[#E6E9F0] bg-white px-6 pb-4 pt-5">
        <h2 className="font-editorial text-2xl text-[#1B2433] [overflow-wrap:anywhere]">{title}</h2>
        <button type="button" onClick={onClose} aria-label="Close" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[#667184] hover:bg-[#F7F8FB]"><X className="h-4 w-4" /></button>
      </div>
      <div data-lenis-prevent className="atelier-modal-scroll min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5 text-[13px] text-[#34445F]">{children}</div>
      {footer && <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[#E6E9F0] bg-white px-6 py-3.5">{footer}</div>}
    </div>
  </div>;
}

/** Asks before an irreversible or slow change: what it does, then Cancel or the action. */
export function ConfirmDialog({ title, children, confirm, busy = false, danger = false, onConfirm, onCancel }: {
  title: string; children: React.ReactNode; confirm: string; busy?: boolean; danger?: boolean; onConfirm: () => void; onCancel: () => void;
}) {
  return <Dialog title={title} onClose={onCancel} label={title} footer={<>
    <button type="button" className={QUIET_BUTTON} onClick={onCancel}>Cancel</button>
    <button type="button" data-autofocus className={danger ? DANGER_BUTTON : DARK_BUTTON} disabled={busy} onClick={onConfirm}>{confirm}</button>
  </>}>{children}</Dialog>;
}

/** A folded block at the bottom of a page ("Processing health"); `defaultOpen` opens it when it is first drawn. */
export function FoldPanel({ summary, children, label, onToggle, defaultOpen = false }: { summary: React.ReactNode; children: React.ReactNode; label?: string;
  onToggle?: (open: boolean) => void; defaultOpen?: boolean }) {
  return <details className={`group ${PANEL}`} aria-label={label} open={defaultOpen || undefined} onToggle={onToggle ? e => onToggle(e.currentTarget.open) : undefined}>
    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 text-[13px] font-semibold text-[#34445F] [&::-webkit-details-marker]:hidden">
      <span>{summary}</span><span aria-hidden="true" className="text-[11px] font-normal text-[#9AA3B2]"><span className="group-open:hidden">Show</span><span className="hidden group-open:inline">Hide</span></span>
    </summary>
    <div className="space-y-4 border-t border-[#EEF0F4] p-5 text-[13px] text-[#34445F]">{children}</div>
  </details>;
}

/** "26 Oct 2026". */
export function shortDay(value: string | null | undefined): string {
  if (!value) return '';
  const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00Z` : value);
  return Number.isFinite(date.getTime()) ? date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : '';
}

/** A sentence the server wrote, as a person reads it: without commands, plan codes, decision ids or "under delegation". */
export function plainReason(text: string | null | undefined): string {
  return plainMessage((text ?? '')
    .replace(/\s*\((?=[^)]*(?:\b(?!USD)[A-Z]{1,3}[. ]?[A-Z]?\d+\b|delegat|\b\d+\.[A-Z]+\d+))[^)]*\)/g, '')
    .replace(/\s*[;,]?\s*(?:decided |approved |made )?under (?:[\w’']+ )?delegation\b/gi, ''));
}
