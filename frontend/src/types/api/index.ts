// API Types for Floodingnaque Frontend
// Barrel exports from modular type files

export * from "./alert";
export * from "./auth";
export * from "./common";
export * from "./community";
export * from "./lgu";
export * from "./prediction";
export * from "./weather";

// ============================================================================
// Export Types
// ============================================================================

export interface ExportOptions {
  format: "pdf" | "csv";
  dateRange?: {
    start: string;
    end: string;
  };
  includeCharts?: boolean;
  filters?: Record<string, unknown>;
}

export interface ExportResponse {
  downloadUrl: string;
  filename: string;
  size: number;
  expiresAt: string;
}
