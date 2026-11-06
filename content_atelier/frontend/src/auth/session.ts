/** Same user contract and cookie-backed endpoints as Command Center's services/api/auth.ts. */
export interface AuthUser {
  email: string;
  name: string;
  role: 'team' | 'client';
}

export function readSessionUser(value: unknown): AuthUser {
  const user = value as Partial<AuthUser> | null;
  if (!user || typeof user.email !== 'string' || !user.email.trim() || typeof user.name !== 'string' || !['team', 'client'].includes(user.role!)) throw new Error('Invalid Command Center session response.');
  return { email: user.email, name: user.name.trim() || user.email, role: user.role! };
}

/** How this host signs a person in, as its server says on every session check (server/app.mjs, `X-Atelier-Sign-In`): through
    Command Center's hand-off when its public origin is set, otherwise with this host's own form (6.F8). */
export type SignInRoute = 'command-center' | 'form';
export const signInRouteOf = (response: Pick<Response, 'headers'>): SignInRoute =>
  response.headers.get('x-atelier-sign-in') === 'command-center' ? 'command-center' : 'form';

/** The session, and how to sign in when there is none. */
export async function checkSession(signal?: AbortSignal, fetcher: typeof fetch = fetch): Promise<{ user: AuthUser | null; signIn: SignInRoute }> {
  const response = await fetcher('/api/auth/session', { credentials: 'include', cache: 'no-store', signal });
  const signIn = signInRouteOf(response);
  if (response.status === 401) return { user: null, signIn };
  if (!response.ok) throw new Error('Command Center session service is unavailable.');
  return { user: readSessionUser((await response.json()).user), signIn };
}

export async function getSession(signal?: AbortSignal, fetcher: typeof fetch = fetch): Promise<AuthUser | null> {
  return (await checkSession(signal, fetcher)).user;
}

/** The Node server's sign-out round trip through Command Center (server/app.mjs), so one sign-out clears both apps. */
export const SHARED_SIGNOUT = '/api/auth/signout';

export async function logoutSession(fetcher: typeof fetch = fetch): Promise<void> {
  const response = await fetcher('/api/auth/logout', { method: 'POST', credentials: 'include', cache: 'no-store', signal: AbortSignal.timeout(10_000) });
  if (!response.ok) throw new Error('Could not sign out of Command Center. Try again.');
}

export function userInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts.length >= 2 ? parts[0][0] + parts[1][0] : (parts[0] || '').slice(0, 2)).toUpperCase();
}

/** Where the sign-in link goes. A deep link survives sign-in: the page the person was on is passed as `returnTo`, which the
    server and the sign-in page accept only as a path on this host (server/sso.mjs localReturnTo, server/login.js). With
    Command Center's public origin set the link goes straight to its hand-off, one hop (6.F8); otherwise to this host's form. */
export function commandCenterLoginUrl(returnTo = currentPath(), route: SignInRoute = 'form'): string {
  const target = returnTo && returnTo !== '/' ? `?returnTo=${encodeURIComponent(returnTo)}` : '';
  // Local development signs in on Command Center's own dashboard (another localhost port that shares the cookie); the page
  // rides along there too.
  if (import.meta.env?.DEV) return `${(import.meta.env?.VITE_COMMAND_CENTER_URL || 'http://localhost:5173').replace(/\/+$/, '')}/login${target}`;
  // Production issues the same signed session through the Atelier's own host: a login on another Railway domain cannot set
  // this host's cookie, so both ways in start here.
  return route === 'command-center' ? `/api/auth/sso/start${target}` : `/login${target}`;
}

const currentPath = () => typeof window === 'undefined' ? '/' : window.location.pathname + window.location.search;

export function userGreeting(user: AuthUser | null, now = new Date()): string {
  if (!user) return 'Welcome to Content Atelier';
  // The viewer's own time of day.
  const hour = now.getHours();
  const greeting = `Good ${hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening'}`;
  // The first name, as the 20 October mockup greets the person ("Good morning, Whitney"); the shared company account gets none.
  if (/wedding industry ads/i.test(user.name)) return greeting;
  const first = user.name.trim().split(/\s+/)[0] || user.name;
  return `${greeting}, ${first}`;
}
