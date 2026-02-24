// API Types for Floodingnaque Frontend
// Barrel exports from modular type files

export * from './common';
export * from './prediction';
export * from './weather';
export * from './alert';
export * from './auth';

// ============================================================================
// Export Types
// ============================================================================

export interface ExportOptions {
  format: 'pdf' | 'csv';
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
