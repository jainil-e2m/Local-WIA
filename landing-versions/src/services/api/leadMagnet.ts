import { createApi } from "./axios.config";

/**
 * Lead Magnet captured-lead records, served by this dashboard's own Express
 * server (the INTERIM store — see Lead_Magnet/leadmagnet_central_dashboard_integration.md).
 * The browser talks same-origin, so the session cookie rides along and the
 * server enforces auth on everything except the public capture POST the
 * funnel site uses. When the three per-service Lead Magnet backends exist,
 * this module re-points at their BFF mounts and nothing above it changes.
 */

/** The only sources the Lead Magnet funnels produce (retired types never appear). */
export type LeadType = "technical_seo" | "onpage_seo" | "ai_seo";

export interface LeadDetails {
  score?: number;
  grade?: string;
  passed?: number;
  warnings?: number;
  critical?: number;
  /* A real Technical SEO snapshot reports five severities where this shape
     originally carried three. Older leads simply lack these keys — the store
     sanitizes `details` field-by-field, so a partial object is normal. */
  opportunities?: number;
  info?: number;
  /** Identifier of the audit behind this lead. The audit service keeps both
   *  report formats durably, so the id is enough to retrieve them later. */
  audit_id?: string;
  /** "FULL_AUDIT_COMPLETED" marks a lead whose deep-dive audit has run. */
  scheduler_cron?: string;
  last_audit_time?: string;
}

export interface Lead {
  /** Primary key (opaque). Used for every PATCH/DELETE — never displayed. */
  id: string;
  /**
   * Human-readable display number, server-assigned from 1 upwards. Stable: it
   * never shifts when the table is re-sorted, and is never reused after a
   * delete. Optional only to tolerate a record written before it existed.
   */
  seq?: number;
  name: string;
  email: string;
  phone?: string;
  domainUrl?: string;
  type: LeadType;
  /** ISO 8601 UTC, server-assigned. The list arrives newest-first. */
  timestamp: string;
  details?: LeadDetails;
  /**
   * Free-text note written by whoever is working the pipeline — not captured
   * from the lead. Writable only through updateLead (the public capture
   * endpoint ignores it).
   */
  notes?: string;
  /**
   * The call this lead booked through the funnel's scheduler, pushed by zcal's
   * webhook. Absent until they book.
   *
   * `bookedEmail` / `bookedName` are the details entered on zcal's own form,
   * which the funnel pre-fills but the prospect can change. They are kept
   * separate from `email` / `name` rather than overwriting them: the submitted
   * identity and the booking identity are different facts, and the console shows
   * when they disagree.
   */
  meeting?: LeadMeeting;
  /**
   * The audit run attached to this lead.
   *
   * The server has always projected these three (rowToLead in leads-db.mjs, and
   * sanitizeState in leads-store.mjs preserves them across a reload) — they were
   * simply never declared here, so the console could not read a run it already
   * had. Declaring them is a compile-time change only.
   *
   * `auditStatus` is the SHARED vocabulary: queued | running | completed |
   * completed_partial | failed | cancelled | interrupted. On-Page's own 14-value
   * status is translated to it server-side, so this never carries a
   * product-specific value.
   */
  auditId?: string;
  auditStatus?: string;
  /** Why the run ended badly. Present only for a failed/interrupted run. */
  auditError?: string;
  /**
   * Client PDF for the finished full audit — an absolute link, stored when the
   * run completed successfully. Absent for a failed run, and for any lead whose
   * audit finished before the console started capturing it.
   */
  auditReportUrl?: string;
  /**
   * ISO 8601 — when a FULL audit was started from this console, and only then.
   *
   * Provenance for `auditId`, which has two producers that mean different runs:
   * the funnel's own quick audit (pushed in by an audit backend) and a deep-dive
   * started here. Only the latter stamps this. Without it the console cannot
   * tell them apart, and every funnel-captured lead read as "a full audit is
   * already running" — see hasRunInFlight in server/leadmagnet-full-audit.mjs.
   */
  fullAuditStartedAt?: string;
}

/**
 * Statuses that mean the run ENDED, whatever the outcome.
 *
 * The exact twin of TERMINAL_FULL_AUDIT_STATUSES in
 * server/leadmagnet-full-audit.mjs. It has to be, because the console decides
 * from this whether to offer "Run full audit" or a live "Running" control, and
 * the server decides from its copy whether a start request launches a new run or
 * attaches to the existing one. If the two disagree, the console offers a button
 * that does the opposite of what it says.
 */
export const TERMINAL_AUDIT_STATUSES = [
  "completed",
  "completed_partial",
  "failed",
  "cancelled",
  "interrupted",
] as const;

/**
 * Is a full audit for this lead still in flight?
 *
 * Mirrors hasRunInFlight() in server/leadmagnet-full-audit.mjs, INCLUDING its
 * empty-status rule: an `auditId` with no recorded status was written by an
 * older code path that tracked none, and is treated as finished rather than
 * pinning the row on "Running" forever.
 */
export function isFullAuditRunning(lead: Lead): boolean {
  if (!lead.auditId) return false;
  // Provenance before status, mirroring the server. An audit id the funnel
  // pushed in is not a full run, however its status reads.
  if (!lead.fullAuditStartedAt) return false;
  const status = typeof lead.auditStatus === "string" ? lead.auditStatus.trim() : "";
  if (!status) return false;
  return !(TERMINAL_AUDIT_STATUSES as readonly string[]).includes(status);
}

export interface LeadMeeting {
  /** zcal's event id. Stable across a reschedule, which is how one is matched. */
  eventId?: string;
  /** ISO 8601 UTC — the absolute instant the call starts. */
  startsAt: string;
  durationMinutes?: number;
  /** The prospect's IANA zone, as they booked in. */
  timezone?: string;
  /** A cancelled booking keeps its time: cancelled is not the same as never booked. */
  status: "booked" | "cancelled";
  /** Google Meet / Zoom link zcal generated. */
  url?: string;
  bookedEmail?: string;
  bookedName?: string;
  /**
   * Answers to the invite's own questions, as typed on zcal's booking form.
   *
   * Keyed by the question's text because zcal gives answers no stable id. The
   * console renders these in the Notes card but never merges them into `notes` —
   * that column is the operator's, and an inbound push must not overwrite it.
   */
  questionAnswers?: LeadMeetingAnswer[];
}

export interface LeadMeetingAnswer {
  /** The question as the client worded it. Absent if zcal sent no label. */
  question?: string;
  answer: string;
}

export interface LeadInput {
  name: string;
  email: string;
  phone?: string;
  domainUrl?: string;
  type: LeadType;
  details?: LeadDetails;
}

export interface LeadPatch {
  name?: string;
  email?: string;
  phone?: string;
  domainUrl?: string;
  /** Merged per-field server-side, so partial score updates are safe. */
  details?: LeadDetails;
  /** Replaces the stored note; an empty/whitespace value clears it. */
  notes?: string;
}

const api = createApi("/api/leadmagnet");

/** All captured leads, newest first. */
export async function listLeads(): Promise<Lead[]> {
  const { data } = await api.get<{ leads: Lead[] }>("/leads");
  return data.leads;
}

export async function createLead(input: LeadInput): Promise<Lead> {
  const { data } = await api.post<{ lead: Lead }>("/leads", input);
  return data.lead;
}

export async function updateLead(id: string, patch: LeadPatch): Promise<Lead> {
  const { data } = await api.patch<{ lead: Lead }>(`/leads/${encodeURIComponent(id)}`, patch);
  return data.lead;
}

export async function deleteLead(id: string): Promise<void> {
  await api.delete(`/leads/${encodeURIComponent(id)}`);
}

/* ── Full audit ────────────────────────────────────────────────────
   The console's "Run full audit" button. The dashboard server owns the mapping
   from a lead to its product's audit service and holds that service's token, so
   the browser never learns either — it only ever addresses a LEAD.

   Two calls, and the poll is the important one: it is an idempotent tick that
   records a finished run as a side effect. So progress is not something this tab
   is responsible for keeping alive. Closing it loses nothing; the next caller —
   a reload, another operator — finishes the run instead. That matters because a
   full audit is budgeted in hours, unlike the ~50s snapshot this replaced. */

export interface FullAuditStart {
  auditId: string;
  auditStatus: string;
  /** Tool page that can render this run: /automations/<toolId>?run=<auditId>. */
  toolId: string;
  /** True when a run was already going and this call joined it. */
  attached: boolean;
  lead?: Lead;
}

export type FullAuditState = "idle" | "running" | "completed" | "failed" | "unknown";

export interface FullAuditProgress {
  state: FullAuditState;
  auditId?: string;
  toolId?: string;
  auditStatus?: string;
  percent?: number;
  stage?: string;
  message?: string;
  lead?: Lead;
}

/**
 * Identity the operator supplies before an AI SEO run.
 *
 * Only AI SEO asks for any — its backend declares country and state required and
 * a lead row has no geography at all. The server owns which product needs what;
 * this is only the carrier. Blank values are dropped server-side rather than
 * sent as empty strings, because a padded identity resolves to the wrong company
 * in the Knowledge Graph lookup.
 */
export interface FullAuditIdentity {
  country?: string;
  state?: string;
  city?: string;
  businessType?: string;
  /**
   * Overrides the lead's own `name` for this run.
   *
   * Offered because for AI SEO the business name is the primary Knowledge Graph
   * query term, and the funnel field that fills `lead.name` is labelled "Name*"
   * — so it carries a contact's name about as often as a company's.
   */
  businessName?: string;
}

/**
 * Which identity fields each funnel must supply before a full audit can start.
 *
 * A UI HINT, NOT THE RULE. The server owns the real requirement (see
 * FULL_AUDIT_PRODUCTS in server/leadmagnet-full-audit.mjs) and answers 422
 * `identity_required` naming what is missing, so a stale copy here cannot start
 * an invalid run. It exists so the console can ask BEFORE submitting rather than
 * opening a progress console and immediately replacing it with an error.
 */
export const FULL_AUDIT_IDENTITY_FIELDS: Record<LeadType, Array<keyof FullAuditIdentity>> = {
  technical_seo: [],
  onpage_seo: [],
  // Its backend declares country and state required, and a lead row has no
  // geography — the funnel never asks a prospect for one.
  ai_seo: ["country", "state"],
};

export async function startFullAudit(
  leadId: string,
  identity: FullAuditIdentity = {},
): Promise<FullAuditStart> {
  const { data } = await api.post<FullAuditStart>(
    `/leads/${encodeURIComponent(leadId)}/full-audit`,
    identity,
  );
  return data;
}

export async function pollFullAudit(leadId: string): Promise<FullAuditProgress> {
  const { data } = await api.get<FullAuditProgress>(
    `/leads/${encodeURIComponent(leadId)}/full-audit`,
  );
  return data;
}
