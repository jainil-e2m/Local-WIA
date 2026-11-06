import React, { useEffect, useRef, useState } from 'react';
import type { BlockerItem, BriefVersion, RemovedMaterial } from '../api/types';
import { FIELD_MAP, briefFields, fieldChanges, fieldLabel, isLocked, optionWords, pattern, type BriefField } from './briefFields';
import { useSwapFocus } from './shared/a11y';
import { Select } from './ThemedSelect';
import { EDIT_FIELD, EDIT_LABEL, EditBar, PANEL_HEADING, QUIET, rowsFor } from './studio/parts';
import { TAKES, TimeNote } from './studio/GenerationTime';

/* Gate 2's editing (5.F1, 5.F4, 5.F5, 5.B6, 5.F2): edit any field by its path, refresh with feedback while the lines a
   person wrote stay locked, see every version with who made it and why, and read what stops approval in plain words. */

type Perform = (path: string, method?: string, body?: unknown) => Promise<void>;
const button = 'rounded-full border border-[#E6E9F0] bg-white px-3.5 py-1.5 text-[12px] font-medium text-[#34445F] hover:bg-[#F7F8FB] disabled:opacity-40 disabled:cursor-not-allowed';
const input = 'block w-full border rounded-lg p-2 mt-1';

export type { BlockerItem };
const BLOCKER_NAMES: Record<string, string> = {
  removed_material: 'Removed on request', open_question: 'Open question', cta_unconfirmed: 'Call to action not confirmed', blocking_finding: 'A problem in the copy',
  stale: 'Out of date', claims_check: 'Claims not checked', role: 'Your role',
};
export const blockerName = (kind: string) => BLOCKER_NAMES[kind] ?? 'To resolve';

/** What an item built on material removed at a client's request (6.B12) must not be used for, in the backend's words. */
export const REMOVED_ACTION = 'Do not approve or publish it; develop a new card from other calls.';

/** Why an item cannot be developed, approved or marked ready because it is built on material removed at a client's request
    (6.B12): the removal's own note, with its day. */
export function RemovedMaterialNote({ removed }: { removed: RemovedMaterial | null | undefined }) {
  if (!removed?.note) return null;
  return <p role="note" className="rounded bg-amber-50 p-2 text-sm"><strong>{blockerName('removed_material')}:</strong> {removed.note}</p>;
}

/** What stops approval, each by name, with what to do (5.F2, R50). A brief built on removed material (6.B12) shows the
    removal's note, with its day, on that blocker; if the list does not carry the blocker, it is added first. */
export function BlockerList({ items, removed }: { items: BlockerItem[]; removed?: RemovedMaterial | null }) {
  const shown: BlockerItem[] = removed?.note && !items.some(b => b.kind === 'removed_material')
    ? [{ kind: 'removed_material', title: removed.note, action: REMOVED_ACTION }, ...items] : items;
  if (!shown.length) return <p className="text-sm">Nothing stops approval.</p>;
  return <ul className="mt-2 space-y-2 text-sm">{shown.map((b, i) => {
    const detail = b.detail ?? (b.kind === 'removed_material' && removed?.note !== b.title ? removed?.note : null);
    return <li key={i} className="rounded bg-amber-50 p-2">
      <p><strong>{blockerName(b.kind)}:</strong> {b.title}</p>{detail && <p className="text-slate-700">{detail}</p>}
      <p className="text-slate-600">{b.action}</p></li>;
  })}</ul>;
}

/** The refresh-with-feedback body (5.B6): live from the screen, with the locked lines the reviewer releases. */
export function refreshRequest(expected: string, instructions: string, unlock: string[]): { body: Record<string, unknown> } | { error: string } {
  if (!instructions.trim()) return { error: 'Say what the refreshed version should change.' };
  return { body: { expected_hash: expected, instructions: instructions.trim(), mode: 'live', evidence_ids: [], unlock } };
}

/** One field: its value, a lock mark, and its editor while it is being changed. */
function FieldRow({ field, locked, draft, setDraft, canEdit }: { field: BriefField; locked: boolean; draft: string | undefined; setDraft: (v: string | undefined) => void; canEdit: boolean }) {
  const shown = draft ?? (field.value === null ? '' : String(field.value));
  // Edit swaps the line for its field: focus goes into the field, and back to Edit on Cancel (6.F6).
  const swap = useSwapFocus(draft !== undefined);
  return <div className="py-1">
    <div className="flex flex-wrap items-baseline gap-2 text-sm"><span className="font-medium">{field.label}</span>
      {locked && <span className="rounded bg-slate-200 px-1 text-xs" title="A person wrote this line: a refresh keeps it word for word">Locked: kept on refresh</span>}
      {canEdit && draft === undefined && <button ref={swap.controlRef} className="text-xs underline" onClick={() => { swap.arm(); setDraft(shown); }}>Edit</button>}
      {draft !== undefined && <button className="text-xs underline" onClick={() => { swap.arm(); setDraft(undefined); }}>Cancel</button>}</div>
    {draft === undefined ? <p className="text-sm whitespace-pre-wrap">{shown || <span className="text-slate-500">Empty</span>}</p>
      : field.kind === 'choice' ? <Select ref={swap.fieldRef} aria-label={field.label} className={input} value={shown} onChange={e => setDraft(e.target.value)}>{field.options!.map(o => <option key={o} value={o}>{optionWords(o)}</option>)}</Select>
      : field.multiline ? <textarea ref={swap.fieldRef} aria-label={field.label} className={input} rows={Math.min(12, Math.max(3, shown.split('\n').length + 1))} value={shown} onChange={e => setDraft(e.target.value)} />
      : <input ref={swap.fieldRef} aria-label={field.label} className={input} type={field.kind === 'number' ? 'number' : 'text'} value={shown} onChange={e => setDraft(e.target.value)} />}
  </div>;
}

/** Every field of the brief, by section, editable one by one; the drafted ones are saved together as one new version. */
export function BriefFieldEditor({ body, schemaVersion, locks, expected, briefId, canEdit, busy, perform }: {
  body: Record<string, unknown>; schemaVersion: string; locks: string[]; expected: string; briefId: string; canEdit: boolean; busy: boolean; perform: Perform;
}) {
  const groups = briefFields(body, schemaVersion);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const all = groups.flatMap(g => g.fields);
  const pending = Object.keys(drafts).length;
  const save = () => {
    const request = fieldChanges(expected, all, drafts);
    if ('error' in request) { setError(request.error); return; }
    setError(''); void perform(`/briefs/${briefId}`, 'PATCH', request.body);
  };
  return <details className="rounded-lg border p-3" open={pending > 0}><summary className="font-medium cursor-pointer">Edit any field ({all.length} fields; {locks.length} locked)</summary>
    <p className="mt-2 text-sm text-slate-600">Each line you change is kept word for word from then on: a refresh rewrites the rest around it.</p>
    {groups.map(g => <fieldset key={g.section} className="mt-3 border-t pt-2"><legend className="font-medium">{g.label}</legend>
      {g.fields.map(f => <FieldRow key={f.path} field={f} locked={isLocked(f.path, locks)} draft={drafts[f.path]} canEdit={canEdit}
        setDraft={v => setDrafts(d => { const next = { ...d }; if (v === undefined) delete next[f.path]; else next[f.path] = v; return next; })} />)}</fieldset>)}
    {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
    {canEdit && <button className={`${button} mt-3`} disabled={busy || !pending} onClick={save}>Save {pending || ''} {pending === 1 ? 'change' : 'changes'} as a new version</button>}
  </details>;
}

// The lines that steer the writer or describe how a piece is made rather than what it says: folded beneath a section's copy.
const DIRECTION = /(\.job|\.premise|\.takeaway|\.distinct_because|\.timestamps\[\d+\]|\.credits\[\d+\]\.\w+|\.details\[\d+\]|\.kind|\.style|\.production|\.register|\.source|\.read_time_seconds|\.offer_descriptor|\.send_header\.\w+)$/;
const PIECE = /^format_plan\.(reels\[(\d+)\]|email|carousel|caption|stories)/;
const MAP_ORDER = Object.keys(FIELD_MAP);
const PIECE_NAMES: Record<string, string> = { email: 'Email', carousel: 'Carousel', caption: 'Caption', stories: 'Stories' };

/** The sections of the editor: the brief's own, then one for each piece of the pack. A line's label drops the piece's name. */
export function editorSections(groups: { section: string; label: string; fields: BriefField[] }[]) {
  const sections: { key: string; label: string; piece: boolean; fields: BriefField[] }[] = [];
  for (const group of groups) {
    for (const field of group.fields) {
      const piece = PIECE.exec(field.path);
      const key = piece ? piece[1] : field.section;
      const label = piece ? (piece[2] ? `Reel ${Number(piece[2]) + 1}` : PIECE_NAMES[piece[1]]) : group.label;
      let section = sections.find(s => s.key === key);
      if (!section) { section = { key, label, piece: !!piece, fields: [] }; sections.push(section); }
      const short = piece ? field.label.replace(new RegExp(`^${label}:?\\s*`, 'i'), '') : field.label.replace(/^Before publishing P(\d+)/, 'Item $1');
      section.fields.push({ ...field, label: short ? short.charAt(0).toUpperCase() + short.slice(1) : field.label });
    }
  }
  // The database keeps a record's keys in its own order: a section reads in the field map's order, its lists in their own.
  const place = (f: BriefField) => { const at = MAP_ORDER.indexOf(pattern(f.path).key); return at < 0 ? MAP_ORDER.length : at; };
  for (const section of sections) section.fields = section.fields.map((f, i) => [f, i] as const).sort(([a, i], [b, j]) => place(a) - place(b) || i - j).map(([f]) => f);
  return sections;
}

/** The brief's text, ready to change (gates.one_click): it stands in for the brief while open. Every line is already a field, a
    line you change is kept word for word from then on, and all the changes save together as one new version. */
export function BriefTextEditor({ body, schemaVersion, locks, expected, briefId, busy, perform, onClose }: {
  body: Record<string, unknown>; schemaVersion: string; locks: string[]; expected: string; briefId: string; busy: boolean; perform: Perform; onClose: () => void;
}) {
  const groups = briefFields(body, schemaVersion);
  const all = groups.flatMap(g => g.fields);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  const original = (f: BriefField) => f.value === null ? '' : String(f.value);
  const change = (f: BriefField, value: string) => setDrafts(d => {
    const next = { ...d };
    if (value === original(f)) delete next[f.path]; else next[f.path] = value;
    return next;
  });
  const save = () => {
    const request = fieldChanges(expected, all, drafts);
    if ('error' in request) { setError(request.error); return; }
    setError(''); void perform(`/briefs/${briefId}`, 'PATCH', request.body);
  };
  const line = (f: BriefField) => {
    const shown = drafts[f.path] ?? original(f);
    const name = <>{f.label}{isLocked(f.path, locks) && <span className="ml-2 font-normal text-[11px] text-[#7A8496]">A person wrote this: kept on refresh</span>}</>;
    if (f.kind === 'choice') return <label key={f.path} className={EDIT_LABEL}>{name}<Select className={EDIT_FIELD} value={shown} onChange={e => change(f, e.target.value)}>{f.options!.map(o => <option key={o} value={o}>{optionWords(o)}</option>)}</Select></label>;
    if (f.multiline) return <label key={f.path} className={EDIT_LABEL}>{name}<textarea className={EDIT_FIELD} rows={rowsFor(shown)} value={shown} onChange={e => change(f, e.target.value)} /></label>;
    return <label key={f.path} className={EDIT_LABEL}>{name}<input className={EDIT_FIELD} type={f.kind === 'number' ? 'number' : 'text'} value={shown} onChange={e => change(f, e.target.value)} /></label>;
  };
  return <section aria-label="Edit this brief" className="space-y-4">
    <div><h3 ref={heading} tabIndex={-1} className="font-editorial text-[19px] text-[#1B2433] outline-none">Edit the text</h3>
      <p className="mt-1 text-[12px] text-[#667184]">Change any line. What you change is kept word for word, also when you ask for a refreshed version. Saving makes a new version straight away.</p></div>
    {editorSections(groups).map(section => {
      const copy = section.fields.filter(f => !DIRECTION.test(f.path)), direction = section.fields.filter(f => DIRECTION.test(f.path));
      return <details key={section.key} open={!section.piece} className="group rounded-xl border border-[#E6E9F0] bg-[#F7F8FB]">
        <summary className="cursor-pointer list-none flex items-center justify-between gap-3 px-4 py-3 [&::-webkit-details-marker]:hidden">
          <span className={PANEL_HEADING}>{section.label}</span>
          <span aria-hidden="true" className="text-[#9AA3B2] text-[11px]"><span className="group-open:hidden">Show</span><span className="hidden group-open:inline">Hide</span></span></summary>
        <div className="px-4 pb-4 space-y-4">{copy.map(line)}
          {direction.length > 0 && <details className="pt-1"><summary className="cursor-pointer text-[12px] font-medium text-[#34445F]">More fields: direction and details</summary>
            <div className="mt-3 space-y-4">{direction.map(line)}</div></details>}</div>
      </details>;
    })}
    <EditBar count={Object.keys(drafts).length} error={error} busy={busy} onCancel={onClose} onSave={save} saveLabel="Save my edits" />
  </section>;
}

/** Refresh with feedback (5.B6): the reviewer's instructions go to the writer live; locked lines stay unless released. */
export function RefreshPanel({ briefId, expected, locks, canEdit, busy, perform, running }: {
  briefId: string; expected: string; locks: string[]; canEdit: boolean; busy: boolean; perform: Perform; running?: boolean;
}) {
  const [instructions, setInstructions] = useState(''), [unlock, setUnlock] = useState<string[]>([]), [error, setError] = useState('');
  if (!canEdit) return null;
  const send = () => {
    const request = refreshRequest(expected, instructions, unlock);
    if ('error' in request) { setError(request.error); return; }
    setError(''); void perform(`/briefs/${briefId}/revise`, 'POST', request.body);
  };
  return <section aria-label="Refresh with feedback" className="space-y-3">
    {running ? <div role="status" className="rounded-lg border border-[#D1DBFF] bg-[#F7F9FF] p-3 text-[12.5px] text-[#34445F] space-y-1.5">
      <p>A new version is being written from your feedback. It opens here when it is ready.</p>
      <TimeNote>This takes {TAKES.brief}. You can close this and come back.</TimeNote></div>
    : <label className={EDIT_LABEL}>What should change?<textarea className={EDIT_FIELD} rows={3} value={instructions} onChange={e => setInstructions(e.target.value)} /></label>}
    {!running && !!locks.length && <fieldset className="text-[12px] text-[#34445F] space-y-1"><legend className="mb-1 text-[#667184]">Lines a person wrote stay word for word. Tick one to let the writer rewrite it:</legend>{locks.map(path => <label key={path} className="flex gap-2">
      <input type="checkbox" checked={unlock.includes(path)} onChange={e => setUnlock(e.target.checked ? [...unlock, path] : unlock.filter(p => p !== path))} />
      Let the writer rewrite: {fieldLabel(path)}</label>)}</fieldset>}
    {error && <p role="alert" className="text-[12px] text-red-800">{error}</p>}
    {!running && <div className="flex flex-wrap items-center justify-between gap-3">
      <TimeNote>A new version of the brief takes {TAKES.brief}.</TimeNote>
      <button type="button" className={QUIET} disabled={busy || !instructions.trim()} onClick={send}>Refresh with feedback</button></div>}
  </section>;
}

/** Every version of the brief, oldest first, with who made it and why (5.F5 d). */
export function VersionList({ versions, current, onOpen }: { versions: BriefVersion[]; current: string; onOpen: (id: string) => void }) {
  if (!versions.length) return null;
  return <details className="rounded-lg border p-3"><summary className="cursor-pointer font-medium">Versions ({versions.length})</summary>
    <ol className="mt-2 space-y-1 text-sm">{versions.map((v, i) => <li key={v.brief_id}>
      <button className="text-left underline disabled:no-underline" disabled={v.brief_id === current} onClick={() => onOpen(v.brief_id)}>
        Version {i + 1}{v.brief_id === current ? ' (this one)' : ''}</button>
      {' · '}{new Date(v.created_at).toLocaleString()} · {v.author || v.updated_by || 'the system'} · {v.reason || 'No reason recorded'}
      {!!v.fields?.length && <span className="text-slate-600"> ({v.fields.map(fieldLabel).join(', ')})</span>} · {v.approval_status}</li>)}</ol>
  </details>;
}
