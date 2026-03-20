/**
 * FloodTrendPanel Component
 *
 * Tabbed panel showing flood trend analytics:
 * - Seasonal: area chart of monthly rainfall vs flood events
 * - Correlation: scatter chart of rainfall → flood probability
 * - Radar: seasonal risk radar chart
 *
 * Includes an insight callout highlighting a key takeaway.
 */

import { Lightbulb, TrendingUp } from "lucide-react";
import { memo, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useFloodHistory } from "../hooks/useAnalytics";
import type { FloodHistoryData } from "../types";

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

type Tab = "seasonal" | "correlation" | "radar";

const TABS: { value: Tab; label: string }[] = [
  { value: "seasonal", label: "Seasonal" },
  { value: "correlation", label: "Correlation" },
  { value: "radar", label: "Radar" },
];

// ---------------------------------------------------------------------------
// Recharts tooltip style
// ---------------------------------------------------------------------------

const tooltipStyle = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: 12,
};

// ---------------------------------------------------------------------------
// SeasonalChart
// ---------------------------------------------------------------------------

function SeasonalChart({ data }: { data: FloodHistoryData["monthly"] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart
        data={data}
        margin={{ top: 5, right: 10, bottom: 5, left: -10 }}
      >
        <defs>
          <linearGradient id="rain-grad" x1="0" y1="0" x2="0" y2="1">
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
          <linearGradient id="events-grad" x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="5%"
              stopColor="hsl(var(--destructive))"
              stopOpacity={0.3}
            />
            <stop
              offset="95%"
              stopColor="hsl(var(--destructive))"
              stopOpacity={0}
            />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="month" tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip contentStyle={tooltipStyle} />
        <Area
          type="monotone"
          dataKey="rain"
          stroke="hsl(var(--primary))"
          fill="url(#rain-grad)"
          strokeWidth={2}
          name="Rainfall (mm)"
        />
        <Area
          type="monotone"
          dataKey="events"
          stroke="hsl(var(--destructive))"
          fill="url(#events-grad)"
          strokeWidth={2}
          name="Flood Events"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------------------
// CorrelationChart
// ---------------------------------------------------------------------------

function CorrelationChart({ data }: { data: FloodHistoryData["monthly"] }) {
  // Derive scatter data from monthly: each month → {rain, flood events}
  const points = data.map((m) => ({ rain: m.rain, flood: m.events }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          type="number"
          dataKey="rain"
          name="Rainfall (mm)"
          tick={{ fontSize: 11 }}
          unit=" mm"
        />
        <YAxis
          type="number"
          dataKey="flood"
          name="Flood Events"
          tick={{ fontSize: 11 }}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ strokeDasharray: "3 3" }}
        />
        <Scatter
          data={points}
          fill="hsl(var(--primary))"
          fillOpacity={0.7}
          r={5}
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------------------
// RadarRiskChart
// ---------------------------------------------------------------------------

function RadarRiskChart({ data }: { data: FloodHistoryData["monthly"] }) {
  // Group months into seasons
  const seasons = useMemo(() => {
    const groups: Record<string, number> = {
      "Dec-Feb": 0,
      "Mar-May": 0,
      "Jun-Aug": 0,
      "Sep-Nov": 0,
    };
    const monthToSeason: Record<string, string> = {
      Jan: "Dec-Feb",
      Feb: "Dec-Feb",
      Mar: "Mar-May",
      Apr: "Mar-May",
      May: "Mar-May",
      Jun: "Jun-Aug",
      Jul: "Jun-Aug",
      Aug: "Jun-Aug",
      Sep: "Sep-Nov",
      Oct: "Sep-Nov",
      Nov: "Sep-Nov",
      Dec: "Dec-Feb",
    };
    for (const m of data) {
      const s = monthToSeason[m.month];
      if (s) groups[s] = (groups[s] ?? 0) + m.events;
    }
    const maxVal = Math.max(...Object.values(groups), 1);
    return Object.entries(groups).map(([season, events]) => ({
      season,
      risk: Math.round((events / maxVal) * 100),
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <RadarChart data={seasons} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid className="stroke-muted" />
        <PolarAngleAxis dataKey="season" tick={{ fontSize: 11 }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9 }} />
        <Radar
          dataKey="risk"
          stroke="hsl(var(--primary))"
          fill="hsl(var(--primary))"
          fillOpacity={0.25}
          strokeWidth={2}
          name="Risk Score"
        />
        <Tooltip contentStyle={tooltipStyle} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------------------
// FloodTrendPanel
// ---------------------------------------------------------------------------

export const FloodTrendPanel = memo(function FloodTrendPanel({
  className,
}: {
  className?: string;
}) {
  const { data, isLoading } = useFloodHistory();
  const [tab, setTab] = useState<Tab>("seasonal");

  // Derive insight from data
  const insight = useMemo(() => {
    if (!data) return null;
    const peakMonth = [...data.monthly].sort((a, b) => b.events - a.events)[0];
    if (!peakMonth) return null;
    return `Peak flooding occurs in ${peakMonth.month} with ${peakMonth.events} recorded events and ${peakMonth.rain} mm average rainfall.`;
  }, [data]);

  if (isLoading || !data) {
    return <FloodTrendPanelSkeleton className={className} />;
  }

  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-risk-safe/60 via-teal-400 to-risk-safe/60" />

      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b border-border">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-risk-safe/10 flex items-center justify-center ring-4 ring-risk-safe/20">
            <TrendingUp className="h-4 w-4 text-risk-safe" />
          </div>
          Flood Trend Analysis
        </CardTitle>
        <div className="flex items-center gap-1.5">
          {TABS.map((t) => (
            <Button
              key={t.value}
              variant={tab === t.value ? "default" : "ghost"}
              size="sm"
              onClick={() => setTab(t.value)}
              className={cn(
                "h-6 px-2 text-[10px] font-mono uppercase tracking-wider",
                tab !== t.value && "text-muted-foreground",
              )}
            >
              {t.label}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Insight callout */}
        {insight && (
          <div className="flex items-start gap-2.5 rounded-lg border border-risk-safe/30 bg-risk-safe/5 p-3">
            <Lightbulb className="h-4 w-4 text-risk-safe shrink-0 mt-0.5" />
            <p className="text-xs text-risk-safe/80 leading-relaxed">
              {insight}
            </p>
          </div>
        )}

        {/* Tab content */}
        {tab === "seasonal" && <SeasonalChart data={data.monthly} />}
        {tab === "correlation" && <CorrelationChart data={data.monthly} />}
        {tab === "radar" && <RadarRiskChart data={data.monthly} />}
      </CardContent>
    </GlassCard>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function FloodTrendPanelSkeleton({ className }: { className?: string }) {
  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-muted/60 via-muted to-muted/60" />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b border-border">
        <Skeleton className="h-5 w-40" />
        <div className="flex gap-1.5">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-16 rounded" />
          ))}
        </div>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        <Skeleton className="h-12 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </CardContent>
    </GlassCard>
  );
}

export default FloodTrendPanel;
