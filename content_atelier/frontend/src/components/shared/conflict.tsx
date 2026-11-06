import React, { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage, isConflict } from '../../api/client';

/* One handler for a write that the backend refuses (plan 1.F2). A 409 means a conflict, such as a card or brief that
   changed since it was opened. The screen shows the backend's message and offers a reload, but it never reloads by
   itself: reloading replaces the data the form was built from, and the person's unsaved input stays in the form until
   they choose. Any other failure shows its message. */

export interface Conflict { message: string }

/** `describe` words a failure for this screen (the knowledge screens say a refusal in their reader's terms). */
export function useGuardedAction(reload?: () => unknown | Promise<unknown>, describe: (failure: unknown) => string = errorMessage) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState<Conflict | null>(null);

  /** Runs a write. Resolves to its answer, or undefined when it failed (the failure is on `error` or `conflict`). */
  const run = useCallback(async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true); setError(''); setConflict(null);
    try { return await action(); }
    catch (failure) {
      if (isConflict(failure)) setConflict({ message: describe(failure) });
      else setError(describe(failure));
      return undefined;
    } finally { setBusy(false); }
  }, [describe]);

  const reloadLatest = useCallback(async () => {
    try { await reload?.(); setConflict(null); setError(''); }
    catch (failure) { setError(describe(failure)); }
  }, [reload, describe]);

  return { busy, error, conflict, run, reloadLatest, clear: () => { setError(''); setConflict(null); }, setError };
}

export function ConflictNotice({ conflict, onReload, onDismiss }: { conflict: Conflict | null; onReload?: () => void; onDismiss?: () => void }) {
  const box = useRef<HTMLDivElement>(null);
  // The form may be far below the top of the page: bring the notice into view when it appears.
  useEffect(() => { if (conflict) box.current?.scrollIntoView?.({ block: 'nearest' }); }, [conflict]);
  if (!conflict) return null;
  return <div ref={box} role="alert" data-conflict className="rounded-xl bg-amber-50 border border-amber-200 p-4 text-sm text-amber-900 space-y-2">
    <p className="font-medium">This changed while you were working on it.</p>
    <p>{conflict.message}</p>
    <p>What you typed is still in the form. Copy it if you want to keep it, then reload to see the latest version.</p>
    <div className="flex gap-3">
      {onReload && <button type="button" className="rounded-lg border border-amber-400 px-3 py-1.5" onClick={onReload}>Reload the latest version</button>}
      {onDismiss && <button type="button" className="underline" onClick={onDismiss}>Keep editing</button>}
    </div>
  </div>;
}

/** The error line a guarded action shows when it is not a conflict. Like the conflict notice, it is brought into view when
    it appears: the form that failed (a card's decision, a brief's approval) may be far below it, and a refusal nobody sees
    reads as a click that did nothing. */
export function ActionError({ message }: { message: string }) {
  const box = useRef<HTMLParagraphElement>(null);
  useEffect(() => { if (message) box.current?.scrollIntoView?.({ block: 'nearest' }); }, [message]);
  return message ? <p ref={box} role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{message}</p> : null;
}
