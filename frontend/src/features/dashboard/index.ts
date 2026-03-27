/**
 * Dashboard Feature Module
 *
 * Barrel export for all dashboard-related components,
 * hooks, and services.
 */

// Services
export {
  dashboardApi,
  type ActivityItem,
  type DashboardStats,
} from "./services/dashboardApi";

// Hooks
export { dashboardQueryKeys, useDashboardStats } from "./hooks/useDashboard";

// Components
export {
  AlertFrequency,
  RainfallTrend,
  RiskDistribution,
} from "./components/AnalyticsCharts";
export { BarangayRiskMap } from "./components/BarangayRiskMap";
export { EmergencyInfoPanel } from "./components/EmergencyInfoPanel";
export {
  FloodStatusHero,
  FloodStatusHeroSkeleton,
} from "./components/FloodStatusHero";
export {
  ForecastPanel,
  ForecastPanelSkeleton,
} from "./components/ForecastPanel";
export { LGUDashboard } from "./components/LGUDashboard";
export {
  AccuracyProgressionChart,
  ModelSummaryCards,
  ModelVersionTable,
} from "./components/ModelManagement";
export { QuickActions, QuickActionsCompact } from "./components/QuickActions";
export {
  RecentActivity,
  RecentActivitySkeleton,
} from "./components/RecentActivity";
export {
  RecentAlerts,
  RecentAlertsSkeleton,
  type AlertData,
} from "./components/RecentAlerts";
export { ResidentDashboard } from "./components/ResidentDashboard";
export { StatsCards, StatsCardsSkeleton } from "./components/StatsCards";

// Enhanced Dashboard Panels
export {
  EnhancedPredictionCard,
  EnhancedPredictionCardSkeleton,
} from "./components/EnhancedPredictionCard";
export {
  EvacuationStatusGrid,
  EvacuationStatusGridSkeleton,
} from "./components/EvacuationStatusGrid";
export {
  RainfallMonitor,
  RainfallMonitorSkeleton,
} from "./components/RainfallMonitor";
export {
  RiverLevelMonitor,
  RiverLevelMonitorSkeleton,
} from "./components/RiverLevelMonitor";

// Enhanced Dashboard Hooks
export { useRainfallHistory } from "./hooks/useRainfallHistory";
export { useRiverLevel } from "./hooks/useRiverLevel";

// Analytics Panels
export {
  AlertCenterPanel,
  AlertCenterPanelSkeleton,
} from "./components/AlertCenterPanel";
export {
  FloodTrendPanel,
  FloodTrendPanelSkeleton,
} from "./components/FloodTrendPanel";
export {
  HistoricalFloodPanel,
  HistoricalFloodPanelSkeleton,
} from "./components/HistoricalFloodPanel";
export {
  ModelConfidencePanel,
  ModelConfidencePanelSkeleton,
} from "./components/ModelConfidencePanel";
export {
  analyticsQueryKeys,
  useFloodHistory,
  useModelMetrics,
} from "./hooks/useAnalytics";
export { analyticsApi } from "./services/analyticsApi";

// Dashboard Types
export type {
  AlertChannel,
  BarangayStatus,
  EmergencyContact,
  FeatureContribution,
  FloodEvent,
  FloodFrequencyItem,
  FloodHistoryData,
  FloodHistorySummary,
  HeatmapCell,
  IncidentTimelineEntry,
  ModelMetrics,
  ModelMetricsData,
  MonthlyFloodTrend,
  PreparednessItem,
  PreparednessPhase,
  RainfallFloodPoint,
  RainfallMetrics,
  RainfallPoint,
  RiverReading,
  RiverStation,
  SeasonalRisk,
  SmsLogEntry,
  SmsTemplate,
  YearlyFloodTrend,
} from "./types";

// Emergency & Community components
export {
  EmergencyCommandPanel,
  EmergencyCommandPanelSkeleton,
} from "./components/EmergencyCommandPanel";
export {
  FloodPreparednessGuide,
  FloodPreparednessGuideSkeleton,
} from "./components/FloodPreparednessGuide";
export {
  FloodRiskHeatmap,
  FloodRiskHeatmapSkeleton,
} from "./components/FloodRiskHeatmap";
