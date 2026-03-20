/**
 * Storage Management API Service
 *
 * Provides API methods for the Storage Management page:
 * storage stats, cleanup count previews, bulk-delete, and purge operations.
 */

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";

// ── Types ──

export interface TableStats {
  total: number;
  active: number;
  soft_deleted: number;
  last_record_at: string | null;
  estimated_size_bytes: number;
}

export interface StorageSummary {
  total_rows: number;
  total_active: number;
  total_soft_deleted: number;
  estimated_total_bytes: number;
}

export interface StorageStatsResponse {
  success: boolean;
  tables: Record<string, TableStats>;
  summary: StorageSummary;
}

export interface CleanupCountResponse {
  success: boolean;
  count: number;
}

export interface CleanupResult {
  success: boolean;
  deleted_count?: number;
  message?: string;
  error?: string;
}

export interface PurgeResult {
  success: boolean;
  purged?: Record<string, number>;
  total_purged?: number;
  message?: string;
  error?: string;
}

// ── API Methods ──

export const storageApi = {
  /** Get storage stats for all tables */
  async getStats(): Promise<StorageStatsResponse> {
    return api.get<StorageStatsResponse>(API_ENDPOINTS.admin.storage);
  },

  /** Preview how many rows a cleanup would affect */
  async getCleanupCount(params: {
    type: "logs" | "reports" | "alerts";
    older_than_days: number;
    status?: string;
    delivery_status?: string;
  }): Promise<CleanupCountResponse> {
    const query = new URLSearchParams();
    query.set("type", params.type);
    query.set("older_than_days", String(params.older_than_days));
    if (params.status && params.status !== "all")
      query.set("status", params.status);
    if (params.delivery_status && params.delivery_status !== "all")
      query.set("delivery_status", params.delivery_status);
    return api.get<CleanupCountResponse>(
      `${API_ENDPOINTS.admin.storageCleanupCount}?${query.toString()}`,
    );
  },

  /** Bulk soft-delete API request logs */
  async bulkDeleteLogs(older_than_days: number): Promise<CleanupResult> {
    return api.post<CleanupResult>(API_ENDPOINTS.admin.logsBulkDelete, {
      older_than_days,
      confirm: true,
    });
  },

  /** Bulk soft-delete community reports */
  async bulkDeleteReports(
    older_than_days: number,
    status?: string,
  ): Promise<CleanupResult> {
    const body: Record<string, unknown> = {
      older_than_days,
      confirm: true,
    };
    if (status && status !== "all") body.status = status;
    return api.post<CleanupResult>(API_ENDPOINTS.admin.reportsBulkDelete, body);
  },

  /** Bulk soft-delete alert history */
  async bulkDeleteAlerts(
    older_than_days: number,
    delivery_status?: string,
  ): Promise<CleanupResult> {
    const body: Record<string, unknown> = {
      older_than_days,
      confirm: true,
    };
    if (delivery_status && delivery_status !== "all")
      body.delivery_status = delivery_status;
    return api.post<CleanupResult>(API_ENDPOINTS.admin.alertsBulkDelete, body);
  },

  /** Permanently purge soft-deleted records */
  async purgeDeleted(tables: string[]): Promise<PurgeResult> {
    return api.post<PurgeResult>(API_ENDPOINTS.admin.purgeDeleted, {
      tables,
      confirm: true,
    });
  },
};
