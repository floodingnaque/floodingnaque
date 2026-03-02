/**
 * Dashboard Page
 *
 * Role-differentiated dashboard view:
 *   - user     → ResidentDashboard (hero risk card + map + alerts + emergency)
 *   - operator → LGUDashboard       (KPI row + forecast + analytics + map)
 *   - admin    → ResidentDashboard  (default view; admin panel is at /admin)
 *
 * Falls back to ResidentDashboard for unauthenticated or unknown roles.
 */

import { useUser } from '@/state';
import { ResidentDashboard } from '@/features/dashboard/components/ResidentDashboard';
import { LGUDashboard } from '@/features/dashboard/components/LGUDashboard';

/**
 * Dashboard page component - renders based on user role
 */
export function DashboardPage() {
  const user = useUser();

  if (user?.role === 'operator') {
    return <LGUDashboard />;
  }

  // Default: Resident dashboard (works for 'user', 'admin', and unauthenticated)
  return <ResidentDashboard />;
}

export default DashboardPage;
