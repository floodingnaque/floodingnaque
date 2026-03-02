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
export { FloodStatusHero, FloodStatusHeroSkeleton } from './components/FloodStatusHero';
export { BarangayRiskMap } from './components/BarangayRiskMap';
export { EmergencyInfoPanel } from './components/EmergencyInfoPanel';
export { ForecastPanel } from './components/ForecastPanel';
export { RainfallTrend, RiskDistribution, AlertFrequency } from './components/AnalyticsCharts';
export { ModelVersionTable, AccuracyProgressionChart, ModelSummaryCards } from './components/ModelManagement';
export { ResidentDashboard } from './components/ResidentDashboard';
export { LGUDashboard } from './components/LGUDashboard';
