/**
 * SafeRouteLayer Component
 *
 * Renders real road-following evacuation routes on the Leaflet map
 * using OSRM driving directions. Routes connect each barangay centroid
 * to its designated evacuation center and are color-coded by flood risk.
 */

import { Polyline, Tooltip } from "react-leaflet";
import {
  useEvacuationRoutes,
  type BarangayRoute,
} from "../hooks/useEvacuationRoutes";

// Risk-based route colors
const ROUTE_COLORS: Record<string, string> = {
  high: "#ef4444", // red-500  - high-risk evacuation
  moderate: "#f59e0b", // amber-500 - moderate-risk
  low: "#22c55e", // green-500 - low-risk
};

function formatDistance(meters: number): string {
  return meters >= 1000
    ? `${(meters / 1000).toFixed(1)} km`
    : `${Math.round(meters)} m`;
}

function formatDuration(seconds: number): string {
  const mins = Math.round(seconds / 60);
  return mins < 1 ? "< 1 min" : `~${mins} min`;
}

function RoutePolyline({ r }: { r: BarangayRoute }) {
  const color = ROUTE_COLORS[r.floodRisk] ?? ROUTE_COLORS.moderate;

  return (
    <Polyline
      positions={r.route.coordinates}
      pathOptions={{
        color,
        weight: 4,
        opacity: 0.8,
        lineCap: "round",
        lineJoin: "round",
      }}
    >
      <Tooltip direction="top" sticky>
        <div className="text-xs space-y-0.5">
          <p>
            <strong>{r.name}</strong> → {r.evacuationCenter}
          </p>
          <p className="text-muted-foreground">
            {formatDistance(r.route.distance)} &middot;{" "}
            {formatDuration(r.route.duration)} drive
          </p>
        </div>
      </Tooltip>
    </Polyline>
  );
}

export function SafeRouteLayer() {
  const { data: routes } = useEvacuationRoutes();

  if (!routes?.length) return null;

  return (
    <>
      {routes.map((r) => (
        <RoutePolyline key={r.key} r={r} />
      ))}
    </>
  );
}
