/**
 * EvacuationPanel Component
 *
 * Collapsible side panel showing evacuation center capacity dashboard,
 * "Find Nearest" functionality, and center cards with occupancy bars.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { EvacuationCenter } from "@/types";
import {
  ChevronLeft,
  ChevronRight,
  LifeBuoy,
  Loader2,
  MapPin,
  Navigation,
} from "lucide-react";
import { memo, useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  useEvacuationCenters,
  useNearestCenters,
} from "../hooks/useEvacuationCenters";

// ---------------------------------------------------------------------------
// Helper: occupancy badge variant
// ---------------------------------------------------------------------------

function occupancyVariant(
  pct: number,
): "default" | "secondary" | "destructive" | "outline" {
  if (pct >= 90) return "destructive";
  if (pct >= 70) return "secondary";
  return "default";
}

function occupancyLabel(pct: number): string {
  if (pct >= 90) return "Full";
  if (pct >= 70) return "Busy";
  return "Available";
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface EvacuationPanelProps {
  /** Callback when user clicks a center to navigate to it */
  onCenterSelect?: (center: EvacuationCenter) => void;
  /** Callback when user wants a route to a specific center */
  onRouteRequest?: (center: EvacuationCenter) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const EvacuationPanel = memo(function EvacuationPanel({
  onCenterSelect,
  onRouteRequest,
}: EvacuationPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [userLocation, setUserLocation] = useState<{
    lat: number;
    lon: number;
  } | null>(null);

  const { data: allCenters = [], isLoading } = useEvacuationCenters({
    active_only: true,
  });
  const { data: nearestResults, isFetching: findingNearest } =
    useNearestCenters(userLocation?.lat, userLocation?.lon, 3);

  // Summary stats
  const stats = useMemo(() => {
    const total = allCenters.length;
    const totalCapacity = allCenters.reduce(
      (sum, c) => sum + c.capacity_total,
      0,
    );
    const totalOccupied = allCenters.reduce(
      (sum, c) => sum + c.capacity_current,
      0,
    );
    const avgOccupancy = totalCapacity
      ? Math.round((totalOccupied / totalCapacity) * 100)
      : 0;
    const available = allCenters.filter((c) => c.occupancy_pct < 90).length;

    return { total, totalCapacity, totalOccupied, avgOccupancy, available };
  }, [allCenters]);

  // Find nearest handler
  const handleFindNearest = useCallback(() => {
    if (!navigator.geolocation) {
      toast.error("Geolocation not supported by your browser");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        });
      },
      () => {
        toast.error("Unable to get your location");
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }, []);

  if (collapsed) {
    return (
      <button
        type="button"
        className="absolute right-0 top-1/2 -translate-y-1/2 z-1000 rounded-l-lg bg-white/90 dark:bg-gray-900/90 backdrop-blur-md shadow-lg p-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        onClick={() => setCollapsed(false)}
      >
        <ChevronLeft className="h-5 w-5" />
      </button>
    );
  }

  return (
    <div className="absolute right-0 top-0 z-1000 h-full w-80 overflow-y-auto bg-white/95 dark:bg-gray-900/95 backdrop-blur-md shadow-xl border-l border-gray-200 dark:border-gray-800">
      {/* Header */}
      <div className="sticky top-0 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <LifeBuoy className="h-5 w-5 text-risk-safe" />
          <h3 className="font-semibold text-sm">Evacuation Centers</h3>
        </div>
        <button
          type="button"
          className="text-gray-400 hover:text-gray-600 transition-colors"
          onClick={() => setCollapsed(true)}
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-risk-safe/10 dark:bg-risk-safe/15 p-2">
            <p className="text-lg font-bold text-risk-safe">
              {stats.available}
            </p>
            <p className="text-[10px] text-gray-500">Available</p>
          </div>
          <div className="rounded-lg bg-blue-50 dark:bg-blue-950/30 p-2">
            <p className="text-lg font-bold text-blue-700 dark:text-blue-400">
              {stats.total}
            </p>
            <p className="text-[10px] text-gray-500">Total</p>
          </div>
          <div className="rounded-lg bg-risk-alert/10 dark:bg-risk-alert/15 p-2">
            <p className="text-lg font-bold text-risk-alert">
              {stats.avgOccupancy}%
            </p>
            <p className="text-[10px] text-gray-500">Avg. Load</p>
          </div>
        </div>

        {/* Find Nearest button */}
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={handleFindNearest}
          disabled={findingNearest}
        >
          {findingNearest ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Navigation className="h-4 w-4 mr-2" />
          )}
          Find Nearest Center
        </Button>

        {/* Nearest results */}
        {nearestResults && nearestResults.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Nearest to You
            </p>
            {nearestResults.map((r) => (
              <div
                key={`nearest-${r.center.id}`}
                className="rounded-lg border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-950/20 p-3 space-y-1.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium">{r.center.name}</p>
                  <Badge variant="outline" className="text-[10px] shrink-0">
                    {r.distance_km.toFixed(1)} km
                  </Badge>
                </div>
                <p className="text-xs text-gray-500">
                  {r.available_slots} slots available ({r.occupancy_pct}% full)
                </p>
                <div className="flex gap-2">
                  {onRouteRequest && (
                    <Button
                      variant="default"
                      size="sm"
                      className="flex-1 h-7 text-xs"
                      onClick={() => onRouteRequest(r.center)}
                    >
                      Get Route
                    </Button>
                  )}
                  <a
                    href={r.google_maps_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1"
                  >
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full h-7 text-xs"
                    >
                      Google Maps
                    </Button>
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* All centers */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            All Centers
          </p>

          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          )}

          {allCenters.map((c) => (
            <button
              key={`panel-center-${c.id}`}
              type="button"
              className="w-full text-left rounded-lg border border-gray-200 dark:border-gray-800 p-3 space-y-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              onClick={() => onCenterSelect?.(c)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-risk-safe shrink-0" />
                  <p className="text-sm font-medium leading-tight">{c.name}</p>
                </div>
                <Badge
                  variant={occupancyVariant(c.occupancy_pct)}
                  className="text-[10px] shrink-0"
                >
                  {occupancyLabel(c.occupancy_pct)}
                </Badge>
              </div>

              {/* Capacity bar */}
              <div className="space-y-0.5">
                <div className="flex justify-between text-[10px] text-gray-500">
                  <span>
                    {c.capacity_current}/{c.capacity_total}
                  </span>
                  <span>{c.occupancy_pct}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(c.occupancy_pct, 100)}%`,
                      backgroundColor:
                        c.occupancy_pct >= 90
                          ? "hsl(var(--risk-critical))"
                          : c.occupancy_pct >= 70
                            ? "hsl(var(--risk-alert))"
                            : "hsl(var(--risk-safe))",
                    }}
                  />
                </div>
              </div>

              <p className="text-[10px] text-gray-400">{c.barangay}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
});

export default EvacuationPanel;
