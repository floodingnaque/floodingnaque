/**
 * Resident - Community Reports Page
 *
 * Submitted and verified flood reports from other residents, with
 * severity badges, status indicators, filter by barangay, and
 * "Verified by DRRMO" tags.
 */

import {
  CheckCircle,
  Clock,
  Droplets,
  Filter,
  MapPin,
  MessageSquare,
  Plus,
  RefreshCw,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useCommunityReports } from "@/features/resident";
import type { CommunityReport } from "@/types";

const SEVERITY_BADGE: Record<string, string> = {
  minor: "bg-green-500/10 text-green-700 border-green-500/30",
  moderate: "bg-amber-500/10 text-amber-700 border-amber-500/30",
  severe: "bg-red-500/10 text-red-700 border-red-500/30",
};

/** Map risk_label (Safe/Alert/Critical) to display severity key */
const RISK_TO_SEVERITY: Record<string, string> = {
  Safe: "minor",
  Alert: "moderate",
  Critical: "severe",
};

/** Derive severity from risk_label first, fall back to flood_height_cm */
function getSeverityKey(report: CommunityReport): string {
  if (report.risk_label && RISK_TO_SEVERITY[report.risk_label]) {
    return RISK_TO_SEVERITY[report.risk_label];
  }
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

export default function ResidentCommunityPage() {
  const { data: reports, isLoading, refetch } = useCommunityReports({});
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!reports) return [];
    if (!search.trim()) return reports;
    const q = search.toLowerCase();
    return reports.filter(
      (r: CommunityReport) =>
        r.barangay?.toLowerCase().includes(q) ||
        r.description?.toLowerCase().includes(q),
    );
  }, [reports, search]);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            Mga Ulat ng Komunidad / Community Reports
          </h2>
          <p className="text-sm text-muted-foreground">
            Verified flood reports from Parañaque residents
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => refetch()}
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </Button>
          <Button asChild size="sm" className="gap-2">
            <Link to="/resident/report">
              <Plus className="h-4 w-4" />
              Report
            </Link>
          </Button>
        </div>
      </div>

      {/* ── Search / Filter ───────────────────────────────────────── */}
      <div className="relative">
        <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-10"
          placeholder="Filter by barangay or keyword…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* ── Report List ───────────────────────────────────────────── */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((report: CommunityReport) => {
            const severityKey = getSeverityKey(report);

            return (
              <Card key={report.id}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    {report.photo_url ? (
                      <img
                        src={report.photo_url}
                        alt="Flood report"
                        className="h-16 w-16 rounded-lg object-cover shrink-0"
                      />
                    ) : (
                      <div className="h-16 w-16 rounded-lg bg-muted/50 flex items-center justify-center shrink-0">
                        <Droplets className="h-6 w-6 text-muted-foreground/40" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        {report.barangay && (
                          <span className="text-sm font-medium flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {report.barangay}
                          </span>
                        )}
                        <Badge
                          variant="outline"
                          className={SEVERITY_BADGE[severityKey]}
                        >
                          {severityKey.charAt(0).toUpperCase() +
                            severityKey.slice(1)}
                        </Badge>
                        {report.verified ? (
                          <Badge
                            variant="outline"
                            className="bg-green-500/10 text-green-700 border-green-500/30 text-[10px]"
                          >
                            <CheckCircle className="h-3 w-3 mr-0.5" />
                            Verified by DRRMO
                          </Badge>
                        ) : report.status === "pending" ? (
                          <Badge
                            variant="outline"
                            className="bg-amber-500/10 text-amber-700 border-amber-500/30 text-[10px]"
                          >
                            <Clock className="h-3 w-3 mr-0.5" />
                            Pending verification
                          </Badge>
                        ) : null}
                      </div>
                      {report.description && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
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
                          {report.created_at
                            ? timeAgo(report.created_at)
                            : "Recently"}
                        </span>
                        {report.confirmation_count > 0 && (
                          <span>
                            {report.confirmation_count} confirmation
                            {report.confirmation_count > 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <MessageSquare className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm font-medium">
              {search
                ? "No matching reports"
                : "Wala pang ulat / No reports yet"}
            </p>
            <p className="text-xs mt-1">
              {search
                ? "Try a different search term"
                : "Be the first to report - help others stay safe"}
            </p>
            {!search && (
              <Button
                asChild
                variant="outline"
                size="sm"
                className="mt-3 gap-2"
              >
                <Link to="/resident/report">
                  <Plus className="h-4 w-4" />
                  Report Flood
                </Link>
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
