import { useCallback, useEffect, useMemo, useState } from "react";
import * as authApi from "@/services/api/auth";
import type { AuthUser } from "@/services/api/auth";
import { AuthContext, type AuthStatus } from "./auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  // Restore the session (HttpOnly cookie → server check) on first load.
  useEffect(() => {
    let cancelled = false;
    authApi.getSession().then((sessionUser) => {
      if (cancelled) return;
      setUser(sessionUser);
      setStatus(sessionUser ? "authenticated" : "unauthenticated");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const loggedIn = await authApi.login(email, password);
    setUser(loggedIn);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    // Clear local state first so protected routes lock immediately even if
    // the network call is slow; the server call ends the session.
    setUser(null);
    setStatus("unauthenticated");
    await authApi.logout().catch(() => {});
    // One sign-out for Command Center and the Content Atelier (S.C1): the
    // server's sign-out round trip also clears the Atelier's cookie and lands
    // on /login. A full page load, because only the Atelier's own host can
    // clear its cookie.
    window.location.assign("/api/auth/signout");
  }, []);

  const value = useMemo(() => ({ status, user, login, logout }), [status, user, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
