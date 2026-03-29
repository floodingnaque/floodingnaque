/**
 * BarangayRiskMap Component (P1 - MUST HAVE)
 *
 * Leaflet map rendering all 16 Parañaque barangay polygons,
 * color-filled by risk level.  Click a polygon to see the risk
 * label, precipitation, and evacuation center via popover.
 */

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  Marker,
  Polygon,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BARANGAYS, type BarangayData } from "@/config/paranaque";
import { ReportMapLayer } from "@/features/community/components/ReportMapLayer";
import { EvacuationMarkers } from "@/features/map/components/EvacuationMarkers";
import { FloodDepthOverlay } from "@/features/map/components/FloodDepthOverlay";
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

/** Road-network label overlay - renders on top of any base map */
const ROAD_OVERLAY_URL =
  "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png";

// ---------------------------------------------------------------------------
// Data freshness floating badge
// ---------------------------------------------------------------------------

function DataFreshnessBadge({ timestamp }: { timestamp: string }) {
  const [, setTick] = useState(0);

  // Re-render every 30s to keep the "X ago" text current
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 30_000);
    return () => clearInterval(id);
  }, []);

  const diffMs = Date.now() - new Date(timestamp).getTime();
  const diffMin = Math.floor(diffMs / 60_000);

  let label: string;
  let isStale = false;
  if (diffMin < 1) {
    label = "Data updated just now";
  } else if (diffMin < 60) {
    label = `Data updated ${diffMin} min ago`;
    isStale = diffMin > 10;
  } else {
    const hrs = Math.floor(diffMin / 60);
    label = `Data updated ${hrs}h ago`;
    isStale = true;
  }

  return (
    <div
      className={cn(
        "absolute bottom-3 right-3 z-1000 rounded-md border px-2.5 py-1 text-[10px] font-mono shadow-sm backdrop-blur-sm",
        isStale
          ? "border-amber-400/60 bg-amber-50/90 text-amber-700 dark:bg-amber-950/80 dark:text-amber-300"
          : "border-border bg-background/90 text-muted-foreground",
      )}
    >
      {isStale && "⚠️ "}
      {label}
    </div>
  );
}

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
// Map fly-to helper (must be a child of MapContainer)
// ---------------------------------------------------------------------------

function FlyToUser({ position }: { position: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(position, 15);
  }, [map, position]);
  return null;
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
  /** User GPS location to display on the map */
  userLocation?: [number, number] | null;
  /** Additional Leaflet layers to render inside the MapContainer */
  children?: React.ReactNode;
  className?: string;
}

/** Blue location pin icon for the user's GPS position */
function createUserLocationIcon(): L.DivIcon {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="40" height="60">
      <defs>
        <filter id="loc-glow" x="-40%" y="-20%" width="180%" height="160%">
          <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#3b82f6" flood-opacity="0.5"/>
        </filter>
      </defs>
      <path filter="url(#loc-glow)" fill="#3b82f6"
        stroke="#fff" stroke-width="2"
        d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24C24 5.37 18.63 0 12 0z"/>
      <circle cx="12" cy="11" r="5" fill="#fff" opacity="0.9"/>
      <circle cx="12" cy="11" r="2.5" fill="#3b82f6"/>
    </svg>
  `;
  return L.divIcon({
    html: svg,
    className: "user-location-marker",
    iconSize: [40, 60],
    iconAnchor: [20, 60],
    popupAnchor: [0, -60],
  });
}

export const BarangayRiskMap = memo(function BarangayRiskMap({
  livePredictions,
  prediction,
  height = 420,
  userLocation: userLocationProp,
  children,
  className,
}: BarangayRiskMapProps) {
  // Auto-detect user location if not provided by parent
  const [autoLocation, setAutoLocation] = useState<[number, number] | null>(
    null,
  );

  const requestAutoLocation = useCallback(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setAutoLocation([pos.coords.latitude, pos.coords.longitude]);
      },
      () => {
        /* silently ignore errors */
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300_000 },
    );
  }, []);

  useEffect(() => {
    if (!userLocationProp) {
      requestAutoLocation();
    }
  }, [userLocationProp, requestAutoLocation]);

  const userLocation = userLocationProp ?? autoLocation;

  const userLocationIcon = useMemo(() => createUserLocationIcon(), []);
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
    evacuation: true,
    traffic: false,
    communityReports: true,
    safeRoute: false,
    floodDepth: true,
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

            {/* Barangay polygons - boundaries & flood-zone shading */}
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

            {/* Flood depth estimation */}
            <FloodDepthOverlay visible={layers.floodDepth} />

            {/* Additional layers from parent */}
            {children}

            {/* User GPS location */}
            {userLocation && <FlyToUser position={userLocation} />}
            {userLocation && (
              <Marker
                position={userLocation}
                icon={userLocationIcon}
                zIndexOffset={1000}
              >
                <Tooltip direction="top" offset={[0, -60]} permanent>
                  <span className="font-semibold text-xs inline-flex items-center gap-1">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#3b82f6"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                    You are here
                  </span>
                </Tooltip>
              </Marker>
            )}
          </MapContainer>

          {/* Floating layer-control panel */}
          <MapLayerControl
            layers={layers}
            onLayerChange={setLayers}
            baseMap={baseMap}
            onBaseMapChange={setBaseMap}
          />

          {/* Floating color legend */}
          {layers.floodZones && (
            <div className="absolute bottom-3 left-3 z-1000 rounded-lg border border-border bg-background/90 backdrop-blur-sm px-3 py-2 shadow-md">
              <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-1.5">
                Risk Level
              </div>
              <div className="flex flex-col gap-1">
                {(
                  [
                    ["low", "Low"],
                    ["moderate", "Alert"],
                    ["high", "High"],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key} className="flex items-center gap-2">
                    <span
                      className="inline-block h-3 w-5 rounded-sm border"
                      style={{
                        backgroundColor: RISK_COLORS[key].fill,
                        borderColor: RISK_COLORS[key].stroke,
                      }}
                    />
                    <span className="text-[10px] font-mono text-foreground">
                      {label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Data freshness badge */}
          {prediction?.timestamp && (
            <DataFreshnessBadge timestamp={prediction.timestamp} />
          )}
        </div>
      </CardContent>
    </Card>
  );
});
