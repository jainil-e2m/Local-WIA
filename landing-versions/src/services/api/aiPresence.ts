import { createApi } from "./axios.config";
import type { BackendQuery, ReviewedQuery } from "@/lib/queryReview";

/**
 * The AI Presence query-review gate.
 *
 * Kept out of audits.ts deliberately: that module is the contract three audit
 * products share, and these two routes exist on one of them. They reach the
 * service through the same authenticated BFF mount, so the browser still sends
 * nothing but its session cookie.
 */

const AI_PRESENCE_BFF_BASE_URL = "/api/ai-presence";

const api = createApi(AI_PRESENCE_BFF_BASE_URL);

export interface AuditQueriesResponse {
  audit_id: string;
  queries: BackendQuery[];
}

/**
 * The generated query set awaiting review.
 *
 * The service answers 409 while the set is still being generated and 500 if
 * generation failed, so a caller polling toward `pending_user_review` should
 * treat a rejection as "not yet" and retry rather than as a dead end.
 */
export async function getAuditQueries(auditId: string): Promise<BackendQuery[]> {
  const { data } = await api.get<AuditQueriesResponse>(
    `/audits/${encodeURIComponent(auditId)}/queries`,
  );
  return data.queries ?? [];
}

export interface ConfirmQueriesResponse {
  audit_id: string;
  status: string;
  updated_query_count: number;
  already_processed?: boolean;
}

/**
 * Commit the reviewed set and release the run into evaluation.
 *
 * `queries` must be the COMPLETE final set. The service deletes the run's
 * existing rows and re-inserts exactly what it receives, so anything left out is
 * dropped from the audit — build this with buildConfirmQueriesPayload, which
 * walks every section for that reason.
 *
 * Only valid while the run is parked at `pending_user_review`; a second attempt
 * (another tab, a double click) gets 409 or `already_processed: true`. Treat
 * both as "someone already confirmed this" and re-read the run's status rather
 * than surfacing an error.
 */
export async function confirmAuditQueries(
  auditId: string,
  queries: ReviewedQuery[],
): Promise<ConfirmQueriesResponse> {
  const { data } = await api.post<ConfirmQueriesResponse>(
    `/audits/${encodeURIComponent(auditId)}/queries/confirm`,
    { queries },
  );
  return data;
}
