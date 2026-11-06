import {
  DEFAULT_MOMENT_PAGE, MOMENT_PAGE_SIZES, SEARCH_LIMIT,
  type Citation, type ConsentStatus, type FacetQuery, type MomentCallType, type MomentQuery, type MomentSourceType, type MomentType, type SearchRequest,
  type SpeakerRole, type SurroundingPassage,
} from '../api/moments';

/* The moments ledger's filters (2.F1) and the plain words for what the API says about a moment (2.F2). The filters live
   in the query string of /moments, so a refresh or a shared link shows the same page of the same search. Anything in the
   URL that is not a known value is ignored.

   Nothing here decides whether a quote may be used: the consent status is the backend's, and these functions only name it. */

export const MOMENT_TYPES: readonly MomentType[] = ['result', 'testimonial', 'story', 'objection', 'decision', 'tension', 'mechanism', 'observation', 'teaching', 'soundbite', 'data_point', 'question'];
export const SPEAKER_ROLES: readonly SpeakerRole[] = ['client', 'staff', 'prospect', 'vendor', 'outside', 'ai_agent', 'unknown'];
export const CONSENT_STATUSES: readonly ConsentStatus[] = ['cleared', 'anonymise', 'internal_only', 'do_not_use'];
export const MOMENT_SOURCE_TYPES: readonly MomentSourceType[] = ['zoom', 'fathom', 'slack', 'manual', 'file', 'attachment'];
export const MOMENT_CALL_TYPES: readonly MomentCallType[] = ['client_1to1', 'office_hours', 'workshop', 'prospect', 'internal', 'vendor', 'fragment', 'slack_thread', 'other'];

/** The consent choices of the filter: none (the API's own default, which leaves out "do not use"), one status, or every status. */
export type ConsentChoice = ConsentStatus | 'all' | '';

export const MOMENT_TYPE_LABELS: Record<string, string> = {
  result: 'Result', testimonial: 'Testimonial', story: 'Story', objection: 'Objection', decision: 'Decision', tension: 'Tension', mechanism: 'How it works',
  observation: 'Observation', teaching: 'Teaching', soundbite: 'Soundbite', data_point: 'Data point', question: 'Question',
};
/** Who spoke, in the words a reviewer uses. */
export const SPEAKER_LABELS: Record<string, string> = {
  client: 'Client', staff: 'WIA team', prospect: 'Prospect', vendor: 'Vendor', outside: 'Outside voice', ai_agent: 'AI note-taker', unknown: 'Role unknown',
};
const SPEAKER_PHRASES: Record<string, string> = {
  client: 'a client', staff: 'someone on the WIA team', prospect: 'a prospect', vendor: 'a vendor', outside: 'an outside voice', ai_agent: 'the AI note-taker', unknown: 'someone whose role could not be worked out',
};
export const CONSENT_LABELS: Record<string, string> = {
  cleared: 'Cleared for naming', anonymise: 'Anonymise', internal_only: 'Internal only', do_not_use: 'Do not use',
};
/** What each status asks of the person using the quote. */
export const CONSENT_HINTS: Record<string, string> = {
  cleared: 'The client can be named alongside this quote.',
  anonymise: 'Use it without naming the client or their business.',
  internal_only: 'For the team only. It is not for public content.',
  do_not_use: 'Nothing from this client may be used.',
};
export const CONSENT_CHOICE_LABELS: Record<string, string> = { ...CONSENT_LABELS, all: 'Everything, including do not use' };

const humanise = (value: string) => value.replaceAll('_', ' ');
const article = (word: string) => `${/^[aeiou]/i.test(word) ? 'an' : 'a'} ${word}`;
const sentence = (value: string) => value ? value[0].toUpperCase() + value.slice(1) : value;

export const momentTypeLabel = (value: string | null) => value ? MOMENT_TYPE_LABELS[value] ?? sentence(humanise(value)) : 'Untyped';
export const speakerLabel = (value: string | null) => value ? SPEAKER_LABELS[value] ?? sentence(humanise(value)) : 'Role unknown';
export const consentLabel = (value: string) => CONSENT_LABELS[value] ?? sentence(humanise(value));
export const consentHint = (value: string) => CONSENT_HINTS[value] ?? '';

export interface MomentFilters {
  /** The words searched for; when set (and unverified quotes are off) the ledger searches by words and meaning. */
  q: string;
  /** Calendar days (YYYY-MM-DD) of the date window, or ''. */
  from: string; to: string;
  client_id: string; source_type: MomentSourceType | ''; call_type: MomentCallType | ''; speaker_role: SpeakerRole | ''; moment_type: MomentType | '';
  consent_status: ConsentChoice; topic_id: string;
  /** Off by default: a quote that could not be matched to its transcript is hidden. */
  unverified: boolean;
  limit: number; offset: number;
}

export const NO_MOMENT_FILTERS: MomentFilters = {
  q: '', from: '', to: '', client_id: '', source_type: '', call_type: '', speaker_role: '', moment_type: '', consent_status: '', topic_id: '', unverified: false,
  limit: DEFAULT_MOMENT_PAGE, offset: 0,
};

const ID = /^[A-Za-z0-9_-]{1,140}$/;
const oneOf = <T extends string>(value: string | null, allowed: readonly T[]): T | '' => allowed.includes(value as T) ? value as T : '';
const identifier = (value: string | null) => value && ID.test(value) ? value : '';
const day = (value: string | null) => {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return '';
  return new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value ? value : '';
};

export function readMomentFilters(params: URLSearchParams): MomentFilters {
  const limit = Number(params.get('limit'));
  const offset = Number(params.get('offset'));
  return {
    q: (params.get('q') ?? '').trim().slice(0, 200), from: day(params.get('from')), to: day(params.get('to')),
    client_id: identifier(params.get('client_id')), source_type: oneOf(params.get('source_type'), MOMENT_SOURCE_TYPES), call_type: oneOf(params.get('call_type'), MOMENT_CALL_TYPES),
    speaker_role: oneOf(params.get('speaker_role'), SPEAKER_ROLES), moment_type: oneOf(params.get('moment_type'), MOMENT_TYPES),
    consent_status: oneOf(params.get('consent_status'), [...CONSENT_STATUSES, 'all'] as const), topic_id: identifier(params.get('topic_id')),
    unverified: params.get('unverified') === '1',
    limit: (MOMENT_PAGE_SIZES as readonly number[]).includes(limit) ? limit : DEFAULT_MOMENT_PAGE,
    offset: Number.isInteger(offset) && offset > 0 ? offset : 0,
  };
}

const TEXT_KEYS = ['q', 'from', 'to', 'client_id', 'source_type', 'call_type', 'speaker_role', 'moment_type', 'consent_status', 'topic_id'] as const;

/** The query string for these filters: only what differs from the default, so the plain ledger has a plain URL. */
export function writeMomentFilters(filters: MomentFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of TEXT_KEYS) if (filters[key]) params.set(key, filters[key]);
  if (filters.unverified) params.set('unverified', '1');
  if (filters.limit !== DEFAULT_MOMENT_PAGE) params.set('limit', String(filters.limit));
  if (filters.offset) params.set('offset', String(filters.offset));
  return params;
}

/** How many filters are narrowing the ledger (the page and its size are not filters). */
export const momentFilterCount = (filters: MomentFilters) => TEXT_KEYS.filter(key => filters[key]).length + (filters.unverified ? 1 : 0);

/** Words are searched by meaning as well as by wording, but only over verified quotes: an unverified quote is found by its words in the list. */
export const searching = (filters: MomentFilters) => !!filters.q && !filters.unverified;

const nextDay = (value: string) => {
  const next = new Date(`${value}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  return `${next.toISOString().slice(0, 10)}T00:00:00Z`;
};
/** The API takes datetimes with an offset; `to` is exclusive, so the last day of a window is included by asking for the day after. */
const dateWindow = (filters: MomentFilters) => ({ ...(filters.from ? { from: `${filters.from}T00:00:00Z` } : {}), ...(filters.to ? { to: nextDay(filters.to) } : {}) });

/** The statuses the filter asks for. None is left out of the request, so the API's default (without "do not use") applies. */
export function consentList(choice: ConsentChoice): ConsentStatus[] | undefined {
  if (!choice) return undefined;
  return choice === 'all' ? [...CONSENT_STATUSES] : [choice];
}

/** The request for the list of moments (browsing, or searching unverified quotes by their words). */
export function momentQuery(filters: MomentFilters): MomentQuery {
  const consent = consentList(filters.consent_status);
  return {
    ...(filters.q ? { q: filters.q } : {}), ...(filters.client_id ? { client_id: filters.client_id } : {}),
    ...(filters.source_type ? { source_type: filters.source_type } : {}), ...(filters.call_type ? { call_type: filters.call_type } : {}),
    ...(filters.speaker_role ? { speaker_role: filters.speaker_role } : {}), ...(filters.moment_type ? { moment_type: filters.moment_type } : {}),
    ...(consent ? { consent_status: consent.join(',') } : {}), ...(filters.topic_id ? { topic_id: filters.topic_id } : {}),
    ...(filters.unverified ? { quote_verified: 'any' as const } : {}), ...dateWindow(filters),
    limit: filters.limit, offset: filters.offset,
  };
}

/** The counts for the controls: the same filters without a page. While searching, the words are left out (the counts are the ledger's, under the other filters). */
export function facetQuery(filters: MomentFilters): FacetQuery {
  const { limit: _limit, offset: _offset, ...rest } = momentQuery(filters);
  if (searching(filters)) delete rest.q;
  return rest;
}

/** The search request: the words, with the same filters. */
export function searchRequest(filters: MomentFilters): SearchRequest {
  const consent = consentList(filters.consent_status);
  const dates = dateWindow(filters);
  return {
    text: filters.q, k: SEARCH_LIMIT, scope: 'moments',
    filters: {
      ...(filters.client_id ? { client_id: filters.client_id } : {}), ...(filters.source_type ? { source_type: filters.source_type } : {}),
      ...(filters.call_type ? { call_type: filters.call_type } : {}), ...(filters.speaker_role ? { speaker_role: [filters.speaker_role] } : {}),
      ...(filters.moment_type ? { moment_type: [filters.moment_type] } : {}), ...(consent ? { consent_status: consent } : {}),
      ...(filters.topic_id ? { topic_id: filters.topic_id } : {}),
      ...(dates.from ? { date_from: dates.from } : {}), ...(dates.to ? { date_to: dates.to } : {}),
    },
  };
}

/** The page being shown, as "26 to 50 of 140 moments". */
export function momentRange(total: number, offset: number, shown: number): string {
  if (!total || !shown) return 'No moments';
  return `${offset + 1} to ${offset + shown} of ${total.toLocaleString('en-US')}`;
}

/** Why a search found a moment, in the reviewer's words. */
export function matchReason(matchedBy: readonly string[]): string {
  const phrase = matchedBy.includes('phrase'), meaning = matchedBy.includes('semantic');
  if (phrase && meaning) return 'Matches your words and their meaning';
  if (phrase) return 'Matches your words';
  if (meaning) return 'Close in meaning to your search';
  return 'Matches your search';
}

/** "4 Mar 2026", or an honest "Date not recorded". */
export function whenLine(value: string | null | undefined): string {
  if (!value) return 'Date not recorded';
  const when = new Date(value);
  return Number.isNaN(when.getTime()) ? value : when.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

// ---- what the API records about one moment, in words

const record = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const text = (value: unknown) => typeof value === 'string' && value ? value : null;
const strings = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' || typeof item === 'number').map(String) : [];

/** The facts behind a consent status, as the backend recorded them. They explain the status; they do not change it. */
export function consentReasons(checks: Record<string, unknown>): string[] {
  const consent = record(checks.consent);
  const reasons: string[] = [];
  if ('client_consent' in consent) {
    const given = text(consent.client_consent);
    reasons.push(given === 'may_name' ? 'The client has agreed to be named.'
      : given === 'anonymise_only' ? 'The client has agreed to be quoted only without their name.'
      : given === 'no_use' ? 'The client has asked that nothing from them is used.'
      : given ? `The client's permission is recorded as "${humanise(given)}".` : 'No permission is recorded for this client.');
  }
  const sensitivity = text(consent.sensitivity);
  if (sensitivity) reasons.push(sensitivity === 'public_candidate' ? 'The line looks suitable for public use.'
    : sensitivity === 'internal_only' ? 'The line was marked as for the team only.' : `The line was marked "${humanise(sensitivity)}".`);
  const kind = text(consent.evidence_kind);
  if (kind) reasons.push(kind === 'direct_quote' ? 'It is in the speaker\'s own words.' : kind === 'team_report' ? 'A team member relayed it; the client did not say it themselves.' : `The evidence is a ${humanise(kind)}.`);
  return reasons;
}

/** The checks that failed, each as a sentence. An empty list with `recorded` true means every check passed. */
export function failedChecks(checks: Record<string, unknown>): { recorded: boolean; failures: string[] } {
  const numbers = record(checks.numbers), role = record(checks.role_plausibility);
  const failures: string[] = [];
  for (const figure of strings(numbers.absent)) failures.push(`The source does not contain the figure ${figure}.`);
  for (const figure of strings(numbers.context_only)) failures.push(`The figure ${figure} appears only in the conversation around the quote, not in the line itself.`);
  if (role.passed === false) {
    const original = text(role.original_type), stored = text(role.moment_type), who = SPEAKER_PHRASES[text(role.speaker_role) ?? 'unknown'] ?? 'someone else';
    failures.push(`It was first tagged as ${original ? article(momentTypeLabel(original).toLowerCase()) : 'a client claim'}, but it was said by ${who}, and that is the client's to claim.`
      + (stored && stored !== original ? ` It is shown as ${article(momentTypeLabel(stored).toLowerCase())} instead.` : ' It is treated as a team member relaying it.'));
  }
  return { recorded: 'numbers' in checks || 'role_plausibility' in checks, failures };
}

/** The note for a quote that was repaired, and the wording before and after. */
export function repairNote(repair: Record<string, unknown> | null): { note: string; before: string | null; after: string | null } | null {
  if (!repair) return null;
  return { note: 'The quote was matched to the transcript\'s own wording.', before: text(repair.original_quote), after: text(repair.repaired_quote) };
}

export const UNVERIFIED_NOTE = 'This quote could not be matched to the transcript, so it is not shown as the speaker\'s exact words. Do not treat it as a verbatim quote.';

export const approvalLabel = (value: string) => ({ pending: 'Waiting for a decision', approved: 'Approved', rejected: 'Rejected' } as Record<string, string>)[value] ?? sentence(humanise(value));
export const evidenceRoleLabel = (value: string) => ({ supports_argument: 'Supports the argument', anchor: 'Main evidence', context: 'Context' } as Record<string, string>)[value] ?? sentence(humanise(value));

/** The quote's place inside a passage, as the text before it, the quote and the text after it; null when the passage does not hold it. */
export function highlight(passage: Pick<SurroundingPassage, 'text' | 'start' | 'end' | 'anchor' | 'cited'>, citation: Pick<Citation, 'start' | 'end' | 'quote'> | null, quote: string | null): [string, string, string] | null {
  if (citation && passage.anchor && citation.start >= passage.start && citation.end <= passage.end) {
    const from = citation.start - passage.start, to = citation.end - passage.start;
    if (passage.text.slice(from, to) === citation.quote) return [passage.text.slice(0, from), citation.quote, passage.text.slice(to)];
  }
  const wanted = quote ?? citation?.quote ?? null;
  if (wanted && passage.cited) {
    const at = passage.text.indexOf(wanted);
    if (at >= 0) return [passage.text.slice(0, at), wanted, passage.text.slice(at + wanted.length)];
  }
  return null;
}
