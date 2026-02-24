/**
 * ProtectedRoute Component
 *
 * Route wrapper that requires authentication.
 * Redirects unauthenticated users to login page.
 */

import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/state/stores/authStore';

/**
 * ProtectedRoute guards routes that require authentication
 *
 * If the user is not authenticated, they are redirected to /login
 * with the current location stored in state for redirect after login.
 */
export function ProtectedRoute() {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    // Redirect to login, preserving the intended destination
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // User is authenticated, render the child routes
  return <Outlet />;
}

export default ProtectedRoute;
