/**
 * ProtectedRoute Component
 *
 * Route wrapper that requires authentication.
 * Waits for Zustand store rehydration before making a redirect decision,
 * preventing a flash-then-logout on hard refresh.
 */

import { PageLoader } from "@/components/feedback/PageLoader";
import { canAccessRoute, getDefaultRoute } from "@/config/role-routes";
import { useAuthStore } from "@/state/stores/authStore";
import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { toast } from "sonner";

/**
 * ProtectedRoute guards routes that require authentication
 *
 * If Zustand has not finished rehydrating from localStorage we show
 * nothing (or a spinner) instead of immediately redirecting to /login.
 * Once hydration is complete, unauthenticated users are redirected.
 */
export function ProtectedRoute() {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const user = useAuthStore((state) => state.user);

  // Wait for Zustand to finish rehydrating persisted state before deciding
  if (!hasHydrated) {
    // Show a spinner while rehydrating so the user gets visual feedback
    return <PageLoader />;
  }

  if (!isAuthenticated || !user) {
    // Redirect to login, preserving the intended destination
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Enforce route access - prevent cross-role navigation
  // e.g. a resident manually typing /admin in the URL
  const currentPath = location.pathname;
  const accessDenied = !canAccessRoute(user.role, currentPath);

  useEffect(() => {
    if (accessDenied) {
      toast.error(
        "Access denied - you don't have permission to view that page",
      );
    }
  }, [accessDenied]);

  if (accessDenied) {
    return <Navigate to={getDefaultRoute(user.role)} replace />;
  }

  // User is authenticated and authorized, render the child routes
  return <Outlet />;
}

export default ProtectedRoute;
