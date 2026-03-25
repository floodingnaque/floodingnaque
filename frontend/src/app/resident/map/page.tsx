/**
 * Resident — Live Map Page
 *
 * Leaflet map centered on Parañaque City with:
 * - Barangay hazard overlay (colored by risk)
 * - Evacuation center markers
 * - GPS "my location" button
 * - Risk badge + layer legend
 */

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Crosshair, Layers, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvacuationCenters } from "@/features/evacuation";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { EvacuationMarkers, HazardOverlay, useHazardMap } from "@/features/map";
import { RISK_CONFIGS, type RiskLevel } from "@/types/api/prediction";

const PARANAQUE_CENTER: [number, number] = [14.4793, 121.0198];
const DEFAULT_ZOOM = 13;

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
  const { data: hazardData } = useHazardMap();
  const { isLoading: evacLoading } = useEvacuationCenters();
  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;

  const mapRef = useRef<L.Map | null>(null);
  const [userPos, setUserPos] = useState<[number, number] | null>(null);
  const [locating, setLocating] = useState(false);

  const handleLocate = useCallback(() => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords: [number, number] = [
          pos.coords.latitude,
          pos.coords.longitude,
        ];
        setUserPos(coords);
        mapRef.current?.flyTo(coords, 15);
        setLocating(false);
      },
      () => setLocating(false),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, []);

  const isLoading = predLoading || evacLoading;

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-4 w-full">
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
        <div className="flex gap-2">
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
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </Button>
        </div>
      </div>

      {/* ── Map ───────────────────────────────────────────────────── */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <Skeleton className="w-full aspect-video" />
          ) : (
            <div className="w-full" style={{ height: "60vh", minHeight: 350 }}>
              <MapContainer
                center={PARANAQUE_CENTER}
                zoom={DEFAULT_ZOOM}
                className="h-full w-full z-0"
                ref={mapRef}
                scrollWheelZoom
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {/* Barangay hazard overlay */}
                {hazardData?.features && (
                  <HazardOverlay
                    features={hazardData.features}
                    mode="hazard"
                    fillOpacity={0.35}
                  />
                )}

                {/* Evacuation center pins */}
                <EvacuationMarkers />

                {/* User position */}
                {userPos && (
                  <CircleMarker
                    center={userPos}
                    radius={8}
                    pathOptions={{
                      color: "#7c3aed",
                      fillColor: "#7c3aed",
                      fillOpacity: 0.8,
                      weight: 2,
                    }}
                  >
                    <Tooltip>Ikaw / You are here</Tooltip>
                  </CircleMarker>
                )}
              </MapContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Legend ─────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Legend / Gabay sa Mapa</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-green-500" />
              Safe / Ligtas
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-amber-500" />
              Alert / Alerto
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-red-500" />
              Critical / Kritikal
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-green-600" />
              Evac Center
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-purple-600" />
              Your Location
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
