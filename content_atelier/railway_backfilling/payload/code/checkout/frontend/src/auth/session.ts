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

export async function getSession(signal?: AbortSignal, fetcher: typeof fetch = fetch): Promise<AuthUser | null> {
  const response = await fetcher('/api/auth/session', { credentials: 'include', cache: 'no-store', signal });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error('Command Center session service is unavailable.');
  return readSessionUser((await response.json()).user);
}

export async function logoutSession(fetcher: typeof fetch = fetch): Promise<void> {
  const response = await fetcher('/api/auth/logout', { method: 'POST', credentials: 'include', cache: 'no-store', signal: AbortSignal.timeout(10_000) });
  if (!response.ok) throw new Error('Could not sign out of Command Center. Try again.');
}

export function userInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts.length >= 2 ? parts[0][0] + parts[1][0] : (parts[0] || '').slice(0, 2)).toUpperCase();
}

export function commandCenterLoginUrl(): string {
  // Production issues the same signed session through the Atelier's own host.
  // A login on another Railway domain cannot set this host's cookie.
  if (!import.meta.env?.DEV) return '/login';
  const base = import.meta.env?.VITE_COMMAND_CENTER_URL || (import.meta.env?.DEV ? 'http://localhost:5173' : '');
  return base ? `${base.replace(/\/+$/, '')}/login` : '/login';
}

export function userGreeting(user: AuthUser | null, now = new Date()): string {
  if (!user) return 'Welcome to Content Atelier';
  const hour = Number(new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Calcutta', hour: '2-digit', hourCycle: 'h23' }).format(now));
  return `Good ${hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening'}, ${user.name}`;
}
