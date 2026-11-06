export async function storageRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api/atelier${path}`, { method, credentials: 'same-origin', cache: 'no-store', redirect: 'error',
    headers: { accept: 'application/json', ...(body ? { 'content-type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}), signal: AbortSignal.timeout(15_000) });
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Weekly storage is unavailable.');
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === 'object' && !Array.isArray(data.detail) ? data.detail?.message : typeof data.detail === 'string' ? data.detail : null;
    const error = new Error(detail || data.error || (response.status === 422 ? 'The request is invalid. Check the selected date and refresh.' : 'Weekly request failed.')) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  return data as T;
}
