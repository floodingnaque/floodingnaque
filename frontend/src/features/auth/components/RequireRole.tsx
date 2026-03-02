/**
 * RequireRole Component
 *
 * Route guard that restricts access to users with a specific role.
 * Prevents the guarded route's lazy chunk from being downloaded
 * by users who lack the required role.
 */

import { Navigate } from 'react-router-dom';
import { useUser } from '@/state';

interface RequireRoleProps {
  /** The role required to render the children */
  role: string;
  /** Content to render when the user has the correct role */
  children: React.ReactNode;
  /** Path to redirect to when the user lacks the role (default: /) */
  redirectTo?: string;
}

/**
 * RequireRole guards routes that require a specific user role.
 *
 * If the current user does not have the required role, they are
 * redirected to the specified path (default: home).
 */
export function RequireRole({ role, children, redirectTo = '/' }: RequireRoleProps) {
  const user = useUser();

  if (!user || user.role !== role) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}

export default RequireRole;
