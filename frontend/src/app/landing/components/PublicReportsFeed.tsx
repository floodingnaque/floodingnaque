/**
 * PublicReportsFeed
 *
 * Live feed of recent community-submitted flood reports visible to
 * everyone on the landing page. Fetches from the public
 * GET /api/v1/reports endpoint (no auth required) and auto-refreshes
 * every 2 minutes. Includes report stats banner, vote buttons,
 * and a "Submit a Report" CTA.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCommunityReports,
  useReportStats,
  useVoteReport,
} from "@/features/community/hooks/useCommunityReports";
import { cn } from "@/lib/utils";
import { FLOOD_HEIGHT_OPTIONS, type CommunityReport } from "@/types";
import {
  Camera,
  CheckCircle,
  Clock,
  Droplets,
  MapPin,
  MessageSquare,
  ThumbsDown,
  ThumbsUp,
  Waves,
} from "lucide-react";
import { Link } from "react-router-dom";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function floodHeightLabel(cm: number | null): string | null {
  if (cm === null) return null;
  const match = FLOOD_HEIGHT_OPTIONS.find(
    (o) => o.value !== null && Math.abs(o.value - cm) < 10,
  );
  return match ? `${match.label} (~${cm}cm)` : `${cm}cm`;
}

const RISK_STYLE: Record<string, { dot: string; badge: string }> = {
  Critical: {
    dot: "bg-risk-critical",
    badge: "bg-risk-critical/10 text-risk-critical border-risk-critical/30",
  },
  Alert: {
    dot: "bg-risk-alert",
    badge: "bg-risk-alert/10 text-risk-alert border-risk-alert/30",
  },
  Safe: {
    dot: "bg-risk-safe",
    badge: "bg-risk-safe/10 text-risk-safe border-risk-safe/30",
  },
};

// ---------------------------------------------------------------------------
// Single report card
// ---------------------------------------------------------------------------

function ReportCard({ report }: { report: CommunityReport }) {
  const voteMutation = useVoteReport();
  const style: { dot: string; badge: string } = RISK_STYLE[
    report.risk_label
  ] ?? {
    dot: "bg-risk-safe",
    badge: "bg-risk-safe/10 text-risk-safe border-risk-safe/30",
  };
  const height = floodHeightLabel(report.flood_height_cm);

  return (
    <div className="rounded-lg border border-border/40 bg-background p-3.5 space-y-2.5 transition-shadow hover:shadow-sm">
      {/* Header: risk dot + barangay + time */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={cn("h-2.5 w-2.5 rounded-full shrink-0", style.dot)}
          />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <MapPin className="h-3 w-3 text-muted-foreground shrink-0" />
              <span className="text-sm font-medium truncate">
                {report.barangay ?? "Unknown location"}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Badge
            variant="outline"
            className={cn("text-[10px] h-5", style.badge)}
          >
            {report.risk_label}
          </Badge>
          <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
            <Clock className="h-2.5 w-2.5" />
            {timeAgo(report.created_at)}
          </span>
        </div>
      </div>

      {/* Description */}
      {report.description && (
        <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
          {report.description}
        </p>
      )}

      {/* Metadata row: flood height, photo, credibility */}
      <div className="flex items-center gap-3 flex-wrap text-[10px] text-muted-foreground">
        {height && (
          <span className="flex items-center gap-1">
            <Droplets className="h-3 w-3" />
            {height}
          </span>
        )}
        {report.photo_url && (
          <span className="flex items-center gap-1">
            <Camera className="h-3 w-3" />
            Photo attached
          </span>
        )}
        {report.verified && (
          <span className="flex items-center gap-1 text-risk-safe">
            <CheckCircle className="h-3 w-3" />
            Verified
          </span>
        )}
        {report.credibility_score !== null && (
          <span
            className={cn(
              "font-medium",
              report.credibility_score >= 0.8
                ? "text-risk-safe"
                : report.credibility_score >= 0.6
                  ? "text-risk-alert"
                  : "text-muted-foreground",
            )}
          >
            {Math.round(report.credibility_score * 100)}% credibility
          </span>
        )}
      </div>

      {/* Vote buttons */}
      <div className="flex items-center gap-2 pt-0.5">
        <button
          type="button"
          onClick={() =>
            voteMutation.mutate({ id: report.id, vote: "confirm" })
          }
          disabled={voteMutation.isPending}
          className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-risk-safe transition-colors"
        >
          <ThumbsUp className="h-3 w-3" />
          <span className="tabular-nums">{report.confirmation_count}</span>
        </button>
        <button
          type="button"
          onClick={() =>
            voteMutation.mutate({ id: report.id, vote: "dispute" })
          }
          disabled={voteMutation.isPending}
          className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-risk-critical transition-colors"
        >
          <ThumbsDown className="h-3 w-3" />
          <span className="tabular-nums">{report.dispute_count}</span>
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stats banner
// ---------------------------------------------------------------------------

function StatsBanner() {
  const { data, isLoading } = useReportStats({ hours: 24 });

  if (isLoading) {
    return (
      <div className="flex gap-3 mb-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 flex-1 rounded-lg" />
        ))}
      </div>
    );
  }

  const stats = data?.stats;
  if (!stats) return null;

  const items = [
    { label: "Total (24h)", value: stats.total, cls: "text-foreground" },
    { label: "Verified", value: stats.verified, cls: "text-risk-safe" },
    { label: "Pending", value: stats.pending, cls: "text-risk-alert" },
    { label: "Critical", value: stats.critical, cls: "text-risk-critical" },
  ];

  return (
    <div className="grid grid-cols-4 gap-2 mb-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-lg border border-border/40 bg-muted/20 p-2.5 text-center"
        >
          <p className={cn("text-lg font-bold tabular-nums", item.cls)}>
            {item.value}
          </p>
          <p className="text-[9px] text-muted-foreground">{item.label}</p>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function PublicReportsFeed() {
  const { data, isLoading } = useCommunityReports({
    limit: 10,
    hours: 24,
  });

  const reports: CommunityReport[] = data?.reports ?? [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Waves className="h-4 w-4 text-muted-foreground" />
            Community Flood Reports
          </CardTitle>
          <Badge variant="outline" className="text-[10px]">
            <MessageSquare className="h-3 w-3 mr-1" />
            Live Feed
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Real-time flood reports submitted by residents in the last 24 hours.
          Anyone can submit a report.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats banner */}
        <StatsBanner />

        {/* Reports list */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="rounded-lg border p-3.5 space-y-2">
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            ))}
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-8">
            <Waves className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              No flood reports in the last 24 hours
            </p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              This is a good sign - no active flooding reported
            </p>
          </div>
        ) : (
          <div className="space-y-2.5 max-h-120 overflow-y-auto pr-1 scrollbar-thin">
            {reports.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </div>
        )}

        {/* Submit CTA */}
        <div className="rounded-lg bg-muted/30 p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-foreground">
              Want to submit a report?
            </p>
            <p className="text-xs text-muted-foreground">Get verified now!</p>
          </div>
          <Button asChild size="sm" variant="outline" className="shrink-0">
            <Link to="/login">Submit a Report</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
