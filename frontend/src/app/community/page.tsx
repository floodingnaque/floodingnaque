/**
 * Community Reports Page
 *
 * Displays crowdsourced flood reports with live stats, filters,
 * paginated card list with admin actions, and submit form.
 */

import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  Camera,
  CheckCircle,
  Clock,
  Droplets,
  Eye,
  Filter,
  Flag,
  Loader2,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Users2,
  XCircle,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { GlassCard } from "@/components/ui/glass-card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BARANGAYS } from "@/config/paranaque";
import { ReportSubmitModal } from "@/features/community/components/ReportSubmitModal";
import {
  useCommunityReports,
  useFlagReport,
  useReportRealtimeSync,
  useReportStats,
  useVerifyReport,
} from "@/features/community/hooks/useCommunityReports";
import type { ReportListParams } from "@/features/community/services/communityApi";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { useUser } from "@/state";
import type { CommunityReport } from "@/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const RISK_BADGE: Record<string, { className: string; label: string }> = {
  Safe: {
    className: "bg-risk-safe/15 text-risk-safe",
    label: "Safe",
  },
  Alert: {
    className: "bg-risk-alert/15 text-risk-alert",
    label: "Alert",
  },
  Critical: {
    className: "bg-risk-critical/15 text-risk-critical",
    label: "Critical",
  },
};

const STATUS_BADGE: Record<string, { className: string; label: string }> = {
  pending: {
    className: "bg-risk-alert/15 text-risk-alert",
    label: "Pending",
  },
  accepted: {
    className: "bg-risk-safe/15 text-risk-safe",
    label: "Verified",
  },
  rejected: {
    className: "bg-destructive/15 text-destructive",
    label: "Dismissed",
  },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function CommunityPage() {
  const [submitOpen, setSubmitOpen] = useState(false);
  const [barangay, setBarangay] = useState<string>("");
  const [hours, setHours] = useState<number>(24);
  const [status, setStatus] = useState<string>("");
  const [selectedReport, setSelectedReport] = useState<CommunityReport | null>(
    null,
  );

  const user = useUser();
  const isAdmin = user?.role === "admin";

  // Real-time sync: listen for cross-tab report changes
  useReportRealtimeSync();

  const openReport = useCallback((report: CommunityReport) => {
    setSelectedReport(report);
  }, []);

  const handleBarangayChange = (v: string) => setBarangay(v === "all" ? "" : v);
  const handleStatusChange = (v: string) => setStatus(v === "all" ? "" : v);

  const params: ReportListParams = useMemo(
    () => ({
      ...(barangay && { barangay }),
      hours,
      ...(status && { status }),
      limit: 50,
    }),
    [barangay, hours, status],
  );

  const {
    data,
    isLoading,
    isError,
    refetch: refetchReports,
  } = useCommunityReports(params);
  const reports = useMemo(() => data?.reports ?? [], [data]);

  // Live stats from the dedicated stats endpoint
  const statsParams = useMemo(
    () => ({ hours, ...(barangay && { barangay }) }),
    [hours, barangay],
  );
  const { data: statsData, refetch: refetchStats } =
    useReportStats(statsParams);
  const stats = statsData?.stats ?? {
    total: 0,
    verified: 0,
    pending: 0,
    critical: 0,
  };

  // Admin action mutations
  const verifyMutation = useVerifyReport();
  const flagMutation = useFlagReport();

  const handleVerify = (id: number) => {
    verifyMutation.mutate(
      { id, status: "accepted" },
      {
        onSuccess: () => {
          toast.success("Report verified");
          refetchReports();
          refetchStats();
        },
        onError: () => toast.error("Failed to verify report"),
      },
    );
  };

  const handleDismiss = (id: number) => {
    verifyMutation.mutate(
      { id, status: "rejected" },
      {
        onSuccess: () => {
          toast.success("Report dismissed");
          refetchReports();
          refetchStats();
        },
        onError: () => toast.error("Failed to dismiss report"),
      },
    );
  };

  const handleFlag = (id: number) => {
    flagMutation.mutate(id, {
      onSuccess: () => {
        toast.success("Report flagged");
        refetchReports();
        refetchStats();
      },
      onError: () => toast.error("Failed to flag report"),
    });
  };

  const sectionRef = useRef<HTMLDivElement>(null);
  const inView = useInView(sectionRef, { once: true, amount: 0.1 });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <PageHeader
          icon={Users2}
          title="Community Reports"
          subtitle="Crowdsourced flood reports from residents across Parañaque City"
        />
      </div>

      {/* Stats + Filters + Reports */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={sectionRef}>
          <SectionHeading
            label="Crowdsourced Data"
            title="Recent Flood Reports"
            subtitle="View and filter community-submitted flood observations. Reports are verified by the system for credibility."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={inView ? "show" : undefined}
            className="space-y-6"
          >
            {/* Stats Row - live from /stats endpoint */}
            <motion.div
              variants={fadeUp}
              className="grid grid-cols-2 md:grid-cols-4 gap-4"
            >
              <GlassCard className="p-4 text-center">
                <p className="text-2xl font-bold text-primary">{stats.total}</p>
                <p className="text-xs text-muted-foreground">Total Reports</p>
              </GlassCard>
              <GlassCard className="p-4 text-center">
                <p className="text-2xl font-bold text-risk-safe">
                  {stats.verified}
                </p>
                <p className="text-xs text-muted-foreground">Verified</p>
              </GlassCard>
              <GlassCard className="p-4 text-center">
                <p className="text-2xl font-bold text-risk-alert">
                  {stats.pending}
                </p>
                <p className="text-xs text-muted-foreground">Pending</p>
              </GlassCard>
              <GlassCard className="p-4 text-center">
                <p className="text-2xl font-bold text-risk-critical">
                  {stats.critical}
                </p>
                <p className="text-xs text-muted-foreground">Critical</p>
              </GlassCard>
            </motion.div>

            {/* Filters */}
            <motion.div variants={fadeUp}>
              <GlassCard className="p-4">
                <div className="flex flex-wrap items-end gap-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <Filter className="h-4 w-4" />
                    Filters
                  </div>

                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">
                      Barangay
                    </span>
                    <Select
                      value={barangay || "all"}
                      onValueChange={handleBarangayChange}
                    >
                      <SelectTrigger className="w-44 h-8 text-xs">
                        <SelectValue placeholder="All barangays" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        {BARANGAYS.map((b) => (
                          <SelectItem key={b.key} value={b.name}>
                            {b.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">
                      Time Range
                    </span>
                    <Select
                      value={String(hours)}
                      onValueChange={(v) => setHours(Number(v))}
                    >
                      <SelectTrigger className="w-32 h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="24">Last 24h</SelectItem>
                        <SelectItem value="168">Last 7 days</SelectItem>
                        <SelectItem value="720">Last 30 days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">
                      Status
                    </span>
                    <Select
                      value={status || "all"}
                      onValueChange={handleStatusChange}
                    >
                      <SelectTrigger className="w-32 h-8 text-xs">
                        <SelectValue placeholder="All" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="accepted">Verified</SelectItem>
                        <SelectItem value="rejected">Dismissed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center gap-2 ml-auto">
                    <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      <span className="relative flex h-2 w-2">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-risk-safe opacity-75" />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-risk-safe" />
                      </span>
                      Live
                    </div>
                    <Button
                      size="sm"
                      className="h-8"
                      onClick={() => setSubmitOpen(true)}
                    >
                      Report Flood
                    </Button>
                  </div>
                </div>
              </GlassCard>
            </motion.div>

            {/* Report Cards */}
            <motion.div variants={fadeUp}>
              {isLoading ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <GlassCard
                      key={`skeleton-${i}`}
                      className="p-4 h-40 animate-pulse"
                    />
                  ))}
                </div>
              ) : isError ? (
                <GlassCard className="p-12 text-center">
                  <AlertTriangle className="mx-auto h-10 w-10 text-destructive/50" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    Failed to load community reports.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4 gap-2"
                    onClick={() => refetchReports()}
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Retry
                  </Button>
                </GlassCard>
              ) : reports.length === 0 ? (
                <GlassCard className="p-12 text-center">
                  <CheckCircle className="mx-auto h-10 w-10 text-risk-safe/50" />
                  <p className="mt-3 text-sm font-medium">All Clear</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    No flood reports from the community for the selected
                    filters.
                  </p>
                </GlassCard>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {reports.map((report) => {
                    const risk = (RISK_BADGE[report.risk_label] ??
                      RISK_BADGE.Safe)!;
                    const statusInfo = (STATUS_BADGE[report.status] ??
                      STATUS_BADGE.pending)!;
                    return (
                      <GlassCard
                        key={report.id}
                        className="p-4 space-y-3 hover:shadow-lg transition-shadow"
                      >
                        {/* Header row */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <MapPin className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                            <span className="text-sm font-medium leading-tight truncate">
                              {report.barangay ?? "Unknown"}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Badge className={statusInfo.className}>
                              {statusInfo.label}
                            </Badge>
                            <Badge className={risk.className}>
                              {risk.label}
                            </Badge>
                          </div>
                        </div>

                        {/* Specific location */}
                        {report.specific_location && (
                          <p className="text-[10px] text-muted-foreground">
                            Near: {report.specific_location}
                          </p>
                        )}

                        {/* Description */}
                        {report.description && (
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {report.description}
                          </p>
                        )}

                        {/* Photo thumbnail - clickable */}
                        {report.photo_url && (
                          <button
                            type="button"
                            className="relative group w-full cursor-pointer"
                            onClick={() => openReport(report)}
                          >
                            <img
                              src={report.photo_url}
                              alt="Flood evidence"
                              width={400}
                              height={224}
                              className="w-full h-28 object-cover rounded-lg transition-opacity group-hover:opacity-80"
                              loading="lazy"
                              decoding="async"
                            />
                            <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                              <span className="bg-black/60 text-white text-xs px-2.5 py-1 rounded-full flex items-center gap-1">
                                <Eye className="h-3 w-3" />
                                View Full
                              </span>
                            </span>
                          </button>
                        )}

                        {/* Footer */}
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                          <div className="flex items-center gap-3">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {timeAgo(report.created_at)}
                            </span>
                            {report.flood_height_cm && (
                              <span>{report.flood_height_cm} cm</span>
                            )}
                            <span>
                              {report.user_id
                                ? `User #${report.user_id}`
                                : "Anonymous"}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="flex items-center gap-0.5 text-risk-safe">
                              <CheckCircle className="h-3 w-3" />
                              {report.confirmation_count}
                            </span>
                            <span className="flex items-center gap-0.5 text-destructive">
                              <AlertTriangle className="h-3 w-3" />
                              {report.dispute_count}
                            </span>
                            {report.verified && (
                              <Badge
                                variant="outline"
                                className="text-[9px] px-1 py-0"
                              >
                                Verified ✓
                              </Badge>
                            )}
                          </div>
                        </div>

                        {/* View Report button */}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-full h-7 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
                          onClick={() => openReport(report)}
                        >
                          <Eye className="h-3 w-3" />
                          View Report
                        </Button>

                        {/* Audit trail */}
                        {report.verified_at && (
                          <p className="text-[10px] text-muted-foreground/70">
                            {report.status === "accepted"
                              ? "Verified"
                              : "Dismissed"}{" "}
                            {report.verified_by
                              ? `by Admin #${report.verified_by}`
                              : ""}{" "}
                            {timeAgo(report.verified_at)}
                          </p>
                        )}

                        {/* Admin actions */}
                        {isAdmin && report.status === "pending" && (
                          <div className="flex items-center gap-2 pt-1 border-t border-border/50">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs gap-1 text-risk-safe hover:bg-risk-safe/10"
                              onClick={() => handleVerify(report.id)}
                              disabled={verifyMutation.isPending}
                            >
                              {verifyMutation.isPending ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <ShieldCheck className="h-3 w-3" />
                              )}
                              Verify
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs gap-1 text-risk-alert hover:bg-risk-alert/10"
                              onClick={() => handleFlag(report.id)}
                              disabled={flagMutation.isPending}
                            >
                              <Flag className="h-3 w-3" />
                              Flag
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs gap-1 text-destructive hover:bg-destructive/10"
                              onClick={() => handleDismiss(report.id)}
                              disabled={verifyMutation.isPending}
                            >
                              <XCircle className="h-3 w-3" />
                              Dismiss
                            </Button>
                          </div>
                        )}
                      </GlassCard>
                    );
                  })}
                </div>
              )}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Submit Modal */}
      <ReportSubmitModal open={submitOpen} onOpenChange={setSubmitOpen} />

      {/* Report Detail Dialog */}
      <Dialog
        open={!!selectedReport}
        onOpenChange={(open) => !open && setSelectedReport(null)}
      >
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedReport &&
            (() => {
              const r = selectedReport;
              const risk = (RISK_BADGE[r.risk_label] ?? RISK_BADGE.Safe)!;
              const statusInfo = (STATUS_BADGE[r.status] ??
                STATUS_BADGE.pending)!;
              return (
                <>
                  <DialogHeader>
                    <div className="flex items-start justify-between gap-3">
                      <DialogTitle className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        {r.barangay ?? "Unknown"}
                      </DialogTitle>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <Badge className={statusInfo.className}>
                          {statusInfo.label}
                        </Badge>
                        <Badge className={risk.className}>{risk.label}</Badge>
                      </div>
                    </div>
                    {r.specific_location && (
                      <p className="text-xs text-muted-foreground">
                        Near: {r.specific_location}
                      </p>
                    )}
                  </DialogHeader>

                  {/* Full-size photo */}
                  {r.photo_url && (
                    <img
                      src={r.photo_url}
                      alt="Flood evidence"
                      className="w-full max-h-96 object-contain rounded-lg bg-muted"
                    />
                  )}

                  {/* Description */}
                  {r.description && (
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {r.description}
                    </p>
                  )}

                  {/* Details grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                    {r.flood_height_cm && (
                      <div className="rounded-lg border p-2.5">
                        <Droplets className="h-4 w-4 mx-auto mb-1 text-primary" />
                        <p className="text-sm font-semibold">
                          {r.flood_height_cm} cm
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          Flood Height
                        </p>
                      </div>
                    )}
                    <div className="rounded-lg border p-2.5">
                      <Clock className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
                      <p className="text-sm font-semibold">
                        {timeAgo(r.created_at)}
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        Reported
                      </p>
                    </div>
                    <div className="rounded-lg border p-2.5">
                      <CheckCircle className="h-4 w-4 mx-auto mb-1 text-risk-safe" />
                      <p className="text-sm font-semibold">
                        {r.confirmation_count}
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        Confirmations
                      </p>
                    </div>
                    <div className="rounded-lg border p-2.5">
                      <AlertTriangle className="h-4 w-4 mx-auto mb-1 text-destructive" />
                      <p className="text-sm font-semibold">{r.dispute_count}</p>
                      <p className="text-[10px] text-muted-foreground">
                        Disputes
                      </p>
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <span>Report #{r.id}</span>
                    <span>
                      {r.user_id ? `User #${r.user_id}` : "Anonymous"}
                    </span>
                    {r.photo_url && (
                      <span className="flex items-center gap-1">
                        <Camera className="h-3 w-3" />
                        Photo attached
                      </span>
                    )}
                    {r.credibility_score !== null && (
                      <span>
                        Credibility: {Math.round(r.credibility_score * 100)}%
                      </span>
                    )}
                  </div>

                  {/* Audit trail */}
                  {r.verified_at && (
                    <p className="text-xs text-muted-foreground/70 border-t pt-2">
                      {r.status === "accepted" ? "Verified" : "Dismissed"}{" "}
                      {r.verified_by ? `by Admin #${r.verified_by}` : ""}{" "}
                      {timeAgo(r.verified_at)}
                    </p>
                  )}

                  {/* Admin actions inside dialog */}
                  {isAdmin && r.status === "pending" && (
                    <div className="flex items-center gap-2 pt-2 border-t">
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1 text-risk-safe hover:bg-risk-safe/10"
                        onClick={() => {
                          handleVerify(r.id);
                          setSelectedReport(null);
                        }}
                        disabled={verifyMutation.isPending}
                      >
                        <ShieldCheck className="h-3.5 w-3.5" />
                        Verify
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1 text-risk-alert hover:bg-risk-alert/10"
                        onClick={() => {
                          handleFlag(r.id);
                          setSelectedReport(null);
                        }}
                        disabled={flagMutation.isPending}
                      >
                        <Flag className="h-3.5 w-3.5" />
                        Flag
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1 text-destructive hover:bg-destructive/10"
                        onClick={() => {
                          handleDismiss(r.id);
                          setSelectedReport(null);
                        }}
                        disabled={verifyMutation.isPending}
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        Dismiss
                      </Button>
                    </div>
                  )}
                </>
              );
            })()}
        </DialogContent>
      </Dialog>
    </div>
  );
}
