/**
 * ReportMapLayer Component
 *
 * Renders community flood reports as CircleMarkers on a Leaflet map.
 * Marker color reflects risk level, opacity reflects credibility,
 * and radius reflects flood depth.
 *
 * Listens for SSE `flood_report` events for real-time updates.
 */

import { useCallback, useEffect, useState } from "react";
import { CircleMarker, LayerGroup, Popup } from "react-leaflet";

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
  if (floodHeightCm == null) return 8;
  if (floodHeightCm < 15) return 6;
  if (floodHeightCm < 30) return 9;
  if (floodHeightCm < 60) return 12;
  return 16;
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

export function ReportMapLayer({ hours = 6, limit = 50 }: ReportMapLayerProps) {
  const { data } = useCommunityReports({ hours, limit });
  const voteMutation = useVoteReport();
  const flagMutation = useFlagReport();

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
      {reports.map((report) => (
        <CircleMarker
          key={report.id}
          center={[report.latitude, report.longitude]}
          radius={markerRadius(report.flood_height_cm)}
          pathOptions={{
            color: RISK_COLORS[report.risk_label] ?? RISK_COLORS.Alert,
            fillColor: RISK_COLORS[report.risk_label] ?? RISK_COLORS.Alert,
            fillOpacity: combinedOpacity(
              report.credibility_score,
              report.created_at,
              hours,
            ),
            weight: 2,
          }}
        >
          <Popup maxWidth={260} className="report-popup">
            <div className="space-y-2 text-sm">
              {/* Header */}
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold">
                  {report.barangay ?? "Unknown"}
                </span>
                <span className="text-xs text-gray-500">
                  {timeAgo(report.created_at)}
                </span>
              </div>

              {/* Flood info */}
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

              {/* Credibility badge */}
              <div className="flex items-center gap-2">
                {report.verified ? (
                  <Badge variant="default" className="text-xs bg-risk-safe">
                    ✓ Verified
                  </Badge>
                ) : (report.credibility_score ?? 0) >= 0.6 ? (
                  <Badge variant="secondary" className="text-xs">
                    AI Scored:{" "}
                    {((report.credibility_score ?? 0) * 100).toFixed(0)}%
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

              {/* Photo */}
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

              {/* Vote buttons + counts */}
              <div className="flex items-center gap-2 pt-1">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  onClick={() => handleVote(report.id, "confirm")}
                >
                  👍 {report.confirmation_count}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  onClick={() => handleVote(report.id, "dispute")}
                >
                  👎 {report.dispute_count}
                </Button>
                <button
                  className="ml-auto text-xs text-destructive hover:underline"
                  onClick={() => handleFlag(report.id)}
                >
                  Report Abuse
                </button>
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </LayerGroup>
  );
}
