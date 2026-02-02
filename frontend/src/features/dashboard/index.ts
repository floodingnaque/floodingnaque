/**
 * Dashboard Feature Module
 *
 * Barrel export for all dashboard-related components,
 * hooks, and services.
 */

// Services
export { dashboardApi, type DashboardStats, type ActivityItem } from './services/dashboardApi';

// Hooks
export { useDashboardStats, dashboardQueryKeys } from './hooks/useDashboard';

// Components
export { StatsCards, StatsCardsSkeleton } from './components/StatsCards';
export { RecentActivity, RecentActivitySkeleton } from './components/RecentActivity';
export { RecentAlerts, RecentAlertsSkeleton, type AlertData } from './components/RecentAlerts';
export { QuickActions, QuickActionsCompact } from './components/QuickActions';
