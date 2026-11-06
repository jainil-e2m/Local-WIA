import { useQueries } from '@tanstack/react-query';
import { apiGet } from './routes';
import { queryKey } from './query';
import type { MomentDetail as MomentEvidence } from './schema';

/** The original evidence behind a card's moments, read only once the person asks for it (`enabled`). A moment's evidence
    is fixed, so a read stays fresh for five minutes. */
export function useMomentEvidence(momentIds: string[], enabled: boolean) {
  const results = useQueries({
    queries: momentIds.map(id => ({
      queryKey: queryKey('/moments/{moment_id}', { path: { moment_id: id } }),
      queryFn: ({ signal }: { signal: AbortSignal }) => apiGet('/moments/{moment_id}', { path: { moment_id: id } }, { signal }),
      enabled, staleTime: 300_000,
    })),
  });
  const evidence = results.flatMap(result => result.data ? [result.data] : []) as MomentEvidence[];
  return {
    evidence,
    loading: enabled && results.some(result => result.isPending),
    error: results.find(result => result.error)?.error?.message ?? '',
    retry: () => results.forEach(result => { if (result.error) void result.refetch(); }),
  };
}
