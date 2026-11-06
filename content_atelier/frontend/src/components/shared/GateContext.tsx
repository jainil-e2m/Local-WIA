import React, { useState } from 'react';
import type { GateContextItem } from '../../api/types';
import { Select } from '../ThemedSelect';

/* Context and attested facts at either gate (5.B7, R57; interface 2). The same panel serves a card at Gate 1 and a brief
   at Gate 2: the list of what reviewers added, each with its kind, who gave it and when, and the form to add one. An
   attested fact is a fact an approver states as true: it is evidence, may appear in copy and is shown as attested; a
   paraphrase is the client's words in the reviewer's and is never quoted. */

export type ContextKind = GateContextItem['kind'];
export type { GateContextItem };
type Perform = (path: string, method?: string, body?: unknown) => Promise<void>;

export const CONTEXT_KINDS: Record<ContextKind, { label: string; help: string }> = {
  context: { label: 'Context', help: 'A note for the writer about this piece. It guides the copy; it is not evidence.' },
  attested_fact: { label: 'Attested fact', help: 'A fact you state as true. It counts as evidence, may appear in the copy and is shown as attested by you. Approvers only.' },
  paraphrase: { label: "Paraphrase of the client's words", help: "What the client said, in your words. The copy may use it, but never in quotation marks." },
};

/** The route that adds context to a card (Gate 1) or a brief (Gate 2). */
export const contextPath = (target: 'angle' | 'brief', id: string) => target === 'angle' ? `/angles/${id}/context` : `/briefs/${id}/context`;

/** The add-context body, or what is missing. */
export function contextRequest(kind: ContextKind, text: string, author: string): { body: Record<string, unknown> } | { error: string } {
  if (!text.trim()) return { error: 'Write the context first.' };
  if (text.length > 4000) return { error: 'Keep it under 4,000 characters.' };
  return { body: { kind, text: text.trim(), ...(author.trim() ? { author: author.trim() } : {}) } };
}

/** One item in a reviewer's words: its kind, who gave it and on which day, and where it stands. */
export function contextLine(item: GateContextItem): string {
  const day = item.created_at.slice(0, 10);
  const who = item.kind === 'attested_fact' ? `attested by ${item.author} on ${day}` : `from ${item.author} on ${day}`;
  const where = item.in_brief === false ? '; the next refresh uses it' : '';
  return `${CONTEXT_KINDS[item.kind].label}, ${who}${where}`;
}

export function GateContextPanel({ target, id, items, canAdd, canAttest, busy, perform }: {
  target: 'angle' | 'brief'; id: string; items: GateContextItem[]; canAdd: boolean; canAttest: boolean; busy: boolean; perform: Perform;
}) {
  const [kind, setKind] = useState<ContextKind>('context');
  const [text, setText] = useState(''), [author, setAuthor] = useState(''), [error, setError] = useState('');
  const kinds = (Object.keys(CONTEXT_KINDS) as ContextKind[]).filter(k => k !== 'attested_fact' || canAttest);
  const add = () => {
    const request = contextRequest(kind, text, author);
    if ('error' in request) { setError(request.error); return; }
    setError(''); void perform(contextPath(target, id), 'POST', request.body);
  };
  return <section className="rounded-lg border p-3 space-y-2" aria-label="Context and attested facts">
    <h3 className="font-medium">Context and attested facts</h3>
    {!items.length && <p className="text-sm text-slate-600">No context has been added yet.</p>}
    <ul className="space-y-2 text-sm">{items.map(item => <li key={item.id} className={item.kind === 'attested_fact' ? 'rounded bg-emerald-50 p-2' : 'rounded bg-slate-50 p-2'}>
      <p className="text-xs uppercase tracking-wide text-slate-600">{contextLine(item)}</p>
      <p className="whitespace-pre-wrap">{item.text}</p></li>)}</ul>
    {canAdd && <div className="space-y-2">
      <label className="block text-sm">Kind<Select className="block w-full border rounded-lg p-2 mt-1" value={kind} onChange={e => setKind(e.target.value as ContextKind)}>
        {kinds.map(k => <option key={k} value={k}>{CONTEXT_KINDS[k].label}</option>)}</Select></label>
      <p className="text-xs text-slate-600">{CONTEXT_KINDS[kind].help}</p>
      <label className="block text-sm">Text<textarea className="block w-full border rounded-lg p-2 mt-1" rows={3} value={text} onChange={e => setText(e.target.value)} /></label>
      <label className="block text-sm">Whose words are these? (leave empty if yours)<input className="block w-full border rounded-lg p-2 mt-1" value={author} onChange={e => setAuthor(e.target.value)} /></label>
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
      <button className="rounded-lg border border-[#C4CBD7] px-3 py-2 text-sm disabled:opacity-40" disabled={busy || !text.trim()} onClick={add}>
        {target === 'brief' ? 'Add to this brief (saves a new version)' : 'Add to this card'}</button>
    </div>}
  </section>;
}
