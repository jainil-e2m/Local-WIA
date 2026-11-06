import React, { useEffect, useRef, useState } from 'react';
import type { Card, CardSelection, ConsideredIdea, Disposition, Ledger, RosterEntry, Rubric, StoredAngle } from '../api/types';
import { useMomentEvidence } from '../api/evidence';
import { RemovedMaterialNote } from './BriefEditing';
import { CARD_FIELDS, CONTENT_TYPES, PILLARS, cardChanges, cardFieldLabel, choiceLabel, editableFields, formValues, recordText } from './cardFields';
import { CardRationale } from './studio/CardRationale';
import { DARK, PANEL, PANEL_HEADING, QUIET, cardDay, rowsFor, EDIT_FIELD, EDIT_LABEL, EditBar } from './studio/parts';
import { TAKES, TimeNote } from './studio/GenerationTime';
import { useOneClick } from '../utils/workspace';
import { Select } from './ThemedSelect';
import { DateInput } from './DateInput';

/* Gate 1 card screen (E.F2) and disposition control (E.F1), built for a non-technical reviewer (R50).
   Every action calls the Gate 1 API (E.B20): one decision and one label per disposition. */

// Resolves to true when the write succeeded (the screen's guarded action shows any failure or conflict itself).
type Perform = (path: string, method?: string, body?: unknown) => Promise<unknown>;
const button = 'rounded-full border border-[#E6E9F0] bg-white px-3.5 py-1.5 text-[12px] font-medium text-[#34445F] hover:bg-[#F7F8FB] disabled:opacity-40 disabled:cursor-not-allowed';
const field = 'block w-full rounded-lg border border-[#E0E4EC] bg-white p-2 mt-1 text-[13px]';

export const DISPOSITIONS = [
  { value: 'develop', label: 'Develop', help: 'Approve it for a brief.' },
  { value: 'reframe', label: 'Reframe', help: 'Keep the idea with a new title or central point.' },
  { value: 'hold', label: 'Hold', help: 'Not now; come back to it on a date.' },
  { value: 'internal', label: 'Internal', help: 'Useful for sales or the team, not public content.' },
  { value: 'skip', label: 'Skip', help: 'Not worth developing.' },
] as const;
export type DispositionValue = typeof DISPOSITIONS[number]['value'];
// Whitney's own categories, then the strategist's ranking terms (backend gates/decisions.py REASON_CODES).
export const REASON_CODES: [string, string][] = [
  ['strong', 'Strong as it is'], ['positioning', 'Positioning'], ['audience', 'Audience'], ['accuracy', 'Accuracy'],
  ['voice', 'Voice'], ['format', 'Format'], ['edit_scope', 'Edit scope'], ['strategic_fit', 'Strategic fit'],
  ['distinctiveness', 'Not distinctive'], ['duplicate', 'Duplicate'], ['evidence', 'Evidence'], ['timing', 'Timing'],
  ['internal_use', 'Internal use'], ['other', 'Other'],
];
export const DECIDE_IN_DEVELOPMENT = { choice: 'decide_in_development' };
// What a person who may read the week but not decide on it sees in place of the decision controls (S.F1, R50): the server
// would refuse their decision, so none is offered.
export const NO_DECIDE = 'Your account can read these ideas but cannot decide on them. Deciding needs the approver role; ask an administrator to add you.';
// Every decision records whose it is (E.B20, K49): the signed-in reviewer, or the person they relay.
export const AUTHOR_LABEL ='Whose decision is this? (leave empty if it is yours; or e.g. "Whitney Hodges" when relaying her)';
const words = (s: string) => s.replaceAll('_', ' ');

export interface DispositionForm {
  disposition: DispositionValue; reason_code: string; note: string; author: string;
  reframe_title: string; reframe_point: string; central_point_kept: '' | 'yes' | 'no'; hold_until: string;
  cta: string; decide_in_development: boolean; verified: string[]; overlap_acknowledged: boolean;
  // Ratings on review rubric 2.3a by criterion (E.X7): optional, but all or none.
  rubric: Record<string, number>;
}
export const emptyForm = (): DispositionForm => ({ disposition: 'develop', reason_code: '', note: '', author: '', reframe_title: '',
  reframe_point: '', central_point_kept: '', hold_until: '', cta: '', decide_in_development: true, verified: [], overlap_acknowledged: false,
  rubric: {} });

/** The request body for a card disposition, or the reason it cannot be sent yet (the server's own rules). */
export function cardDispositionBody(f: DispositionForm, card: Card, expectedHash: string, overlap: boolean, today = new Date().toISOString().slice(0, 10), ledger?: Ledger | null, rubric?: Rubric | null, oneClick = false):
  { body: Record<string, unknown> } | { error: string } {
  const rated = rubric ? rubric.criteria.filter(c => f.rubric[c.key]).length : 0;
  if (rubric && rated && rated < rubric.criteria.length) return { error: 'Rate the card on every rubric point, or on none.' };
  // The ratings go with the rubric version the form showed, which the server records (E.X7).
  const common = { expected_hash: expectedHash, disposition: f.disposition, note: f.note.trim() || null, author: f.author.trim() || null,
    reason_code: f.reason_code || null, ...(rubric && rated ? { rubric_ratings: f.rubric, rubric_version: rubric.version } : {}) };
  if (f.disposition !== 'develop' && !f.reason_code) return { error: 'Choose a reason.' };
  if (f.disposition === 'develop' && oneClick) {
    // The server takes the approval as the acknowledgement (gates.one_click).
    return { body: { ...common, cta: DECIDE_IN_DEVELOPMENT, verify_acknowledged: [...card.verify_before_publishing, ...blockingFlags(ledger).map(b => b.id)], overlap_acknowledged: overlap } };
  }
  if (f.disposition === 'develop') {
    const missing = card.verify_before_publishing.filter(v => !f.verified.includes(v));
    if (missing.length) return { error: 'Tick every "verify before publishing" item first.' };
    const blocking = blockingFlags(ledger);
    if (blocking.some(b => !f.verified.includes(b.id))) return { error: 'Check each blocking evidence flag against the call and tick it, or reframe the card instead.' };
    if (blocking.length && !f.note.trim()) return { error: 'Say in the note how you checked the blocking evidence flags.' };
    if (!f.decide_in_development && !f.cta.trim()) return { error: 'Write the CTA, or leave it to be decided in development.' };
    if (overlap && (!f.overlap_acknowledged || !f.note.trim())) return { error: 'This card overlaps another one: tick the overlap box and say in the note how it differs.' };
    return { body: { ...common, cta: f.decide_in_development ? DECIDE_IN_DEVELOPMENT : { text: f.cta.trim() },
      verify_acknowledged: [...card.verify_before_publishing, ...blocking.map(b => b.id)], overlap_acknowledged: f.overlap_acknowledged } };
  }
  if (f.disposition === 'reframe') {
    const reframe: Record<string, string> = {};
    if (f.reframe_title.trim()) reframe.title = f.reframe_title.trim();
    if (f.reframe_point.trim()) reframe.core_perspective = f.reframe_point.trim();
    if (!Object.keys(reframe).length) return { error: 'Write the reframed title or central point.' };
    if (!f.central_point_kept) return { error: 'Say whether the central point was kept.' };
    return { body: { ...common, reframe, central_point_kept: f.central_point_kept === 'yes' } };
  }
  if (f.disposition === 'hold') {
    if (!f.hold_until || f.hold_until <= today) return { error: 'Choose a date after today.' };
    return { body: { ...common, hold_until: f.hold_until } };
  }
  return { body: common };
}

export const blockingFlags = (ledger?: Ledger | null) => (ledger?.flags || []).filter(x => x.severity === 'block');
// Where on the card a flag points, in the reviewer's words (R50): never a field name or an index.
const FIELD_LABELS: Record<string, string> = { title: 'title', core_perspective: 'the point', point: 'the point', why_it_matters: 'why it matters',
  wia_in_action: 'WIA’s expertise or process', offer_connection: 'offer connection', evidence_points: 'evidence', moment_ids: 'the scenes it cites',
  card: 'the whole card', audience: 'who it is for', point_is_about: 'what the point is about', reader_takeaway: 'what the reader comes away thinking',
  surprise_for_experienced_advertiser: 'whether it surprises an owner who runs ads', reader_fit: 'who the reader is',
  belief_ref: 'the belief it proves', offer_fit: 'the offer and CTA', public_stance: 'public stance', guardrail: 'editorial guardrail' };
export function fieldLabel(field: string): string {
  const point = /^evidence_points\[(\d+)\]$/.exec(field);
  if (point) return `evidence point ${Number(point[1]) + 1}`;
  return FIELD_LABELS[field] || words(field);
}
// How the second check (a model from another family, E.B10) went, without naming the model.
export function modelCheckNote(modelPass: string): string {
  if (modelPass === 'not_run') return 'Checked by rule only; the second check runs with the weekly cycle.';
  if (modelPass === 'unavailable') return 'The second check was unavailable this week; only the rule checks ran. Tick each point under "Must be resolved" once you have checked it against the call.';
  return 'Also checked a second time.';
}
const READINESS: Record<Ledger['readiness'], string> = {
  ready: 'Evidence checked: nothing to resolve', needs_check: 'Evidence: some points need a look',
  research_required: 'Evidence: a blocking problem to resolve before developing',
};

/** The ledger, collapsed beneath the card (E.F2, E.B10). Blocking flags carry a tick box for the reviewer's check. */
export function LedgerPanel({ ledger, checked, onCheck, editable }: { ledger: Ledger; checked: string[]; onCheck: (id: string, on: boolean) => void; editable: boolean }) {
  const groups = [['block', 'Must be resolved'], ['check', 'Worth a look'], ['style', 'Style notes (warnings only)']] as const;
  return <details className="rounded-lg border p-3 text-sm" open={ledger.readiness === 'research_required'}>
    <summary className="cursor-pointer font-medium">{READINESS[ledger.readiness]}</summary>
    {groups.map(([severity, title]) => {
      const items = ledger.flags.filter(x => x.severity === severity);
      return items.length ? <div key={severity} className="mt-2"><p className="font-medium">{title}</p><ul className="ml-2 space-y-1">{items.map(x => <li key={x.id}>
        {severity === 'block' ? <label className="flex gap-2"><input type="checkbox" disabled={!editable} checked={checked.includes(x.id)} onChange={e => onCheck(x.id, e.target.checked)} />
          <span>{x.message} <span className="text-slate-500">({fieldLabel(x.field)})</span></span></label> : <span>{x.message} <span className="text-slate-500">({fieldLabel(x.field)})</span></span>}
      </li>)}</ul></div> : null;
    })}
    {!!ledger.qualifiers.length && <div className="mt-2"><p className="font-medium">Must stay true when developed</p><ul className="ml-6 list-disc">{ledger.qualifiers.map((q, i) => <li key={i}>{q}</li>)}</ul></div>}
    {ledger.critic && <p className="mt-2">Second opinion: WIA is the subject: {ledger.critic.wia_is_the_subject} · worth attention: {ledger.critic.worth_attention}. {ledger.critic.reason}</p>}
    <p className="mt-2 text-slate-500">{modelCheckNote(ledger.model_pass)}</p>
  </details>;
}

/** A transcript speaker as the reviewer should read it: roster name and role, or "client" / "prospect". Without a
    roster nobody can be told apart, so the transcript's own name is shown rather than calling WIA's team "client". */
export function speakerLabel(speaker: string | null, roster: RosterEntry[], recording = ''): string {
  if (!roster.length) return (speaker || '').trim() || 'Speaker';
  const name = (speaker || '').trim().toLowerCase();
  const entry = name ? roster.find(r => r.aliases.some(a => a.toLowerCase() === name || name.startsWith(a.toLowerCase() + ' '))) : undefined;
  if (entry?.status === 'current') return `${entry.name} (WIA, ${entry.role.split(/[.;:]/)[0]})`;
  if (entry?.status === 'former') return `${entry.name} (former WIA team member)`;
  if (entry?.status === 'outside') return `${entry.name} (${entry.role.split(/[.;:]/)[0]})`;
  return /sales|discovery|strategy call|audit|prospect|consult/i.test(recording) ? 'Prospect' : 'Client';
}

export function purposeMix(cards: Card[]): string {
  return PILLARS.map(p => [p, cards.filter(c => c.pillar === p).length] as const).filter(([, n]) => n).map(([p, n]) => `${n} ${p}`).join(' · ');
}

const time = (ms: number | null) => ms === null ? '' : `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`;
// A recorded decision in the words of the control that made it (R50), not its stored codes.
const dispositionLabel = (value: string) => DISPOSITIONS.find(d => d.value === value)?.label ?? (value === 'revive' ? 'Revived as a card' : words(value));
const reasonLabel = (code: string) => REASON_CODES.find(([value]) => value === code)?.[1] ?? words(code);
const decided = (d?: Disposition | null) => d ? `${dispositionLabel(d.disposition)}${d.reason_code ? ` (${reasonLabel(d.reason_code)})` : ''}${d.hold_until ? ` until ${d.hold_until}` : ''}` : null;

/** Review rubric 2.3a on the decision form (E.X3, E.X7): its text and version come from the API, so the form shows what the
    server records. Rating is optional; every point or none. Gate 2 rates a brief on the same rubric (E.X9). */
export function RubricRating({ rubric, name, value, onChange, what = 'card' }: { rubric: Rubric; name: string; value: Record<string, number>;
  onChange: (value: Record<string, number>) => void; what?: 'card' | 'brief' }) {
  return <details className="rounded-lg border p-3 text-sm"><summary className="cursor-pointer font-medium">Rate this {what} (optional)</summary>
    <p className="mt-2 text-slate-600">{rubric.instruction}</p>
    {rubric.criteria.map((c, i) => <div key={c.key} role="radiogroup" aria-label={c.name} className="mt-3">
      <p><strong>{i + 1}. {c.name}.</strong> {c.text}</p>
      <div className="flex gap-3 mt-1">{rubric.scale.map(n => <label key={n} className="flex gap-1">
        <input type="radio" name={`${name}-${c.key}`} checked={value[c.key] === n} onChange={() => onChange({ ...value, [c.key]: n })} />{n}</label>)}</div>
    </div>)}
  </details>;
}

/** Where a card stands, for its header. A card marked internal or skipped is closed (the API stores it as rejected). */
export function cardStatus(a: Pick<StoredAngle, 'approval_status' | 'has_replacement' | 'disposition' | 'matching_result'>): string {
  if (a.approval_status === 'approved') return 'Approved';
  if (a.has_replacement) return 'Replaced by a newer version';
  if (a.approval_status === 'rejected') {
    const disposition = a.disposition?.disposition;
    return disposition === 'internal' ? 'Kept for internal use, not public content' : disposition === 'skip' ? 'Skipped' : 'Not taken forward';
  }
  if (a.matching_result?.selection?.selection_status === 'suppressed') return 'Folded into a better-ranked idea (too similar)';
  return 'Waiting for your decision';
}

/** Cards the strategist's publishing order leaves for a later week (about three pieces a week, ruling R-10). */
export function heldCards(order: number[], cards: Card[]): Card[] {
  return cards.filter(card => !order.includes(card.rank)).sort((a, b) => a.rank - b.rank);
}

/** Why the strategist chose this week's cards. `bare` is the Weekly Studio's folded note (the mockup's grid with "Why these
    ideas" folded beneath it): no frame or heading of its own, and the considered ideas are listed with the other folded ideas. */
export function CardWeekPanel({ weekId, selection, cards, roster, busy, perform, canDecide = true, bare = false }: { weekId: string; selection: CardSelection; cards: { angle: StoredAngle; card: Card }[]; roster: RosterEntry[]; busy: boolean; perform: Perform; canDecide?: boolean; bare?: boolean }) {
  const byRank = new Map(cards.map(c => [c.card.rank, c.card]));
  return <section className={bare ? 'space-y-4 text-sm' : 'rounded-2xl border bg-white p-5 space-y-4'} aria-label="Why these cards">
    {!bare && <h2 className="font-editorial text-2xl text-[#173354]">Why these ideas</h2>}
    <p>{selection.week_summary}</p>
    {selection.plan_warning && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{selection.plan_warning}</p>}
    {!bare && <p className="text-sm"><strong>Purpose mix:</strong> {purposeMix(cards.map(c => c.card)) || 'No cards'}</p>}
    {!!selection.publishing_order?.length && <div className="text-sm"><strong>Proposed publishing order:</strong>
      <ol className="list-decimal ml-6 mt-1">{selection.publishing_order.map(rank => <li key={rank}>{byRank.get(rank)?.title || `Card ${rank}`}{byRank.get(rank)?.series ? ` · ${byRank.get(rank)!.series}` : ''}</li>)}</ol>
      {heldCards(selection.publishing_order, cards.map(c => c.card)).length > 0 && <p className="mt-1">Held for a later week: {heldCards(selection.publishing_order, cards.map(c => c.card)).map(c => c.title).join('; ')}</p>}</div>}
    {!bare && !!selection.pillar_notes?.length && <div className="text-sm"><strong>Other pillars this week:</strong><ul className="ml-6 list-disc">{selection.pillar_notes.map(n => <li key={n.pillar}>{n.pillar}: {n.note}</li>)}</ul></div>}
    {!!selection.seed_pairings?.length && <div className="text-sm"><strong>Your seeds:</strong><ul className="ml-6 list-disc">{selection.seed_pairings.map(s => <li key={s.seed_ref}>
      {s.seed_text ? <>“{s.seed_text}”: </> : null}{s.unanswered ? 'Not answered this week; it stays for the next cycle.' : s.moment_ids.length ? s.note : `No call evidence. ${s.note}`}</li>)}</ul></div>}
    {!bare && <details className="rounded-lg bg-slate-50 p-3"><summary className="font-medium">Considered and dropped ({selection.considered_not_selected.length})</summary>
      <ul className="mt-3 space-y-4">{selection.considered_not_selected.map(idea => <li key={idea.index} className="border-t pt-3">
        <ConsideredItem idea={idea} weekId={weekId} selection={selection} busy={busy} perform={perform} canDecide={canDecide} />
      </li>)}</ul></details>}
    {bare && <details className="rounded-lg bg-slate-50 p-3"><summary className="font-medium cursor-pointer">Details</summary>
      <p className="mt-2"><strong>Purpose mix:</strong> {purposeMix(cards.map(c => c.card)) || 'No cards'}</p>
      {!!selection.pillar_notes?.length && <div className="mt-2"><strong>Other pillars this week:</strong><ul className="ml-6 list-disc">{selection.pillar_notes.map(n => <li key={n.pillar}>{n.pillar}: {n.note}</li>)}</ul></div>}
    </details>}
    <details className="rounded-lg bg-slate-50 p-3"><summary className="font-medium">Internal insights ({selection.internal_insights.length})</summary>
      <ul className="mt-2 space-y-2 text-sm">{selection.internal_insights.map((i, n) => <li key={n}><p>{i.insight}</p><p className="text-slate-600">Use: {i.use}</p></li>)}</ul></details>
    {!bare && roster.length === 0 && <p className="text-sm text-amber-800">The team roster is not loaded, so speakers show as they appear in the transcript.</p>}
  </section>;
}

/** A considered idea the strategist did not choose, with revive and record-a-decision for a person who decides. */
export function ConsideredItem({ idea, weekId, selection, busy, perform, canDecide }: { idea: ConsideredIdea; weekId: string; selection: CardSelection; busy: boolean; perform: Perform; canDecide: boolean }) {
  const [open, setOpen] = useState<'' | 'revive' | 'other'>('');
  const [card, setCard] = useState({ title: idea.idea, pillar: 'WARM', content_type: 'behind_the_scenes', audience: '', why_it_matters: '' });
  const [reviveAuthor, setReviveAuthor] = useState('');
  const [other, setOther] = useState({ disposition: 'skip', reason_code: '', note: '', author: '', hold_until: '' });
  const base = `/weeks/${weekId}/considered/${idea.index}`;
  const done = decided(idea.disposition);
  const formId = (kind: string) => `considered-${idea.index}-${kind}`;
  // A saved decision closes its form; focus then moves to this idea's name (SQLWeeklyAngles, 6.F6).
  const save = (path: string, body: Record<string, unknown>) => void Promise.resolve(perform(path, 'POST', body)).then(ok => { if (ok) setOpen(''); });
  return <div className="space-y-2">
    <div className="flex flex-wrap items-center justify-between gap-3">
    <p tabIndex={-1} data-focus-key={`considered:${weekId}:${idea.index}`} className="text-[13px] font-medium text-[#34445F]">{idea.idea}{done && <span className="ml-2 text-[11px] font-normal text-[#7A8496]">· {done}</span>}</p>
    {idea.disposition?.disposition !== 'revive' && canDecide && <div className="flex gap-2">
      <button className={button} disabled={busy} aria-expanded={open === 'revive'} aria-controls={open === 'revive' ? formId('revive') : undefined} onClick={() => setOpen(open === 'revive' ? '' : 'revive')}>Revive as a card</button>
      <button className={button} disabled={busy} aria-expanded={open === 'other'} aria-controls={open === 'other' ? formId('other') : undefined} onClick={() => setOpen(open === 'other' ? '' : 'other')}>Record a decision</button></div>}
    </div>
    {open === 'revive' && <form id={formId('revive')} aria-label="Revive as a card" className="space-y-2" onSubmit={e => { e.preventDefault(); save(`${base}/revive`, { expected_hash: selection.selection_hash, card, author: reviveAuthor.trim() || null }); }}>
      <label className="block text-sm">Title<input className={field} required value={card.title} onChange={e => setCard({ ...card, title: e.target.value })} /></label>
      <div className="flex gap-3"><label className="text-sm">Pillar<Select className={field} value={card.pillar} onChange={e => setCard({ ...card, pillar: e.target.value })}>{PILLARS.map(p => <option key={p}>{p}</option>)}</Select></label>
        <label className="text-sm">Type<Select className={field} value={card.content_type} onChange={e => setCard({ ...card, content_type: e.target.value })}>{CONTENT_TYPES.map(t => <option key={t} value={t}>{words(t)}</option>)}</Select></label></div>
      <label className="block text-sm">Who it is for<input className={field} required value={card.audience} onChange={e => setCard({ ...card, audience: e.target.value })} /></label>
      <label className="block text-sm">Why it matters<textarea className={field} required value={card.why_it_matters} onChange={e => setCard({ ...card, why_it_matters: e.target.value })} /></label>
      <p className="text-sm text-slate-600">The new card is checked against earlier content before you can develop it.</p>
      <button className={button} disabled={busy}>Revive</button></form>}
    {open === 'other' && <form id={formId('other')} aria-label="Record a decision" className="space-y-2" onSubmit={e => { e.preventDefault(); save(`${base}/decision`, { expected_hash: selection.selection_hash, ...other, note: other.note || null, author: other.author || null, hold_until: other.disposition === 'hold' ? other.hold_until : null }); }}>
      <div className="flex gap-3"><label className="text-sm">Decision<Select className={field} value={other.disposition} onChange={e => setOther({ ...other, disposition: e.target.value })}>{DISPOSITIONS.filter(d => ['hold', 'internal', 'skip'].includes(d.value)).map(d => <option key={d.value} value={d.value}>{d.label}</option>)}</Select></label>
        <label className="text-sm">Reason<Select className={field} required value={other.reason_code} onChange={e => setOther({ ...other, reason_code: e.target.value })}><option value="">Choose…</option>{REASON_CODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></label></div>
      {other.disposition === 'hold' && <label className="block text-sm">Until<DateInput className={field} required value={other.hold_until} onChange={e => setOther({ ...other, hold_until: e.target.value })} /></label>}
      <label className="block text-sm">Note (optional)<textarea className={field} value={other.note} onChange={e => setOther({ ...other, note: e.target.value })} /></label>
      <button className={button} disabled={busy}>Save decision</button></form>}
  </div>;
}

type Stance = { takes_stance: boolean; stance: string | null };
const stanceOf = (card: Card) => (card as Card & { public_stance?: Stance | null }).public_stance ?? null;
/** Whether a card takes a public stance no approver has confirmed yet (D31): it cannot be developed until one does. */
export const stanceUnconfirmed = (a: Pick<StoredAngle, 'stance_confirmation'>, card: Card) => !!stanceOf(card)?.takes_stance && !a.stance_confirmation;

/** Why a card waiting for a decision cannot be developed yet, in the reviewer's words; null when it can. */
export function developBlocker(a: Pick<StoredAngle, 'can_approve' | 'matching_result'> & Partial<Pick<StoredAngle, 'public_use' | 'stance_confirmation' | 'removed_material' | 'check'>>, card?: Card, oneClick = false): string | null {
  // Built on material removed at a client's request (6.B12): never developed, whatever else is true of it.
  if (a.removed_material) return `${a.removed_material.note} It cannot be developed.`;
  if (a.public_use && !a.public_use.allowed) return 'This card is not for public content as it stands (see why above): reframe it, or mark it internal.';
  if (card && !oneClick && stanceUnconfirmed(a, card)) return 'This card takes a public stance: an approver confirms the stance above before it can be developed.';
  if (a.can_approve) return null;
  if (a.matching_result?.selection?.selection_status === 'suppressed') return 'This idea is too close to a better-ranked one to develop on its own.';
  if (a.check?.status === 'queued' || a.check?.status === 'running') return 'This new version is being checked against earlier content. It takes under a minute and this page updates by itself.';
  return 'This version has not been checked against earlier content yet, so it cannot be developed yet. The team runs that check; you can still reframe, hold, mark it internal or skip it.';
}

/** The card screen (E.F2). `bare` is its form inside the review dialog's "Content Angle" panel, without a frame of its own. The
    card reads in plain words first (its topic and editorial rationale, as on the Weekly Studio's card); every stored field,
    with the strategist's internal ones, is under Details. */
export function CardReview({ angle: a, card, roster, rubric, busy, perform, canDecide = true, bare = false }: { angle: StoredAngle; card: Card; roster: RosterEntry[]; rubric?: Rubric | null; busy: boolean; perform: Perform; canDecide?: boolean; bare?: boolean }) {
  const [showing, setShowing] = useState(false);
  const { evidence, error: evidenceError } = useMomentEvidence(a.moment_ids, showing);
  const oneClick = useOneClick();
  const [form, setForm] = useState<DispositionForm>(emptyForm);
  const [formError, setFormError] = useState('');
  const overlap = (a.matching_result?.current_batch_flags || []).length > 0;
  const ledger = a.content_body.ledger || null;
  const waiting = a.approval_status === 'pending' && !a.has_replacement;
  // The decision controls are offered only to a person the server lets decide (S.F1): anyone else reads the card.
  const pending = waiting && canDecide;
  const notReady = developBlocker(a, card, oneClick);
  const developReady = !notReady;
  const submit = () => {
    const result = cardDispositionBody(form, card, a.content_hash, overlap, undefined, ledger, rubric, oneClick);
    if ('error' in result) { setFormError(result.error); return; }
    setFormError(''); void perform(`/angles/${a.angle_id}/decision`, 'POST', result.body);
  };
  const set = (patch: Partial<DispositionForm>) => setForm({ ...form, ...patch });
  const made = a.content_body.refresh;
  // Editing, refreshing and adding context are an editor's or approver's (the server's can_edit), on a card waiting for a decision.
  const editable = waiting && !!a.can_edit;
  // Editing the text swaps the card for its editor (gates.one_click): nothing else is asked of the reviewer meanwhile.
  const [editing, setEditing] = useState(false);
  if (editing && editable) return <article id={`angle-${a.angle_id}`} className={bare ? 'space-y-4 text-[13px] text-[#34445F]' : 'rounded-2xl bg-white border p-5 space-y-4'}>
    <CardEditor angle={a} card={card} busy={busy} perform={perform} onClose={() => setEditing(false)} /></article>;
  return <article id={`angle-${a.angle_id}`} className={bare ? 'space-y-4 text-[13px] text-[#34445F]' : 'rounded-2xl bg-white border p-5 space-y-4'}>
    <header>
      <h2 className={bare ? 'sr-only' : 'font-editorial text-2xl'} tabIndex={-1} data-focus-key={`angle:${a.angle_id}:${a.content_hash}`}>{card.title}</h2>
      <div className={`flex flex-wrap items-center justify-between gap-3 ${bare ? '-mt-2' : 'mt-1'}`}>
        <p className="text-[12px] text-[#7A8496]">{cardStatus(a)}{a.disposition?.created_at && !waiting ? ` · ${cardDay(a.disposition.created_at)}` : ''}{a.hold ? ` · on hold until ${cardDay(a.hold.until)}` : ''}</p>
        {oneClick && editable && <button type="button" className={QUIET} disabled={busy || !!a.refresh && REFRESH_WORKING.includes(a.refresh.status)}
          title={a.refresh && REFRESH_WORKING.includes(a.refresh.status) ? 'A new version is being written. You can edit it when it is here.' : undefined} onClick={() => setEditing(true)}>Edit the text</button>}
      </div></header>
    {made && <RefreshedNote made={made} />}
    <RemovedMaterialNote removed={a.removed_material} />
    {a.public_use && !a.public_use.allowed && publicReasons(a).length > 0 && <PublicUseNote reasons={publicReasons(a)} />}
    <CardRationale card={card} full />
    {oneClick ? <StanceLine card={card} /> : <StancePanel angle={a} card={card} busy={busy} perform={perform} canConfirm={pending} />}
    <details className="rounded-xl border border-[#E6E9F0] bg-white p-4" onToggle={e => { if (e.currentTarget.open) setShowing(true); }}><summary className="cursor-pointer text-[13px] font-medium text-[#34445F]">What was said on the call</summary>
      {evidenceError && <p role="alert">{evidenceError}</p>}
      {evidence?.map((m, i) => <div key={i} className="mt-3 space-y-2">{m.passages.map(p => <blockquote key={p.passage_id} className="whitespace-pre-wrap text-[12.5px] leading-relaxed border-l-2 border-[#D9BE87] pl-3 text-[#4F5B6E]">
        <span className="block font-semibold text-[#34445F]">{speakerLabel(p.speaker, roster, p.title)}{p.start_ms !== null ? ` · ${time(p.start_ms)}` : ''}</span>“{p.text}”</blockquote>)}</div>)}</details>
    {oneClick && waiting && <FeedbackPanel angle={a} busy={busy} perform={perform} editable={editable} canApprove={pending} notReady={notReady} approve={submit} formError={formError} onEdit={() => setEditing(true)} />}
    {!oneClick && pending && card.verify_before_publishing.length > 0 && <div className="rounded-lg bg-amber-50 p-3 text-sm"><p className="font-medium">Verify before publishing</p>
      {card.verify_before_publishing.map(v => <label key={v} className="flex gap-2 mt-1"><input type="checkbox" disabled={!pending} checked={form.verified.includes(v)}
        onChange={e => set({ verified: e.target.checked ? [...form.verified, v] : form.verified.filter(x => x !== v) })} />{v}</label>)}</div>}
    {!oneClick && pending && ledger && <LedgerPanel ledger={ledger} checked={form.verified} editable={pending}
      onCheck={(id, on) => set({ verified: on ? [...form.verified, id] : form.verified.filter(x => x !== id) })} />}
    {!oneClick && !editable && <ContextPanel angle={a} busy={busy} perform={perform} canAdd={false} canAttest={false} />}
    {editable && !oneClick && <details className="rounded-xl border border-[#E6E9F0] bg-white p-4 [&>*+*]:mt-4">
      <summary className="cursor-pointer text-[13px] font-medium text-[#34445F]">Edit, add context or ask for a new version</summary>
      <CardEditor angle={a} card={card} busy={busy} perform={perform} />
      <ContextPanel angle={a} busy={busy} perform={perform} canAdd={editable} canAttest={canDecide} />
      <RefreshPanel angle={a} busy={busy} perform={perform} />
    </details>}
    {waiting && !canDecide && <p role="note" className="border-t pt-4 text-sm text-slate-600">{NO_DECIDE}</p>}
    {pending && <OtherOptions fold={oneClick}><fieldset className="rounded-xl border border-[#E6E9F0] bg-white p-4 space-y-3"><legend className="px-1 text-[13px] font-semibold text-[#34445F]">Your decision</legend>
      <div className="flex flex-wrap gap-2">{DISPOSITIONS.map(d => <label key={d.value} className={`${button} flex gap-2 items-center`} title={d.help}>
        <input type="radio" name={`disposition-${a.angle_id}`} checked={form.disposition === d.value} onChange={() => set({ disposition: d.value })} />{d.label}</label>)}</div>
      <p className="text-sm text-slate-600">{DISPOSITIONS.find(d => d.value === form.disposition)?.help}</p>
      {form.disposition === 'develop' && <>
        {notReady && <p className="text-sm text-amber-800">{notReady}</p>}
        <label className="flex gap-2 text-sm"><input type="checkbox" checked={form.decide_in_development} onChange={e => set({ decide_in_development: e.target.checked })} />Decide the CTA in development</label>
        {!form.decide_in_development && <label className="block text-sm">CTA<input className={field} value={form.cta} onChange={e => set({ cta: e.target.value })} /></label>}
        {overlap && <label className="flex gap-2 text-sm"><input type="checkbox" checked={form.overlap_acknowledged} onChange={e => set({ overlap_acknowledged: e.target.checked })} />This overlaps another card this week; my note says how it differs.</label>}
      </>}
      {form.disposition === 'reframe' && <>
        <label className="block text-sm">Reframed title<input className={field} value={form.reframe_title} onChange={e => set({ reframe_title: e.target.value })} /></label>
        <label className="block text-sm">Reframed central point (optional)<textarea className={field} value={form.reframe_point} onChange={e => set({ reframe_point: e.target.value })} /></label>
        <fieldset className="text-sm"><legend>Is the central point the same?</legend>
          <div className="mt-1 flex flex-wrap gap-4">
            <label className="flex gap-1"><input type="radio" name={`central-point-${a.angle_id}`} value="yes" checked={form.central_point_kept === 'yes'} onChange={() => set({ central_point_kept: 'yes' })} />Yes, a light reframe</label>
            <label className="flex gap-1"><input type="radio" name={`central-point-${a.angle_id}`} value="no" checked={form.central_point_kept === 'no'} onChange={() => set({ central_point_kept: 'no' })} />No, the point changed</label></div></fieldset>
      </>}
      {form.disposition === 'hold' && <label className="block text-sm">Hold until<DateInput className={field} value={form.hold_until} onChange={e => set({ hold_until: e.target.value })} /></label>}
      <label className="block text-sm">Reason{form.disposition === 'develop' ? ' (optional)' : ''}<Select className={field} value={form.reason_code} onChange={e => set({ reason_code: e.target.value })}><option value="">Choose…</option>{REASON_CODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></label>
      <label className="block text-sm">Note (optional)<textarea className={field} value={form.note} onChange={e => set({ note: e.target.value })} /></label>
      {formError && <p role="alert" className="text-sm text-red-800">{formError}</p>}
      <button className="rounded-full bg-[#1B2838] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#34445F] disabled:opacity-40" disabled={busy || (form.disposition === 'develop' && !developReady)} onClick={submit}>Save decision</button>
    </fieldset></OtherOptions>}
  </article>;
}

/** The card's public stance as a line of the card (gates.one_click): approving it confirms it. */
function StanceLine({ card }: { card: Card }) {
  const stance = stanceOf(card);
  if (!stance?.takes_stance) return null;
  return <section aria-label="Public stance" className={PANEL}><div className="mb-2"><span className={PANEL_HEADING}>Public stance</span></div>
    <p className="text-[12.5px] leading-relaxed text-[#34445F]">{stance.stance || card.point || card.core_perspective}</p></section>;
}

/** What a reviewer does with a card (gates.one_click): say what should change, or approve it. */
function FeedbackPanel({ angle, busy, perform, editable, canApprove, notReady, approve, formError, onEdit }: { angle: StoredAngle; busy: boolean; perform: Perform;
  editable: boolean; canApprove: boolean; notReady: string | null; approve: () => void; formError: string; onEdit: () => void }) {
  // A new version is on its way: this one is about to be replaced, so it is neither approved nor edited.
  const replacing = !!angle.refresh && REFRESH_WORKING.includes(angle.refresh.status);
  return <section aria-label="Your feedback" className={PANEL}>
    <div className="mb-3"><span className={PANEL_HEADING}>Your feedback</span></div>
    {editable && <RefreshPanel angle={angle} busy={busy} perform={perform} />}
    {(editable || canApprove) && <div className="mt-4 pt-4 border-t border-[#E6E9F0] space-y-3">
      {!replacing && notReady && <p className="text-[12px] text-amber-800">{notReady}</p>}
      {formError && <p role="alert" className="text-[12px] text-red-800">{formError}</p>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {editable ? <button type="button" className={QUIET} disabled={busy || replacing} onClick={onEdit}>Edit the text</button> : <span />}
        {canApprove && <div className="ml-auto flex flex-wrap items-center justify-end gap-3">
          {!notReady && !replacing && <TimeNote>The brief takes {TAKES.brief} to write.</TimeNote>}
          <button type="button" className={DARK} disabled={busy || !!notReady || replacing} onClick={approve}>Approve & create brief</button></div>}
      </div>
    </div>}
  </section>;
}

/** The hold, skip and other decisions, folded away when approving is one click. */
function OtherOptions({ fold, children }: { fold: boolean; children: React.ReactNode }) {
  if (!fold) return <>{children}</>;
  return <details className="rounded-xl border border-[#E6E9F0] bg-white p-4 [&>*+*]:mt-4"><summary className="cursor-pointer text-[13px] font-medium text-[#34445F]">Other options: hold, skip or mark internal</summary>{children}</details>;
}

// Shown in the card's header, or with their own controls below, so not repeated among its fields.
const SHOWN_ELSEWHERE = new Set(['title', 'pillar', 'content_type', 'series', 'verify_before_publishing', 'rank', 'moment_ids']);
const filled = (value: unknown) => value !== null && value !== undefined && value !== '' && !(Array.isArray(value) && !value.length);

/** The card's fields in Whitney's order (plan section 4.2), from the field map (3.F2): a new field shows here by its map entry. */
export function CardFieldList({ values }: { values: Record<string, unknown> }) {
  return <dl className="space-y-2">{Object.entries(CARD_FIELDS).filter(([name]) => !SHOWN_ELSEWHERE.has(name) && filled(values[name])).map(([name, f]) => {
    const value = values[name];
    return <div key={name}><dt className="text-xs uppercase tracking-wide text-slate-500">{f.label}</dt>
      <dd>{f.kind === 'list' && Array.isArray(value) ? <ul className="list-disc ml-6">{value.map((p, i) => <li key={i}>{String(p)}</li>)}</ul>
        : f.kind === 'record' ? recordText(f, value) : f.kind === 'choice' ? choiceLabel(String(value), f.choices) : String(value)}</dd></div>;
  })}</dl>;
}

/** Why a strategist v7 card is not for public content (E.B30), in the checks' own plain words. */
/** Why a card is not for public use, without the removal's note, which the card shows on its own line (6.B12). */
export const publicReasons = (a: Partial<Pick<StoredAngle, 'public_use' | 'removed_material'>>) =>
  (a.public_use?.reasons ?? []).filter(reason => reason !== a.removed_material?.note);

export function PublicUseNote({ reasons }: { reasons: string[] }) {
  return <div role="note" className="rounded-lg bg-red-50 p-3 text-sm text-red-900"><p className="font-medium">Not for public content as it stands</p>
    <ul className="ml-6 list-disc">{reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
    <p className="mt-1">Reframe it, or mark it internal if it is useful to the team.</p></div>;
}

/** A card that takes a public stance (D31): the stance, who confirmed it and when, or, for an approver, the confirmation. The
    server keeps the card from being developed until the stance is confirmed; an edit of the stance or the point drops it. */
export function StancePanel({ angle: a, card, busy, perform, canConfirm }: { angle: StoredAngle; card: Card; busy: boolean; perform: Perform; canConfirm: boolean }) {
  const [note, setNote] = useState('');
  const stance = stanceOf(card);
  if (!stance?.takes_stance) return null;
  const confirmed = a.stance_confirmation;
  const said = stance.stance || card.point || card.core_perspective || '';
  if (confirmed) return <p className="rounded-lg bg-emerald-50 p-3 text-sm">Public stance confirmed by {confirmed.by} on {confirmed.at.slice(0, 10)}: “{confirmed.stance || said}”.{confirmed.note ? ` Note: ${confirmed.note}` : ''}</p>;
  return <section className="rounded-lg bg-amber-50 p-3 text-sm space-y-2" aria-label="Public stance">
    <p className="font-medium">This card takes a public stance: “{said}”</p>
    <p>{canConfirm ? 'Please confirm it before the card is developed. To change its wording, edit the card or ask for a refreshed version below.' : 'An approver confirms it here.'}</p>
    {canConfirm && <>
      <textarea aria-label="Optional public stance note" placeholder="Note (optional)" className={field} value={note} onChange={e => setNote(e.target.value)} />
      <button type="button" className={button} disabled={busy} onClick={() => void perform(`/angles/${a.angle_id}/stance`, 'POST', { expected_hash: a.content_hash, note: note.trim() || null })}>Confirm this public stance</button>
    </>}
  </section>;
}

const KEPT_NOTE = 'Fields you edit are kept word for word, also when you ask for a refreshed version.';

// What the card shows, in its order; the strategist's own fields are folded beneath them.
const MAIN_FIELDS = new Set(['title', 'pillar', 'content_type', 'point', 'core_perspective', 'audience', 'why_it_matters', 'wia_in_action',
  'evidence_points', 'guardrail', 'offer_fit', 'public_stance', 'verify_before_publishing']);
const HALF_WIDTH = new Set(['pillar', 'content_type']);

/** Every card field, editable from the card screen (3.B7 a): built from the field map, so a new field needs one map entry. Only
    the fields whose text changed are sent; the server records them as written by a person. With `onClose` it stands in for the
    card itself, open at once, and closes when saved or cancelled. */
export function CardEditor({ angle: a, card, busy, perform, onClose }: { angle: StoredAngle; card: Card; busy: boolean; perform: Perform; onClose?: () => void }) {
  const values = card as unknown as Record<string, unknown>;
  const [open, setOpen] = useState(!!onClose);
  const [form, setForm] = useState(() => formValues(values));
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (onClose) heading.current?.focus(); }, []);
  const change = (key: string, value: string) => setForm(f => ({ ...f, [key]: value }));
  const start = formValues(values);
  const count = Object.keys(form).filter(key => form[key] !== start[key]).length;
  const kept = (form.verify_before_publishing ?? '').split('\n').map(line => line.trim());
  // The server asks why only when a person drops an item to verify, or edits a card on hold (S.B3).
  const needsNote = !!a.hold || card.verify_before_publishing.some(v => !kept.includes(v));
  const save = async () => {
    const result = cardChanges(values, form);
    if ('error' in result) { setError(result.error); return; }
    setError('');
    const saved = await perform(`/angles/${a.angle_id}`, 'PATCH', { expected_hash: a.content_hash, changes: result.changes, note: note.trim() || null });
    if (saved) onClose?.();
  };
  const fieldFor = (name: string) => {
    const f = CARD_FIELDS[name];
    const wide = HALF_WIDTH.has(name) ? '' : 'sm:col-span-2';
    const label = f.label + (f.optional ? ' (optional)' : '') + (f.kind === 'list' ? ' (one per line)' : '');
    if (f.kind === 'record') return <fieldset key={name} className="sm:col-span-2 grid grid-cols-1 gap-3 min-w-0"><legend className={`${EDIT_LABEL} mb-1`}>{f.label}</legend>
      {f.parts?.map(p => {
        const key = `${name}.${p.key}`;
        if (p.kind === 'check') return <label key={key} className="flex items-center gap-2 text-[12.5px] text-[#34445F]"><input type="checkbox" checked={form[key] === 'true'} onChange={e => change(key, String(e.target.checked))} />{p.label}</label>;
        if (p.neededWhen && form[`${name}.${p.neededWhen}`] !== 'true') return null;
        const partLabel = p.label + (p.optional && !p.neededWhen ? ' (optional)' : '');
        if (p.kind === 'choice') return <label key={key} className={EDIT_LABEL}>{partLabel}<Select className={EDIT_FIELD} value={form[key]} onChange={e => change(key, e.target.value)}>
          {p.options?.map(o => <option key={o} value={o}>{choiceLabel(o, p.choices)}</option>)}</Select></label>;
        return <label key={key} className={EDIT_LABEL}>{partLabel}{p.multiline
          ? <textarea className={EDIT_FIELD} rows={rowsFor(form[key])} value={form[key]} onChange={e => change(key, e.target.value)} />
          : <input className={EDIT_FIELD} value={form[key]} onChange={e => change(key, e.target.value)} />}</label>;
      })}</fieldset>;
    if (f.kind === 'choice') return <label key={name} className={`${EDIT_LABEL} ${wide}`}>{label}<Select className={EDIT_FIELD} value={form[name]} onChange={e => change(name, e.target.value)}>
      {f.options?.map(o => <option key={o} value={o}>{choiceLabel(o, f.choices)}</option>)}</Select></label>;
    return <label key={name} className={`${EDIT_LABEL} ${wide}`}>{label}{f.multiline
      ? <textarea className={EDIT_FIELD} rows={rowsFor(form[name], f.kind === 'list' ? 3 : 2)} value={form[name]} onChange={e => change(name, e.target.value)} />
      : <input className={EDIT_FIELD} value={form[name]} onChange={e => change(name, e.target.value)} />}</label>;
  };
  const names = editableFields(values);
  const main = names.filter(name => MAIN_FIELDS.has(name)), more = names.filter(name => !MAIN_FIELDS.has(name));
  return <section className={onClose ? 'space-y-4' : 'border-t pt-4 space-y-3'} aria-label="Edit this card">
    {onClose ? <div><h3 ref={heading} tabIndex={-1} className="font-editorial text-[19px] text-[#1B2433] outline-none">Edit the text</h3>
      <p className="mt-1 text-[12px] text-[#667184]">{KEPT_NOTE} Saving makes a new version straight away.</p></div>
      : <button type="button" className={button} disabled={busy} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Close the editor' : 'Edit this card'}</button>}
    {open && <>
      {!onClose && <p className="text-sm text-slate-600">{KEPT_NOTE} A new version is checked against earlier content before it can be developed.</p>}
      <div className={`${PANEL} grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-4`}>{main.map(fieldFor)}</div>
      {more.length > 0 && <details className={PANEL}><summary className="cursor-pointer text-[12px] font-medium text-[#34445F]">More fields: how the strategist reasoned about this angle</summary>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-4">{more.map(fieldFor)}</div></details>}
      {needsNote && <label className={`${PANEL} ${EDIT_LABEL}`}>Why are you changing this? {a.hold ? 'The card is on hold, and editing lifts the hold.' : 'You removed an item to verify.'}<textarea className={EDIT_FIELD} rows={2} value={note} onChange={e => setNote(e.target.value)} /></label>}
      <EditBar count={count} error={error} busy={busy} onCancel={onClose} onSave={() => void save()} saveLabel="Save my edits" />
    </>}
  </section>;
}

// A refresh in hand: this version is about to be replaced.
const REFRESH_WORKING = ['queued', 'running', 'waiting'];

/** Refresh with feedback (3.B7 b): a new version written from the reviewer's words. The fields she edited are kept word for
    word; a refresh waiting, being written or refused shows here with its reason. */
export function RefreshPanel({ angle: a, busy, perform }: { angle: StoredAngle; busy: boolean; perform: Perform }) {
  const pending = a.refresh;
  const [feedback, setFeedback] = useState(pending?.status === 'failed' ? pending.feedback : '');
  const [author, setAuthor] = useState('');
  const [error, setError] = useState('');
  const working = !!pending && REFRESH_WORKING.includes(pending.status);
  const kept = (a.content_body.person_edits || []).map(cardFieldLabel);
  const ask = () => {
    if (!feedback.trim()) { setError('Write what the refreshed version should change.'); return; }
    setError(''); void perform(`/angles/${a.angle_id}/refresh`, 'POST', { expected_hash: a.content_hash, feedback: feedback.trim(), author: author.trim() || null });
  };
  return <section className="space-y-3" aria-label="Refresh with feedback">
    {working && pending!.status !== 'waiting' && <div role="status" className="rounded-lg border border-[#D1DBFF] bg-[#F7F9FF] p-3 text-[12.5px] text-[#34445F] space-y-1.5">
      <p>A refreshed version is being written from this feedback: “{pending!.feedback}”. It replaces this card here when it is ready.</p>
      <TimeNote>This takes {TAKES.angleRefresh}. You can close this and come back.</TimeNote></div>}
    {pending?.status === 'waiting' && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">A refreshed version from this feedback, “{pending.feedback}”, is waiting for budget and starts by itself when there is room. {pending.message}</p>}
    {pending?.status === 'failed' && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">The refreshed version could not be written. {pending.message}</p>}
    {!working && <>
      <label className={EDIT_LABEL}>What should the refreshed version change?<textarea className={EDIT_FIELD} rows={3} value={feedback} onChange={e => setFeedback(e.target.value)} /></label>
      {kept.length > 0 && <p className="text-[12px] text-[#667184]">Kept word for word because you edited them: {kept.join(', ')}.</p>}
      {error && <p role="alert" className="text-[12px] text-red-800">{error}</p>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <TimeNote>The whole angle is rewritten. This takes {TAKES.angleRefresh}.</TimeNote>
        <button type="button" className={`ml-auto ${QUIET}`} disabled={busy} onClick={ask}>Ask for a refreshed version</button></div>
    </>}
  </section>;
}

/** Who wrote a refreshed version (R58): the model, from a reviewer's feedback; what it changed and what it kept. */
function RefreshedNote({ made }: { made: NonNullable<StoredAngle['content_body']['refresh']> }) {
  return <div className="rounded-lg bg-[#F4F6FA] p-3 text-sm space-y-2"><p className="font-medium">A new version, written from your feedback.</p>
    {made.reason && <p>{made.reason}</p>}
    <p className="text-[12px] text-[#667184]">{made.changed.length ? `Changed: ${made.changed.map(cardFieldLabel).join(', ')}.` : ''}
      {made.kept.length ? ` Kept word for word as a person wrote it: ${made.kept.map(cardFieldLabel).join(', ')}.` : ''}</p>
    <details><summary className="cursor-pointer text-[12px] font-medium text-[#34445F]">Your feedback</summary><p className="mt-1 whitespace-pre-wrap">{made.feedback}</p></details></div>;
}

/* Context and attested facts at Gate 1 (5.B7, common brief interface 2). The route and the card's `context_items` are the
   backend's (POST /angles/{id}/context); until the generated schema carries them, this is their agreed shape. */
export type ContextKind = 'context' | 'attested_fact' | 'paraphrase';
export interface CardContextItem { id: string; kind: ContextKind; text: string; author: string; created_at: string }
export const CONTEXT_KINDS: { value: ContextKind; label: string; help: string; approver?: boolean }[] = [
  { value: 'context', label: 'Context', help: 'Background for the writer. It is not quoted or stated as fact.' },
  { value: 'attested_fact', label: 'A fact I confirm is true', help: 'May be stated in the copy, marked as confirmed by you today.', approver: true },
  { value: 'paraphrase', label: 'What the client said, in my words', help: 'Used as a paraphrase, never quoted as their exact words.' },
];
const day = (iso: string) => iso.slice(0, 10);

export function contextItemLabel(item: CardContextItem): string {
  if (item.kind === 'attested_fact') return `Attested fact, confirmed by ${item.author} on ${day(item.created_at)}`;
  if (item.kind === 'paraphrase') return `Paraphrase of the client, added by ${item.author}; never quoted as their exact words`;
  return `Context from ${item.author}`;
}

export function ContextPanel({ angle: a, busy, perform, canAdd, canAttest }: { angle: StoredAngle; busy: boolean; perform: Perform; canAdd: boolean; canAttest: boolean }) {
  const items = ((a as StoredAngle & { context_items?: CardContextItem[] | null }).context_items) || [];
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<ContextKind>('context');
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const kinds = CONTEXT_KINDS.filter(k => !k.approver || canAttest);
  const add = async () => {
    if (!text.trim()) { setError('Write the context first.'); return; }
    setError('');
    if (await perform(`/angles/${a.angle_id}/context`, 'POST', { kind, text: text.trim() }) === true) { setText(''); setOpen(false); }
  };
  if (!items.length && !canAdd) return null;
  return <section className="border-t pt-4 space-y-2" aria-label="Context for this card">
    <p className="font-medium">Context for this card</p>
    {items.length ? <ul className="space-y-2 text-sm">{items.map(item => <li key={item.id} className={item.kind === 'attested_fact' ? 'rounded-lg bg-emerald-50 p-2' : ''}>
      <p className="text-xs uppercase tracking-wide text-slate-500">{contextItemLabel(item)}</p><p>{item.text}</p></li>)}</ul>
      : <p className="text-sm text-slate-600">None added yet.</p>}
    {canAdd && <button type="button" className={button} disabled={busy} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Close' : 'Add context or a fact'}</button>}
    {canAdd && open && <div className="space-y-2">
      <div role="radiogroup" aria-label="What are you adding?" className="space-y-1">{kinds.map(k => <label key={k.value} className="flex gap-2 text-sm">
        <input type="radio" name={`context-kind-${a.angle_id}`} checked={kind === k.value} onChange={() => setKind(k.value)} />
        <span><strong>{k.label}.</strong> {k.help}</span></label>)}</div>
      <label className="block text-sm">What do you want to add?<textarea className={field} rows={3} value={text} onChange={e => setText(e.target.value)} /></label>
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
      <button type="button" className={button} disabled={busy} onClick={() => void add()}>Add to this card</button>
    </div>}
  </section>;
}
