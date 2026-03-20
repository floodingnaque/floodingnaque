/**
 * Evacuation Feature Module
 *
 * Self-contained module for evacuation center management,
 * real-time capacity monitoring, safe routing, and SMS alerts.
 */

// Services
export { evacuationApi } from "./services/evacuationApi";
export type { CenterListParams } from "./services/evacuationApi";

// Hooks
export { useCapacityStream } from "./hooks/useCapacityStream";
export {
  evacuationKeys,
  useEvacuationCenters,
  useEvacuationRoute,
  useNearestCenters,
  useTriggerAlert,
  useUpdateCapacity,
} from "./hooks/useEvacuationCenters";

// Components
export {
  EvacuationCapacityCard,
  EvacuationCapacityCardSkeleton,
} from "./components/EvacuationCapacityCard";
export type { EvacuationCapacityCardProps } from "./components/EvacuationCapacityCard";
export { EvacuationCenterMarkers } from "./components/EvacuationCenterMarkers";
export type { EvacuationCenterMarkersProps } from "./components/EvacuationCenterMarkers";
export { EvacuationPanel } from "./components/EvacuationPanel";
export type { EvacuationPanelProps } from "./components/EvacuationPanel";
export { EvacuationRoute } from "./components/EvacuationRoute";
export type { EvacuationRouteProps } from "./components/EvacuationRoute";
