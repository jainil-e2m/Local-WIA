import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/auth";
import type { UserRole } from "@/services/api/auth";

interface RequireAuthProps {
  /** Roles allowed through. Omit to allow any signed-in account. */
  roles?: UserRole[];
}

/**
 * Route guard for everything except the landing page and /login.
 * While the session check is in flight it shows the same neutral surface as
 * the lazy-route fallback, so there's no flash of protected content.
 *
 * `roles` narrows a route to specific accounts. This is a UX guard, not the
 * security boundary — a determined client-role user can call the API directly,
 * so anything gated here MUST also be gated server-side (see requireRole in
 * server/index.mjs). Its job is to stop a legitimate user landing on a page
 * that would only render errors.
 */
export function RequireAuth({ roles }: RequireAuthProps = {}) {
  const { status, user } = useAuth();
  const location = useLocation();

  /* DEV-ONLY BYPASS. Set VITE_AUTH_DISABLED=1 in .env.local to work on
     protected routes without the BFF on :8787 issuing a session.

     An env flag rather than a commented-out guard on purpose: it cannot ship
     enabled by accident (production never sets it), and it is reverted by
     deleting one line from a git-ignored file instead of by remembering to
     undo a code edit. Mirrored server-side by AUTH_DISABLED — the route guard
     and the API gate are separate boundaries, so both are needed. */
  if (import.meta.env.VITE_AUTH_DISABLED === "1") {
    return <Outlet />;
  }

  if (status === "loading") {
    return <div className="bg-hero min-h-[100svh]" aria-hidden />;
  }

  if (status === "unauthenticated") {
    // Remember where the user was headed so login can return them there.
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // Signed in but not permitted. Home rather than /login: they are already
  // authenticated, so bouncing to a login form would just loop them.
  if (roles && user && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
