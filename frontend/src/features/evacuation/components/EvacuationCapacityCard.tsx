/**
 * EvacuationCapacityCard
 *
 * Displays evacuation center capacity status with visual fill bars
 * and "Almost Full" / "Full" badges.  Designed for the resident
 * dashboard to provide at-a-glance capacity awareness.
 */

import { AlertTriangle, Building, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvacuationCenters } from "@/features/evacuation";
import { cn } from "@/lib/cn";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CapacityCenter {
  name: string;
  barangay: string;
  capacity_total: number;
  capacity_current: number;
  available_slots: number;
  occupancy_pct: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getCapacityColor(pct: number): string {
  if (pct >= 90) return "bg-risk-critical";
  if (pct >= 70) return "bg-risk-alert";
  return "bg-risk-safe";
}

function getCapacityBadge(pct: number) {
  if (pct >= 95)
    return (
      <Badge variant="destructive" className="ml-2 text-xs">
        Full
      </Badge>
    );
  if (pct >= 80)
    return (
      <Badge className="ml-2 bg-risk-alert/15 text-risk-alert text-xs hover:bg-risk-alert/25">
        Almost Full
      </Badge>
    );
  return null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface EvacuationCapacityCardProps {
  className?: string;
  /** Maximum number of centers to display */
  limit?: number;
}

export function EvacuationCapacityCard({
  className,
  limit = 5,
}: EvacuationCapacityCardProps) {
  const { data, isLoading, isError } = useEvacuationCenters();

  if (isLoading) return <EvacuationCapacityCardSkeleton />;

  const allCenters: CapacityCenter[] =
    (data as unknown as { centers?: CapacityCenter[] })?.centers ?? [];
  const centers = allCenters.slice(0, limit);

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Building className="h-4 w-4" />
          Evacuation Centers
        </CardTitle>
        <CardDescription>Real-time capacity status</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isError && (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4" />
            Failed to load centers
          </div>
        )}

        {centers.length === 0 && !isError && (
          <p className="text-sm text-muted-foreground">
            No active evacuation centers
          </p>
        )}

        {centers.map((center) => (
          <div key={center.name} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium truncate max-w-50">
                {center.name}
                {getCapacityBadge(center.occupancy_pct)}
              </span>
              <span className="flex items-center gap-1 text-muted-foreground">
                <Users className="h-3 w-3" />
                {center.capacity_current}/{center.capacity_total}
              </span>
            </div>
            {/* Capacity fill bar */}
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  getCapacityColor(center.occupancy_pct),
                )}
                style={{ width: `${Math.min(center.occupancy_pct, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function EvacuationCapacityCardSkeleton() {
  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-1">
            <div className="flex justify-between">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-16" />
            </div>
            <Skeleton className="h-2 w-full rounded-full" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
