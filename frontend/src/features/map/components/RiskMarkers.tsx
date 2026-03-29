/**
 * RiskMarkers Component
 *
 * Renders alert markers on the map with color-coded icons based on risk level.
 * Each marker displays a popup with alert details.
 */

import { RISK_HEX } from "@/lib/colors";
import type { Alert } from "@/types";
import type { RiskLevel } from "@/types/api/prediction";
import L from "leaflet";
import { memo, useMemo } from "react";
import { Marker, Popup } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

export interface RiskMarkersProps {
  /** Array of alerts to display as markers */
  alerts: Alert[];
}

/**
 * Risk level color mapping (0=Safe/green, 1=Alert/yellow, 2=Critical/red)
 */
const RISK_COLORS: Record<RiskLevel, string> = {
  0: RISK_HEX.safe,
  1: RISK_HEX.alert,
  2: RISK_HEX.critical,
};

/**
 * Risk level label mapping
 */
const RISK_LABELS: Record<RiskLevel, string> = {
  0: "Safe",
  1: "Alert",
  2: "Critical",
};

/** Parañaque City approximate bounding box */
const PARANAQUE_BOUNDS = {
  latMin: 14.3,
  latMax: 14.6,
  lngMin: 120.9,
  lngMax: 121.1,
} as const;

function isInBounds(lat: number, lng: number): boolean {
  return (
    lat >= PARANAQUE_BOUNDS.latMin &&
    lat <= PARANAQUE_BOUNDS.latMax &&
    lng >= PARANAQUE_BOUNDS.lngMin &&
    lng <= PARANAQUE_BOUNDS.lngMax
  );
}

/**
 * Create a custom colored SVG marker icon with inner symbol
 */
function createMarkerIcon(riskLevel: RiskLevel): L.DivIcon {
  const color = RISK_COLORS[riskLevel];
  const label = RISK_LABELS[riskLevel];
  const isCritical = riskLevel === 2;

  // Safe = checkmark, Alert = exclamation, Critical = X
  const innerSymbol =
    riskLevel === 0
      ? `<path d="M10.5 12.5l1.5 1.5 3-3" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>`
      : riskLevel === 1
        ? `<g fill="${color}"><rect x="11.25" y="6.5" width="1.5" height="4" rx="0.75"/><circle cx="12" cy="12" r="0.9"/></g>`
        : `<g stroke="${color}" stroke-width="1.5" stroke-linecap="round"><line x1="10" y1="7.5" x2="14" y2="11.5"/><line x1="14" y1="7.5" x2="10" y2="11.5"/></g>`;

  const svgIcon = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="30" height="45" role="img" aria-label="${label} risk marker">
      <title>${label} risk marker</title>
      <defs>
        <filter id="risk-shadow-${riskLevel}" x="-20%" y="-10%" width="140%" height="130%">
          <feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#000" flood-opacity="0.3"/>
        </filter>
      </defs>
      <path filter="url(#risk-shadow-${riskLevel})" fill="${color}" stroke="#fff" stroke-width="1.5"
        d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24C24 5.37 18.63 0 12 0z"/>
      <circle cx="12" cy="9.5" r="5" fill="#fff"/>
      ${innerSymbol}
    </svg>
  `;

  return L.divIcon({
    html: svgIcon,
    className: isCritical
      ? "custom-marker-icon marker-pulse-critical"
      : "custom-marker-icon",
    iconSize: [30, 45],
    iconAnchor: [15, 45],
    popupAnchor: [0, -45],
  });
}

/**
 * Format date for display
 */
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/**
 * Create a custom cluster icon showing alert count + dominant risk color
 */
function createClusterIcon(cluster: L.MarkerCluster): L.DivIcon {
  const childMarkers = cluster.getAllChildMarkers();
  const count = childMarkers.length;

  // Determine dominant risk color by highest severity in cluster
  let maxRisk: RiskLevel = 0;
  for (const m of childMarkers) {
    const risk = (m.options as { riskLevel?: RiskLevel }).riskLevel ?? 0;
    if (risk > maxRisk) maxRisk = risk;
  }
  const color = RISK_COLORS[maxRisk];
  const size = count < 10 ? 36 : count < 50 ? 44 : 52;
  const half = size / 2;
  const fontSize = count < 10 ? 12 : count < 50 ? 13 : 14;

  return L.divIcon({
    html: `
      <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
        <circle cx="${half}" cy="${half}" r="${half - 1}" fill="${color}" fill-opacity="0.85" stroke="#fff" stroke-width="2"/>
        <circle cx="${half}" cy="${half}" r="${half - 5}" fill="${color}" fill-opacity="0.4" stroke="none"/>
        <text x="${half}" y="${half}" text-anchor="middle" dominant-baseline="central"
          fill="#fff" font-weight="700" font-size="${fontSize}" font-family="system-ui, sans-serif">${count}</text>
      </svg>
    `,
    className: "custom-cluster-icon",
    iconSize: L.point(size, size),
  });
}

/**
 * RiskMarkers - Renders clustered colored markers for alerts on the map
 *
 * @example
 * <RiskMarkers alerts={alerts} />
 */
export const RiskMarkers = memo(function RiskMarkers({
  alerts,
}: RiskMarkersProps) {
  // Filter alerts that have valid coordinates
  const validAlerts = useMemo(
    () =>
      alerts.filter(
        (alert) =>
          alert.latitude !== undefined &&
          alert.longitude !== undefined &&
          !isNaN(alert.latitude) &&
          !isNaN(alert.longitude) &&
          isInBounds(alert.latitude, alert.longitude),
      ),
    [alerts],
  );

  // Memoize marker icons
  const markerIcons = useMemo(() => {
    const icons: Record<RiskLevel, L.DivIcon> = {
      0: createMarkerIcon(0),
      1: createMarkerIcon(1),
      2: createMarkerIcon(2),
    };
    return icons;
  }, []);

  if (validAlerts.length === 0) {
    return null;
  }

  return (
    <>
      <MarkerClusterGroup
        iconCreateFunction={createClusterIcon}
        maxClusterRadius={50}
        spiderfyOnMaxZoom
        showCoverageOnHover={false}
        zoomToBoundsOnClick
      >
        {validAlerts.map((alert) => (
          <Marker
            key={alert.id}
            position={[alert.latitude!, alert.longitude!]}
            icon={markerIcons[alert.risk_level]}
            // @ts-expect-error custom option for cluster icon color
            riskLevel={alert.risk_level}
          >
            <Popup className="risk-marker-popup">
              <div className="min-w-50 p-1">
                {/* Risk Level Badge */}
                <div className="mb-2 flex items-center gap-2">
                  <span
                    className={`inline-block h-3 w-3 rounded-full ${
                      alert.risk_level === 0
                        ? "bg-risk-safe"
                        : alert.risk_level === 1
                          ? "bg-risk-alert"
                          : "bg-risk-critical"
                    }`}
                  />
                  <span className="font-semibold text-sm">
                    {RISK_LABELS[alert.risk_level]}
                  </span>
                </div>

                {/* Alert Message */}
                <p className="mb-2 text-sm text-gray-700">{alert.message}</p>

                {/* Location */}
                {alert.location && (
                  <p className="mb-1 text-xs text-gray-500">
                    <strong>Location:</strong> {alert.location}
                  </p>
                )}

                {/* Coordinates */}
                <p className="mb-1 text-xs text-gray-500">
                  <strong>Coordinates:</strong> {alert.latitude?.toFixed(4)},{" "}
                  {alert.longitude?.toFixed(4)}
                </p>

                {/* Triggered Time */}
                <p className="mb-1 text-xs text-gray-500">
                  <strong>Triggered:</strong> {formatDate(alert.triggered_at)}
                </p>

                {/* Expires Time */}
                {alert.expires_at && (
                  <p className="text-xs text-gray-500">
                    <strong>Expires:</strong> {formatDate(alert.expires_at)}
                  </p>
                )}

                {/* Acknowledged Status */}
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                      alert.acknowledged
                        ? "bg-risk-safe/15 text-risk-safe"
                        : "bg-risk-alert/15 text-risk-alert"
                    }`}
                  >
                    {alert.acknowledged ? "Acknowledged" : "Pending"}
                  </span>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MarkerClusterGroup>

      {/* Custom styles for marker icon */}
      <style>{`
        .custom-marker-icon {
          background: transparent;
          border: none;
        }
        .custom-cluster-icon {
          background: transparent;
          border: none;
        }
        .risk-marker-popup .leaflet-popup-content {
          margin: 8px 12px;
        }
      `}</style>
    </>
  );
});

export default RiskMarkers;
