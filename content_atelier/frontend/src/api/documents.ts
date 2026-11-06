/* Reads of the documents API (1.B8, 1.F3). The types are the generated ones, so a renamed field fails `npm run lint`
   after `npm run api:types`. Every document screen imports from here. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, type ReadArgs, type ResponseOf } from './routes';
import type { components } from './schema';

export type DocumentSummary = components['schemas']['DocumentSummary'];
export type DocumentList = components['schemas']['DocumentList'];
export type DocumentDetail = components['schemas']['DocumentDetail'];
export type DocumentCounts = components['schemas']['DocumentCounts'];
export type DocumentPassage = components['schemas']['DocumentPassage'];
export type ClassificationRequest = components['schemas']['ClassificationRequest'];
export type DocumentUpload = components['schemas']['DocumentUpload'];
export type DocumentUploadResult = components['schemas']['DocumentUploadResult'];

/** The longest transcript the API accepts, in characters (DocumentUpload.content). */
export const UPLOAD_CHARACTERS = 2_000_000;

/** The query parameters of GET /documents; every one is optional. */
export type DocumentQuery = NonNullable<NonNullable<ReadArgs<'/documents'>['query']>>;
type Filter<K extends keyof DocumentQuery> = NonNullable<DocumentQuery[K]>;
export type SourceType = Filter<'source_type'>;
export type CallType = Filter<'call_type'>;
export type ExtractionStatus = Filter<'extraction_status'>;

export const DOCUMENT_PAGE_SIZES = [25, 50, 100, 200] as const;
export const DEFAULT_DOCUMENT_PAGE = 50;

/** A page of documents under these filters. `enabled` stays false for a session that may not read them. */
export function useDocuments(query: DocumentQuery, enabled = true) {
  return useQuery<ResponseOf<'/documents', 'get'>, Error>({
    queryKey: ['api', '/documents', query],
    queryFn: ({ signal }) => apiGet('/documents', { query }, { signal }),
    enabled, placeholderData: previous => previous, refetchInterval: 30_000,
  });
}

/** After a write: the lists and that document are read again. */
function useRefresh() {
  const client = useQueryClient();
  return (transcriptId?: string) => Promise.all([
    client.invalidateQueries({ queryKey: ['api', '/documents'] }),
    ...(transcriptId ? [client.invalidateQueries({ queryKey: ['api', '/documents/{transcript_id}', transcriptId] })] : []),
  ]);
}

/** A person sets a document's call type (1.F6). The backend records the decision as a person's, which no rule overwrites. */
export function useClassifyDocument(transcriptId: string) {
  const refresh = useRefresh();
  return useMutation<ResponseOf<'/documents/{transcript_id}/classification', 'post'>, Error, ClassificationRequest>({
    mutationFn: request => apiPost('/documents/{transcript_id}/classification', { path: { transcript_id: transcriptId }, body: request }),
    onSuccess: () => refresh(transcriptId),
  });
}

/** One transcript file through the same import as `documents import` (1.F7). */
export function useUploadDocument() {
  const refresh = useRefresh();
  return useMutation<DocumentUploadResult, Error, DocumentUpload>({
    mutationFn: upload => apiPost('/documents/import', { body: upload }),
    onSuccess: result => refresh(result.transcript_id),
  });
}

export function useDocument(transcriptId: string, enabled = true) {
  return useQuery<ResponseOf<'/documents/{transcript_id}', 'get'>, Error>({
    queryKey: ['api', '/documents/{transcript_id}', transcriptId],
    queryFn: ({ signal }) => apiGet('/documents/{transcript_id}', { path: { transcript_id: transcriptId } }, { signal }),
    enabled: enabled && !!transcriptId,
  });
}
