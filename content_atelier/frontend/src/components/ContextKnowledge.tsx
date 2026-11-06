import React, { useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AlertTriangle, CalendarClock, Lock, Plus, X } from 'lucide-react';
import type { ContextItem, EntryBody, ItemHistory, ItemKind, KnownItems, Permission, PublishedPiece, StaleWarning, Visibility } from '../api/types';
import { useApiQuery, useInvalidate } from '../api/query';
import { storageRequest } from '../utils/weeklyStorage';
import { KIND_ORDER, PERMISSION_LABELS, STATUS_LABELS, VISIBILITY_LABELS, authorLabel, contextError, contextFailure, formatDate, kindLabel,
  sourceInWords, todayIso, validityLabel } from '../utils/context';
import { paths } from '../app/routes';
import { ConflictNotice, useGuardedAction } from './shared/conflict';
import { LoadingState } from './shared/states';
import { useModalBehavior } from './useModalBehavior';
import { PageHeading } from './PageHeading';
import { DARK_BUTTON, Dialog, FIELD, FilterSelect, HEADER_PRIMARY, HEADER_QUIET, LABEL, META, PANEL, QUIET_BUTTON, SELECT, StatusLine, TEXT_BUTTON, plainReason } from './AdminParts';
import { Select } from './ThemedSelect';
import { DateInput } from './DateInput';

/* Knowledge → What the system knows: the confirmed entries in use on a date, grouped by kind, each with its text and one
   quiet line (in use from, public or internal); where an entry came from and who decided it are in its History. "Add a
   fact", "Record a published piece", "Add a figure", "Link to a brief" and "Import figures" open dialogs. Changing an entry
   sends its key and the date the change takes effect, so the new version is used from that date. */

export const EDITABLE_KINDS = ['offer', 'price', 'roster_member', 'cta', 'result'] as const;
export type EditableKind = typeof EDITABLE_KINDS[number];
type FieldSpec = { name: string; label: string; required?: boolean; long?: boolean; options?: [string, string][] };

export const FACT_FIELDS: Record<EditableKind, FieldSpec[]> = {
  offer: [{ name: 'name', label: 'Offer name', required: true }, { name: 'description', label: 'What it is', required: true, long: true },
    { name: 'state', label: 'Is it current?', options: [['current', 'Current'], ['retired', 'Retired name (never present it as current)']] },
    { name: 'access', label: 'How a buyer gets to it' }, { name: 'ownership', label: 'Who does what' }],
  price: [{ name: 'offer', label: 'Offer', required: true }, { name: 'amount', label: 'Price', required: true }, { name: 'terms', label: 'Terms (optional)', long: true }],
  roster_member: [{ name: 'name', label: 'Name', required: true }, { name: 'role', label: 'Role', required: true },
    { name: 'state', label: 'With WIA?', required: true, options: [['current', 'Current team member'], ['former', 'Former team member'], ['outside', 'Outside partner']] },
    { name: 'left_on', label: 'Left on (if former)' }],
  cta: [{ name: 'wording', label: 'The wording', required: true, long: true },
    { name: 'cta_type', label: 'Kind of ask', required: true, options: [['dm_keyword', 'DM a keyword'], ['reply', 'Reply'], ['waitlist', 'Join the waitlist'], ['apply', 'Apply'],
      ['register', 'Register'], ['link', 'Follow a link'], ['podcast', 'Listen to the podcast'], ['none', 'No explicit ask'], ['other', 'Other']] },
    { name: 'used_for', label: 'Used for (optional)' }, { name: 'channel', label: 'Channel (optional)' }, { name: 'offer', label: 'Offer (optional)' }],
  result: [{ name: 'claim', label: 'The result', required: true, long: true }, { name: 'client_type', label: 'Kind of client (optional)' },
    { name: 'offer', label: 'Offer (optional)' }, { name: 'first_published', label: 'First published (optional)' }],
};

export interface FactForm {
  kind: EditableKind; changing: string; fields: Record<string, string>; visibility: Visibility; client_private: boolean;
  permission: Permission | ''; valid_from: string; valid_to: string; reason: string; author: string;
}

export function emptyFact(kind: EditableKind): FactForm {
  const fields = Object.fromEntries(FACT_FIELDS[kind].map(f => [f.name, f.options && f.required ? f.options[0][0] : f.name === 'state' ? 'current' : '']));
  return { kind, changing: '', fields, visibility: kind === 'price' ? 'internal' : 'public', client_private: false, permission: '',
    valid_from: '', valid_to: '', reason: '', author: '' };
}

/** The form for changing an existing entry: its current values, taking effect from today unless another date is chosen. */
export function factFromItem(item: ContextItem, today = todayIso()): FactForm {
  const kind = item.kind as EditableKind;
  const base = emptyFact(kind);
  const fields = Object.fromEntries(FACT_FIELDS[kind].map(f => [f.name, typeof item.body[f.name] === 'string' ? item.body[f.name] as string : base.fields[f.name]]));
  return { ...base, changing: item.item_id, fields, visibility: item.visibility, client_private: item.sensitivity === 'client_private',
    permission: item.permission || '', valid_from: today, valid_to: '' };
}

/** The approver entry for POST /context/items, or what is still missing. */
export function entryRequest(f: FactForm, existing?: ContextItem | null): { body: EntryBody } | { error: string } {
  const specs = FACT_FIELDS[f.kind];
  const body: Record<string, unknown> = existing ? { ...existing.body } : {};
  for (const spec of specs) {
    const value = (f.fields[spec.name] || '').trim();
    if (spec.required && !value) return { error: `Fill in "${spec.label}".` };
    if (value) body[spec.name] = value; else delete body[spec.name];
  }
  if (f.kind === 'price' && !/\d/.test(String(body.amount))) return { error: 'A price needs a figure, such as $297.' };
  if (f.kind === 'result' && !f.permission) return { error: 'Say what permission WIA has for this result.' };
  if (f.client_private && f.visibility !== 'internal') return { error: 'A client-private result must be internal.' };
  if (f.valid_from && f.valid_to && f.valid_to < f.valid_from) return { error: 'The end date must be after the start date.' };
  if (existing && !f.valid_from) return { error: 'Choose the date the change takes effect.' };
  if (!f.reason.trim()) return { error: 'Write a reason. It is kept with the entry.' };
  const names: Record<EditableKind, unknown> = { offer: body.name, price: body.offer, roster_member: body.name, cta: body.used_for || body.wording, result: body.claim };
  const entry: EntryBody = {
    kind: f.kind, body, visibility: f.visibility, sensitivity: f.client_private ? 'client_private' : 'none', reason: f.reason.trim(),
    ...(existing ? { key: existing.key } : { name: String(names[f.kind]).slice(0, 80) }),
    ...(f.kind === 'result' && f.permission ? { permission: f.permission } : {}),
    ...(f.valid_from ? { valid_from: f.valid_from } : {}), ...(f.valid_to ? { valid_to: f.valid_to } : {}),
    ...(f.author.trim() ? { author: f.author.trim() } : {}),
  };
  return { body: entry };
}

export function knownPath(kind: string, on: string): string {
  const query = new URLSearchParams({ ...(kind ? { kind } : {}), ...(on ? { on } : {}) }).toString();
  return `/context/items${query ? `?${query}` : ''}`;
}

export function groupByKind(items: ContextItem[]): { kind: ItemKind; items: ContextItem[] }[] {
  return KIND_ORDER.map(kind => ({ kind, items: items.filter(i => i.kind === kind) })).filter(g => g.items.length);
}

const HISTORY_ACTIONS: Record<string, string> = {
  context_accept: 'Accepted', context_edit: 'Edited and accepted', context_reject: 'Rejected', context_enter: 'Entered by an approver',
  context_retire: 'Retired when its end date passed',
};
export const historyAction = (action: string) => HISTORY_ACTIONS[action] || action.replace(/^context_/, '').replaceAll('_', ' ');

// Performance entry (L.B7, 3.B10).
export interface PieceForm { published_on: string; channel: string; title: string; text: string; brief_id: string }
export function pieceRequest(f: PieceForm): { body: Record<string, string> } | { error: string } {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(f.published_on)) return { error: 'Choose the date it was published.' };
  if (!f.channel.trim()) return { error: 'Say where it was published.' };
  if (!f.title.trim()) return { error: 'Give the piece its title or first line.' };
  return { body: { published_on: f.published_on, channel: f.channel.trim(), title: f.title.trim(), ...(f.text.trim() ? { text: f.text.trim() } : {}), ...(f.brief_id ? { brief_id: f.brief_id } : {}) } };
}
export interface MetricForm { content_id: string; on: string; metric: string; value: string; direction: '' | 'positive' | 'negative' }
export function metricRequest(f: MetricForm): { path: string; body: Record<string, string> } | { error: string } {
  if (!f.content_id) return { error: 'Choose the piece.' };
  if (!/^\d{4}-\d{2}-\d{2}$/.test(f.on)) return { error: 'Choose the date of the figure.' };
  if (!f.metric.trim() || !f.value.trim()) return { error: 'Name the measure and its figure.' };
  return { path: `/context/published/${f.content_id}/performance`, body: { on: f.on, metric: f.metric.trim(), value: f.value.trim(), ...(f.direction ? { direction: f.direction } : {}) } };
}
export function linkRequest(contentId: string, briefId: string): { path: string; body: { brief_id: string } } | { error: string } {
  if (!contentId || !briefId) return { error: 'Choose the piece and the approved brief behind it.' };
  return { path: `/context/published/${contentId}/link`, body: { brief_id: briefId } };
}
export const CSV_COLUMNS = ['date', 'channel', 'piece', 'metric', 'value'];
export function csvRequest(csv: string): { body: { csv: string } } | { error: string } {
  const text = csv.replace(/^﻿/, '').trim();
  if (!text) return { error: 'Choose a CSV file or paste its contents.' };
  if (text.length > 60000) return { error: 'The file is too large; split it into smaller files.' };
  const header = text.split(/\r?\n/)[0].split(',').map(c => c.trim().toLowerCase());
  const missing = CSV_COLUMNS.filter(c => !header.includes(c));
  if (missing.length) return { error: `The first row must name the columns ${CSV_COLUMNS.join(', ')} (missing: ${missing.join(', ')}).` };
  return { body: { csv: text } };
}
export const pieceLabel = (p: PublishedPiece) => [p.title || 'Untitled piece', p.channel, formatDate(p.published_on)].filter(Boolean).join(' · ');
export interface BriefOption { brief_id: string; title: string }
export function briefOptions(rows: { brief_id: string; content_body?: { document?: unknown } }[]): BriefOption[] {
  return rows.map(b => {
    const document = b.content_body?.document as { title?: string; header?: { title?: string } } | undefined;
    return { brief_id: b.brief_id, title: document?.title || document?.header?.title || 'Untitled brief' };
  });
}
export const figureLabel = (p: { metric: string; value: string; date: string; direction?: string | null }) =>
  `${p.metric}: ${p.value}${p.direction === 'positive' ? ' (did well)' : p.direction === 'negative' ? ' (did poorly)' : ''}, ${formatDate(p.date)}`;

const GROUP_SHOWN = 8;

/** An entry's text on the list: its source references in brackets are left to its History. */
export const entryText = (text: string) => plainReason(text.replace(/\s*\((?:source|sources):[^)]*\)/gi, ''));

export function WarningsList({ warnings }: { warnings: StaleWarning[] }) {
  if (!warnings.length) return null;
  return <div role="status" className="rounded-2xl bg-[#FFF8E9] p-4 text-[13px] text-[#947021] space-y-1">
    <p className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" strokeWidth={1.75} />Due for a review</p>
    <ul className="ml-6 list-disc">{warnings.map((w, i) => <li key={i}>{w.message}{w.since ? ` (since ${formatDate(w.since)})` : ''}</li>)}</ul>
  </div>;
}

/** One quiet line under an entry: when it is in use and who may see it. */
export function itemLine(item: Pick<ContextItem, 'valid_from' | 'valid_to' | 'visibility'>, scheduled = false): string {
  const when = scheduled ? `Starts ${formatDate(item.valid_from)}` : validityLabel(item.valid_from, item.valid_to);
  return `${when} · ${item.visibility === 'internal' ? 'Internal' : 'Public'}`;
}

function ItemRow({ item, onHistory, onChange, scheduled }: { item: ContextItem; onHistory: (item: ContextItem) => void; onChange?: (item: ContextItem) => void; scheduled?: boolean }) {
  return <li className="group flex items-start justify-between gap-4 py-3">
    <div className="min-w-0 space-y-1">
      <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-[#1B2433] line-clamp-3">{entryText(item.text)}</p>
      <p className={`${META} flex items-center gap-1`}>{item.visibility === 'internal' && <Lock aria-hidden="true" className="h-3 w-3" strokeWidth={1.75} />}{itemLine(item, scheduled)}</p>
    </div>
    <div className="flex shrink-0 items-center gap-3 opacity-70 group-hover:opacity-100">
      {onChange && <button type="button" className={TEXT_BUTTON} onClick={() => onChange(item)}>Change</button>}
      <button type="button" className={TEXT_BUTTON} onClick={() => onHistory(item)}>History</button>
    </div>
  </li>;
}

/** One kind of fact, folded to its name and count when the page lists every kind (so the list stays a page long), and open
    when it is the only kind shown. */
function KindGroup({ kind, items, onHistory, onChange, startOpen = false }: { kind: ItemKind; items: ContextItem[]; onHistory: (item: ContextItem) => void;
  onChange?: (item: ContextItem) => void; startOpen?: boolean }) {
  const [all, setAll] = useState(false);
  const shown = all ? items : items.slice(0, GROUP_SHOWN);
  const editable = (EDITABLE_KINDS as readonly string[]).includes(kind);
  return <details open={startOpen} className={`group/kind ${PANEL} px-5`} aria-label={kindLabel(kind, true)}>
    <summary className="flex cursor-pointer list-none items-center gap-3 py-4 [&::-webkit-details-marker]:hidden">
      <h3 className="font-editorial text-xl text-[#1B2433]">{kindLabel(kind, true)}</h3>
      <span className="rounded-full border border-[#E6E9F0] bg-white px-2.5 py-0.5 text-[10px] text-[#8B93A3]">{items.length}</span>
      <span aria-hidden="true" className="ml-auto text-[11px] text-[#9AA3B2]"><span className="group-open/kind:hidden">Show</span><span className="hidden group-open/kind:inline">Hide</span></span>
    </summary>
    <ul className="divide-y divide-[#EEF0F4] border-t border-[#EEF0F4]">{shown.map(i => <ItemRow key={i.item_id} item={i} onHistory={onHistory} onChange={editable ? onChange : undefined} />)}</ul>
    {items.length > GROUP_SHOWN && <button type="button" className={`${TEXT_BUTTON} mb-3`} onClick={() => setAll(!all)}>{all ? 'Show fewer' : `Show all ${items.length}`}</button>}
  </details>;
}

export function KnownList({ known, onHistory, onChange }: { known: KnownItems; onHistory: (item: ContextItem) => void; onChange?: (item: ContextItem) => void }) {
  return <div className="space-y-4">
    {!known.items.length && <p className={`${PANEL} p-5 text-[13px]`}>Nothing confirmed is in use on this date.</p>}
    {(() => { const groups = groupByKind(known.items); return groups.map(g => <KindGroup key={g.kind} kind={g.kind} items={g.items} onHistory={onHistory} onChange={onChange} startOpen={groups.length === 1} />); })()}
    {known.scheduled.length > 0 && <section className={`${PANEL} px-5 pt-4 pb-2`} aria-label="Coming up">
      <h3 className="flex items-center gap-2 font-editorial text-xl text-[#1B2433]"><CalendarClock className="h-5 w-5 text-[#5070FF]" strokeWidth={1.5} />Coming up</h3>
      <p className={META}>New versions that runs start using on a later date.</p>
      <ul className="divide-y divide-[#EEF0F4]">{known.scheduled.map(i => <ItemRow key={i.item_id} item={i} onHistory={onHistory} scheduled />)}</ul>
    </section>}
  </div>;
}

export function HistoryDrawer({ history, onClose }: { history: ItemHistory | null; onClose: () => void }) {
  // A modal dialog: focus moves in and stays in, Escape closes it, and focus goes back to the History button.
  const dialog = useModalBehavior(onClose);
  return <div className="atelier-modal-overlay fixed inset-0 z-50 flex justify-end" onClick={onClose}>
    <aside ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-label="History" className="h-full w-full max-w-lg space-y-5 overflow-y-auto border-l border-[#E6E9F0] bg-[#F6F7FB] p-6 text-[#1B2433]" onClick={e => e.stopPropagation()}>
      <div className="flex items-center justify-between"><h3 className="font-editorial text-2xl">History</h3>
        <button type="button" aria-label="Close history" className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-white" onClick={onClose}><X className="h-4 w-4" strokeWidth={1.5} /></button></div>
      {!history ? <p className="text-[13px]">Loading…</p> : <>
        <section className="space-y-2"><h4 className="text-[13px] font-semibold">Versions ({history.versions.length})</h4>
          <ol className="space-y-2 text-[13px]">{history.versions.map(v => <li key={v.item_id} className={`${PANEL} p-4 space-y-1`}>
            <p className="whitespace-pre-wrap">{v.text}</p>
            <p className={META}>{STATUS_LABELS[v.status] || v.status} · {validityLabel(v.valid_from, v.valid_to)} · {VISIBILITY_LABELS[v.visibility]}</p>
            <p className={META}>{sourceInWords(v).from} · Who said it: {authorLabel(v.author)}</p></li>)}</ol></section>
        <section className="space-y-2"><h4 className="text-[13px] font-semibold">Decisions</h4>
          {!history.decisions.length && <p className="text-[13px] text-[#8B93A3]">No decisions recorded.</p>}
          <ol className="space-y-2 text-[13px]">{history.decisions.map((d, i) => <li key={i} className="border-l-2 border-[#E6E9F0] pl-3">
            <p><span className="font-medium">{historyAction(d.action)}</span> by {plainReason(d.author || d.actor) || 'someone'} on {formatDate(d.created_at)}</p>
            {d.note && <p className="text-[#667184]">Why: {plainReason(d.note)}</p>}</li>)}</ol></section>
      </>}
    </aside>
  </div>;
}

export function FactEditor({ entries, busy, onSave, initialKind = 'price', initial, onCancel }: {
  entries: ContextItem[]; busy: boolean; onSave: (body: EntryBody) => void; initialKind?: EditableKind; initial?: ContextItem | null; onCancel?: () => void;
}) {
  const [form, setForm] = useState<FactForm>(() => initial ? factFromItem(initial) : emptyFact(initialKind));
  const [error, setError] = useState('');
  const existing = entries.find(e => e.item_id === form.changing) || null;
  const choices = entries.filter(e => e.kind === form.kind);
  const set = (patch: Partial<FactForm>) => setForm({ ...form, ...patch });
  const submit = () => {
    const r = entryRequest(form, existing);
    if ('error' in r) { setError(r.error); return; }
    setError(''); onSave(r.body);
  };
  return <section className="space-y-4 text-[13px]" aria-label="Add or change a fact">
    <h3 className="sr-only">Add or change a fact</h3>
    <p className="text-[#667184]">Your entry is confirmed as soon as you save it. To change something, pick it and choose the date the change takes effect.</p>
    <div className="grid gap-3 sm:grid-cols-2">
      <label className={LABEL}>What kind of fact<Select className={FIELD} value={form.kind} onChange={e => setForm(emptyFact(e.target.value as EditableKind))}>
        {EDITABLE_KINDS.map(k => <option key={k} value={k}>{kindLabel(k)}</option>)}</Select></label>
      <label className={LABEL}>New, or a change to<Select className={FIELD} value={form.changing} onChange={e => { const item = choices.find(c => c.item_id === e.target.value); setForm(item ? factFromItem(item) : emptyFact(form.kind)); }}>
        <option value="">A new {kindLabel(form.kind).toLowerCase()}</option>{choices.map(c => <option key={c.item_id} value={c.item_id}>{c.text.slice(0, 90)}</option>)}</Select></label>
    </div>
    <div className="grid gap-3 sm:grid-cols-2">{FACT_FIELDS[form.kind].map(spec => {
      const value = form.fields[spec.name] || '';
      const update = (v: string) => set({ fields: { ...form.fields, [spec.name]: v } });
      return <label key={spec.name} className={`${LABEL} ${spec.long ? 'sm:col-span-2' : ''}`}>{spec.label}{spec.required ? ' *' : ''}
        {spec.options ? <Select className={FIELD} value={value} onChange={e => update(e.target.value)}>{spec.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
          : spec.long ? <textarea className={FIELD} rows={3} value={value} onChange={e => update(e.target.value)} />
          : <input className={FIELD} value={value} onChange={e => update(e.target.value)} />}</label>;
    })}</div>
    <div className="grid gap-3 sm:grid-cols-2">
      <label className={LABEL}>Who may see it<Select className={FIELD} value={form.visibility} onChange={e => set({ visibility: e.target.value as Visibility })}>
        <option value="public">{VISIBILITY_LABELS.public}</option><option value="internal">{VISIBILITY_LABELS.internal}</option></Select>
        {form.kind === 'price' && <span className="mt-1 block font-normal text-[#8B93A3]">Prices are internal by default: the system knows them but they are never stated in public copy.</span>}</label>
      {form.kind === 'result' && <label className={LABEL}>Permission to use it *<Select className={FIELD} value={form.permission} onChange={e => set({ permission: e.target.value as Permission })}>
        <option value="">Choose…</option>{(Object.keys(PERMISSION_LABELS) as Permission[]).map(p => <option key={p} value={p}>{PERMISSION_LABELS[p]}</option>)}</Select></label>}
      {form.kind === 'result' && <label className="flex items-center gap-2 sm:col-span-2"><input type="checkbox" checked={form.client_private} onChange={e => set({ client_private: e.target.checked, ...(e.target.checked ? { visibility: 'internal' as const } : {}) })} />Private to the client (kept internal)</label>}
      <label className={LABEL}>In use from{existing ? ' *' : ' (optional)'}<DateInput className={FIELD} value={form.valid_from} onChange={e => set({ valid_from: e.target.value })} /></label>
      <label className={LABEL}>In use until (optional)<DateInput className={FIELD} value={form.valid_to} onChange={e => set({ valid_to: e.target.value })} /></label>
    </div>
    {existing && <p className="rounded-xl bg-[#F7F8FB] p-3 text-[#667184]">Current version: {existing.text}. {validityLabel(existing.valid_from, existing.valid_to)}. The current version stays in use until the day before your change starts.</p>}
    <label className={`${LABEL} block`}>Reason *<input className={FIELD} value={form.reason} onChange={e => set({ reason: e.target.value })} /></label>
    <label className={`${LABEL} block`}>Entering it for someone else? Their name (optional)<input className={FIELD} value={form.author} onChange={e => set({ author: e.target.value })} /></label>
    <StatusLine tone="error">{error}</StatusLine>
    <div className="flex justify-end gap-2">
      {onCancel && <button type="button" className={QUIET_BUTTON} onClick={onCancel}>Cancel</button>}
      <button type="button" className={DARK_BUTTON} disabled={busy} onClick={submit}>{busy ? 'Saving…' : existing ? 'Save the change' : 'Save the new fact'}</button>
    </div>
  </section>;
}

type PerformanceForm = 'piece' | 'figure' | 'link' | 'import';
const FORM_TITLES: Record<PerformanceForm, string> = {
  piece: 'Record a published piece', figure: 'Add a figure to a piece', link: 'Link a piece to the approved brief it came from', import: 'Import figures from a spreadsheet',
};

/** One of the published-piece forms, for a dialog; `onPost` sends it and resolves true once it is saved. */
export function PerformanceForms({ form, pieces, briefs, busy, onPost, onCancel }: {
  form: PerformanceForm; pieces: PublishedPiece[]; briefs: BriefOption[]; busy: boolean; onPost: (path: string, body: unknown, done: string) => void; onCancel?: () => void;
}) {
  const [piece, setPiece] = useState<PieceForm>({ published_on: '', channel: '', title: '', text: '', brief_id: '' });
  const [metric, setMetric] = useState<MetricForm>({ content_id: '', on: '', metric: '', value: '', direction: '' });
  const [link, setLink] = useState({ content_id: '', brief_id: '' });
  const [csv, setCsv] = useState('');
  const [error, setError] = useState('');
  const run = <T,>(r: T | { error: string }, then: (v: T) => void) => { if (r && typeof r === 'object' && 'error' in r) { setError((r as { error: string }).error); return; } setError(''); then(r as T); };
  const pieceSelect = (value: string, onChange: (v: string) => void) => <Select className={FIELD} value={value} onChange={e => onChange(e.target.value)}>
    <option value="">Choose a piece…</option>{pieces.map(p => <option key={p.content_id} value={p.content_id}>{pieceLabel(p)}</option>)}</Select>;
  const briefSelect = (value: string, onChange: (v: string) => void, empty: string) => <Select className={FIELD} value={value} onChange={e => onChange(e.target.value)}>
    <option value="">{empty}</option>{briefs.map(b => <option key={b.brief_id} value={b.brief_id}>{b.title}</option>)}</Select>;
  const buttons = (label: string) => <div className="flex justify-end gap-2 pt-1">
    {onCancel && <button type="button" className={QUIET_BUTTON} onClick={onCancel}>Cancel</button>}
    <button className={DARK_BUTTON} disabled={busy}>{busy ? 'Saving…' : label}</button></div>;
  return <div className="space-y-3 text-[13px]">
    <h4 className="sr-only">{FORM_TITLES[form]}</h4>
    {form === 'piece' && <form className="space-y-3" onSubmit={e => { e.preventDefault(); run(pieceRequest(piece), r => onPost('/context/published', r.body, 'The piece is recorded.')); }}>
      <div className="grid gap-3 sm:grid-cols-2"><label className={LABEL}>Published on *<DateInput className={FIELD} value={piece.published_on} onChange={e => setPiece({ ...piece, published_on: e.target.value })} /></label>
        <label className={LABEL}>Where *<input className={FIELD} list="context-channels" value={piece.channel} onChange={e => setPiece({ ...piece, channel: e.target.value })} /></label></div>
      <label className={`${LABEL} block`}>Title or first line *<input className={FIELD} value={piece.title} onChange={e => setPiece({ ...piece, title: e.target.value })} /></label>
      <label className={`${LABEL} block`}>The final text (optional)<textarea className={FIELD} rows={4} value={piece.text} onChange={e => setPiece({ ...piece, text: e.target.value })} /></label>
      <label className={`${LABEL} block`}>The approved brief behind it (optional){briefSelect(piece.brief_id, v => setPiece({ ...piece, brief_id: v }), 'No brief')}</label>
      {buttons('Record the piece')}</form>}
    {form === 'figure' && <form className="space-y-3" onSubmit={e => { e.preventDefault(); run(metricRequest(metric), r => onPost(r.path, r.body, 'The figure is recorded.')); }}>
      <label className={`${LABEL} block`}>Piece *{pieceSelect(metric.content_id, v => setMetric({ ...metric, content_id: v }))}</label>
      <div className="grid gap-3 sm:grid-cols-2"><label className={LABEL}>Date of the figure *<DateInput className={FIELD} value={metric.on} onChange={e => setMetric({ ...metric, on: e.target.value })} /></label>
        <label className={LABEL}>Measure *<input className={FIELD} list="context-metrics" value={metric.metric} onChange={e => setMetric({ ...metric, metric: e.target.value })} /></label>
        <label className={LABEL}>Figure *<input className={FIELD} value={metric.value} onChange={e => setMetric({ ...metric, value: e.target.value })} /></label>
        <label className={LABEL}>How it did<Select className={FIELD} value={metric.direction} onChange={e => setMetric({ ...metric, direction: e.target.value as MetricForm['direction'] })}>
          <option value="">Not said</option><option value="positive">Did well</option><option value="negative">Did poorly</option></Select></label></div>
      {buttons('Add the figure')}</form>}
    {form === 'link' && <form className="space-y-3" onSubmit={e => { e.preventDefault(); run(linkRequest(link.content_id, link.brief_id), r => onPost(r.path, r.body, 'The piece is linked to its brief.')); }}>
      <label className={`${LABEL} block`}>Piece *{pieceSelect(link.content_id, v => setLink({ ...link, content_id: v }))}</label>
      <label className={`${LABEL} block`}>Approved brief *{briefSelect(link.brief_id, v => setLink({ ...link, brief_id: v }), 'Choose a brief…')}</label>
      {buttons('Link them')}</form>}
    {form === 'import' && <form className="space-y-3" onSubmit={e => { e.preventDefault(); run(csvRequest(csv), r => onPost('/context/published/import', r.body, 'The file is imported.')); }}>
      <p className="text-[#667184]">Save it as CSV with the columns {CSV_COLUMNS.join(', ')}.</p>
      <input type="file" accept=".csv,text/csv" onChange={e => { const file = e.target.files?.[0]; if (file) void file.text().then(setCsv); }} />
      <textarea className={FIELD} rows={4} aria-label="CSV contents" value={csv} onChange={e => setCsv(e.target.value)} />
      {buttons('Import')}</form>}
    <StatusLine tone="error">{error}</StatusLine>
    <datalist id="context-channels">{['email', 'carousel', 'reel', 'instagram', 'linkedin', 'podcast'].map(c => <option key={c} value={c} />)}</datalist>
    <datalist id="context-metrics">{['opens', 'clicks', 'replies', 'bookings', 'saves', 'shares', 'views'].map(c => <option key={c} value={c} />)}</datalist>
  </div>;
}

/** The published pieces and their figures, with the buttons that open the forms. */
export function PerformancePanel({ pieces, onOpen }: { pieces: PublishedPiece[]; onOpen: (form: PerformanceForm) => void }) {
  const withFigures = pieces.filter(p => p.performance?.length).slice(0, 10);
  return <section className={`${PANEL} p-5 space-y-3 text-[13px]`} aria-label="Published pieces and performance">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h3 className="font-editorial text-xl text-[#1B2433]">Published pieces and how they did</h3>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={QUIET_BUTTON} onClick={() => onOpen('figure')}>Add a figure</button>
        <button type="button" className={QUIET_BUTTON} onClick={() => onOpen('link')}>Link to a brief</button>
        <button type="button" className={QUIET_BUTTON} onClick={() => onOpen('import')}>Import figures</button>
      </div>
    </div>
    {!withFigures.length && <p className="text-[#8B93A3]">{pieces.length ? `${pieces.length} published ${pieces.length === 1 ? 'piece is' : 'pieces are'} recorded; none has a figure yet.` : 'No published piece is recorded yet.'}</p>}
    {withFigures.length > 0 && <ul className="divide-y divide-[#EEF0F4]">{withFigures.map(p => <li key={p.content_id} className="py-2">
      <p className="text-[#1B2433]">{pieceLabel(p)}{p.brief_id ? ' · linked to its brief' : ''}</p>
      <p className={META}>{p.performance!.map(figureLabel).join(' · ')}</p></li>)}</ul>}
  </section>;
}

export function ContextKnowledge() {
  const { itemId } = useParams();
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const invalidate = useInvalidate();
  // The kind and the day are in the query string (`?kind=offer&on=2026-10-18`); an entry's history has its own path.
  const kind = search.get('kind') ?? '', on = /^\d{4}-\d{2}-\d{2}$/.test(search.get('on') ?? '') ? search.get('on')! : todayIso();
  const setParam = (name: string, value: string) => setSearch(prev => { const next = new URLSearchParams(prev); if (value) next.set(name, value); else next.delete(name); return next; }, { replace: true });
  const [notice, setNotice] = useState('');
  const [editing, setEditing] = useState<{ item: ContextItem | null } | null>(null);
  const [form, setForm] = useState<PerformanceForm | null>(null);
  const known = useApiQuery('/context/items', { query: { kind: (kind || undefined) as ItemKind | undefined, on } });
  const everything = useApiQuery('/context/items', {});
  const warnings = useApiQuery('/context/warnings', undefined, { refetchInterval: 300_000 });
  const published = useApiQuery('/context/published', { query: { limit: 200 } });
  // The approved briefs fill the piece and link forms' choice; a full brief is heavy to read, so they are read only while one of
  // those forms is open, and only the latest 20 (100 at once ran past the server's time limit on the production copy).
  const approved = useApiQuery('/briefs', { query: { status: 'approved', limit: 20 } }, { enabled: form === 'piece' || form === 'link', staleTime: 300_000 });
  const history = useApiQuery('/context/items/{item_id}/history', { path: { item_id: itemId ?? '' } }, { enabled: !!itemId });
  const entries = everything.data ? [...everything.data.items, ...everything.data.scheduled].filter(i => (EDITABLE_KINDS as readonly string[]).includes(i.kind)) : [];
  const briefs = briefOptions(approved.data?.items.map(b => ({ brief_id: b.brief_id, content_body: b.content_body })) ?? []);
  const reload = () => Promise.all([known.refetch(), everything.refetch(), published.refetch(), warnings.refetch()]);
  const guard = useGuardedAction(reload, contextFailure);
  const post = (path: string, body: unknown, done: string) => {
    setNotice('');
    return guard.run(async () => {
      await storageRequest(path, 'POST', body);
      setNotice(done); setEditing(null); setForm(null);
      await invalidate('/context/items', '/context/published', '/context/warnings', '/context/summary', '/context/queue', '/context/items/{item_id}/history');
    });
  };
  const readError = known.error || history.error;
  const error = guard.error || (readError ? contextError(readError).message : '');
  return <section className="space-y-5" aria-label="What the system knows">
    <PageHeading title="Knowledge" subtitle={`What runs use on ${formatDate(on)}`} actions={<>
      <div className="max-w-sm text-right"><StatusLine>{!editing && !form ? notice : ''}</StatusLine></div>
      <button type="button" className={HEADER_QUIET} onClick={() => { setNotice(''); setForm('piece'); }}>Record a published piece</button>
      <button type="button" className={HEADER_PRIMARY} onClick={() => { setNotice(''); setEditing({ item: null }); }}><Plus aria-hidden="true" className="h-3.5 w-3.5" />Add a fact</button>
    </>} />
    <WarningsList warnings={warnings.data?.warnings ?? []} />
    <div className="flex flex-wrap items-center gap-2.5">
      <FilterSelect label="Show" any="Everything" value={kind} options={KIND_ORDER.map(k => ({ value: k, label: kindLabel(k, true) }))} onChange={value => setParam('kind', value)} />
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">In use on<DateInput className={SELECT} value={on} onChange={e => setParam('on', e.target.value)} /></label>
    </div>
    <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
    {!editing && !form && <StatusLine tone="error">{error}</StatusLine>}
    {known.isPending && !known.error && <LoadingState>Loading what the system knows…</LoadingState>}
    {known.data && <KnownList known={known.data} onChange={item => { setNotice(''); setEditing({ item }); }}
      onHistory={item => navigate(paths.knownItem(item.item_id) + (search.size ? `?${search}` : ''))} />}
    <PerformancePanel pieces={published.data?.items ?? []} onOpen={next => { setNotice(''); setForm(next); }} />
    {editing && <Dialog title={editing.item ? 'Change a fact' : 'Add a fact'} wide onClose={() => setEditing(null)}>
      <FactEditor entries={entries} busy={guard.busy} initial={editing.item} onCancel={() => setEditing(null)}
        onSave={body => void post('/context/items', body, 'Saved. It is confirmed and in use from its start date.')} />
      <StatusLine tone="error">{error}</StatusLine>
    </Dialog>}
    {form && <Dialog title={FORM_TITLES[form]} onClose={() => setForm(null)}>
      <PerformanceForms form={form} pieces={published.data?.items ?? []} briefs={briefs} busy={guard.busy} onCancel={() => setForm(null)} onPost={(path, body, done) => void post(path, body, done)} />
      <StatusLine tone="error">{error}</StatusLine>
    </Dialog>}
    {itemId && <HistoryDrawer history={history.data ?? null} onClose={() => navigate(paths.known + (search.size ? `?${search}` : ''))} />}
  </section>;
}
