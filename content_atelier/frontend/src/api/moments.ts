/* Reads of the moments API (2.B6, 2.B8, 2.B12) and the one write a person may make there (a moment's topics, 2.B7). The
   types are the generated ones, so a renamed field fails `npm run lint` after `npm run api:types`. Every moment screen
   imports from here. Whether a quote may be used is computed by the backend (`consent_status`); nothing here decides it. */
import { useQuery } from '@tanstack/react-query';
import { queryKey } from './query';
import { apiGet, apiPost, type ReadArgs, type ResponseOf } from './routes';
import type { components } from './schema';

export type MomentSummary = components['schemas']['MomentSummary'];
export type MomentList = components['schemas']['MomentList'];
export type MomentFacets = components['schemas']['MomentFacets'];
export type FacetCount = components['schemas']['FacetCount'];
export type MomentDetail = components['schemas']['MomentDetail'];
export type MomentTopic = components['schemas']['MomentTopic'];
export type SurroundingPassage = components['schemas']['SurroundingPassage'];
export type CitingCard = components['schemas']['CitingCard'];
export type Citation = components['schemas']['Citation'];
export type SearchResponse = components['schemas']['SearchResponse'];
export type SearchHit = components['schemas']['SearchHit'];
export type SearchRequest = components['schemas']['backend_pipeline__search__api__SearchRequest'];
export type SearchFilters = components['schemas']['SearchFilters'];
export type TopicSummary = components['schemas']['TopicSummary'];
export type ExtractionHealth = components['schemas']['ExtractionHealth'];
export type ExtractionStats = components['schemas']['ExtractionStats'];
export type SourceTypeStats = components['schemas']['SourceTypeStats'];
export type FailedDocument = components['schemas']['FailedDocument'];

/** The query parameters of GET /moments and /moments/facets; every one is optional. */
export type MomentQuery = NonNullable<NonNullable<ReadArgs<'/moments'>['query']>>;
export type FacetQuery = NonNullable<NonNullable<ReadArgs<'/moments/facets'>['query']>>;
export type MomentType = NonNullable<SearchFilters['moment_type']>[number];
export type SpeakerRole = NonNullable<SearchFilters['speaker_role']>[number];
export type ConsentStatus = NonNullable<SearchFilters['consent_status']>[number];
export type MomentSourceType = NonNullable<SearchFilters['source_type']>;
export type MomentCallType = NonNullable<SearchFilters['call_type']>;

export const MOMENT_PAGE_SIZES = [10, 25, 50] as const;
export const DEFAULT_MOMENT_PAGE = 25;
/** The most matches a search returns (the API's `k` is 1 to 50); pages of a search are cut from them. */
export const SEARCH_LIMIT = 50;

/** The ledger's page, newest first. `enabled` is false while a search, or a session that may not read them, is in charge. */
export function useMoments(query: MomentQuery, enabled = true) {
  return useQuery<ResponseOf<'/moments', 'get'>, Error>({
    queryKey: ['api', '/moments', query],
    queryFn: ({ signal }) => apiGet('/moments', { query }, { signal }),
    enabled, placeholderData: previous => previous,
  });
}

/** The counts behind the filter controls, each counted under the other filters. */
export function useMomentFacets(query: FacetQuery, enabled = true) {
  return useQuery<ResponseOf<'/moments/facets', 'get'>, Error>({
    queryKey: ['api', '/moments/facets', query],
    queryFn: ({ signal }) => apiGet('/moments/facets', { query }, { signal }),
    enabled, placeholderData: previous => previous,
  });
}

/** Search is a read made with POST, so it is a query keyed by its request, not a mutation. */
export function useMomentSearch(request: SearchRequest, enabled = true) {
  return useQuery<ResponseOf<'/search', 'post'>, Error>({
    queryKey: ['api', '/search', request],
    queryFn: ({ signal }) => apiPost('/search', { body: request }, { signal }),
    enabled, placeholderData: previous => previous,
  });
}

export function useMoment(momentId: string, enabled = true) {
  return useQuery<ResponseOf<'/moments/{moment_id}', 'get'>, Error>({
    queryKey: queryKey('/moments/{moment_id}', { path: { moment_id: momentId } }),
    queryFn: ({ signal }) => apiGet('/moments/{moment_id}', { path: { moment_id: momentId } }, { signal }),
    enabled: enabled && !!momentId,
  });
}

/** The active topics, for the topic filter and for an editor adding one to a moment. */
export function useTopics(enabled = true) {
  return useQuery<ResponseOf<'/topics', 'get'>, Error>({
    queryKey: ['api', '/topics', { query: { status: 'active', limit: 200 } }],
    queryFn: ({ signal }) => apiGet('/topics', { query: { status: 'active', limit: 200 } }, { signal }),
    enabled, staleTime: 60_000,
  });
}

export function useExtractionHealth(enabled = true) {
  return useQuery<ResponseOf<'/documents/extraction-health', 'get'>, Error>({
    queryKey: ['api', '/documents/extraction-health', null],
    queryFn: ({ signal }) => apiGet('/documents/extraction-health', undefined, { signal }),
    enabled, refetchInterval: 60_000,
  });
}

/** An editor adds topics to a moment or takes them off. The answer is the moment's topics. A caller re-reads what shows them afterwards
    (`useInvalidate(...MOMENT_TOPIC_READS)`); a plain call rather than a mutation, as the app's other writes are. */
export function changeMomentTopics(momentId: string, change: { add?: string[]; remove?: string[] }) {
  return apiPost('/moments/{moment_id}/topics', { path: { moment_id: momentId }, body: { add: change.add ?? [], remove: change.remove ?? [] } });
}

/** The reads a change of topics makes stale. */
export const MOMENT_TOPIC_READS = ['/moments/{moment_id}', '/moments', '/moments/facets', '/topics'] as const;
