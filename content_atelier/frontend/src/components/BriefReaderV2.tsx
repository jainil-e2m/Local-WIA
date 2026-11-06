import React, { useState } from 'react';
import { REASON_CODES, speakerLabel } from './CardReview';
import type { BriefBodyV2, BriefBodyV3, BriefBodyV4, BriefCta as BriefCTA, BriefVersion, RosterEntry, Rubric, StoredBriefV2, StoredBriefV3, StoredBriefV4 } from '../api/types';
import { BlockerList, BriefFieldEditor, BriefTextEditor, RefreshPanel, VersionList, type BlockerItem } from './BriefEditing';
import { GateContextPanel } from './shared/GateContext';
import { AccountMemoryPanel } from './AccountMemory';
import { Select } from './ThemedSelect';
import { DARK, PANEL, PANEL_HEADING, QUIET } from './studio/parts';
import { TAKES, TimeNote } from './studio/GenerationTime';
import { useOneClick } from '../utils/workspace';

/* Version 2 and 3 brief reader and Gate 2 decision (E.F4; R50; E.B23). The WIA perspective comes first; the checks and
   evidence sit collapsed beneath. No passage IDs or offsets appear: evidence shows its speaker and time only. A v3 brief
   adds the Reel script, the email's and the caption's finished bodies, and each claim's ledger status.

   A v4 brief (E.B33) goes through the same Gate 2: its reader (BriefReaderV4's body view, passed in as `bodyView`) replaces
   the v2 and v3 body above the panels, and everything below it (the CTA, before publishing, the checks and named blockers,
   the field editor over briefFields.ts's v4 map, refresh with feedback, context and attested facts, versions, the claims
   and the decision) is the same code, since the three contracts share the header, the ledger and the Gate 2 routes. */

type Perform = (path: string, method?: string, body?: unknown) => Promise<void>;
const button = 'rounded-full border border-[#E6E9F0] bg-white px-3.5 py-1.5 text-[12px] font-medium text-[#34445F] hover:bg-[#F7F8FB] disabled:opacity-40 disabled:cursor-not-allowed';
const field = 'block w-full rounded-lg border border-[#E0E4EC] bg-white p-2 mt-1 text-[13px]';
const words = (s: string) => s.replaceAll('_', ' ');

export type { BriefCTA, BriefBodyV2, BriefBodyV3, StoredBriefV2, StoredBriefV3 };
/** A brief of the v2 family: contract v2, v3 with its ledger built after writing, or v4 (E.B33), which shares v3's ledger. */
export type LedgerBrief = StoredBriefV2 | StoredBriefV3 | StoredBriefV4;
type Body = BriefBodyV2 | BriefBodyV3;

// The server's checks, in the reviewer's words (R50): what to do, with no evidence or passage identifiers.
const PLAIN: [RegExp, string][] = [
  [/scoped grounding\/differentiation review|admitted-archive\/legacy-history limitation/, 'Record the check of the claims below (the brief is new or changed since the last check).'],
  [/Related prior use changed/, 'Earlier content on this point changed since your check: check the claims again.'],
  [/writer.s proposal; a person confirms it/, 'Confirm the CTA, or choose no explicit ask.'],
  [/Required before-publishing items remain unanswered/, 'Answer every required item under "Before publishing".'],
  [/A replacement brief exists/, 'A newer version of this brief exists: open it from the brief list.'],
  [/Brief content hash changed/, 'The brief changed while it was open: reload it.'],
];
const IDS = /\b(?:ev|evidence|passage|moment|claim|transcript)_[A-Za-z0-9_]+\b/g;
export function plainBlocker(message: string): string {
  const known = PLAIN.find(([pattern]) => pattern.test(message));
  return known ? known[1] : message.replace(/^Evidence \S+ /, 'A quoted turn ').replace(IDS, 'a quoted turn');
}
export const plainBlockers = (messages: string[]) => [...new Set(messages.map(plainBlocker))];

/** Whether the reader below shows this brief: contracts v2 and v3 share it. */
export const isV2 = (brief: { content_body: { schema_version?: string | null } }) =>
  brief.content_body.schema_version === 'brief_document_v2' || brief.content_body.schema_version === 'brief_document_v3';
export const briefTitle = (brief: { content_body: { schema_version?: string | null; document: unknown } }) =>
  isV2(brief) ? (brief.content_body.document as { body: Body }).body.approved_angle.title : (brief.content_body.document as { title: string }).title;
// The ledger's status of a v3 claim, in the reviewer's words.
const STATUS: Record<string, string> = { bound: 'matches the call', supported: 'checked by the verifier', unsupported: 'not supported by the call',
  unchecked: 'check it against the call', kept_by_person: 'kept by a person', attested: 'attested by a person' };
type Attested = { attested?: { kind: string; by: string; on: string } | null };
/** A claim's status in the reviewer's words; an attested one names who attested it and when (R57). */
export const claimStatus = (c: { status?: string } & Attested) => c.attested
  ? `${c.attested.kind === 'paraphrase' ? "a paraphrase of the client's words, given" : 'attested'} by ${c.attested.by} on ${c.attested.on}`
  : STATUS[c.status ?? ''] || words(c.status ?? '');
type LedgerRecord = { verifier?: { status?: string; reason?: string } };
type RepairRecord = { used?: boolean; accepted?: boolean; rejected_because?: string };
const at = (ms: number | null) => ms === null ? '' : ` at ${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`;

/** The CTA confirmation body, or what is missing. */
export function ctaRequest(expected: string, choice: 'explicit' | 'no_explicit_ask', action: string): { body: Record<string, unknown> } | { error: string } {
  if (choice === 'explicit' && !action.trim()) return { error: 'Write the CTA, or choose no explicit ask.' };
  if (/\$\s?\d/.test(action)) return { error: 'A CTA never states a price.' };
  return { body: { expected_hash: expected, choice, action: choice === 'explicit' ? action.trim() : null } };
}

/** A person's choice of the anchor piece (E.B23): the edit route's `anchor`, a piece key, or null for the rule. */
export const anchorRequest = (expected: string, key: string | null) => ({ expected_hash: expected, changes: { anchor: key } });

/** The anchor in the reviewer's words: which piece production writes first, and who chose it. */
export function anchorLine(anchor: LedgerBrief['anchor']): string {
  if (!anchor?.key) return 'No piece to write first: the format plan is empty.';
  const label = anchor.options?.find(o => o.key === anchor.key)?.label ?? anchor.key;
  return `Written first in production: ${label} (${anchor.chosen_by === 'person' ? 'chosen by a person' : `the rule: ${anchor.rule.toLowerCase()}`}).`;
}

/** The Gate 2 decision body with E.F1's reason and author; a rejection needs its reason in the note. The ratings on review
    rubric 2.3a (E.X9) are optional, but all or none, and go with the rubric version the form showed. */
export function briefDecisionRequest(expected: string, decision: 'approved' | 'rejected', reason_code: string, note: string, author: string,
  rubric?: Rubric | null, ratings: Record<string, number> = {}): { body: Record<string, unknown> } | { error: string } {
  if (decision === 'rejected' && (!reason_code || !note.trim())) return { error: 'Choose a reason and say why in the note.' };
  const rated = rubric ? rubric.criteria.filter(c => ratings[c.key]).length : 0;
  if (rubric && rated && rated < rubric.criteria.length) return { error: 'Rate the brief on every rubric point, or on none.' };
  return { body: { expected_hash: expected, decision, reason_code: reason_code || null, note: note.trim() || null, author: author.trim() || null,
    ...(rubric && rated ? { rubric_ratings: ratings, rubric_version: rubric.version } : {}) } };
}

export function BriefReaderV2({ brief, busy, perform, versions = [], onOpen = () => {}, refreshing = false, bodyView, approveLabel = 'Approve the brief' }: {
  brief: LedgerBrief; busy: boolean; perform: Perform; versions?: BriefVersion[]; onOpen?: (briefId: string) => void; refreshing?: boolean;
  bodyView?: React.ReactNode;
  /** The approve button's words: a v4 brief with content packs on says that approving creates its pack (NP.F3). */
  approveLabel?: string;
}) {
  const { header, body: b } = brief.content_body.document as { header: StoredBriefV2['content_body']['document']['header']; body: Body | BriefBodyV4 };
  const review = brief.content_body.review as typeof brief.content_body.review & { ledger?: LedgerRecord; repair?: RepairRecord };
  const verifier = review.ledger?.verifier;
  const expected = brief.content_hash;
  const roster = brief.content_body.provenance?.roster || [];
  const blockers = plainBlockers(brief.blockers);
  // The blockers by name (5.F2): the server's list in plain words, else the older messages made plain here.
  const named: BlockerItem[] = brief.blocker_items ?? blockers.map(title => ({ kind: 'blocking_finding' as const, title, action: '' }));
  const locks = brief.locked_fields ?? brief.content_body.review.locked_fields ?? [];
  // A client's result in the copy, or a line of the call quoted in public: both are cleared with the client's permission below.
  const permissionNeeded = brief.blockers.some(x => /client's permission|source-use and attribution clearance/.test(x));
  const cleared = brief.content_body.review.clearances || {};
  const sources = (brief.selected_evidence || []).filter(e => e.transcript_id);
  const quoted = (b.claims as { public_quote?: boolean; quote?: string | null; evidence_ids: string[] }[]).filter(c => c.public_quote && c.quote && !c.evidence_ids.some(id => cleared[id]));
  const [clearance, setClearance] = useState({ evidence_id: quoted[0]?.evidence_ids[0] ?? '', permission_reference: '', attribution_reference: '' });
  const [cta, setCta] = useState<{ choice: 'explicit' | 'no_explicit_ask'; action: string }>({ choice: header.cta.choice === 'no_explicit_ask' ? 'no_explicit_ask' : 'explicit', action: header.cta.action || '' });
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [reviewReason, setReviewReason] = useState(''), [reviewAck, setReviewAck] = useState(false);
  const [decision, setDecision] = useState({ reason_code: '', note: '', author: '' });
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const rubric = (brief as { rubric?: Rubric | null }).rubric ?? null;
  const [error, setError] = useState('');
  const [anchorKey, setAnchorKey] = useState(brief.anchor?.key ?? '');
  const send = (path: string, result: { body: Record<string, unknown> } | { error: string }, method = 'POST') => {
    if ('error' in result) { setError(result.error); return; }
    setError(''); void perform(path, method, result.body);
  };
  const pending = brief.approval_status === 'pending';
  // Approving is one click and the screen asks only for feedback (gates.one_click).
  const oneClick = useOneClick();
  const simple = oneClick && pending;
  // Editing the text swaps the brief for its editor; a saved edit is a new version, which opens on its own.
  const [editing, setEditing] = useState(false);
  if (editing && simple && brief.can_edit) return <BriefTextEditor body={b as unknown as Record<string, unknown>} schemaVersion={brief.content_body.schema_version} locks={locks} expected={expected}
    briefId={brief.brief_id} busy={busy} perform={perform} onClose={() => setEditing(false)} />;
  const plan = (b as Body).format_plan;
  // Which piece production writes first (E.B23), and for an editor the choice of another.
  const anchorPanel = <div className="mt-2 rounded bg-slate-50 p-2 text-sm"><p>{anchorLine(brief.anchor)}</p>{brief.anchor?.note && <p className="text-amber-800">{brief.anchor.note}</p>}
    {brief.can_edit && !!brief.anchor?.options?.length && <div className="mt-2 flex flex-wrap items-center gap-2">
      <label>Write first<Select className="ml-2 border rounded p-1" value={anchorKey} onChange={e => setAnchorKey(e.target.value)}>{brief.anchor.options.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}</Select></label>
      <button className={button} disabled={busy || !anchorKey || anchorKey === brief.anchor.key} onClick={() => void perform(`/briefs/${brief.brief_id}`, 'PATCH', anchorRequest(expected, anchorKey))}>Make this the anchor</button>
      {brief.anchor.chosen_by === 'person' && <button className={button} disabled={busy} onClick={() => void perform(`/briefs/${brief.brief_id}`, 'PATCH', anchorRequest(expected, null))}>Use the rule</button>}</div>}</div>;
  return <div className="space-y-5">
    {simple && brief.can_edit && <div className="flex justify-end"><button type="button" className={QUIET} disabled={busy || refreshing}
      title={refreshing ? 'A new version is being written. You can edit it when it is here.' : undefined} onClick={() => setEditing(true)}>Edit the text</button></div>}
    {bodyView ? bodyView : <>
    <header><p className="text-xs uppercase tracking-wide text-slate-500">{header.purpose} · {words(b.strategic_purpose.content_type)} · {header.channels.join(', ')}</p>
      <h2 className="font-editorial text-2xl">{b.approved_angle.title}</h2><p className="mt-1">{b.approved_angle.core_perspective}</p>
      {b.sharpened_point && <p className="mt-2 text-sm rounded bg-slate-50 p-2"><strong>Sharper point proposed:</strong> {b.sharpened_point.text} <span className="text-slate-600">({b.sharpened_point.reason})</span></p>}</header>
    <section className="rounded-xl border-2 border-[#173354] p-4"><h3 className="font-medium">WIA perspective</h3><p className="mt-2 whitespace-pre-wrap">{b.wia_perspective}</p></section>
    <section><h3 className="font-medium">Supporting example</h3><p>{b.supporting_example.scene}</p><p><strong>What WIA did:</strong> {b.supporting_example.wia_move}</p><p><strong>What the client contributed:</strong> {b.supporting_example.client_contribution}</p></section>
    <section className="grid gap-3 md:grid-cols-2"><div><h3 className="font-medium">Who it is for</h3><p>{b.audience.who}</p><p className="text-sm">{b.audience.reason_to_care}</p></div>
      <div><h3 className="font-medium">The shift</h3><p className="text-sm">Understand: {b.intended_shift.understand}</p><p className="text-sm">Believe: {b.intended_shift.believe}</p>{b.intended_shift.do && <p className="text-sm">Do: {b.intended_shift.do}</p>}</div></section>
    <section><h3 className="font-medium">Narrative</h3><ul className="ml-6 list-disc">{b.narrative_outline.hooks.map((h, i) => <li key={i}>Hook ({words(h.style)}): {h.text}</li>)}
      <li>Main point: {b.narrative_outline.main_point}</li><li>Transformation: {b.narrative_outline.transformation}</li></ul></section>
    <details className="rounded-lg border p-3"><summary className="font-medium cursor-pointer">Format plan</summary>
      {anchorPanel}
      {plan.reels.map((r, i) => <div key={i} className="mt-2"><p><strong>Reel {i + 1}: {r.job}</strong> · about {r.read_time_seconds} seconds</p><p className="text-sm">Cover: {r.cover_text} · Opening: {r.spoken_opening}</p><ul className="ml-6 list-disc text-sm">{r.beats.map((x, n) => <li key={n}>{x}</li>)}</ul>
        {'script' in r && r.script && <p className="mt-1 text-sm whitespace-pre-wrap"><strong>Script:</strong> {r.script}</p>}</div>)}
      {plan.carousel && <div className="mt-2"><p><strong>Carousel: {plan.carousel.job}</strong></p><ol className="ml-6 list-decimal text-sm">{plan.carousel.slides.map(s => <li key={s.number}>{s.job}: {s.text}</li>)}</ol></div>}
      {plan.email && <div className="mt-2 text-sm whitespace-pre-wrap"><p><strong>Email</strong>: {plan.email.subject_options.join(' | ')}</p><p>{plan.email.opening}</p><p>{'body' in plan.email ? plan.email.body : plan.email.argument}</p><p>{plan.email.ending}</p></div>}
      {plan.caption && ('body' in plan.caption
        ? <div className="mt-2 text-sm whitespace-pre-wrap"><p><strong>Caption</strong>: {plan.caption.hook}</p><p>{plan.caption.body}</p><p>{plan.caption.ending}</p></div>
        : <p className="mt-2 text-sm"><strong>Caption</strong>: {plan.caption.hook} · {plan.caption.ending}</p>)}
    </details></>}
    {simple && (brief.can_edit || brief.can_review) && <section aria-label="Your feedback" className={`${PANEL} mt-4`}>
      <div className="mb-3"><span className={PANEL_HEADING}>Your feedback</span></div>
      <RefreshPanel briefId={brief.brief_id} expected={expected} locks={locks} canEdit={brief.can_edit} busy={busy} perform={perform} running={refreshing} />
      {(brief.can_edit || brief.can_review) && <div className="mt-4 pt-4 border-t border-[#E6E9F0] space-y-3">
        {brief.can_review && !brief.can_approve && <p className="text-[12px] text-amber-800">{blockers[0] || 'This version cannot be approved.'}</p>}
        {error && <p role="alert" className="text-[12px] text-red-800">{error}</p>}
        <div className="flex flex-wrap items-center justify-between gap-3">
          {brief.can_edit ? <button type="button" className={QUIET} disabled={busy || refreshing} onClick={() => setEditing(true)}>Edit the text</button> : <span />}
          {brief.can_review && <div className="ml-auto flex flex-wrap items-center justify-end gap-3">
            {brief.can_approve && !refreshing && /pack/i.test(approveLabel) && <TimeNote>The pack takes {TAKES.pack} to make.</TimeNote>}
            <button type="button" className={DARK} disabled={busy || refreshing || !brief.can_approve} onClick={() => send(`/briefs/${brief.brief_id}/decision`, briefDecisionRequest(expected, 'approved', '', '', '', null, {}))}>{approveLabel}</button></div>}
        </div>
      </div>}
    </section>}
    {simple && brief.can_review && <details className="mt-4 rounded-xl border border-[#E6E9F0] bg-white p-4"><summary className="cursor-pointer text-[13px] font-medium text-[#34445F]">Reject this brief</summary>
      <label className="mt-3 block text-sm">Why<textarea className={field} value={decision.note} onChange={e => setDecision({ ...decision, note: e.target.value })} /></label>
      <button type="button" className={`${QUIET} mt-2`} disabled={busy || !decision.note.trim()} onClick={() => send(`/briefs/${brief.brief_id}/decision`, briefDecisionRequest(expected, 'rejected', 'other', decision.note, '', null, {}))}>Reject the brief</button></details>}
    {pending && !simple && <>
    <section className="rounded-lg bg-slate-50 p-3"><h3 className="font-medium">CTA</h3>
      <p>{header.cta.action || 'No explicit ask'} <span className="text-sm text-slate-600">({header.cta.chosen_by === 'person' ? 'confirmed by a person' : 'the writer’s proposal'})</span></p><p className="text-sm">{b.cta_why}</p>
      {header.cta.chosen_by !== 'person' && brief.can_review && <div className="mt-2 space-y-2">
        <fieldset className="space-y-2"><legend className="text-sm font-medium">Which CTA should the brief use?</legend>
          <label className="flex gap-2 text-sm"><input type="radio" name={`cta-${brief.brief_id}`} value="explicit" checked={cta.choice === 'explicit'} onChange={() => setCta({ ...cta, choice: 'explicit' })} />Use this CTA</label>
          {cta.choice === 'explicit' && <label className="block text-sm">What the CTA asks the reader to do<input className={field} value={cta.action} onChange={e => setCta({ ...cta, action: e.target.value })} /></label>}
          <label className="flex gap-2 text-sm"><input type="radio" name={`cta-${brief.brief_id}`} value="no_explicit_ask" checked={cta.choice === 'no_explicit_ask'} onChange={() => setCta({ ...cta, choice: 'no_explicit_ask' })} />No explicit ask</label>
        </fieldset>
        <button className={button} disabled={busy} onClick={() => send(`/briefs/${brief.brief_id}/cta`, ctaRequest(expected, cta.choice, cta.action))}>Confirm the CTA</button></div>}
    </section>
    <section><h3 className="font-medium">Before publishing</h3>{b.before_publishing.map((x, i) => <label key={i} className="block text-sm mt-1">{x.text}{x.required ? ' (required)' : ''}
      <textarea className={field} disabled={!brief.can_review} value={answers[`P${i + 1}`] ?? x.answer ?? ''} onChange={e => setAnswers({ ...answers, [`P${i + 1}`]: e.target.value })} /></label>)}
      {!!b.before_publishing.length && <button className={`${button} mt-2`} disabled={!brief.can_review || busy || !Object.keys(answers).length} onClick={() => void perform(`/briefs/${brief.brief_id}/answers`, 'POST', { expected_hash: expected, answers })}>Save answers</button>}</section>
    </>}
    <details className="rounded-xl border border-[#E6E9F0] bg-white p-4"><summary className="cursor-pointer text-[13px] font-medium text-[#34445F]">What was said on the call</summary>
      <ul className="mt-3 space-y-2 text-[12.5px] leading-relaxed text-[#4F5B6E]">{b.evidence.map(x => <li key={x.evidence_id} className="border-l-2 border-[#D9BE87] pl-3"><span className="block font-semibold text-[#34445F]">{speakerLabel(x.speaker, roster)}{at(x.start_ms)}</span>“{x.quote}”</li>)}</ul></details>
    {pending && !simple && <>
    <details className="rounded-lg border p-3" open={named.length > 0}><summary className="cursor-pointer">Checks ({named.length} to resolve)</summary>
      <BlockerList items={named} removed={brief.removed_material} />
      <ul className="mt-2 ml-6 list-disc text-sm text-slate-600">{brief.content_body.review.findings.filter(f => f.severity === 'warning').map((f, i) => <li key={i}>{f.message}</li>)}</ul>
      {verifier && verifier.status !== 'run' && verifier.status !== 'nothing_to_check' && <p className="mt-2 text-sm">The second check of the copy against the call did not run{verifier.reason ? ` (${verifier.reason})` : ''}: check the lines marked below yourself.</p>}
      {review.repair?.used && review.repair.accepted === false && <p className="mt-2 text-sm">The automatic fix was not used, because it added caveats to the copy. The writer's copy is shown, with what needs fixing above.</p>}</details>
    <BriefFieldEditor body={b as unknown as Record<string, unknown>} schemaVersion={brief.content_body.schema_version} locks={locks} expected={expected}
      briefId={brief.brief_id} canEdit={brief.can_edit} busy={busy} perform={perform} />
    {pending && <RefreshPanel briefId={brief.brief_id} expected={expected} locks={locks} canEdit={brief.can_edit} busy={busy} perform={perform} running={refreshing} />}
    <GateContextPanel target="brief" id={brief.brief_id} items={brief.context_items ?? []} canAdd={brief.can_edit && pending}
      canAttest={brief.can_review} busy={busy} perform={perform} />
    {brief.can_review && <section className="space-y-2"><h3 className="font-medium">Check the claims</h3>
      <ul className="ml-6 list-disc text-sm">{b.claims.map(c => <li key={c.claim_id}>{c.text} <span className="text-slate-500">({words(c.claim_class)}{'status' in c ? `; ${claimStatus(c as typeof c & Attested)}` : ''})</span></li>)}</ul>
      <label className="block text-sm">What you checked<textarea className={field} value={reviewReason} onChange={e => setReviewReason(e.target.value)} /></label>
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={reviewAck} onChange={e => setReviewAck(e.target.checked)} />I checked every claim against the call, and earlier coverage of this point.</label>
      <button className={button} disabled={busy || !reviewReason.trim() || !reviewAck} onClick={() => void perform(`/briefs/${brief.brief_id}/review`, 'POST', { expected_hash: expected, claim_ids: b.claims.map(c => c.claim_id), reason: reviewReason, history_acknowledged: true })}>Record the check</button></section>}
    {(permissionNeeded || Object.keys(cleared).length > 0) && brief.can_review && <section className="rounded-lg bg-amber-50 p-3 space-y-2 text-sm">
      <h3 className="font-medium">Client permission</h3>
      <p>{quoted.length ? `The public copy quotes the call: ${quoted.map(c => `“${c.quote}”`).join(', ')}. Record where the client gave permission, or edit the copy so it no longer quotes the call.` : 'A client’s result appears in the public copy. Record where the client gave permission, for the call it comes from.'}</p>
      {Object.keys(cleared).length > 0 && <p>Permission recorded for {Object.keys(cleared).length} {Object.keys(cleared).length === 1 ? 'call excerpt' : 'call excerpts'}.</p>}
      <label className="block">The call excerpt<Select className={field} value={clearance.evidence_id} onChange={e => setClearance({ ...clearance, evidence_id: e.target.value })}>
        <option value="">Choose…</option>{sources.map(e => <option key={e.evidence_id} value={e.evidence_id}>{speakerLabel(e.speaker || null, roster, e.title)}: {e.excerpt.slice(0, 80)}</option>)}</Select></label>
      <label className="block">Where the client gave permission (an email, a signed form, a message)<input className={field} value={clearance.permission_reference} onChange={e => setClearance({ ...clearance, permission_reference: e.target.value })} /></label>
      <label className="block">How the client may be named (by name, or anonymised as…)<input className={field} value={clearance.attribution_reference} onChange={e => setClearance({ ...clearance, attribution_reference: e.target.value })} /></label>
      <button className={button} disabled={busy || !clearance.evidence_id || !clearance.permission_reference.trim() || !clearance.attribution_reference.trim()}
        onClick={() => void perform(`/briefs/${brief.brief_id}/clearance`, 'POST', { expected_hash: expected, ...clearance })}>Record the permission</button>
    </section>}
    {pending && brief.can_review && <fieldset className="rounded-xl border border-[#E6E9F0] bg-white p-4 space-y-2"><legend className="px-1 text-[13px] font-semibold text-[#34445F]">Your decision</legend>
      <label className="block text-sm">Reason<Select className={field} value={decision.reason_code} onChange={e => setDecision({ ...decision, reason_code: e.target.value })}><option value="">Choose…</option>{REASON_CODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></label>
      <label className="block text-sm">Note<textarea className={field} value={decision.note} onChange={e => setDecision({ ...decision, note: e.target.value })} /></label>
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
      <div className="flex gap-3"><button className={button} disabled={busy || !brief.can_approve} onClick={() => send(`/briefs/${brief.brief_id}/decision`, briefDecisionRequest(expected, 'approved', decision.reason_code, decision.note, decision.author, rubric, ratings))}>{approveLabel}</button>
        <button className={button} disabled={busy} onClick={() => send(`/briefs/${brief.brief_id}/decision`, briefDecisionRequest(expected, 'rejected', decision.reason_code, decision.note, decision.author, rubric, ratings))}>Reject the brief</button></div>
    </fieldset>}
    </>}
    <p><a className="text-[12px] font-medium text-[#5070FF] hover:underline" href={`/api/atelier/briefs/${brief.brief_id}/export.md`}>Download the brief</a></p>
  </div>;
}
