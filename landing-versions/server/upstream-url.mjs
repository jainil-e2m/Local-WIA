/* ────────────────────────────────────────────────────────────────
   Which audit-service upstream URLs the BFF is willing to proxy to.

   This is a security boundary, not a formatting check. The dashboard's Express
   process is the only thing holding the audit APIs' bearer tokens; every request
   it forwards carries one. Sending that token over plain http would leak it to
   anything on the network path, so https is required for real hosts —
   unconditionally, with no env var able to turn it off.

   The single exception is local development: an audit backend on
   http://127.0.0.1:8010 has no TLS and no network path to sniff. That exception
   is deliberately narrow and doubly gated:

     1. the host must be a loopback literal (no DNS names, so no rebinding to a
        remote address, and no "localhost.attacker.com" style suffix tricks), and
     2. the process must not be running in production.

   Because it is a separate module it can be unit-tested without importing
   index.mjs, which calls app.listen() at module scope. Its tests are the
   regression guard on the exception staying narrow.
   ──────────────────────────────────────────────────────────────── */

/** Hostnames that cannot leave the machine. `URL.hostname` KEEPS the brackets on
    an IPv6 literal (`new URL("http://[::1]:80").hostname === "[::1]"`), so the
    bracketed form is what has to be listed. Both spellings are included so the
    set stays correct if that ever changes. */
const LOOPBACK_HOSTNAMES = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);

/**
 * True when `value` is a URL this process may forward a bearer token to.
 *
 * @param {string | undefined} value      configured upstream origin
 * @param {object} [options]
 * @param {string} [options.nodeEnv]      defaults to process.env.NODE_ENV
 * @returns {boolean}
 */
export function isAllowedUpstreamUrl(value, { nodeEnv = process.env.NODE_ENV } = {}) {
  if (!value) return false;

  let url;
  try {
    url = new URL(value);
  } catch {
    return false;
  }

  if (url.protocol === "https:") return true;
  if (url.protocol !== "http:") return false;

  // Plain http is a local-development affordance only. Production never gets it,
  // regardless of how the URL is spelled.
  if (nodeEnv === "production") return false;
  return LOOPBACK_HOSTNAMES.has(url.hostname);
}

/** Explanation for logs/errors when a URL is rejected. Keeps the operator from
    guessing why a set variable is reported as "not configured". */
export function describeUpstreamUrlRejection(value, { nodeEnv = process.env.NODE_ENV } = {}) {
  // Delegate the verdict so this function can never disagree with the predicate
  // that actually gates proxying. Returning a reason for a URL that is in fact
  // accepted produced a boot warning saying the BFF was "not usable" while it
  // proxied fine — the exact misleading message this function exists to avoid.
  if (isAllowedUpstreamUrl(value, { nodeEnv })) return null;

  if (!value) return "not set";

  let url;
  try {
    url = new URL(value);
  } catch {
    return "not a valid absolute URL";
  }

  if (url.protocol !== "http:") {
    return `unsupported protocol "${url.protocol}" (expected https:)`;
  }
  if (nodeEnv === "production") {
    return "plain http is refused in production (a bearer token would be sent in clear text)";
  }
  return (
    `plain http is only allowed for a loopback host; "${url.hostname}" is not one of ` +
    `${[...LOOPBACK_HOSTNAMES].join(", ")}`
  );
}
