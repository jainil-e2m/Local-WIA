import React from 'react';
import type { AccountEntry, AccountMemory } from '../api/schema';

/* Account memory (3.B17, D25): beside a client story card at Gate 1 and its brief at Gate 2, the account the card is about,
   from WIA's records only. Its current state and what happened after the card's call keep a public story honest (a
   recommendation already built, an account that needed a look); internal meetings' remarks are for the reviewer only. */

const NAMING: Record<AccountMemory['naming'], string> = {
  may_name: 'May be named in public copy.',
  anonymise: 'Anonymise in public copy: never name the account or its people.',
  never_name: 'Never name this account or its people, whatever anyone asks.',
  no_use: 'Its material is not used in public copy at all.',
};
const KIND: Record<AccountEntry['kind'], string> = {
  recommended: 'Recommended', built: 'Built', decided: 'Decided', measured: 'Measured', said: 'Said', open: 'Left open',
  published: 'Published', sent: 'Sent by WIA', internal: 'Internal meeting',
};

/** "12 Oct 2026", or "week of 8 Jun 2026" when only the call's week is known (1.B11). */
export function entryDate(date: string | null, precision: string): string {
  if (!date) return 'Undated';
  const d = new Date(`${date}T12:00:00Z`);
  const text = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  return precision === 'week' ? `week of ${text}` : text;
}

function Entries({ items }: { items: AccountEntry[] }) {
  return <ul className="space-y-1">{items.map((e, i) => <li key={i} className="text-sm">
    <span className="text-xs uppercase tracking-wide text-slate-500">{KIND[e.kind]} · {entryDate(e.date, e.precision)}</span>
    <br />{e.text}{typeof e.source?.title === 'string' ? <span className="text-slate-500"> ({e.source.title})</span> : null}</li>)}</ul>;
}

export function AccountMemoryPanel({ accounts }: { accounts?: AccountMemory[] | null }) {
  if (!accounts?.length) return null;
  return <section aria-label="Account memory" className="rounded-lg border border-[#C4CBD7] bg-[#F6F8FB] p-3 space-y-3">
    {accounts.map(acc => <div key={acc.client_id} className="space-y-2">
      <p className="font-medium">{acc.name}{acc.business ? <span className="font-normal text-slate-600"> · {acc.business}</span> : null}
        <span className="font-normal text-slate-600"> · {acc.status}</span></p>
      <p className="text-sm">{NAMING[acc.naming]}</p>
      <p className="text-sm text-slate-700">{acc.calls} {acc.calls === 1 ? 'call' : 'calls'} on record
        {acc.last_call ? `; the last ${entryDate(acc.last_call.date, acc.last_call.precision)} (${acc.last_call.title})` : ''}.</p>
      {acc.what_happened_next.length > 0 ? <details open><summary className="cursor-pointer text-sm font-medium">
        What happened after this card's call ({acc.what_happened_next.length})</summary><Entries items={acc.what_happened_next} /></details>
        : <p className="text-sm text-slate-600">Nothing on record after this card's call.</p>}
      {acc.latest.length > 0 && <details><summary className="cursor-pointer text-sm">The account's latest records</summary><Entries items={acc.latest} /></details>}
      {(acc.internal_since.length > 0 || acc.cautions.length > 0) && <div className="rounded-md bg-amber-50 p-2">
        <p className="text-sm font-medium">From internal meetings (for you, never for copy)</p>
        <Entries items={acc.internal_since.length ? acc.internal_since : acc.cautions} /></div>}
    </div>)}
  </section>;
}
