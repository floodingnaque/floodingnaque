/**
 * useRainfallHistory Hook
 *
 * Wraps useHourlyWeather and transforms weather data into
 * chart-ready rainfall points with derived metrics.
 */

import { useHourlyWeather } from "@/features/weather/hooks/useWeather";
import { useMemo } from "react";
import type { RainfallMetrics, RainfallPoint } from "../types";

function classifyIntensity(mm: number): RainfallPoint["intensity"] {
  if (mm >= 7.5) return "heavy";
  if (mm >= 2.5) return "moderate";
  return "light";
}

export function useRainfallHistory(days = 1) {
  const {
    data: weatherData,
    isLoading,
    isError,
    error,
  } = useHourlyWeather(
    { days },
    { staleTime: 2 * 60 * 1000, refetchInterval: 2 * 60 * 1000 },
  );

  const { data, metrics } = useMemo(() => {
    if (!weatherData?.length) {
      return {
        data: [] as RainfallPoint[],
        metrics: {
          current: 0,
          rolling3h: 0,
          trend: "steady",
          intensity: "light",
        } as RainfallMetrics,
      };
    }

    // Sort chronologically
    const sorted = [...weatherData].sort(
      (a, b) =>
        new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime(),
    );

    const points: RainfallPoint[] = sorted.map((w) => ({
      time: new Date(w.recorded_at).toLocaleTimeString("en-PH", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      mm: w.precipitation,
      intensity: classifyIntensity(w.precipitation),
    }));

    const current = sorted[sorted.length - 1]?.precipitation ?? 0;

    // 3-hour rolling total (last 3 entries if hourly)
    const last3 = sorted.slice(-3);
    const rolling3h = last3.reduce((sum, w) => sum + w.precipitation, 0);

    // Trend: compare last 3 to previous 3
    const prev3 = sorted.slice(-6, -3);
    const prevTotal = prev3.reduce((sum, w) => sum + w.precipitation, 0);
    let trend: RainfallMetrics["trend"] = "steady";
    if (rolling3h > prevTotal * 1.2) trend = "rising";
    else if (rolling3h < prevTotal * 0.8) trend = "falling";

    return {
      data: points,
      metrics: {
        current,
        rolling3h,
        trend,
        intensity: classifyIntensity(current),
      } satisfies RainfallMetrics,
    };
  }, [weatherData]);

  return { data, metrics, isLoading, isError, error };
}
