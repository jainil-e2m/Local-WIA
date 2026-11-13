/* ────────────────────────────────────────────────────────────────
   Display fallback for the signed-in user.
   The real session lives in src/context/AuthContext.tsx (backed by
   the /api/auth endpoints); this object is the display default used
   on the public landing page and anywhere no session is loaded.
   ──────────────────────────────────────────────────────────────── */

export interface CurrentUser {
  /** Display name shown in the hero greeting and header pill. */
  name: string;
  /** Optional finer label under/next to the name (role, company…). */
  label?: string;
}

export const currentUser: CurrentUser = {
  name: "Wedding Industry Ads",
  label: "Client",
};

/** "Wedding Industry" → "WI", "Sam" → "SA" */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

/**
 * Display form of the account name for the hero greeting and the header pill.
 *
 * This used to return the first word, which is right for a person and wrong
 * for the account this app actually runs under: the seeded name is
 * "Wedding Industry Ads", so the landing page greeted the client as
 * "Good afternoon · Wedding" and the header pill read "Wedding". The whole
 * name is the safe answer for both shapes — a person's full name reads
 * correctly in a greeting too — and the pill truncates on width instead.
 */
export function accountName(name: string): string {
  return name.trim();
}
