import React from 'react';
import type { Card } from '../../api/types';
import { CTA_SLOTS } from '../cardFields';
import { PANEL, PANEL_HEADING, PANEL_LIST, sentences } from './parts';

/* A card's "Topic & editorial rationale", as the 20 October mockup's angle card shows it (src/mock AngleRationale): content
   pillar and type with the point, audience, why this matters, WIA's expertise or process, the evidence in the referenced
   call, and the editorial guardrail with the next step. Only plain words: the strategist's internal fields (what the point is
   about, the surprise test, the reader fit, the belief reference, why it was chosen, the rank) are under Details in the review
   dialog. */

const words = (s: string) => s.replaceAll('_', ' ');
const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
/** A content type as WIA names it. */
export const CONTENT_TYPE_WORDS: Record<string, string> = {
  polarizing_opinion: 'Polarizing opinion', founder_forward: 'Founder-forward', campaign_breakdown: 'Campaign breakdown', trend: 'Trend',
  uvp: 'UVP', lightbulb_moment: 'Lightbulb moment', process_or_framework: 'Process or framework', behind_the_scenes: 'Behind the scenes',
  education: 'Education', founder_story: 'Founder story', solution_selling: 'Solution selling', social_proof: 'Social proof',
};
/** A phrase ended with a full stop, unless it already ends with one. */
const withStop = (text: string) => /[.!?]$/.test(text.trim()) ? text.trim() : `${text.trim()}.`;
export const contentTypeWords = (type: string) => CONTENT_TYPE_WORDS[type] ?? sentence(words(type));
// A call time at the end of an evidence point ("(20:20–21:25)") reads as noise on the card; the dialog keeps it.
const withoutTimes = (text: string) => text.replace(/\s*\((?:\d{1,2}:\d{2}(?:[–-]\d{1,2}:\d{2})?(?:[,;]\s*)?)+\)\s*$/, '').trim();

/** The next step a card names: the CTA and the offer it serves, in words. */
export function nextStep(card: Card): string {
  const fit = card.offer_fit;
  if (fit) {
    const slot = CTA_SLOTS[fit.cta_slot] ?? words(fit.cta_slot);
    return [slot, fit.offer].filter(Boolean).join(' · ');
  }
  return card.offer_connection ?? '';
}

/** The text a card is searched by and the offer it is filtered by. */
export const cardSearchText = (card: Card) => [card.title, card.point ?? card.core_perspective, card.audience, card.why_it_matters, card.wia_in_action ?? '',
  ...(card.evidence_points ?? []), card.guardrail ?? '', card.series ?? ''].join(' ');
export const cardOfferText = (card: Card) => [card.offer_fit?.offer ?? '', card.offer_connection ?? ''].join(' ');

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return <li><strong className="font-semibold text-[#34445F]">{label}: </strong>{children}</li>;
}

/** What an angle card shows: its content type and the idea in a few lines, and why it matters. The full rationale (audience,
    WIA's expertise, the call's evidence, the guardrails) is in the review dialog. */
export function CardSummary({ card }: { card: Card }) {
  const point = card.point || card.core_perspective;
  return <div className="space-y-2.5 text-[12.5px] leading-relaxed text-[#4F5B6E]">
    <p className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.12em]">
      <span className="rounded-md bg-[#EFF3FF] px-2 py-0.5 text-[#5070FF]">{card.pillar}</span>
      <span className="text-[#A38B61]">{contentTypeWords(card.content_type)}</span></p>
    {point && <p className="line-clamp-3">{point}</p>}
    {card.why_it_matters && <p className="line-clamp-2 text-[#7A8496]"><span className="font-semibold text-[#34445F]">Why it matters: </span>{card.why_it_matters}</p>}
  </div>;
}

export function CardRationale({ card, full = false }: { card: Card; full?: boolean }) {
  const point = card.point || card.core_perspective;
  const guardrail = card.guardrail ? sentences(card.guardrail) : [];
  const next = nextStep(card);
  return <section aria-label="Topic and editorial rationale" className={PANEL}>
    <div className="mb-3"><span className={PANEL_HEADING}>Topic & editorial rationale</span></div>
    <ul className={PANEL_LIST}>
      <Item label="Content pillar / type"><span className="font-semibold text-[#5070FF]">{card.pillar}</span>
        <span className="block mt-1">{withStop(`${contentTypeWords(card.content_type)}${card.series ? ` · ${card.series}` : ''}`)} {point}</span></Item>
      {card.audience && <Item label="Audience">{card.audience}</Item>}
      {card.why_it_matters && <Item label="Why this matters">{card.why_it_matters}</Item>}
      {card.wia_in_action && <Item label="WIA’s expertise or process">{card.wia_in_action}</Item>}
      {(card.evidence_points ?? []).length > 0 && <Item label="Evidence in the referenced call">
        <ul className="mt-1 list-disc pl-4 space-y-1">{(card.evidence_points ?? []).map((p, i) => <li key={i}>{full ? p : withoutTimes(p)}</li>)}</ul></Item>}
      {(guardrail.length > 0 || next) && <Item label="Editorial guardrail / next step">
        <ul className="mt-1 list-disc pl-4 space-y-1">{guardrail.map((g, i) => <li key={i}>{g}</li>)}{next && <li>Next step: {next}</li>}</ul></Item>}
    </ul>
  </section>;
}
