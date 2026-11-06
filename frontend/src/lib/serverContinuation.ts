/** A server route to continue to after signing in: only the Content Atelier hand-off (server/atelier-sso.mjs), which
 *  sends a signed-out visitor here with `?next=`. Anything else is ignored, so `next` can never redirect off-site. */
export function serverContinuation(search: string): string | null {
  const next = new URLSearchParams(search).get("next");
  if (!next || !/^\/api\/auth\/content-atelier\/(authorize|launch)(\?|$)/.test(next) || /[\\\r\n]/.test(next)) return null;
  return next;
}
