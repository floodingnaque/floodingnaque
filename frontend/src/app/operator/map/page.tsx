/**
 * Operator - Live Flood Map Page
 *
 * Full-page interactive Leaflet map with barangay hazard overlay,
 * evacuation center markers, alert markers, community report layer,
 * and layer toggle controls.
 */

import { Layers, RefreshCw } from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAlerts } from "@/features/alerts";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import {
  EvacuationMarkers,
  FloodMap,
  useHazardMap,
  type FloodMapRef,
} from "@/features/map";
import { SafeRouteLayer } from "@/features/map/components/SafeRouteLayer";
import { cn } from "@/lib/utils";
import type { Alert } from "@/types/api/alert";
import { RISK_CONFIGS, type RiskLevel } from "@/types/api/prediction";

const RISK_BADGE: Record<RiskLevel, string> = {
  0: "bg-green-500/10 text-green-700 border-green-500/30",
  1: "bg-amber-500/10 text-amber-700 border-amber-500/30",
  2: "bg-red-500/10 text-red-700 border-red-500/30",
};

type OverlayMode = "hazard" | "elevation" | "drainage";

export default function OperatorMapPage() {
  const mapRef = useRef<FloodMapRef>(null);
  const { data: prediction, refetch } = useLivePrediction();
  const { data: hazardData } = useHazardMap();
  const { data: alertsData } = useAlerts();
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("hazard");
  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;

  const alerts: Alert[] = (() => {
    if (!alertsData) return [];
    if (Array.isArray(alertsData)) return alertsData;
    if ("data" in alertsData) return alertsData.data ?? [];
    return [];
  })();

  const hazardFeatures = useMemo(
    () => hazardData?.features ?? [],
    [hazardData],
  );

  const handleBarangayClick = useCallback(
    (key: string) => {
      const feature = hazardFeatures.find((f) => f.properties.key === key);
      if (feature) {
        mapRef.current?.flyTo(
          feature.properties.lat,
          feature.properties.lon,
          15,
        );
      }
    },
    [hazardFeatures],
  );

  return (
    <div className="p-4 sm:p-6 space-y-4">
      {/* Map controls bar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="gap-1">
            <Layers className="h-3 w-3" />
            Flood Risk Overlay
          </Badge>
          {prediction && (
            <Badge variant="outline" className={RISK_BADGE[riskLevel]}>
              {RISK_CONFIGS[riskLevel].label}
            </Badge>
          )}
          {/* Overlay mode toggles */}
          <div className="flex items-center border rounded-lg overflow-hidden">
            {(["hazard", "elevation", "drainage"] as OverlayMode[]).map(
              (mode) => (
                <button
                  key={mode}
                  onClick={() => setOverlayMode(mode)}
                  className={cn(
                    "px-3 py-1.5 text-xs font-medium transition-colors capitalize",
                    overlayMode === mode
                      ? "bg-primary text-primary-foreground"
                      : "bg-card hover:bg-muted",
                  )}
                >
                  {mode}
                </button>
              ),
            )}
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={() => refetch()}
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </Button>
      </div>

      {/* Full-page Map */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <FloodMap
            ref={mapRef}
            height={600}
            alerts={alerts}
            hazardFeatures={hazardFeatures}
            hazardMode={overlayMode}
            hazardOpacity={0.35}
            onBarangayClick={handleBarangayClick}
          >
            <EvacuationMarkers />
            <SafeRouteLayer />
          </FloodMap>
        </CardContent>
      </Card>

      {/* Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-x-6 gap-y-3 text-xs">
            {/* Risk zone polygons */}
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-sm bg-green-500/50 border border-green-600/40" />
              <span>Low Risk Zone</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-sm bg-amber-500/50 border border-amber-600/40" />
              <span>Moderate Risk Zone</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-sm bg-red-500/50 border border-red-600/40" />
              <span>High Risk Zone</span>
            </div>

            {/* Evacuation center marker */}
            <div className="flex items-center gap-1.5">
              <svg width="12" height="16" viewBox="0 0 24 36">
                <path
                  fill="#16a34a"
                  stroke="#fff"
                  strokeWidth="1.5"
                  d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24C24 5.37 18.63 0 12 0z"
                />
                <path fill="#fff" d="M12 6.5l-5.5 6.5h2.5v4h6v-4h2.5L12 6.5z" />
              </svg>
              <span>Evacuation Center</span>
            </div>

            {/* Evacuation route lines */}
            <div className="flex items-center gap-1.5">
              <svg width="24" height="12" viewBox="0 0 24 6">
                <line
                  x1="0"
                  y1="3"
                  x2="24"
                  y2="3"
                  stroke="#ef4444"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
              </svg>
              <span>High-Risk Route</span>
            </div>
            <div className="flex items-center gap-1.5">
              <svg width="24" height="12" viewBox="0 0 24 6">
                <line
                  x1="0"
                  y1="3"
                  x2="24"
                  y2="3"
                  stroke="#f59e0b"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
              </svg>
              <span>Moderate-Risk Route</span>
            </div>
            <div className="flex items-center gap-1.5">
              <svg width="24" height="12" viewBox="0 0 24 6">
                <line
                  x1="0"
                  y1="3"
                  x2="24"
                  y2="3"
                  stroke="#22c55e"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
              </svg>
              <span>Low-Risk Route</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
