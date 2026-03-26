/**
 * EvacuationMarkers Component
 *
 * Renders shelter/evacuation-center pin markers for all 16
 * barangays of Parañaque City on the Leaflet map.
 * Each marker shows the evacuation center name, barangay,
 * population, and flood risk classification.
 */

import { BARANGAYS } from "@/config/paranaque";
import { Home } from "lucide-react";
import L from "leaflet";
import { useMemo } from "react";
import { Marker, Popup, Tooltip } from "react-leaflet";

// ---------------------------------------------------------------------------
// Custom SVG evacuation-center icon (green pin with shelter silhouette)
// ---------------------------------------------------------------------------

function createEvacuationIcon(): L.DivIcon {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="28" height="42">
      <path fill="#16a34a" stroke="#ffffff" stroke-width="1.5"
        d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24C24 5.37 18.63 0 12 0z"/>
      <path fill="#ffffff" d="M12 6.5l-5.5 6.5h2.5v4h6v-4h2.5L12 6.5z"/>
    </svg>
  `;

  return L.divIcon({
    html: svg,
    className: "evacuation-marker",
    iconSize: [28, 42],
    iconAnchor: [14, 42],
    popupAnchor: [0, -42],
  });
}

const EVAC_ICON = createEvacuationIcon();

const RISK_CLASS: Record<string, string> = {
  high: "text-risk-critical font-semibold",
  moderate: "text-risk-alert font-semibold",
  low: "text-risk-safe font-semibold",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface EvacuationMarkersProps {
  /** Show name tooltip on hover (default: true) */
  showTooltips?: boolean;
}

/**
 * EvacuationMarkers - Green shelter-pin markers for every barangay
 *
 * @example
 * <MapContainer>
 *   <EvacuationMarkers />
 * </MapContainer>
 */
export function EvacuationMarkers({
  showTooltips = true,
}: EvacuationMarkersProps) {
  const markers = useMemo(
    () =>
      BARANGAYS.map((b) => ({
        key: b.key,
        position: [b.lat, b.lon] as [number, number],
        center: b.evacuationCenter,
        barangay: b.name,
        population: b.population,
        risk: b.floodRisk,
      })),
    [],
  );

  return (
    <>
      {markers.map((m) => (
        <Marker key={`evac-${m.key}`} position={m.position} icon={EVAC_ICON}>
          {showTooltips && (
            <Tooltip direction="top" offset={[0, -44]}>
              <strong>{m.center}</strong>
            </Tooltip>
          )}
          <Popup maxWidth={280}>
            <div className="min-w-50 space-y-1.5 text-sm">
              <p className="font-semibold text-risk-safe flex items-center gap-1.5">
                <Home className="h-4 w-4" /> Evacuation Center
              </p>
              <p className="font-medium text-gray-900 dark:text-gray-100">
                {m.center}
              </p>
              <div className="text-xs text-gray-500 dark:text-gray-400 space-y-0.5">
                <p>Barangay: {m.barangay}</p>
                <p>Population: {m.population.toLocaleString()}</p>
                <p>
                  Flood Risk:{" "}
                  <span className={RISK_CLASS[m.risk]}>
                    {m.risk.charAt(0).toUpperCase() + m.risk.slice(1)}
                  </span>
                </p>
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

export default EvacuationMarkers;
