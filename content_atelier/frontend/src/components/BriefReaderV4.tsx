import React from 'react';
import type { BriefBodyV4, BriefVersion, CaptionPlanV3, PremiseOption, ReelPlanV4, ReelPlanV5, StoredBriefV4 } from '../api/types';
import { BriefReaderV2, briefTitle as titleV2 } from './BriefReaderV2';
import { contentTypeWords } from './studio/CardRationale';
import { reelKindWords } from './packFields';
import { Fold } from './packParts';

/* A read-only view of a contract v4 brief (E.B33): the brief in the 13 October order, then the finished copy of every asset
   in the layout of the packs WIA reviewed on 20 October (the email with its send header, each Reel with its kind, cover,
   on-screen hook, script or screens and caption, the carousel with its title and caption). Gate 2's editing, refresh,
   context and decision are the v2 reader's panels (BriefEditing, GateContext): BriefGateV4 puts this view inside them, so a
   v4 brief is edited, refreshed and approved exactly as a v3 one is, with v4's labels from briefFields.ts.
   A brief from the Round 2 writer has Reel 1 as the central story and Reels 2 and 3 each with a premise of its own: each Reel
   shows its premise, takeaway and why it differs, and the premises the writer weighed are folded under the plan. */

export type { StoredBriefV4 };
export const isV4 = (brief: { content_body: { schema_version?: string | null } }) => brief.content_body.schema_version === 'brief_document_v4';
/** A brief's title for lists, any contract: v4's approved angle, else the v2 reader's rule. */
export const briefTitle = (brief: { content_body: { schema_version?: string | null; document: unknown } }) =>
  isV4(brief) ? (brief.content_body.document as { body: BriefBodyV4 }).body.approved_angle.title : titleV2(brief);

type AnyReel = ReelPlanV4 | ReelPlanV5;
/** A Reel's kind in words: "Central story · Face to camera" since Round 2, "face to camera, story" before. */
const kindWords = (reel: AnyReel) => reelKindWords(reel.kind, 'production' in reel ? reel.production : null);
const USED_FOR: Record<string, string> = { reel_1: 'Became Reel 1', reel_2: 'Became Reel 2', reel_3: 'Became Reel 3' };

/** A section of the brief in the 20 October mockup's panel (its "Content brief" headings). */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mt-4 rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4 text-[13px] leading-relaxed text-[#34445F] space-y-1">
    <h3 className="mb-2 font-sans text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]">{title}</h3>{children}</section>;
}

function Caption({ caption }: { caption?: CaptionPlanV3 | null }) {
  if (!caption) return null;
  return <div className="mt-2 text-sm whitespace-pre-wrap"><p><strong>Caption</strong></p><p>{caption.hook}</p><p>{caption.body}</p><p>{caption.ending}</p></div>;
}

/** A Reel's premise in a line, then its takeaway and why it differs in small muted text (Round 2); nothing for an earlier Reel. */
function ReelDirection({ reel }: { reel: AnyReel }) {
  if (!('premise' in reel) || !reel.premise) return null;
  return <div className="mt-1 space-y-0.5 text-[12px] text-[#667184]">
    <p className="text-[13px] text-[#34445F]">{reel.premise}</p>
    {reel.takeaway && <p><span className="font-semibold text-[#34445F]">Takeaway</span> · {reel.takeaway}</p>}
    {reel.distinct_because && <p><span className="font-semibold text-[#34445F]">Why it's different</span> · {reel.distinct_because}</p>}
  </div>;
}

/** The premises the writer weighed for the Reels, folded: each one, the Reel it became or "Not used", and why. */
export function PremisesConsidered({ options }: { options: PremiseOption[] }) {
  if (!options.length) return null;
  return <div className="pt-2"><Fold summary={`Premises considered (${options.length})`}>
    <ul className="space-y-2">{options.map((o, i) => <li key={i}>
      <p className="text-[#34445F]">{o.premise}</p>
      <p>{(o.used_for && USED_FOR[o.used_for]) || 'Not used'}{o.why ? ` · ${o.why}` : ''}</p>
    </li>)}</ul>
  </Fold></div>;
}

function Reel({ reel, n }: { reel: AnyReel; n: number }) {
  return <div className="mt-3 text-sm">
    <p><strong>Reel {n}: {reel.job}</strong></p>
    <p>Format: {kindWords(reel)} · about {reel.read_time_seconds} seconds</p>
    <p>Cover: {reel.cover_text}</p>
    <p>On-screen hook: {reel.on_screen_hook}</p>
    {reel.screens?.length ? <ol className="ml-6 list-decimal">{reel.screens.map((s, i) => <li key={i}>{s}</li>)}</ol> : null}
    {reel.script ? <p className="whitespace-pre-wrap"><strong>Script:</strong> {reel.script}</p> : reel.spoken_opening ? <p>Opening: {reel.spoken_opening}</p> : null}
    {reel.personal_lines.length ? <p>Personal lines for Whitney to keep or cut: {reel.personal_lines.join(' | ')}</p> : null}
    <Caption caption={reel.caption} />
    {reel.offer_descriptor ? <p>Offer descriptor: {reel.offer_descriptor}</p> : null}
  </div>;
}

/** Gate 2's label on the asset copy when content packs are on (NP.F3, D43b): the pack finishes this copy after approval. */
export const DRAFT_COPY_NOTE = 'Draft copy: the content pack finishes it. Any line you edit here is kept word for word.';

/** The v4 brief body, read-only, in the 13 October order. With `draftCopy` (content packs on), the asset copy is the pack's,
    so the brief shows its plan and not the draft copy. */
export function BriefBodyV4View({ body, draftCopy = false }: { body: BriefBodyV4; draftCopy?: boolean }) {
  const plan = body.format_plan, sp = body.strategic_purpose, ex = body.supporting_example, outline = body.narrative_outline;
  return <div>
    <Section title="Central point"><p>{body.central_point}</p></Section>
    <Section title="Strategic purpose and desired response">
      <p>{sp.pillar} · {contentTypeWords(sp.content_type)}. {sp.why_now}</p><p>Desired response: {sp.desired_response}</p>
    </Section>
    <Section title="Audience and reason to care"><p>{body.audience.who}</p><p>{body.audience.reason_to_care}</p></Section>
    <Section title="WIA perspective"><p className="whitespace-pre-wrap">{body.wia_perspective}</p></Section>
    <Section title="Supporting example">
      <p>{ex.scene}</p>
      {ex.timestamps.length > 0 && <ul className="ml-5 list-disc text-[12.5px] text-[#667184]">{ex.timestamps.map((t, i) => <li key={`t${i}`}>{t}</li>)}</ul>}
    </Section>
    <Section title="Narrative outline">
      <ul className="ml-5 list-disc space-y-1">
        {outline.hooks[0] && <li>Hook: {outline.hooks[0].text}</li>}
        <li>Problems, desires or symptoms: {outline.problems_desires_symptoms.join(' ')}</li>
        <li>Main point: {outline.main_point}</li><li>Transformation: {outline.transformation}</li><li>CTA: {outline.cta}</li>
      </ul>
    </Section>
    <Section title="Format and creative approach">
      <ul className="ml-5 list-disc space-y-1">
        {plan.email && <li>Email: {plan.email.job}</li>}
        {plan.reels.map((r, i) => <li key={i}>Reel {i + 1} ({kindWords(r)}): {r.job}<ReelDirection reel={r} /></li>)}
        {plan.carousel && <li>Carousel: {plan.carousel.job}</li>}
      </ul>
      {'premise_options' in plan && <PremisesConsidered options={plan.premise_options} />}
    </Section>
    <Section title="CTA and essential boundaries">
      <p>{body.cta.action ?? 'No explicit ask'}</p>
      <p>{body.cta_why}</p>
    </Section>
    {!draftCopy && plan.email && <Section title="Email">
      <div className="text-sm whitespace-pre-wrap">
        <p>DATE: {plan.email.send_header.date}</p><p>SEND TIME: {plan.email.send_header.send_time}</p><p>RECIPIENTS: {plan.email.send_header.recipients}</p>
        <p>SUBJECT: {plan.email.subject_options.join(' | ')}</p><p>PREVIEW TEXT: {plan.email.preview}</p>
        <p>{plan.email.opening}</p><p>{plan.email.body}</p><p>{plan.email.ending}</p>
        {plan.email.offer_descriptor ? <p>Offer descriptor: {plan.email.offer_descriptor}</p> : null}
      </div>
    </Section>}
    {!draftCopy && plan.reels.length > 0 && <Section title="Reels">{plan.reels.map((r, i) => <Reel key={i} reel={r} n={i + 1} />)}</Section>}
    {!draftCopy && plan.carousel && <Section title={`Carousel: ${plan.carousel.title}`}>
      <ol className="ml-6 list-decimal text-sm whitespace-pre-wrap">{plan.carousel.slides.map(s => <li key={s.number}>{s.text}</li>)}</ol>
      <Caption caption={plan.carousel.caption} />
      {plan.carousel.offer_descriptor ? <p className="text-sm">Offer descriptor: {plan.carousel.offer_descriptor}</p> : null}
    </Section>}
  </div>;
}

/** A stored v4 brief, read-only. */
export function BriefReaderV4({ brief, draftCopy = false }: { brief: StoredBriefV4; draftCopy?: boolean }) {
  return <BriefBodyV4View body={brief.content_body.document.body} draftCopy={draftCopy} />;
}

/** A v4 brief at Gate 2: this reader inside the v2 reader's panels (edit any field, refresh with feedback, versions, context
    and attested facts, named blockers, the CTA, before publishing and the decision). With content packs on (NP.F3), the
    asset copy is labelled a draft the pack finishes, and approving says it creates the content pack. */
export function BriefGateV4({ brief, packsEnabled = false, ...gate }: { brief: StoredBriefV4; busy: boolean; perform: (path: string, method?: string, body?: unknown) => Promise<void>;
  versions?: BriefVersion[]; onOpen?: (briefId: string) => void; refreshing?: boolean; packsEnabled?: boolean }) {
  return <BriefReaderV2 brief={brief} {...gate} bodyView={<BriefReaderV4 brief={brief} draftCopy={packsEnabled} />}
    approveLabel={packsEnabled ? 'Approve brief and create content pack' : undefined} />;
}
