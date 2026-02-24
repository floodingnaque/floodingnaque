/**
 * Dashboard Page
 *
 * Main dashboard view displaying statistics, recent activity,
 * alerts, and quick actions in a responsive layout.
 */

import { Droplets } from 'lucide-react';
import { ConnectionStatus, ErrorDisplay } from '@/components/feedback';
import { useDashboardStats } from '@/features/dashboard/hooks/useDashboard';
import {
  StatsCards,
  StatsCardsSkeleton,
} from '@/features/dashboard/components/StatsCards';
import {
  RecentActivity,
  RecentActivitySkeleton,
} from '@/features/dashboard/components/RecentActivity';
import {
  RecentAlerts,
  RecentAlertsSkeleton,
  type AlertData,
} from '@/features/dashboard/components/RecentAlerts';
import { QuickActionsCompact } from '@/features/dashboard/components/QuickActions';
import { useRecentAlerts } from '@/features/alerts';

/** Map API RiskLevel (0 | 1 | 2) → 0-100 score for the RecentAlerts component */
const RISK_SCORE: Record<number, number> = { 0: 15, 1: 50, 2: 75 };

/**
 * Dashboard page component with responsive layout
 */
export function DashboardPage() {
  const {
    data: stats,
    isLoading,
    isError,
    error,
    refetch,
  } = useDashboardStats();

  const { data: recentAlerts, isLoading: alertsLoading } = useRecentAlerts(5);

  /** Convert API alerts to the AlertData shape expected by RecentAlerts */
  const dashboardAlerts: AlertData[] = (recentAlerts ?? []).map((a) => ({
    id: a.id,
    message: a.message,
    risk_level: RISK_SCORE[a.risk_level] ?? a.risk_level,
    created_at: a.created_at,
    location: a.location,
  }));

  return (
    <div className="min-h-screen bg-background">
      {/* Page Container */}
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Droplets className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
              <p className="text-sm text-muted-foreground">
                Flood prediction and monitoring overview
              </p>
            </div>
          </div>
          <ConnectionStatus showLabel size="md" />
        </header>

        {/* Error State */}
        {isError && (
          <ErrorDisplay
            error={error}
            retry={() => refetch()}
            title="Failed to load dashboard"
          />
        )}

        {/* Stats Cards */}
        {isLoading ? (
          <StatsCardsSkeleton />
        ) : stats ? (
          <StatsCards stats={stats} />
        ) : null}

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column - Recent Activity (2/3 width on desktop) */}
          <div className="lg:col-span-2">
            {isLoading ? (
              <RecentActivitySkeleton />
            ) : stats ? (
              <RecentActivity activities={stats.recent_activity} />
            ) : null}
          </div>

          {/* Right Column - Alerts & Quick Actions (1/3 width on desktop) */}
          <div className="space-y-6">
            {/* Recent Alerts */}
            {isLoading || alertsLoading ? (
              <RecentAlertsSkeleton />
            ) : (
              <RecentAlerts alerts={dashboardAlerts} maxAlerts={5} />
            )}

            {/* Quick Actions */}
            <QuickActionsCompact />
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
