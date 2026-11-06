import React from 'react';
import { Link } from 'react-router-dom';
import type { WeekPlanSlotV2 } from '../api/types';
import { useApiQuery } from '../api/query';
import { weekWords } from '../utils/editorialWeeks';
import { CTA_LABELS } from './packFields';
import { StateChip, button, packHref, shortDate } from './packParts';
import { EmptyState, ErrorState, LoadingState } from './shared/states';

/* A week's content packs (NP.F4; the content-packs plan, section 4.4): the proposed allocation for the publishing week (one
   Tuesday email and three Instagram pieces, one of them the week's offer post), read only, with its date, slot, piece and
   call to action; the week's checks; the week's packs; the bank of every other unpublished piece; what is marked published;
   and the week's pack document to download, as Markdown or as a Word file (NP.B12). The plan is computed by the API each
   time it is read: a piece marked published leaves it on the next read, and nothing here schedules or posts anything (D43e). */

const card = 'rounded-xl border border-[#E0DFE2] bg-white p-4 space-y-3';
const later = (weeks: number | null | undefined) => !weeks ? null : weeks === 1 ? 'next week' : `in ${weeks} weeks`;

function Slot({ slot, base }: { slot: WeekPlanSlotV2; base: string }) {
  return <li className="grid gap-2 border-t border-[#E6E9F0] py-3 first:border-t-0 md:grid-cols-[150px_130px_minmax(0,1fr)_170px] md:items-baseline" data-slot={slot.slot}>
    <p className="text-sm font-medium text-[#173354]"><time dateTime={slot.date}>{slot.weekday}, {shortDate(slot.date)}</time></p>
    <p className="text-sm text-slate-600">{slot.label}</p>
    <div className="min-w-0 text-sm">
      {slot.pack_id && slot.piece
        ? <Link className="underline" to={packHref(base, slot.pack_id, slot.piece)}>{slot.piece_label ?? slot.piece} · {slot.title ?? 'Untitled'}</Link>
        : <span className="text-slate-500">Nothing proposed</span>}
      {slot.note && <p className="text-xs text-slate-500">{slot.note}</p>}
    </div>
    <p className="text-sm text-slate-600">{slot.cta ? CTA_LABELS[slot.cta] ?? slot.cta : ''}</p>
  </li>;
}

export function PackWeek({ weekId, base }: { weekId: string; base: string }) {
  const plan = useApiQuery('/weeks/{week_id}/pack-plan', { path: { week_id: weekId } });
  const packs = useApiQuery('/packs', { query: { week_id: weekId, limit: 100 } });
  const data = plan.data;
  const published = (packs.data?.items ?? []).flatMap(p => p.pieces.filter(piece => piece.published).map(piece => ({ pack: p, piece })));
  const refresh = () => { void plan.refetch(); void packs.refetch(); };
  return <section className="space-y-5" aria-label="The week's content packs">
    <nav className="flex flex-wrap gap-4 text-sm"><Link to={base} className="underline">All content packs</Link>
      <Link to={`${base}?week=${encodeURIComponent(weekId)}`} className="underline">This week's packs in the list</Link></nav>
    <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-slate-500">Content packs · {weekWords(weekId)}</p>
        <h1 className="font-editorial text-3xl text-[#173354]">The week's plan</h1>
        {data && <p className="text-sm text-slate-600">For the publishing week of {shortDate(data.publishing_week_start)} to {shortDate(data.publishing_week_end)}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={button} onClick={refresh}>Refresh</button>
        <a className={button} href={`/api/atelier/weeks/${encodeURIComponent(weekId)}/packs.md`} download>Download the week's pack document</a>
        <a className={button} href={`/api/atelier/weeks/${encodeURIComponent(weekId)}/packs.docx`} download>Download as Word (.docx)</a>
      </div>
    </header>
    {plan.error && <ErrorState message={plan.error.message} onRetry={() => void plan.refetch()} />}
    {!data && !plan.error && <LoadingState>Loading the week's plan…</LoadingState>}
    {data && <>
      <section className={card} aria-label="Proposed for the week">
        <h2 className="font-semibold text-[#173354]">Proposed for the week</h2>
        <p className="text-xs text-slate-600">One Tuesday email and three Instagram pieces, one of them the week's offer post. The dates are suggestions, worked out each time this page is read; nothing is scheduled or posted by the system.</p>
        {data.slots.length ? <ol>{[...data.slots].sort((a, b) => a.date.localeCompare(b.date)).map(s => <Slot key={s.slot} slot={s} base={base} />)}</ol>
          : <EmptyState>No piece is proposed for this week yet.</EmptyState>}
      </section>
      {data.findings.length > 0 && <section className={card} aria-label="Week checks">
        <h2 className="font-semibold text-[#173354]">Checks across the week ({data.findings.length})</h2>
        <ul className="space-y-1 text-sm">{data.findings.map((f, i) => <li key={i} className={`rounded-lg px-3 py-2 ${f.severity === 'blocking' ? 'bg-red-50 text-red-900' : 'bg-amber-50 text-amber-900'}`}>
          {f.severity === 'blocking' ? 'To resolve: ' : 'Check: '}{f.message}</li>)}</ul>
      </section>}
      <section className={card} aria-label="This week's packs">
        <h2 className="font-semibold text-[#173354]">This week's packs ({data.packs.length})</h2>
        {data.packs.length ? <ul className="space-y-2">{data.packs.map(p => <li key={p.pack_id} className="flex flex-wrap items-center gap-2 text-sm">
          <StateChip state={p.state} /><Link className="underline" to={packHref(base, p.pack_id)}>{p.title}</Link>{p.pillar && <span className="text-slate-500">{p.pillar}</span>}</li>)}</ul>
          : <p className="text-sm text-slate-500">No content pack has been made for this week yet.</p>}
      </section>
      <section className={card} aria-label="The bank">
        <h2 className="font-semibold text-[#173354]">The bank ({data.bank.length})</h2>
        <p className="text-xs text-slate-600">Every other unpublished piece, in a suggested order for the weeks after this one.</p>
        {data.bank.length ? <ol className="space-y-2">{data.bank.map(b => <li key={`${b.pack_id}:${b.piece}`} className="text-sm">
          <Link className="underline" to={packHref(base, b.pack_id, b.piece)}>{b.piece_label} · {b.title}</Link>
          {later(b.suggested_week) && <span className="text-slate-500"> · suggested {later(b.suggested_week)}</span>}
          {b.reason && <p className="text-xs text-slate-500">{b.reason}</p>}</li>)}</ol> : <p className="text-sm text-slate-500">Nothing waits in the bank.</p>}
      </section>
      <section className={card} aria-label="Published">
        <h2 className="font-semibold text-[#173354]">Published ({published.length})</h2>
        {packs.error && <ErrorState message={packs.error.message} onRetry={() => void packs.refetch()} />}
        {published.length ? <ul className="space-y-1 text-sm">{published.map(({ pack, piece }) => <li key={`${pack.pack_id}:${piece.key}`}>
          <Link className="underline" to={packHref(base, pack.pack_id, piece.key)}>{pack.title} · {piece.label}</Link></li>)}</ul>
          : !packs.error && <p className="text-sm text-slate-500">Nothing from this week is marked published yet. Mark a piece published on its pack when it goes out.</p>}
      </section>
    </>}
  </section>;
}
