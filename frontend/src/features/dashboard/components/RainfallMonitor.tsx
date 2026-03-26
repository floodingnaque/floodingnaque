/**
 * RainfallMonitor - 24-Hour Rainfall Monitoring Panel
 *
 * Metric strip showing current rate, intensity, 3-hr rolling total, and trend,
 * plus a 24-hour area chart with intensity reference lines.
 */

import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltip } from "@/components/ui/chart-tooltip";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { CloudRain, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { memo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useRainfallHistory } from "../hooks/useRainfallHistory";

// ─── Intensity colors ──────────────────────────────────────────────────────

const intensityColor: Record<string, string> = {
  light: "text-risk-safe",
  moderate: "text-risk-alert",
  heavy: "text-risk-critical",
};

const trendIcon: Record<string, React.ElementType> = {
  rising: TrendingUp,
  falling: TrendingDown,
  steady: Minus,
};

// ─── Metric Pill ────────────────────────────────────────────────────────────

function MetricPill({
  label,
  value,
  valueCls,
}: {
  label: string;
  value: string;
  valueCls?: string;
}) {
  return (
    <div className="flex flex-col items-center rounded-lg bg-muted/50 px-3 py-2">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
        {label}
      </span>
      <span className={cn("text-sm font-bold font-mono", valueCls)}>
        {value}
      </span>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export const RainfallMonitor = memo(function RainfallMonitor({
  className,
}: {
  className?: string;
}) {
  const { data, metrics, isLoading } = useRainfallHistory();

  if (isLoading) return <RainfallMonitorSkeleton className={className} />;

  const TrendIcon = trendIcon[metrics.trend] ?? Minus;

  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-blue-500 via-blue-400 to-cyan-400" />
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <CloudRain className="h-4 w-4 text-blue-500" />
          Rainfall Monitor
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Metric strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <MetricPill
            label="Current Rate"
            value={`${metrics.current.toFixed(1)} mm/h`}
            valueCls={intensityColor[metrics.intensity]}
          />
          <MetricPill
            label="Intensity"
            value={
              metrics.intensity.charAt(0).toUpperCase() +
              metrics.intensity.slice(1)
            }
            valueCls={intensityColor[metrics.intensity]}
          />
          <MetricPill
            label="3h Rolling"
            value={`${metrics.rolling3h.toFixed(1)} mm`}
          />
          <MetricPill
            label="Trend"
            value={
              metrics.trend.charAt(0).toUpperCase() + metrics.trend.slice(1)
            }
            valueCls={
              metrics.trend === "rising"
                ? "text-risk-critical"
                : metrics.trend === "falling"
                  ? "text-risk-safe"
                  : undefined
            }
          />
        </div>

        {/* 24h area chart */}
        {data.length > 0 ? (
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data}
                margin={{ top: 5, right: 5, bottom: 0, left: -20 }}
              >
                <defs>
                  <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="5%"
                      stopColor="hsl(var(--primary))"
                      stopOpacity={0.3}
                    />
                    <stop
                      offset="95%"
                      stopColor="hsl(var(--primary))"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  className="stroke-border/30"
                />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 10 }}
                  className="fill-muted-foreground"
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  className="fill-muted-foreground"
                  unit=" mm"
                />
                <Tooltip content={<ChartTooltip unit=" mm" />} />
                <ReferenceLine
                  y={7.5}
                  stroke="hsl(var(--destructive))"
                  strokeDasharray="4 4"
                  label={{ value: "Heavy", position: "right", fontSize: 10 }}
                />
                <ReferenceLine
                  y={2.5}
                  stroke="hsl(var(--chart-4))"
                  strokeDasharray="4 4"
                  label={{ value: "Moderate", position: "right", fontSize: 10 }}
                />
                <Area
                  type="monotone"
                  dataKey="mm"
                  name="Rainfall"
                  stroke="hsl(var(--primary))"
                  fill="url(#rainGrad)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            No rainfall data available
          </div>
        )}

        {/* Trend icon indicator */}
        <div className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
          <TrendIcon className="h-3.5 w-3.5" />
          <span>24-hour trend</span>
        </div>
      </CardContent>
    </GlassCard>
  );
});

// ─── Skeleton ───────────────────────────────────────────────────────────────

export function RainfallMonitorSkeleton({ className }: { className?: string }) {
  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-blue-500/50 via-blue-400/50 to-cyan-400/50" />
      <CardHeader className="pb-2">
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-48 rounded-lg" />
      </CardContent>
    </GlassCard>
  );
}
