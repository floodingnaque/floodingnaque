/**
 * useDashboard Hook Tests
 *
 * Tests for dashboard React Query hooks.
 */

import {
  dashboardQueryKeys,
  useDashboardStats,
} from "@/features/dashboard/hooks/useDashboard";
import { createWrapper } from "@/test/utils";
import { createMockDashboardStats } from "@/tests/mocks/handlers";
import { server } from "@/tests/mocks/server";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

describe("dashboardQueryKeys", () => {
  it("should generate correct query keys", () => {
    expect(dashboardQueryKeys.all).toEqual(["dashboard"]);
    expect(dashboardQueryKeys.stats()).toEqual(["dashboard", "stats"]);
  });
});

describe("useDashboardStats", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("should fetch dashboard stats successfully", async () => {
    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.total_predictions).toBeDefined();
    expect(result.current.data?.predictions_today).toBeDefined();
    expect(result.current.data?.active_alerts).toBeDefined();
    expect(result.current.data?.avg_risk_level).toBeDefined();
    expect(result.current.data?.recent_activity).toBeDefined();
  });

  it("should handle loading state", () => {
    // Use delay handler to ensure we can capture loading state
    server.use(
      http.get("*/api/v1/dashboard/stats", async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json(createMockDashboardStats());
      }),
    );

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("should handle error state", async () => {
    server.use(
      http.get("*/api/v1/dashboard/stats", () => {
        return HttpResponse.json(
          { code: "SERVER_ERROR", message: "Internal server error" },
          { status: 500 },
        );
      }),
    );

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeDefined();
  });

  it("should return correct data structure", async () => {
    server.use(
      http.get("*/api/v1/dashboard/stats", () => {
        return HttpResponse.json(createMockDashboardStats());
      }),
    );

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Values are normalised from the nested backend format
    expect(result.current.data?.total_predictions).toBe(1234);
    expect(result.current.data?.predictions_today).toBe(42);
    expect(result.current.data?.active_alerts).toBe(3);
    expect(result.current.data?.recent_activity).toHaveLength(0);
  });

  it("should not refetch when hook is not enabled", async () => {
    // First render with data
    const wrapper = createWrapper();
    const { result, rerender } = renderHook(() => useDashboardStats(), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Store initial data
    const initialData = result.current.data;

    // Rerender should use cached data
    rerender();

    expect(result.current.data).toEqual(initialData);
  });
});

describe("useDashboardStats with empty response", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("should handle empty recent activity", async () => {
    server.use(
      http.get("*/api/v1/dashboard/stats", () => {
        return HttpResponse.json({
          success: true,
          summary: {
            weather_data: { total: 0, today: 0, latest: null },
            predictions: { total: 0, today: 0, this_week: 0, latest: null },
            alerts: { total: 0, today: 0, critical_24h: 0 },
            risk_distribution_30d: { safe: 0, alert: 0, critical: 0 },
          },
          generated_at: new Date().toISOString(),
          request_id: "mock-request-id",
        });
      }),
    );

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.total_predictions).toBe(0);
    expect(result.current.data?.recent_activity).toHaveLength(0);
  });
});
