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

/**
 * Mock alerts data (placeholder until alerts hook is available from WS7)
 * In production, this would come from useRecentAlerts hook
 */
const mockAlerts: AlertData[] = [
  {
    id: 1,
    message: 'High flood risk detected in Metro Manila due to continuous rainfall',
    risk_level: 75,
    created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    location: 'Metro Manila',
  },
  {
    id: 2,
    message: 'Moderate risk warning for Pampanga River Basin - water levels rising',
    risk_level: 55,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    location: 'Pampanga',
  },
  {
    id: 3,
    message: 'Low risk advisory: Monitor water levels in Laguna de Bay',
    risk_level: 25,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    location: 'Laguna',
  },
];

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
            {isLoading ? (
              <RecentAlertsSkeleton />
            ) : (
              <RecentAlerts alerts={mockAlerts} maxAlerts={5} />
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
