/**
 * ProtectedRoute Component
 *
 * Route wrapper that requires authentication.
 * Waits for Zustand store rehydration before making a redirect decision,
 * preventing a flash-then-logout on hard refresh.
 */

import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/state/stores/authStore';
import { PageLoader } from '@/components/feedback/PageLoader';

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

  // Wait for Zustand to finish rehydrating persisted state before deciding
  if (!hasHydrated) {
    // Show a spinner while rehydrating so the user gets visual feedback
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    // Redirect to login, preserving the intended destination
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // User is authenticated, render the child routes
  return <Outlet />;
}

export default ProtectedRoute;
