/**
 * ForecastPanel Component (P1 - MUST HAVE)
 *
 * 3-hour rolling forecast for LGU / MDRRMO operators.
 * Shows hourly risk bars with precipitation, temperature, and tide status.
 * Data source: /api/data/hourly
 */

import { DataUnavailable } from "@/components/feedback";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { weatherApi } from "@/features/weather/services/weatherApi";
import { useQuery } from "@tanstack/react-query";
import { Clock, CloudRain } from "lucide-react";
import { memo, useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ForecastHour {
  hour: string; // "3 PM"
  precipitation: number; // mm
  temperature: number; // °C
  humidity: number;
  riskColor: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function riskColor(precip: number): string {
  if (precip >= 7.5) return "hsl(var(--risk-critical))"; // Critical
  if (precip >= 2.5) return "hsl(var(--risk-alert))"; // Alert
  return "hsl(var(--risk-safe))"; // Safe
}

// Meteostat hourly API returns temperature in Celsius — no conversion needed

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ForecastPanelProps {
  className?: string;
  /** Number of forecast hours to display (default 12) */
  hours?: number;
}

export const ForecastPanel = memo(function ForecastPanel({
  className,
  hours = 12,
}: ForecastPanelProps) {
  const {
    data: rawForecast,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["weather", "hourly", "forecast"],
    queryFn: () =>
      weatherApi.getHourlyForecast({
        lat: 14.4793,
        lon: 121.0198,
        days: 1,
      }),
    staleTime: 15 * 60 * 1000, // 15 min
    refetchInterval: 15 * 60 * 1000,
    retry: 2,
  });

  const forecastData: ForecastHour[] = useMemo(() => {
    if (!rawForecast?.length) return [];

    return rawForecast.slice(0, hours).map((w) => {
      const d = new Date(w.recorded_at);
      return {
        hour: d.toLocaleTimeString("en-PH", {
          hour: "numeric",
          hour12: true,
        }),
        precipitation: w.precipitation,
        temperature: w.temperature ? Math.round(w.temperature) : 0,
        humidity: w.humidity,
        riskColor: riskColor(w.precipitation),
      };
    });
  }, [rawForecast, hours]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Hourly Forecast
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-48 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!forecastData.length) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Hourly Forecast
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataUnavailable
            title="Forecast data unavailable"
            description="Weather data source is temporarily unavailable."
            action={{
              label: isFetching ? "Retrying..." : "Retry",
              onClick: () => void refetch(),
            }}
            compact
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <CloudRain className="h-4 w-4" />
            Precipitation Forecast
          </CardTitle>
          <span className="text-xs text-muted-foreground">
            Next {forecastData.length} hours
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={forecastData}
            margin={{ top: 5, right: 5, bottom: 5, left: -10 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="hour"
              tick={{ fontSize: 11 }}
              className="text-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              className="text-muted-foreground"
              unit=" mm"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.5rem",
                fontSize: 12,
              }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload as ForecastHour;
                return (
                  <div className="rounded-lg border bg-card p-2 text-xs shadow-sm">
                    <p className="font-medium">{d.hour}</p>
                    <p>Precipitation: {d.precipitation.toFixed(1)} mm</p>
                    <p>Temperature: {d.temperature}°C</p>
                    <p>Humidity: {d.humidity}%</p>
                  </div>
                );
              }}
            />
            <Bar dataKey="precipitation" radius={[4, 4, 0, 0]}>
              {forecastData.map((entry, idx) => (
                <Cell key={idx} fill={entry.riskColor} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Hourly detail rows */}
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {forecastData.slice(0, 8).map((h) => (
            <div
              key={h.hour}
              className="flex items-center gap-2 px-2 py-1.5 rounded-md border text-xs"
            >
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: h.riskColor }}
              />
              <span className="font-medium">{h.hour}</span>
              <span className="ml-auto text-muted-foreground">
                {h.precipitation.toFixed(1)}mm · {h.temperature}°C
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
});
