/* ────────────────────────────────────────────────────────────────
   Audit history.
   Populated from the backend audit runner once it's wired up — the
   History page reads this array. Empty until then, so the page shows
   its empty state. "running" entries render in the live section,
   everything else under Past audits (newest first).
   ──────────────────────────────────────────────────────────────── */

import type { AuditType } from "@/services/api/audits";

/** User-facing terminal states preserve the backend's partial-success signal. */
export type AuditStatus = "running" | "completed" | "partial" | "failed";

export interface AuditRecord {
  id: string;
  /** Must match a tool id in src/data/tools.ts (drives icon + colors). */
  toolId: string;
  /** Which audit service this row came from — status refreshes and progress
      streams must be reopened against the same one. */
  auditType: AuditType;
  /** e.g. "Full site crawl", "Core Web Vitals check" */
  label: string;
  /** Display name of the business the audit ran against. */
  business: string;
  /** The business site's URL (shown as the subline in the list view). */
  businessUrl: string;
  status: AuditStatus;
  /**
   * The run is parked waiting for a person, not for the pipeline. AI Presence
   * stops after generating its query set and evaluates nothing until that set is
   * confirmed, so such a row needs its own call to action rather than a progress
   * chip that will never move.
   */
  awaitingReview?: boolean;
  /** Backend-estimated overall completion for a running audit. */
  progressPercent?: number;
  /** Current persisted backend operation/check. */
  progressStage?: string;
  /** Last time the worker persisted progress. */
  progressUpdatedAt?: string;
  /** Timestamp from the backend (ISO string or display string). */
  startedAt: string;
  /** Raw ISO timestamp behind `startedAt`, used to order rows across services.
      `startedAt` is already localized for display and does not sort correctly. */
  sortKey?: string;
  duration?: string;
  /** Short human summary shown on the row. */
  summary?: string;
  /** Backend failure/cancellation detail, shown only for terminal failures. */
  failureReason?: string;
  /** Link to the downloadable report, when the run produced one. */
  reportUrl?: string;
  /**
   * The run finished and reported a report, but its PDF has not landed yet. AI
   * Presence renders on a queue after the run goes terminal, so this is a real
   * state rather than an error: the row shows "Preparing" and is polled until
   * the link appears or the wait window closes.
   */
  reportPending?: boolean;
}

export const audits: AuditRecord[] = [];
