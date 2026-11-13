import {
  countVisibilityQueries,
  mapBackendStatusToVisibilityStage,
  type QuerySection,
  type VisibilityStage,
} from "@/lib/queryReview";

/**
 * What a listed audit offers the user, and how to pick a parked run back up.
 *
 * Ported from f-o_ai_readiness (`features/audit/utils/pastAuditsFlow.js`). The
 * scenario it exists for: someone starts a presence audit, walks away while it
 * waits for query approval, runs something else, and needs the list to tell them
 * which run is blocked on them and to restore that run's review exactly as they
 * left it.
 */

export const AUDIT_ACTION = {
  VIEW_PROGRESS: "view_progress",
  REQUIRE_APPROVAL: "require_approval",
  VIEW_REPORT: "view_report",
  NONE: "none",
} as const;
export type AuditAction = (typeof AUDIT_ACTION)[keyof typeof AUDIT_ACTION];

/**
 * The subset of a listed audit these decisions need. Kept structural rather than
 * importing HistoryPage's record type: the same logic runs against a live run on
 * the tool page, which has no such record.
 */
export interface ActionableAudit {
  /** Dashboard-vocabulary status: queued | running | completed | partial | failed. */
  status?: string;
  /** The service's own untranslated status — `pending_user_review` lives here. */
  backendStatus?: string;
  /** Set by the API when the run is parked awaiting query confirmation. */
  awaitingReview?: boolean;
  reportReady?: boolean;
}

export const isAuditInFlight = (audit: ActionableAudit | null | undefined) =>
  audit?.status === "queued" || audit?.status === "running";

export const isAuditTerminal = (audit: ActionableAudit | null | undefined) =>
  audit?.status === "completed" || audit?.status === "partial" || audit?.status === "failed";

/**
 * Whether this run is blocked on the user confirming its query set.
 *
 * Reads the API's `awaiting_review` flag first and falls back to the raw status.
 * Both are checked because the flag is newer than the status: a response cached
 * or replayed from before it existed still resolves correctly.
 */
export const requiresQueryApproval = (audit: ActionableAudit | null | undefined) =>
  isAuditInFlight(audit) &&
  (audit?.awaitingReview === true || audit?.backendStatus === "pending_user_review");

export function resolveAuditAction(
  audit: ActionableAudit | null | undefined,
  { hasReport = false }: { hasReport?: boolean } = {},
): AuditAction {
  if (!audit) return AUDIT_ACTION.NONE;

  if (isAuditInFlight(audit)) {
    return requiresQueryApproval(audit)
      ? AUDIT_ACTION.REQUIRE_APPROVAL
      : AUDIT_ACTION.VIEW_PROGRESS;
  }

  if (audit.status === "failed") return AUDIT_ACTION.NONE;

  if (audit.status === "completed" || audit.status === "partial") {
    return hasReport || audit.reportReady ? AUDIT_ACTION.VIEW_REPORT : AUDIT_ACTION.NONE;
  }

  return AUDIT_ACTION.NONE;
}

export function auditActionLabel(
  audit: ActionableAudit | null | undefined,
  options: { hasReport?: boolean } = {},
): string {
  const action = resolveAuditAction(audit, options);

  // A finished run whose report has not landed yet is not "nothing to do" — it
  // is momentarily between states, and saying so beats an empty cell.
  if (
    action === AUDIT_ACTION.NONE &&
    (audit?.status === "completed" || audit?.status === "partial") &&
    !audit?.reportReady &&
    !options.hasReport
  ) {
    return "Finalizing…";
  }

  switch (action) {
    case AUDIT_ACTION.REQUIRE_APPROVAL:
      return "Review queries";
    case AUDIT_ACTION.VIEW_PROGRESS:
      return "View progress";
    case AUDIT_ACTION.VIEW_REPORT:
      return "View report";
    default:
      return "";
  }
}

/* ── Resuming a run ────────────────────────────────────────────── */

export interface ResumePlan {
  backendStatus: string;
  stage: VisibilityStage;
  /** Keep the sections already in memory rather than refetching over an edit. */
  preserveQueries: boolean;
  shouldFetchQueries: boolean;
  shouldClearQueries: boolean;
}

/**
 * How to restore the review panel for a run being reopened.
 *
 * The `preserveQueries` branch is what stops a poll landing mid-review from
 * wiping edits the user has not confirmed yet; `shouldClearQueries` is its
 * inverse, and exists so reopening a *different* run cannot inherit the previous
 * one's query set — the cross-contamination the original was written to prevent.
 */
export function buildResumePlan(
  audit: ActionableAudit | null | undefined,
  existing: { stage?: VisibilityStage; queries?: QuerySection[] } | null = null,
): ResumePlan {
  const backendStatus = audit?.backendStatus || audit?.status || "queued";
  const hasQueries = countVisibilityQueries(existing?.queries) > 0;

  const stageFromBackend = mapBackendStatusToVisibilityStage(backendStatus, {
    visibilityQueriesStage: existing?.stage,
    hasQueries,
  });

  const stage: VisibilityStage =
    backendStatus === "running_evals" ||
    backendStatus === "running" ||
    backendStatus === "complete"
      ? "confirmed"
      : stageFromBackend;

  const preserveQueries =
    hasQueries &&
    (stage === "showing" ||
      stage === "confirmed" ||
      existing?.stage === "showing" ||
      existing?.stage === "confirmed");

  return {
    backendStatus,
    stage,
    preserveQueries,
    shouldFetchQueries: requiresQueryApproval(audit) && !preserveQueries,
    shouldClearQueries: !preserveQueries,
  };
}
