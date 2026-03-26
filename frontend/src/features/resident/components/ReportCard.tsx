/**
 * ReportCard - Displays a single community flood report
 *
 * Renders status badge, location, description, flood height, and timestamp.
 * Used in My Reports list and potentially in community reports views.
 */

import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Droplets,
  Flag,
  MapPin,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { CommunityReport } from "@/types";

const FALLBACK_STATUS = {
  icon: Clock,
  label: "Pending",
  color: "bg-amber-500/10 text-amber-700 border-amber-500/30",
};

const STATUS_CONFIG: Record<
  string,
  { icon: React.ElementType; label: string; color: string }
> = {
  pending: FALLBACK_STATUS,
  accepted: {
    icon: CheckCircle,
    label: "Verified",
    color: "bg-green-500/10 text-green-700 border-green-500/30",
  },
  rejected: {
    icon: XCircle,
    label: "Dismissed",
    color: "bg-muted text-muted-foreground border-border",
  },
  flagged: {
    icon: Flag,
    label: "Flagged",
    color: "bg-red-500/10 text-red-700 border-red-500/30",
  },
};

const SEVERITY_BADGE: Record<string, { label: string; color: string }> = {
  minor: {
    label: "Minor",
    color: "bg-green-500/10 text-green-700 border-green-500/30",
  },
  moderate: {
    label: "Moderate",
    color: "bg-amber-500/10 text-amber-700 border-amber-500/30",
  },
  severe: {
    label: "Severe",
    color: "bg-red-500/10 text-red-700 border-red-500/30",
  },
};

const RISK_TO_SEVERITY: Record<string, string> = {
  Safe: "minor",
  Alert: "moderate",
  Critical: "severe",
};

function getSeverityKey(report: CommunityReport): string {
  const mapped = report.risk_label
    ? RISK_TO_SEVERITY[report.risk_label]
    : undefined;
  if (mapped) return mapped;
  if (report.flood_height_cm != null) {
    return report.flood_height_cm > 60
      ? "severe"
      : report.flood_height_cm > 15
        ? "moderate"
        : "minor";
  }
  return "moderate";
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

interface ReportCardProps {
  report: CommunityReport;
}

export function ReportCard({ report }: ReportCardProps) {
  const statusKey = report.verified ? "accepted" : (report.status ?? "pending");
  const status = STATUS_CONFIG[statusKey] ?? FALLBACK_STATUS;
  const StatusIcon = status.icon;
  const sevKey = getSeverityKey(report);
  const severity = SEVERITY_BADGE[sevKey] ?? {
    label: "Moderate",
    color: "bg-amber-500/10 text-amber-700 border-amber-500/30",
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {report.photo_url ? (
            <img
              src={report.photo_url}
              alt="Submitted flood report"
              className="h-14 w-14 rounded-lg object-cover shrink-0"
            />
          ) : (
            <div className="h-14 w-14 rounded-lg bg-muted/50 flex items-center justify-center shrink-0">
              <AlertTriangle className="h-5 w-5 text-muted-foreground/40" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono text-muted-foreground">
                #{String(report.id).padStart(4, "0")}
              </span>
              <Badge variant="outline" className={status.color}>
                <StatusIcon className="h-3 w-3 mr-1" />
                {status.label}
              </Badge>
              <Badge variant="outline" className={severity.color}>
                {severity.label}
              </Badge>
            </div>
            {report.barangay && (
              <p className="text-sm font-medium mt-1 flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {report.barangay}
              </p>
            )}
            {report.description && (
              <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
                {report.description}
              </p>
            )}
            <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
              {report.flood_height_cm != null && (
                <span className="flex items-center gap-1">
                  <Droplets className="h-3 w-3" />
                  {report.flood_height_cm} cm
                </span>
              )}
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {report.created_at ? timeAgo(report.created_at) : "Recently"}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
