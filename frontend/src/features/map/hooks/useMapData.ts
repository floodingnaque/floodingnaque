/**
 * useMapData – composite hook that aggregates all data sources
 * needed by the main map view into a single, consistent object.
 *
 * Composes:
 *   1. useLivePrediction – current flood risk from live prediction
 *   2. useHazardMap      – barangay-level hazard polygons
 *   3. useRecentAlerts   – latest alert markers
 *   4. useAlertCoverage  – delivery coverage stats
 *   5. useReportDensity  – community report heatmap GeoJSON
 */

import { useAlertCoverage } from "@/features/alerts/hooks/useAlertCoverage";
import { useRecentAlerts } from "@/features/alerts/hooks/useAlerts";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { useHazardMap } from "@/features/map/hooks/useHazardMap";
import { useReportDensity } from "@/features/reports/hooks/useReportDensity";
import { useMemo } from "react";

interface UseMapDataOptions {
  lat?: number;
  lon?: number;
  /** Whether to enable all queries (disable when map is not visible) */
  enabled?: boolean;
  /** Lookback hours for alert coverage (default: 24) */
  coverageHours?: number;
  /** Lookback hours for report density (default: 168 = 7 days) */
  densityHours?: number;
}

export function useMapData({
  lat,
  lon,
  enabled = true,
  coverageHours = 24,
  densityHours = 168,
}: UseMapDataOptions = {}) {
  const prediction = useLivePrediction({ lat, lon, enabled });
  const hazardMap = useHazardMap();
  const alerts = useRecentAlerts(20);
  const coverage = useAlertCoverage(coverageHours);
  const density = useReportDensity(densityHours);

  const isLoading =
    prediction.isLoading || hazardMap.isLoading || alerts.isLoading;

  const isError = prediction.isError || !!hazardMap.error || alerts.isError;

  const errors = useMemo(
    () =>
      [
        prediction.error,
        hazardMap.error ? new Error(hazardMap.error) : null,
        alerts.error,
      ].filter(Boolean) as Error[],
    [prediction.error, hazardMap.error, alerts.error],
  );

  return {
    prediction,
    hazardMap,
    alerts,
    coverage,
    density,
    isLoading,
    isError,
    errors,
  };
}
