/**
 * ReportDensityLayer – deck.gl HeatmapLayer for community flood reports.
 *
 * Uses the /api/v1/reports/density endpoint for pre-aggregated grid data
 * and renders it as a WebGL heatmap overlay.
 */

import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import type { MapViewState, ViewStateChangeParameters } from "@deck.gl/core";
import DeckGL, { type DeckGLRef } from "@deck.gl/react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  useReportDensity,
  type DensityFeature,
} from "../hooks/useReportDensity";

// ── Constants ───────────────────────────────────────────────────────────

const PARANAQUE_CENTER = { longitude: 121.02, latitude: 14.479 };

const RISK_COLOR_RANGE: [number, number, number, number][] = [
  [65, 182, 196, 100],
  [127, 205, 187, 140],
  [199, 233, 180, 160],
  [237, 248, 177, 180],
  [255, 237, 160, 200],
  [254, 217, 118, 220],
  [254, 178, 76, 230],
  [253, 141, 60, 240],
  [240, 59, 32, 250],
  [189, 0, 38, 255],
];

// ── Component ───────────────────────────────────────────────────────────

interface ReportDensityLayerProps {
  hours?: number;
  minCredibility?: number;
  className?: string;
}

export function ReportDensityLayer({
  hours = 168,
  minCredibility = 0,
  className,
}: ReportDensityLayerProps) {
  const deckRef = useRef<DeckGLRef>(null);
  const { data } = useReportDensity(hours, minCredibility);

  const [viewState, setViewState] = useState<MapViewState>({
    ...PARANAQUE_CENTER,
    zoom: 13,
    pitch: 0,
    bearing: 0,
  });

  // Release WebGL context on unmount
  useEffect(() => {
    const ref = deckRef.current;
    return () => {
      try {
        const canvas = ref?.deck?.getCanvas?.();
        const gl =
          canvas?.getContext?.("webgl2") ?? canvas?.getContext?.("webgl");
        if (gl) {
          const ext = gl.getExtension("WEBGL_lose_context");
          ext?.loseContext();
        }
      } catch {
        // best-effort
      }
    };
  }, []);

  const onViewStateChange = useCallback(
    ({ viewState: vs }: ViewStateChangeParameters) => {
      setViewState(vs as MapViewState);
    },
    [],
  );

  const features = data?.features ?? [];

  const layers = [
    new HeatmapLayer<DensityFeature>({
      id: "report-density-heatmap",
      data: features,
      getPosition: (d) => d.geometry.coordinates as [number, number],
      getWeight: (d) => d.properties.weight,
      radiusPixels: 40,
      intensity: 1.5,
      threshold: 0.05,
      colorRange: RISK_COLOR_RANGE,
    }),
  ];

  return (
    <div
      className={className}
      style={{ width: "100%", height: "400px", position: "relative" }}
    >
      <DeckGL
        ref={deckRef}
        viewState={viewState}
        onViewStateChange={onViewStateChange}
        layers={layers}
        controller
        style={{ position: "absolute", inset: "0" }}
      />
      {/* Overlay stats */}
      {data && (
        <div className="absolute bottom-3 left-3 bg-background/80 backdrop-blur-sm rounded-md px-3 py-2 text-xs">
          <span className="font-medium">{data.meta.total_reports}</span> reports
          in <span className="font-medium">{data.meta.grid_cells}</span> cells
          (last {data.meta.hours}h)
        </div>
      )}
    </div>
  );
}
