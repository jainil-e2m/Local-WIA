/* The server-state layer (plan 1.F1): TanStack Query over the typed routes. A view asks for a route and its parameters;
   the cache shares the answer between views, polls while work is running, and drops it when a write invalidates it. */
import { QueryClient, useQuery, useQueryClient, type QueryKey, type UseQueryResult } from '@tanstack/react-query';
import { isApiError } from './client';
import { apiGet, type ReadArgs, type ResponseOf, type Route, type RoutesFor } from './routes';

/** Reads are fresh for five seconds; a refused request (4xx) is final, anything else is tried once more. */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5_000,
        refetchOnWindowFocus: true,
        retry: (count, error) => !(isApiError(error) && error.status >= 400 && error.status < 500) && count < 1,
      },
    },
  });
}

export const queryKey = (route: Route, args?: unknown): QueryKey => ['api', route, args ?? null];

export interface PollOptions<T> {
  enabled?: boolean;
  staleTime?: number;
  /** Milliseconds between reads, or false. A function decides from the latest answer, so polling stops when work ends. */
  refetchInterval?: number | false | ((data: T | undefined) => number | false);
}

export function useApiQuery<R extends RoutesFor<'get'>>(
  route: R, args?: ReadArgs<R>, options: PollOptions<ResponseOf<R, 'get'>> = {},
): UseQueryResult<ResponseOf<R, 'get'>, Error> {
  const { refetchInterval, ...rest } = options;
  return useQuery<ResponseOf<R, 'get'>, Error>({
    queryKey: queryKey(route, args),
    queryFn: ({ signal }) => (apiGet as (route: string, args: unknown, options: { signal: AbortSignal }) => Promise<ResponseOf<R, 'get'>>)(route, args, { signal }),
    refetchInterval: typeof refetchInterval === 'function' ? query => refetchInterval(query.state.data) : refetchInterval,
    ...rest,
  });
}

/** Re-reads every answer for these routes, whatever their parameters: call it after a write that changes them. */
export function useInvalidate() {
  const client = useQueryClient();
  return (...routes: Route[]) => Promise.all(routes.map(route => client.invalidateQueries({ queryKey: ['api', route] })));
}

/** The message to show for a failed read, or '' while it has not failed. */
export const queryError = (query: { error: Error | null }) => query.error?.message ?? '';
