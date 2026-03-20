/**
 * useReports Hooks
 *
 * React Query mutations for generating and downloading reports.
 * Supports PDF and CSV export with automatic browser download.
 */

import { captureException } from "@/lib/sentry";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import {
  reportsApi,
  type ReportParams,
  type ReportType,
} from "../services/reportsApi";

/**
 * Helper function to trigger browser download of a Blob
 *
 * @param blob - The file blob to download
 * @param filename - Name for the downloaded file
 */
export function downloadBlob(blob: Blob, filename: string): void {
  // Create object URL for the blob
  const url = window.URL.createObjectURL(blob);

  // Create hidden anchor element
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";

  // Append to body, click, and cleanup
  document.body.appendChild(link);
  link.click();

  // Cleanup
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Generate a filename based on report parameters
 *
 * @param reportType - Type of report
 * @param extension - File extension (pdf or csv)
 * @param startDate - Optional start date
 * @param endDate - Optional end date
 */
function generateFilename(
  reportType: ReportType,
  extension: "pdf" | "csv",
  startDate?: string,
  endDate?: string,
): string {
  const timestamp = new Date().toISOString().split("T")[0];
  const dateRange = startDate && endDate ? `_${startDate}_to_${endDate}` : "";
  return `floodingnaque_${reportType}_report${dateRange}_${timestamp}.${extension}`;
}

/**
 * Query keys for reports
 */
export const reportsKeys = {
  all: ["reports"] as const,
  exports: () => [...reportsKeys.all, "exports"] as const,
};

/**
 * Hook for exporting reports as PDF
 *
 * @returns Mutation object for PDF export
 *
 * @example
 * const { mutate: exportPDF, isPending } = useExportPDF();
 * exportPDF({ report_type: 'predictions', start_date: '2026-01-01', end_date: '2026-01-31' });
 */
export function useExportPDF() {
  return useMutation({
    mutationFn: (params: ReportParams) => reportsApi.exportPDF(params),
    onSuccess: (blob, params) => {
      const filename = generateFilename(
        params.report_type,
        "pdf",
        params.start_date,
        params.end_date,
      );
      downloadBlob(blob, filename);
      toast.success("PDF Report Downloaded", {
        description: `Your ${params.report_type} report has been downloaded successfully.`,
      });
    },
    onError: (error: Error) => {
      captureException(error, { context: "PDF export" });
      toast.error("Export Failed", {
        description:
          error.message || "Failed to generate PDF report. Please try again.",
      });
    },
  });
}

/**
 * Hook for exporting reports as CSV
 *
 * @returns Mutation object for CSV export
 *
 * @example
 * const { mutate: exportCSV, isPending } = useExportCSV();
 * exportCSV({ report_type: 'alerts', start_date: '2026-01-01', end_date: '2026-01-31' });
 */
export function useExportCSV() {
  return useMutation({
    mutationFn: (params: ReportParams) => reportsApi.exportCSV(params),
    onSuccess: (blob, params) => {
      const filename = generateFilename(
        params.report_type,
        "csv",
        params.start_date,
        params.end_date,
      );
      downloadBlob(blob, filename);
      toast.success("CSV Report Downloaded", {
        description: `Your ${params.report_type} report has been downloaded successfully.`,
      });
    },
    onError: (error: Error) => {
      captureException(error, { context: "CSV export" });
      toast.error("Export Failed", {
        description:
          error.message || "Failed to generate CSV report. Please try again.",
      });
    },
  });
}

/**
 * Combined hook for report generation with format selection
 *
 * @returns Object with export functions and loading states
 *
 * @example
 * const { exportReport, isExporting } = useReportExport();
 * exportReport({ report_type: 'weather' }, 'pdf');
 */
export function useReportExport() {
  const [progress, setProgress] = useState(0);
  const pdfMutation = useExportPDF();
  const csvMutation = useExportCSV();

  const exportReport = (params: ReportParams, format: "pdf" | "csv") => {
    setProgress(0);
    // Reset previous state before starting new export
    pdfMutation.reset();
    csvMutation.reset();
    if (format === "pdf") {
      pdfMutation.mutate(params);
    } else {
      csvMutation.mutate(params);
    }
  };

  return {
    exportReport,
    exportPDF: pdfMutation.mutate,
    exportCSV: csvMutation.mutate,
    isExportingPDF: pdfMutation.isPending,
    isExportingCSV: csvMutation.isPending,
    isExporting: pdfMutation.isPending || csvMutation.isPending,
    isSuccess: pdfMutation.isSuccess || csvMutation.isSuccess,
    isError: pdfMutation.isError || csvMutation.isError,
    error: pdfMutation.error || csvMutation.error,
    pdfError: pdfMutation.error,
    csvError: csvMutation.error,
    /** Reset mutation states (success/error) for a fresh form */
    reset: () => {
      pdfMutation.reset();
      csvMutation.reset();
    },
    /** Download progress 0–100 */
    progress,
    setProgress,
  };
}

/**
 * Hook for background report generation with task polling.
 * For date ranges > 7 days, submits an async job and polls every 3s.
 * Falls back to synchronous download if backend doesn't support it.
 */
export function useAsyncReport() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const { exportReport, isExporting, progress, setProgress } =
    useReportExport();

  const statusQuery = useQuery({
    queryKey: ["report-status", taskId],
    queryFn: () => reportsApi.getReportStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) =>
      query.state.data?.status === "completed" ||
      query.state.data?.status === "failed"
        ? false
        : 3000,
  });

  const submitReport = async (params: ReportParams, format: "pdf" | "csv") => {
    // Only attempt async for date ranges > 7 days
    const isLongRange =
      params.start_date &&
      params.end_date &&
      (new Date(params.end_date).getTime() -
        new Date(params.start_date).getTime()) /
        86_400_000 >
        7;

    if (isLongRange) {
      const result = await reportsApi.submitAsyncReport(params, format);
      if (result) {
        setTaskId(result.taskId);
        toast.info("Report Queued", {
          description: "Your report is being generated in the background.",
        });
        return;
      }
    }

    // Fallback: synchronous download
    exportReport(params, format);
  };

  const reset = () => setTaskId(null);

  return {
    submitReport,
    taskId,
    taskStatus: statusQuery.data?.status ?? null,
    downloadUrl: statusQuery.data?.downloadUrl ?? null,
    isExporting,
    progress,
    setProgress,
    reset,
  };
}

export default useReportExport;
