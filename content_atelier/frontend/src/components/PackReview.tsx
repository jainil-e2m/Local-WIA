import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import type { PackNoteV2, PackQuoteV2, StoredPackV2 } from '../api/types';
import {
  VERSION_LABELS, attestRequest, clearanceRequest, decisionRequest, findingText, packFindings, refinishRequest, type PackFinding,
} from './packFields';
import type { PackWrite } from './PackPiece';
import { button, input, primary, shortDate } from './packParts';
import { useSwapFocus } from './shared/a11y';
import { RemovedMaterialNote } from './BriefEditing';
import { useModalBehavior } from './useModalBehavior';
import { personName } from './studio/parts';
import { TAKES } from './studio/GenerationTime';

/* The review panel of a content pack (NP.F3; the content-packs plan, sections 4.1, 4.5 and 5.7): what stops Ready, named
   (`ready_blockers`, R50); blocking findings in plain words, each with "Attest it is true" where allowed (R57); the
   before-publishing notes and client quotes, each markable done with an optional reference (a client's permission is a note
   for whoever posts the piece, never a blocker); stronger with permission, where an approver grants an item or states a fact
   in their own words and the pack is finished again with them as evidence (NP.B15), and what was granted; the personal lines
   to keep or cut; Finish again (confirmed first); Ready to publish and Back to review; and the versions. */

const words = (s: string) => s.replaceAll('_', ' ');
/** Who did something on the pack, as a person reads it: a name, or "the team" for an address or a delegated approval. */
const who = (by: string | null | undefined) => personName(by) || 'the team';
const card = 'rounded-xl border border-[#E0DFE2] bg-white p-4 space-y-2';

/** A note or quote marked done. It replaces the Mark done control, so after the write focus moves here (`focus`, 6.F6). */
function Done({ done, verb, focus }: { done: NonNullable<PackNoteV2['done']>; verb: string; focus?: string }) {
  return <p className="text-xs text-emerald-800" tabIndex={focus ? -1 : undefined} data-focus-key={focus}>{verb} by {who(done.by)} on {shortDate(done.at)}{done.delegated ? ' (delegated)' : ''}{done.reference ? ` · ${done.reference}` : ''}{done.note ? ` · ${done.note}` : ''}</p>;
}

/** Marks a note done or a quote cleared, with an optional reference (where the okay was given). */
function MarkDone({ itemId, label, action, busy, enabled, onDone }: { itemId: string; label: string; action: string; busy: boolean; enabled: boolean;
  onDone: (itemId: string, reference: string) => Promise<true | undefined> }) {
  const [open, setOpen] = useState(false), [reference, setReference] = useState('');
  // The control swaps itself for its form: focus goes to the reference field, and back to the control on Cancel (6.F6).
  const swap = useSwapFocus(open);
  if (!enabled) return null;
  if (!open) return <button ref={swap.controlRef} type="button" className={`${button} !px-3 !py-1 text-xs`} onClick={() => { swap.arm(); setOpen(true); }} aria-label={`${action}: ${label}`}>{action}</button>;
  return <div className="space-y-2">
    <label className="block text-xs">Reference (optional: where the okay was given, or what was checked)<input ref={swap.fieldRef} className={input} value={reference} onChange={e => setReference(e.target.value)} /></label>
    <div className="flex gap-2"><button type="button" className={`${primary} !px-3 !py-1 text-xs`} disabled={busy} onClick={async () => { if (await onDone(itemId, reference)) setOpen(false); }}>{action}</button>
      <button type="button" className={`${button} !px-3 !py-1 text-xs`} onClick={() => { swap.arm(); setOpen(false); }}>Cancel</button></div>
  </div>;
}

function Attest({ finding, busy, onAttest }: { finding: PackFinding; busy: boolean; onAttest: (findingId: string, statement: string) => Promise<true | undefined> }) {
  const [open, setOpen] = useState(false), [statement, setStatement] = useState(''), [error, setError] = useState('');
  const swap = useSwapFocus(open);
  if (!open) return <button ref={swap.controlRef} type="button" className={`${button} !px-3 !py-1 text-xs`} onClick={() => { swap.arm(); setOpen(true); }}>Attest it is true</button>;
  return <div className="space-y-2">
    <label className="block text-xs">How you know it is true (kept with the attestation)<textarea ref={swap.fieldRef} className={input} rows={3} value={statement} onChange={e => setStatement(e.target.value)} /></label>
    {error && <p role="alert" className="text-xs text-red-800">{error}</p>}
    <div className="flex gap-2"><button type="button" className={`${primary} !px-3 !py-1 text-xs`} disabled={busy} onClick={async () => {
      if (statement.trim().length < 3) { setError('Say why the sentence is true, for the record.'); return; }
      setError('');
      if (await onAttest(finding.finding_id, statement)) setOpen(false);
    }}>Attest it is true</button><button type="button" className={`${button} !px-3 !py-1 text-xs`} onClick={() => { swap.arm(); setOpen(false); }}>Cancel</button></div>
  </div>;
}

/** One item of Stronger with permission: Grant swaps itself for the statement field, and focus follows (6.F6). */
function GrantItem({ text, enabled, open, statement, onOpen, onStatement }: { text: string; enabled: boolean; open: boolean; statement: string;
  onOpen: (open: boolean) => void; onStatement: (statement: string) => void }) {
  const swap = useSwapFocus(open);
  return <li className="space-y-1 rounded-lg bg-[#F7F8FB] p-3 text-sm [overflow-wrap:anywhere]">
    <p>{text}</p>
    {enabled && (!open ? <button ref={swap.controlRef} type="button" className={`${button} !px-3 !py-1 text-xs`} aria-label={`Grant: ${text}`} onClick={() => { swap.arm(); onOpen(true); }}>Grant</button>
      : <><label className="block text-xs">What may now be said (your words; kept with the grant)<textarea ref={swap.fieldRef} className={input} rows={2} value={statement}
        onChange={e => onStatement(e.target.value)} /></label>
        <button type="button" className={`${button} !px-3 !py-1 text-xs`} onClick={() => { swap.arm(); onOpen(false); }}>Don't grant</button></>)}
  </li>;
}

/** Stronger with permission (NP.B15): each item the finisher listed, grantable in the approver's own words, and a fact they
    state; "Finish again with these" runs the finisher with them as evidence, attested with the person and date (R57). */
function Grants({ pack, busy, enabled, write }: { pack: StoredPackV2; busy: boolean; enabled: boolean; write: PackWrite }) {
  const [statements, setStatements] = useState<Record<string, string>>({});
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [fact, setFact] = useState(''), [error, setError] = useState('');
  const items = pack.stronger_with_permission.map((text, i) => ({ id: `S${i + 1}`, text }));
  const submit = async () => {
    const grants = [...items.filter(i => open[i.id]).map(i => ({ item_id: i.id, statement: statements[i.id] ?? '' })),
      ...(fact.trim() ? [{ item_id: null, statement: fact }] : [])];
    const request = refinishRequest(pack.manifest_hash ?? '', grants);
    if ('error' in request) { setError(request.error); return; }
    setError('');
    if (await write(`/packs/${pack.pack_id}/refinish`, 'POST', request.body)) { setStatements({}); setOpen({}); setFact(''); }
  };
  const chosen = items.some(i => open[i.id]) || !!fact.trim();
  return <section className={card} aria-label="Stronger with permission">
    <h2 className="font-semibold text-[#173354]">Stronger with permission</h2>
    <p className="text-xs text-slate-600">What the pack could say if the client agrees. Grant an item, in your own words, or state a fact, and the pack is finished again with it as evidence. Each grant is kept as attested by you.</p>
    {items.length > 0 && <ul className="space-y-2">{items.map(i => <GrantItem key={i.id} text={i.text} enabled={enabled} open={!!open[i.id]} statement={statements[i.id] ?? ''}
      onOpen={value => setOpen(o => ({ ...o, [i.id]: value }))} onStatement={value => setStatements(s => ({ ...s, [i.id]: value }))} />)}</ul>}
    {enabled && <label className="block text-xs">A fact to add (optional: something true the pack may say)<textarea className={input} rows={2} value={fact} onChange={e => setFact(e.target.value)} /></label>}
    {error && <p role="alert" className="text-xs text-red-800">{error}</p>}
    {enabled && <button type="button" className={primary} disabled={busy || !chosen} onClick={() => void submit()}>Finish again with these</button>}
    {pack.granted.length > 0 && <>
      <h3 className="pt-2 text-sm font-semibold">Granted</h3>
      <ul className="space-y-1 text-sm">{pack.granted.map((g, i) => <li key={i} className="[overflow-wrap:anywhere]">{g.item ? `${g.item} · ` : ''}“{g.statement}”
        <span className="text-xs text-slate-600"> · attested by {who(g.by)} on {shortDate(g.at)}{g.delegated ? ' (delegated)' : ''}</span></li>)}</ul>
    </>}
  </section>;
}

/** Why Ready to publish cannot be pressed now, beyond the named blockers: the state, the run, the role. */
export function readyUnavailable(pack: Pick<StoredPackV2, 'state' | 'run_active' | 'can_decide' | 'manifest_hash'>): string {
  if (pack.state === 'superseded') return 'This is an earlier version: open the newest version to decide on it.';
  if (pack.run_active || pack.state === 'finishing') return 'The pack is still being finished.';
  if (pack.state === 'waiting') return 'The pack is waiting to continue; it opens for review when it is finished.';
  if (!pack.manifest_hash) return 'The pack has no finished version yet.';
  if (!pack.can_decide) return 'An approver marks a pack ready to publish.';
  return '';
}

/** Finish again's confirmation, shown in place: focus moves to Cancel, stays inside until the person answers, Escape cancels,
    and focus goes back to Finish again (6.F6). */
function ConfirmFinish({ busy, onConfirm, onCancel }: { busy: boolean; onConfirm: () => void; onCancel: () => void }) {
  const dialog = useModalBehavior(onCancel, { lockScroll: false });
  return <div ref={dialog} role="alertdialog" aria-modal="true" aria-labelledby="pack-finish-again-question" tabIndex={-1} className="space-y-2 rounded-lg bg-amber-50 p-3 text-sm">
    <p id="pack-finish-again-question">Finish this pack again? It runs the writing steps again, which takes {TAKES.pack}, and makes a new version that goes back to review.</p>
    <div className="flex gap-2"><button type="button" className={primary} disabled={busy} onClick={onConfirm}>Yes, finish again</button>
      <button type="button" className={button} data-autofocus onClick={onCancel}>Cancel</button></div>
  </div>;
}

export function PackReview({ pack, busy, write, onShowPiece, versionHref }: { pack: StoredPackV2; busy: boolean; write: PackWrite; onShowPiece: (key: string) => void;
  versionHref: (packId: string) => string }) {
  const [note, setNote] = useState('');
  const [confirmFinish, setConfirmFinish] = useState(false);
  const manifest = pack.manifest_hash ?? '';
  const findings = packFindings(pack);
  const label = (key: string | null | undefined) => pack.pieces.find(p => p.key === key)?.label ?? (key ? words(key) : 'The pack');
  const blocking = findings.filter(f => f.status === 'open' && f.severity === 'blocking');
  const warnings = findings.filter(f => f.status === 'open' && f.severity === 'warning');
  const resolved = findings.filter(f => f.status !== 'open');
  const unavailable = readyUnavailable(pack);
  const canAct = !pack.run_active && pack.state !== 'superseded' && !!manifest && pack.can_decide;
  const decide = (decision: 'ready_to_publish' | 'in_review') => {
    const request = decisionRequest(manifest, decision, note);
    if ('body' in request) void write(`/packs/${pack.pack_id}/decision`, 'POST', request.body).then(ok => { if (ok) setNote(''); });
  };
  const clear = (itemId: string, reference: string) => {
    const request = clearanceRequest(manifest, itemId, reference);
    return 'body' in request ? write(`/packs/${pack.pack_id}/clearances`, 'POST', request.body) : Promise.resolve(undefined);
  };
  const attest = (findingId: string, statement: string) => {
    const request = attestRequest(manifest, statement);
    return 'body' in request ? write(`/packs/${pack.pack_id}/findings/${findingId}/attest`, 'POST', request.body) : Promise.resolve(undefined);
  };
  const personal = pack.pieces.filter(p => p.channel === 'reel' && Array.isArray(p.content?.personal_lines) && (p.content.personal_lines as unknown[]).length > 0);
  // A note can carry an unbroken id ("prior angle angle_b8c6…"), which ran past its box on a phone (N4): it may break anywhere.
  const notes = (items: PackNoteV2[]) => items.map(n => <li key={n.id} className="space-y-1 rounded-lg bg-[#F7F8FB] p-3 [overflow-wrap:anywhere]">
    <p className="text-sm">{n.text}{n.required ? ' (required)' : ''}</p>
    {n.client_permission && <p className="text-xs text-slate-600">A note for whoever posts the piece: confirm the client's okay first. It never blocks Ready.</p>}
    {n.answer && <p className="text-xs text-slate-600">Answered with the brief: {n.answer}</p>}
    {n.done ? <Done done={n.done} verb="Marked done" focus={`pack:${pack.pack_id}:done:${n.id}`} /> : <MarkDone itemId={n.id} label={n.text} action="Mark done" busy={busy} enabled={canAct} onDone={clear} />}
  </li>);
  const quotes = (items: PackQuoteV2[]) => items.map(q => <li key={q.quote_id} className="space-y-1 rounded-lg bg-[#F7F8FB] p-3 [overflow-wrap:anywhere]">
    <blockquote className="text-sm">“{q.quote}”</blockquote>
    <p className="text-xs text-slate-600">{q.speaker ? `${q.speaker} · ` : ''}{label(q.piece)} · a note for whoever posts: the client okays their words before posting</p>
    {q.cleared ? <Done done={q.cleared} verb="Cleared" focus={`pack:${pack.pack_id}:done:${q.quote_id}`} /> : <MarkDone itemId={q.quote_id} label={q.quote} action="Mark cleared" busy={busy} enabled={canAct} onDone={clear} />}
  </li>);

  // The removal's note is shown on its own line; the same sentence among the blockers is not said twice.
  const removedNote = pack.removed_material?.note?.trim();
  const others = pack.ready_blockers.filter(b => !removedNote || (b.trim() !== removedNote && findingText(b).trim() !== removedNote));
  const waitsOn = others.length + (removedNote ? 1 : 0);
  return <aside aria-label="Review the pack" className="min-w-0 space-y-4">
    <section className={card} aria-label="Ready to publish">
      <h2 className="font-editorial text-xl text-[#173354]" tabIndex={-1} data-focus-key={`pack:${pack.pack_id}:ready`}>Ready to publish</h2>
      {pack.state === 'ready_to_publish' ? <>
        <p className="text-sm">Marked ready{personName(pack.approved_by) ? ` by ${personName(pack.approved_by)}` : ''}{pack.approved_at ? ` on ${shortDate(pack.approved_at)}` : ''}{pack.approval_delegated ? ' (under delegation)' : ''}. Mark each piece published as it goes out.</p>
        <label className="block text-xs">Note (optional)<input className={input} value={note} onChange={e => setNote(e.target.value)} /></label>
        <button type="button" className={button} disabled={busy || !canAct} onClick={() => decide('in_review')}>Back to review</button>
      </> : <>
        {pack.ready_blockers.length > 0 || pack.removed_material
          ? <div role="status" aria-label="What stops Ready"><p className="text-sm font-medium">Ready to publish waits on {waitsOn === 1 ? 'one thing' : `${waitsOn} things`}:</p>
            {/* Built on material removed at a client's request (6.B12): the removal's note, with its day, first. */}
            <RemovedMaterialNote removed={pack.removed_material} />
            {others.length > 0 && <ul className="mt-1 ml-5 list-disc space-y-1 text-sm">{others.map((b, i) => <li key={i}>{findingText(b)}</li>)}</ul>}</div>
          : !unavailable && <p className="text-sm text-slate-600">Nothing blocks Ready. The before-publishing notes below stay with the pack for whoever posts.</p>}
        {unavailable && <p className="text-sm text-slate-600">{unavailable}</p>}
        <label className="block text-xs">Note (optional)<input className={input} value={note} onChange={e => setNote(e.target.value)} /></label>
        <button type="button" className={primary} disabled={busy || !!unavailable || pack.ready_blockers.length > 0 || !!pack.removed_material || pack.state !== 'in_review'} onClick={() => decide('ready_to_publish')}>Ready to publish</button>
      </>}
    </section>

    {blocking.length > 0 && <section className={card} aria-label="To resolve">
      <h2 className="font-semibold text-[#173354]">To resolve ({blocking.length})</h2>
      <ul className="space-y-2">{blocking.map(f => <li key={f.finding_id} className="space-y-1 rounded-lg bg-red-50 p-3 text-sm text-red-900">
        <p><button type="button" className="font-medium underline" onClick={() => f.piece && onShowPiece(f.piece)}>{label(f.piece)}</button>: {findingText(f.message)}</p>
        {f.sentence && <blockquote className="border-l-2 border-red-300 pl-2 text-[13px]">“{f.sentence}”</blockquote>}
        {f.can_attest && canAct && <><p className="text-xs">Edit the sentence in the piece, or attest it is true.</p><Attest finding={f} busy={busy} onAttest={attest} /></>}
      </li>)}</ul>
    </section>}

    <section className={card} aria-label="Before publishing">
      <h2 className="font-semibold text-[#173354]">Before publishing</h2>
      <p className="text-xs text-slate-600">Notes for whoever posts each piece. They are listed here and in the week's document, and never block Ready.</p>
      {pack.before_publishing.length ? <ul className="space-y-2">{notes(pack.before_publishing)}</ul> : <p className="text-sm text-slate-500">No notes.</p>}
      {pack.client_quotes.length > 0 && <>
        <h3 className="pt-2 text-sm font-semibold">Client quotes to clear</h3>
        <ul className="space-y-2">{quotes(pack.client_quotes)}</ul>
      </>}
    </section>

    {(pack.stronger_with_permission.length > 0 || pack.granted.length > 0 || (pack.can_finish_again && canAct)) &&
      <Grants pack={pack} busy={busy} enabled={pack.can_finish_again && canAct} write={write} />}

    {personal.length > 0 && <section className={card} aria-label="Personal lines">
      <h2 className="font-semibold text-[#173354]">Personal lines to keep or cut</h2>
      <p className="text-xs text-slate-600">Lines in Whitney's own voice. Keep, edit or cut each one in its Reel.</p>
      {personal.map(p => <div key={p.key} className="text-sm"><button type="button" className="font-medium underline" onClick={() => onShowPiece(p.key)}>{p.label}</button>
        <ul className="ml-5 list-disc">{(p.content!.personal_lines as unknown[]).filter((l): l is string => typeof l === 'string').map((l, i) => <li key={i}>{l}</li>)}</ul></div>)}
    </section>}

    {warnings.length > 0 && <details className={card}><summary className="cursor-pointer font-semibold text-[#173354]">Checks to consider ({warnings.length})</summary>
      <ul className="mt-2 space-y-1 text-sm">{warnings.map(f => <li key={f.finding_id}>{label(f.piece)}: {findingText(f.message)}</li>)}</ul></details>}

    {resolved.length > 0 && <details className={card}><summary className="cursor-pointer font-semibold text-[#173354]">Resolved findings ({resolved.length})</summary>
      <ul className="mt-2 space-y-1 text-sm">{resolved.map(f => <li key={f.finding_id}>{label(f.piece)}: {findingText(f.message)} · {f.status === 'attested' ? 'attested' : 'cleared'}
        {f.resolution ? ` by ${who(f.resolution.by)}${f.resolution.delegated ? ' (delegated)' : ''}${f.resolution.note ? `: ${f.resolution.note}` : ''}` : ''}</li>)}</ul></details>}

    {(pack.pack_notes.length > 0 || pack.change_notes.length > 0) && <details className={card}><summary className="cursor-pointer font-semibold text-[#173354]">Notes from the system</summary>
      <ul className="mt-2 ml-5 list-disc space-y-1 text-sm">{[...pack.pack_notes, ...pack.change_notes].map((n, i) => <li key={i}>{n}</li>)}</ul></details>}

    {pack.can_finish_again && <section className={card} aria-label="Finish again">
      <h2 className="font-semibold text-[#173354]">Finish again</h2>
      <p className="text-xs text-slate-600">Finishes the pack again with no new instruction. Every line a person wrote is kept word for word.</p>
      {/* The button stays while the confirmation is open, so focus can go back to it when the confirmation closes. */}
      <button type="button" className={button} aria-expanded={confirmFinish} disabled={busy || pack.run_active || pack.state === 'superseded' || !manifest} onClick={() => setConfirmFinish(true)}>Finish again</button>
      {confirmFinish && <ConfirmFinish busy={busy} onCancel={() => setConfirmFinish(false)} onConfirm={() => {
        setConfirmFinish(false);
        void write(`/packs/${pack.pack_id}/finish`, 'POST', { expected_manifest_hash: manifest });
      }} />}
    </section>}

    {pack.versions.length > 0 && <details className={card}><summary className="cursor-pointer font-semibold text-[#173354]">Versions ({pack.versions.length})</summary>
      <ol className="mt-2 space-y-1 text-sm">{pack.versions.map((v, i) => <li key={v.pack_id}>
        {v.pack_id === pack.pack_id ? <span className="font-medium" aria-current="page">Version {i + 1} (this one)</span>
          : <Link className="underline" to={versionHref(v.pack_id)}>Version {i + 1}</Link>}
        {' · '}{shortDate(v.created_at)} · {VERSION_LABELS[v.kind] ?? words(v.kind)} · {v.by ? who(v.by) : 'the system'}{v.delegated ? ' (delegated)' : ''}
        {v.paths.length > 0 && <span className="text-slate-500"> ({v.pieces.map(label).join(', ') || v.paths.join(', ')})</span>}{v.note ? ` · ${v.note}` : ''}</li>)}</ol></details>}
  </aside>;
}
