/**
 * Resident - Live Map Page
 *
 * Full-featured Leaflet map centered on Parañaque City with:
 * - Barangay risk polygons (color-coded by risk level)
 * - Layer controls & base-map switching
 * - Evacuation center markers
 * - Community flood reports & safe routes
 * - GPS "my location" button
 */

import { Crosshair, Layers, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useState } from "react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BarangayRiskMap } from "@/features/dashboard";
import { ResidentDecisionPanel } from "@/features/flooding";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import {
  ForecastOverlay,
  ForecastTimeSelector,
  useForecastOverlayState,
} from "@/features/map/components/ForecastOverlay";
import { RISK_CONFIGS, type RiskLevel } from "@/types/api/prediction";

const RISK_BADGE: Record<RiskLevel, string> = {
  0: "bg-green-500/10 text-green-700 border-green-500/30",
  1: "bg-amber-500/10 text-amber-700 border-amber-500/30",
  2: "bg-red-500/10 text-red-700 border-red-500/30",
};

export default function ResidentMapPage() {
  const {
    data: prediction,
    isLoading: predLoading,
    refetch,
  } = useLivePrediction();
  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;

  const [locating, setLocating] = useState(false);
  const [userLocation, setUserLocation] = useState<[number, number] | null>(
    null,
  );
  const { selectedOffset, setSelectedOffset, offsets } =
    useForecastOverlayState();

  const handleLocate = useCallback(() => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation([pos.coords.latitude, pos.coords.longitude]);
        setLocating(false);
      },
      () => setLocating(false),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, []);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-4 w-full">
      <Breadcrumb
        items={[{ label: "Home", href: "/resident" }, { label: "Flood Map" }]}
        className="mb-4"
      />

      {/* ── Controls ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1">
            <Layers className="h-3 w-3" />
            Flood Risk
          </Badge>
          {prediction && (
            <Badge variant="outline" className={RISK_BADGE[riskLevel]}>
              {RISK_CONFIGS[riskLevel].label}
            </Badge>
          )}
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          <ForecastTimeSelector
            offsets={offsets}
            selected={selectedOffset}
            onSelect={setSelectedOffset}
          />
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={handleLocate}
            disabled={locating}
          >
            {locating ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Crosshair className="h-3 w-3" />
            )}
            My Location
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => refetch()}
            disabled={predLoading}
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </Button>
        </div>
      </div>

      {/* ── Map ───────────────────────────────────────────────────── */}
      <BarangayRiskMap
        livePredictions={undefined}
        prediction={prediction}
        height={600}
        userLocation={userLocation}
      >
        <ForecastOverlay selectedOffset={selectedOffset} />
      </BarangayRiskMap>

      {/* ── Decision Panel ────────────────────────────────────────── */}
      <ResidentDecisionPanel
        prediction={prediction}
        userLocation={userLocation}
      />
    </div>
  );
}
