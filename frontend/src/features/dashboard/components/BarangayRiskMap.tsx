/**
 * BarangayRiskMap Component (P1 — MUST HAVE)
 *
 * Leaflet map rendering all 16 Parañaque barangay polygons,
 * color-filled by risk level.  Click a polygon to see the risk
 * label, precipitation, and evacuation center via popover.
 */

import { memo, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Polygon,
  Popup,
  Tooltip,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BARANGAYS, type BarangayData } from '@/config/paranaque';
import type { PredictionResponse, RiskLevel } from '@/types';

// ---------------------------------------------------------------------------
// Leaflet icon fix (default marker icon assets)
// ---------------------------------------------------------------------------

// @ts-expect-error leaflet private property workaround
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// ---------------------------------------------------------------------------
// Design tokens
// ---------------------------------------------------------------------------

const RISK_COLORS: Record<BarangayData['floodRisk'], { fill: string; stroke: string; label: string; badge: string }> = {
  low: {
    fill: 'rgba(40, 167, 69, 0.30)',
    stroke: '#28A745',
    label: 'Low Risk',
    badge: 'bg-risk-safe text-white',
  },
  moderate: {
    fill: 'rgba(255, 193, 7, 0.35)',
    stroke: '#FFC107',
    label: 'Moderate Risk',
    badge: 'bg-risk-alert text-black',
  },
  high: {
    fill: 'rgba(220, 53, 69, 0.35)',
    stroke: '#DC3545',
    label: 'High Risk',
    badge: 'bg-risk-critical text-white',
  },
};

/** Map center (Parañaque City) */
const MAP_CENTER: [number, number] = [14.4793, 121.0198];
const MAP_ZOOM = 13;

// ---------------------------------------------------------------------------
// Dynamic risk overlay — if prediction data is present, override static risk
// ---------------------------------------------------------------------------

function riskForBarangay(
  brgy: BarangayData,
  livePredictions?: Map<string, RiskLevel>,
): BarangayData['floodRisk'] {
  if (!livePredictions?.has(brgy.key)) return brgy.floodRisk;
  const level = livePredictions.get(brgy.key)!;
  return level === 0 ? 'low' : level === 1 ? 'moderate' : 'high';
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
  const heightClass =
    height === '100%' ? 'h-full' :
    height === 300 ? 'h-[300px]' :
    height === 350 ? 'h-[350px]' :
    height === 400 ? 'h-[400px]' :
    height === 420 ? 'h-[420px]' :
    height === 500 ? 'h-[500px]' :
    height === 600 ? 'h-[600px]' :
    'h-[420px]';

  // Count at-risk barangays
  const riskCounts = useMemo(() => {
    let high = 0, moderate = 0, low = 0;
    for (const b of BARANGAYS) {
      const r = riskForBarangay(b, livePredictions);
      if (r === 'high') high++;
      else if (r === 'moderate') moderate++;
      else low++;
    }
    return { high, moderate, low };
  }, [livePredictions]);

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Barangay Flood Risk Map</CardTitle>
          <div className="flex gap-1.5 text-xs">
            <Badge variant="outline" className="bg-risk-safe/10 text-risk-safe border-risk-safe/30 font-normal">
              {riskCounts.low} Low
            </Badge>
            <Badge variant="outline" className="bg-risk-alert/10 text-risk-alert border-risk-alert/30 font-normal">
              {riskCounts.moderate} Alert
            </Badge>
            <Badge variant="outline" className="bg-risk-critical/10 text-risk-critical border-risk-critical/30 font-normal">
              {riskCounts.high} High
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div
          className={cn('relative rounded-b-lg overflow-hidden', heightClass)}
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
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {BARANGAYS.map((brgy) => {
              const risk = riskForBarangay(brgy, livePredictions);
              const colors = RISK_COLORS[risk];

              return (
                <Polygon
                  key={brgy.key}
                  positions={brgy.polygon}
                  pathOptions={{
                    fillColor: colors.fill.replace(/rgba?\([^)]+\)/, colors.stroke),
                    fillOpacity: risk === 'high' ? 0.35 : risk === 'moderate' ? 0.28 : 0.2,
                    color: colors.stroke,
                    weight: 2,
                  }}
                >
                  <Tooltip direction="top" sticky>
                    <span className="font-semibold">{brgy.name}</span>
                  </Tooltip>
                  <Popup>
                    <div className="min-w-45 space-y-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-base">{brgy.name}</span>
                        <span className={cn('px-2 py-0.5 rounded text-xs font-semibold', colors.badge)}>
                          {colors.label}
                        </span>
                      </div>
                      <div className="text-muted-foreground space-y-1">
                        <p>Population: {brgy.population.toLocaleString()}</p>
                        <p>Evacuation: {brgy.evacuationCenter}</p>
                        {prediction?.weather_data && (
                          <p>
                            Precipitation:{' '}
                            {prediction.weather_data.precipitation.toFixed(1)} mm
                          </p>
                        )}
                      </div>
                    </div>
                  </Popup>
                </Polygon>
              );
            })}
          </MapContainer>
        </div>
      </CardContent>
    </Card>
  );
});
