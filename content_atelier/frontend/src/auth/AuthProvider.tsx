import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { AuthUser, SHARED_SIGNOUT, checkSession, logoutSession, type SignInRoute } from './session';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'error';
export interface AuthState {
  user: AuthUser | null;
  status: AuthStatus;
  error: string;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  /** How to sign in when there is no session: the server says on each check (6.F8). Absent, this host's form. */
  signIn?: SignInRoute;
}
export const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<{ user: AuthUser | null; status: AuthStatus; error: string }>({ user: null, status: 'loading', error: '' });
  const [signIn, setSignIn] = useState<SignInRoute>('form');
  const pending = useRef<AbortController | null>(null);
  const queries = useQueryClient();
  const signingOut = useRef(false);
  const refresh = useCallback(async () => {
    if (signingOut.current) return;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 10_000);
    try {
      const { user, signIn: route } = await checkSession(controller.signal);
      if (pending.current === controller) { setSignIn(route); setSession({ user, status: user ? 'authenticated' : 'unauthenticated', error: '' }); }
    } catch {
      if (pending.current === controller) setSession({ user: null, status: 'error', error: 'Cannot reach the Command Center session service. Check that it is running, then retry.' });
    } finally {
      window.clearTimeout(timeout);
      if (pending.current === controller) pending.current = null;
    }
  }, []);

  useEffect(() => {
    void refresh();
    const recheck = () => { if (document.visibilityState === 'visible') void refresh(); };
    window.addEventListener('focus', recheck);
    document.addEventListener('visibilitychange', recheck);
    const interval = window.setInterval(recheck, 60_000);
    return () => {
      window.removeEventListener('focus', recheck);
      document.removeEventListener('visibilitychange', recheck);
      window.clearInterval(interval);
      const controller = pending.current;
      pending.current = null;
      controller?.abort();
    };
  }, [refresh]);

  const logout = useCallback(async () => {
    if (signingOut.current) return;
    signingOut.current = true;
    pending.current?.abort();
    pending.current = null;
    setSession({ user: null, status: 'loading', error: '' });
    try {
      await logoutSession();
      // Nothing one person read stays in the cache for the next person on this device.
      queries.clear();
      setSession({ user: null, status: 'unauthenticated', error: '' });
      // One sign-out for both apps (S.C1): the session is already ended; this round trip also clears Command Center's
      // cookie, which only its own host can do, and ends on its sign-in page.
      window.location.assign(SHARED_SIGNOUT);
    } catch {
      setSession({ user: null, status: 'error', error: 'Sign-out could not be confirmed by Command Center. Retry before leaving this device.' });
    } finally {
      signingOut.current = false;
    }
  }, [queries]);

  const value = useMemo(() => ({ ...session, signIn, refresh, logout }), [session, signIn, refresh, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('useAuth must be used inside AuthProvider');
  return auth;
}
