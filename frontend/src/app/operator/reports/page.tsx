/**
 * Operator - Community Reports Page
 *
 * Verification queue for citizen-submitted flood reports.
 * Shows report stats, filterable list with verify/flag actions.
 */

import { Check, Clock, FileText, Flag, MapPin, Search, X } from "lucide-react";
import { useMemo, useState } from "react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCommunityReports,
  useFlagReport,
  useReportStats,
  useVerifyReport,
} from "@/features/community";
import { cn } from "@/lib/utils";
import type { CommunityReport, ReportStatus } from "@/types/api/community";

const STATUS_CFG: Record<ReportStatus, { label: string; cls: string }> = {
  pending: {
    label: "Pending",
    cls: "bg-amber-500/10 text-amber-700 border-amber-300",
  },
  accepted: {
    label: "Verified",
    cls: "bg-green-500/10 text-green-700 border-green-300",
  },
  rejected: {
    label: "Dismissed",
    cls: "bg-gray-500/10 text-gray-600 border-gray-300",
  },
};

function ReportRow({
  report,
  onVerify,
  onReject,
  onFlag,
}: {
  report: CommunityReport;
  onVerify: (id: number) => void;
  onReject: (id: number) => void;
  onFlag: (id: number) => void;
}) {
  const statusCfg = STATUS_CFG[report.status];
  return (
    <div className="flex items-start justify-between gap-4 p-4 border rounded-lg hover:bg-muted/30 transition-colors">
      <div className="flex gap-3 min-w-0 flex-1">
        {report.photo_url && (
          <img
            src={report.photo_url}
            alt="Flood report"
            className="h-14 w-14 rounded-lg object-cover shrink-0"
          />
        )}
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium truncate">
              {report.description ?? "Flood report"}
            </span>
            <Badge
              variant="outline"
              className={cn("text-[10px] px-1.5", statusCfg?.cls)}
            >
              {statusCfg?.label}
            </Badge>
            {report.risk_label && (
              <Badge variant="secondary" className="text-[10px]">
                {report.risk_label}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
            {report.barangay && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {report.barangay}
              </span>
            )}
            {report.flood_height_cm != null && (
              <span>{report.flood_height_cm} cm flood height</span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {new Date(report.created_at).toLocaleDateString("en-PH", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            {report.credibility_score != null && (
              <span>
                Credibility: {Math.round(report.credibility_score * 100)}%
              </span>
            )}
            <span className="text-muted-foreground/70">
              {report.confirmation_count} confirms · {report.dispute_count}{" "}
              disputes
            </span>
          </div>
        </div>
      </div>
      {report.status === "pending" && (
        <div className="flex items-center gap-1 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="gap-1 text-xs text-green-600 dark:text-green-400"
            onClick={() => onVerify(report.id)}
          >
            <Check className="h-3 w-3" /> Verify
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="gap-1 text-xs"
            onClick={() => onReject(report.id)}
          >
            <X className="h-3 w-3" /> Dismiss
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="gap-1 text-xs text-red-500"
            onClick={() => onFlag(report.id)}
          >
            <Flag className="h-3 w-3" />
          </Button>
        </div>
      )}
    </div>
  );
}

export default function OperatorReportsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: reportsData, isLoading } = useCommunityReports({ hours: 168 });
  const { data: statsData } = useReportStats();
  const verify = useVerifyReport();
  const flag = useFlagReport();

  const reports: CommunityReport[] = useMemo(() => {
    if (!reportsData) return [];
    if (Array.isArray(reportsData)) return reportsData;
    if ("reports" in reportsData)
      return (reportsData as { reports: CommunityReport[] }).reports ?? [];
    if ("data" in reportsData)
      return (reportsData as { data: CommunityReport[] }).data ?? [];
    return [];
  }, [reportsData]);

  const stats = useMemo(() => {
    if (statsData && typeof statsData === "object") {
      const s = statsData as unknown as Record<string, number>;
      return {
        pending: s.pending ?? 0,
        verified: s.verified_today ?? s.verified ?? 0,
        total: s.total ?? reports.length,
      };
    }
    return {
      pending: reports.filter((r) => r.status === "pending").length,
      verified: reports.filter((r) => r.status === "accepted").length,
      total: reports.length,
    };
  }, [statsData, reports]);

  const filtered = useMemo(() => {
    let result = reports;
    if (statusFilter !== "all") {
      result = result.filter((r) => r.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (r) =>
          r.barangay?.toLowerCase().includes(q) ||
          r.description?.toLowerCase().includes(q) ||
          r.specific_location?.toLowerCase().includes(q),
      );
    }
    return result;
  }, [reports, statusFilter, search]);

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <Breadcrumb
        items={[
          { label: "Operations", href: "/operator" },
          { label: "Community Reports" },
        ]}
        className="mb-4"
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {stats.pending}
            </p>
            <p className="text-xs text-muted-foreground">Pending Review</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">
              {stats.verified}
            </p>
            <p className="text-xs text-muted-foreground">Verified</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-xs text-muted-foreground">Total Reports</p>
          </CardContent>
        </Card>
      </div>

      {/* Report Queue */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            Community Reports
          </CardTitle>
          <CardDescription>
            Verify, flag, or dismiss citizen-submitted flood reports
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-10"
                placeholder="Search by location, barangay, or description…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="accepted">Verified</SelectItem>
                <SelectItem value="rejected">Dismissed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* List */}
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full rounded-lg" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <Flag className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm font-medium">
                {search || statusFilter !== "all"
                  ? "No reports match your filters"
                  : "No community reports yet"}
              </p>
              <p className="text-xs mt-1">
                Reports submitted by residents will appear here for verification
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((report) => (
                <ReportRow
                  key={report.id}
                  report={report}
                  onVerify={(id) => verify.mutate({ id, status: "accepted" })}
                  onReject={(id) => verify.mutate({ id, status: "rejected" })}
                  onFlag={(id) => flag.mutate(id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
