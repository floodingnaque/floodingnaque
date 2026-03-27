/**
 * ForecastOverlay Component
 *
 * Renders barangay polygons colored by predicted future flood risk.
 * Shows a "Now / +1h / +3h" toggle above the map.
 * Uses the /predict/forecast-map endpoint.
 */

import type { PathOptions } from "leaflet";
import { Clock } from "lucide-react";
import { memo, useMemo, useState } from "react";
import { Polygon, Tooltip } from "react-leaflet";

import { Button } from "@/components/ui/button";
import { BARANGAYS } from "@/config/paranaque";
import { cn } from "@/lib/utils";
import { useForecastMap, type BarangayForecast } from "../hooks/useForecastMap";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const OFFSET_LABELS: Record<number, string> = {
  0: "Now",
  1: "+1 Hour",
  3: "+3 Hours",
};

const RISK_COLORS: Record<number, string> = {
  0: "hsl(var(--risk-safe))",
  1: "hsl(var(--risk-alert))",
  2: "hsl(var(--risk-critical))",
};

const RISK_LABELS: Record<number, string> = {
  0: "Safe",
  1: "Alert",
  2: "Critical",
};

// ---------------------------------------------------------------------------
// Sub-component: Time selector (rendered outside the map via portal or slot)
// ---------------------------------------------------------------------------

interface ForecastTimeSelectorProps {
  offsets: number[];
  selected: number;
  onSelect: (offset: number) => void;
  className?: string;
}

export function ForecastTimeSelector({
  offsets,
  selected,
  onSelect,
  className,
}: ForecastTimeSelectorProps) {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <Clock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
      {offsets.map((offset) => (
        <Button
          key={offset}
          variant={selected === offset ? "default" : "outline"}
          size="sm"
          className="h-7 px-2.5 text-xs"
          onClick={() => onSelect(offset)}
        >
          {OFFSET_LABELS[offset] ?? `+${offset}h`}
        </Button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main overlay
// ---------------------------------------------------------------------------

export interface ForecastOverlayProps {
  /** Currently selected time offset (hours) */
  selectedOffset?: number;
  /** Fill opacity for polygons */
  fillOpacity?: number;
}

export const ForecastOverlay = memo(function ForecastOverlay({
  selectedOffset = 0,
  fillOpacity = 0.4,
}: ForecastOverlayProps) {
  const { data } = useForecastMap();

  const polygons = useMemo(() => {
    if (!data?.barangays) return [];

    return BARANGAYS.map((brgy) => {
      const forecasts = data.barangays[brgy.key];
      const forecast: BarangayForecast | undefined =
        forecasts?.[String(selectedOffset)];

      const riskLevel = forecast?.risk_level ?? 0;
      const color = RISK_COLORS[riskLevel] ?? RISK_COLORS[0]!;

      const pathOptions: PathOptions = {
        color,
        fillColor: color,
        fillOpacity: forecast
          ? fillOpacity * 0.5 + forecast.confidence * fillOpacity * 0.5
          : fillOpacity * 0.3,
        weight: 2,
        opacity: 0.8,
      };

      return {
        key: brgy.key,
        name: brgy.name,
        positions: brgy.polygon,
        pathOptions,
        forecast,
        riskLevel,
      };
    });
  }, [data, selectedOffset, fillOpacity]);

  if (!data) return null;

  return (
    <>
      {polygons.map((p) => (
        <Polygon
          key={p.key}
          positions={p.positions}
          pathOptions={p.pathOptions}
        >
          <Tooltip sticky>
            <div className="text-xs space-y-0.5">
              <p className="font-semibold">{p.name}</p>
              <p>
                Risk:{" "}
                <span className="font-medium">
                  {RISK_LABELS[p.riskLevel] ?? "Unknown"}
                </span>
              </p>
              {p.forecast && (
                <>
                  <p>
                    Probability: {(p.forecast.probability * 100).toFixed(1)}%
                  </p>
                  <p>Confidence: {(p.forecast.confidence * 100).toFixed(0)}%</p>
                </>
              )}
              <p className="text-muted-foreground">
                {OFFSET_LABELS[selectedOffset] ?? `+${selectedOffset}h`}{" "}
                forecast
              </p>
            </div>
          </Tooltip>
        </Polygon>
      ))}
    </>
  );
});

// ---------------------------------------------------------------------------
// Combined container with self-contained time selector + overlay
// ---------------------------------------------------------------------------

export interface ForecastOverlayWithControlsProps {
  className?: string;
}

/**
 * Stand-alone component that manages its own time offset state.
 * Renders the map overlay + a floating time selector badge.
 * Use only the overlay portion as map children and the selector externally.
 */
export function useForecastOverlayState() {
  const [selectedOffset, setSelectedOffset] = useState(0);
  const offsets = [0, 1, 3];
  return { selectedOffset, setSelectedOffset, offsets };
}
