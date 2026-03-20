/**
 * EvacuationCenterMarkers Component
 *
 * Enhanced evacuation-center markers with real-time capacity
 * progress bars, color-coded by occupancy, and "Get Route" action.
 * Listens for SSE `evacuation_capacity` CustomEvents and patches
 * the TanStack Query cache directly for instant updates.
 */

import type { EvacuationCenter } from "@/types";
import { useQueryClient } from "@tanstack/react-query";
import L from "leaflet";
import { useCallback, useEffect, useMemo } from "react";
import { Marker, Popup, Tooltip } from "react-leaflet";

import { RISK_HEX } from "@/lib/colors";
import {
  evacuationKeys,
  useEvacuationCenters,
} from "../hooks/useEvacuationCenters";

// ---------------------------------------------------------------------------
// Icon helpers
// ---------------------------------------------------------------------------

function occupancyColor(pct: number): string {
  if (pct >= 90) return RISK_HEX.critical;
  if (pct >= 70) return RISK_HEX.alert;
  return RISK_HEX.safe;
}

function createCenterIcon(occupancyPct: number): L.DivIcon {
  const fill = occupancyColor(occupancyPct);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="30" height="45">
      <path fill="${fill}" stroke="#fff" stroke-width="1.5"
        d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24C24 5.37 18.63 0 12 0z"/>
      <path fill="#fff" d="M12 6.5l-5.5 6.5h2.5v4h6v-4h2.5L12 6.5z"/>
    </svg>
  `;
  return L.divIcon({
    html: svg,
    className: "evac-center-marker",
    iconSize: [30, 45],
    iconAnchor: [15, 45],
    popupAnchor: [0, -45],
  });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface EvacuationCenterMarkersProps {
  /** Callback when user clicks "Get Route" on a center */
  onRouteRequest?: (center: EvacuationCenter) => void;
  /** Show name tooltip on hover (default: true) */
  showTooltips?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EvacuationCenterMarkers({
  onRouteRequest,
  showTooltips = true,
}: EvacuationCenterMarkersProps) {
  const queryClient = useQueryClient();
  const params = useMemo(() => ({ active_only: true }), []);
  const { data: centers = [] } = useEvacuationCenters(params);

  // Listen for real-time capacity SSE events and patch the query cache
  const handleCapacityUpdate = useCallback(
    (e: Event) => {
      const { detail } = e as CustomEvent<{
        center_id: number;
        capacity_current: number;
        capacity_total: number;
        near_full: boolean;
      }>;

      queryClient.setQueryData<EvacuationCenter[]>(
        evacuationKeys.centers(params),
        (old) => {
          if (!old) return old;
          return old.map((c) =>
            c.id === detail.center_id
              ? {
                  ...c,
                  capacity_current: detail.capacity_current,
                  capacity_total: detail.capacity_total,
                  occupancy_pct: Math.round(
                    (detail.capacity_current / detail.capacity_total) * 100,
                  ),
                  available_slots:
                    detail.capacity_total - detail.capacity_current,
                }
              : c,
          );
        },
      );
    },
    [queryClient, params],
  );

  useEffect(() => {
    window.addEventListener("evacuation_capacity", handleCapacityUpdate);
    return () =>
      window.removeEventListener("evacuation_capacity", handleCapacityUpdate);
  }, [handleCapacityUpdate]);

  // Memoize icons to avoid recreating on each render
  const iconMap = useMemo(() => {
    const map = new Map<number, L.DivIcon>();
    for (const c of centers) {
      map.set(c.id, createCenterIcon(c.occupancy_pct));
    }
    return map;
  }, [centers]);

  if (!centers.length) return null;

  return (
    <>
      {centers.map((c) => (
        <Marker
          key={`evac-${c.id}`}
          position={[c.latitude, c.longitude]}
          icon={iconMap.get(c.id)!}
        >
          {showTooltips && (
            <Tooltip direction="top" offset={[0, -47]}>
              <strong>{c.name}</strong>
            </Tooltip>
          )}
          <Popup maxWidth={300}>
            <div className="min-w-56 space-y-2 text-sm">
              <p className="font-semibold text-risk-safe flex items-center gap-1.5">
                <span className="text-base">🏠</span> Evacuation Center
              </p>
              <p className="font-medium text-gray-900 dark:text-gray-100">
                {c.name}
              </p>

              {/* Capacity bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-gray-500">
                  <span>
                    {c.capacity_current} / {c.capacity_total}
                  </span>
                  <span
                    className="font-medium"
                    style={{ color: occupancyColor(c.occupancy_pct) }}
                  >
                    {c.occupancy_pct}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(c.occupancy_pct, 100)}%`,
                      backgroundColor: occupancyColor(c.occupancy_pct),
                    }}
                  />
                </div>
                <p className="text-xs text-gray-400">
                  {c.available_slots} slots available
                </p>
              </div>

              <div className="text-xs text-gray-500 space-y-0.5">
                <p>Barangay: {c.barangay}</p>
                {c.address && <p>{c.address}</p>}
                {c.contact_number && <p>Contact: {c.contact_number}</p>}
              </div>

              {onRouteRequest && (
                <button
                  type="button"
                  className="w-full rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                  onClick={() => onRouteRequest(c)}
                >
                  Get Route →
                </button>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

export default EvacuationCenterMarkers;
