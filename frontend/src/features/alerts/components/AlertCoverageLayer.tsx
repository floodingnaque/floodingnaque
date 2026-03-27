/**
 * AlertCoverageLayer – displays per-barangay alert delivery coverage
 * as a colour-coded overlay on the map.
 *
 * Green = high delivery rate, amber = moderate, red = low delivery rate.
 * Requires the /api/v1/alerts/coverage endpoint.
 */

import { cn } from "@/lib/cn";
import { useMemo } from "react";
import { useAlertCoverage } from "../hooks/useAlertCoverage";

// ── Component ───────────────────────────────────────────────────────────

function getDeliveryColor(pct: number): string {
  if (pct >= 80) return "bg-emerald-500/60 border-emerald-600";
  if (pct >= 50) return "bg-amber-500/60 border-amber-600";
  return "bg-red-500/60 border-red-600";
}

function getDeliveryLabel(pct: number): string {
  if (pct >= 80) return "Good";
  if (pct >= 50) return "Moderate";
  return "Low";
}

interface AlertCoverageLayerProps {
  hours?: number;
  className?: string;
}

export function AlertCoverageLayer({
  hours = 24,
  className,
}: AlertCoverageLayerProps) {
  const { data, isLoading } = useAlertCoverage(hours);

  const sortedBarangays = useMemo(() => {
    if (!data?.barangays) return [];
    return Object.entries(data.barangays)
      .map(([name, stats]) => ({ name, ...stats }))
      .sort((a, b) => a.delivery_pct - b.delivery_pct);
  }, [data]);

  if (isLoading) {
    return (
      <div className={cn("space-y-2 animate-pulse", className)}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 bg-muted rounded" />
        ))}
      </div>
    );
  }

  if (!data || sortedBarangays.length === 0) {
    return (
      <div
        className={cn(
          "text-sm text-muted-foreground text-center py-4",
          className,
        )}
      >
        No alert coverage data available for the last {hours}h.
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total Alerts" value={data.coverage.total_alerts} />
        <StatCard
          label="Delivery Rate"
          value={`${data.coverage.delivery_rate_pct}%`}
        />
        <StatCard
          label="Median Delivery"
          value={
            data.coverage.median_delivery_seconds != null
              ? `${data.coverage.median_delivery_seconds}s`
              : "N/A"
          }
        />
        <StatCard label="Failed" value={data.coverage.total_failed} />
      </div>

      {/* Channel breakdown */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(data.channels).map(([channel, stats]) => (
          <div
            key={channel}
            className="text-xs border rounded-md px-2 py-1 bg-muted/50"
          >
            <span className="font-medium capitalize">{channel}</span>:{" "}
            {stats.total > 0
              ? Math.round((stats.delivered / stats.total) * 100)
              : 0}
            % delivered
          </div>
        ))}
      </div>

      {/* Per-barangay coverage bars */}
      <div className="space-y-1.5 max-h-80 overflow-y-auto">
        {sortedBarangays.map((b) => (
          <div key={b.name} className="flex items-center gap-2 text-sm">
            <span className="w-36 truncate font-medium">{b.name}</span>
            <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  getDeliveryColor(b.delivery_pct),
                )}
                style={{ width: `${Math.min(b.delivery_pct, 100)}%` }}
              />
            </div>
            <span className="w-10 text-right text-xs font-mono tabular-nums">
              {b.delivery_pct}%
            </span>
            <span
              className={cn(
                "w-16 text-xs text-right",
                b.delivery_pct >= 80
                  ? "text-emerald-600"
                  : b.delivery_pct >= 50
                    ? "text-amber-600"
                    : "text-red-600",
              )}
            >
              {getDeliveryLabel(b.delivery_pct)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{String(value)}</p>
    </div>
  );
}
