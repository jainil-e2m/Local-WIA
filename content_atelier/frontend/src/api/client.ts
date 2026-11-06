/* The one way the app talks to the Node server's /api/atelier relay (plan 1.F1). Every route the app calls is in the
   generated schema (schema.d.ts, from backend/openapi.json); `apiRequest` is the untyped transport under the typed
   helpers in routes.ts. */

/** A failed request. A 409 means a conflict, such as a changed hash: the screen keeps the person's input (1.F2). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
  get conflict() { return this.status === 409; }
}

export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError;
export const isConflict = (error: unknown): error is ApiError => isApiError(error) && error.conflict;
export const errorMessage = (error: unknown, fallback = 'Request failed.') => error instanceof Error && error.message ? error.message : fallback;

export interface RequestOptions {
  signal?: AbortSignal;
  /** Overrides the default 15 seconds for a slow read. */
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 15_000;
const TIMED_OUT = 'This is taking longer than it should. Wait a moment, then try again.';

function detailOf(data: { detail?: unknown; error?: unknown }): { message: string | null; code: string | null } {
  const detail = data.detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const { message, code } = detail as { message?: unknown; code?: unknown };
    return { message: typeof message === 'string' ? message : null, code: typeof code === 'string' ? code : null };
  }
  return { message: typeof detail === 'string' ? detail : typeof data.error === 'string' ? data.error : null, code: null };
}

export async function apiRequest<T>(path: string, method = 'GET', body?: unknown, options: RequestOptions = {}): Promise<T> {
  const timeout = AbortSignal.timeout(options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  const response = await fetch(`/api/atelier${path}`, {
    method, credentials: 'same-origin', cache: 'no-store', redirect: 'error',
    headers: { accept: 'application/json', ...(body ? { 'content-type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: options.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
  }).catch((error: unknown) => {
    // The browser's own words for this are "signal timed out".
    if (error instanceof Error && error.name === 'TimeoutError') throw new ApiError(TIMED_OUT, 504);
    throw error;
  });
  if (!response.headers.get('content-type')?.includes('application/json')) throw new ApiError('Weekly storage is unavailable.', response.status);
  const data = await response.json();
  if (!response.ok) {
    const { message, code } = detailOf(data ?? {});
    throw new ApiError(message || (response.status === 422 ? 'The request is invalid. Check the selected date and refresh.' : 'Weekly request failed.'), response.status, code);
  }
  return data as T;
}

/** Kept under its earlier name for the call sites that build their own path. */
export const storageRequest = apiRequest;
