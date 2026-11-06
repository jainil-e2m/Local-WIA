import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AuthUser, getSession, logoutSession } from './session';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'error';
export interface AuthState {
  user: AuthUser | null;
  status: AuthStatus;
  error: string;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}
export const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<{ user: AuthUser | null; status: AuthStatus; error: string }>({ user: null, status: 'loading', error: '' });
  const pending = useRef<AbortController | null>(null);
  const signingOut = useRef(false);
  const refresh = useCallback(async () => {
    if (signingOut.current) return;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 10_000);
    try {
      const user = await getSession(controller.signal);
      if (pending.current === controller) setSession({ user, status: user ? 'authenticated' : 'unauthenticated', error: '' });
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
      setSession({ user: null, status: 'unauthenticated', error: '' });
    } catch {
      setSession({ user: null, status: 'error', error: 'Sign-out could not be confirmed by Command Center. Retry before leaving this device.' });
    } finally {
      signingOut.current = false;
    }
  }, []);

  const value = useMemo(() => ({ ...session, refresh, logout }), [session, refresh, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('useAuth must be used inside AuthProvider');
  return auth;
}
