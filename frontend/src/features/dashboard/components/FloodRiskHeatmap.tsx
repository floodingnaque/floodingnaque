/**
 * FloodRiskHeatmap
 *
 * Treemap-style 4×4 heatmap grid showing per-barangay flood risk or event frequency.
 * Wired to useFloodHistory() for frequency data and BARANGAYS for canonical names.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BARANGAYS } from "@/config/paranaque";
import { cn } from "@/lib/utils";
import { ArrowDown, ArrowUp, Grid3X3, Minus } from "lucide-react";
import { memo, useMemo, useState } from "react";
import { useFloodHistory } from "../hooks/useAnalytics";
import type { HeatmapCell } from "../types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type ViewMode = "risk" | "frequency";

/** Map a 0–1 risk score to a Tailwind bg class */
function riskBg(score: number): string {
  if (score >= 0.7) return "bg-risk-critical/80 text-white";
  if (score >= 0.4) return "bg-risk-alert/70 text-foreground";
  return "bg-risk-safe/60 text-foreground";
}

/** Map a frequency count relative to max → 0..1 */
function normalize(value: number, max: number): number {
  return max === 0 ? 0 : value / max;
}

// ---------------------------------------------------------------------------
// Cell component
// ---------------------------------------------------------------------------

function HeatCell({
  cell,
  mode,
  maxFreq,
}: {
  cell: HeatmapCell;
  mode: ViewMode;
  maxFreq: number;
}) {
  const score = mode === "risk" ? cell.risk : normalize(cell.freq, maxFreq);
  const TrendIcon =
    cell.trend > 0 ? ArrowUp : cell.trend < 0 ? ArrowDown : Minus;
  const trendColor =
    cell.trend > 0
      ? "text-risk-critical"
      : cell.trend < 0
        ? "text-risk-safe"
        : "text-muted-foreground";

  return (
    <div
      className={cn(
        "relative rounded-md p-2 flex flex-col justify-between aspect-square transition-colors",
        riskBg(score),
      )}
    >
      <span className="text-[10px] font-mono font-bold leading-tight line-clamp-2">
        {cell.name}
      </span>
      <div className="flex items-end justify-between">
        <span className="text-lg font-bold font-mono leading-none">
          {mode === "risk" ? `${Math.round(cell.risk * 100)}%` : cell.freq}
        </span>
        <TrendIcon className={cn("h-3 w-3", trendColor)} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Legend bar
// ---------------------------------------------------------------------------

function GradientLegend({ mode }: { mode: ViewMode }) {
  return (
    <div className="flex items-center gap-2 mt-3">
      <span className="text-[9px] text-muted-foreground font-mono uppercase">
        {mode === "risk" ? "Low Risk" : "Few Events"}
      </span>
      <div className="flex-1 h-2 rounded-full bg-linear-to-r from-risk-safe via-risk-alert to-risk-critical" />
      <span className="text-[9px] text-muted-foreground font-mono uppercase">
        {mode === "risk" ? "High Risk" : "Many Events"}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const FloodRiskHeatmap = memo(function FloodRiskHeatmap() {
  const [mode, setMode] = useState<ViewMode>("risk");
  const { data, isLoading } = useFloodHistory();

  const { cells, maxFreq } = useMemo(() => {
    const freqMap = new Map<string, number>();
    for (const item of data?.frequency ?? []) {
      freqMap.set(item.barangay, item.events);
    }

    const max = Math.max(1, ...Array.from(freqMap.values()));

    const result: HeatmapCell[] = BARANGAYS.map((b) => {
      const freq = freqMap.get(b.name) ?? 0;
      return {
        name: b.name,
        risk: normalize(freq, max), // derive risk from relative frequency
        freq,
        trend: 0, // could be computed from yearly data later
      };
    });

    // Sort descending by the active metric
    result.sort((a, b) =>
      mode === "risk" ? b.risk - a.risk : b.freq - a.freq,
    );

    return { cells: result, maxFreq: max };
  }, [data, mode]);

  if (isLoading) return <FloodRiskHeatmapSkeleton />;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-bold font-mono tracking-wide">
          <Grid3X3 className="h-4 w-4" />
          Flood Risk Heatmap
        </CardTitle>
        <div className="flex gap-1">
          {(["risk", "frequency"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={cn(
                "rounded-md border px-2.5 py-1 text-[10px] font-mono transition-colors",
                mode === m
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-muted text-muted-foreground hover:bg-accent/50",
              )}
            >
              {m === "risk" ? "Risk Score" : "Event Freq."}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        {cells.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground font-mono">
            No flood history data available.
          </div>
        ) : (
          <>
            <div className="grid grid-cols-4 gap-1.5">
              {cells.map((c) => (
                <HeatCell key={c.name} cell={c} mode={mode} maxFreq={maxFreq} />
              ))}
            </div>

            <GradientLegend mode={mode} />

            <div className="flex items-center justify-between mt-3 text-[9px] text-muted-foreground font-mono">
              <span>
                {cells.length} barangays ·{" "}
                {cells.filter((c) => c.risk >= 0.7).length} critical
              </span>
              <Badge
                variant="outline"
                className="text-[9px] px-1.5 py-0 font-mono"
              >
                Last 3 years
              </Badge>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function FloodRiskHeatmapSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-44" />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-1.5">
          {Array.from({ length: 16 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square rounded-md" />
          ))}
        </div>
        <Skeleton className="h-2 w-full mt-3" />
      </CardContent>
    </Card>
  );
}
