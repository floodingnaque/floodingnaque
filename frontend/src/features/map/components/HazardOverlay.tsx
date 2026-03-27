/**
 * HazardOverlay Component
 *
 * Renders barangay-level flood hazard polygons on a Leaflet map.
 * Each polygon is color-coded by hazard classification (low/moderate/high)
 * and shows a popup with elevation, drainage, and hazard scoring details.
 *
 * Supports three overlay modes:
 * - hazard: Composite flood hazard score (default)
 * - elevation: SRTM DEM elevation bands
 * - drainage: Drainage capacity classification
 */

import type { PathOptions } from "leaflet";
import { memo, useMemo } from "react";
import { Polygon, Popup, Tooltip } from "react-leaflet";
import type {
  HazardFeature,
  HazardFeatureProperties,
} from "../hooks/useHazardMap";

export interface HazardOverlayProps {
  /** GeoJSON features to render as polygons */
  features: HazardFeature[];
  /** Overlay mode affecting popup content */
  mode?: "hazard" | "elevation" | "drainage";
  /** Opacity for polygon fill (0-1, default: 0.35) */
  fillOpacity?: number;
  /** Whether to show tooltips on hover */
  showTooltips?: boolean;
  /** Callback when a barangay polygon is clicked */
  onBarangayClick?: (
    barangayKey: string,
    properties: HazardFeatureProperties,
  ) => void;
}

/**
 * Convert GeoJSON [lon, lat] coordinates to Leaflet [lat, lng] format
 */
function geoJsonToLeaflet(coords: number[][][]): [number, number][] {
  return coords[0]!.map(([lon, lat]) => [lat, lon] as [number, number]);
}

/**
 * Get color for a feature based on overlay mode
 */
function getFeatureColor(
  properties: HazardFeatureProperties,
  mode: string,
): string {
  switch (mode) {
    case "elevation":
      return properties.hazard_color || "#6c757d";
    case "drainage": {
      const drainColors: Record<string, string> = {
        poor: "hsl(var(--risk-critical))",
        moderate: "hsl(var(--risk-alert))",
        good: "hsl(var(--risk-safe))",
      };
      return drainColors[properties.drainage_capacity] || "#6c757d";
    }
    case "hazard":
    default:
      return properties.hazard_color || "#6c757d";
  }
}

/**
 * Format hazard score as percentage
 */
function formatScore(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

/**
 * HazardOverlay - Renders flood hazard polygons on the map
 */
export const HazardOverlay = memo(function HazardOverlay({
  features,
  mode = "hazard",
  fillOpacity = 0.35,
  showTooltips = true,
  onBarangayClick,
}: HazardOverlayProps) {
  const polygons = useMemo(() => {
    return features.map((feature) => {
      const props = feature.properties;
      const positions = geoJsonToLeaflet(feature.geometry.coordinates);
      const color = getFeatureColor(props, mode);

      // Modulate opacity by confidence: 0.2 baseline + confidence * 0.6 range
      const confidence = props.confidence ?? 0.7;
      const adaptiveOpacity = 0.2 + confidence * 0.6;

      const pathOptions: PathOptions = {
        color: color,
        fillColor: color,
        fillOpacity: adaptiveOpacity,
        weight: 2,
        opacity: 0.8,
      };

      return {
        key: props.key,
        positions,
        pathOptions,
        properties: props,
      };
    });
  }, [features, mode, fillOpacity]);

  return (
    <>
      {polygons.map(({ key, positions, pathOptions, properties }) => (
        <Polygon
          key={key}
          positions={positions}
          pathOptions={pathOptions}
          eventHandlers={{
            click: () => onBarangayClick?.(key, properties),
          }}
        >
          {/* Tooltip on hover */}
          {showTooltips && (
            <Tooltip direction="top" sticky>
              <strong>{properties.name}</strong>
              <br />
              {mode === "hazard" && (
                <>
                  Hazard: {properties.hazard_classification.toUpperCase()} (
                  {formatScore(properties.hazard_score)})
                  <br />
                  Confidence: {formatScore(properties.confidence ?? 0.7)}
                  {properties.current_rainfall_mm > 0 && (
                    <>
                      <br />
                      Rain: {properties.current_rainfall_mm.toFixed(1)} mm/hr
                    </>
                  )}
                </>
              )}
              {mode === "elevation" && (
                <>
                  Elevation: {properties.mean_elevation_m}m (min:{" "}
                  {properties.min_elevation_m}m)
                </>
              )}
              {mode === "drainage" && (
                <>
                  Drainage: {properties.drainage_capacity}
                  <br />
                  Waterway: {properties.nearest_waterway}
                </>
              )}
            </Tooltip>
          )}

          {/* Detail popup on click */}
          <Popup maxWidth={320}>
            <div className="text-sm">
              <h3 className="mb-2 text-base font-semibold">
                {properties.name}
              </h3>
              <p className="text-muted-foreground mb-2 text-xs">
                Pop: {properties.population.toLocaleString()} · Coordinates:{" "}
                {properties.lat.toFixed(4)}, {properties.lon.toFixed(4)}
              </p>

              {/* Hazard Assessment */}
              <div className="mb-2 rounded border p-2">
                <div className="mb-1 flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: properties.hazard_color }}
                  />
                  <strong>
                    {properties.hazard_classification.toUpperCase()} RISK
                  </strong>
                  <span className="text-muted-foreground text-xs">
                    ({formatScore(properties.hazard_score)})
                  </span>
                </div>
                <div className="text-muted-foreground text-xs">
                  Data confidence: {formatScore(properties.confidence ?? 0.7)}
                  {(properties.confidence ?? 0.7) >= 0.9
                    ? " — Live data"
                    : (properties.confidence ?? 0.7) >= 0.85
                      ? " — Recently evaluated"
                      : " — Static baseline"}
                </div>
              </div>

              {/* Elevation */}
              <div className="mb-1">
                <span className="font-medium">Elevation:</span>{" "}
                {properties.mean_elevation_m}m avg /{" "}
                {properties.min_elevation_m}m min
                <span className="text-muted-foreground text-xs">
                  {" "}
                  (slope: {properties.slope_pct}%)
                </span>
              </div>

              {/* Drainage */}
              <div className="mb-1">
                <span className="font-medium">Drainage:</span>{" "}
                {properties.drainage_capacity}
                <span className="text-muted-foreground text-xs">
                  {" "}
                  · {properties.nearest_waterway} (
                  {properties.distance_to_waterway_m}m)
                </span>
              </div>

              {/* Surface */}
              <div className="mb-1">
                <span className="font-medium">Impervious surface:</span>{" "}
                {properties.impervious_surface_pct}%
              </div>

              {/* History */}
              <div className="mb-1">
                <span className="font-medium">Flood events (recorded):</span>{" "}
                {properties.flood_history_events}
              </div>

              {/* Current rainfall */}
              {properties.current_rainfall_mm > 0 && (
                <div className="mt-2 rounded bg-blue-50 p-1.5 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                  <span className="font-medium">Live rainfall:</span>{" "}
                  {properties.current_rainfall_mm.toFixed(1)} mm/hr
                </div>
              )}
            </div>
          </Popup>
        </Polygon>
      ))}
    </>
  );
});

export default HazardOverlay;
