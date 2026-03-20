/**
 * Admin Feature Module
 *
 * Barrel exports for admin-related components, hooks, and services.
 */

// Services
export { adminApi } from "./services/adminApi";

// Hooks
export {
  adminQueryKeys,
  useApiResponseStats,
  useFeatureFlags,
  useModelComparison,
  useModels,
  useMonitoringSummary,
  useSystemHealth,
  useTriggerRetrain,
  useUpdateFeatureFlag,
  useUptimeStats,
} from "./hooks/useAdmin";

// Components
export {
  ApiHealthMonitor,
  ApiHealthMonitorSkeleton,
} from "./components/ApiHealthMonitor";
export type { ApiHealthMonitorProps } from "./components/ApiHealthMonitor";
