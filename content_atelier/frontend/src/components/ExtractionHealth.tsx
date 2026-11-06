import React from 'react';
import { Link } from 'react-router-dom';
import { useExtractionHealth, type ExtractionHealth, type FailedDocument } from '../api/moments';
import { paths } from '../app/routes';
import { sourceLabel } from '../utils/documents';
import { failureParts } from './shared/JobProgress';
import { DocumentsView } from './DocumentsView';
import { ViewBoundary } from './shared/ViewBoundary';
import { EmptyState, ErrorState, LoadingState } from './shared/states';
import { FoldPanel, plainReason, shortDay } from './AdminParts';

/* "Processing health" at the bottom of Sources → All documents, folded: are the included documents being read, how many are
   waiting, which one has waited longest, and which failed and why. The list of documents is the page; this is the check an
   administrator opens when something looks stuck. */

const FAILED_SHOWN = 5;
const count = (n: number) => n.toLocaleString('en-US');

/** "3 days", "5 hours" or "less than an hour": how long a document has been waiting. */
export function waited(hours: number): string {
  if (hours < 1) return 'less than an hour';
  if (hours < 48) { const h = Math.floor(hours); return `${h} ${h === 1 ? 'hour' : 'hours'}`; }
  return `${Math.floor(hours / 24)} days`;
}

function Failed({ doc }: { doc: FailedDocument }) {
  return <li className="py-2.5 border-b last:border-b-0 border-[#EEF0F4] space-y-0.5">
    <p><Link className="font-medium text-[#1B2433] hover:underline" to={paths.document(doc.document_id)}>{doc.title}</Link>
      <span className="text-[#8B93A3]"> · {sourceLabel(doc.source_type)} · {doc.failed_at ? `failed ${shortDay(doc.failed_at)}` : 'date not recorded'}</span></p>
    <p className="text-[12px] text-[#947021]">{plainReason(failureParts(doc.error_summary).reason) || 'No reason was recorded.'}</p>
  </li>;
}

function Figure({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl bg-[#F7F8FB] px-4 py-3"><p className="text-[11px] text-[#8B93A3]">{label}</p><p className="font-editorial text-2xl text-[#1B2433] tabular-nums">{count(value)}</p></div>;
}

export function ExtractionHealthBody({ health }: { health: ExtractionHealth }) {
  const { totals, failed, oldest_pending: oldest } = health;
  if (!totals.included_documents) return <EmptyState>No documents are included yet, so there is nothing to read.</EmptyState>;
  const by = totals.by_status;
  const waiting = (by.pending ?? 0) + (by.queued ?? 0) + (by.running ?? 0);
  return <div className="space-y-4">
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Figure label="Documents included" value={totals.included_documents} />
      <Figure label="Read" value={totals.completed_documents} />
      <Figure label="Waiting" value={waiting} />
      <Figure label="Failed" value={health.failed_total} />
    </div>
    <p data-oldest-waiting>
      {oldest
        ? <>Waiting longest: <Link className="text-[#5070FF] hover:underline" to={paths.document(oldest.document_id)}>{oldest.title}</Link> ({sourceLabel(oldest.source_type)}), for {waited(oldest.waiting_hours)}.</>
        : 'No document is waiting.'}
    </p>
    <section aria-label="Failed documents" className="space-y-1">
      <h3 className="font-semibold">{health.failed_total ? `${count(health.failed_total)} ${health.failed_total === 1 ? 'document' : 'documents'} failed` : 'No document has failed'}</h3>
      {failed.length > 0 && <>
        <ul>{failed.slice(0, FAILED_SHOWN).map(doc => <Failed key={doc.document_id} doc={doc} />)}</ul>
        {failed.length > FAILED_SHOWN && <details><summary className="cursor-pointer text-[12px] font-medium text-[#5070FF]">Show {failed.length - FAILED_SHOWN} more</summary>
          <ul>{failed.slice(FAILED_SHOWN).map(doc => <Failed key={doc.document_id} doc={doc} />)}</ul></details>}
        {health.failed_total > failed.length && <p className="text-[12px] text-[#8B93A3]">The {count(failed.length)} most recent are listed.</p>}
      </>}
    </section>
  </div>;
}

export function ExtractionHealthPanel() {
  const health = useExtractionHealth();
  const failed = health.data?.failed_total ?? 0;
  return <FoldPanel label="Processing health" summary={<>Processing health{failed ? <span className="ml-2 font-normal text-[#947021]">· {count(failed)} failed</span> : null}</>}>
    {health.data === undefined && !health.error && <LoadingState>Checking processing…</LoadingState>}
    {health.error && <ErrorState message={health.data ? `The latest check failed: ${health.error.message}` : health.error.message} onRetry={() => void health.refetch()} />}
    {health.data && <ExtractionHealthBody health={health.data} />}
  </FoldPanel>;
}

/** `/sources/documents`: the documents, with the processing health folded at the bottom. */
export function DocumentsOverview() {
  // The panel has its own boundary, so a health answer that cannot be shown leaves the list of documents working.
  return <div className="space-y-6"><DocumentsView /><ViewBoundary name="Processing health"><ExtractionHealthPanel /></ViewBoundary></div>;
}
