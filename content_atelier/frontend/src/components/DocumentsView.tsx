import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { DOCUMENT_PAGE_SIZES, useDocument, useDocuments, type DocumentDetail, type DocumentSummary } from '../api/documents';
import { paths } from '../app/routes';
import {
  CALL_LABELS, CALL_TYPES, EXTRACTION_LABELS, EXTRACTION_STATUSES, NO_FILTERS, SOURCE_LABELS, SOURCE_TYPES, callLabel, clock, documentQuery, filterCount,
  pageRange, readFilters, roleLabel, sourceLabel, writeFilters, type DocumentFilters,
} from '../utils/documents';
import { EmptyState, ErrorState, LoadingState } from './shared/states';
import { ClassifyControl, UploadTranscriptButton } from './DocumentActions';
import { useMe } from '../utils/me';
import { PageHeading } from './PageHeading';
import {
  FilterSelect, META, MoreFilters, PANEL, Pager, Pill, QUIET_BUTTON, SELECT, SearchBox, TEXT_BUTTON, plainReason, shortDay,
} from './AdminParts';
import { Select } from './ThemedSelect';
import { DateInput } from './DateInput';

/* Sources → All documents: every stored document, independent of weeks. A row says what a person needs to find a call: its
   title, date, source and call type, client, whether it is included, and, when the rules could not place it, a choice of call
   type right there. The search and three filters are in view, the rest under "More filters"; all of them, and the page, are
   in the URL. Each document has a page of its own, with the reason it is excluded (in plain words) and its passages. */

const options = (values: readonly string[], labels: Record<string, string>) => values.map(value => ({ value, label: labels[value] ?? value }));

/** "4 Mar 2026", or "Undated". */
export const documentDay = (doc: Pick<DocumentSummary, 'date_state' | 'occurred_at'>) =>
  doc.date_state === 'undated' || !doc.occurred_at ? 'Undated' : shortDay(doc.occurred_at) || 'Undated';

/** Why a document is left out, in plain words (no plan codes or delegation notes). */
export const exclusionText = (doc: Pick<DocumentSummary, 'included' | 'exclusion_reason'>) =>
  doc.included ? '' : plainReason(doc.exclusion_reason) || 'No reason was recorded.';

export function DocumentFilterBar({ filters, onChange }: { filters: DocumentFilters; onChange: (patch: Partial<DocumentFilters>) => void }) {
  const [text, setText] = useState(filters.q);
  const [client, setClient] = useState(filters.client_id);
  // A search is sent once the person stops typing for a moment, or presses Enter.
  useEffect(() => {
    if (text.trim() === filters.q) return;
    const timer = setTimeout(() => onChange({ q: text.trim() }), 450);
    return () => clearTimeout(timer);
  }, [text]);
  const active = filterCount(filters);
  const more = (['extraction_status', 'date_state', 'client_id', 'needs_review', 'from', 'to'] as const).filter(key => filters[key]).length;
  return <form aria-label="Filter documents" className="space-y-3" onSubmit={e => { e.preventDefault(); onChange({ q: text.trim(), client_id: client.trim() }); }}>
    <div className="flex flex-wrap items-center gap-2.5">
      <SearchBox label="Search titles and text" value={text} onChange={setText} placeholder="Search titles and what was said…" />
      <FilterSelect label="Source" any="All sources" value={filters.source_type} options={options(SOURCE_TYPES, SOURCE_LABELS)} onChange={v => onChange({ source_type: v as DocumentFilters['source_type'] })} />
      <FilterSelect label="Call type" any="All call types" value={filters.call_type} options={options(CALL_TYPES, CALL_LABELS)} onChange={v => onChange({ call_type: v as DocumentFilters['call_type'] })} />
      <FilterSelect label="Included" any="Included or not" value={filters.included} options={[{ value: 'true', label: 'Included' }, { value: 'false', label: 'Excluded' }]}
        onChange={v => onChange({ included: v as DocumentFilters['included'] })} />
      {active > 0 && <button type="button" className={TEXT_BUTTON} onClick={() => { setText(''); setClient(''); onChange({ ...NO_FILTERS, limit: filters.limit }); }}>Clear {active} {active === 1 ? 'filter' : 'filters'}</button>}
    </div>
    <MoreFilters active={more}>
      <FilterSelect label="Waiting for a person" any="Sorted or not" value={filters.needs_review} options={[{ value: 'true', label: 'Needs a call type' }]} onChange={v => onChange({ needs_review: v as DocumentFilters['needs_review'] })} />
      <FilterSelect label="Processing" any="Any processing state" value={filters.extraction_status} options={options(EXTRACTION_STATUSES, EXTRACTION_LABELS)} onChange={v => onChange({ extraction_status: v as DocumentFilters['extraction_status'] })} />
      <FilterSelect label="Date" any="Dated or not" value={filters.date_state} options={[{ value: 'dated', label: 'Dated' }, { value: 'undated', label: 'Undated' }]} onChange={v => onChange({ date_state: v as DocumentFilters['date_state'] })} />
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">From
        <DateInput className={SELECT} value={filters.from} max={filters.to || undefined} onChange={e => onChange({ from: e.target.value })} /></label>
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">To
        <DateInput className={SELECT} value={filters.to} min={filters.from || undefined} onChange={e => onChange({ to: e.target.value })} /></label>
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">Client ID
        <input className={`${SELECT} w-40`} value={client} maxLength={140} onChange={e => setClient(e.target.value)} onBlur={() => client.trim() !== filters.client_id && onChange({ client_id: client.trim() })} /></label>
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">Per page
        <Select className={SELECT} value={filters.limit} onChange={e => onChange({ limit: Number(e.target.value) })}>
          {DOCUMENT_PAGE_SIZES.map(size => <option key={size} value={size}>{size}</option>)}</Select></label>
    </MoreFilters>
  </form>;
}

export function DocumentRow({ doc, onClient, canClassify = false }: { doc: DocumentSummary; onClient?: (clientId: string) => void; canClassify?: boolean }) {
  const client = doc.client_name || doc.client_id;
  return <li className="px-5 py-4 border-b last:border-b-0 border-[#EEF0F4] space-y-2" data-document={doc.transcript_id}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 space-y-1">
        <Link to={paths.document(doc.transcript_id)} className="text-[14px] font-medium text-[#1B2433] hover:underline">{doc.title}</Link>
        <p className={META}>
          <span data-date-state={doc.date_state}>{documentDay(doc)}</span>
          {' · '}{sourceLabel(doc.source_type)} · {callLabel(doc.call_type)}
          {client && <>{' · '}{doc.client_id && onClient ? <button type="button" className="hover:underline" onClick={() => onClient(doc.client_id!)}>{client}</button> : client}</>}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {doc.needs_review && <Pill tone="waiting">Needs a call type</Pill>}
        {doc.extraction_status === 'failed' && <Pill tone="alert">Processing failed</Pill>}
        <Pill tone={doc.included ? 'approved' : 'quiet'}>{doc.included ? 'Included' : 'Excluded'}</Pill>
      </div>
    </div>
    {doc.needs_review && canClassify && <ClassifyControl doc={doc} compact />}
  </li>;
}

export function DocumentsList({ filters, onChange }: { filters: DocumentFilters; onChange: (patch: Partial<DocumentFilters>) => void }) {
  const documents = useDocuments(documentQuery(filters));
  const { me } = useMe();
  const canEdit = me.can.edit_cards;
  const list = documents.data;
  return <div className="space-y-4">
    <PageHeading title="Sources" subtitle={list ? `${list.counts.included.toLocaleString('en-US')} calls included · ${list.counts.excluded.toLocaleString('en-US')} excluded` : undefined}
      actions={canEdit ? <UploadTranscriptButton /> : undefined} />
    <DocumentFilterBar filters={filters} onChange={onChange} />
    {documents.error && <ErrorState message={documents.error.message} onRetry={() => void documents.refetch()} />}
    {documents.isPending && !documents.error && <LoadingState>Loading documents…</LoadingState>}
    {list && !list.items.length && <EmptyState>{filterCount(filters) ? 'No documents match these filters.' : 'No documents have been stored yet.'}</EmptyState>}
    {list && list.items.length > 0 && <>
      <ul className={`${PANEL} overflow-hidden`} aria-label="Documents">{list.items.map(doc =>
        <DocumentRow key={doc.transcript_id} doc={doc} canClassify={canEdit} onClient={client_id => onChange({ client_id })} />)}</ul>
      <Pager range={`Showing ${pageRange(list, list.items.length)}`} hasPrevious={list.offset > 0} hasNext={list.offset + list.limit < list.total}
        onPrevious={() => onChange({ offset: Math.max(0, list.offset - list.limit) })} onNext={() => onChange({ offset: list.offset + list.limit })} />
    </>}
  </div>;
}

/** `/sources/documents`: the list, with its filters read from and written to the query string. */
export function DocumentsView() {
  const [search, setSearch] = useSearchParams();
  const filters = readFilters(search);
  const change = (patch: Partial<DocumentFilters>) => {
    // A new filter starts from the first page; moving between pages keeps the filter.
    const resets = Object.keys(patch).some(key => key !== 'offset');
    setSearch(writeFilters({ ...filters, ...patch, ...(resets && !('offset' in patch) ? { offset: 0 } : {}) }));
  };
  return <DocumentsList filters={filters} onChange={change} />;
}

const PASSAGE_CHUNK = 200;
const METHOD: Record<string, string> = { rule: 'by a rule', model: 'by the system', person: 'by a person' };

export function DocumentBody({ doc }: { doc: DocumentDetail }) {
  const [shown, setShown] = useState(PASSAGE_CHUNK);
  const { me } = useMe();
  const term = 'text-[11px] font-semibold uppercase tracking-[0.1em] text-[#A38B61]';
  return <article className="space-y-5">
    <section className={`${PANEL} p-6 space-y-5`}>
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 className="font-editorial text-[28px] leading-tight text-[#1B2433]">{doc.title}</h2>
          <div className="flex flex-wrap gap-1.5">
            {doc.needs_review && <Pill tone="waiting">Needs a call type</Pill>}
            {doc.extraction_status === 'failed' && <Pill tone="alert">Processing failed</Pill>}
            <Pill tone={doc.included ? 'approved' : 'quiet'}>{doc.included ? 'Included' : 'Excluded'}</Pill>
          </div>
        </div>
        <p className={META}><span data-date-state={doc.date_state}>{documentDay(doc)}</span> · {sourceLabel(doc.source_type)} · {callLabel(doc.call_type)}</p>
      </header>
      {!doc.included && <p className="rounded-xl bg-[#F7F8FB] p-3 text-[13px] text-[#34445F]"><span className="font-medium">Why it is excluded: </span>{exclusionText(doc)}</p>}
      {doc.canonical_document_id && <p className="rounded-xl bg-[#FFF8E9] p-3 text-[13px] text-[#947021]">This is a copy of <Link className="underline" to={paths.document(doc.canonical_document_id)}>another document</Link>, which is the one used.</p>}
      <dl className="grid gap-x-8 gap-y-4 text-[13px] sm:grid-cols-3">
        <div><dt className={term}>Client</dt><dd className="mt-1">{doc.client_name || doc.client_id || 'None recorded'}</dd></div>
        <div><dt className={term}>Week</dt><dd className="mt-1">{doc.week_id ? <Link className="text-[#5070FF] hover:underline" to={paths.week(doc.week_id)}>Open the week</Link> : 'Not tied to a week'}</dd></div>
        <div><dt className={term}>Call type</dt><dd className="mt-1">{doc.classification
          ? `${callLabel(doc.classification.call_type)}, ${METHOD[doc.classification.method ?? ''] ?? 'method not recorded'}${doc.classification.reason ? `: ${plainReason(doc.classification.reason)}` : ''}`
          : 'Not sorted yet'}</dd></div>
      </dl>
      {me.can.edit_cards && <section aria-label="Classify" className="border-t border-[#EEF0F4] pt-4 space-y-2">
        <h3 className="text-[13px] font-semibold text-[#34445F]">{doc.needs_review ? 'What kind of call is this?' : 'Change the call type'}</h3>
        <ClassifyControl key={`${doc.call_type}|${doc.classification?.method}`} doc={doc} />
      </section>}
    </section>
    <section aria-label="Participants" className={`${PANEL} p-6 space-y-3`}><h3 className="font-editorial text-xl text-[#1B2433]">Who spoke</h3>
      {doc.participants.length ? <ul className="flex flex-wrap gap-2 text-[13px]">{doc.participants.map((p, i) => <li key={`${p.name}-${i}`} className="rounded-full bg-[#F7F8FB] px-3 py-1.5">{p.name} <span className="text-[#8B93A3]">· {roleLabel(p.role)}</span></li>)}</ul>
        : <p className="text-[13px] text-[#8B93A3]">No one is recorded.</p>}</section>
    <section aria-label="What was said" className={`${PANEL} p-6 space-y-3`}><h3 className="font-editorial text-xl text-[#1B2433]">What was said</h3>
      {!doc.passages.length && <p className="text-[13px] text-[#8B93A3]">No text is stored for this document.</p>}
      <ol className="space-y-3">{doc.passages.slice(0, shown).map(p => <li key={p.passage_id} className="text-[13px] leading-relaxed">
        <p className="text-[11px] text-[#8B93A3]"><span className="font-semibold text-[#34445F]">{p.speaker}</span>{p.speaker_role ? ` · ${roleLabel(p.speaker_role)}` : ''}{clock(p.start_ms) ? ` · ${clock(p.start_ms)}` : ''}</p>
        <p className="whitespace-pre-wrap text-[#34445F]">{p.text}</p></li>)}</ol>
      {doc.passages.length > shown && <button type="button" className={QUIET_BUTTON} onClick={() => setShown(shown + PASSAGE_CHUNK)}>Show more</button>}
    </section>
  </article>;
}

/** `/sources/documents/:transcriptId`: one document, at a path that survives a refresh. */
export function DocumentView() {
  const { transcriptId = '' } = useParams();
  const document = useDocument(transcriptId);
  return <div className="space-y-4">
    <PageHeading title="Sources" subtitle="A document" />
    <Link to={paths.documents} className="inline-flex items-center gap-1 text-[12px] font-medium text-[#5070FF] hover:underline"><ArrowLeft size={14} />All documents</Link>
    {document.isPending && !document.error && <LoadingState>Loading the document…</LoadingState>}
    {document.error && <ErrorState message={document.error.message} onRetry={() => void document.refetch()} />}
    {document.data && <DocumentBody doc={document.data} />}
  </div>;
}

