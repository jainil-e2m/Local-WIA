import React, { useEffect, useState } from 'react';
import { X, Sparkles } from 'lucide-react';
import { useModalBehavior } from './useModalBehavior';
import type { Seed } from '../api/schema';
import { useApiQuery, useInvalidate } from '../api/query';
import { storageRequest } from '../utils/weeklyStorage';
import { ActionError, ConflictNotice, useGuardedAction } from './shared/conflict';
import { ErrorState } from './shared/states';
import { useDocuments } from '../api/documents';
import { Select } from './ThemedSelect';

/* Founder seeds (E.F3, on E.B19's API): a thought, a draft or a published asset, with an optional target offer,
   that the next cycle's strategist pairs with call evidence or flags as having none. Layout from FlagIdeaModal.
   A founder note (L.B13, D29) is one line on what stood out in one call: it names the call, and the cycle pairs it with that
   call's scenes or shows it as unanswered in the week's review document. */

export type { Seed };
export interface SeedForm { kind: Seed['kind']; text: string; target_offer: string; source_url: string; author: string; always_true: boolean; transcript_id?: string }
export const OFFERS = ['', 'ELEVATE', 'Ads Accelerators', 'LeadLock'];
const KIND_HELP: Record<Seed['kind'], string> = {
  thought: 'An idea in your own words.', draft: 'Copy you have started.', asset: 'Something already published; add its link.',
  founder_note: 'One line on what stood out to you in one call: "What stood out to me was ...".',
};
const KIND_LABEL: Record<Seed['kind'], string> = { thought: 'Thought', draft: 'Draft', asset: 'Asset', founder_note: 'Founder note' };
export const NOTE_CHARACTERS = 600;

/** The request body, or what is still missing (the API's own rules). */
export function seedRequest(f: SeedForm): { body: Record<string, unknown> } | { error: string } {
  const text = f.text.trim();
  if (f.kind === 'founder_note') {
    if (!text) return { error: 'Write what stood out to you.' };
    if (text.length > NOTE_CHARACTERS) return { error: `Keep the note to one line (under ${NOTE_CHARACTERS} characters).` };
    if (!f.transcript_id) return { error: 'Choose the call the note is about.' };
    return { body: { kind: 'founder_note', text, transcript_id: f.transcript_id, author: f.author.trim() || null } };
  }
  if (!text) return { error: 'Write the seed.' };
  if (text.length > 8000) return { error: 'Keep the seed under 8,000 characters.' };
  const link = f.source_url.trim();
  if (f.kind === 'asset' && !link) return { error: 'Add the link to the published asset.' };
  if (link && !/^https?:\/\//i.test(link)) return { error: 'The link must start with http:// or https://.' };
  return { body: { kind: f.kind, text, target_offer: f.target_offer || null, source_url: link || null, author: f.author.trim() || null, always_true: f.always_true } };
}

export function SeedCaptureModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const modalRef = useModalBehavior(onClose);
  const [form, setForm] = useState<SeedForm>({ kind: 'thought', text: '', target_offer: '', source_url: '', author: '', always_true: false });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = seedRequest(form);
    if ('error' in result) { setError(result.error); return; }
    setBusy(true); setError('');
    try { await storageRequest('/seeds', 'POST', result.body); onSaved(); onClose(); }
    catch (err) { setError(err instanceof Error ? err.message : 'The seed could not be saved.'); }
    finally { setBusy(false); }
  };
  const field = 'w-full rounded-xl border border-[#E0DFE2] bg-white p-3 text-sm';
  return <div data-lenis-prevent className="atelier-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4">
    <div ref={modalRef} role="dialog" aria-modal="true" aria-label="Add a seed" tabIndex={-1} onClick={e => e.stopPropagation()}
      className="atelier-modal bg-[#FAF9F7] w-full max-w-lg max-h-[92dvh] flex flex-col rounded-2xl border border-[#E0DFE2] shadow-saas-dropdown overflow-hidden text-[#221E17]">
      <div className="px-6 py-4 border-b border-[#E0DFE2] bg-white flex items-center justify-between">
        <div className="flex items-center gap-2"><Sparkles strokeWidth={1.5} className="w-4 h-4 text-[#5070FF]" /><h3 className="font-editorial text-xl font-bold">Flag an idea</h3></div>
        <button onClick={onClose} aria-label="Close Add a seed" className="w-8 h-8 rounded-lg hover:bg-[#FAF9F7] border border-transparent hover:border-[#E0DFE2] flex items-center justify-center text-[#4B4137]"><X strokeWidth={1.5} className="w-4 h-4" /></button>
      </div>
      <form data-lenis-prevent onSubmit={e => void submit(e)} className="atelier-modal-scroll min-h-0 flex-1 overflow-y-auto p-6 space-y-4 text-xs">
        <p className="text-[#4B4137] leading-relaxed">It goes into next week's ideas, matched with what was said on the calls.</p>
        <fieldset className="space-y-1"><legend className="font-semibold block">What is it?</legend>
          <div className="flex flex-wrap gap-2">{(['thought', 'draft', 'asset', 'founder_note'] as const).map(k => <label key={k} className="flex items-center gap-1 rounded-lg border border-[#E0DFE2] bg-white px-3 py-2">
            <input type="radio" name="seed-kind" checked={form.kind === k} onChange={() => setForm({ ...form, kind: k })} />{KIND_LABEL[k]}</label>)}</div>
          <p className="text-[#4B4137]">{KIND_HELP[form.kind]}</p></fieldset>
        {form.kind === 'founder_note' && <CallPicker value={form.transcript_id ?? ''} onChange={id => setForm({ ...form, transcript_id: id })} className={field} />}
        <label className="space-y-1 block"><span className="font-semibold block">{form.kind === 'founder_note' ? 'What stood out *' : 'Your idea *'}</span>
          <textarea required rows={form.kind === 'founder_note' ? 2 : 5} value={form.text} onChange={e => setForm({ ...form, text: e.target.value })} className={field} /></label>
        {form.kind !== 'founder_note' && <>
        <label className="space-y-1 block"><span className="font-semibold block">Target offer (optional)</span>
          <Select value={form.target_offer} onChange={e => setForm({ ...form, target_offer: e.target.value })} className={field}>{OFFERS.map(o => <option key={o} value={o}>{o || 'No particular offer'}</option>)}</Select></label>
        <label className="space-y-1 block"><span className="font-semibold block">Link{form.kind === 'asset' ? ' *' : ' (optional)'}</span>
          <input type="url" value={form.source_url} onChange={e => setForm({ ...form, source_url: e.target.value })} className={field} /></label>
        <label className="flex gap-2 items-center"><input type="checkbox" checked={form.always_true} onChange={e => setForm({ ...form, always_true: e.target.checked })} />Use it every week, not just next week</label>
        </>}
        {error && <p role="alert" className="text-red-800">{error}</p>}
        <button disabled={busy} className="rounded-full bg-[#1B2838] text-white px-5 py-2 text-[12px] font-medium disabled:opacity-40">Flag idea</button>
      </form>
    </div>
  </div>;
}

export function SeedList({ seeds, busy, onWithdraw }: { seeds: Seed[]; busy: boolean; onWithdraw?: (id: string) => void }) {
  if (!seeds.length) return <p className="text-sm text-slate-600">No open seeds. The next cycle uses the calls alone.</p>;
  return <ul className="space-y-2">{seeds.map(s => <li key={s.seed_id} className="rounded-lg border bg-white p-3 text-sm">
    <p><strong>{KIND_LABEL[s.kind]}</strong> from {s.author}{s.target_offer ? ` · for ${s.target_offer}` : ''}{s.always_true ? ' · every cycle' : ''}{s.transcript_id ? ' · about one call' : ''}</p>
    <p className="whitespace-pre-wrap mt-1">{s.text}</p>
    {s.source_url && /^https?:\/\//i.test(s.source_url) && <a className="underline" href={s.source_url} target="_blank" rel="noreferrer">Open the asset</a>}
    {onWithdraw && <button className="mt-2 rounded-lg border border-[#C4CBD7] px-3 py-1 disabled:opacity-40" disabled={busy} onClick={() => onWithdraw(s.seed_id)}>Withdraw</button>}
  </li>)}</ul>;
}

/** The calls of the last three weeks, newest first, to say which one a founder note is about. */
function CallPicker({ value, onChange, className }: { value: string; onChange: (id: string) => void; className: string }) {
  const [since] = useState(() => new Date(Date.now() - 21 * 86_400_000).toISOString().replace(/\.\d{3}Z$/, 'Z'));
  const calls = useDocuments({ included: true, from: since, limit: 100 });
  const rows = calls.data?.items ?? [];
  return <label className="space-y-1 block"><span className="font-semibold block">The call *</span>
    {calls.error && <span role="alert" className="block text-red-800">The calls could not be loaded: {calls.error.message}</span>}
    <Select required value={value} onChange={e => onChange(e.target.value)} className={className}>
      <option value="">Choose the call…</option>
      {rows.map(d => <option key={d.transcript_id} value={d.transcript_id}>{d.occurred_at ? `${d.occurred_at.slice(0, 10)} · ` : ''}{d.title}</option>)}
    </Select></label>;
}

/** Open seeds, with add and withdraw for a person who may make them (the editor role; the server checks it again). */
export function SeedsPanel({ canEdit = true }: { canEdit?: boolean }) {
  const seeds = useApiQuery('/seeds', { query: { status: 'open' } });
  const invalidate = useInvalidate();
  const [open, setOpen] = useState(false);
  const guard = useGuardedAction(() => seeds.refetch());
  const withdraw = (id: string) => guard.run(async () => {
    await storageRequest(`/seeds/${id}/withdraw`, 'POST', {});
    await invalidate('/seeds');
  });
  const rows = seeds.data ?? [];
  return <details className="rounded-xl bg-white border p-4"><summary className="font-medium">Seeds for the next cycle ({rows.length})</summary>
    <div className="mt-3 space-y-3">
      {seeds.error && <ErrorState message={seeds.error.message} onRetry={() => void seeds.refetch()} />}
      <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
      <ActionError message={guard.error} />
      {canEdit && <button className="rounded-lg border border-[#C4CBD7] px-3 py-2 text-sm" onClick={() => setOpen(true)}>Add a seed</button>}
      <SeedList seeds={rows} busy={guard.busy} onWithdraw={canEdit ? id => void withdraw(id) : undefined} /></div>
    {open && canEdit && <SeedCaptureModal onClose={() => setOpen(false)} onSaved={() => void invalidate('/seeds')} />}
  </details>;
}
