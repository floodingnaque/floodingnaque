/**
 * Community Feature Module
 *
 * Barrel exports for crowdsourced flood reporting components, hooks, and services.
 */

// Services
export {
  communityApi,
  type ReportListParams,
  type ReportListResponse,
  type ReportStatsParams,
  type ReportStatsResponse,
} from "./services/communityApi";

// Hooks
export {
  communityKeys,
  useCommunityReport,
  useCommunityReports,
  useFlagReport,
  useReportStats,
  useSubmitReport,
  useVerifyReport,
  useVoteReport,
} from "./hooks/useCommunityReports";

// Components
export {
  CommunityReportsPanel,
  CommunityReportsPanelSkeleton,
} from "./components/CommunityReportsPanel";
export { ReportFAB, type ReportFABProps } from "./components/ReportFAB";
export {
  ReportMapLayer,
  type ReportMapLayerProps,
} from "./components/ReportMapLayer";
export {
  ReportSubmitModal,
  type ReportSubmitModalProps,
} from "./components/ReportSubmitModal";
