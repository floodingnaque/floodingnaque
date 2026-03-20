/**
 * BarangayRiskMap Component (P1 - MUST HAVE)
 *
 * Leaflet map rendering all 16 Parañaque barangay polygons,
 * color-filled by risk level.  Click a polygon to see the risk
 * label, precipitation, and evacuation center via popover.
 */

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { memo, useMemo, useState } from "react";
import {
  MapContainer,
  Polygon,
  Popup,
  TileLayer,
  Tooltip,
} from "react-leaflet";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BARANGAYS, type BarangayData } from "@/config/paranaque";
import { ReportMapLayer } from "@/features/community/components/ReportMapLayer";
import { EvacuationMarkers } from "@/features/map/components/EvacuationMarkers";
import {
  MapLayerControl,
  type BaseMapType,
  type LayerVisibility,
} from "@/features/map/components/MapLayerControl";
import { SafeRouteLayer } from "@/features/map/components/SafeRouteLayer";
import { cn } from "@/lib/utils";
import type { PredictionResponse, RiskLevel } from "@/types";

// ---------------------------------------------------------------------------
// Leaflet icon fix (default marker icon assets)
// ---------------------------------------------------------------------------

// @ts-expect-error leaflet private property workaround
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "/leaflet/marker-icon-2x.png",
  iconUrl: "/leaflet/marker-icon.png",
  shadowUrl: "/leaflet/marker-shadow.png",
});

// ---------------------------------------------------------------------------
// Design tokens
// ---------------------------------------------------------------------------

import { RISK_FILL_HEX, RISK_HEX } from "@/lib/colors";

const RISK_COLORS: Record<
  BarangayData["floodRisk"],
  { fill: string; stroke: string; label: string; badge: string }
> = {
  low: {
    fill: RISK_FILL_HEX.safe,
    stroke: RISK_HEX.safe,
    label: "Low Risk",
    badge: "bg-risk-safe text-white",
  },
  moderate: {
    fill: RISK_FILL_HEX.alert,
    stroke: RISK_HEX.alert,
    label: "Moderate Risk",
    badge: "bg-risk-alert text-black",
  },
  high: {
    fill: RISK_FILL_HEX.critical,
    stroke: RISK_HEX.critical,
    label: "High Risk",
    badge: "bg-risk-critical text-white",
  },
};

/** Map center (Parañaque City) */
const MAP_CENTER: [number, number] = [14.4793, 121.0198];
const MAP_ZOOM = 13;

// ---------------------------------------------------------------------------
// Tile-layer configs for base-map switching & road overlay
// ---------------------------------------------------------------------------

const TILE_LAYERS: Record<
  BaseMapType,
  { url: string; attribution: string; maxZoom: number }
> = {
  standard: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "&copy; Esri, Maxar, Earthstar Geographics",
    maxZoom: 18,
  },
  topo: {
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenTopoMap (CC-BY-SA)",
    maxZoom: 17,
  },
};

/** Road-network label overlay — renders on top of any base map */
const ROAD_OVERLAY_URL =
  "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png";

// ---------------------------------------------------------------------------
// Dynamic risk overlay - if prediction data is present, override static risk
// ---------------------------------------------------------------------------

function riskForBarangay(
  brgy: BarangayData,
  livePredictions?: Map<string, RiskLevel>,
): BarangayData["floodRisk"] {
  if (!livePredictions?.has(brgy.key)) return brgy.floodRisk;
  const level = livePredictions.get(brgy.key)!;
  return level === 0 ? "low" : level === 1 ? "moderate" : "high";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface BarangayRiskMapProps {
  /** Optional live prediction overrides per barangay */
  livePredictions?: Map<string, RiskLevel>;
  /** Current global prediction (used for header subtitle) */
  prediction?: PredictionResponse | null;
  /** Optional map height (CSS value) */
  height?: string | number;
  className?: string;
}

export const BarangayRiskMap = memo(function BarangayRiskMap({
  livePredictions,
  prediction,
  height = 420,
  className,
}: BarangayRiskMapProps) {
  const heightMap: Record<string | number, string> = {
    "100%": "h-full",
    300: "h-[250px] sm:h-[300px]",
    350: "h-[280px] sm:h-[350px]",
    400: "h-[300px] sm:h-[400px]",
    420: "h-[300px] sm:h-[420px]",
    500: "h-[350px] sm:h-[500px]",
    600: "h-[400px] sm:h-[600px]",
  };
  const heightClass = heightMap[height] ?? "h-[300px] sm:h-[420px]";

  // GIS layer state
  const [baseMap, setBaseMap] = useState<BaseMapType>("standard");
  const [layers, setLayers] = useState<LayerVisibility>({
    boundaries: true,
    floodZones: true,
    evacuation: false,
    traffic: false,
    communityReports: false,
    safeRoute: false,
  });

  // Count at-risk barangays
  const riskCounts = useMemo(() => {
    let high = 0,
      moderate = 0,
      low = 0;
    for (const b of BARANGAYS) {
      const r = riskForBarangay(b, livePredictions);
      if (r === "high") high++;
      else if (r === "moderate") moderate++;
      else low++;
    }
    return { high, moderate, low };
  }, [livePredictions]);

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Barangay Flood Risk Map</CardTitle>
          <div className="flex gap-1.5 text-xs">
            <Badge
              variant="outline"
              className="bg-risk-safe/10 text-risk-safe border-risk-safe/30 font-normal"
            >
              {riskCounts.low} Low
            </Badge>
            <Badge
              variant="outline"
              className="bg-risk-alert/10 text-risk-alert border-risk-alert/30 font-normal"
            >
              {riskCounts.moderate} Alert
            </Badge>
            <Badge
              variant="outline"
              className="bg-risk-critical/10 text-risk-critical border-risk-critical/30 font-normal"
            >
              {riskCounts.high} High
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div
          className={cn("relative rounded-b-lg overflow-hidden", heightClass)}
          role="region"
          aria-label="Barangay flood risk map"
        >
          <MapContainer
            center={MAP_CENTER}
            zoom={MAP_ZOOM}
            scrollWheelZoom={true}
            className="h-full w-full z-0"
            attributionControl={false}
          >
            {/* Dynamic base-map tile layer */}
            <TileLayer
              key={baseMap}
              attribution={TILE_LAYERS[baseMap].attribution}
              url={TILE_LAYERS[baseMap].url}
              maxZoom={TILE_LAYERS[baseMap].maxZoom}
            />

            {/* Road-network / label overlay */}
            {layers.traffic && (
              <TileLayer
                key="road-overlay"
                url={ROAD_OVERLAY_URL}
                attribution="&copy; CARTO"
                opacity={0.85}
                zIndex={400}
              />
            )}

            {/* Barangay polygons — boundaries & flood-zone shading */}
            {(layers.boundaries || layers.floodZones) &&
              BARANGAYS.map((brgy) => {
                const risk = riskForBarangay(brgy, livePredictions);
                const colors = RISK_COLORS[risk];

                return (
                  <Polygon
                    key={brgy.key}
                    positions={brgy.polygon}
                    pathOptions={{
                      color: colors.stroke,
                      weight: layers.boundaries ? 2.5 : 0.5,
                      dashArray:
                        layers.boundaries && !layers.floodZones
                          ? "6 4"
                          : undefined,
                      fillColor: colors.stroke,
                      fillOpacity: layers.floodZones
                        ? risk === "high"
                          ? 0.35
                          : risk === "moderate"
                            ? 0.28
                            : 0.2
                        : 0,
                      opacity: layers.boundaries ? 0.9 : 0.4,
                    }}
                  >
                    <Tooltip direction="top" sticky>
                      <span className="font-semibold">{brgy.name}</span>
                    </Tooltip>
                    <Popup>
                      <div className="min-w-45 space-y-2 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-base">
                            {brgy.name}
                          </span>
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded text-xs font-semibold",
                              colors.badge,
                            )}
                          >
                            {colors.label}
                          </span>
                        </div>
                        <div className="text-muted-foreground space-y-1">
                          <p>Population: {brgy.population.toLocaleString()}</p>
                          <p>Zone: {brgy.zone}</p>
                          <p>Flood Events: {brgy.floodEvents}</p>
                          <p>Evacuation: {brgy.evacuationCenter}</p>
                          {prediction?.weather_data && (
                            <p>
                              Precipitation:{" "}
                              {prediction.weather_data.precipitation.toFixed(1)}{" "}
                              mm
                            </p>
                          )}
                        </div>
                      </div>
                    </Popup>
                  </Polygon>
                );
              })}

            {/* Evacuation-center markers */}
            {layers.evacuation && <EvacuationMarkers />}

            {/* Community flood reports */}
            {layers.communityReports && <ReportMapLayer />}

            {/* Safe evacuation routes */}
            {layers.safeRoute && <SafeRouteLayer />}
          </MapContainer>

          {/* Floating layer-control panel */}
          <MapLayerControl
            layers={layers}
            onLayerChange={setLayers}
            baseMap={baseMap}
            onBaseMapChange={setBaseMap}
          />
        </div>
      </CardContent>
    </Card>
  );
});
