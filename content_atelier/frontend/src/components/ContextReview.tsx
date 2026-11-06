import React, { useId, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Lock } from 'lucide-react';
import type { BatchBody, ContextItem, ContextQueue, ContextSummary, DecisionAction, DecisionBody, ItemChanges, ItemKind,
  Permission, PublishedPiece, Sensitivity, Visibility } from '../api/types';
import { useApiQuery, useInvalidate } from '../api/query';
import { storageRequest } from '../utils/weeklyStorage';
import { KIND_ORDER, PERMISSION_LABELS, VISIBILITY_LABELS, authorLabel, changeInWords, contextError, contextFailure, formatDate,
  kindLabel, sensitivityLabel, sourceInWords, whoDecides } from '../utils/context';
import { ConflictNotice, useGuardedAction } from './shared/conflict';
import { LoadingState } from './shared/states';
import { PageHeading } from './PageHeading';
import { DARK_BUTTON, FIELD, LABEL, META, PANEL, Pager, Pill, QUIET_BUTTON, SELECT, StatusLine } from './AdminParts';
import { Select } from './ThemedSelect';
import { DateInput } from './DateInput';

/* L.F1: the review queue. A non-technical reviewer (R50) accepts, edits or rejects every candidate the seed and the
   learning loop propose, with a reason. Suggestions are pre-selected, never applied on their own. Batch decisions
   only for audience phrases and for unconfirmed published pieces (L.B3). */

export const PAGE_SIZE = 50;
export const PUBLISHED_TAB = 'published';
export const ACTIONS: { value: DecisionAction; label: string; help: string }[] = [
  { value: 'accept', label: 'Accept', help: 'Keep it as written.' },
  { value: 'edit', label: 'Edit and accept', help: 'Correct the wording, then keep it.' },
  { value: 'reject', label: 'Reject', help: 'Leave it out of what the system knows.' },
];

export interface ReviewForm {
  action: DecisionAction | ''; reason: string; author: string; text: string;
  visibility: Visibility; sensitivity: Sensitivity; permission: Permission | ''; valid_from: string; valid_to: string;
}

/** The form a candidate opens with: its own values, with the suggestion's choice, reason and settings pre-selected. */
export function initialForm(item: ContextItem): ReviewForm {
  const s = item.suggestion;
  const changes = s?.changes || {};
  return {
    action: s && s.action !== 'review' ? s.action : '', reason: s?.reason || '', author: '', text: item.text,
    visibility: (changes.visibility || item.visibility) as Visibility,
    sensitivity: (changes.sensitivity || (item.sensitivity === 'client_private' ? 'client_private' : 'none')) as Sensitivity,
    permission: (changes.permission || item.permission || '') as Permission | '',
    valid_from: item.valid_from || '', valid_to: item.valid_to || '',
  };
}

/** The decision request for one candidate, or what is still missing (the API's own rules). */
export function decisionRequest(item: ContextItem, f: ReviewForm): { path: string; body: DecisionBody } | { error: string } {
  if (!f.action) return { error: 'Choose Accept, Edit and accept, or Reject.' };
  const reason = f.reason.trim();
  if (!reason) return { error: 'Write a reason. It is kept with the decision.' };
  if (reason.length > 2000) return { error: 'Keep the reason under 2,000 characters.' };
  const path = `/context/items/${item.item_id}/decision`;
  const base: DecisionBody = { expected_hash: item.hash, action: f.action, reason, ...(f.author.trim() ? { author: f.author.trim() } : {}) };
  if (f.action === 'reject') return { path, body: base };
  const changes: ItemChanges = {};
  if (f.action === 'edit') {
    const text = f.text.trim();
    if (!text) return { error: 'The wording cannot be empty.' };
    if (text === item.text.trim()) return { error: 'Change the wording to edit it, or choose Accept.' };
    if (text.length > 8000) return { error: 'Keep the wording under 8,000 characters.' };
    changes.text = text;
  }
  if (f.sensitivity === 'client_private' && f.visibility !== 'internal') return { error: 'Client-private material must be internal.' };
  if (item.kind === 'result' && !f.permission) return { error: 'Say what permission WIA has for this result.' };
  if (f.valid_from && f.valid_to && f.valid_to < f.valid_from) return { error: 'The end date must be after the start date.' };
  if (f.visibility !== item.visibility) changes.visibility = f.visibility;
  if (f.sensitivity !== (item.sensitivity || 'none')) changes.sensitivity = f.sensitivity;
  if (item.kind === 'result' && f.permission && f.permission !== item.permission) changes.permission = f.permission;
  if ((f.valid_from || null) !== (item.valid_from || null)) changes.valid_from = f.valid_from || null;
  if ((f.valid_to || null) !== (item.valid_to || null)) changes.valid_to = f.valid_to || null;
  return { path, body: Object.keys(changes).length ? { ...base, changes } : base };
}

/** A batch decision: only for the low-risk kinds the API names (audience phrases), 1 to 100 entries. */
export function batchRequest(items: ContextItem[], action: 'accept' | 'reject', reason: string, batchKinds: string[], author = ''): { body: BatchBody } | { error: string } {
  if (!items.length) return { error: 'Tick the entries to decide together.' };
  if (items.length > 100) return { error: 'Decide at most 100 entries at once.' };
  if (items.some(i => !batchKinds.includes(i.kind))) return { error: 'Only audience phrases can be decided together; decide the others one by one.' };
  if (!reason.trim()) return { error: 'Write a reason for the batch.' };
  return { body: { action, reason: reason.trim(), ...(author.trim() ? { author: author.trim() } : {}), entries: items.map(i => ({ item_id: i.item_id, expected_hash: i.hash })) } };
}

export function publishedConfirmRequest(ids: string[], reason: string): { body: { content_ids: string[]; reason: string } } | { error: string } {
  if (!ids.length) return { error: 'Tick the pieces WIA published.' };
  if (ids.length > 100) return { error: 'Confirm at most 100 pieces at once.' };
  if (!reason.trim()) return { error: 'Write a reason.' };
  return { body: { content_ids: ids, reason: reason.trim() } };
}

/** Candidates in queue order, with those that share an entry kept together. */
export function groupQueue(items: ContextItem[], groups: Record<string, string[]>): { key: string; items: ContextItem[] }[] {
  const out: { key: string; items: ContextItem[] }[] = [];
  const at = new Map<string, number>();
  for (const item of items) {
    const grouped = (groups[item.key] || []).includes(item.item_id);
    if (grouped && at.has(item.key)) { out[at.get(item.key)!].items.push(item); continue; }
    if (grouped) at.set(item.key, out.length);
    out.push({ key: grouped ? item.key : item.item_id, items: [item] });
  }
  return out;
}

/** The tabs: everything, each kind with candidates waiting, and the published pieces. */
export function kindTabs(summary: ContextSummary | null): { id: string; label: string; count: number }[] {
  if (!summary) return [{ id: '', label: 'Everything', count: 0 }];
  const kinds = KIND_ORDER.filter(k => (summary.kinds[k]?.candidate || 0) > 0)
    .map(k => ({ id: k as string, label: kindLabel(k, true), count: summary.kinds[k]!.candidate || 0 }));
  return [{ id: '', label: 'Everything', count: summary.candidates }, ...kinds,
    { id: PUBLISHED_TAB, label: 'Published pieces', count: summary.published.unconfirmed || 0 }];
}

export function progressLabel(summary: ContextSummary | null): string {
  if (!summary) return '';
  const n = summary.candidates + (summary.published.unconfirmed || 0);
  if (!n) return 'Nothing left to review';
  return `${n.toLocaleString('en-US')} left to review`;
}

export const pageLabel = (q: Pick<ContextQueue, 'offset' | 'total'>, shown: number) =>
  q.total ? `Showing ${q.offset + 1} to ${q.offset + shown} of ${q.total.toLocaleString('en-US')}` : '';

export function ReviewCard({ item, busy, selectable, selected, onSelect, onDecide }: {
  item: ContextItem; busy: boolean; selectable: boolean; selected: boolean; onSelect: (on: boolean) => void;
  onDecide: (path: string, body: DecisionBody) => void;
}) {
  const [form, setForm] = useState<ReviewForm>(() => initialForm(item));
  const [error, setError] = useState('');
  const radioName = useId();
  const set = (patch: Partial<ReviewForm>) => setForm({ ...form, ...patch });
  const source = sourceInWords(item);
  const allowed = item.can_decide !== false;
  const suggestion = item.suggestion;
  const suggested = suggestion?.action === 'review' ? 'Look closely before deciding' : ACTIONS.find(a => a.value === suggestion?.action)?.label;
  const diffs = item.source_kind === 'brief_edit' ? item.source_detail?.diffs || [] : [];
  const submit = () => {
    const result = decisionRequest(item, form);
    if ('error' in result) { setError(result.error); return; }
    setError(''); onDecide(result.path, result.body);
  };
  const settings = <div className="grid gap-3 sm:grid-cols-2">
    <label className={LABEL}>Who may see it<Select className={FIELD} value={form.visibility} onChange={e => set({ visibility: e.target.value as Visibility })}>
      <option value="public">{VISIBILITY_LABELS.public}</option><option value="internal">{VISIBILITY_LABELS.internal}</option></Select></label>
    <label className={LABEL}>Private to a client?<Select className={FIELD} value={form.sensitivity} onChange={e => set({ sensitivity: e.target.value as Sensitivity })}>
      <option value="none">No</option><option value="client_private">Yes, client-private (kept internal)</option></Select></label>
    {item.kind === 'result' && <label className={LABEL}>Permission to use it<Select className={FIELD} value={form.permission} onChange={e => set({ permission: e.target.value as Permission })}>
      <option value="">Choose…</option>{(Object.keys(PERMISSION_LABELS) as Permission[]).map(p => <option key={p} value={p}>{PERMISSION_LABELS[p]}</option>)}</Select></label>}
    <label className={LABEL}>In use from (optional)<DateInput className={FIELD} value={form.valid_from} onChange={e => set({ valid_from: e.target.value })} /></label>
    <label className={LABEL}>In use until (optional)<DateInput className={FIELD} value={form.valid_to} onChange={e => set({ valid_to: e.target.value })} /></label>
  </div>;
  return <article className={`${PANEL} p-5 space-y-4 text-[13px] text-[#34445F]`} aria-label={`${kindLabel(item.kind)} to review`}>
    <header className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-3">
        {selectable && <label className="flex items-center gap-2 text-[12px]"><input type="checkbox" checked={selected} disabled={!allowed || busy} onChange={e => onSelect(e.target.checked)} />Select</label>}
        <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]">{kindLabel(item.kind)}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Pill tone="quiet">{item.visibility === 'internal' && <Lock className="h-3 w-3" strokeWidth={1.75} />}{item.visibility === 'internal' ? 'Internal' : 'Public'}</Pill>
        {sensitivityLabel(item.sensitivity) && <Pill tone="quiet">{sensitivityLabel(item.sensitivity)}</Pill>}
        {item.kind === 'result' && <Pill tone="quiet">{item.permission ? PERMISSION_LABELS[item.permission] : 'Permission not recorded'}</Pill>}
      </div>
    </header>
    <p className="whitespace-pre-wrap font-editorial text-[17px] leading-relaxed text-[#1B2433]">{item.text}</p>
    <p className={META}>{source.from} · Who said it: {authorLabel(item.author)}</p>
    {item.would_change && <div className="rounded-xl bg-[#F7F8FB] p-3"><p>{changeInWords(item)}</p>
      {item.would_change.replaces && <p className="mt-1 border-l-2 border-[#E6E9F0] pl-3 text-[#667184]">Current entry: {item.would_change.replaces.text}</p>}</div>}
    {diffs.length > 0 && <div><p className="mb-1 text-[12px] font-semibold">The edits it came from</p>
      <ul className="space-y-1">{diffs.map((d, i) => <li key={i} className="rounded-xl bg-[#F7F8FB] p-2"><span className="text-red-800 line-through">{d.before}</span> <span className="text-emerald-800">{d.after}</span></li>)}</ul></div>}
    {suggestion && <p className="rounded-xl bg-[#EFF3FF] p-3"><span className="font-semibold text-[#1B2433]">Suggested: {suggested}.</span> <span className="text-[#667184]">{suggestion.reason}</span></p>}
    <fieldset className="space-y-3 border-t border-[#EEF0F4] pt-4" disabled={!allowed}>
      <legend className="sr-only">Your decision</legend>
      {!allowed && <p className="text-[12px] text-[#947021]">{whoDecides(item.kind)}</p>}
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Decision">{ACTIONS.map(a => <label key={a.value} title={a.help}
        className={`flex cursor-pointer items-center gap-2 rounded-full border px-3.5 py-1.5 text-[12px] font-medium ${form.action === a.value ? 'border-[#5070FF] bg-[#EFF3FF] text-[#1B2433]' : 'border-[#E6E9F0] bg-white text-[#34445F]'}`}>
        <input type="radio" name={radioName} checked={form.action === a.value} onChange={() => set({ action: a.value })} />{a.label}</label>)}</div>
      {form.action === 'edit' && <>
        <label className={`${LABEL} block`}>The wording<textarea className={FIELD} rows={5} value={form.text} onChange={e => set({ text: e.target.value })} /></label>
        {settings}
      </>}
      {form.action === 'accept' && <details><summary className="cursor-pointer text-[12px] text-[#5070FF]">Who may see it and when it is used: {VISIBILITY_LABELS[form.visibility]}{form.sensitivity === 'client_private' ? ' · client-private' : ''}{item.kind === 'result' && form.permission ? ` · ${PERMISSION_LABELS[form.permission]}` : ''}</summary>
        <div className="mt-2">{settings}</div></details>}
      <div className="grid gap-3 sm:grid-cols-[1fr_16rem]">
        <label className={LABEL}>Reason *<textarea className={FIELD} rows={2} value={form.reason} onChange={e => set({ reason: e.target.value })} /></label>
        <label className={LABEL}>Deciding for someone else? Their name<input className={FIELD} value={form.author} onChange={e => set({ author: e.target.value })} /></label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className={DARK_BUTTON} disabled={busy || !allowed} onClick={submit}>{busy ? 'Saving…' : 'Save decision'}</button>
        <StatusLine tone="error">{error}</StatusLine>
      </div>
    </fieldset>
  </article>;
}

export function ReviewQueueList({ queue, batchKinds, busy, selected, onSelect, onDecide }: {
  queue: ContextQueue; batchKinds: string[]; busy: boolean; selected: string[]; onSelect: (id: string, on: boolean) => void;
  onDecide: (path: string, body: DecisionBody) => void;
}) {
  if (!queue.items.length) return <p className={`${PANEL} p-5 text-[13px]`}>Nothing waiting here. Every entry has been decided.</p>;
  return <div className="space-y-4">{groupQueue(queue.items, queue.groups).map(group => {
    const cards = group.items.map(item => <ReviewCard key={`${item.item_id}:${item.hash}`} item={item} busy={busy}
      selectable={batchKinds.includes(item.kind)} selected={selected.includes(item.item_id)} onSelect={on => onSelect(item.item_id, on)} onDecide={onDecide} />);
    return group.items.length > 1
      ? <section key={group.key} className="space-y-3 rounded-3xl border border-dashed border-[#DCE1EA] p-3" aria-label="Suggestions for the same entry">
        <p className="px-2 text-[12px] text-[#8B93A3]">{group.items.length} suggestions for the same {kindLabel(group.items[0].kind).toLowerCase()}. Accept the best one and reject the others.</p>{cards}</section>
      : <React.Fragment key={group.key}>{cards}</React.Fragment>;
  })}</div>;
}

export function PublishedList({ pieces, selected, busy, onSelect }: { pieces: PublishedPiece[]; selected: string[]; busy: boolean; onSelect: (ids: string[]) => void }) {
  if (!pieces.length) return <p className={`${PANEL} p-5 text-[13px]`}>No published pieces wait for confirmation.</p>;
  const all = pieces.every(p => selected.includes(p.content_id));
  return <div className={`${PANEL} p-5 space-y-3 text-[13px]`}>
    <label className="flex items-center gap-2 font-medium"><input type="checkbox" checked={all} disabled={busy} onChange={e => onSelect(e.target.checked ? pieces.map(p => p.content_id) : [])} />Select all {pieces.length}</label>
    <ul className="divide-y divide-[#EEF0F4]">{pieces.map(p => <li key={p.content_id} className="py-2">
      <label className="flex gap-3"><input type="checkbox" disabled={busy} checked={selected.includes(p.content_id)}
        onChange={e => onSelect(e.target.checked ? [...selected, p.content_id] : selected.filter(x => x !== p.content_id))} />
        <span><span className="block text-[#1B2433]">{p.title || 'Untitled piece'}</span>
          <span className={META}>{[p.channel, formatDate(p.published_on) || (p.details?.date_text as string | undefined), p.source_kind === 'export_seed' ? 'from the published-content log' : null].filter(Boolean).join(' · ')}</span></span></label>
    </li>)}</ul>
  </div>;
}

function BatchBar({ count, label, reason, busy, onReason, actions }: { count: number; label: string; reason: string; busy: boolean; onReason: (v: string) => void; actions: { label: string; run: () => void }[] }) {
  if (!count) return null;
  return <div className="sticky top-2 z-10 space-y-2 rounded-2xl border border-[#D1DBFF] bg-[#EFF3FF] p-4 text-[13px] shadow-[0_3px_18px_rgba(28,36,52,0.06)]">
    <p className="font-semibold text-[#1B2433]">{count} {label} selected</p>
    <label className={`${LABEL} block`}>Reason for all of them *<input className={FIELD} value={reason} onChange={e => onReason(e.target.value)} /></label>
    <div className="flex gap-2">{actions.map(a => <button key={a.label} type="button" className={QUIET_BUTTON} disabled={busy} onClick={a.run}>{a.label}</button>)}</div>
  </div>;
}

export function ContextReview() {
  const [search, setSearch] = useSearchParams();
  const invalidate = useInvalidate();
  // The tab and the page are in the query string (`?kind=offer&offset=50`), so a refresh keeps the place.
  const tab = search.get('kind') ?? '', offset = Math.max(0, Number(search.get('offset')) || 0);
  const [selected, setSelected] = useState<string[]>([]);
  const [batchReason, setBatchReason] = useState('');
  const [notice, setNotice] = useState('');
  const [formError, setFormError] = useState('');
  const summaryQuery = useApiQuery('/context/summary', undefined, { refetchInterval: 60_000 });
  const kindsQuery = useApiQuery('/context/kinds', undefined, { staleTime: 600_000 });
  const published = tab === PUBLISHED_TAB;
  const queueQuery = useApiQuery('/context/queue', { query: { kind: (tab || undefined) as ItemKind | undefined, status: 'candidate', limit: PAGE_SIZE, offset } }, { enabled: !published });
  const piecesQuery = useApiQuery('/context/published', { query: { status: 'unconfirmed', limit: 100 } }, { enabled: published });
  const summary = summaryQuery.data ?? null, queue = published ? null : queueQuery.data ?? null, pieces = piecesQuery.data?.items ?? [];
  const reload = () => Promise.all([summaryQuery.refetch(), published ? piecesQuery.refetch() : queueQuery.refetch()]);
  const guard = useGuardedAction(reload, contextFailure);
  const busy = guard.busy;
  const perform = (path: string, body: unknown, done: string) => {
    setNotice(''); setFormError('');
    return guard.run(async () => {
      await storageRequest(path, 'POST', body);
      setSelected([]); setBatchReason(''); setNotice(done);
      await invalidate('/context/summary', '/context/queue', '/context/published', '/context/items', '/context/warnings');
    });
  };
  const readError = [summaryQuery.error, published ? piecesQuery.error : queueQuery.error].find(Boolean);
  const error = formError || guard.error || (readError ? contextError(readError).message : '');
  const batchKinds = kindsQuery.data?.batch || queue?.batch_kinds || ['audience_phrase'];
  const chosen = (queue?.items || []).filter(i => selected.includes(i.item_id));
  const runBatch = (action: 'accept' | 'reject') => {
    const r = batchRequest(chosen, action, batchReason, batchKinds);
    if ('error' in r) { setFormError(r.error); return; }
    void perform('/context/batch', r.body, `${chosen.length} audience phrases ${action === 'accept' ? 'accepted' : 'rejected'}.`);
  };
  const confirmPieces = () => {
    const r = publishedConfirmRequest(selected, batchReason);
    if ('error' in r) { setFormError(r.error); return; }
    void perform('/context/published/confirm', r.body, `${selected.length} published pieces confirmed.`);
  };
  const choose = (id: string) => {
    setSearch(id ? { kind: id } : {}, { replace: true });
    setSelected([]); setNotice(''); setFormError(''); setBatchReason(id === PUBLISHED_TAB ? 'WIA published these pieces' : '');
  };
  const setOffset = (value: number) => setSearch(prev => { const next = new URLSearchParams(prev); if (value) next.set('offset', String(value)); else next.delete('offset'); return next; }, { replace: true });
  const tabs = kindTabs(summary);
  return <section className="space-y-5" aria-label="Review queue">
    <PageHeading title="Knowledge" subtitle={progressLabel(summary) || 'What the system could learn, for you to accept, correct or reject'} />
    <div className="flex flex-wrap items-center gap-3">
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">Show
        <Select aria-label="What to review" className={SELECT} value={tab} onChange={e => choose(e.target.value)}>
          {tabs.map(t => <option key={t.id || 'all'} value={t.id}>{t.label} ({t.count.toLocaleString('en-US')})</option>)}</Select></label>
      <StatusLine tone="error">{error}</StatusLine>
      <StatusLine>{notice}</StatusLine>
    </div>
    <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
    {(published ? piecesQuery : queueQuery).isPending && !readError && <LoadingState>Loading the queue…</LoadingState>}
    {published ? piecesQuery.data && <>
      <p className={META}>Pieces found in the published-content log. Confirm the ones WIA really published; they then inform what the strategist reuses.</p>
      <BatchBar count={selected.length} label="pieces" reason={batchReason} busy={busy} onReason={setBatchReason} actions={[{ label: `Confirm ${selected.length} published`, run: confirmPieces }]} />
      <PublishedList pieces={pieces} selected={selected} busy={busy} onSelect={setSelected} />
    </> : queue && <>
      <BatchBar count={chosen.length} label="audience phrases" reason={batchReason} busy={busy} onReason={setBatchReason}
        actions={[{ label: `Accept ${chosen.length}`, run: () => runBatch('accept') }, { label: `Reject ${chosen.length}`, run: () => runBatch('reject') }]} />
      <ReviewQueueList queue={queue} batchKinds={batchKinds} busy={busy} selected={selected}
        onSelect={(id, on) => setSelected(on ? [...selected, id] : selected.filter(x => x !== id))}
        onDecide={(path, body) => void perform(path, body, body.action === 'reject' ? 'Rejected.' : 'Saved. It is now part of what the system knows.')} />
      {queue.total > PAGE_SIZE && <Pager range={pageLabel(queue, queue.items.length)} hasPrevious={!busy && offset > 0} hasNext={!busy && offset + PAGE_SIZE < queue.total}
        onPrevious={() => setOffset(Math.max(0, offset - PAGE_SIZE))} onNext={() => setOffset(offset + PAGE_SIZE)} />}
    </>}
  </section>;
}
