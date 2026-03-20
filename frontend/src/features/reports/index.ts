/**
 * Reports Feature Module
 *
 * Barrel exports for the reports feature including services,
 * hooks, and components for report generation and export.
 */

// Services
export {
  getReportLabel,
  reportsApi,
  type ReportParams,
  type ReportType,
} from "./services/reportsApi";

// Hooks
export {
  downloadBlob,
  reportsKeys,
  useExportCSV,
  useExportPDF,
  useReportExport,
} from "./hooks/useReports";

// Components
export {
  ReportGenerator,
  type ReportGeneratorProps,
} from "./components/ReportGenerator";
