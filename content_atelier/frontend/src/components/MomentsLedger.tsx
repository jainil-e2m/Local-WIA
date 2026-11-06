import React, { useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import {
  MOMENT_PAGE_SIZES, useMomentFacets, useMomentSearch, useMoments, useTopics,
  type FacetCount, type MomentSummary,
} from '../api/moments';
import { useAuth } from '../auth/AuthProvider';
import { paths } from '../app/routes';
import { CALL_LABELS, SOURCE_LABELS } from '../utils/documents';
import {
  CONSENT_CHOICE_LABELS, CONSENT_HINTS, CONSENT_STATUSES, MOMENT_CALL_TYPES, MOMENT_SOURCE_TYPES, MOMENT_TYPES, MOMENT_TYPE_LABELS, NO_MOMENT_FILTERS,
  SPEAKER_LABELS, SPEAKER_ROLES, consentLabel, facetQuery, momentFilterCount, momentQuery, momentRange, momentTypeLabel, readMomentFilters,
  searchRequest, searching, whenLine, writeMomentFilters, type MomentFilters,
} from '../utils/moments';
import { EmptyState, ErrorState, LoadingState } from './shared/states';
import { PageHeading } from './PageHeading';
import { FilterSelect, META, MoreFilters, PANEL, Pager, Pill, SELECT, SearchBox, TEXT_BUTTON, type Tone } from './AdminParts';
import { Select } from './ThemedSelect';
import { DateInput } from './DateInput';

/* Moments, for the team: what clients and the team said on calls and in threads, as the exact words, who said them, when, for
   which client, and whether they may be used. The words in the search box are looked for by wording and by meaning (POST
   /search, on Enter); with none, the moments are listed newest first (GET /moments). The search, the type, the client and
   the consent are in view; who spoke, the source, the call type, the topic and the dates are under "More filters". Filters and
   the page are in the URL. A quote that could not be matched to its transcript is hidden unless asked for, and "do not use"
   moments are hidden until the reviewer asks for them. Whether a quote is usable is the backend's answer: this screen shows
   it. */

// Kept for the moment's page: a small neutral pill and the base for a toned one.
export const pill = 'inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-medium';
export const badge = `${pill} bg-[#F1F3F7] text-[#667184]`;
const CONSENT_TONE: Record<string, Tone> = { cleared: 'approved', anonymise: 'progress', internal_only: 'quiet', do_not_use: 'alert' };

/** The Moments area: a team view, so any other session sees only this notice and mounts nothing that would ask for the data. */
export function MomentsShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== 'team') return <><PageHeading title="Moments" /><p className="p-8">Moments are available to the internal team.</p></>;
  return <section className="space-y-6 pb-12 text-[#1B2433]">{children}</section>;
}

export function ConsentBadge({ status }: { status: string }) {
  return <span data-consent-badge={status} title={CONSENT_HINTS[status]} className="inline-flex"><Pill tone={CONSENT_TONE[status] ?? 'quiet'}>{consentLabel(status)}</Pill></span>;
}

export const TypeTag = ({ type }: { type: string | null }) => <span className={badge}>{momentTypeLabel(type)}</span>;

interface Option { value: string; label: string }
const labelled = (values: readonly string[], labels: Record<string, string>): Option[] => values.map(value => ({ value, label: labels[value] ?? value }));

export function MomentFilterBar({ filters, onChange, facets, topics }: {
  filters: MomentFilters; onChange: (patch: Partial<MomentFilters>) => void;
  facets?: { clients: FacetCount[] };
  topics?: { topic_id: string; name: string }[];
}) {
  const [text, setText] = useState(filters.q);
  const active = momentFilterCount(filters);
  const more = (['speaker_role', 'source_type', 'call_type', 'topic_id', 'from', 'to'] as const).filter(key => filters[key]).length + (filters.unverified ? 1 : 0);
  const clients: Option[] = (facets?.clients ?? []).map(c => ({ value: c.value, label: c.label || c.value }));
  if (filters.client_id && !clients.some(c => c.value === filters.client_id)) clients.unshift({ value: filters.client_id, label: filters.client_id });
  const topicOptions: Option[] = (topics ?? []).map(t => ({ value: t.topic_id, label: t.name }));
  if (filters.topic_id && !topicOptions.some(t => t.value === filters.topic_id)) topicOptions.unshift({ value: filters.topic_id, label: filters.topic_id });
  const consentOptions: Option[] = [...CONSENT_STATUSES, 'all' as const].map(value => ({ value, label: CONSENT_CHOICE_LABELS[value] }));
  return <form aria-label="Filter moments" className="space-y-3" onSubmit={e => { e.preventDefault(); onChange({ q: text.trim() }); }}>
    <div className="flex flex-wrap items-center gap-2.5">
      <SearchBox label="Search the moments" value={text} onChange={setText} placeholder="Words or an idea, then Enter…" />
      <button type="submit" className="sr-only">Search</button>
      <FilterSelect label="Type" any="All types" value={filters.moment_type} options={labelled(MOMENT_TYPES, MOMENT_TYPE_LABELS)} onChange={moment_type => onChange({ moment_type: moment_type as MomentFilters['moment_type'] })} />
      <FilterSelect label="Client" any="All clients" value={filters.client_id} options={clients} onChange={client_id => onChange({ client_id })} />
      <FilterSelect label="Consent" any="All except do not use" value={filters.consent_status} options={consentOptions} onChange={consent_status => onChange({ consent_status: consent_status as MomentFilters['consent_status'] })} />
      {active > 0 && <button type="button" className={TEXT_BUTTON} onClick={() => { setText(''); onChange({ ...NO_MOMENT_FILTERS, limit: filters.limit }); }}>Clear {active} {active === 1 ? 'filter' : 'filters'}</button>}
    </div>
    <MoreFilters active={more}>
      <FilterSelect label="Who spoke" any="Anyone speaking" value={filters.speaker_role} options={labelled(SPEAKER_ROLES, SPEAKER_LABELS)} onChange={speaker_role => onChange({ speaker_role: speaker_role as MomentFilters['speaker_role'] })} />
      <FilterSelect label="Source" any="All sources" value={filters.source_type} options={labelled(MOMENT_SOURCE_TYPES, SOURCE_LABELS)} onChange={source_type => onChange({ source_type: source_type as MomentFilters['source_type'] })} />
      <FilterSelect label="Call type" any="All call types" value={filters.call_type} options={labelled(MOMENT_CALL_TYPES, CALL_LABELS)} onChange={call_type => onChange({ call_type: call_type as MomentFilters['call_type'] })} />
      <FilterSelect label="Topic" any="All topics" value={filters.topic_id} options={topicOptions} onChange={topic_id => onChange({ topic_id })} />
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">From
        <DateInput className={SELECT} value={filters.from} max={filters.to || undefined} onChange={e => onChange({ from: e.target.value })} /></label>
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">To
        <DateInput className={SELECT} value={filters.to} min={filters.from || undefined} onChange={e => onChange({ to: e.target.value })} /></label>
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">Per page
        <Select className={SELECT} value={filters.limit} onChange={e => onChange({ limit: Number(e.target.value) })}>
          {MOMENT_PAGE_SIZES.map(size => <option key={size} value={size}>{size}</option>)}</Select></label>
      <label className="inline-flex items-center gap-2 text-[12px] text-[#667184]">
        <input type="checkbox" checked={filters.unverified} onChange={e => onChange({ unverified: e.target.checked })} />Show quotes not matched to the call</label>
    </MoreFilters>
  </form>;
}

/** Where the person came from, so the moment's page can lead back to the same filtered list. */
export const ledgerState = (location: { pathname: string; search: string }) => ({ from: `${location.pathname}${location.search}` });

/** A moment as a card: the quote, who said it and when, for which client, whether it may be used, and "Read the moment". */
export function MomentRow({ moment }: { moment: MomentSummary; matchedBy?: readonly string[] }) {
  const location = useLocation();
  return <li data-consent={moment.consent_status} className={`${PANEL} flex flex-col gap-3 p-5`}>
    <div className="flex items-center justify-end gap-3">
      <div className="flex items-center gap-1.5">
        {!moment.quote_verified && <Pill tone="waiting">Quote not verified</Pill>}
        <ConsentBadge status={moment.consent_status} />
      </div>
    </div>
    {moment.consent_status === 'do_not_use' && <p className="text-[12px] text-red-800">Shown because you asked for it. {CONSENT_HINTS.do_not_use}</p>}
    {moment.quote
      ? <blockquote className="font-editorial text-[18px] leading-snug text-[#1B2433] line-clamp-4">“{moment.quote}”</blockquote>
      : <p className="text-[13px] text-[#8B93A3]">No quote is stored for this moment.</p>}
    <p className={META}>{[moment.speaker_label || 'Speaker not recorded', whenLine(moment.occurred_at), moment.client_name].filter(Boolean).join(' · ')}</p>
    <div className="mt-auto border-t border-[#EEF0F4] pt-3">
      <Link className={TEXT_BUTTON} to={paths.moment(moment.moment_id)} state={ledgerState(location)}>Read the moment <span aria-hidden="true">→</span></Link>
    </div>
  </li>;
}

export function MomentsLedger({ filters, onChange }: { filters: MomentFilters; onChange: (patch: Partial<MomentFilters>) => void }) {
  const searchMode = searching(filters);
  const facets = useMomentFacets(facetQuery(filters));
  const topics = useTopics();
  const list = useMoments(momentQuery(filters), !searchMode);
  const found = useMomentSearch(searchRequest(filters), searchMode);
  const active = searchMode ? found : list;

  let rows: { moment: MomentSummary }[] = [], total = 0, offset = filters.offset;
  if (searchMode && found.data) {
    // A search returns its best matches in one answer; its pages are cut from them.
    const all = found.data.hits.flatMap(hit => hit.moment ? [{ moment: hit.moment }] : []);
    total = all.length;
    rows = all.slice(filters.offset, filters.offset + filters.limit);
  } else if (!searchMode && list.data) {
    rows = list.data.items.map(moment => ({ moment })); total = list.data.total; offset = list.data.offset;
  }
  const filtered = momentFilterCount(filters) > 0;
  const subtitle = list.data && !filtered ? `${list.data.total.toLocaleString('en-US')} moments from calls and threads` : 'What was said on calls and in threads, and whether it may be used';
  return <div className="space-y-5">
    <PageHeading title="Moments" subtitle={subtitle} />
    <MomentFilterBar key={filters.q} filters={filters} onChange={onChange} facets={facets.data} topics={topics.data?.items} />
    {active.error && active.data === undefined && <ErrorState message={active.error.message} onRetry={() => void active.refetch()} />}
    {active.error && active.data !== undefined && <ErrorState message={`The latest read failed: ${active.error.message}`} onRetry={() => void active.refetch()} />}
    {active.data === undefined && !active.error && <LoadingState>{searchMode ? 'Searching the moments…' : 'Loading the moments…'}</LoadingState>}
    {searchMode && found.data?.query_embedding_status === 'unavailable' &&
      <p role="status" className="rounded-xl bg-[#FFF8E9] p-3 text-[13px] text-[#947021]">Matching by meaning is not available right now, so this search looked for your words only.</p>}
    {searchMode && found.data && found.data.hits_withheld > 0 &&
      <p role="status" className="rounded-xl bg-[#FFF8E9] p-3 text-[13px] text-[#947021]">{found.data.hits_withheld} {found.data.hits_withheld === 1 ? 'match was' : 'matches were'} left out because the quote could not be checked against the call.</p>}
    {active.data !== undefined && !rows.length && !total && <EmptyState>{filtered
      ? <>No moments match {filters.q ? 'this search and these filters' : 'these filters'}.</>
      : 'No moments have been found yet.'}</EmptyState>}
    {rows.length > 0 && <>
      <ul className="grid grid-cols-1 items-stretch gap-4 xl:grid-cols-2" aria-label="Moments">{rows.map(row =>
        <MomentRow key={row.moment.moment_id} moment={row.moment} />)}</ul>
      <Pager range={`${searchMode ? `Best ${total.toLocaleString('en-US')} ${total === 1 ? 'match' : 'matches'} for “${filters.q}”: ` : ''}Showing ${momentRange(total, offset, rows.length)}`}
        hasPrevious={offset > 0} hasNext={offset + filters.limit < total}
        onPrevious={() => onChange({ offset: Math.max(0, offset - filters.limit) })} onNext={() => onChange({ offset: offset + filters.limit })} />
    </>}
  </div>;
}

/** `/moments`: the ledger, with its filters read from and written to the query string. */
export function MomentsView() {
  const [search, setSearch] = useSearchParams();
  const filters = readMomentFilters(search);
  const change = (patch: Partial<MomentFilters>) => {
    // A new filter starts from the first page; moving between pages keeps the filter.
    const resets = Object.keys(patch).some(key => key !== 'offset');
    setSearch(writeMomentFilters({ ...filters, ...patch, ...(resets && !('offset' in patch) ? { offset: 0 } : {}) }));
  };
  return <MomentsLedger filters={filters} onChange={change} />;
}
