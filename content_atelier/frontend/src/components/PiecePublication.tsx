import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check } from 'lucide-react';
import type { PackPieceV2, PackPublishedV2, StoredPackV2 } from '../api/types';
import { storageRequest } from '../api/client';
import { useApiQuery, useInvalidate } from '../api/query';
import { productionChanged, requestId } from '../utils/production';
import { Dialog } from './AdminParts';
import { DateInput } from './DateInput';
import { Select } from './ThemedSelect';
import { CHANNELS, defaultChannel, pieceBodyText, pieceTitle, publishedRequest, safeUrl, today, type PublishChannel, type PublishedForm } from './packFields';
import { button, input, primary, shortDate } from './packParts';
import { ActionError, ConflictNotice, useGuardedAction } from './shared/conflict';
import { ErrorState, LoadingState } from './shared/states';

/** Manual recording is independent of the former whole-pack approval action. */
export function publicationUnavailable(pack: StoredPackV2, piece: PackPieceV2): string {
  if (pack.state === 'superseded') return 'Open the newest version to record publication.';
  if (pack.run_active || pack.state === 'finishing' || pack.state === 'waiting') return 'Wait for the pack to finish.';
  if (!pack.manifest_hash || piece.origin === 'not_written' || !piece.content) return 'This piece has not been written yet.';
  if (!pack.can_mark_published) return 'Your role cannot record publication.';
  return '';
}

export function PublicationStatus({ piece }: { piece: PackPieceV2 }) {
  if (!piece.published.length) return null;
  return <ul aria-label={`${piece.label}: published`} className="space-y-2">{piece.published.map(mark => <li key={mark.content_id} className="rounded-xl bg-emerald-50 px-4 py-3 text-[12px] text-emerald-900">
    <p className="font-medium"><Check className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" />{piece.channel === 'email' ? 'Sent' : 'Published'} {shortDate(mark.published_on)} · {CHANNELS.find(([value]) => value === mark.channel)?.[1] ?? mark.channel}</p>
    <p className="mt-1">Manually marked · Not verified on platform</p>
    {safeUrl(mark.url) && <a className="mt-1 inline-block underline" href={safeUrl(mark.url)!} target="_blank" rel="noreferrer">Open the published piece</a>}
  </li>)}</ul>;
}

export function MarkPublishedButton({ pack, piece, busy = false, className = primary, onSaved }: {
  pack: StoredPackV2; piece: PackPieceV2; busy?: boolean; className?: string; onSaved?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const recorded = piece.published.length > 0;
  const reason = publicationUnavailable(pack, piece);
  return <>
    <button type="button" className={`${className} inline-flex items-center gap-2`} aria-haspopup="dialog"
      disabled={busy || (!recorded && !!reason)} title={!recorded && reason ? reason : undefined} onClick={() => setOpen(true)}>
      <Check aria-hidden="true" className="h-3.5 w-3.5" />{recorded ? `${piece.channel === 'email' ? 'Sent' : 'Published'} · View details` : 'Mark as Published'}
    </button>
    {open && createPortal(<PublicationDialog key={`${pack.pack_id}:${piece.key}`} pack={pack} piece={piece} onClose={() => setOpen(false)} onSaved={onSaved} />, document.body)}
  </>;
}

/** Both entry points use the same form and persisted publication endpoint. No provider result is inferred here. */
export function PublicationDialog({ pack, piece, onClose, onSaved }: {
  pack: StoredPackV2; piece: PackPieceV2; onClose: () => void; onSaved?: () => void;
}) {
  const [form, setForm] = useState<PublishedForm>(() => ({ published_on: today(), channel: defaultChannel(piece), final_text: pieceBodyText(piece), url: '' }));
  const [validation, setValidation] = useState('');
  const ids = useRef(new Map<string, string>());
  const invalidate = useInvalidate();
  const guard = useGuardedAction(() => invalidate('/packs/{pack_id}'));
  const recorded = piece.published.length > 0;
  const reason = publicationUnavailable(pack, piece);
  const sent = piece.channel === 'email';
  const close = () => { if (!guard.busy) onClose(); };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (guard.busy || reason) return;
    const request = publishedRequest(form);
    if ('error' in request) { setValidation(request.error); return; }
    setValidation('');
    await guard.run(async () => {
      const fingerprint = JSON.stringify(request.body);
      if (!ids.current.has(fingerprint)) ids.current.set(fingerprint, requestId());
      await storageRequest<PackPublishedV2>(`/packs/${pack.pack_id}/pieces/${piece.key}/published`, 'POST', { ...request.body, request_id: ids.current.get(fingerprint) });
      ids.current.delete(fingerprint);
      productionChanged();
      await invalidate('/packs', '/packs/{pack_id}', '/packs/{pack_id}/production', '/weeks/{week_id}/pack-plan', '/calendar');
      onSaved?.();
      onClose();
    });
  };
  return <Dialog title={recorded ? `${piece.label} · Publication details` : `Mark ${piece.label} as ${sent ? 'sent' : 'published'}`} onClose={close}>
    <p className="font-medium text-[#173354]">{pieceTitle(piece)}</p>
    {recorded ? <><PublicationStatus piece={piece} /><button type="button" className={button} onClick={close}>Done</button></> : <>
      <p className="text-[12px] text-[#667184]">Record what already went out. This marks only {piece.label}; it does not send or publish content.</p>
      <form onSubmit={event => void submit(event)} aria-label={`Mark ${piece.label} ${sent ? 'sent' : 'published'}`} className="space-y-4">
        <fieldset disabled={guard.busy || !!reason} className="space-y-4 disabled:opacity-60">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-[12px]">{sent ? 'Sent on' : 'Published on'}<DateInput required max={today()} className={input} value={form.published_on} onChange={event => setForm({ ...form, published_on: event.target.value })} /></label>
            <label className="block text-[12px]">Channel<Select className={input} value={form.channel} onChange={event => setForm({ ...form, channel: event.target.value as PublishChannel })}>
              {CHANNELS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </Select></label>
          </div>
          <label className="block text-[12px]">{sent ? 'Link to the email or campaign (optional)' : 'Link to the post (optional)'}<input type="text" inputMode="url" className={input} placeholder="https://" value={form.url} onChange={event => setForm({ ...form, url: event.target.value })} /></label>
          <details className="rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-3">
            <summary className="cursor-pointer text-[12px] font-medium">Review final {sent ? 'sent' : 'published'} text</summary>
            <label className="mt-3 block text-[12px]">The text as it was {sent ? 'sent' : 'published'}<textarea className={input} rows={8} value={form.final_text} onChange={event => setForm({ ...form, final_text: event.target.value })} /></label>
          </details>
          <p className="text-[12px] text-[#667184]">Saved as a manual mark. This does not verify publication on Instagram or GHL.</p>
        </fieldset>
        {reason && <p role="status" className="text-[12px] text-amber-800">{reason}</p>}
        <ActionError message={validation || guard.error} />
        <ConflictNotice conflict={guard.conflict} onReload={() => void guard.reloadLatest()} onDismiss={guard.clear} />
        <div className="flex flex-wrap justify-end gap-2"><button type="button" className={button} disabled={guard.busy} onClick={close}>Cancel</button>
          <button type="submit" className={primary} disabled={guard.busy || !!reason}>{guard.busy ? 'Saving…' : sent ? 'Confirm Sent' : 'Confirm Published'}</button></div>
      </form>
    </>}
  </Dialog>;
}

/** Refresh the linked pack before a calendar action, including its permissions and existing publication marks. */
export function CalendarPublication({ packId, pieceKey, onClose, onSaved }: {
  packId: string; pieceKey: string; onClose: () => void; onSaved: () => void;
}) {
  const query = useApiQuery('/packs/{pack_id}', { path: { pack_id: packId } });
  const piece = query.data?.pieces.find(item => item.key === pieceKey);
  if (query.data && piece) return <PublicationDialog key={`${packId}:${pieceKey}`} pack={query.data} piece={piece} onClose={onClose} onSaved={onSaved} />;
  return <Dialog title="Publication record" onClose={onClose}>{query.error ? <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />
    : query.data ? <p role="status">This scheduled piece is no longer available. Open its content pack to review the latest version.</p> : <LoadingState>Loading the scheduled piece…</LoadingState>}</Dialog>;
}
