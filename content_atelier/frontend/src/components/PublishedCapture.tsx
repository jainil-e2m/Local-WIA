import React, { useState } from 'react';
import { errorMessage } from '../api/client';
import { useApiQuery, useInvalidate } from '../api/query';
import { apiPost } from '../api/routes';
import type { BriefPublished, PublishedFinal, StoredBrief } from '../api/types';
import { DARK_BUTTON, Dialog, FIELD, HEADING, LABEL, META, PANEL, QUIET_BUTTON, StatusLine } from './AdminParts';
import { Select } from './ThemedSelect';
import { DateInput } from './DateInput';

/* What WIA published from an approved brief. After the brief is approved a team member opens "Record a published piece",
   pastes the final copy, chooses its channel and publish date, and may add the link and a first figure. The server links it to the brief, keeps the difference from
   the brief's copy for the learning loop, and the next cycle's strategist reads it as already published. */

export const CAPTURE_CHANNELS = ['email', 'reel', 'carousel', 'caption', 'stories'] as const;
export type CaptureChannel = typeof CAPTURE_CHANNELS[number];
const CHANNEL_LABELS: Record<CaptureChannel, string> = { email: 'Email', reel: 'Reel', carousel: 'Carousel', caption: 'Caption', stories: 'Stories' };

export interface CaptureForm { channel: CaptureChannel | ''; piece: number; title: string; text: string; published_on: string; url: string; metric: string; value: string }
export const emptyCapture = (channel: CaptureChannel | '' = ''): CaptureForm => ({ channel, piece: 1, title: '', text: '', published_on: '', url: '', metric: '', value: '' });


/** The channels this brief planned, in the order the form offers them; every channel when it names none. */
export function briefChannels(brief: Pick<StoredBrief, 'content_body'>): CaptureChannel[] {
  const document = brief.content_body.document as { header?: { channels?: string[] } };
  const named = (document.header?.channels ?? []).filter((c): c is CaptureChannel => (CAPTURE_CHANNELS as readonly string[]).includes(c));
  return named.length ? named : [...CAPTURE_CHANNELS];
}

/** The request body, or what is missing. A figure needs both its name and its value. */
export function captureRequest(form: CaptureForm, today = new Date().toISOString().slice(0, 10)): { body: PublishedFinal } | { error: string } {
  if (!form.channel) return { error: 'Choose the channel it was published on.' };
  if (!form.title.trim() || !form.text.trim()) return { error: 'Paste the published text and give it its title.' };
  if (!/^\d{4}-\d{2}-\d{2}$/.test(form.published_on)) return { error: 'Choose the day it was published.' };
  if (form.published_on > today) return { error: 'The publish date cannot be in the future.' };
  const url = form.url.trim();
  if (url && !/^https?:\/\/\S+$/.test(url)) return { error: 'The link must start with http:// or https://.' };
  const metric = form.metric.trim(), value = form.value.trim();
  if (!!metric !== !!value) return { error: 'A figure needs both its name and its value, or leave both empty.' };
  return { body: { channel: form.channel, piece: form.channel === 'reel' ? form.piece : 1, title: form.title.trim(), text: form.text.trim(),
    published_on: form.published_on, url: url || null, metrics: metric ? [{ metric, value }] : [] } };
}

const capture = (row: BriefPublished) => (row.details?.capture ?? {}) as { url?: string | null; piece?: number };
const edit = (row: BriefPublished) => (row.details?.edit ?? null) as { before?: string; after?: string } | null;

/** One saved piece: what was published, where, and what changed from the brief. */
export function SavedPiece({ row }: { row: BriefPublished }) {
  const changed = edit(row), url = capture(row).url;
  return <li className="rounded-xl border border-[#E6E9F0] bg-white p-3 text-[13px] space-y-1">
    <p><span className="font-medium text-[#1B2433]">{row.published_on ?? 'Undated'} · {row.channel}: {row.title}</span>{row.created_by ? <span className="text-[#8B93A3]"> (recorded by {row.created_by})</span> : null}</p>
    {url && /^https?:\/\//.test(url) && <p><a className="text-[#5070FF] hover:underline" href={url} target="_blank" rel="noreferrer">Open the published piece</a></p>}
    {!!row.performance?.length && <p>{row.performance.map(p => `${p.metric}: ${p.value}`).join(' · ')}</p>}
    {changed ? <details><summary className="cursor-pointer text-[12px] text-[#5070FF]">What changed from the brief</summary>
      {changed.before && <p className="mt-1"><span className="text-[#8B93A3]">The brief said:</span> <span className="whitespace-pre-wrap">{changed.before}</span></p>}
      {changed.after && <p className="mt-1"><span className="text-[#8B93A3]">Published:</span> <span className="whitespace-pre-wrap">{changed.after}</span></p>}
    </details> : <p className="text-[#8B93A3]">No change from the brief's copy recorded.</p>}
  </li>;
}

/** The form and, unless `showSaved` is off, the pieces already recorded; the caller does the request. */
export function PublishedCaptureForm({ channels, saved, busy, error, onSubmit, showSaved = true, onCancel }: {
  channels: CaptureChannel[]; saved: BriefPublished[]; busy: boolean; error: string; onSubmit: (form: CaptureForm) => Promise<boolean>; showSaved?: boolean; onCancel?: () => void;
}) {
  const [form, setForm] = useState<CaptureForm>(() => emptyCapture(channels.length === 1 ? channels[0] : ''));
  const set = (change: Partial<CaptureForm>) => setForm({ ...form, ...change });
  const submit = async () => { if (await onSubmit(form)) setForm(emptyCapture(form.channel)); };
  return <section className="space-y-4 text-[13px]">
    <h3 className={showSaved ? HEADING : 'sr-only'}>What was published from this brief</h3>
    <p className="text-[#667184]">Paste the final copy as it went out. It is kept with this brief, and the next cycle knows it is already published.</p>
    {showSaved && saved.length > 0 && <ul className="space-y-2">{saved.map(row => <SavedPiece key={row.content_id} row={row} />)}</ul>}
    <div className="grid gap-3 md:grid-cols-3">
      <label className={LABEL}>Channel<Select className={FIELD} value={form.channel} onChange={e => set({ channel: e.target.value as CaptureChannel | '' })}>
        <option value="">Choose…</option>{channels.map(c => <option key={c} value={c}>{CHANNEL_LABELS[c]}</option>)}</Select></label>
      {form.channel === 'reel' && <label className={LABEL}>Which reel<Select className={FIELD} value={form.piece} onChange={e => set({ piece: Number(e.target.value) })}>
        {[1, 2, 3].map(n => <option key={n} value={n}>Reel {n}</option>)}</Select></label>}
      <label className={LABEL}>Published on<DateInput className={FIELD} value={form.published_on} onChange={e => set({ published_on: e.target.value })} /></label>
    </div>
    <label className={`${LABEL} block`}>Title (the subject line, the cover text or the first line)<input className={FIELD} value={form.title} onChange={e => set({ title: e.target.value })} /></label>
    <label className={`${LABEL} block`}>The published text<textarea className={FIELD} rows={8} value={form.text} onChange={e => set({ text: e.target.value })} /></label>
    <label className={`${LABEL} block`}>Link (optional)<input className={FIELD} value={form.url} placeholder="https://" onChange={e => set({ url: e.target.value })} /></label>
    <div className="grid gap-3 md:grid-cols-2">
      <label className={LABEL}>A figure (optional), for example replies<input className={FIELD} value={form.metric} onChange={e => set({ metric: e.target.value })} /></label>
      <label className={LABEL}>Its value<input className={FIELD} value={form.value} onChange={e => set({ value: e.target.value })} /></label>
    </div>
    <StatusLine tone="error">{error}</StatusLine>
    <div className="flex justify-end gap-2">
      {onCancel && <button type="button" className={QUIET_BUTTON} onClick={onCancel}>Cancel</button>}
      <button type="button" className={DARK_BUTTON} disabled={busy} onClick={() => void submit()}>{busy ? 'Saving…' : 'Record the published piece'}</button>
    </div>
  </section>;
}

/** On an approved brief, for an editor or approver: the pieces already recorded, and "Record a published piece", which opens
    the form in a dialog. */
export function PublishedCapture({ brief }: { brief: StoredBrief }) {
  const saved = useApiQuery('/briefs/{brief_id}/published', { path: { brief_id: brief.brief_id } });
  const invalidate = useInvalidate();
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [open, setOpen] = useState(false), [done, setDone] = useState('');
  const onSubmit = async (form: CaptureForm) => {
    const request = captureRequest(form);
    if ('error' in request) { setError(request.error); return false; }
    setBusy(true); setError('');
    try {
      await apiPost('/briefs/{brief_id}/published', { path: { brief_id: brief.brief_id }, body: request.body });
      await invalidate('/briefs/{brief_id}/published', '/context/published');
      setOpen(false); setDone('The published piece is recorded.');
      return true;
    } catch (e) {
      setError(errorMessage(e, 'The published piece was not recorded.'));
      return false;
    } finally { setBusy(false); }
  };
  const rows = saved.data?.items ?? [];
  return <section className={`${PANEL} p-5 space-y-3`} aria-label="What was published from this brief">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h3 className={HEADING}>What was published from this brief</h3>
      <button type="button" className={QUIET_BUTTON} onClick={() => { setDone(''); setError(''); setOpen(true); }}>Record a published piece</button>
    </div>
    <StatusLine>{done}</StatusLine>
    {saved.error && <StatusLine tone="error">{saved.error.message}</StatusLine>}
    {rows.length ? <ul className="space-y-2">{rows.map(row => <SavedPiece key={row.content_id} row={row} />)}</ul> : <p className={META}>Nothing recorded yet.</p>}
    {open && <Dialog title="Record a published piece" wide onClose={() => setOpen(false)}>
      <PublishedCaptureForm channels={briefChannels(brief)} saved={rows} showSaved={false} busy={busy} error={error} onSubmit={onSubmit} onCancel={() => setOpen(false)} />
    </Dialog>}
  </section>;
}
