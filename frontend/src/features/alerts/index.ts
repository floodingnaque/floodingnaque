/**
 * Alerts Feature Module
 *
 * Barrel exports for all alerts-related components, hooks, and services.
 */

// Services
export { alertsApi } from './services/alertsApi';

// Hooks
export {
  useAlerts,
  useRecentAlerts,
  useAlertHistory,
  useAcknowledgeAlert,
  useAcknowledgeAll,
  useSimulateSms,
  alertKeys,
} from './hooks/useAlerts';
export { useAlertStream } from './hooks/useAlertStream';

// Types
export type { SmsSimulationResponse } from './services/alertsApi';

// Components
export { AlertBadge } from './components/AlertBadge';
export { AlertCard } from './components/AlertCard';
export { AlertList } from './components/AlertList';
export { LiveAlertsBanner } from './components/LiveAlertsBanner';
export { ConnectionStatus } from './components/ConnectionStatus';
export { SmsSimulationPanel } from './components/SmsSimulationPanel';
