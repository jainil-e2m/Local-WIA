import kb from '@kb-live';
import { signInAgain } from './auth';

/*
 * Edits people make in the app that everyone must see: Action Hub changes and client details (name, owner,
 * logo, cover, archive). The KB builds the records; these are layered on top (backend/services/edits.py).
 *
 * - Live app (the KB snapshot is loaded): saved on the KB server when a person presses a button that commits
 *   the change, loaded by everyone at start. Nothing is kept in one browser.
 * - Sample preview (no KB): kept in memory for the visit only, so the demo still works.
 *
 * Each save names the revision it was based on; if a colleague saved in between, the server refuses it and
 * this keeps their version (EditConflict), so nobody silently overwrites anyone.
 */

export type EditKind = 'action' | 'client';
export interface EditRow { data: Record<string, unknown>; revision: number | null; by?: string; at?: string }

const rows: Record<EditKind, Map<string, EditRow>> = { action: new Map(), client: new Map() };
// The server only exists behind the live app (and the local dev server proxying the KB API); a static export of
// real data has no API, so it keeps edits for the visit like the sample.
const shared = () => !!kb.meta && (import.meta.env.MODE === 'portfolio' || import.meta.env.MODE === 'wia');

export class EditConflict extends Error {}

export const editOf = (kind: EditKind, key: string): EditRow | undefined => rows[kind].get(key);
/** True while a save for this item is still on its way (callers settle the screen only once the last one lands). */
export const isSaving = (kind: EditKind, key: string) => inFlight.has(`${kind}:${key}`);
export const allEdits = (kind: EditKind): [string, EditRow][] => [...rows[kind]];

/** Once at start (main.tsx), before any view reads the records. */
export async function loadEdits(): Promise<void> {
  if (!shared()) return;
  const res = await fetch('/api/v1/edits', { credentials: 'same-origin' });
  if (!res.ok) throw new Error(`The KB answered ${res.status}.`);
  const data = await res.json() as { actions: Record<string, EditRow>; clients: Record<string, EditRow> };
  for (const [key, row] of Object.entries(data.actions ?? {})) rows.action.set(key, row);
  for (const [key, row] of Object.entries(data.clients ?? {})) rows.client.set(key, row);
}

// One save at a time per item: two quick clicks (Done, then Acknowledge) must not race each other's revision.
const inFlight = new Map<string, Promise<unknown>>();

/** Save the changed fields (undefined or null: back to the KB's value). Resolves with the saved copy. */
export function saveEdit(kind: EditKind, key: string, changes: Record<string, unknown>, viewer: string): Promise<EditRow> {
  const id = `${kind}:${key}`;
  // A save queued behind one a colleague's newer version refused was made on the same old copy: refuse it too,
  // rather than send it on their revision and overwrite them. Any other failure doesn't change the copy.
  const next = (inFlight.get(id) ?? Promise.resolve()).then(
    () => send(kind, key, changes, viewer),
    error => { if (error instanceof EditConflict) throw new EditConflict(error.message); return send(kind, key, changes, viewer); });
  inFlight.set(id, next);
  void next.finally(() => { if (inFlight.get(id) === next) inFlight.delete(id); }).catch(() => undefined);
  return next;
}

async function send(kind: EditKind, key: string, changes: Record<string, unknown>, viewer: string): Promise<EditRow> {
  // JSON drops undefined; the server needs null to clear a field.
  const sent = Object.fromEntries(Object.entries(changes).map(([k, v]) => [k, v === undefined ? null : v]));
  const before = rows[kind].get(key);
  if (!shared()) {
    const data = Object.fromEntries(Object.entries({ ...(before?.data ?? {}), ...sent }).filter(([, v]) => v !== null));
    const row = { data, revision: (before?.revision ?? 0) + 1, by: viewer, at: new Date().toISOString() };
    rows[kind].set(key, row);
    return row;
  }
  const res = await fetch(`/api/v1/edits/${kind}/${encodeURIComponent(key)}`, {
    method: 'PUT', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ changes: sent, expected_revision: before?.revision ?? null, viewer }),
  }).catch(() => null);
  const body = res ? await res.json().catch(() => ({})) : {};
  if (res?.status === 409) {
    const current = body?.detail?.current as EditRow | undefined;
    if (current?.revision) rows[kind].set(key, current); else rows[kind].delete(key);
    throw new EditConflict(body?.detail?.message || 'A colleague changed this since you opened it; it now shows their version.');
  }
  if (res?.status === 401) { signInAgain(); throw new Error('Your session ended: signing you in again.'); }
  if (!res?.ok) throw new Error(`Not saved: ${body?.detail?.message || (res ? `the KB answered ${res.status}` : 'the KB can’t be reached')}.`);
  rows[kind].set(key, body as EditRow);
  return body as EditRow;
}
