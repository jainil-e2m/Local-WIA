import kb from '@kb-live';
import { VIEWERS } from './data';

/*
 * Who is signed in, and which view they get (backend/routes/auth.py, GET /api/auth/session).
 *
 * The live app is reached through Command Center's sign-in, like the Content Atelier: `user` is the person's own
 * Command Center account. With role-based views off (RBAC_ENABLED=false, this release) everyone sees what
 * `viewAs` (KB_DEFAULT_VIEWER, Whitney) sees, and the account area shows the person who signed in, with no
 * switching. The sample preview, with no KB behind it, keeps the preview-account switcher.
 */

export interface SignedInUser { email: string; name: string; role: 'team' | 'client' }
export const auth: { user: SignedInUser | null; rbac: boolean; viewAs: string } = { user: null, rbac: false, viewAs: 'Whitney' };

/** Once at start (main.tsx), in builds with a KB server behind them. */
export async function loadAuth(): Promise<void> {
  if (!kb.meta || !['portfolio', 'wia'].includes(import.meta.env.MODE)) return;
  const res = await fetch('/api/auth/session', { credentials: 'same-origin' });
  if (res.status === 401) { signInAgain(); return; }
  if (!res.ok) throw new Error(`The KB answered ${res.status}.`);
  const data = await res.json() as { user: SignedInUser | null; rbac: boolean; viewAs: string };
  Object.assign(auth, { user: data.user, rbac: !!data.rbac, viewAs: data.viewAs || 'Whitney' });
}

/** The view a person gets: everyone's shared view while role-based views are off, else their own (by first name). */
export function initialViewer(): string {
  if (!auth.user || !auth.rbac) return auth.viewAs;
  const first = auth.user.name.split(/\s+/)[0]?.toLowerCase();
  return VIEWERS.find(v => v.name.toLowerCase() === first)?.name ?? auth.viewAs;
}

/** Back through Command Center's sign-in to this same page (the session ended or was signed out elsewhere). */
export function signInAgain() {
  const back = window.location.pathname + window.location.search + window.location.hash;
  window.location.assign(`/api/auth/sso/start?returnTo=${encodeURIComponent(back)}`);
}

export const SIGN_OUT_HREF = '/api/auth/signout';

/** The name to sign a change with: the person who signed in (first name, as the team writes names), whatever view
 *  they're in. In the sample preview, the preview account. The server records the full identity anyway. */
export const me = (viewer?: string) => auth.user ? (auth.user.name.split(/\s+/)[0] || auth.user.name) : viewer ?? "";
