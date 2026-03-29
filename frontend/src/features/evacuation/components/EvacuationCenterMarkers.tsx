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
import { Home } from "lucide-react";
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
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 45" width="30" height="45">
      <defs>
        <filter id="ec-shadow" x="-20%" y="-10%" width="140%" height="130%">
          <feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="0.25"/>
        </filter>
      </defs>
      <path filter="url(#ec-shadow)" fill="${fill}" stroke="#fff" stroke-width="1.5"
        d="M15 0C6.72 0 0 6.72 0 15c0 11.25 15 30 15 30s15-18.75 15-30C30 6.72 23.28 0 15 0z"/>
      <g transform="translate(7.5, 7.5)" fill="#fff">
        <path d="M7.5 0L0 6.5h2.2v5.5h4.3v-3.2h2v3.2h4.3V6.5h2.2L7.5 0z"/>
        <rect x="5.75" y="8.5" width="3.5" height="3.3" rx="0.5" fill="${fill}"/>
      </g>
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
                <Home className="h-4 w-4" /> Evacuation Center
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
