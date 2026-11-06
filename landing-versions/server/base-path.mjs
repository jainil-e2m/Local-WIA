/* ────────────────────────────────────────────────────────────────
   Optional path prefix for an audit service that does not serve the audit
   contract at its origin root.

   Technical SEO and AI Crawlability expose POST /audits directly. The AI
   Presence Checker mounts its routers under its own API_PREFIX (default
   /api/v1), so the BFF has to rebuild /api/ai-presence/audits as
   /api/v1/audits rather than /audits.

   That prefix cannot simply be appended to the service's URL: the proxy
   resolves an ABSOLUTE suffix against it, and per the URL spec an absolute path
   replaces the base's path entirely —

     new URL("/audits", "https://host/api/v1/")  →  https://host/audits

   — so a configured "https://host/api/v1" would be silently discarded and every
   proxied call would 404 against the service root. Hence a separate field,
   normalized here.

   Extracted from index.mjs so it can be unit-tested: that module calls
   app.listen() at module scope, the same reason upstream-url.mjs is separate.
   ──────────────────────────────────────────────────────────────── */

/**
 * Normalize a path prefix to "" or "/a/b" — leading slash, no trailing one — so
 * it concatenates cleanly with a suffix that always begins with "/".
 *
 * @param {string | undefined | null} value
 * @returns {string}
 */
export function normalizeBasePath(value) {
  const trimmed = (value ?? "").trim();
  if (!trimmed) return "";
  // Collapse any run of slashes at either end, then re-add exactly one leading
  // slash. "//api/v1//" and "api/v1" both have to land on "/api/v1", or the
  // joined URL gets an empty path segment the upstream router will not match.
  const stripped = trimmed.replace(/^\/+/, "").replace(/\/+$/, "");
  return stripped ? `/${stripped}` : "";
}

/**
 * Read a base path from the environment.
 *
 * Deliberately not routed through index.mjs's env() helper, which treats "" as
 * unset: an empty string is meaningful here — it says the service serves the
 * audit contract at its root — and must override the fallback rather than be
 * replaced by it.
 *
 * @param {Record<string, string | undefined>} source  usually process.env
 * @param {string} name
 * @param {string} fallback   used only when the variable is absent entirely
 * @returns {string}
 */
export function readBasePath(source, name, fallback) {
  const raw = source[name];
  return normalizeBasePath(raw === undefined ? fallback : raw);
}
