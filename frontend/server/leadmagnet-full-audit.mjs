/**
 * Full audits started from the Lead Magnet console's "Run full audit" button.
 *
 * WHAT THIS REPLACES
 * The button used to call the Lead Magnet backend (`/api/lead-magnet`) for every
 * lead whatever its funnel, and print "Technical SEO snapshot" while doing it.
 * That deployment runs FULL_AUDIT_ENABLED=false — it is the ~50 second snapshot a
 * prospect gets for free, not the deep run the operator is asking for. So an
 * On-Page lead was labelled "On-Page SEO" over a Technical SEO lead-magnet run,
 * and no lead ever got a full audit at all.
 *
 * This routes each lead to its OWN product's full-audit service instead.
 *
 * WHY THE START LIVES ON THE SERVER RATHER THAN IN THE BROWSER
 * A browser-driven start would be two calls — launch the audit, then write the
 * id back — and anything that fails between them leaves a live run on a paid
 * backend that nothing references and nobody can find. Starting and recording in
 * one request makes that unrepresentable.
 *
 * (This argument was originally written around a role split: the leads store was
 * `requireSession + requireRole("team")` while the audit proxies were session-only,
 * so a `client` could start a run and then take a 403 recording it. That gate was
 * deliberately removed — the console is open to every signed-in account — so the
 * 403 half no longer applies. The crash/abort half still does.)
 *
 * WHY TWO PRODUCTS NEED NO INTAKE FORM AND ONE DOES
 * Technical SEO and On-Page accept `{ seed_urls: [url] }` and nothing else is
 * required — see INTAKE_PROFILES in src/data/auditIntake.ts, which already
 * declares `identity: false` for both because "their API accepts a site URL and
 * a client name and has nowhere to put the rest". A lead row is therefore
 * already a superset of their payload, and their runs start from the row alone.
 *
 * AI SEO is the one product where that stops being true — it is the only member
 * of IDENTITY_AWARE_AUDIT_TYPES — so its registry entry declares the identity
 * fields it needs and the console collects them from the operator first. See the
 * note on `requiredIdentity` below for why they are asked for rather than
 * defaulted.
 */

/** Shared status vocabulary, matching TERMINAL_AUDIT_STATUSES in services/api/audits.ts. */
export const TERMINAL_FULL_AUDIT_STATUSES = new Set([
  "completed",
  "completed_partial",
  "failed",
  "cancelled",
  "interrupted",
]);

/**
 * A run older than this is written off as stalled.
 *
 * Deliberately generous: Technical SEO's RQ job_timeout is 86400s, so a run that
 * is merely slow must not be declared dead. This exists for the case the age
 * cutoff is really for — On-Page runs sit at `queued` FOREVER when the
 * control-plane relay is not running, and without a cutoff such a lead would
 * hold its duplicate-run guard closed permanently.
 */
export const FULL_AUDIT_MAX_AGE_MS = 24 * 60 * 60 * 1000;

/**
 * lead.product -> the full-audit service that serves it.
 *
 * `serviceId` indexes AUDIT_SERVICES in index.mjs, so each entry inherits that
 * service's URL, bearer token and basePath — this file never learns a token.
 * Paths here are written WITHOUT the version prefix for the same reason: On-Page
 * carries `basePath: "/v1"` and Technical SEO carries none, and duplicating that
 * knowledge is how the two drift apart.
 *
 * `toolId` indexes src/data/tools.ts. It is what lets the console link a finished
 * run at /automations/<toolId>?run=<auditId>, where the existing AuditPanel
 * resumes it — which is why nothing here fetches or parses a report. Those are
 * ~2MB documents and the lead store is explicitly designed never to hold one.
 */
export const FULL_AUDIT_PRODUCTS = {
  technical_seo: {
    serviceId: "technical-seo",
    toolId: "technical-seo",
    label: "Technical SEO",
    submitPath: "/audits",
    statusPath: (auditId) => `/audits/${encodeURIComponent(auditId)}`,
    requiredIdentity: [],
    optionalIdentity: [],
  },
  onpage_seo: {
    serviceId: "on-page-seo",
    toolId: "on-page-seo",
    label: "On-Page SEO",
    // The dashboard-shaped alias: POST /v1/audits accepts { seed_urls,
    // business_name } and translates it to this service's native request body.
    // Unknown keys are ignored by design, so one body shape serves both products.
    submitPath: "/audits",
    statusPath: (auditId) => `/audits/${encodeURIComponent(auditId)}`,
    requiredIdentity: [],
    optionalIdentity: [],
  },
  ai_seo: {
    serviceId: "ai-seo",
    toolId: "ai-seo",
    label: "AI Crawlability Readiness Checker",
    submitPath: "/audits",
    statusPath: (auditId) => `/audits/${encodeURIComponent(auditId)}`,
    /* The reason this product could not simply be added alongside the other two.
       Its dashboard alias declares country and state as Field(..., min_length=1)
       with a require_non_blank validator on top, and a lead row has no geography
       at all — the funnel collects businessName, domainUrl, email and phone and
       nothing else. So the console asks an operator for them before it will
       start a run.

       WHY NOT JUST DEFAULT THEM SERVER-SIDE. Because a plausible wrong value is
       worse than an absent one, and the backend measured it. From its own
       identity.py: "Redfin Seattle Washington broker" resolves to Redfin, while
       "Redfin Unknown Unknown unknown" resolves to Ballston Lake — a different
       company. Padding turns a missing-data case into a confidently wrong
       finding on a high-severity check, which is worse than refusing to start. */
    requiredIdentity: ["country", "state"],
    /* businessName is here rather than in requiredIdentity because the lead row
       always carries SOMETHING usable as a fallback — it is an override, not a
       missing value. It is offered for correction because for this product alone
       it is load-bearing: business_name is the primary Knowledge Graph query
       term, while the funnel field feeding it is labelled "Name*" and is as
       often a contact's name as a company's. "Jainil" and "Wahha Design" resolve
       to very different entities.

       city and businessType are genuinely optional: absent, they are padded
       backend-side and then stripped again by clean_identity_value before any
       check reads them, so omitting them costs precision on the Knowledge Graph
       lookup and nothing else. */
    optionalIdentity: ["businessName", "city", "businessType"],
  },
};

/**
 * Identity field -> the key the dashboard contract actually reads.
 *
 * Mostly identical, and `businessType` is carried because DashboardAuditRequest
 * declares `business_type` with `alias="businessType"`. `business_name` has NO
 * such alias, so sending the camelCase form would be accepted and then silently
 * ignored — the run would proceed with the wrong name and nothing would report a
 * problem. That is the whole reason this map exists rather than passing the
 * field names straight through.
 */
const IDENTITY_WIRE_KEYS = {
  country: "country",
  state: "state",
  city: "city",
  businessType: "businessType",
  businessName: "business_name",
};

/** Required identity fields this product has not been given. */
export function missingIdentityFields(product, identity) {
  return (product?.requiredIdentity ?? []).filter(
    (field) => !String(identity?.[field] ?? "").trim(),
  );
}

/**
 * The seed URL for a lead, or null when it has none.
 *
 * A scheme is REQUIRED rather than assumed. Technical SEO answers 202 to a
 * scheme-less host and only discovers the problem inside the worker, so guessing
 * here would spend a real job slot to produce a failure several minutes later.
 * Rejecting up front turns that into an immediate 422.
 *
 * domain_url is stored absolute by the store's own normalizeUrl, so this is a
 * re-assertion at the trust boundary rather than a second normalisation: rows
 * predating that guarantee, or written by another consumer, still reach here.
 */
export function seedUrlForLead(lead) {
  const raw = typeof lead?.domainUrl === "string" ? lead.domainUrl.trim() : "";
  if (!raw) return null;
  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    return null;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
  if (!parsed.hostname) return null;
  return parsed.toString();
}

/**
 * The status a run is in, in the shared vocabulary.
 *
 * On-Page reports its own 14-value vocabulary in `status` and the shared one in
 * `dashboard_status`; Technical SEO emits the shared vocabulary natively and
 * sends no `dashboard_status`. Preferring the translation when present is the
 * same rule resolveStatus() applies in services/api/audits.ts — kept identical
 * on purpose, because a lead row and the tool page disagreeing about whether a
 * run finished is a bug with no good failure mode.
 */
export function readUpstreamStatus(payload, warn) {
  const dashboard = payload?.dashboard_status;
  const raw = typeof dashboard === "string" && dashboard.trim() ? dashboard : payload?.status;
  // Normalized here rather than at each call site so the status route and the
  // summary webhook cannot drift apart again — that divergence IS this bug.
  return normalizeAuditStatus(raw, warn) || "queued";
}

/**
 * Foreign status words → the shared vocabulary.
 *
 * Every audit backend names its own states, and the dashboard has exactly five
 * terminal ones. The mismatch is not hypothetical: the AI SEO service reports
 * `completed` on its dashboard alias but `complete` on its native API, and the
 * funnel pushes the native word. One letter meant `isTerminalStatus` said false
 * forever, every AI SEO lead read as "a full audit is already running", and the
 * start route attached to a funnel run instead of submitting a real one — so no
 * AI SEO full audit was ever created, silently, for weeks.
 *
 * Aliases are deliberately conservative: only words whose meaning is
 * unambiguous. Anything unrecognised passes through untouched AND is reported by
 * normalizeAuditStatus, because the failure mode this map exists to prevent was
 * invisible precisely because nothing ever said "I don't know this word".
 */
export const AUDIT_STATUS_ALIASES = new Map([
  ["complete", "completed"],
  ["success", "completed"],
  ["succeeded", "completed"],
  ["completed_with_errors", "completed_partial"],
  ["coverage_limited", "completed_partial"],
  ["partial", "completed_partial"],
  ["error", "failed"],
  ["errored", "failed"],
  ["failure", "failed"],
  ["canceled", "cancelled"],
  ["timeout", "interrupted"],
  ["timed_out", "interrupted"],
  ["in_progress", "running"],
  ["processing", "running"],
  ["pending", "queued"],
]);

/** Words this dashboard understands — the aliases' targets plus the two live ones. */
const KNOWN_AUDIT_STATUSES = new Set([
  "queued",
  "running",
  "completed",
  "completed_partial",
  "failed",
  "cancelled",
  "interrupted",
]);

/**
 * Normalize one status word into the shared vocabulary.
 *
 * Returns "" for an absent value rather than guessing, because the callers mean
 * different things by absence and none of them should be handed a default: the
 * status route substitutes "queued", while the summary webhook must leave the
 * stored status alone.
 *
 * @param {unknown} raw
 * @param {(message: string) => void} [warn] reporter for an unrecognised word
 */
export function normalizeAuditStatus(raw, warn) {
  const value = typeof raw === "string" ? raw.trim().toLowerCase() : "";
  if (!value) return "";
  const mapped = AUDIT_STATUS_ALIASES.get(value) ?? value;
  if (!KNOWN_AUDIT_STATUSES.has(mapped) && typeof warn === "function") {
    warn(
      `unrecognised audit status "${raw}" — treated as non-terminal. Add it to ` +
        "AUDIT_STATUS_ALIASES in leadmagnet-full-audit.mjs if it means a run has ended.",
    );
  }
  return mapped;
}

/** Did this run end, whatever the outcome? */
export function isTerminalStatus(status) {
  return TERMINAL_FULL_AUDIT_STATUSES.has(status);
}

/**
 * Did this run end WELL?
 *
 * `completed_partial` counts as success: a partial run produced a report worth
 * reading, and On-Page reports partial on essentially every run (see the note in
 * AuditPanel.tsx). Treating it as failure would mark almost every On-Page audit
 * broken.
 */
export function isSuccessStatus(status) {
  return status === "completed" || status === "completed_partial";
}

/**
 * The finished run's client-PDF URL, or "" when the service supplied none.
 *
 * Two placements because the services differ: Technical SEO reports it at the
 * top level and also nests it under `outputs`, and AI SEO mirrors that. Same
 * precedence as clientPdfDownloadUrl() in services/api/audits.ts.
 *
 * VALIDATED, not just read. This value comes from an upstream service and is
 * rendered straight into an href in the console, so it is held to the same
 * boundary the store applies to domainUrl and the meeting URL: absolute http(s)
 * only, so nothing can put a `javascript:` URL behind a button an operator
 * clicks. An unusable value degrades to no button rather than a broken link.
 */
export function readReportUrl(payload) {
  const raw =
    payload?.outputs?.client_pdf_download_url ?? payload?.client_pdf_download_url ?? "";
  const text = typeof raw === "string" ? raw.trim() : "";
  if (!text) return "";
  try {
    const parsed = new URL(text);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return "";
    return parsed.toString();
  } catch {
    // Relative or malformed. No product currently sends one, and guessing an
    // origin for it would produce a link to the dashboard itself.
    return "";
  }
}

/**
 * The submit body.
 *
 * `seed_urls` + `business_name` is the whole payload for Technical SEO and
 * On-Page. AI SEO additionally carries the identity fields its registry entry
 * declares, and ONLY those — the identity keys are never sent to a product that
 * did not ask for them, which is the same reason audits.ts gates them behind
 * IDENTITY_AWARE_AUDIT_TYPES rather than sending them everywhere and letting
 * each backend ignore what it does not use.
 *
 * `business_name` is optional everywhere, so a lead with an unusable name still
 * starts a run rather than 422-ing. Note it does NOT mean the same thing to
 * every product: for the other two it seeds the client PDF's cover, but for AI
 * SEO it is the primary Knowledge Graph query term.
 *
 * An empty identity value is OMITTED rather than sent blank. The backend treats
 * an absent field as "not known" and drops it from the provider query, whereas a
 * blank string would have to be padded — and padding is what produces the wrong
 * entity (see the note on requiredIdentity above).
 */
export function fullAuditSubmitBody(lead, seedUrl, product, identity) {
  const body = { seed_urls: [seedUrl] };

  // The lead's own name is the default. An operator correction supplied through
  // `identity.businessName` overwrites it below, via the same loop as every
  // other identity field — so a product that does not declare businessName can
  // never have its name overridden by a stray key in the request body.
  const name = typeof lead?.name === "string" ? lead.name.trim() : "";
  if (name) body.business_name = name.slice(0, 200);

  const fields = [
    ...(product?.requiredIdentity ?? []),
    ...(product?.optionalIdentity ?? []),
  ];
  for (const field of fields) {
    const wireKey = IDENTITY_WIRE_KEYS[field];
    if (!wireKey) continue;
    const value = String(identity?.[field] ?? "").trim();
    if (value) body[wireKey] = value.slice(0, 200);
  }
  return body;
}

/**
 * Is this lead's run still in flight, and therefore not restartable?
 *
 * Guards against a double click and against two operators on the same row.
 *
 * There is deliberately no age check here, and so no need for a
 * `full_audit_started_at` column: staleness is the TICK's job, because only the
 * tick has the run's real timestamps (the lead row records when a run finished,
 * never when it began). The tick writes `interrupted` once a run passes
 * FULL_AUDIT_MAX_AGE_MS, and that terminal status is what reopens this guard.
 */
export function hasRunInFlight(lead) {
  if (!lead?.auditId) return false;
  /* PROVENANCE FIRST, and it is the load-bearing check.
     An audit id alone proves nothing about a FULL run: the summary webhook
     writes one for the funnel's own quick audit, on a deployment this dashboard
     cannot even reach. Only the start route stamps fullAuditStartedAt, so a lead
     without it has no full run to be in flight — whatever its status says. */
  if (!lead.fullAuditStartedAt) return false;
  const status = normalizeAuditStatus(lead.auditStatus);
  // No recorded status means the id was written by an older code path that did
  // not track one. Treat it as finished rather than blocking the button forever.
  if (!status) return false;
  return !isTerminalStatus(status);
}

/**
 * Has an unfinished run been going long enough to write off?
 *
 * Reads the upstream's own timestamps rather than anything stored here. Falls
 * back to "no" when neither is present or parseable, so a service that omits
 * them can never have its runs killed on a guess.
 */
export function isStaleRun(statusPayload, { now = Date.now() } = {}) {
  const started =
    Date.parse(statusPayload?.started_at ?? "") ||
    Date.parse(statusPayload?.submitted_at ?? "");
  if (!Number.isFinite(started) || started <= 0) return false;
  return now - started > FULL_AUDIT_MAX_AGE_MS;
}
