/**
 * EvacuationStatusGrid - Filterable Evacuation Center Overview
 *
 * Filter buttons (All/Open/Closed), summary metric cards,
 * and a scrollable list of center cards with capacity bars.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvacuationCenters } from "@/features/evacuation/hooks/useEvacuationCenters";
import { cn } from "@/lib/utils";
import type { EvacuationCenter } from "@/types";
import { Building2, MapPin, Users } from "lucide-react";
import { memo, useMemo, useState } from "react";

// ─── Status helpers ─────────────────────────────────────────────────────────

type FilterMode = "all" | "open" | "closed";

function statusInfo(center: EvacuationCenter) {
  if (!center.is_active)
    return { label: "CLOSED", cls: "bg-muted text-muted-foreground" };
  if (center.occupancy_pct >= 95)
    return { label: "FULL", cls: "bg-risk-critical text-white" };
  if (center.occupancy_pct >= 80)
    return { label: "ALMOST FULL", cls: "bg-risk-alert text-black" };
  return { label: "OPEN", cls: "bg-risk-safe text-white" };
}

// ─── Center Card ────────────────────────────────────────────────────────────

function CenterCard({ center }: { center: EvacuationCenter }) {
  const status = statusInfo(center);
  const pct = Math.min(100, center.occupancy_pct);

  return (
    <div className="rounded-lg border bg-card/50 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground truncate">
            {center.name}
          </p>
          <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
            <MapPin className="h-3 w-3 shrink-0" />
            <span className="truncate">{center.barangay}</span>
          </p>
        </div>
        <Badge className={cn("shrink-0 text-[10px] px-1.5", status.cls)}>
          {status.label}
        </Badge>
      </div>

      {/* Capacity bar */}
      <div>
        <div className="flex justify-between text-[10px] text-muted-foreground mb-0.5">
          <span>
            {center.capacity_current} / {center.capacity_total}
          </span>
          <span className="font-mono">{pct.toFixed(0)}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              pct >= 95
                ? "bg-risk-critical"
                : pct >= 80
                  ? "bg-risk-alert"
                  : "bg-risk-safe",
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Summary Metric ─────────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
}) {
  return (
    <div className="flex flex-col items-center rounded-lg bg-muted/50 px-3 py-2">
      <Icon className="h-4 w-4 text-muted-foreground mb-1" />
      <span className="text-lg font-bold font-mono text-foreground">
        {value}
      </span>
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export const EvacuationStatusGrid = memo(function EvacuationStatusGrid({
  className,
}: {
  className?: string;
}) {
  const { data: centers, isLoading } = useEvacuationCenters();
  const [filter, setFilter] = useState<FilterMode>("all");

  const filtered = useMemo(() => {
    if (!centers) return [];
    if (filter === "open") return centers.filter((c) => c.is_active);
    if (filter === "closed") return centers.filter((c) => !c.is_active);
    return centers;
  }, [centers, filter]);

  const summary = useMemo(() => {
    if (!centers?.length) return { total: 0, occupied: 0, available: 0 };
    const total = centers.reduce((s, c) => s + c.capacity_total, 0);
    const occupied = centers.reduce((s, c) => s + c.capacity_current, 0);
    return { total, occupied, available: Math.max(0, total - occupied) };
  }, [centers]);

  if (isLoading) return <EvacuationStatusGridSkeleton className={className} />;

  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-risk-safe via-risk-safe to-teal-400" />
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Building2 className="h-4 w-4 text-risk-safe" />
            Evacuation Centers
          </CardTitle>
          <div className="flex gap-1">
            {(["all", "open", "closed"] as const).map((mode) => (
              <Button
                key={mode}
                variant={filter === mode ? "default" : "ghost"}
                size="sm"
                className="h-6 px-2 text-[10px]"
                onClick={() => setFilter(mode)}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Summary metrics */}
        <div className="grid grid-cols-3 gap-2">
          <SummaryCard
            icon={Building2}
            label="Total Capacity"
            value={summary.total.toLocaleString()}
          />
          <SummaryCard
            icon={Users}
            label="Occupied"
            value={summary.occupied.toLocaleString()}
          />
          <SummaryCard
            icon={MapPin}
            label="Available"
            value={summary.available.toLocaleString()}
          />
        </div>

        {/* Center list */}
        {filtered.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 max-h-80 overflow-y-auto pr-1">
            {filtered.map((center) => (
              <CenterCard key={center.id} center={center} />
            ))}
          </div>
        ) : (
          <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
            No evacuation centers found
          </div>
        )}
      </CardContent>
    </GlassCard>
  );
});

// ─── Skeleton ───────────────────────────────────────────────────────────────

export function EvacuationStatusGridSkeleton({
  className,
}: {
  className?: string;
}) {
  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-risk-safe/50 via-risk-safe/50 to-teal-400/50" />
      <CardHeader className="pb-2">
        <Skeleton className="h-5 w-44" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      </CardContent>
    </GlassCard>
  );
}
