import React from 'react';
import { Link } from 'react-router-dom';
import { Check } from 'lucide-react';
import type { PackSummaryV2, StoredBrief } from '../../api/types';
import { paths } from '../../app/routes';
import { briefTitle } from '../BriefReaderV4';
import { plainBlockers } from '../BriefReaderV2';
import { handoverNote, isV4Brief } from '../PackHandover';
import { contentTypeWords } from './CardRationale';
import { TAKES, TimeNote } from './GenerationTime';
import { reelKindWords } from '../packFields';
import { CARD, DARK, PANEL, PANEL_HEADING, Pill, QUIET, cardDay, offerName } from './parts';

/* A brief card in the 20 October mockup's form (src/mock EditorialHub with BriefingOverview): the serif title and its status,
   the date and offer, the "Content brief" panel (central point, strategic purpose, audience and reason to care, WIA
   perspective, supporting example, narrative outline, format and creative approach, CTA and essential boundaries), "← View
   source angle", "Read full brief" (the whole Gate 2 reader and editor) and "Approve & generate pack", which is offered only
   when nothing blocks approval; otherwise one plain line says what is left. */

type Loose = Record<string, unknown> & { [key: string]: any }; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The brief's body, whatever its contract (v2, v3 and v4 share the sections the card shows; v1 has none of them). */
const bodyOf = (brief: StoredBrief): Loose | null => {
  const document = brief.content_body.document as { body?: Loose } | undefined;
  return document?.body ?? null;
};
const headerOf = (brief: StoredBrief): Loose | null => (brief.content_body.document as { header?: Loose } | undefined)?.header ?? null;

/** The text a brief is searched by and the offer it is filtered by. */
export function briefSearchText(brief: StoredBrief): string {
  const b = bodyOf(brief);
  return [briefTitle(brief), b?.central_point, b?.approved_angle?.core_perspective, b?.audience?.who, b?.wia_perspective, b?.supporting_example?.scene].filter(Boolean).join(' ');
}
export function briefOfferText(brief: StoredBrief): string {
  const b = bodyOf(brief), h = headerOf(brief);
  return [h?.cta?.track, h?.cta?.offer_connection, b?.cta?.track, b?.cta?.offer_connection, b?.cta?.action].filter(Boolean).join(' ');
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <li><strong className="font-semibold text-[#34445F]">{label}:</strong><div className="mt-1">{children}</div></li>;
}

/** The mockup's "Content brief" panel over a stored brief. */
export function BriefOverview({ brief }: { brief: StoredBrief }) {
  const b = bodyOf(brief);
  if (!b) return null;
  const sp = b.strategic_purpose ?? {}, ex = b.supporting_example ?? {}, outline = b.narrative_outline ?? {}, plan = b.format_plan ?? {};
  const central = b.central_point ?? b.sharpened_point?.text ?? b.approved_angle?.core_perspective;
  const cta = b.cta ?? headerOf(brief)?.cta ?? {};
  const formats: [string, string][] = [
    ...(plan.email?.job ? [['Email', plan.email.job] as [string, string]] : []),
    // A Reel from the Round 2 writer is listed by its own premise; an earlier one by its job.
    ...((plan.reels ?? []) as Loose[]).map((r, i) => {
      const kind = reelKindWords(r.kind, r.production);
      return [`Reel ${i + 1}${kind ? ` (${kind})` : ''}`, r.premise || r.job] as [string, string];
    }),
    ...(plan.carousel?.job ? [['Carousel', plan.carousel.job] as [string, string]] : []),
  ].filter(([, job]) => !!job);
  const hook = (outline.hooks ?? [])[0]?.text;
  return <section aria-label="Content brief overview" className={PANEL}>
    <h4 className={`mb-3 ${PANEL_HEADING}`}>Content brief</h4>
    <ul className="space-y-3 pl-4 list-disc marker:text-[#A38B61] text-[12px] leading-relaxed text-[#667184] [&>li+li]:border-t [&>li+li]:border-[#E0DFE2] [&>li+li]:pt-3">
      {central && <Field label="Central point">{central}</Field>}
      <Field label="Strategic purpose"><span className="font-semibold text-[#5070FF]">{sp.pillar}</span>{sp.content_type ? <span> · {contentTypeWords(sp.content_type)}</span> : null}
        <p className="mt-1">{sp.desired_response ? `${sp.why_now ?? ''} The desired response: ${sp.desired_response}`.trim() : sp.why_now}</p></Field>
      {b.audience && <Field label="Audience and reason to care"><p>{b.audience.who}</p>{b.audience.reason_to_care && <p className="mt-1">{b.audience.reason_to_care}</p>}</Field>}
      {b.wia_perspective && <Field label="WIA perspective"><p className="whitespace-pre-wrap">{b.wia_perspective}</p></Field>}
      {ex.scene && <Field label="Supporting example"><p>{ex.scene}</p>
        {!!ex.timestamps?.length && <ul className="mt-1 list-disc pl-4 space-y-1">{(ex.timestamps as string[]).map((t, i) => <li key={i}>{t}</li>)}</ul>}</Field>}
      {(hook || outline.main_point) && <Field label="Narrative outline"><ul className="list-disc pl-4 space-y-1">
        {hook && <li><strong className="font-semibold text-[#34445F]">Hook:</strong> {hook}</li>}
        {!!outline.problems_desires_symptoms?.length && <li><strong className="font-semibold text-[#34445F]">Problems, desires, symptoms:</strong> {(outline.problems_desires_symptoms as string[]).join(' ')}</li>}
        {outline.main_point && <li><strong className="font-semibold text-[#34445F]">Main point:</strong> {outline.main_point}</li>}
        {outline.transformation && <li><strong className="font-semibold text-[#34445F]">Transformation:</strong> {outline.transformation}</li>}
        {outline.cta && <li><strong className="font-semibold text-[#34445F]">CTA:</strong> {outline.cta}</li>}
      </ul></Field>}
      {formats.length > 0 && <Field label="Format and creative approach"><ul className="list-disc pl-4 space-y-1">{formats.map(([name, job]) => <li key={name}>
        <strong className="font-semibold text-[#34445F]">{name}:</strong> {job}</li>)}</ul></Field>}
      <Field label="CTA and essential boundaries"><p>{cta.action || 'No explicit ask'}{cta.chosen_by && cta.chosen_by !== 'person' ? ' (proposed; confirm it in the full brief)' : ''}</p>
        {b.cta_why && <p className="mt-1">{b.cta_why}</p>}</Field>
    </ul>
  </section>;
}

/** What a brief card shows: the content type, the central point in a few lines and the pieces the pack will hold. The whole
    brief is one click away ("Read full brief"). */
export function BriefSummary({ brief }: { brief: StoredBrief }) {
  const b = bodyOf(brief);
  if (!b) return null;
  const sp = b.strategic_purpose ?? {}, plan = b.format_plan ?? {};
  const central = b.central_point ?? b.sharpened_point?.text ?? b.approved_angle?.core_perspective;
  const reels = ((plan.reels ?? []) as Loose[]).length;
  const pieces = [plan.email?.job ? '1 Email' : '', plan.carousel?.job ? '1 Carousel' : '', reels ? `${reels} ${reels === 1 ? 'Reel' : 'Reels'}` : ''].filter(Boolean);
  return <div className="space-y-2.5 text-[12.5px] leading-relaxed text-[#4F5B6E]">
    {sp.pillar && <p className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.12em]">
      <span className="rounded-md bg-[#EFF3FF] px-2 py-0.5 text-[#5070FF]">{sp.pillar}</span>
      {sp.content_type && <span className="text-[#A38B61]">{contentTypeWords(sp.content_type)}</span>}</p>}
    {central && <p className="line-clamp-3">{central}</p>}
    {pieces.length > 0 && <p className="text-[11px] text-[#7A8496]">{pieces.join(' · ')}</p>}
  </div>;
}

export const briefCardFocusKey = (briefId: string) => `brief-card:${briefId}`;

/** What stops approval, in one plain line (the server's named blockers, else its messages made plain). */
export function whatIsLeft(brief: StoredBrief): string {
  const items = brief.blocker_items?.map(i => i.title) ?? plainBlockers(brief.blockers);
  if (!items.length) return '';
  return items.length === 1 ? `Before approval: ${items[0].replace(/\.$/, '')}.` : `Before approval: ${items[0].replace(/\.$/, '')}, and ${items.length - 1} more.`;
}

export function BriefCard({ brief, week, pack, packMaking = false, packsOn, busy, onApprove, fullBriefHref }: {
  brief: StoredBrief; week: string; pack?: PackSummaryV2; packMaking?: boolean; packsOn: boolean; busy: boolean; onApprove: () => void; fullBriefHref: string;
}) {
  const pending = brief.approval_status === 'pending', approved = brief.approval_status === 'approved';
  const left = pending && !brief.can_approve ? whatIsLeft(brief) : '';
  const offer = offerName(briefOfferText(brief));
  const createsPack = packsOn && isV4Brief(brief);
  return <article id={`brief-${brief.brief_id}`} className={CARD}>
    <div className="flex items-start justify-between gap-3">
      <h3 tabIndex={-1} data-focus-key={briefCardFocusKey(brief.brief_id)} className="min-w-0 font-editorial text-[23px] leading-tight text-[#1B2433]">{briefTitle(brief)}</h3>
      <Pill tone={approved ? 'approved' : pending ? 'waiting' : 'quiet'}>{approved ? 'Approved' : pending ? 'Awaiting approval' : 'Not approved'}</Pill>
    </div>
    <p className="-mt-2 text-[11px] text-[#9199A7]">{cardDay(brief.created_at)}{offer ? ` · ${offer}` : ''}</p>
    <BriefSummary brief={brief} />
    {left && <p className="text-[11px] text-amber-800">{left} <Link className="font-medium text-[#5070FF]" to={fullBriefHref}>Read full brief <span aria-hidden="true">→</span></Link></p>}
    <div className="mt-auto pt-3 border-t border-[#EEF0F4] flex flex-wrap items-center gap-2">
      <Link to={fullBriefHref} className={QUIET} aria-label={`Read full brief: ${briefTitle(brief)}`}>Read full brief</Link>
      {approved && (pack ? <Link className="ml-auto text-[12px] font-semibold text-[#5070FF] hover:underline" to={paths.studioPack(pack.pack_id)}>Open pack <span aria-hidden="true">→</span></Link>
        : packMaking ? <TimeNote className="ml-auto">Pack being made · {TAKES.pack}</TimeNote>
        : <span className="ml-auto text-[11px] text-[#9199A7]">{createsPack ? 'No pack yet' : handoverNote(brief, packsOn)}</span>)}
      {pending && brief.can_review && <button type="button" className={`ml-auto ${DARK}`} disabled={busy || !!left || !brief.can_approve} onClick={onApprove}
        title={!brief.can_approve && !left ? 'Approving a brief needs the approver role.' : undefined}>
        <Check aria-hidden="true" className="w-3 h-3" />{createsPack ? 'Approve & generate pack' : 'Approve brief'}</button>}
      {pending && brief.can_review && createsPack && brief.can_approve && <TimeNote className="basis-full justify-end">The pack takes {TAKES.pack} to make.</TimeNote>}
    </div>
  </article>;
}
