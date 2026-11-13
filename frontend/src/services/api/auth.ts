import axios from "axios";

/**
 * Auth endpoints live on the dashboard's own origin (the Express server that
 * also serves this bundle), while every audit has its own configured service
 * URL. A dedicated same-origin client keeps the session cookie first-party.
 * In dev, the Vite proxy forwards /api/auth/* to the local auth server.
 */
const authApi = axios.create({
  baseURL: "",
  timeout: 10_000,
  headers: { "Content-Type": "application/json" },
});

/** Roles a session can hold. `team` is the internal developer account; `client`
    is the consumer login. See server/auth-core.mjs for how they're resolved. */
export type UserRole = "team" | "client";

export interface AuthUser {
  email: string;
  name: string;
  role: UserRole;
}

/** Resolves with the user on success; throws AxiosError (401/429) otherwise. */
export async function login(email: string, password: string): Promise<AuthUser> {
  const { data } = await authApi.post<{ user: AuthUser }>("/api/auth/login", { email, password });
  return data.user;
}

export async function logout(): Promise<void> {
  await authApi.post("/api/auth/logout");
}

/** Returns the signed-in user, or null when there is no valid session. */
export async function getSession(): Promise<AuthUser | null> {
  try {
    const { data } = await authApi.get<{ user: AuthUser }>("/api/auth/session");
    return data.user;
  } catch {
    return null;
  }
}
