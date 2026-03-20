/**
 * FloodDensityMap — deck.gl WebGL Overlay
 *
 * Renders flood alert data as a heatmap (HeatmapLayer) and individual
 * scatter markers (ScatterplotLayer, visible at zoom >= 14).
 *
 * Lazy-loaded via React.lazy() and only fetched when:
 *   1. WebGL is available (checked by webgl-detect.ts)
 *   2. User navigates to a map view
 *
 * GPU resources are explicitly released on unmount to prevent
 * "too many active WebGL contexts" errors.
 */

import type { Alert } from "@/types";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import type { MapViewState, ViewStateChangeParameters } from "@deck.gl/core";
import { ScatterplotLayer } from "@deck.gl/layers";
import DeckGL, { type DeckGLRef } from "@deck.gl/react";
import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FloodDensityMapProps {
  alerts: Alert[];
  onAlertClick?: (alert: Alert) => void;
}

// ---------------------------------------------------------------------------
// Risk → weight / color mapping
// ---------------------------------------------------------------------------

const RISK_COLORS: Record<number, [number, number, number]> = {
  0: [52, 211, 153], // green — Safe
  1: [251, 191, 36], // amber — Alert
  2: [239, 68, 68], // red   — Critical
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function FloodDensityMap({
  alerts,
  onAlertClick,
}: FloodDensityMapProps) {
  const deckRef = useRef<DeckGLRef>(null);

  const [viewState, setViewState] = useState<MapViewState>({
    longitude: 121.02,
    latitude: 14.479,
    zoom: 13,
    pitch: 0,
    bearing: 0,
  });

  // Filter alerts with valid coordinates
  const geoAlerts = alerts.filter(
    (a): a is Alert & { latitude: number; longitude: number } =>
      a.latitude != null && a.longitude != null,
  );

  const layers = [
    new HeatmapLayer<Alert & { latitude: number; longitude: number }>({
      id: "flood-heatmap",
      data: geoAlerts,
      getPosition: (d) => [d.longitude, d.latitude],
      getWeight: (d) => (d.risk_level ?? 0) + 1,
      radiusPixels: 60,
      intensity: 1.5,
      threshold: 0.1,
      colorRange: [
        [65, 182, 131, 100],
        [255, 255, 0, 140],
        [255, 165, 0, 180],
        [255, 0, 0, 220],
      ],
    }),
    new ScatterplotLayer<Alert & { latitude: number; longitude: number }>({
      id: "flood-markers",
      data: geoAlerts,
      getPosition: (d) => [d.longitude, d.latitude],
      getRadius: 80,
      getFillColor: (d) => [
        ...(RISK_COLORS[d.risk_level ?? 0] ?? RISK_COLORS[0]!),
        200,
      ],
      getLineColor: [255, 255, 255, 180],
      lineWidthMinPixels: 1,
      pickable: true,
      visible: viewState.zoom >= 14,
      onClick: (info) => {
        if (info.object && onAlertClick) {
          onAlertClick(info.object as Alert);
        }
      },
    }),
  ];

  const handleViewStateChange = useCallback(
    (params: ViewStateChangeParameters) => {
      const vs = params.viewState as MapViewState;
      setViewState(vs);
    },
    [],
  );

  // GPU memory cleanup on unmount
  useEffect(() => {
    const deck = deckRef.current;
    return () => {
      try {
        if (deck) {
          (deck as unknown as { finalize?: () => void }).finalize?.();
        }
      } catch {
        // Cleanup is best-effort
      }
    };
  }, []);

  return (
    <div className="absolute inset-0" style={{ pointerEvents: "auto" }}>
      <DeckGL
        ref={deckRef}
        viewState={viewState}
        onViewStateChange={handleViewStateChange}
        layers={layers}
        controller={true}
        style={{ position: "absolute", inset: "0" }}
        getTooltip={({ object }: { object?: Alert }) =>
          object
            ? {
                text: `${object.location ?? "Unknown"} — Risk Level ${object.risk_level}`,
              }
            : null
        }
      />
    </div>
  );
}

export default FloodDensityMap;
