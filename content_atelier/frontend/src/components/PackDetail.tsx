import React, { useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import type { PackSavedV2, StoredPackV2 } from '../api/types';
import { isApiError, storageRequest } from '../api/client';
import { useApiQuery, useInvalidate } from '../api/query';
import { productionChanged, requestId } from '../utils/production';
import { weekWords } from '../utils/editorialWeeks';
import { plainMessage } from '../utils/plainText';
import { STATE_HINTS, findingText, packFindings, packPlainText } from './packFields';
import { CopyButton, StateChip, packHref } from './packParts';
import { PieceCard, type PackWrite } from './PackPiece';
import { BeforePublishing } from './PackBeforePublishing';
import { PageHeading } from './PageHeading';
import { RemovedMaterialNote } from './BriefEditing';
import { packReason } from './HomeSummary';
import { ActionError, ConflictNotice, useGuardedAction } from './shared/conflict';
import { focusKey } from './shared/a11y';
import { EmptyState, ErrorState, LoadingState } from './shared/states';
import { TAKES } from './studio/GenerationTime';
import { PackScheduling } from './PackScheduling';
import { MarkPublishedButton } from './PiecePublication';

/* The pack's top bar records publication of the selected piece, with a shared dialog also used by calendar items.
   Copy, editing, the pill tabs and content checks retain their existing layout. Pack approval is no longer offered here.
   Content edits take the version's manifest hash: a stale one (409
   `stale_pack`) shows the conflict notice with the person's input kept, and a write while a run is active (409
   `pack_running`) is refused with its reason. An edit makes a new version, which opens in place. */

/** What a pack write did, in a sentence for the live region and the confirmation (6.F6). With the pack, an editor's finding
    kept with a reason says "Kept" and a client quote says "Marked cleared". */
export function packWriteMessage(path: string, method: string, body: Record<string, unknown>, newVersion: boolean,
  pack?: Pick<StoredPackV2, 'findings' | 'pieces' | 'client_quotes'>): string {
  const opened = newVersion ? ' The new version is open.' : '';
  const finding = /\/findings\/([^/]+)\/attest$/.exec(path)?.[1];
  if (finding && pack && packFindings(pack).some(f => f.finding_id === finding && f.source === 'editorial')) return `Kept, with your reason.${opened}`;
  if (/\/clearances$/.test(path) && pack?.client_quotes.some(q => q.quote_id === body.item_id)) return 'Marked cleared.';
  if (method === 'PATCH') return `Saved.${opened}`;
  if (/\/revert$/.test(path)) return `The brief's line is back.${opened}`;
  if (/\/published$/.test(path)) return 'Marked published.';
  if (/\/recorded$/.test(path)) return `The caption and covers are being written from what you said.${opened}`;
  if (/\/clearances$/.test(path)) return 'Marked done.';
  if (/\/attest$/.test(path)) return `Attested.${opened}`;
  if (/\/(?:finish|refinish)$/.test(path)) return `Finishing the pack again.${opened}`;
  if (/\/decision$/.test(path)) return body.decision === 'ready_to_publish' ? 'Marked ready to publish.' : 'Back in review.';
  return `Saved.${opened}`;
}

/** Where focus goes after a pack write (6.F6): the piece's heading for a write to a piece, the item's "Marked done" line, the
    pack's state for a decision or an attestation, else the pack's title. Each key names the version the write made, so the
    old version on screen is never the target. */
export function packWriteTarget(path: string, body: Record<string, unknown>, packId: string): string {
  const piece = /\/pieces\/([^/]+)/.exec(path)?.[1];
  if (piece) return focusKey(`pack:${packId}:piece:${piece}`);
  if (/\/clearances$/.test(path) && typeof body.item_id === 'string') return focusKey(`pack:${packId}:done:${body.item_id}`);
  if (/\/(?:decision|attest)$/.test(path)) return focusKey(`pack:${packId}:ready`);
  return focusKey(`pack:${packId}:title`);
}

const capitalise = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

export type Announce = (text: string, target?: string | null) => void;

/** The pack's writes: each gets a request id kept for an identical retry (idempotent), a refusal while a run is active is
    said in words, and the version a write made opens in place of this one; the result is said and focus moves into it. */
function usePackWrites(pack: StoredPackV2 | undefined, base: string, piece: string, reload: () => Promise<unknown>, announce?: Announce) {
  const navigate = useNavigate();
  const invalidate = useInvalidate();
  const ids = useRef(new Map<string, string>());
  const guard = useGuardedAction(reload);
  const write: PackWrite = (path, method, body) => guard.run(async () => {
    const key = `${method} ${path} ${JSON.stringify(body)}`;
    if (!ids.current.has(key)) ids.current.set(key, requestId());
    let saved: PackSavedV2;
    try {
      saved = await storageRequest<PackSavedV2>(path, method, { ...body, request_id: ids.current.get(key) });
    } catch (failure) {
      // A run is finishing this pack: not a conflict to reload, a refusal to wait out. The input stays in the form.
      if (isApiError(failure) && failure.code === 'pack_running') throw new Error(`${failure.message || 'The pack is being written.'} What you typed is still in the form: save it when it is done.`);
      throw failure;
    }
    ids.current.delete(key);
    productionChanged();
    // The new version first, so the superseded one is never shown as the answer; then every read the write changed.
    const newVersion = !!pack && !!saved.pack_id && saved.pack_id !== pack.pack_id;
    if (newVersion) navigate(packHref(base, saved.pack_id, piece), { replace: true });
    await invalidate('/packs', '/packs/{pack_id}', '/packs/{pack_id}/production', '/weeks/{week_id}/pack-plan');
    const packId = (newVersion ? saved.pack_id : pack?.pack_id) ?? '';
    if (packId) announce?.(packWriteMessage(path, method, body, newVersion, pack), packWriteTarget(path, body, packId));
    return true as const;
  });
  return { ...guard, write };
}

/** The tab list, as the mockup's pill tabs: arrow keys, Home and End move between the pieces (roving focus). */
function PieceTabs({ pack, active, onSelect }: { pack: StoredPackV2; active: string; onSelect: (key: string) => void }) {
  const keys = pack.pieces.map(p => p.key);
  const move = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const current = keys.indexOf(active as typeof keys[number]);
    const next = event.key === 'Home' ? keys[0] : event.key === 'End' ? keys[keys.length - 1]
      : keys[(current + (event.key === 'ArrowRight' ? 1 : -1) + keys.length) % keys.length];
    onSelect(next);
    event.currentTarget.parentElement?.querySelector<HTMLButtonElement>(`#pack-piece-tab-${next}`)?.focus();
  };
  return <div role="tablist" aria-label="Content pack pieces" className="atelier-modal-tabs inline-flex flex-wrap gap-1 rounded-full border border-[#E6E9F0] bg-white p-1 text-[12px]">
    {pack.pieces.map(p => <button key={p.key} type="button" role="tab" id={`pack-piece-tab-${p.key}`} aria-selected={active === p.key}
      aria-controls={`pack-piece-panel-${p.key}`} tabIndex={active === p.key ? 0 : -1} onClick={() => onSelect(p.key)} onKeyDown={move}
      className={`rounded-full px-4 py-2 font-medium transition-colors ${active === p.key ? 'bg-[#5070FF] text-white' : 'text-[#667184] hover:text-[#34445F]'}`}>
      {p.label}
      {p.origin === 'not_written' && <span className="sr-only">, not written</span>}
      {p.published.length > 0 && <><span className="ml-1.5" aria-hidden="true">✓</span><span className="sr-only">, published</span></>}
    </button>)}
  </div>;
}

export function PackDetail({ packId, base, announce }: { packId: string; base: string; announce?: Announce }) {
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const busyStates = (state?: string) => state === 'finishing' || state === 'waiting';
  const packQuery = useApiQuery('/packs/{pack_id}', { path: { pack_id: packId } }, { refetchInterval: data => busyStates(data?.state) ? 8_000 : false });
  const pack = packQuery.data;
  const v2 = !!pack && pack.contract_version === 'content_pack_v2' && Array.isArray(pack.pieces);
  const requested = search.get('piece') ?? '';
  const active = v2 && pack.pieces.some(p => p.key === requested) ? requested : v2 ? pack.pieces[0]?.key ?? '' : '';
  const select = (key: string) => setSearch(prev => { const next = new URLSearchParams(prev); next.set('piece', key); return next; }, { replace: true });
  // Reload after a conflict: the pack again, and the newest version of its lineage when this one was superseded.
  const reload = async () => {
    const fresh = await packQuery.refetch();
    const versions = fresh.data?.versions ?? [];
    const latest = versions[versions.length - 1]?.pack_id;
    if (latest && latest !== packId) navigate(packHref(base, latest, active), { replace: true });
  };
  const { write, busy, error, conflict, reloadLatest, clear } = usePackWrites(pack, base, active, reload, announce);
  const back = <Link to={base} className="inline-flex items-center text-[12px] font-medium text-[#5070FF] hover:underline"><span aria-hidden="true">←&nbsp;</span>Content packs</Link>;

  if (!pack) return <section className="space-y-4">
    {back}
    {packQuery.error ? <ErrorState message={packQuery.error.message} onRetry={() => void packQuery.refetch()} /> : <LoadingState>Loading the content pack…</LoadingState>}
  </section>;
  if (!v2) return <section className="space-y-4">
    {back}
    <p role="status" className="rounded-xl border border-dashed p-4 text-sm">This pack was made in an earlier format, which this screen does not show.</p>
  </section>;

  const latest = pack.versions[pack.versions.length - 1]?.pack_id;
  const selectedPiece = pack.pieces.find(piece => piece.key === active);
  // The removal's note is shown on its own line; the same sentence among the blockers is not said twice.
  const removedNote = pack.removed_material?.note?.trim();
  const blockers = pack.ready_blockers.filter(b => !removedNote || (b.trim() !== removedNote && findingText(b).trim() !== removedNote)).map(b => plainMessage(findingText(b)));
  const stopped = blockers.length > 0 || !!pack.removed_material;
  const finished = pack.state === 'in_review' || pack.state === 'ready_to_publish';
  const status = finished ? 'Mark each piece published or sent when it goes out.' : pack.state === 'waiting' && pack.state_reason ? `Waiting: ${packReason(pack.state_reason)}.` : STATE_HINTS[pack.state];
  return <section className="space-y-5 text-[13px] text-[#34445F]" aria-label="Content pack" data-pack-id={pack.pack_id}>
    <PageHeading title={pack.title} subtitle={[pack.pillar, capitalise(weekWords(pack.week_id))].filter(Boolean).join(' · ')} actions={<>
      <CopyButton text={packPlainText(pack)} label="the whole pack, every piece in full"
        className="inline-flex h-10 items-center rounded-full border border-[#E6E9F0] bg-white px-4 text-[12px] font-medium text-[#34445F] hover:bg-[#F7F8FB] cursor-pointer">Copy all</CopyButton>
      {selectedPiece && <MarkPublishedButton key={`${pack.pack_id}:${selectedPiece.key}`} pack={pack} piece={selectedPiece} busy={busy}
        className="atelier-page-primary inline-flex h-10 items-center gap-2 rounded-full px-5 text-[12px] disabled:opacity-40 disabled:cursor-not-allowed"
        onSaved={() => announce?.(`${selectedPiece.label} marked ${selectedPiece.channel === 'email' ? 'sent' : 'published'}.`, packWriteTarget(`/pieces/${selectedPiece.key}`, {}, pack.pack_id))} />}
    </>} />
    <span tabIndex={-1} data-focus-key={`pack:${pack.pack_id}:title`} className="sr-only">{pack.title}</span>
    <div className="flex flex-wrap items-center justify-between gap-3">
      {back}
      <div className="flex flex-wrap items-center gap-3 text-[12px] text-[#7A8496]">
        {finished ? <span className="rounded-full bg-[#F1F3F7] px-3 py-1 text-[11px] text-[#667184]">Generated</span> : <StateChip state={pack.state} />}
        <span tabIndex={-1} data-focus-key={`pack:${pack.pack_id}:ready`}>{status}</span>
      </div>
    </div>
    {pack.state === 'superseded' && latest && latest !== pack.pack_id && <p role="status" className="rounded-xl bg-slate-100 p-3 text-sm">
      This is an earlier version. <Link className="underline" to={packHref(base, latest, active)}>Open the newest version</Link></p>}
    {finished && stopped && <div role="status" aria-label="Content checks" className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-[13px] text-amber-900">
      <p className="font-medium">Content checks to review:</p>
      {/* Built on material removed at a client's request (6.B12): the removal's note, with its day, first. */}
      <RemovedMaterialNote removed={pack.removed_material} />
      {blockers.length > 0 && <ul className="mt-1 ml-5 list-disc space-y-1">{blockers.map((b, i) => <li key={i}>{b}</li>)}</ul>}
    </div>}
    <ConflictNotice conflict={conflict} onReload={() => void reloadLatest()} onDismiss={clear} />
    <ActionError message={error} />
    {pack.pieces.length ? <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PieceTabs pack={pack} active={active} onSelect={select} />
        <PackScheduling pack={pack} active={active} busy={busy} />
      </div>
      {pack.pieces.map(p => <PieceCard key={p.key} piece={p} pack={pack} active={p.key === active} busy={busy} write={write} />)}
    </div> : <EmptyState tone="dashed">The email, the carousel and the three Reels appear here when the pack is written.{pack.state === 'finishing' ? ` This takes ${TAKES.pack}.` : ''}</EmptyState>}
    <BeforePublishing pack={pack} busy={busy} write={write} />
  </section>;
}
