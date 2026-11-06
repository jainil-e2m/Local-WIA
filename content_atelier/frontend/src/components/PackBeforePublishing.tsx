import React, { useState } from 'react';
import type { PackDoneV2, StoredPackV2 } from '../api/types';
import { clearanceRequest, toCheck } from './packFields';
import type { PackWrite } from './PackPiece';
import { button, input, primary, shortDate } from './packParts';
import { FoldPanel } from './AdminParts';
import { useSwapFocus } from './shared/a11y';
import { personName } from './studio/parts';
import { plainMessage } from '../utils/plainText';

/* Before publishing (Round 2: WIA asked that what to check stays available, apart from the publishable copy): one folded line
   under the pieces, "Before publishing · 3 to check", counting the notes not yet done and the client quotes not yet cleared.
   Open, it lists the before-publishing notes (with the answer given at Gate 2), the client quotes to clear, the system's
   notes as "Also check" and what would be stronger with the client's permission. An approver marks a note done or a quote
   cleared, with an optional reference; what is done shows who and when. None of it ever blocks Ready. */

// The packs whose list is open: a write makes a new version, drawn afresh, and the list stays open across it.
const opened = new Set<string>();

/** Who did something on the pack, as a person reads it: a name, or "the team" for an address. */
const who = (by: string | null | undefined) => personName(by) || 'the team';
const heading = 'text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A38B61]';
const muted = 'text-[12px] text-[#7A8496]';

/** A note marked done or a quote cleared, in muted text. It replaces the control, so after the write focus moves here (6.F6). */
function Done({ done, verb, focus }: { done: PackDoneV2; verb: string; focus: string }) {
  return <p className={muted} tabIndex={-1} data-focus-key={focus}>{verb} by {who(done.by)} on {shortDate(done.at)}{done.reference ? ` · ${done.reference}` : ''}{done.note ? ` · ${done.note}` : ''}</p>;
}

/** Marks a note done or a quote cleared, with an optional reference (where the okay was given, or what was checked). */
function MarkDone({ itemId, label, action, busy, onDone }: { itemId: string; label: string; action: string; busy: boolean;
  onDone: (itemId: string, reference: string) => Promise<true | undefined> }) {
  const [open, setOpen] = useState(false), [reference, setReference] = useState('');
  // The control swaps itself for its field: focus goes to the reference, and back to the control on Cancel (6.F6).
  const swap = useSwapFocus(open);
  if (!open) return <button ref={swap.controlRef} type="button" className={`${button} !px-3 !py-1 text-xs`} aria-label={`${action}: ${label}`} onClick={() => { swap.arm(); setOpen(true); }}>{action}</button>;
  return <div className="space-y-2">
    <label className="block text-xs">Reference (optional: where the okay was given, or what was checked)<input ref={swap.fieldRef} className={input} value={reference} onChange={e => setReference(e.target.value)} /></label>
    <div className="flex gap-2"><button type="button" className={`${primary} !px-3 !py-1 text-xs`} disabled={busy} onClick={async () => { if (await onDone(itemId, reference)) setOpen(false); }}>{action}</button>
      <button type="button" className={`${button} !px-3 !py-1 text-xs`} onClick={() => { swap.arm(); setOpen(false); }}>Cancel</button></div>
  </div>;
}

export function BeforePublishing({ pack, busy, write }: { pack: StoredPackV2; busy: boolean; write: PackWrite }) {
  const { before_publishing: notes, client_quotes: quotes, pack_notes: also, stronger_with_permission: stronger } = pack;
  if (!notes.length && !quotes.length && !also.length && !stronger.length) return null;
  const left = toCheck(pack);
  const canAct = pack.can_decide && !pack.run_active && pack.state !== 'superseded' && !!pack.manifest_hash;
  const clear = (itemId: string, reference: string) => {
    const request = clearanceRequest(pack.manifest_hash ?? '', itemId, reference);
    return 'body' in request ? write(`/packs/${pack.pack_id}/clearances`, 'POST', request.body) : Promise.resolve(undefined);
  };
  const pieceLabel = (key: string) => pack.pieces.find(p => p.key === key)?.label ?? '';
  const lineage = pack.source_brief_id;
  // A note can carry an unbroken name or address, which ran past its box on a phone (N4): it may break anywhere.
  return <FoldPanel label="Before publishing" defaultOpen={opened.has(lineage)} onToggle={open => { if (open) opened.add(lineage); else opened.delete(lineage); }}
    summary={<>Before publishing<span className="ml-2 font-normal text-[#7A8496]">· {left ? `${left} to check` : 'all done'}</span></>}>
    {notes.length > 0 && <ul className="space-y-3 [overflow-wrap:anywhere]">{notes.map(n => <li key={n.id} className="space-y-1">
      <p>{plainMessage(n.text)}</p>
      {n.answer && <p className={muted}>Answer: {n.answer}</p>}
      {n.done ? <Done done={n.done} verb="Done" focus={`pack:${pack.pack_id}:done:${n.id}`} />
        : canAct && <MarkDone itemId={n.id} label={n.text} action="Mark done" busy={busy} onDone={clear} />}
    </li>)}</ul>}
    {quotes.length > 0 && <div className="space-y-2">
      <h3 className={heading}>Client quotes to clear</h3>
      <ul className="space-y-3 [overflow-wrap:anywhere]">{quotes.map(q => <li key={q.quote_id} className="space-y-1">
        <blockquote>“{q.quote}”</blockquote>
        <p className={muted}>{[q.speaker, pieceLabel(q.piece)].filter(Boolean).join(' · ')}</p>
        {q.cleared ? <Done done={q.cleared} verb="Cleared" focus={`pack:${pack.pack_id}:done:${q.quote_id}`} />
          : canAct && <MarkDone itemId={q.quote_id} label={q.quote} action="Mark cleared" busy={busy} onDone={clear} />}
      </li>)}</ul>
    </div>}
    {also.length > 0 && <div className="space-y-2">
      <h3 className={heading}>Also check</h3>
      <ul className="ml-4 list-disc space-y-1 [overflow-wrap:anywhere]">{also.map((n, i) => <li key={i}>{plainMessage(n)}</li>)}</ul>
    </div>}
    {stronger.length > 0 && <div className="space-y-2">
      <h3 className={heading}>Would be stronger with the client's permission</h3>
      <ul className="ml-4 list-disc space-y-1 [overflow-wrap:anywhere]">{stronger.map((n, i) => <li key={i}>{plainMessage(n)}</li>)}</ul>
    </div>}
  </FoldPanel>;
}
