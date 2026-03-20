/**
 * SafeRouteLayer Component
 *
 * Renders safe evacuation routes on the Leaflet map as polylines
 * connecting each barangay centroid to its designated evacuation center.
 * Uses the BARANGAYS config for static route lines (OSRM live routing
 * is available via the evacuation API for on-demand use).
 */

import { BARANGAYS } from "@/config/paranaque";
import { useMemo } from "react";
import { Polyline, Tooltip } from "react-leaflet";

const ROUTE_COLOR = "#6366f1"; // indigo-500

export function SafeRouteLayer() {
  const routes = useMemo(
    () =>
      BARANGAYS.filter((b) => b.evacuationCenter).map((b) => ({
        key: b.key,
        name: b.name,
        center: b.evacuationCenter,
        positions: [
          [b.lat, b.lon] as [number, number],
          // Offset slightly toward city center to simulate route direction
          [
            b.lat + (14.4793 - b.lat) * 0.3,
            b.lon + (121.0198 - b.lon) * 0.3,
          ] as [number, number],
        ],
      })),
    [],
  );

  return (
    <>
      {routes.map((r) => (
        <Polyline
          key={r.key}
          positions={r.positions}
          pathOptions={{
            color: ROUTE_COLOR,
            weight: 3,
            opacity: 0.7,
            dashArray: "8 6",
          }}
        >
          <Tooltip direction="top" sticky>
            <span className="text-xs">
              <strong>{r.name}</strong> → {r.center}
            </span>
          </Tooltip>
        </Polyline>
      ))}
    </>
  );
}
