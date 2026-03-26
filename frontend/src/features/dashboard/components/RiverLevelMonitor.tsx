/**
 * RiverLevelMonitor - River/Water Level Monitoring Panel
 *
 * Left: SVG gauge showing current water level
 * Right: Level progress bar, threshold references, headroom card
 * Bottom: 24h water level trend line chart
 */

import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltip } from "@/components/ui/chart-tooltip";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { SvgGauge } from "@/components/ui/svg-gauge";
import { cn } from "@/lib/utils";
import { Waves } from "lucide-react";
import { memo, useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useRiverLevel } from "../hooks/useRiverLevel";
import type { RiverReading } from "../types";

// ─── Helpers ────────────────────────────────────────────────────────────────

function levelStatus(value: number, alarm: number, critical: number) {
  if (value >= critical)
    return { label: "Critical", cls: "text-risk-critical bg-risk-critical/15" };
  if (value >= alarm)
    return { label: "Alert", cls: "text-risk-alert bg-risk-alert/15" };
  return { label: "Normal", cls: "text-risk-safe bg-risk-safe/15" };
}

// ─── Main Component ─────────────────────────────────────────────────────────

export const RiverLevelMonitor = memo(function RiverLevelMonitor({
  className,
}: {
  className?: string;
}) {
  const { data: readings, isLoading } = useRiverLevel();

  const latest = useMemo<RiverReading | null>(() => {
    if (!readings?.length) return null;
    return (
      [...readings].sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      )[0] ?? null
    );
  }, [readings]);

  const chartData = useMemo(() => {
    if (!readings?.length) return [];
    return [...readings]
      .sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      )
      .map((r) => ({
        time: new Date(r.timestamp).toLocaleTimeString("en-PH", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        level: r.water_level,
      }));
  }, [readings]);

  if (isLoading) return <RiverLevelMonitorSkeleton className={className} />;

  if (!latest) {
    return (
      <GlassCard className={cn("overflow-hidden", className)}>
        <div className="h-1 w-full bg-linear-to-r from-cyan-500 via-teal-400 to-emerald-400" />
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Waves className="h-4 w-4 text-cyan-500" />
            River Level Monitor
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            No station data available
          </div>
        </CardContent>
      </GlassCard>
    );
  }

  const status = levelStatus(
    latest.water_level,
    latest.alarm_level,
    latest.critical_level,
  );
  const headroom = Math.max(0, latest.critical_level - latest.water_level);
  const progressPct = Math.min(
    100,
    (latest.water_level / latest.critical_level) * 100,
  );

  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-cyan-500 via-teal-400 to-emerald-400" />
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Waves className="h-4 w-4 text-cyan-500" />
          River Level Monitor
          <span
            className={cn(
              "ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold",
              status.cls,
            )}
          >
            {status.label}
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Gauge + Stats */}
        <div className="flex items-center gap-6">
          <SvgGauge
            value={latest.water_level}
            max={latest.critical_level * 1.2}
            warnThreshold={latest.alarm_level}
            dangerThreshold={latest.critical_level}
            unit="m"
            label="Water Level"
            size={140}
          />

          <div className="flex-1 space-y-3">
            {/* Progress bar */}
            <div>
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Current: {latest.water_level.toFixed(2)} m</span>
                <span>Critical: {latest.critical_level.toFixed(2)} m</span>
              </div>
              <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-700",
                    latest.water_level >= latest.critical_level
                      ? "bg-risk-critical"
                      : latest.water_level >= latest.alarm_level
                        ? "bg-risk-alert"
                        : "bg-risk-safe",
                  )}
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>

            {/* Thresholds */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-md bg-risk-alert/10 px-2 py-1.5 text-center">
                <span className="text-muted-foreground">Alert</span>
                <p className="font-bold font-mono text-risk-alert">
                  {latest.alarm_level.toFixed(2)} m
                </p>
              </div>
              <div className="rounded-md bg-risk-critical/10 px-2 py-1.5 text-center">
                <span className="text-muted-foreground">Critical</span>
                <p className="font-bold font-mono text-risk-critical">
                  {latest.critical_level.toFixed(2)} m
                </p>
              </div>
            </div>

            {/* Headroom */}
            <div className="rounded-md bg-muted/50 px-3 py-2 text-center">
              <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Headroom to Critical
              </span>
              <p className="text-lg font-bold font-mono text-foreground">
                {headroom.toFixed(2)} m
              </p>
            </div>
          </div>
        </div>

        {/* 24h trend chart */}
        {chartData.length > 1 ? (
          <div className="h-36">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 5, right: 5, bottom: 0, left: -20 }}
              >
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
                  unit=" m"
                />
                <Tooltip content={<ChartTooltip unit=" m" />} />
                <ReferenceLine
                  y={latest.critical_level}
                  stroke="hsl(var(--destructive))"
                  strokeDasharray="4 4"
                />
                <ReferenceLine
                  y={latest.alarm_level}
                  stroke="hsl(var(--chart-4))"
                  strokeDasharray="4 4"
                />
                <Line
                  type="monotone"
                  dataKey="level"
                  name="Water Level"
                  stroke="hsl(var(--chart-3))"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : null}
      </CardContent>
    </GlassCard>
  );
});

// ─── Skeleton ───────────────────────────────────────────────────────────────

export function RiverLevelMonitorSkeleton({
  className,
}: {
  className?: string;
}) {
  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-cyan-500/50 via-teal-400/50 to-emerald-400/50" />
      <CardHeader className="pb-2">
        <Skeleton className="h-5 w-44" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-6">
          <Skeleton className="h-35 w-35 rounded-full" />
          <div className="flex-1 space-y-3">
            <Skeleton className="h-2 w-full rounded-full" />
            <div className="grid grid-cols-2 gap-2">
              <Skeleton className="h-12 rounded-md" />
              <Skeleton className="h-12 rounded-md" />
            </div>
            <Skeleton className="h-14 rounded-md" />
          </div>
        </div>
        <Skeleton className="h-36 rounded-lg" />
      </CardContent>
    </GlassCard>
  );
}
