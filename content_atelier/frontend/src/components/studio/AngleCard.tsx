import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check } from 'lucide-react';
import type { Card, PackSummaryV2, RosterEntry, StoredAngle, StoredBrief } from '../../api/types';
import { useApiQuery } from '../../api/query';
import { useOneClick } from '../../utils/workspace';
import { paths } from '../../app/routes';
import { blockingFlags, cardDispositionBody, developBlocker, emptyForm, DISPOSITIONS, REASON_CODES, type DispositionForm } from '../CardReview';
import { useModalBehavior } from '../useModalBehavior';
import { CardSummary } from './CardRationale';
import { TAKES, TimeNote } from './GenerationTime';
import { CARD, DARK, Pill, QUIET, cardDay, offerName, personName, type PillTone } from './parts';
export { personName };
import { cardGroup } from './studioWeek';

/* An angle card in the 20 October mockup's form (src/mock EditorialHub): the serif title and its status, the date and offer,
   the topic and editorial rationale, the folded source moment, and two buttons: "Review angle" (the full card screen in a
   dialog: every edit, reframe, check, flag, account memory, rubric and verify-before-publishing) and "Approve & create brief"
   (the develop decision, with the confirmations the card screen requires: every verify-before-publishing item, each blocking
   evidence flag with a note, and an overlap with another card). */

type Perform = (path: string, method?: string, body?: unknown, options?: { target?: string; message?: string }) => Promise<boolean>;

const reasonWords = (code: string | null | undefined) => code ? REASON_CODES.find(([value]) => value === code)?.[1] ?? code.replaceAll('_', ' ') : '';

/** A card's status in the mockup's words, with its pill tone. */
export function cardPill(a: StoredAngle): { tone: PillTone; text: string } {
  const group = cardGroup(a);
  if (group === 'approved') return { tone: 'approved', text: 'Approved' };
  if (group === 'waiting') return { tone: 'waiting', text: 'Awaiting approval' };
  if (a.hold) return { tone: 'quiet', text: `Held until ${cardDay(a.hold.until)}` };
  const d = a.disposition?.disposition;
  if (a.approval_status === 'rejected') return { tone: 'quiet', text: d === 'internal' ? 'Kept for internal use' : d === 'skip' ? 'Skipped' : 'Not taken forward' };
  return { tone: 'quiet', text: 'Folded into a better-ranked idea' };
}

/** The focus key of a card in the grid: after a decision from the card, focus returns to its title wherever it moved. */
export const cardFocusKey = (angleId: string) => `card:${angleId}`;

/** A developed card whose brief has not arrived: being written, or stopped, which leads to the card's screen and its retry. */
function BriefPending({ week, angleId }: { week: string; angleId: string }) {
  const research = useApiQuery('/angles/{angle_id}/research', { path: { angle_id: angleId } }, {
    refetchInterval: data => data?.status === 'failed' ? 30_000 : 8_000,
  });
  if (research.data?.status === 'failed') return <Link className="ml-auto text-[12px] font-semibold text-red-700 hover:underline" to={paths.angle(week, angleId)}>The brief stopped: see why <span aria-hidden="true">→</span></Link>;
  return <TimeNote className="ml-auto">Brief being written · {TAKES.brief}</TimeNote>;
}

/** Where a developed card went next, as one link in its footer: its pack, or its brief. */
function Onward({ week, angleId, brief, pack }: { week: string; angleId: string; brief?: StoredBrief; pack?: PackSummaryV2 }) {
  const link = 'ml-auto text-[12px] font-semibold text-[#5070FF] hover:underline';
  if (pack) return <Link className={link} to={paths.studioPack(pack.pack_id)}>Open pack <span aria-hidden="true">→</span></Link>;
  if (!brief) return <BriefPending week={week} angleId={angleId} />;
  const to = brief.approval_status === 'approved' || brief.approval_status === 'rejected' ? paths.brief(brief.brief_id)
    : `${paths.briefs}?week=${encodeURIComponent(week)}#brief-${brief.brief_id}`;
  return <Link className={link} to={to}>Open brief <span aria-hidden="true">→</span></Link>;
}

/** The develop decision's confirmations, when the card has any: the same rules as the card screen (cardDispositionBody). */
function ApproveDialog({ angle, card, onClose, onApprove, busy }: { angle: StoredAngle; card: Card; onClose: () => void; busy: boolean;
  onApprove: (form: DispositionForm) => string | null }) {
  const modalRef = useModalBehavior(onClose);
  const [form, setForm] = useState<DispositionForm>(emptyForm);
  const [error, setError] = useState('');
  const ledger = angle.content_body.ledger || null;
  const blocking = blockingFlags(ledger);
  const overlap = (angle.matching_result?.current_batch_flags || []).length > 0;
  const tick = (id: string, on: boolean) => setForm({ ...form, verified: on ? [...form.verified, id] : form.verified.filter(x => x !== id) });
  const field = 'block w-full rounded-lg border border-[#E6E9F0] p-2 mt-1 text-[12px]';
  return <div data-lenis-prevent className="atelier-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6">
    <div ref={modalRef} role="dialog" aria-modal="true" aria-label={`Approve and create the brief: ${card.title}`} tabIndex={-1} onClick={e => e.stopPropagation()}
      className="atelier-modal w-full max-w-lg max-h-[92dvh] flex flex-col overflow-hidden rounded-2xl border bg-white">
      <div className="px-6 py-4 border-b border-[#E6E9F0] bg-white"><h2 className="font-editorial text-xl text-[#1B2433]">Approve & create brief</h2>
        <p className="mt-1 text-[12px] text-[#667184]">{card.title}</p></div>
      <div className="atelier-modal-scroll min-h-0 flex-1 overflow-y-auto p-6 space-y-4 text-[12px] text-[#34445F]">
        {card.verify_before_publishing.length > 0 && <fieldset className="rounded-xl bg-amber-50 p-3 space-y-2"><legend className="font-semibold px-1">Verify before publishing</legend>
          <p className="text-[#667184]">Tick each one once you have checked it.</p>
          {card.verify_before_publishing.map(v => <label key={v} className="flex gap-2"><input type="checkbox" checked={form.verified.includes(v)} onChange={e => tick(v, e.target.checked)} />{v}</label>)}</fieldset>}
        {blocking.length > 0 && <fieldset className="rounded-xl bg-red-50 p-3 space-y-2"><legend className="font-semibold px-1">Check against the call</legend>
          {blocking.map(b => <label key={b.id} className="flex gap-2"><input type="checkbox" checked={form.verified.includes(b.id)} onChange={e => tick(b.id, e.target.checked)} />{b.message}</label>)}</fieldset>}
        {overlap && <label className="flex gap-2"><input type="checkbox" checked={form.overlap_acknowledged} onChange={e => setForm({ ...form, overlap_acknowledged: e.target.checked })} />
          This overlaps another card this week; my note says how it differs.</label>}
        {(blocking.length > 0 || overlap) && <label className="block">Note: how you checked it{overlap ? ', and how it differs' : ''}<textarea className={field} rows={3} value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} /></label>}
        <label className="flex gap-2"><input type="checkbox" checked={form.decide_in_development} onChange={e => setForm({ ...form, decide_in_development: e.target.checked })} />Decide the CTA when the brief is written</label>
        {!form.decide_in_development && <label className="block">CTA<input className={field} value={form.cta} onChange={e => setForm({ ...form, cta: e.target.value })} /></label>}
        {error && <p role="alert" className="text-red-800">{error}</p>}
      </div>
      <div className="px-6 py-3.5 border-t border-[#E6E9F0] flex justify-end gap-2">
        <button type="button" className={QUIET} onClick={onClose}>Cancel</button>
        <button type="button" className={DARK} disabled={busy} onClick={() => setError(onApprove(form) ?? '')}><Check aria-hidden="true" className="w-3 h-3" />Approve & create brief</button>
      </div>
    </div>
  </div>;
}

/** Whether developing the card asks for confirmations first. */
export const needsConfirmation = (a: StoredAngle, card: Card) =>
  card.verify_before_publishing.length > 0 || blockingFlags(a.content_body.ledger).length > 0 || (a.matching_result?.current_batch_flags || []).length > 0;

export function AngleCard({ angle: a, card, week, roster, brief, pack, canDecide, busy, perform, onReview, compact = false }: {
  angle: StoredAngle; card: Card; week: string; roster: RosterEntry[]; brief?: StoredBrief; pack?: PackSummaryV2; canDecide: boolean; busy: boolean;
  perform: Perform; onReview: () => void; compact?: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  const group = cardGroup(a);
  const pill = cardPill(a);
  const waiting = group === 'waiting';
  const oneClick = useOneClick();
  const blocker = waiting ? developBlocker(a, card, oneClick) : null;
  const offer = offerName(card.offer_fit?.offer ?? card.offer_connection);
  const approve = (form: DispositionForm): string | null => {
    const result = cardDispositionBody(form, card, a.content_hash, (a.matching_result?.current_batch_flags || []).length > 0, undefined, a.content_body.ledger || null, null, oneClick);
    if ('error' in result) return result.error;
    // The dialog closes either way: a refusal or a conflict is shown on the page, above the cards.
    void perform(`/angles/${a.angle_id}/decision`, 'POST', result.body, { target: cardFocusKey(a.angle_id), message: `Approved. Its brief is being written, which takes ${TAKES.brief}.` })
      .then(() => setConfirming(false));
    return null;
  };
  const decided = a.disposition && group !== 'waiting' && group !== 'approved'
    ? `${DISPOSITIONS.find(d => d.value === a.disposition!.disposition)?.label ?? 'Decided'}${a.disposition.reason_code ? ` · ${reasonWords(a.disposition.reason_code)}` : ''}` : '';
  return <article id={`card-${a.angle_id}`} data-angle-card={a.angle_id} className={CARD}>
    <div className="flex items-start justify-between gap-3">
      <h3 tabIndex={-1} data-focus-key={cardFocusKey(a.angle_id)} className={`min-w-0 font-editorial ${compact ? 'text-[19px]' : 'text-[23px]'} leading-tight text-[#1B2433]`}>{card.title}</h3>
      <Pill tone={pill.tone}>{pill.text}</Pill>
    </div>
    <p className="-mt-2 text-[11px] text-[#9199A7]">{cardDay(a.first_generated_at)}{offer ? ` · ${offer}` : ''}</p>
    {decided && <p className="-mt-2 text-[11px] text-[#667184]">{decided}</p>}
    {!compact && <CardSummary card={card} />}
    {blocker && canDecide && <p className="text-[11px] text-amber-800">{blocker}</p>}
    <div className="mt-auto pt-3 border-t border-[#EEF0F4] flex flex-wrap items-center gap-2">
      <button type="button" onClick={onReview} className={QUIET} aria-label={`Review angle: ${card.title}`}>Review angle</button>
      {group === 'approved' && <Onward week={week} angleId={a.angle_id} brief={brief} pack={pack} />}
      {waiting && canDecide && <button type="button" className={`ml-auto ${DARK}`} disabled={busy || !!blocker}
        onClick={() => !oneClick && needsConfirmation(a, card) ? setConfirming(true) : approve(emptyForm())}><Check aria-hidden="true" className="w-3 h-3" />Approve & create brief</button>}
      {waiting && canDecide && !blocker && <TimeNote className="basis-full justify-end">The brief takes {TAKES.brief} to write.</TimeNote>}
    </div>
    {confirming && <ApproveDialog angle={a} card={card} busy={busy} onClose={() => setConfirming(false)} onApprove={approve} />}
  </article>;
}

