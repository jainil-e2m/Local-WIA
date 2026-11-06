import React from 'react';
import { X } from 'lucide-react';
import { useModalBehavior } from '../useModalBehavior';

/* The pieces the Weekly Studio, Previous Concepts and Content Packs share, in the 20 October mockup's classes (src/mock:
   EditorialHub's cards and sections, IdeaDetailModal's dialog). The mockup's components render the built-in examples, so the
   real app cannot import them (viewRegistry.test.ts); these carry the same markup over the stored data. */

/** The mockup's card surface. */
export const CARD = 'rounded-2xl border border-[#E6E9F0] bg-white p-5 flex flex-col gap-4 shadow-[0_3px_18px_rgba(28,36,52,0.035)] [overflow-wrap:anywhere]';
/** The mockup's panel inside a card ("Topic & editorial rationale", "Content brief"). */
export const PANEL = 'rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4';
export const PANEL_HEADING = 'text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]';
export const PANEL_LIST = 'space-y-2.5 pl-4 text-[12px] leading-relaxed text-[#667184] list-disc marker:text-[#A38B61]';
/** The quiet outline button ("Review angle", "Read full brief"). */
export const QUIET = 'text-[11px] font-medium text-[#34445F] rounded-full border border-[#E6E9F0] bg-white px-3 py-2 hover:bg-[#F7F8FB] disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8DA1FD]';
/** The dark action button ("Approve & create brief"). */
export const DARK = 'flex items-center gap-1.5 text-[11px] font-medium bg-[#1B2838] text-white rounded-full px-3 py-2 hover:bg-[#34445F] disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8DA1FD]';
/** A field in an editor: its label and its input, in the panel's own type. */
export const EDIT_LABEL = 'block min-w-0 text-[11.5px] font-semibold text-[#34445F]';
export const EDIT_FIELD = 'mt-1.5 block w-full rounded-lg border border-[#E0E4EC] bg-white px-3 py-2 text-[12.5px] font-normal leading-relaxed text-[#34445F] focus:outline-none focus:border-[#8DA1FD]';
/** A text area's height for its text, so a long field opens whole. */
export const rowsFor = (text: string | null | undefined, least = 2) =>
  Math.min(16, Math.max(least, (text ?? '').split('\n').reduce((rows, line) => rows + Math.max(1, Math.ceil(line.length / 88)), 0)));
/** A text link in the mockup's blue. */
export const LINK = 'text-[12px] font-medium text-[#5070FF] hover:underline';

export type PillTone = 'waiting' | 'approved' | 'quiet' | 'alert' | 'progress';
const TONES: Record<PillTone, string> = {
  waiting: 'bg-[#FFF8E9] text-[#947021]', approved: 'bg-emerald-50 text-emerald-700', quiet: 'bg-[#F1F3F7] text-[#667184]',
  alert: 'bg-red-50 text-red-800', progress: 'bg-[#EFF3FF] text-[#5070FF]',
};
export function Pill({ tone, children }: { tone: PillTone; children: React.ReactNode }) {
  return <span className={`shrink-0 text-[10px] rounded-full px-2.5 py-1 font-medium ${TONES[tone]}`}>{children}</span>;
}

/** A section of a stage ("Awaiting approval", "Approved"): its serif heading, its count and one line on what it holds. */
export function StageSection({ title, count, description, label, children, id }: { title: string; count: number; description: string; label: string; children: React.ReactNode; id?: string }) {
  return <section aria-label={label} id={id}>
    <div className="mb-4 flex items-center gap-3"><h2 className="font-editorial text-2xl text-[#1B2433]">{title}</h2>
      <span className="bg-white rounded-full border border-[#E6E9F0] px-2.5 py-1 text-[10px] text-[#8B93A3]">{count}</span></div>
    <p className="text-[12px] text-[#8B93A3] mb-4">{description}</p>
    {children}
  </section>;
}

/** The two-column grid of cards (one column below 1280 px). */
export function CardGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">{children}</div>;
}

export function EmptyStage({ children }: { children: React.ReactNode }) {
  return <div role="status" className="rounded-2xl border border-dashed border-[#DCE1EA] py-8 px-4 text-center text-[12px] text-[#8B93A3]">{children}</div>;
}

/** A folded group under the grid ("Held, skipped and other ideas", "Why these ideas", "Cycle details"). */
export function Fold({ summary, children, label, open, onToggle }: { summary: React.ReactNode; children: React.ReactNode; label?: string; open?: boolean;
  onToggle?: (open: boolean) => void }) {
  return <details className="group rounded-2xl border border-[#E6E9F0] bg-white" aria-label={label} open={open} onToggle={onToggle ? e => onToggle(e.currentTarget.open) : undefined}>
    <summary className="cursor-pointer list-none flex items-center justify-between gap-3 px-5 py-4 text-[13px] font-semibold text-[#34445F] [&::-webkit-details-marker]:hidden">
      <span>{summary}</span><span aria-hidden="true" className="text-[#9AA3B2] text-[11px] font-normal"><span className="group-open:hidden">Show</span><span className="hidden group-open:inline">Hide</span></span></summary>
    <div className="border-t border-[#EEF0F4] p-5 space-y-4 text-[13px] text-[#34445F]">{children}</div>
  </details>;
}

/** A decision's author as a person reads it: a name, never an address or a delegation code. */
export const personName = (author: string | null | undefined) => {
  const name = (author ?? '').replace(/\s*\([^)]*\)/g, '').trim();
  return name.includes('@') ? '' : name;
};
/** A date as the mockup writes it on a card: "20 Oct 2026". */
export function cardDay(value: string | null | undefined): string {
  if (!value) return '';
  const date = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
  return Number.isFinite(date.getTime()) ? date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : '';
}

/* WIA's offers, as the mockup's filter names them. A card's or brief's offer is free text ("ELEVATE, our full-service
   advertising management program"), so it is matched by the offer's name. */
export const OFFER_FILTERS = [
  { value: 'elevate', label: 'Elevate', pattern: /elevate/i },
  { value: 'accelerators', label: 'Accelerators', pattern: /accelerator/i },
  { value: 'leadlock', label: 'LeadLock', pattern: /lead\s?lock/i },
] as const;
export type OfferFilter = 'all' | typeof OFFER_FILTERS[number]['value'];

/** The offer's short name for a card's date line, or '' when no offer is named. */
export function offerName(text: string | null | undefined): string {
  if (!text) return '';
  const known = OFFER_FILTERS.filter(o => o.pattern.test(text)).map(o => o.label);
  if (known.length) return known.join(' & ');
  return '';
}

/** Whether free text matches the offer filter and the search words. */
export function matches(text: string, offerText: string, query: string, offer: OfferFilter): boolean {
  if (offer !== 'all' && !OFFER_FILTERS.find(o => o.value === offer)?.pattern.test(offerText)) return false;
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const haystack = text.toLowerCase();
  return words.every(word => haystack.includes(word));
}

/** Sentences of a paragraph, for the mockup's bulleted guardrails; a single sentence stays one line. */
export function sentences(text: string): string[] {
  return text.split(/(?<=[.!?])\s+(?=[A-Z“"(])/).map(s => s.trim()).filter(Boolean);
}

export interface ModalTab { id: string; label: string; selected?: boolean; disabled?: boolean; title?: string; onSelect?: () => void }

/** The mockup's detail dialog (IdeaDetailModal): the serif title and a close button, the stage tabs, a scrolling body and the
    bottom bar. It is rendered in place (not in a portal), so a deep link renders it on the server as well. Escape closes it,
    focus stays inside it and returns where it was (useModalBehavior). */
export function StudioModal({ title, tabs, footerNote, footer, onClose, children, label }: {
  title: string; tabs?: ModalTab[]; footerNote?: React.ReactNode; footer?: React.ReactNode; onClose: () => void; children: React.ReactNode; label?: string;
}) {
  const modalRef = useModalBehavior(onClose);
  return <div data-lenis-prevent className="atelier-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6">
    <div ref={modalRef} role="dialog" aria-modal="true" aria-label={label ?? title} tabIndex={-1} onClick={e => e.stopPropagation()}
      className="atelier-modal bg-[#FAF9F7] w-full max-w-5xl h-[92dvh] max-h-[92dvh] rounded-2xl border border-[#E0DFE2] shadow-saas-dropdown flex flex-col overflow-hidden text-[#221E17]">
      <div className="px-6 pt-5 pb-4 bg-white border-b border-[#E0DFE2] space-y-3">
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-editorial text-2xl sm:text-3xl font-bold tracking-tight text-[#221E17] [overflow-wrap:anywhere]">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="w-8 h-8 shrink-0 flex items-center justify-center text-[#667184] hover:bg-[#F7F8FB] rounded-full"><X className="w-4 h-4" /></button>
        </div>
        {tabs && <nav aria-label="Content stages" className="atelier-modal-tabs flex items-center gap-1 p-1 rounded-full border border-[#E6E9F0] bg-[#F7F8FB] text-xs">
          {tabs.map(tab => <button key={tab.id} type="button" aria-pressed={!!tab.selected} disabled={tab.disabled} title={tab.title} onClick={tab.onSelect}
            className={`px-4 py-2 rounded-full font-medium disabled:opacity-40 disabled:cursor-not-allowed ${tab.selected ? 'bg-white text-[#5070FF] font-semibold' : 'text-[#667184]'}`}>{tab.label}</button>)}
        </nav>}
      </div>
      <div data-lenis-prevent className="atelier-modal-scroll min-h-0 flex-1 overflow-y-auto [scrollbar-gutter:stable] p-6 space-y-6">{children}</div>
      <div className="px-6 py-3.5 bg-white border-t border-[#E0DFE2] flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="text-[#87725F]">{footerNote}</div>
        <div className="flex flex-wrap justify-end items-center gap-2">{footer}
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-full border border-[#E6E9F0] text-[#667184] font-medium">Done</button></div>
      </div>
    </div>
  </div>;
}

/** An editor's bar, held at the foot of the dialog: how much has changed, and save or cancel. */
export function EditBar({ count, error, busy, onCancel, onSave, saveLabel }: { count: number; error?: string; busy: boolean; onCancel?: () => void; onSave: () => void; saveLabel: string }) {
  return <div className="sticky -bottom-6 z-10 rounded-xl border border-[#E6E9F0] bg-white px-4 py-3 shadow-[0_-4px_18px_rgba(28,36,52,0.06)] space-y-2">
    {error && <p role="alert" className="text-[12px] text-red-800">{error}</p>}
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-[11px] text-[#7A8496]">{count ? `${count} ${count === 1 ? 'change' : 'changes'} to save` : 'Nothing changed yet'}</p>
      <div className="flex items-center gap-2">
        {onCancel && <button type="button" className={QUIET} disabled={busy} onClick={onCancel}>Cancel</button>}
        <button type="button" className={DARK} disabled={busy} onClick={onSave}>{busy ? 'Saving…' : saveLabel}</button></div>
    </div>
  </div>;
}

/** A numbered stage panel inside the dialog ("1 Content Angle"), as the mockup's. */
export function StagePanel({ step, title, status, children }: { step: number; title: string; status?: React.ReactNode; children: React.ReactNode }) {
  return <section className="bg-white p-5 rounded-xl border border-[#E0DFE2] shadow-saas-card space-y-4 [overflow-wrap:anywhere]">
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2.5">
        <span className="w-6 h-6 rounded-md bg-[#EFF3FF] text-[#5070FF] text-xs font-bold flex items-center justify-center border border-[#D1DBFF]">{step}</span>
        <h3 className="font-editorial text-lg font-bold text-[#221E17]">{title}</h3>
      </div>
      {status && <span className="text-xs font-bold">{status}</span>}
    </div>
    {children}
  </section>;
}
