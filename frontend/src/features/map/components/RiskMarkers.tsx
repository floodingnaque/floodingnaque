/**
 * RiskMarkers Component
 *
 * Renders alert markers on the map with color-coded icons based on risk level.
 * Each marker displays a popup with alert details.
 */

import { useMemo } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import type { Alert } from '@/types';
import type { RiskLevel } from '@/types/api/prediction';

export interface RiskMarkersProps {
  /** Array of alerts to display as markers */
  alerts: Alert[];
}

/**
 * Risk level color mapping (0=Safe/green, 1=Alert/yellow, 2=Critical/red)
 */
const RISK_COLORS: Record<RiskLevel, string> = {
  0: '#22c55e', // green-500 - Safe
  1: '#eab308', // yellow-500 - Alert
  2: '#ef4444', // red-500 - Critical
};

/**
 * Risk level label mapping
 */
const RISK_LABELS: Record<RiskLevel, string> = {
  0: 'Safe',
  1: 'Alert',
  2: 'Critical',
};

/**
 * Create a custom colored SVG marker icon
 */
function createMarkerIcon(riskLevel: RiskLevel): L.DivIcon {
  const color = RISK_COLORS[riskLevel];

  const svgIcon = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
      <path 
        fill="${color}" 
        stroke="#ffffff" 
        stroke-width="1.5"
        d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"
      />
      <circle cx="12" cy="9" r="3" fill="#ffffff" />
    </svg>
  `;

  return L.divIcon({
    html: svgIcon,
    className: 'custom-marker-icon',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
}

/**
 * Format date for display
 */
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/**
 * RiskMarkers - Renders colored markers for alerts on the map
 *
 * @example
 * <RiskMarkers alerts={alerts} />
 */
export function RiskMarkers({ alerts }: RiskMarkersProps) {
  // Filter alerts that have valid coordinates
  const validAlerts = useMemo(
    () =>
      alerts.filter(
        (alert) =>
          alert.latitude !== undefined &&
          alert.longitude !== undefined &&
          !isNaN(alert.latitude) &&
          !isNaN(alert.longitude)
      ),
    [alerts]
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
      {validAlerts.map((alert) => (
        <Marker
          key={alert.id}
          position={[alert.latitude!, alert.longitude!]}
          icon={markerIcons[alert.risk_level]}
        >
          <Popup className="risk-marker-popup">
            <div className="min-w-[200px] p-1">
              {/* Risk Level Badge */}
              <div className="mb-2 flex items-center gap-2">
                <span
                  className={`inline-block h-3 w-3 rounded-full ${
                    alert.risk_level === 0 ? 'bg-green-500' :
                    alert.risk_level === 1 ? 'bg-yellow-500' :
                    'bg-red-500'
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
                <strong>Coordinates:</strong>{' '}
                {alert.latitude?.toFixed(4)}, {alert.longitude?.toFixed(4)}
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
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}
                >
                  {alert.acknowledged ? 'Acknowledged' : 'Pending'}
                </span>
              </div>
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Custom styles for marker icon */}
      <style>{`
        .custom-marker-icon {
          background: transparent;
          border: none;
        }
        .risk-marker-popup .leaflet-popup-content {
          margin: 8px 12px;
        }
      `}</style>
    </>
  );
}

export default RiskMarkers;
