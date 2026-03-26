/**
 * WeatherChart Component
 *
 * Interactive line/bar chart displaying weather data over time.
 * Shows temperature, humidity, and precipitation with dual Y-axes.
 * Constrains Y-axes to realistic Parañaque ranges and flags outliers.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { WeatherData } from "@/types";
import { format } from "date-fns";
import { AlertTriangle } from "lucide-react";
import { useMemo } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface WeatherChartProps {
  /** Weather data to display */
  data: WeatherData[];
  /** Loading state */
  isLoading?: boolean;
  /** Chart title */
  title?: string;
}

/**
 * Custom tooltip component for the chart
 */
interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-background border rounded-lg shadow-lg p-3">
      <p className="font-medium text-sm mb-2">{label}</p>
      {payload.map((entry, index) => (
        <p key={index} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {formatValue(entry.dataKey, entry.value)}
        </p>
      ))}
    </div>
  );
}

/**
 * Format values based on the data type
 */
function formatValue(key: string, value: number): string {
  switch (key) {
    case "temperature":
      return `${value.toFixed(1)}°C`;
    case "humidity":
      return `${value.toFixed(1)}%`;
    case "precipitation":
      return `${value.toFixed(2)} mm`;
    default:
      return value.toString();
  }
}

/** Check if a Kelvin temperature is realistic for Parañaque (20–45 °C). */
function isPlausibleTemp(kelvin: number): boolean {
  return kelvin >= 293.15 && kelvin <= 318.15;
}

/**
 * WeatherChart component
 *
 * @example
 * <WeatherChart data={weatherData} isLoading={isLoading} />
 */
const CHART_MARGIN = { top: 20, right: 30, left: 20, bottom: 5 } as const;

export function WeatherChart({
  data,
  isLoading,
  title = "Weather Trends",
}: WeatherChartProps) {
  // Transform data for the chart - filter out extreme outliers
  const { chartData, outlierCount } = useMemo(() => {
    let outliers = 0;
    const filtered = data.filter((item) => {
      if (!isPlausibleTemp(item.temperature)) {
        outliers++;
        return false;
      }
      return true;
    });

    const mapped = filtered.map((item) => ({
      ...item,
      time: format(new Date(item.recorded_at), "MMM dd HH:mm"),
      temperature: item.temperature - 273.15,
    }));

    return { chartData: mapped, outlierCount: outliers };
  }, [data]);

  // Compute precipitation max for right Y-axis domain
  const precipMax = useMemo(() => {
    if (!chartData.length) return 20;
    const max = Math.max(...chartData.map((d) => d.precipitation));
    return Math.max(10, Math.ceil(max / 5) * 5 + 5);
  }, [chartData]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-100 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-100 flex items-center justify-center text-muted-foreground">
            No weather data available for the selected period
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          {outlierCount > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-risk-alert">
              <AlertTriangle className="h-3.5 w-3.5" />
              {outlierCount} outlier{outlierCount > 1 ? "s" : ""} excluded
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={chartData} margin={CHART_MARGIN}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />

            {/* X-Axis with timestamps */}
            <XAxis
              dataKey="time"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
            />

            {/* Left Y-Axis for Temperature (20–40 °C) & Humidity (0–100%) */}
            <YAxis
              yAxisId="left"
              domain={[15, 100]}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
              label={{
                value: "Temp (°C) / Humidity (%)",
                angle: -90,
                position: "insideLeft",
                style: { textAnchor: "middle", fontSize: 12 },
              }}
            />

            {/* Right Y-Axis for Precipitation (mm) */}
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, precipMax]}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
              label={{
                value: "Precipitation (mm)",
                angle: 90,
                position: "insideRight",
                style: { textAnchor: "middle", fontSize: 12 },
              }}
            />

            {/* Tooltip */}
            <Tooltip content={<CustomTooltip />} />

            {/* Legend - click to toggle series visibility */}
            <Legend
              wrapperStyle={{ paddingTop: "20px" }}
              formatter={(value) => <span className="text-sm">{value}</span>}
            />

            {/* Precipitation bars */}
            <Bar
              yAxisId="right"
              dataKey="precipitation"
              name="Precipitation"
              fill="#3b82f6"
              opacity={0.5}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />

            {/* Temperature line */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="temperature"
              name="Temperature"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            />

            {/* Humidity line */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="humidity"
              name="Humidity"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export default WeatherChart;
