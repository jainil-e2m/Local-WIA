/* ────────────────────────────────────────────────────────────────
   The Content Atelier's launch link.

   The Atelier is its own app. Command Center reaches it through the
   server's single sign-on hand-off (server/atelier-sso.mjs): a full-page
   navigation to ATELIER_LAUNCH_PATH signs the current session in and lands
   on the configured Atelier URL. Every entry that opens the Atelier goes
   through here, and is disabled or hidden wherever VITE_CONTENT_ATELIER_URL
   is unset or not an http(s) URL, where the server would answer 503.
   ──────────────────────────────────────────────────────────────── */

/** A server route, not an app route: link to it with a plain `<a href>` (or
    `window.location`), never the router. */
export const ATELIER_LAUNCH_PATH = "/api/auth/content-atelier/launch";

/** Tooltip for an Atelier entry that cannot launch in this environment. */
export const ATELIER_UNAVAILABLE = "Content Atelier is in development";

/** The deployed Atelier URL, or undefined when VITE_CONTENT_ATELIER_URL is
    blank or not an http(s) URL. Read per call rather than at import, so a
    test's stubbed env is seen. */
export function deployedAtelierUrl(): string | undefined {
  try {
    const url = new URL(import.meta.env.VITE_CONTENT_ATELIER_URL?.trim() ?? "");
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

/** The launch link where the Atelier is configured, otherwise undefined. */
export function atelierLaunchHref(): string | undefined {
  return deployedAtelierUrl() ? ATELIER_LAUNCH_PATH : undefined;
}
