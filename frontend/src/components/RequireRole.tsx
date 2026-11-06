import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/auth";
import type { UserRole } from "@/services/api/auth";

/**
 * Role-gated route guard — a sibling to <RequireAuth /> for when access should
 * differ between the team and client logins.
 *
 * It is intentionally NOT wired to any route yet: the current policy is
 * permissive (every signed-in user sees everything). When you decide what a
 * role may access, wrap the relevant routes, e.g.:
 *
 *   <Route element={<RequireRole allow={["team"]} />}>
 *     <Route path="/automations/ai-seo" element={<ToolPage />} />
 *   </Route>
 *
 * IMPORTANT: hiding a route (or a tool tile) here is UX only. Any restriction
 * the client must not be able to bypass has to be enforced server-side on the
 * /api/technical-seo proxy as well — the browser can always call the API
 * directly. See RAILWAY_DEPLOYMENT_GUIDE.md.
 */
export function RequireRole({ allow }: { allow: UserRole[] }) {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <div className="bg-hero min-h-[100svh]" aria-hidden />;
  }

  if (status === "unauthenticated" || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!allow.includes(user.role)) {
    // Signed in but not permitted for this area — send home, not to /login.
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
