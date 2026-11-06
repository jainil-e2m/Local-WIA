import React, { useState } from 'react';
import { Layers, Mail, Video } from 'lucide-react';
import type { PackPieceV2, StoredPackV2 } from '../api/types';
import {
  choiceFor, editRequest, editorialText, findingText, isEditablePath, keepRequest,
  attestRequest, packFindings, pieceMeta, piecePlainText, pieceSections, pieceTitle, recordedTakeRequest, reelDirection,
  reelProduction, sectionText,
  type PackField, type PackFinding, type PackSection, type ReelDirection,
} from './packFields';
import { CopyButton, Fold, button, input, primary } from './packParts';
import { useSwapFocus } from './shared/a11y';
import { plainMessage } from '../utils/plainText';
import { PublicationStatus } from './PiecePublication';

/* One piece of a content pack (NP.F1, NP.F2, NP.F3): the card of the mock WIA saw on 20 October on real data, with its
   order badge, kind icon, meta line, working title and labelled sections, Copy for the piece and for each line; editing any
   line by its path (Gate 2's pattern: the drafted lines are saved together, and each becomes a locked line kept word for
   word); a lock mark with who wrote the line; the two toggles "What the system changed" (a word diff against the brief's
   copy, with the change record) and "Use the brief's line"; the published marks with "Mark published"; and, on a
   face-to-camera Reel, "Paste what you said" (NP.B14): the recorded take becomes the script word for word, and the caption
   and covers are written from it in a new version.
   Round 2 adds what sits beside the copy, never in it: "About this Reel" (its premise, takeaway and why it differs, with
   where its material is in the calls folded), the openings the writer weighed and why it chose one (folded), the editor's
   blocking notes where the line is, each kept with a reason or resolved by an edit, its craft notes folded, and an
   optional "why" with an edit. */

export type PackWrite = (path: string, method: 'POST' | 'PATCH', body: Record<string, unknown>) => Promise<true | undefined>;

const ICONS = { email: Mail, carousel: Layers, reel: Video } as const;

/** Why the pack's lines cannot be edited now, in words, or '' when they can. */
export function editBlockedReason(pack: Pick<StoredPackV2, 'can_edit' | 'run_active' | 'state' | 'manifest_hash'>): string {
  if (pack.state === 'superseded') return 'This is an earlier version of the pack. Open the newest version to edit it.';
  if (pack.run_active || pack.state === 'finishing') return 'A run is finishing this pack: editing, reverting and decisions open when it ends.';
  if (!pack.manifest_hash) return 'This pack has no finished version to edit yet.';
  if (!pack.can_edit) return 'Your role reads the pack; an editor or approver edits it.';
  return '';
}

function FieldRow({ piece, field, label, draft, setDraft, canEdit, findings, attest, narrow = false }: {
  piece: PackPieceV2; field: PackField; label: string; draft: string | undefined; setDraft: (value: string | undefined) => void; canEdit: boolean;
  findings: PackFinding[]; attest: (finding: PackFinding) => React.ReactNode; narrow?: boolean;
}) {
  const editable = canEdit && isEditablePath(piece, field.path);
  const id = `pack-${piece.key}-${field.path.replace(/[^A-Za-z0-9]/g, '-')}`;
  // A section of one line (a title, a date) has no line label: its Edit and Copy sit on the section's heading row. In a
  // third-width tile (the email's date, send time and recipients) that row is too narrow for both, and "Recipients" ran
  // under the links (N4's screens check), so there they sit on their own row under the text.
  const compact = !label;
  // Edit swaps the line for its field: focus goes into the field, and back to Edit on Cancel (6.F6).
  const swap = useSwapFocus(draft !== undefined);
  const controls = <span className={`${compact ? (narrow ? 'mt-1 flex items-center gap-3' : 'absolute right-4 top-3 flex items-center gap-3') : 'ml-auto flex items-center gap-3'} ${draft === undefined ? 'opacity-0 group-hover/section:opacity-100 focus-within:opacity-100 transition-opacity' : ''}`}>
    {editable && draft === undefined && <button ref={swap.controlRef} type="button" className="text-xs underline text-[#34445F]" aria-label={`Edit ${piece.label}: ${field.label}`} onClick={() => { swap.arm(); setDraft(field.text); }}>Edit</button>}
    {draft !== undefined && <button type="button" className="text-xs underline text-[#34445F]" aria-label={`Cancel editing ${piece.label}: ${field.label}`} onClick={() => { swap.arm(); setDraft(undefined); }}>Cancel</button>}
    <CopyButton text={field.text} label={`${piece.label}: ${field.label}`} />
  </span>;
  return <div className="py-1.5" data-path={field.path}>
    {!compact && <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      {label && <label htmlFor={draft !== undefined ? id : undefined} className="text-[11px] font-semibold text-[#34445F]">{label}</label>}
      {!compact && controls}
    </div>}
    {compact && !narrow && controls}
    {draft === undefined
      ? <p className="text-[13.5px] text-[#34445F] whitespace-pre-wrap leading-relaxed">{withBold(field.text)}</p>
      : field.multiline
        ? <textarea ref={swap.fieldRef} id={id} aria-label={`${piece.label}: ${field.label}`} className={input} rows={Math.min(14, Math.max(3, draft.split('\n').length + 1, Math.ceil(draft.length / 80)))} value={draft} onChange={e => setDraft(e.target.value)} />
        : <input ref={swap.fieldRef} id={id} aria-label={`${piece.label}: ${field.label}`} className={input} value={draft} onChange={e => setDraft(e.target.value)} />}
    {compact && narrow && controls}
    {findings.filter(f => f.severity === 'blocking').map(f => <div key={f.finding_id} className="mt-1 space-y-1.5 rounded-lg bg-red-50 px-2 py-1.5 text-[12px] text-red-800">
      <p>To resolve: {blockingText(f, piece.label)}</p>{attest(f)}</div>)}
  </div>;
}

/** A blocking finding's words on its line: an editor's without the piece's name, the others as before. */
const blockingText = (f: PackFinding, label: string) => f.source === 'editorial' ? editorialText(f, label) : plainMessage(findingText(f.message));

/** "Edit the sentence, or confirm it is true": the confirmation swaps itself for its field, and focus follows (6.F6). With
    `keep` it is an editor's finding: "Keep it", with why the line is fine as it is. */
function Attest({ finding, busy, onAttest, keep = false }: { finding: PackFinding; busy: boolean; onAttest: (findingId: string, statement: string) => Promise<true | undefined>; keep?: boolean }) {
  const [open, setOpen] = useState(false), [statement, setStatement] = useState(''), [error, setError] = useState('');
  const swap = useSwapFocus(open);
  if (!open) return <button ref={swap.controlRef} type="button" className={`${button} !px-3 !py-1 text-xs`} onClick={() => { swap.arm(); setOpen(true); }}>{keep ? 'Keep it' : 'It is true'}</button>;
  return <div className="space-y-2 text-[#34445F]">
    {keep
      ? <label className="block text-xs">Why is it fine as it is?<input ref={swap.fieldRef} className={input} maxLength={1000} value={statement} onChange={e => setStatement(e.target.value)} /></label>
      : <label className="block text-xs">How you know it is true (kept with the line)<textarea ref={swap.fieldRef} className={input} rows={3} value={statement} onChange={e => setStatement(e.target.value)} /></label>}
    {error && <p role="alert" className="text-xs text-red-800">{error}</p>}
    <div className="flex gap-2"><button type="button" className={`${primary} !px-3 !py-1 text-xs`} disabled={busy} onClick={async () => {
      if (statement.trim().length < 3) { setError(keep ? 'Say why the line is fine as it is.' : 'Say why the sentence is true, for the record.'); return; }
      setError('');
      if (await onAttest(finding.finding_id, statement)) setOpen(false);
    }}>Confirm</button><button type="button" className={`${button} !px-3 !py-1 text-xs`} onClick={() => { swap.arm(); setOpen(false); }}>Cancel</button></div>
  </div>;
}

/** The openings or premises the writer weighed for a piece, folded: each one, the chosen one marked, and why. */
function OpeningsConsidered({ choice }: { choice: NonNullable<ReturnType<typeof choiceFor>> }) {
  return <Fold summary={`Openings considered (${choice.options.length})`}>
    <ul className="space-y-1">{choice.options.map((o, i) => <li key={i} className={o.chosen ? 'text-[#34445F]' : undefined}>
      {o.chosen ? <><span aria-hidden="true" className="mr-1 text-[#5070FF]">✓</span><span className="sr-only">Chosen: </span></> : <span aria-hidden="true" className="mr-1">·</span>}{o.text}</li>)}</ul>
    {choice.why && <p className="mt-2"><span className="font-semibold text-[#34445F]">Why this one</span> · {choice.why}</p>}
  </Fold>;
}

/** About this Reel: the premise in a line, its takeaway and why it differs in small muted text, then two folds (where its
    material is in the calls, the openings considered). Direction for whoever makes the Reel; never copied with the copy. */
function AboutReel({ direction, choice }: { direction: ReelDirection; choice: ReturnType<typeof choiceFor> }) {
  return <section aria-label="About this Reel" className="space-y-1.5 rounded-xl border border-[#EEF0F4] px-4 py-3">
    <h5 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]">About this Reel</h5>
    <p className="text-[13px] leading-relaxed text-[#34445F]">{direction.premise}</p>
    {direction.takeaway && <p className="text-[12px] text-[#667184]"><span className="font-semibold text-[#34445F]">Takeaway</span> · {direction.takeaway}</p>}
    {direction.distinct && <p className="text-[12px] text-[#667184]"><span className="font-semibold text-[#34445F]">Why it's different</span> · {direction.distinct}</p>}
    {(direction.timestamps.length > 0 || choice) && <div className="flex flex-col gap-1.5 pt-1">
      {direction.timestamps.length > 0 && <Fold summary="Where this comes from in the calls">
        <ul className="space-y-1">{direction.timestamps.map((t, i) => <li key={i}>{t}</li>)}</ul></Fold>}
      {choice && <OpeningsConsidered choice={choice} />}
    </div>}
  </section>;
}

/** The copy as it will read: a **marked** phrase in bold. Copy keeps the marks for the email tool. */
export function withBold(text: string): React.ReactNode {
  const parts = text.split(/\*\*([^*]+)\*\*/g);
  return parts.length === 1 ? text : parts.map((part, i) => i % 2 ? <strong key={i} className="font-semibold">{part}</strong> : part);
}

function SectionBox({ piece, section, children }: { piece: PackPieceV2; section: PackSection; children: React.ReactNode }) {
  return <section aria-label={section.label} className={`group/section relative rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4 ${piece.channel === 'email' && section.layout !== 'third' ? '@lg:col-span-3' : ''}`}>
    <div className={`mb-1 flex flex-wrap items-baseline gap-2 ${section.fields.length === 1 && section.layout !== 'third' ? 'pr-24' : ''}`}>
      <h5 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#5070FF]">{section.label}</h5>
      {section.fields.length > 1 && <span className="ml-auto opacity-0 group-hover/section:opacity-100 focus-within:opacity-100 transition-opacity"><CopyButton text={sectionText(section)} label={`${piece.label}: ${section.label}`}>Copy section</CopyButton></span>}
    </div>
    {children}
  </section>;
}

/** The post-recording pass (NP.B14): what Whitney said on the recorded take becomes the Reel's script, word for word, and the
    caption and three covers are written from it; the new version goes back to review. */
function RecordedTake({ piece, busy, write, packId, manifest }: { piece: PackPieceV2; busy: boolean; write: PackWrite; packId: string; manifest: string }) {
  const [open, setOpen] = useState(false), [said, setSaid] = useState(''), [error, setError] = useState('');
  const swap = useSwapFocus(open);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const request = recordedTakeRequest(manifest, said);
    if ('error' in request) { setError(request.error); return; }
    setError('');
    if (await write(`/packs/${packId}/pieces/${piece.key}/recorded`, 'POST', request.body)) { setOpen(false); setSaid(''); }
  };
  if (!open) return <button ref={swap.controlRef} type="button" className={button} onClick={() => { swap.arm(); setOpen(true); }}>Paste what you said</button>;
  const id = `pack-${piece.key}-recorded-take`;
  return <form onSubmit={e => void submit(e)} aria-label={`${piece.label}: paste what you said`} className="space-y-3 rounded-xl border border-[#E6E9F0] bg-[#F7F8FB] p-4">
    <p className="text-sm text-slate-600">Paste the recorded take's transcript, start to end. It becomes this Reel's script word for word, and the caption and three cover options are written from what was said. The new version goes back to review; it takes a minute or two and uses this week's packs budget.</p>
    <label htmlFor={id} className="block text-sm">What Whitney said on the take</label>
    <textarea ref={swap.fieldRef} id={id} className={input} rows={10} value={said} onChange={e => setSaid(e.target.value)} />
    {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
    <div className="flex flex-wrap gap-2"><button type="submit" className={primary} disabled={busy}>Write the caption and covers from it</button>
      <button type="button" className={button} onClick={() => { swap.arm(); setOpen(false); }}>Cancel</button></div>
  </form>;
}

/** One piece's card and panel. It stays mounted while another tab is shown, so a draft survives switching tabs. */
export function PieceCard({ piece, pack, active, busy, write }: { piece: PackPieceV2; pack: StoredPackV2; active: boolean; busy: boolean; write: PackWrite }) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const sections = pieceSections(piece);
  const fields = sections.flatMap(s => s.fields);
  const blocked = editBlockedReason(pack);
  const canEdit = !blocked;
  const findings = packFindings(pack).filter(f => f.piece === piece.key && f.status === 'open');
  const atPath = (path: string) => findings.filter(f => f.path === path);
  const elsewhere = findings.filter(f => !f.path || !fields.some(x => x.path === f.path));
  const pending = Object.keys(drafts).length;
  // An editor's blocking finding is kept with a reason on the attestation's route; a fidelity finding is attested true.
  const attestFor = (finding: PackFinding) => finding.can_attest && pack.can_decide && !pack.run_active && pack.state !== 'superseded' && pack.manifest_hash
    ? <Attest finding={finding} busy={busy} keep={finding.source === 'editorial'} onAttest={(findingId, statement) => {
        const request = (finding.source === 'editorial' ? keepRequest : attestRequest)(pack.manifest_hash ?? '', statement);
        return 'body' in request ? write(`/packs/${pack.pack_id}/findings/${findingId}/attest`, 'POST', request.body) : Promise.resolve(undefined);
      }} />
    : null;
  const notes = findings.filter(f => f.source === 'editorial' && f.severity === 'warning');
  const direction = reelDirection(piece);
  const choice = choiceFor(pack, piece.key);
  const Icon = ICONS[piece.channel] ?? Video;
  const written = piece.origin !== 'not_written' && !!piece.content;
  const save = async () => {
    const request = editRequest(pack.manifest_hash, fields, drafts, reason);
    if ('error' in request) { setError(request.error); return; }
    setError('');
    if (await write(`/packs/${pack.pack_id}/pieces/${piece.key}`, 'PATCH', request.body)) { setDrafts({}); setReason(''); }
  };
  const setDraft = (path: string) => (value: string | undefined) => setDrafts(d => {
    const next = { ...d };
    if (value === undefined) delete next[path]; else next[path] = value;
    return next;
  });
  return <article id={`pack-piece-panel-${piece.key}`} role="tabpanel" aria-labelledby={`pack-piece-tab-${piece.key}`} hidden={!active} tabIndex={0}
    className="space-y-4 rounded-2xl border border-[#E6E9F0] bg-white p-6 shadow-[0_3px_18px_rgba(28,36,52,0.035)]">
    <div className="flex items-start justify-between gap-3 border-b border-[#EEF0F4] pb-4">
      <div className="flex min-w-0 items-start gap-2.5">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-[#D1DBFF] bg-[#EFF3FF] font-mono text-xs font-bold tabular-nums text-[#5070FF]">
          {String(piece.ordinal).padStart(2, '0')}</span>
        <div className="min-w-0">
          <p className={`flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider ${piece.channel === 'reel' ? 'font-semibold text-[#A38B61]' : 'text-[#87725F]'}`}>
            <Icon aria-hidden="true" strokeWidth={1.5} className="h-3.5 w-3.5" />{pieceMeta(piece)}</p>
          <h3 className="font-editorial text-lg font-bold leading-snug text-[#221E17]" tabIndex={-1} data-focus-key={`pack:${pack.pack_id}:piece:${piece.key}`}>{written ? pieceTitle(piece) : `${piece.label}: not written`}</h3>
        </div>
      </div>
      <CopyButton text={piecePlainText(piece)} label={`${piece.label}, every section`} />
    </div>
    <PublicationStatus piece={piece} />
    {!written ? <div role="status" className="rounded-xl border border-dashed border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
      <p className="font-semibold">Not written</p><p>{piece.not_written_reason || 'This piece was not written.'}</p></div> : <>
      {direction && <AboutReel direction={direction} choice={choice} />}
      {/* The quiet folds under the header: the openings weighed (when no About block holds them) and the editor's craft notes. */}
      {((!direction && choice) || notes.length > 0) && <div className="flex flex-wrap items-start gap-x-6 gap-y-1.5">
        {!direction && choice && <OpeningsConsidered choice={choice} />}
        {notes.length > 0 && <Fold summary={`Editor's notes (${notes.length})`}>
          <ul className="space-y-1">{notes.map(f => <li key={f.finding_id}>{editorialText(f, piece.label)}</li>)}</ul></Fold>}
      </div>}
      {/* The email's three header tiles sit side by side only when the piece column is wide enough (a container query): beside
          the sidebar and the review column, a wide screen can still leave the column too narrow for three (N4). */}
      <div className={piece.channel === 'email' ? '@container' : undefined}>
      <div className={piece.channel === 'email' ? 'grid grid-cols-1 gap-3 @lg:grid-cols-3' : 'space-y-3'}>
        {sections.map(s => <SectionBox key={s.id} piece={piece} section={s}>
          {s.fields.map(f => <FieldRow key={f.path} piece={piece} field={f} label={s.fields.length === 1 && f.label === s.label ? '' : f.label}
            draft={drafts[f.path]} setDraft={setDraft(f.path)} canEdit={canEdit} findings={atPath(f.path)} attest={attestFor} narrow={s.layout === 'third'} />)}
        </SectionBox>)}
      </div>
      </div>
      {elsewhere.some(f => f.severity === 'blocking') && <ul className="space-y-1 text-[12px]">{elsewhere.filter(f => f.severity === 'blocking').map(f => <li key={f.finding_id} className="space-y-1.5 rounded-lg bg-red-50 px-2 py-1.5 text-red-800">
        <p>To resolve: {blockingText(f, piece.label)}</p>{attestFor(f)}</li>)}</ul>}
      {(pending > 0 || error) && <div className="sticky bottom-2 flex flex-wrap items-center gap-3 rounded-xl border border-[#D1DBFF] bg-[#EFF3FF] p-3">
        <p className="text-sm text-[#173354]">{pending} {pending === 1 ? 'line' : 'lines'} changed. Saving creates a new version.</p>
        <input aria-label="Why this change? (optional, helps the system learn)" placeholder="Why this change? (optional, helps the system learn)" maxLength={1000}
          className="min-w-[14rem] flex-1 rounded-lg border border-[#D8DFE8] bg-white px-3 py-2 text-[13px] text-[#34445F] placeholder:text-[#9AA3B2]"
          value={reason} onChange={e => setReason(e.target.value)} />
        {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
        <button type="button" className={primary} disabled={busy || !pending || !canEdit} onClick={() => void save()}>Save {pending} {pending === 1 ? 'change' : 'changes'}</button>
        <button type="button" className={button} disabled={busy} onClick={() => { setDrafts({}); setReason(''); setError(''); }}>Discard</button>
      </div>}
      {canEdit && (piece.key === 'reel_1' || piece.key === 'reel_2') && reelProduction(piece) !== 'on_screen_text' &&
        <RecordedTake piece={piece} busy={busy} write={write} packId={pack.pack_id} manifest={pack.manifest_hash ?? ''} />}
    </>}
  </article>;
}
