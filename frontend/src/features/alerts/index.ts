/**
 * Alerts Feature Module
 *
 * Barrel exports for all alerts-related components, hooks, and services.
 */

// Services
export { alertsApi } from "./services/alertsApi";

// Hooks
export {
  coverageKeys,
  useAlertCoverage,
  type CoverageResponse,
} from "./hooks/useAlertCoverage";
export {
  alertKeys,
  useAcknowledgeAlert,
  useAcknowledgeAll,
  useAlertHistory,
  useAlerts,
  useRecentAlerts,
  useSimulateSms,
} from "./hooks/useAlerts";
export { useAlertStream } from "./hooks/useAlertStream";

// Types
export type { SmsSimulationResponse } from "./services/alertsApi";

// Components
export { AlertBadge } from "./components/AlertBadge";
export { AlertCard } from "./components/AlertCard";
export {
  AlertChannelPanel,
  AlertChannelPanelSkeleton,
} from "./components/AlertChannelPanel";
export { AlertCoverageLayer } from "./components/AlertCoverageLayer";
export { AlertList, AlertListSkeleton } from "./components/AlertList";
export { ConnectionStatus } from "./components/ConnectionStatus";
export {
  EmailSubscriptionToggle,
  EmailSubscriptionToggleSkeleton,
} from "./components/EmailSubscriptionToggle";
export type { EmailSubscriptionToggleProps } from "./components/EmailSubscriptionToggle";
export { LiveAlertsBanner } from "./components/LiveAlertsBanner";
export { PushPermissionPrompt } from "./components/PushPermissionPrompt";
export { SmsSimulationPanel } from "./components/SmsSimulationPanel";
export {
  SmsSubscriptionToggle,
  SmsSubscriptionToggleSkeleton,
} from "./components/SmsSubscriptionToggle";
export type { SmsSubscriptionToggleProps } from "./components/SmsSubscriptionToggle";
