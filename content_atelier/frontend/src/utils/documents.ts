import type { CallType, DocumentQuery, DocumentSummary, ExtractionStatus, SourceType } from '../api/documents';
import { DEFAULT_DOCUMENT_PAGE, DOCUMENT_PAGE_SIZES } from '../api/documents';

/* The Sources view's document filters (1.F3). They live in the query string of /sources/documents, so a refresh or a
   shared link shows the same page of the same filter. Anything in the URL that is not a known value is ignored. */

export const SOURCE_TYPES: readonly SourceType[] = ['zoom', 'fathom', 'slack', 'manual', 'file', 'attachment'];
export const CALL_TYPES: readonly CallType[] = ['client_1to1', 'office_hours', 'workshop', 'prospect', 'internal', 'vendor', 'fragment', 'slack_thread', 'other'];
export const EXTRACTION_STATUSES: readonly ExtractionStatus[] = ['pending', 'queued', 'running', 'completed', 'failed', 'not_applicable'];

export const SOURCE_LABELS: Record<string, string> = { zoom: 'Zoom', fathom: 'Fathom', slack: 'Slack', manual: 'Manual entry', file: 'File import', attachment: 'Slack attachment' };
export const CALL_LABELS: Record<string, string> = {
  client_1to1: 'Client 1:1', office_hours: 'Office hours', workshop: 'Workshop', prospect: 'Prospect call', internal: 'Internal',
  vendor: 'Vendor', fragment: 'Fragment', slack_thread: 'Slack thread', other: 'Other',
};
export const EXTRACTION_LABELS: Record<string, string> = {
  pending: 'Waiting', queued: 'Queued', running: 'Running', completed: 'Done', failed: 'Failed', not_applicable: 'Not applicable',
};
export const ROLE_LABELS: Record<string, string> = {
  staff: 'WIA staff', client: 'Client', prospect: 'Prospect', vendor: 'Vendor', outside: 'Outside voice', ai_agent: 'AI note-taker', unknown: 'Role unknown',
};

export interface DocumentFilters {
  source_type: SourceType | ''; call_type: CallType | ''; included: 'true' | 'false' | ''; extraction_status: ExtractionStatus | '';
  date_state: 'dated' | 'undated' | ''; client_id: string; q: string;
  /** Only the calls the rules could not place, which wait for a person (1.F6). */
  needs_review: 'true' | '';
  /** Calendar days (YYYY-MM-DD) of the date window, or ''. */
  from: string; to: string; limit: number; offset: number;
}

export const NO_FILTERS: DocumentFilters = { source_type: '', call_type: '', included: '', extraction_status: '', date_state: '', client_id: '', q: '', needs_review: '', from: '', to: '', limit: DEFAULT_DOCUMENT_PAGE, offset: 0 };

const oneOf = <T extends string>(value: string | null, allowed: readonly T[]): T | '' => allowed.includes(value as T) ? value as T : '';
const day = (value: string | null) => {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return '';
  return new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value ? value : '';
};

export function readFilters(params: URLSearchParams): DocumentFilters {
  const limit = Number(params.get('limit'));
  const offset = Number(params.get('offset'));
  return {
    source_type: oneOf(params.get('source_type'), SOURCE_TYPES), call_type: oneOf(params.get('call_type'), CALL_TYPES),
    included: oneOf(params.get('included'), ['true', 'false'] as const), extraction_status: oneOf(params.get('extraction_status'), EXTRACTION_STATUSES),
    date_state: oneOf(params.get('date_state'), ['dated', 'undated'] as const),
    client_id: (params.get('client_id') ?? '').slice(0, 140), q: (params.get('q') ?? '').trim().slice(0, 200),
    needs_review: oneOf(params.get('needs_review'), ['true'] as const),
    from: day(params.get('from')), to: day(params.get('to')),
    limit: (DOCUMENT_PAGE_SIZES as readonly number[]).includes(limit) ? limit : DEFAULT_DOCUMENT_PAGE,
    offset: Number.isInteger(offset) && offset > 0 ? offset : 0,
  };
}

/** The query string for these filters: only what differs from the default, so the plain list has a plain URL. */
export function writeFilters(filters: DocumentFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of ['source_type', 'call_type', 'included', 'extraction_status', 'date_state', 'client_id', 'q', 'needs_review', 'from', 'to'] as const) {
    if (filters[key]) params.set(key, filters[key]);
  }
  if (filters.limit !== DEFAULT_DOCUMENT_PAGE) params.set('limit', String(filters.limit));
  if (filters.offset) params.set('offset', String(filters.offset));
  return params;
}

/** The request for these filters: the date window becomes datetimes with an offset (UTC), as the API asks. */
/** The API's `to` is exclusive, so the last day of a window is included by asking for the start of the day after. */
const nextDay = (value: string) => {
  const next = new Date(`${value}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  return `${next.toISOString().slice(0, 10)}T00:00:00Z`;
};

export function documentQuery(filters: DocumentFilters): DocumentQuery {
  return {
    ...(filters.source_type ? { source_type: filters.source_type } : {}), ...(filters.call_type ? { call_type: filters.call_type } : {}),
    ...(filters.included ? { included: filters.included === 'true' } : {}), ...(filters.extraction_status ? { extraction_status: filters.extraction_status } : {}),
    ...(filters.date_state ? { date_state: filters.date_state } : {}), ...(filters.client_id ? { client_id: filters.client_id } : {}),
    ...(filters.q ? { q: filters.q } : {}), ...(filters.needs_review ? { needs_review: true } : {}),
    ...(filters.from ? { from: `${filters.from}T00:00:00Z` } : {}), ...(filters.to ? { to: nextDay(filters.to) } : {}),
    limit: filters.limit, offset: filters.offset,
  };
}

export const filterCount = (filters: DocumentFilters) =>
  (['source_type', 'call_type', 'included', 'extraction_status', 'date_state', 'client_id', 'q', 'needs_review', 'from', 'to'] as const).filter(key => filters[key]).length;

const humanise = (value: string) => value.replaceAll('_', ' ');

/** "Dated 14 Oct 2026, from the file name", or an explicit "Undated" with nothing implied about when it happened. */
export function dateLine(doc: Pick<DocumentSummary, 'date_state' | 'occurred_at' | 'date_source'>): string {
  if (doc.date_state === 'undated' || !doc.occurred_at) return 'Undated: no evidence of when this happened';
  const when = new Date(doc.occurred_at);
  const text = Number.isNaN(when.getTime()) ? doc.occurred_at : when.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  return doc.date_source ? `${text}, dated from ${humanise(doc.date_source)}` : `${text}, source not recorded`;
}

export function inclusionLine(doc: Pick<DocumentSummary, 'included' | 'exclusion_reason'>): string {
  if (doc.included) return 'Included';
  return doc.exclusion_reason ? `Excluded: ${doc.exclusion_reason}` : 'Excluded, no reason recorded';
}

export const sourceLabel = (value: string) => SOURCE_LABELS[value] ?? humanise(value);
export const callLabel = (value: string | null) => value ? CALL_LABELS[value] ?? humanise(value) : 'Not classified';
export const extractionLabel = (value: string) => EXTRACTION_LABELS[value] ?? humanise(value);
export const roleLabel = (value: string | null) => value ? ROLE_LABELS[value] ?? humanise(value) : 'Role unknown';

/** The page being shown, as "51 to 100 of 170". */
export function pageRange(list: { total: number; offset: number; limit: number }, shown: number): string {
  if (!list.total || !shown) return 'No documents';
  return `${list.offset + 1} to ${list.offset + shown} of ${list.total.toLocaleString('en-US')}`;
}

/** "12:05" for a passage's start, or '' when the source gave no time. */
export function clock(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || ms < 0) return '';
  const total = Math.floor(ms / 1000), h = Math.floor(total / 3600), m = Math.floor(total / 60) % 60, s = total % 60;
  return `${h ? `${h}:${String(m).padStart(2, '0')}` : m}:${String(s).padStart(2, '0')}`;
}
