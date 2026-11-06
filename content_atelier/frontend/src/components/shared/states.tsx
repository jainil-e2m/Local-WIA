import React from 'react';

/* Loading, empty and error states shared by every backend-backed view (plan 1.F2). A view shows one of them instead of
   its own paragraph, so a failed read looks and behaves the same everywhere: a message and a way to try again. */

export function LoadingState({ children = 'Loading…' }: { children?: React.ReactNode }) {
  return <p role="status" className="text-sm text-slate-500">{children}</p>;
}

export function EmptyState({ children, tone = 'plain' }: { children: React.ReactNode; tone?: 'plain' | 'dashed' }) {
  return <div role="status" className={`rounded-xl p-4 text-sm ${tone === 'dashed' ? 'border border-dashed' : 'bg-white border border-[#E8EBF1]'}`}>{children}</div>;
}

export function ErrorState({ message, onRetry, retryLabel = 'Retry' }: { message: string; onRetry?: () => void; retryLabel?: string }) {
  return <div role="alert" className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
    {message}
    {onRetry && <button type="button" className="ml-4 underline" onClick={onRetry}>{retryLabel}</button>}
  </div>;
}

interface QueryLike<T> { data: T | undefined; error: Error | null; isPending: boolean; isFetching?: boolean; refetch: () => unknown }

/** Renders the right state for a read: loading while the first answer is awaited, an error with a retry when it failed
    and nothing is cached, the empty state when the answer has nothing in it, and the answer otherwise. A refresh that
    fails after a good answer keeps the answer on screen and shows the error above it. */
export function QueryState<T>({ query, loading, empty, isEmpty, children }: {
  query: QueryLike<T>;
  loading?: React.ReactNode;
  empty?: React.ReactNode;
  isEmpty?: (data: T) => boolean;
  children: (data: T) => React.ReactNode;
}) {
  if (query.data === undefined) {
    if (query.error) return <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />;
    return <LoadingState>{loading ?? 'Loading…'}</LoadingState>;
  }
  if (isEmpty?.(query.data)) return <EmptyState>{empty ?? 'Nothing to show yet.'}</EmptyState>;
  return <>
    {query.error && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
    {children(query.data)}
  </>;
}
