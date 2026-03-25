/**
 * RequireRole Component
 *
 * Route guard that restricts access to users with a specific role.
 * Prevents the guarded route's lazy chunk from being downloaded
 * by users who lack the required role.
 */

import { getDefaultRoute } from "@/config/role-routes";
import { useUser } from "@/state";
import { Navigate } from "react-router-dom";

interface RequireRoleProps {
  /** The role(s) allowed to render the children. Accepts a single role or array. */
  requiredRole: string | string[];
  /** Content to render when the user has the correct role */
  children: React.ReactNode;
  /** Path to redirect to when the user lacks the role (default: user's own dashboard) */
  redirectTo?: string;
}

/**
 * RequireRole guards routes that require a specific user role.
 *
 * Accepts a single role string or an array of roles. If the
 * current user does not have one of the allowed roles, they are
 * redirected to their own dashboard.
 */
export function RequireRole({
  requiredRole,
  children,
  redirectTo,
}: RequireRoleProps) {
  const user = useUser();
  const allowed = Array.isArray(requiredRole) ? requiredRole : [requiredRole];

  if (!user || !allowed.includes(user.role)) {
    // Redirect to the explicitly provided path, or the user's own dashboard
    const target = redirectTo ?? getDefaultRoute(user?.role);
    return <Navigate to={target} replace />;
  }

  return <>{children}</>;
}

export default RequireRole;
