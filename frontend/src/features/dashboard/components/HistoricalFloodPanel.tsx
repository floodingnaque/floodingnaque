/**
 * HistoricalFloodPanel Component
 *
 * Tabbed panel showing historical flood data from DRRMO records:
 * - Frequency: horizontal bar chart of events per barangay
 * - Yearly: composed bar+line chart showing events & rainfall over years
 * - Events: scrollable table of recent flood events
 *
 * Includes a summary stat strip at the top.
 */

import {
  BarChart3,
  Calendar,
  Droplets,
  ListOrdered,
  MapPin,
} from "lucide-react";
import { memo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
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

type Tab = "frequency" | "yearly" | "events";

const TABS: { value: Tab; label: string }[] = [
  { value: "frequency", label: "By Barangay" },
  { value: "yearly", label: "Year Trend" },
  { value: "events", label: "Recent Events" },
];

// ---------------------------------------------------------------------------
// Depth badge color
// ---------------------------------------------------------------------------

function depthVariant(
  depth: string,
): "default" | "secondary" | "destructive" | "outline" {
  const lower = depth.toLowerCase();
  if (
    lower.includes("waist") ||
    lower.includes("chest") ||
    lower.includes("neck")
  )
    return "destructive";
  if (lower.includes("knee")) return "default";
  return "secondary";
}

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
// FrequencyChart
// ---------------------------------------------------------------------------

function FrequencyChart({ data }: { data: FloodHistoryData["frequency"] }) {
  const sorted = [...data].sort((a, b) => b.events - a.events);
  const max = Math.max(...sorted.map((d) => d.events), 1);

  return (
    <ResponsiveContainer
      width="100%"
      height={Math.max(sorted.length * 28, 200)}
    >
      <BarChart
        data={sorted}
        layout="vertical"
        margin={{ top: 0, right: 10, bottom: 0, left: 0 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          className="stroke-muted"
          horizontal={false}
        />
        <XAxis type="number" tick={{ fontSize: 10 }} />
        <YAxis
          type="category"
          dataKey="barangay"
          width={120}
          tick={{ fontSize: 10 }}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar dataKey="events" radius={[0, 4, 4, 0]} maxBarSize={18}>
          {sorted.map((d, i) => (
            <Cell
              key={i}
              fill={
                d.events / max > 0.66
                  ? "hsl(var(--destructive))"
                  : d.events / max > 0.33
                    ? "hsl(var(--warning, 38 92% 50%))"
                    : "hsl(var(--primary))"
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------------------
// YearlyChart
// ---------------------------------------------------------------------------

function YearlyChart({ data }: { data: FloodHistoryData["yearly"] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart
        data={data}
        margin={{ top: 5, right: 10, bottom: 5, left: -10 }}
      >
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
        <YAxis
          yAxisId="right"
          orientation="right"
          tick={{ fontSize: 11 }}
          unit=" mm"
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar
          yAxisId="left"
          dataKey="events"
          fill="hsl(var(--primary))"
          radius={[4, 4, 0, 0]}
          maxBarSize={40}
          name="Flood Events"
        />
        <Line
          yAxisId="right"
          dataKey="rain"
          stroke="hsl(var(--destructive))"
          strokeWidth={2}
          dot={{ r: 3 }}
          name="Avg Rainfall (mm)"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------------------
// EventsTable
// ---------------------------------------------------------------------------

function EventsTable({ data }: { data: FloodHistoryData["recentEvents"] }) {
  return (
    <div className="overflow-auto max-h-80 rounded-lg border border-border">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-muted/80 backdrop-blur-sm">
          <tr className="text-left text-muted-foreground font-mono uppercase tracking-wider">
            <th className="p-2">Date</th>
            <th className="p-2">Barangay</th>
            <th className="p-2">Depth</th>
            <th className="p-2">Disturbance</th>
            <th className="p-2">Duration</th>
          </tr>
        </thead>
        <tbody>
          {data.map((e) => (
            <tr
              key={e.id}
              className="border-t border-border hover:bg-muted/40 transition-colors"
            >
              <td className="p-2 font-mono text-muted-foreground">{e.date}</td>
              <td className="p-2 flex items-center gap-1">
                <MapPin className="h-3 w-3 text-muted-foreground shrink-0" />
                {e.barangay}
              </td>
              <td className="p-2">
                <Badge variant={depthVariant(e.depth)} className="text-[10px]">
                  {e.depth}
                </Badge>
              </td>
              <td className="p-2">
                <Badge variant="outline" className="text-[10px]">
                  {e.disturbance}
                </Badge>
              </td>
              <td className="p-2 font-mono">{e.duration}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// HistoricalFloodPanel
// ---------------------------------------------------------------------------

export const HistoricalFloodPanel = memo(function HistoricalFloodPanel({
  className,
}: {
  className?: string;
}) {
  const { data, isLoading } = useFloodHistory();
  const [tab, setTab] = useState<Tab>("frequency");

  if (isLoading || !data) {
    return <HistoricalFloodPanelSkeleton className={className} />;
  }

  const { summary } = data;

  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-blue-500/60 via-cyan-400 to-blue-500/60" />

      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b border-border">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-blue-500/10 flex items-center justify-center ring-4 ring-blue-500/20">
            <BarChart3 className="h-4 w-4 text-blue-500" />
          </div>
          Historical Flood Data
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
        {/* Summary strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {[
            {
              icon: ListOrdered,
              label: "Total Events",
              value: summary.totalEvents,
            },
            {
              icon: MapPin,
              label: "Barangays Hit",
              value: summary.barangaysHit,
            },
            { icon: Droplets, label: "Worst Month", value: summary.worstMonth },
            {
              icon: Calendar,
              label: "Most Affected",
              value: summary.mostAffected,
            },
          ].map(({ icon: Icon, label, value }) => (
            <div
              key={label}
              className="rounded-lg bg-muted border border-border p-2.5"
            >
              <div className="flex items-center gap-1.5 mb-1">
                <Icon className="h-3 w-3 text-muted-foreground" />
                <p className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground">
                  {label}
                </p>
              </div>
              <p className="text-sm font-bold font-mono truncate">{value}</p>
            </div>
          ))}
        </div>

        {/* Tab content */}
        {tab === "frequency" && (
          <div className="overflow-y-auto max-h-80">
            <FrequencyChart data={data.frequency} />
          </div>
        )}
        {tab === "yearly" && <YearlyChart data={data.yearly} />}
        {tab === "events" && <EventsTable data={data.recentEvents} />}
      </CardContent>
    </GlassCard>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function HistoricalFloodPanelSkeleton({
  className,
}: {
  className?: string;
}) {
  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-muted/60 via-muted to-muted/60" />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b border-border">
        <Skeleton className="h-5 w-44" />
        <div className="flex gap-1.5">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-16 rounded" />
          ))}
        </div>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-lg" />
      </CardContent>
    </GlassCard>
  );
}

export default HistoricalFloodPanel;
