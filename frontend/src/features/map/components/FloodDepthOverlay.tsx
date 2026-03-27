/**
 * FloodDepthOverlay Component
 *
 * Renders barangay polygons with graduated blue fills representing
 * estimated flood depth from the physics-informed model.
 *
 * Classification legend:
 *   None      (0 cm)        — transparent
 *   Minor     (1–10 cm)     — light blue
 *   Moderate  (10–30 cm)    — medium blue
 *   Major     (30–60 cm)    — dark blue
 *   Severe    (60+ cm)      — deep navy
 */

import type { PathOptions } from "leaflet";
import { memo, useMemo } from "react";
import { Polygon, Tooltip } from "react-leaflet";

import { BARANGAYS } from "@/config/paranaque";
import { useFloodDepth, type BarangayDepth } from "../hooks/useFloodDepth";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEPTH_COLORS: Record<string, string> = {
  none: "transparent",
  minor: "#93c5fd", // blue-300
  moderate: "#3b82f6", // blue-500
  major: "#1d4ed8", // blue-700
  severe: "#1e3a5f", // deep navy
};

const DEPTH_OPACITY: Record<string, number> = {
  none: 0,
  minor: 0.3,
  moderate: 0.45,
  major: 0.6,
  severe: 0.75,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface FloodDepthOverlayProps {
  /** Whether overlay is visible */
  visible?: boolean;
}

export const FloodDepthOverlay = memo(function FloodDepthOverlay({
  visible = true,
}: FloodDepthOverlayProps) {
  const { data } = useFloodDepth(visible);

  const polygons = useMemo(() => {
    if (!data?.barangays) return [];

    return BARANGAYS.map((brgy) => {
      const depth: BarangayDepth | undefined = data.barangays[brgy.key];
      const classification = depth?.classification ?? "none";
      const color = DEPTH_COLORS[classification] ?? "transparent";
      const fillOpacity = DEPTH_OPACITY[classification] ?? 0;

      const pathOptions: PathOptions = {
        color: classification === "none" ? "transparent" : "#1e40af",
        fillColor: color,
        fillOpacity,
        weight: classification === "none" ? 0 : 1.5,
        opacity: 0.6,
      };

      return {
        key: brgy.key,
        name: brgy.name,
        positions: brgy.polygon,
        pathOptions,
        depth,
        classification,
      };
    });
  }, [data]);

  if (!visible || !data) return null;

  return (
    <>
      {polygons.map((p) =>
        p.classification === "none" ? null : (
          <Polygon
            key={p.key}
            positions={p.positions}
            pathOptions={p.pathOptions}
          >
            <Tooltip sticky>
              <div className="text-xs space-y-0.5">
                <p className="font-semibold">{p.name}</p>
                <p>
                  Depth:{" "}
                  <span className="font-medium">
                    {p.depth?.depth_cm.toFixed(1) ?? 0} cm
                  </span>
                </p>
                <p className="text-muted-foreground">
                  Range: {p.depth?.depth_range_cm[0].toFixed(1)}–
                  {p.depth?.depth_range_cm[1].toFixed(1)} cm (±
                  {p.depth?.uncertainty_pct}%)
                </p>
                <p className="capitalize">Classification: {p.classification}</p>
              </div>
            </Tooltip>
          </Polygon>
        ),
      )}
    </>
  );
});

export default FloodDepthOverlay;
