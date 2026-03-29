/**
 * ReportMapLayer Component
 *
 * Renders community flood reports as CircleMarkers on a Leaflet map.
 * Marker color reflects risk level, opacity reflects credibility,
 * and radius reflects flood depth.
 *
 * Listens for SSE `flood_report` events for real-time updates.
 */

import L from "leaflet";
import { useCallback, useEffect, useMemo, useState } from "react";
import { LayerGroup, Marker, Popup } from "react-leaflet";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RISK_HEX } from "@/lib/colors";
import type { CommunityReport } from "@/types";
import {
  useCommunityReports,
  useFlagReport,
  useVoteReport,
} from "../hooks/useCommunityReports";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const RISK_COLORS: Record<string, string> = {
  Safe: RISK_HEX.safe,
  Alert: RISK_HEX.alert,
  Critical: RISK_HEX.critical,
};

function markerOpacity(score: number | null): number {
  return 0.3 + (score ?? 0.5) * 0.7;
}

/**
 * Time-decay factor: newer reports are more opaque, older fade out.
 * Returns 1.0 for brand-new reports, down to 0.3 at maxHours.
 */
function timeDecayFactor(createdAt: string, maxHours: number): number {
  const ageMs = Date.now() - new Date(createdAt).getTime();
  const ageHours = ageMs / (1000 * 60 * 60);
  return Math.max(0.3, 1 - ageHours / maxHours);
}

/**
 * Combined opacity: credibility × time decay
 */
function combinedOpacity(
  score: number | null,
  createdAt: string,
  maxHours: number,
): number {
  return markerOpacity(score) * timeDecayFactor(createdAt, maxHours);
}

function markerRadius(floodHeightCm: number | null): number {
  if (floodHeightCm == null) return 5;
  if (floodHeightCm < 15) return 4;
  if (floodHeightCm < 30) return 6;
  if (floodHeightCm < 60) return 8;
  return 10;
}

/**
 * Create a DivIcon for community report markers — teardrop pin with wave icon
 */
function createReportIcon(color: string, opacity: number): L.DivIcon {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="36" height="54">
      <defs>
        <filter id="rep-s" x="-20%" y="-10%" width="140%" height="130%">
          <feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="0.25"/>
        </filter>
      </defs>
      <path filter="url(#rep-s)" fill="${color}" fill-opacity="${Math.min(opacity + 0.15, 1)}"
        stroke="#fff" stroke-width="1.5"
        d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24C24 5.37 18.63 0 12 0z"/>
      <g transform="translate(6,5)" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round">
        <path d="M0 7c2-2 4 2 6 0s4 2 6 0"/>
        <path d="M0 10.5c2-2 4 2 6 0s4 2 6 0" opacity="0.6"/>
      </g>
    </svg>
  `;
  return L.divIcon({
    html: svg,
    className: "report-marker",
    iconSize: [36, 54],
    iconAnchor: [18, 54],
    popupAnchor: [0, -54],
  });
}

function timeAgo(isoDate: string): string {
  const diffMs = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ReportMapLayerProps {
  /** Override default 6-hour window */
  hours?: number;
  /** Max reports to display */
  limit?: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReportMapLayer({
  hours = 24,
  limit = 50,
}: ReportMapLayerProps) {
  const { data, error } = useCommunityReports({ hours, limit });
  const voteMutation = useVoteReport();
  const flagMutation = useFlagReport();

  useEffect(() => {
    if (error) {
      toast.error("Failed to load community reports", {
        description: "Report service may be unavailable.",
        id: "community-reports-error",
      });
    }
  }, [error]);

  // ── SSE live updates ──
  const [sseReports, setSseReports] = useState<CommunityReport[]>([]);

  useEffect(() => {
    function handleSseReport(e: Event) {
      try {
        const detail = (e as CustomEvent).detail as CommunityReport;
        setSseReports((prev) => {
          if (prev.some((r) => r.id === detail.id)) return prev;
          return [detail, ...prev].slice(0, limit);
        });
      } catch {
        // ignore malformed events
      }
    }
    window.addEventListener("flood_report", handleSseReport);
    return () => window.removeEventListener("flood_report", handleSseReport);
  }, [limit]);

  // Merge API data + SSE data, deduplicated
  const reports: CommunityReport[] = (() => {
    const apiReports = data?.reports ?? [];
    const ids = new Set(apiReports.map((r) => r.id));
    const merged = [...apiReports, ...sseReports.filter((r) => !ids.has(r.id))];
    return merged;
  })();

  const handleVote = useCallback(
    (id: number, vote: "confirm" | "dispute") => {
      voteMutation.mutate({ id, vote });
    },
    [voteMutation],
  );

  const handleFlag = useCallback(
    (id: number) => {
      flagMutation.mutate(id);
    },
    [flagMutation],
  );

  if (reports.length === 0) return null;

  return (
    <LayerGroup>
      {reports.map((report) => {
        const rColor = RISK_COLORS[report.risk_label] ?? RISK_COLORS.Alert;
        const opacity = combinedOpacity(
          report.credibility_score,
          report.created_at,
          hours,
        );
        return (
          <PulsingReportMarker
            key={report.id}
            report={report}
            color={rColor}
            fillOpacity={opacity}
            onVote={handleVote}
            onFlag={handleFlag}
          />
        );
      })}
    </LayerGroup>
  );
}

// ---------------------------------------------------------------------------
// PulsingReportMarker – CircleMarker with pulsing outer ring animation
// ---------------------------------------------------------------------------

interface PulsingReportMarkerProps {
  report: CommunityReport;
  color: string;
  fillOpacity: number;
  onVote: (id: number, vote: "confirm" | "dispute") => void;
  onFlag: (id: number) => void;
}

function PulsingReportMarker({
  report,
  color,
  fillOpacity,
  onVote,
  onFlag,
}: PulsingReportMarkerProps) {
  const icon = useMemo(
    () => createReportIcon(color, fillOpacity),
    [color, fillOpacity],
  );

  return (
    <Marker position={[report.latitude, report.longitude]} icon={icon}>
      <Popup maxWidth={260} className="report-popup">
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold">
              {report.barangay ?? "Unknown"}
            </span>
            <span className="text-xs text-gray-500">
              {timeAgo(report.created_at)}
            </span>
          </div>
          {report.flood_height_cm != null && (
            <p className="text-xs text-gray-600">
              Flood height: ~{report.flood_height_cm} cm
            </p>
          )}
          {report.description && (
            <p className="text-xs text-gray-600 line-clamp-2">
              {report.description}
            </p>
          )}
          <div className="flex items-center gap-2">
            {report.verified ? (
              <Badge variant="default" className="text-xs bg-risk-safe">
                ✓ Verified
              </Badge>
            ) : (report.credibility_score ?? 0) >= 0.6 ? (
              <Badge variant="secondary" className="text-xs">
                AI Scored: {((report.credibility_score ?? 0) * 100).toFixed(0)}%
              </Badge>
            ) : (
              <Badge
                variant="outline"
                className="text-xs border-amber-400 text-amber-600"
              >
                Pending
              </Badge>
            )}
          </div>
          {report.photo_url && (
            <img
              src={report.photo_url}
              alt="Flood evidence"
              width={400}
              height={224}
              className="w-full rounded max-h-28 object-cover"
              loading="lazy"
              decoding="async"
            />
          )}
          <div className="flex items-center gap-2 pt-1">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={() => onVote(report.id, "confirm")}
            >
              👍 {report.confirmation_count}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={() => onVote(report.id, "dispute")}
            >
              👎 {report.dispute_count}
            </Button>
            <button
              className="ml-auto text-xs text-destructive hover:underline"
              onClick={() => onFlag(report.id)}
            >
              Report Abuse
            </button>
          </div>
        </div>
      </Popup>
    </Marker>
  );
}
