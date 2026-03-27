/**
 * useMapData Hook Tests
 *
 * Tests for the composite hook that aggregates 5 data sources
 * needed by the main map view. Validates aggregated loading, error,
 * and default option behavior via mocked sub-hooks.
 */

import { useMapData } from "@/features/map";
import { createWrapper } from "@/test/utils";
import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock all 5 sub-hooks
// ---------------------------------------------------------------------------

const mockUseLivePrediction = vi.fn();
const mockUseHazardMap = vi.fn();
const mockUseRecentAlerts = vi.fn();
const mockUseAlertCoverage = vi.fn();
const mockUseReportDensity = vi.fn();

vi.mock("@/features/flooding/hooks/useLivePrediction", () => ({
  useLivePrediction: (...args: unknown[]) => mockUseLivePrediction(...args),
}));
vi.mock("@/features/map/hooks/useHazardMap", () => ({
  useHazardMap: (...args: unknown[]) => mockUseHazardMap(...args),
}));
vi.mock("@/features/alerts/hooks/useAlerts", () => ({
  useRecentAlerts: (...args: unknown[]) => mockUseRecentAlerts(...args),
}));
vi.mock("@/features/alerts/hooks/useAlertCoverage", () => ({
  useAlertCoverage: (...args: unknown[]) => mockUseAlertCoverage(...args),
}));
vi.mock("@/features/reports/hooks/useReportDensity", () => ({
  useReportDensity: (...args: unknown[]) => mockUseReportDensity(...args),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockAllLoaded() {
  mockUseLivePrediction.mockReturnValue({
    data: { prediction: 0, risk_level: 0 },
    isLoading: false,
    isError: false,
    error: null,
  });
  mockUseHazardMap.mockReturnValue({
    data: { type: "FeatureCollection", features: [] },
    isLoading: false,
    error: null,
  });
  mockUseRecentAlerts.mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
  });
  mockUseAlertCoverage.mockReturnValue({
    data: { total_alerts: 5, delivery_rate: 80 },
    isLoading: false,
    isError: false,
    error: null,
  });
  mockUseReportDensity.mockReturnValue({
    data: { type: "FeatureCollection", features: [] },
    isLoading: false,
    isError: false,
    error: null,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useMapData", () => {
  it("returns aggregated results from all 5 hooks", () => {
    mockAllLoaded();

    const { result } = renderHook(() => useMapData(), {
      wrapper: createWrapper(),
    });

    expect(result.current.prediction).toBeDefined();
    expect(result.current.hazardMap).toBeDefined();
    expect(result.current.alerts).toBeDefined();
    expect(result.current.coverage).toBeDefined();
    expect(result.current.density).toBeDefined();
  });

  it("isLoading is false when all queries settle", () => {
    mockAllLoaded();

    const { result } = renderHook(() => useMapData(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("isLoading is true when prediction is still loading", () => {
    mockAllLoaded();
    mockUseLivePrediction.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    });

    const { result } = renderHook(() => useMapData(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it("isError is false when all queries succeed", () => {
    mockAllLoaded();

    const { result } = renderHook(() => useMapData(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isError).toBe(false);
    expect(result.current.errors).toHaveLength(0);
  });

  it("isError is true when prediction fails", () => {
    mockAllLoaded();
    mockUseLivePrediction.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network Error"),
    });

    const { result } = renderHook(() => useMapData(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isError).toBe(true);
    expect(result.current.errors).toHaveLength(1);
    expect(result.current.errors[0]!.message).toBe("Network Error");
  });

  it("isError is true when hazardMap has error string", () => {
    mockAllLoaded();
    mockUseHazardMap.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: "Failed to load hazard map",
    });

    const { result } = renderHook(() => useMapData(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isError).toBe(true);
    expect(result.current.errors).toHaveLength(1);
    expect(result.current.errors[0]!.message).toBe("Failed to load hazard map");
  });

  it("passes lat/lon and enabled option to prediction hook", () => {
    mockAllLoaded();

    renderHook(() => useMapData({ lat: 14.5, lon: 121.0, enabled: false }), {
      wrapper: createWrapper(),
    });

    expect(mockUseLivePrediction).toHaveBeenCalledWith({
      lat: 14.5,
      lon: 121.0,
      enabled: false,
    });
  });

  it("passes coverageHours to alert coverage hook", () => {
    mockAllLoaded();

    renderHook(() => useMapData({ coverageHours: 48 }), {
      wrapper: createWrapper(),
    });

    expect(mockUseAlertCoverage).toHaveBeenCalledWith(48);
  });

  it("passes densityHours to report density hook", () => {
    mockAllLoaded();

    renderHook(() => useMapData({ densityHours: 336 }), {
      wrapper: createWrapper(),
    });

    expect(mockUseReportDensity).toHaveBeenCalledWith(336);
  });

  it("uses default options when called without arguments", () => {
    mockAllLoaded();

    renderHook(() => useMapData(), {
      wrapper: createWrapper(),
    });

    expect(mockUseLivePrediction).toHaveBeenCalledWith({
      lat: undefined,
      lon: undefined,
      enabled: true,
    });
    expect(mockUseAlertCoverage).toHaveBeenCalledWith(24);
    expect(mockUseReportDensity).toHaveBeenCalledWith(168);
  });

  it("returns all 8 keys in the result object", () => {
    mockAllLoaded();

    const { result } = renderHook(() => useMapData(), {
      wrapper: createWrapper(),
    });

    expect(Object.keys(result.current)).toEqual(
      expect.arrayContaining([
        "prediction",
        "hazardMap",
        "alerts",
        "coverage",
        "density",
        "isLoading",
        "isError",
        "errors",
      ]),
    );
  });
});
