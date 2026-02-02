// API Types for Floodingnaque Frontend
// Barrel exports from modular type files

export * from './common';
export * from './prediction';
export * from './weather';
export * from './alert';
export * from './auth';

// ============================================================================
// Legacy Types (retained for backward compatibility)
// ============================================================================

// Dashboard Types
export interface DashboardStats {
  totalPredictions: number;
  activeAlerts: number;
  highRiskAreas: number;
  systemHealth: {
    status: 'healthy' | 'degraded' | 'unhealthy';
    uptime: number;
    lastCheck: string;
  };
  recentActivity: {
    predictions24h: number;
    alertsTriggered24h: number;
    usersActive24h: number;
  };
}

// Export Types
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
