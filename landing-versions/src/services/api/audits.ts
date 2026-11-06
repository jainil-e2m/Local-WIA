import { createApi } from "./axios.config";

/**
 * Audit runs. Every product is called through the dashboard's same-origin
 * backend-for-frontend, which holds their private bearer tokens server-side —
 * no audit URL or token is visible to the browser. Where a service serves the
 * shared contract under its own path prefix, the BFF adds it (see the
 * `basePath` field on AUDIT_SERVICES in server/index.mjs).
 *
 *   POST /audits                    { seed_urls: [url], business_name } → { audit_id }
 *   GET  /audits/:auditId/progress  text/event-stream, one JSON message per
 *                                   update: { percent, stage, done }
 *
 * Every service now serves the progress stream, On-Page included. It stays
 * advisory on all of them: a stream may end before its run does — On-Page caps
 * one stream's lifetime and refuses past a concurrency bound, and any hop in
 * between can drop a long-lived connection — so `GET /audits/:auditId` remains
 * the source of truth and the 8-second status poll remains the fallback. Losing
 * the stream costs update latency, never correctness, and is not something the
 * progress copy reports (see inFlightStage in useAuditRun).
 */
export type AuditType = "technical" | "ai" | "on-page" | "ai-presence";

const TECHNICAL_SEO_BFF_BASE_URL = "/api/technical-seo";
const AI_SEO_BFF_BASE_URL = "/api/ai-seo";
const AI_PRESENCE_BFF_BASE_URL = "/api/ai-presence";
const ON_PAGE_SEO_BFF_BASE_URL = "/api/on-page-seo";

const AUDIT_BASE_URLS: Record<AuditType, string> = {
  technical: TECHNICAL_SEO_BFF_BASE_URL,
  ai: AI_SEO_BFF_BASE_URL,
  "on-page": ON_PAGE_SEO_BFF_BASE_URL,
  "ai-presence": AI_PRESENCE_BFF_BASE_URL,
};

const AUDIT_VARIABLES: Record<AuditType, string> = {
  technical: "TECHNICAL_SEO_AUDIT_URL / TECHNICAL_SEO_API_AUTH_TOKEN",
  ai: "AI_SEO_AUDIT_URL / AI_SEO_API_AUTH_TOKEN",
  "on-page": "ON_PAGE_SEO_AUDIT_URL / ON_PAGE_SEO_API_AUTH_TOKEN",
  "ai-presence": "AI_PRESENCE_AUDIT_URL / AI_PRESENCE_API_AUTH_TOKEN",
};

/** Audit products the History page can list. Extend as products go live. */
export const LISTABLE_AUDIT_TYPES: AuditType[] = ["technical", "ai", "ai-presence", "on-page"];

const auditApis = {
  technical: createApi(AUDIT_BASE_URLS.technical),
  ai: createApi(AUDIT_BASE_URLS.ai),
  "on-page": createApi(AUDIT_BASE_URLS["on-page"]),
  "ai-presence": createApi(AUDIT_BASE_URLS["ai-presence"]),
};

function configuredAudit(type: AuditType) {
  const baseUrl = AUDIT_BASE_URLS[type];
  if (!baseUrl) {
    throw new Error(`${AUDIT_VARIABLES[type]} is not configured.`);
  }
  return { api: auditApis[type], baseUrl };
}

export interface AuditSocialProfile {
  platform?: string;
  url: string;
}

export interface AuditCompetitor {
  brandName: string;
  domainUrl: string;
}

export interface AuditRunRequest {
  businessName: string;
  businessUrl: string;
  /**
   * Business identity, collected by AI SEO and AI Presence. Country and state are
   * required by both. City is optional for AI SEO and required by AI Presence,
   * which builds every assistant prompt around "city, state, country".
   */
  country?: string;
  state?: string;
  city?: string;
  businessType?: string;
  socialProfiles?: AuditSocialProfile[];
  /** AI Presence only — the assistants to query (`llm_eval_targets`). */
  aiAssistants?: string[];
  /** AI Presence only — seeds the generated query set. */
  targetKeywords?: string[];
  /** AI Presence only — brands to compare against. */
  competitors?: AuditCompetitor[];
  /**
   * AI Presence only. Each real-estate platform is its own top-level key on that
   * API rather than a list entry, so this maps payload key → profile URL.
   */
  realEstateProfiles?: Record<string, string>;
}

/**
 * Audit products whose intake accepts the business-identity fields. Technical SEO
 * takes only `seed_urls` + `business_name`, so the extra keys are withheld from it
 * rather than sent and ignored.
 */
const IDENTITY_AWARE_AUDIT_TYPES = new Set<AuditType>(["ai"]);

/**
 * AI Presence rejects a submission whose toggles do not enable AI visibility, and
 * it is the only pillar that product has — so the form never asks, it just sends.
 */
const AI_VISIBILITY_TOGGLE = "aiVisibility";

export interface AuditRunResponse {
  auditId: string;
}

/** Shape of each SSE `message` payload on the progress stream. */
export interface AuditProgressEvent {
  percent: number;
  stage: string;
  done?: boolean;
  /** Backend terminal state, present for every event emitted by the current API. */
  status?: AuditBackendStatus;
  /** AI Presence: its own untranslated status, since `status` is lossy for it. */
  backend_status?: string;
  /** AI Presence: the run is parked waiting for its query set to be confirmed. */
  awaiting_review?: boolean;
  failure_reason?: string | null;
}

export type AuditBackendStatus =
  "queued" | "running" | "completed" | "completed_partial" | "failed" | "cancelled" | "interrupted";

export const TERMINAL_AUDIT_STATUSES = new Set<AuditBackendStatus>([
  "completed",
  "completed_partial",
  "failed",
  "cancelled",
  "interrupted",
]);

/**
 * The AI Presence intake is a different shape, not an extension of the others: it
 * takes a singular `domain` instead of a `seed_urls` array and camelCase aliases
 * instead of `business_name`, so it is built rather than patched.
 */
function aiPresenceBody(payload: AuditRunRequest): Record<string, unknown> {
  const body: Record<string, unknown> = {
    businessName: payload.businessName,
    domain: payload.businessUrl,
    country: payload.country,
    state: payload.state,
    city: payload.city,
    businessType: payload.businessType,
    toggles: [AI_VISIBILITY_TOGGLE],
    // Sent explicitly even though the form defaults to every assistant: an empty
    // list means "all targets" to the backend, so an omitted value would run a
    // wider audit than the request appears to describe.
    llm_eval_targets: payload.aiAssistants ?? [],
  };

  const keywords = (payload.targetKeywords ?? []).map((value) => value.trim()).filter(Boolean);
  if (keywords.length) body.queries = keywords;

  const competitors = payload.competitors ?? [];
  if (competitors.length) body.competitors = competitors;

  const profiles = (payload.socialProfiles ?? []).filter((profile) => profile.url.trim());
  if (profiles.length) {
    body.socialProfiles = profiles;
    // The API also carries the YouTube channel as its own top-level field. It is
    // accepted and persisted with the submission; no pipeline stage reads it yet,
    // so this mirrors the intake contract rather than driving behaviour.
    const youtube = profiles.find((profile) => profile.platform === "youtube");
    if (youtube) body.youtubeAccountUrl = youtube.url.trim();
  }

  // Same story as youtubeAccountUrl: `zillowProfileUrl`, `realtorProfileUrl` and
  // `homeLightProfileUrl` are validated and stored at intake but not yet consumed.
  for (const [key, value] of Object.entries(payload.realEstateProfiles ?? {})) {
    if (value.trim()) body[key] = value.trim();
  }

  return body;
}

function auditBody(type: AuditType, payload: AuditRunRequest): Record<string, unknown> {
  if (type === "ai-presence") return aiPresenceBody(payload);

  const body: Record<string, unknown> = {
    seed_urls: [payload.businessUrl],
    business_name: payload.businessName,
  };

  if (IDENTITY_AWARE_AUDIT_TYPES.has(type)) {
    body.country = payload.country;
    body.state = payload.state;
    // Omit rather than send "" — the backend treats an absent city as "no city
    // known" and drops it from the Knowledge Graph query, whereas a blank string
    // would have to be padded and could skew that lookup.
    if (payload.city?.trim()) body.city = payload.city.trim();
    if (payload.businessType?.trim()) body.businessType = payload.businessType.trim();
    const profiles = (payload.socialProfiles ?? []).filter((profile) => profile.url.trim());
    if (profiles.length) body.socialProfiles = profiles;
  }

  return body;
}

/**
 * Submitting is the one audit call that can legitimately outlast the shared 10s
 * client timeout.
 *
 * On-Page probes the site for its canonical origin before it will accept a run —
 * it decides which host the crawl is pinned to, so it happens on the request
 * rather than in a worker, and a slow or redirecting site can hold it well past
 * ten seconds. Timing out here would report "Unable to start audit" for a run
 * that is about to start perfectly happily, and the retry would then bill a
 * second one. Every other audit call keeps the default.
 */
const SUBMIT_TIMEOUT_MS = 180_000;

export async function startAudit(
  type: AuditType,
  payload: AuditRunRequest,
): Promise<AuditRunResponse> {
  const { api } = configuredAudit(type);
  const { data } = await api.post<{ audit_id: string }>("/audits", auditBody(type, payload), {
    timeout: SUBMIT_TIMEOUT_MS,
  });
  return { auditId: data.audit_id };
}

/** Open the SSE progress stream for a run. The caller owns closing it. */
export function openAuditProgress(type: AuditType, auditId: string): EventSource {
  const { baseUrl } = configuredAudit(type);
  return new EventSource(`${baseUrl}/audits/${encodeURIComponent(auditId)}/progress`);
}

/**
 * AI Presence keeps its own status vocabulary on `status` — its standalone SPA
 * matches on the raw values — and reports the dashboard's spelling alongside it.
 * Preferring that field is what stops `complete` (its terminal value) from being
 * read as still-running against TERMINAL_AUDIT_STATUSES, which expects
 * `completed`. Services that already speak this vocabulary omit it entirely.
 *
 * The raw value is moved to `backend_status` rather than dropped. The mapping is
 * lossy where it matters most: `pending_user_review` becomes `running`, which is
 * right for a progress bar and useless for deciding whether to show the query
 * review gate. Callers that need that distinction read `backend_status`.
 */
function resolveStatus<T extends { status?: string; dashboard_status?: string }>(
  row: T,
): T & { backend_status?: string } {
  if (!row.dashboard_status) return row;
  return { ...row, backend_status: row.status, status: row.dashboard_status };
}

/** One row from GET /audits (the History list). Extra backend fields ignored. */
export interface AuditSummary {
  audit_id: string;
  status: AuditBackendStatus | string;
  /** Present only on services whose own vocabulary differs — see resolveStatus. */
  dashboard_status?: string;
  /** The service's own status, preserved when `status` was translated. */
  backend_status?: string;
  /** AI Presence: the run is parked waiting for its query set to be confirmed. */
  awaiting_review?: boolean;
  /**
   * AI Presence: the run produced a report worth rendering. True from the moment
   * the run is finalized, which is before its PDF job has run — so a row can
   * carry this with no `client_pdf_download_url` yet.
   */
  report_ready?: boolean;
  seed_urls: string[];
  business_name?: string | null;
  failure_reason?: string | null;
  submitted_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  progress_percent?: number;
  progress_stage?: string;
  progress_updated_at?: string | null;
  /** Google Drive PDF download URL — present once the report is uploaded. */
  client_pdf_download_url?: string | null;
}

/** Subset of GET /audits/:auditId used to finalize a row once its run ends. */
export interface AuditStatusDetail {
  audit_id: string;
  /** AI Presence: the audited domain, for a run reopened by id alone. */
  domain?: string | null;
  status: AuditBackendStatus | string;
  /** Present only on services whose own vocabulary differs — see resolveStatus. */
  dashboard_status?: string;
  /** The service's own status, preserved when `status` was translated. */
  backend_status?: string;
  /** AI Presence: the run is parked waiting for its query set to be confirmed. */
  awaiting_review?: boolean;
  business_name?: string | null;
  failure_reason?: string | null;
  errors?: Record<string, number>;
  timings?: Record<string, number>;
  submitted_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  progress_percent?: number;
  progress_stage?: string;
  progress_updated_at?: string | null;
  stages?: Record<string, string>;
  checks?: Record<string, string>;
  config?: Record<string, unknown>;
  /** The run produced a report worth rendering. AI Presence reports this. */
  report_ready?: boolean;
  /**
   * Both services report the client PDF at the top level; Technical SEO also
   * nests it under `outputs`, and AI Presence mirrors that placement.
   */
  client_pdf_download_url?: string | null;
  outputs?: {
    json?: string | null;
    md?: string | null;
    html?: string | null;
    client_pdf_download_url?: string | null;
  } | null;
}

/**
 * The client PDF link for a run, wherever the service put it.
 *
 * Technical SEO nests it under `outputs` on the detail and hoists it to the top
 * level on list rows; AI Presence sends both. Reading one place would work for
 * one shape and silently hide the download for the other.
 */
export function clientPdfDownloadUrl(
  source: Pick<AuditStatusDetail, "client_pdf_download_url" | "outputs"> | null | undefined,
): string | undefined {
  return source?.outputs?.client_pdf_download_url ?? source?.client_pdf_download_url ?? undefined;
}

/**
 * List every audit (backend returns newest-first) for the History page.
 *
 * The two envelopes are a real difference, not defensive coding: Technical SEO
 * and AI SEO answer `{ audits: [...] }`, while AI Presence paginates and answers
 * `{ items: [...], pagination: {...} }`. Reading only one of them drops that
 * product's runs silently — an empty array is indistinguishable from "no audits
 * yet", so the History page would look healthy while listing nothing.
 */
export async function listAudits(type: AuditType = "technical"): Promise<AuditSummary[]> {
  const { api } = configuredAudit(type);
  const { data } = await api.get<{ audits?: AuditSummary[]; items?: AuditSummary[] }>("/audits");
  return (data.audits ?? data.items ?? []).map(resolveStatus);
}

/** DB-synced status for one audit — used to finalize a row when its SSE ends. */
export async function getAuditStatus(type: AuditType, auditId: string): Promise<AuditStatusDetail> {
  const { api } = configuredAudit(type);
  const { data } = await api.get<AuditStatusDetail>(`/audits/${encodeURIComponent(auditId)}`);
  return resolveStatus(data);
}

/** Same-origin/proxied URL for one persisted final report. */
export function getAuditReportUrl(
  type: AuditType,
  auditId: string,
  format: "html" | "json" | "md" = "html",
): string {
  const { baseUrl } = configuredAudit(type);
  return `${baseUrl}/audits/${encodeURIComponent(auditId)}/report?format=${format}`;
}
