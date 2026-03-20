/**
 * EvacuationRoute Component
 *
 * Renders a safe-route GeoJSON polyline on the Leaflet map with
 * a floating summary card showing distance, ETA, and flood segments avoided.
 */

import type { EvacuationRoute as RouteType } from "@/types";
import { useMemo } from "react";
import { GeoJSON } from "react-leaflet";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface EvacuationRouteProps {
  /** Route data from the API */
  route: RouteType;
  /** Callback to dismiss / clear the route overlay */
  onClose?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EvacuationRoute({ route, onClose }: EvacuationRouteProps) {
  const geoJsonData = useMemo(
    () =>
      ({
        type: "Feature" as const,
        geometry: route.geometry,
        properties: {},
      }) as GeoJSON.Feature,
    [route.geometry],
  );

  const distanceKm = (route.distance_m / 1000).toFixed(1);
  const durationMin = Math.ceil(route.duration_s / 60);

  return (
    <>
      {/* Route polyline */}
      <GeoJSON
        key={JSON.stringify(route.geometry.coordinates.slice(0, 2))}
        data={geoJsonData}
        style={{
          color: "hsl(var(--primary))",
          weight: 5,
          opacity: 0.85,
          dashArray: "10 6",
        }}
      />

      {/* Floating summary card */}
      <div className="absolute bottom-4 left-4 z-1000 w-64 rounded-xl bg-white/90 dark:bg-gray-900/90 backdrop-blur-md shadow-lg ring-1 ring-black/5 p-3 space-y-1.5 text-sm">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-indigo-600 dark:text-indigo-400">
            Safe Route
          </p>
          {onClose && (
            <button
              type="button"
              className="text-xs text-gray-400 hover:text-gray-600"
              onClick={onClose}
            >
              ✕
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <p className="text-lg font-bold">{distanceKm}</p>
            <p className="text-[10px] text-gray-500">km</p>
          </div>
          <div>
            <p className="text-lg font-bold">{durationMin}</p>
            <p className="text-[10px] text-gray-500">min</p>
          </div>
          <div>
            <p className="text-lg font-bold">{route.flood_segments_avoided}</p>
            <p className="text-[10px] text-gray-500">avoided</p>
          </div>
        </div>

        {route.google_maps_url && (
          <a
            href={route.google_maps_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full rounded-md bg-indigo-600 px-3 py-1.5 text-center text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
          >
            Open in Google Maps
          </a>
        )}
      </div>
    </>
  );
}

export default EvacuationRoute;
