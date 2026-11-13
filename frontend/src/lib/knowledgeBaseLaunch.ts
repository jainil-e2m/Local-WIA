/* ────────────────────────────────────────────────────────────────
   The Client Knowledge Base's launch link.

   Like the Content Atelier (lib/atelierLaunch.ts), the Knowledge Base is
   its own app, reached through the server's sign-on hand-off
   (server/atelier-sso.mjs, mounted at /api/auth/knowledge-base): a
   full-page navigation to KNOWLEDGE_BASE_LAUNCH_PATH signs the current
   session in there. Its entry is live only where VITE_KNOWLEDGE_BASE_URL
   is an http(s) URL; elsewhere it stays on the roadmap.
   ──────────────────────────────────────────────────────────────── */

/** A server route, not an app route: link to it with a plain `<a href>`. */
export const KNOWLEDGE_BASE_LAUNCH_PATH = "/api/auth/knowledge-base/launch";

/** The deployed Knowledge Base URL, or undefined when VITE_KNOWLEDGE_BASE_URL is blank or not an http(s) URL.
    Read per call rather than at import, so a test's stubbed env is seen. */
export function deployedKnowledgeBaseUrl(): string | undefined {
  try {
    const url = new URL(import.meta.env.VITE_KNOWLEDGE_BASE_URL?.trim() ?? "");
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
