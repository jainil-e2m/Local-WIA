/**
 * Lead Magnet Technical SEO audit client.
 *
 * Separate from audits.ts on purpose. That module submits `{seed_urls,
 * business_name}` — a *Full* audit — and the Lead Magnet deployment runs with
 * FULL_AUDIT_ENABLED=false, so it answers 422 to exactly that shape. Widening
 * audits.ts's AuditType union instead would have pulled this into
 * LISTABLE_AUDIT_TYPES, the History page and the tool registry, none of which
 * should list a lead-capture audit.
 *
 * Requests go through the dashboard's own session-gated /api/lead-magnet proxy
 * (AUDIT_SERVICES in server/index.mjs), never to the audit API directly.
 */

const BASE_URL = '/api/lead-magnet';

export type LeadMagnetSeverity = 'critical' | 'warning' | 'opportunity' | 'info' | 'pass';

export const TERMINAL_STATUSES = new Set([
  'completed',
  'completed_partial',
  'failed',
  'cancelled',
  'interrupted',
]);

export interface LeadMagnetStatus {
  audit_id: string;
  status: string;
  progress_percent?: number;
  progress_stage?: string;
  failure_reason?: string | null;
  queued_beyond_capacity?: boolean;
  estimated_wait_seconds?: number | null;
}

export interface LeadMagnetReport {
  audit: {
    audit_id: string;
    business_name: string | null;
    normalized_target: string;
    terminal_status: string;
    finished_at: string;
    worker_runtime_seconds: number | null;
  };
  checks: { check_id: number; display_order: number; name: string; finding_ids: string[] }[];
  findings: { finding_id: string; severity: LeadMagnetSeverity }[];
  /** Keyed by engine check id. The only place that separates a check which ran
   *  and raised notes from one the bounded sample could not evaluate. */
  coverage?: { per_check?: Record<string, { selected_url_count?: number; degraded?: unknown[] }> };
}

export interface LeadMagnetCounts {
  critical: number;
  warning: number;
  opportunity: number;
  info: number;
  pass: number;
}

export class LeadMagnetAuditError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = 'LeadMagnetAuditError';
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
  });
  const text = await response.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    throw new LeadMagnetAuditError('bad_response', 'The audit service returned an unreadable response.');
  }
  if (!response.ok) {
    const detail = body as { message?: string; error?: string; detail?: string };
    throw new LeadMagnetAuditError(
      detail.error || 'request_failed',
      detail.message || detail.detail || detail.error || `Audit request failed (${response.status}).`,
    );
  }
  return body as T;
}

/** `audit_type` is what distinguishes this from a Full submission. Without it
 *  the Lead-only deployment refuses the request with 422. */
export const startLeadMagnetAudit = (input: { businessName?: string; domainUrl: string }) =>
  request<{ audit_id: string }>('/audits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      seed_urls: [input.domainUrl],
      audit_type: 'lead_magnet',
      ...(input.businessName ? { business_name: input.businessName } : {}),
    }),
  });

export const getLeadMagnetStatus = (auditId: string) =>
  request<LeadMagnetStatus>(`/audits/${encodeURIComponent(auditId)}`);

export const getLeadMagnetReport = (auditId: string) =>
  request<LeadMagnetReport>(`/audits/${encodeURIComponent(auditId)}/report?format=json`);

/** Standalone HTML rendering, served through the same session-gated proxy. */
export const leadMagnetReportUrl = (auditId: string) =>
  `${BASE_URL}/audits/${encodeURIComponent(auditId)}/report?format=html`;

export function countSeverities(report: LeadMagnetReport): LeadMagnetCounts {
  const counts: LeadMagnetCounts = { critical: 0, warning: 0, opportunity: 0, info: 0, pass: 0 };
  for (const finding of report.findings) {
    if (finding.severity in counts) counts[finding.severity] += 1;
  }
  return counts;
}

/**
 * Same derived score the funnel shows, kept identical here on purpose: one
 * audit must not read as two different grades in two places. If you change the
 * credits or bands, change them in the funnel's utils/audit.ts too.
 *
 * The unit is the check, not the finding: 21 checks, 21 points, so a site that
 * passes everything scores 100. A check's credit is set by its worst finding,
 * ignoring `info`.
 *
 * `not_assessed` earns half. Those checks produced only a coverage disclosure —
 * bounded discovery found no pagination sequence, no PDF, no location page to
 * sample. Scoring that zero would punish a small site for not having a blog;
 * scoring it 1.0 would turn "we could not check this" into free marks.
 */
const CREDIT = {
  passed: 1,
  /** Ran against real pages and raised only info notes. Scores like a pass:
   *  `info` costs nothing elsewhere in this model, so docking a check for
   *  carrying one would contradict that. */
  reviewed: 1,
  opportunity: 0.75,
  warning: 0.4,
  critical: 0,
  not_assessed: 0.5,
} as const;

/** Credit alone is too forgiving at the top: 20 clean checks plus one critical
 *  earns 95, which would print A+ on a site with a critical defect. */
const CRITICAL_SCORE_CAP = 89;

const ISSUE_SEVERITIES: LeadMagnetSeverity[] = ['critical', 'warning', 'opportunity'];

/** Five ten-point bands, plain letters. Keep in step with the funnel's
 *  utils/audit.ts — the same audit must not read as two different grades. */
function gradeFor(score: number): string {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
}

export interface LeadMagnetScore {
  score: number;
  grade: string;
  passedChecks: number;
  totalChecks: number;
  notAssessedChecks: number;
}

export function scoreFor(report: LeadMagnetReport): LeadMagnetScore {
  const byId = new Map(report.findings.map((finding) => [finding.finding_id, finding]));
  let earned = 0;
  let passed = 0;
  let notAssessed = 0;

  for (const check of report.checks) {
    const findings = check.finding_ids
      .map((id) => byId.get(id))
      .filter((finding): finding is LeadMagnetReport['findings'][number] => Boolean(finding));
    const worst = ISSUE_SEVERITIES.find((severity) =>
      findings.some((finding) => finding.severity === severity),
    );
    if (worst) {
      earned += CREDIT[worst as keyof typeof CREDIT];
      continue;
    }
    if (findings.some((finding) => finding.severity === 'pass')) {
      earned += CREDIT.passed;
      passed += 1;
      continue;
    }
    /* No verdict finding. The findings alone cannot say whether the check ran
       and found nothing or never had anything to look at — only the coverage
       manifest marks the latter. */
    const entry = report.coverage?.per_check?.[String(check.check_id)];
    const degraded = Array.isArray(entry?.degraded) ? entry.degraded.length : 0;
    const selected = typeof entry?.selected_url_count === 'number' ? entry.selected_url_count : 0;
    if (degraded > 0 || selected === 0) {
      earned += CREDIT.not_assessed;
      notAssessed += 1;
    } else {
      earned += CREDIT.reviewed;
      passed += 1;
    }
  }

  const total = report.checks.length || 1;
  const raw = Math.max(0, Math.min(100, Math.round((earned / total) * 100)));
  const hasCritical = report.findings.some((finding) => finding.severity === 'critical');
  const score = hasCritical ? Math.min(raw, CRITICAL_SCORE_CAP) : raw;

  return {
    score,
    grade: gradeFor(score),
    passedChecks: passed,
    totalChecks: report.checks.length,
    notAssessedChecks: notAssessed,
  };
}
