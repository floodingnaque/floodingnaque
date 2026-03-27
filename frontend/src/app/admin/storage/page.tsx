/**
 * Admin Storage Management Page
 *
 * Monitor database storage usage across tables, bulk-delete old records,
 * and permanently purge soft-deleted data. Admin-only access.
 */

import { PageHeader, SectionHeading } from "@/components/layout";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  storageQueryKeys,
  useCleanupCount,
  useStorageStats,
} from "@/features/admin/hooks/useStorage";
import type { TableStats } from "@/features/admin/services/storageApi";
import { storageApi } from "@/features/admin/services/storageApi";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  Archive,
  CheckCircle,
  Clock,
  Database,
  FileText,
  HardDrive,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Trash2,
  Zap,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

// ── Helpers ──

function formatBytes(bytes: number): string {
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(2)} GB`;
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

type AccentLevel = "good" | "warn" | "critical" | "neutral";

function accentGradient(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "from-risk-safe/60 via-risk-safe to-risk-safe/60";
    case "warn":
      return "from-risk-alert/60 via-risk-alert to-risk-alert/60";
    case "critical":
      return "from-risk-critical/60 via-risk-critical to-risk-critical/60";
    default:
      return "from-primary/40 via-primary/60 to-primary/40";
  }
}

function statTextColor(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "text-risk-safe";
    case "warn":
      return "text-risk-alert";
    case "critical":
      return "text-risk-critical";
    default:
      return "";
  }
}

function iconRing(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "bg-risk-safe/10 ring-risk-safe/20";
    case "warn":
      return "bg-risk-alert/10 ring-risk-alert/20";
    case "critical":
      return "bg-risk-critical/10 ring-risk-critical/20";
    default:
      return "bg-primary/10 ring-primary/20";
  }
}

// ── Table metadata ──

const TABLE_META: Record<
  string,
  {
    label: string;
    icon: React.ElementType;
    color: string;
    bgRing: string;
    barColor: string;
  }
> = {
  api_requests: {
    label: "API Request Logs",
    icon: Zap,
    color: "text-blue-500 dark:text-blue-400",
    bgRing: "bg-blue-500/10 ring-1 ring-blue-500/20",
    barColor: "bg-blue-500",
  },
  predictions: {
    label: "Predictions",
    icon: Database,
    color: "text-purple-500 dark:text-purple-400",
    bgRing: "bg-purple-500/10 ring-1 ring-purple-500/20",
    barColor: "bg-purple-500",
  },
  weather_data: {
    label: "Weather Data",
    icon: Database,
    color: "text-cyan-500 dark:text-cyan-400",
    bgRing: "bg-cyan-500/10 ring-1 ring-cyan-500/20",
    barColor: "bg-cyan-500",
  },
  community_reports: {
    label: "Community Reports",
    icon: FileText,
    color: "text-risk-alert",
    bgRing: "bg-risk-alert/10 ring-1 ring-risk-alert/20",
    barColor: "bg-risk-alert",
  },
  alert_history: {
    label: "Alert History",
    icon: ShieldAlert,
    color: "text-risk-critical",
    bgRing: "bg-risk-critical/10 ring-1 ring-risk-critical/20",
    barColor: "bg-risk-critical",
  },
  evacuation_centers: {
    label: "Evacuation Centers",
    icon: Archive,
    color: "text-risk-safe",
    bgRing: "bg-risk-safe/10 ring-1 ring-risk-safe/20",
    barColor: "bg-risk-safe",
  },
};

// ── Stat Card ──

function StatCard({
  icon: Icon,
  label,
  value,
  isLoading,
  health = "neutral",
  description,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  isLoading?: boolean;
  health?: AccentLevel;
  description?: string;
}) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div
        className={cn("h-1 w-full bg-linear-to-r", accentGradient(health))}
      />
      <div className="pt-4 pb-3 px-6 flex items-center gap-3">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl ring-1",
            iconRing(health),
          )}
        >
          <Icon
            className={cn(
              "h-5 w-5",
              health === "neutral" ? "text-primary" : statTextColor(health),
            )}
          />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          {isLoading ? (
            <Skeleton className="h-7 w-20 mt-0.5" />
          ) : (
            <p className={cn("text-2xl font-bold", statTextColor(health))}>
              {value}
            </p>
          )}
          {description && (
            <p className="text-[10px] text-muted-foreground/70">
              {description}
            </p>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

// ── Cleanup Card ──

interface CleanupCardProps {
  title: string;
  description: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  days: string;
  onDaysChange: (v: string) => void;
  minDays: number;
  estimatedCount: number | undefined;
  countLoading: boolean;
  actionLoading: boolean;
  onDelete: () => void;
  dialogTitle: string;
  dialogDescription: React.ReactNode;
  statusFilter?: {
    value: string;
    onChange: (v: string) => void;
    options: { value: string; label: string }[];
  };
}

function CleanupCard({
  title,
  description,
  icon: Icon,
  iconBg,
  iconColor,
  days,
  onDaysChange,
  minDays,
  estimatedCount,
  countLoading,
  actionLoading,
  onDelete,
  dialogTitle,
  dialogDescription,
  statusFilter,
}: CleanupCardProps) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300 flex flex-col">
      <div className="h-1 w-full bg-linear-to-r from-primary/40 via-primary/60 to-primary/40" />
      <div className="pt-5 px-5 pb-5 space-y-4 flex flex-col flex-1">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-lg ring-1",
              iconBg,
            )}
          >
            <Icon className={cn("h-4 w-4", iconColor)} />
          </div>
          <div>
            <p className="text-sm font-medium">{title}</p>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>

        <div className="space-y-3 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm whitespace-nowrap">Older than</span>
            <Input
              type="number"
              min={minDays}
              max={365}
              value={days}
              onChange={(e) => onDaysChange(e.target.value)}
              className="w-20 h-8"
              aria-label={`Days threshold for ${title.toLowerCase()}`}
            />
            <span className="text-sm text-muted-foreground">days</span>
          </div>

          {statusFilter && (
            <div className="flex items-center gap-2">
              <span className="text-sm whitespace-nowrap">Status</span>
              <Select
                value={statusFilter.value}
                onValueChange={statusFilter.onChange}
              >
                <SelectTrigger className="w-full h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {statusFilter.options.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <Separator />

        {/* Estimated count */}
        <p className="text-xs text-muted-foreground">
          {countLoading ? (
            <Skeleton className="h-4 w-48 inline-block" />
          ) : estimatedCount != null ? (
            <>
              This will delete approximately{" "}
              <strong className="text-foreground">
                {estimatedCount.toLocaleString()}
              </strong>{" "}
              records
            </>
          ) : (
            "Unable to estimate affected records"
          )}
        </p>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="destructive"
              size="sm"
              className="w-full"
              disabled={actionLoading || estimatedCount === 0}
            >
              {actionLoading ? (
                <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4 mr-1.5" />
              )}
              Delete Old {title}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                {dialogTitle}
              </AlertDialogTitle>
              <AlertDialogDescription asChild>
                <div>{dialogDescription}</div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={onDelete}>
                Confirm Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </GlassCard>
  );
}

// ── Cleanup history entry (in-memory) ──

interface CleanupEntry {
  id: number;
  timestamp: Date;
  actionType: string;
  rowsAffected: number;
  threshold: string;
  status: "success" | "failed";
}

// ── Component ──

export default function AdminStoragePage() {
  const queryClient = useQueryClient();

  // Cleanup form state
  const [logsDays, setLogsDays] = useState("30");
  const [reportsDays, setReportsDays] = useState("90");
  const [reportsStatus, setReportsStatus] = useState("all");
  const [alertsDays, setAlertsDays] = useState("60");
  const [alertsStatus, setAlertsStatus] = useState("all");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Purge confirmation phrase
  const [purgePhrase, setPurgePhrase] = useState("");

  // Cleanup history (in-session)
  const [cleanupHistory, setCleanupHistory] = useState<CleanupEntry[]>([]);
  const nextId = useRef(1);

  // Refresh
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // ── Queries ──
  const {
    data: storageData,
    isLoading: storageLoading,
    dataUpdatedAt,
  } = useStorageStats();

  const tables = storageData?.tables;
  const summary = storageData?.summary;
  const displayUpdatedAt =
    lastRefreshed ?? (dataUpdatedAt ? new Date(dataUpdatedAt) : null);

  // Cleanup count previews
  const logsDaysNum = parseInt(logsDays) || 30;
  const reportsDaysNum = parseInt(reportsDays) || 90;
  const alertsDaysNum = parseInt(alertsDays) || 60;

  const { data: logsCountData, isLoading: logsCountLoading } = useCleanupCount({
    type: "logs",
    older_than_days: logsDaysNum,
    enabled: logsDaysNum >= 1,
  });
  const { data: reportsCountData, isLoading: reportsCountLoading } =
    useCleanupCount({
      type: "reports",
      older_than_days: reportsDaysNum,
      status: reportsStatus,
      enabled: reportsDaysNum >= 1,
    });
  const { data: alertsCountData, isLoading: alertsCountLoading } =
    useCleanupCount({
      type: "alerts",
      older_than_days: alertsDaysNum,
      delivery_status: alertsStatus,
      enabled: alertsDaysNum >= 1,
    });

  // ── Derived ──

  const totalRows = summary?.total_rows ?? 0;
  const totalActive = summary?.total_active ?? 0;
  const totalDeleted = summary?.total_soft_deleted ?? 0;
  const totalBytes = summary?.estimated_total_bytes ?? 0;

  const purgableTables = useMemo(
    () =>
      tables
        ? Object.entries(tables)
            .filter(
              ([key, t]) => t.soft_deleted > 0 && key !== "evacuation_centers",
            )
            .map(([key]) => key)
        : [],
    [tables],
  );

  // ── Handlers ──

  const refreshAll = useCallback(async () => {
    setIsRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: storageQueryKeys.all });
    setLastRefreshed(new Date());
    setIsRefreshing(false);
  }, [queryClient]);

  const addHistoryEntry = useCallback(
    (
      actionType: string,
      rowsAffected: number,
      threshold: string,
      status: "success" | "failed",
    ) => {
      setCleanupHistory((prev) => [
        {
          id: nextId.current++,
          timestamp: new Date(),
          actionType,
          rowsAffected,
          threshold,
          status,
        },
        ...prev,
      ]);
    },
    [],
  );

  const handleBulkDeleteLogs = useCallback(async () => {
    setActionLoading("logs");
    try {
      const res = await storageApi.bulkDeleteLogs(logsDaysNum);
      if (res.success) {
        toast.success(res.message || `Deleted ${res.deleted_count} log(s)`);
        addHistoryEntry(
          "API Log Cleanup",
          res.deleted_count ?? 0,
          `>${logsDays}d`,
          "success",
        );
        queryClient.invalidateQueries({ queryKey: storageQueryKeys.all });
      } else {
        toast.error(res.error || "Failed to delete logs");
        addHistoryEntry("API Log Cleanup", 0, `>${logsDays}d`, "failed");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      toast.error(msg);
      addHistoryEntry("API Log Cleanup", 0, `>${logsDays}d`, "failed");
    } finally {
      setActionLoading(null);
    }
  }, [logsDaysNum, logsDays, queryClient, addHistoryEntry]);

  const handleBulkDeleteReports = useCallback(async () => {
    setActionLoading("reports");
    const threshold = `>${reportsDays}d${reportsStatus !== "all" ? `, ${reportsStatus}` : ""}`;
    try {
      const res = await storageApi.bulkDeleteReports(
        reportsDaysNum,
        reportsStatus,
      );
      if (res.success) {
        toast.success(res.message || `Deleted ${res.deleted_count} report(s)`);
        addHistoryEntry(
          "Report Cleanup",
          res.deleted_count ?? 0,
          threshold,
          "success",
        );
        queryClient.invalidateQueries({ queryKey: storageQueryKeys.all });
      } else {
        toast.error(res.error || "Failed to delete reports");
        addHistoryEntry("Report Cleanup", 0, threshold, "failed");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      toast.error(msg);
      addHistoryEntry("Report Cleanup", 0, threshold, "failed");
    } finally {
      setActionLoading(null);
    }
  }, [
    reportsDaysNum,
    reportsDays,
    reportsStatus,
    queryClient,
    addHistoryEntry,
  ]);

  const handleBulkDeleteAlerts = useCallback(async () => {
    setActionLoading("alerts");
    const threshold = `>${alertsDays}d${alertsStatus !== "all" ? `, ${alertsStatus}` : ""}`;
    try {
      const res = await storageApi.bulkDeleteAlerts(
        alertsDaysNum,
        alertsStatus,
      );
      if (res.success) {
        toast.success(res.message || `Deleted ${res.deleted_count} alert(s)`);
        addHistoryEntry(
          "Alert Cleanup",
          res.deleted_count ?? 0,
          threshold,
          "success",
        );
        queryClient.invalidateQueries({ queryKey: storageQueryKeys.all });
      } else {
        toast.error(res.error || "Failed to delete alerts");
        addHistoryEntry("Alert Cleanup", 0, threshold, "failed");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      toast.error(msg);
      addHistoryEntry("Alert Cleanup", 0, threshold, "failed");
    } finally {
      setActionLoading(null);
    }
  }, [alertsDaysNum, alertsDays, alertsStatus, queryClient, addHistoryEntry]);

  const handlePurgeDeleted = useCallback(async () => {
    setActionLoading("purge");
    try {
      const res = await storageApi.purgeDeleted(purgableTables);
      if (res.success) {
        toast.success(res.message || `Purged ${res.total_purged} record(s)`);
        addHistoryEntry(
          "Permanent Purge",
          res.total_purged ?? 0,
          purgableTables.join(", "),
          "success",
        );
        queryClient.invalidateQueries({ queryKey: storageQueryKeys.all });
      } else {
        toast.error(res.error || "Failed to purge");
        addHistoryEntry(
          "Permanent Purge",
          0,
          purgableTables.join(", "),
          "failed",
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Purge failed";
      toast.error(msg);
      addHistoryEntry(
        "Permanent Purge",
        0,
        purgableTables.join(", "),
        "failed",
      );
    } finally {
      setActionLoading(null);
      setPurgePhrase("");
    }
  }, [purgableTables, queryClient, addHistoryEntry]);

  // ── Animation refs ──
  const overviewRef = useRef<HTMLDivElement>(null);
  const overviewInView = useInView(overviewRef, { once: true, amount: 0.1 });
  const cleanupRef = useRef<HTMLDivElement>(null);
  const cleanupInView = useInView(cleanupRef, { once: true, amount: 0.1 });
  const historyRef = useRef<HTMLDivElement>(null);
  const historyInView = useInView(historyRef, { once: true, amount: 0.1 });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <Breadcrumb
          items={[
            { label: "Admin", href: "/admin" },
            { label: "Database Storage" },
          ]}
          className="mb-4"
        />
        <div className="flex items-start justify-between">
          <PageHeader
            icon={HardDrive}
            title="Storage Management"
            subtitle="Monitor database usage, clean up old records, and free storage"
          />
          <div className="flex items-center gap-3 pt-1">
            {displayUpdatedAt && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated{" "}
                {formatDistanceToNow(displayUpdatedAt, { addSuffix: true })}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={refreshAll}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn("h-4 w-4 mr-1.5", isRefreshing && "animate-spin")}
              />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* ── Overview Section ── */}
      <section className="py-6 bg-muted/30">
        <div className="w-full px-6" ref={overviewRef}>
          <SectionHeading
            label="Overview"
            title="Database Storage"
            subtitle="Row counts and estimated sizes across all tracked tables"
          />

          {/* Summary cards */}
          <motion.div
            className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 mb-8"
            variants={staggerContainer}
            initial="hidden"
            animate={overviewInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <StatCard
                icon={Database}
                label="Total Rows"
                value={totalRows.toLocaleString()}
                isLoading={storageLoading}
                health="neutral"
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={CheckCircle}
                label="Active Records"
                value={totalActive.toLocaleString()}
                isLoading={storageLoading}
                health="good"
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={Trash2}
                label="Soft-Deleted (Purgeable)"
                value={totalDeleted.toLocaleString()}
                isLoading={storageLoading}
                health={totalDeleted > 0 ? "critical" : "neutral"}
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={HardDrive}
                label="Estimated Storage"
                value={formatBytes(totalBytes)}
                isLoading={storageLoading}
                health="warn"
              />
            </motion.div>
          </motion.div>

          {/* Per-table breakdown */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={overviewInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden">
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <div className="p-6">
                  <h3 className="text-lg font-semibold mb-4">
                    Per-Table Breakdown
                  </h3>

                  {storageLoading ? (
                    <div className="space-y-3">
                      {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton
                          key={`skel-${i}`}
                          className="h-16 w-full rounded-lg"
                        />
                      ))}
                    </div>
                  ) : tables ? (
                    <div className="space-y-3">
                      {Object.entries(tables).map(
                        ([key, stats]: [string, TableStats]) => {
                          const meta = TABLE_META[key] || {
                            label: key,
                            icon: Database,
                            color: "text-muted-foreground",
                            bgRing: "bg-muted/50 ring-1 ring-border/50",
                            barColor: "bg-muted-foreground",
                          };
                          const Icon = meta.icon;
                          const pctNum =
                            totalRows > 0 ? (stats.total / totalRows) * 100 : 0;
                          const pct = pctNum.toFixed(1);
                          return (
                            <div
                              key={key}
                              className="p-3 rounded-lg border bg-card hover:shadow-md transition-all duration-300"
                            >
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-3">
                                  <div
                                    className={cn(
                                      "h-8 w-8 rounded-lg flex items-center justify-center shrink-0",
                                      meta.bgRing,
                                    )}
                                  >
                                    <Icon
                                      className={cn("h-4 w-4", meta.color)}
                                    />
                                  </div>
                                  <div>
                                    <p className="font-medium text-sm">
                                      {meta.label}
                                    </p>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                      <span>{pct}% of total</span>
                                      <span>·</span>
                                      <span>
                                        {formatBytes(
                                          stats.estimated_size_bytes,
                                        )}
                                      </span>
                                      {stats.last_record_at && (
                                        <>
                                          <span>·</span>
                                          <span>
                                            Last:{" "}
                                            {formatDistanceToNow(
                                              new Date(stats.last_record_at),
                                              { addSuffix: true },
                                            )}
                                          </span>
                                        </>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-3 text-sm">
                                  <div className="text-right">
                                    <span className="font-semibold">
                                      {stats.active.toLocaleString()}
                                    </span>
                                    <span className="text-muted-foreground ml-1 text-xs">
                                      active
                                    </span>
                                  </div>
                                  {stats.soft_deleted > 0 && (
                                    <Badge
                                      variant="destructive"
                                      className="text-xs"
                                    >
                                      {stats.soft_deleted.toLocaleString()}{" "}
                                      deleted
                                    </Badge>
                                  )}
                                  <span className="text-muted-foreground font-mono text-xs">
                                    {stats.total.toLocaleString()}
                                  </span>
                                </div>
                              </div>
                              {/* Storage bar */}
                              <div className="h-1.5 rounded-full overflow-hidden bg-muted/30">
                                <div
                                  className={cn(
                                    "h-full rounded-full transition-all duration-500",
                                    meta.barColor,
                                  )}
                                  style={{
                                    width: `${Math.max(pctNum, 1)}%`,
                                  }}
                                />
                              </div>
                            </div>
                          );
                        },
                      )}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-8">
                      No data available
                    </p>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Cleanup Actions Section ── */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={cleanupRef}>
          <SectionHeading
            label="Cleanup"
            title="Data Cleanup"
            subtitle="Bulk soft-delete old records to keep the database lean"
          />

          <motion.div
            className="grid gap-6 lg:grid-cols-3"
            variants={staggerContainer}
            initial="hidden"
            animate={cleanupInView ? "show" : undefined}
          >
            {/* API Logs */}
            <motion.div variants={fadeUp}>
              <CleanupCard
                title="API Request Logs"
                description="These grow fastest and are safe to remove after analysis."
                icon={Zap}
                iconBg="bg-blue-500/10 ring-blue-500/20"
                iconColor="text-blue-500"
                days={logsDays}
                onDaysChange={(v) =>
                  setLogsDays(String(Math.max(7, parseInt(v) || 7)))
                }
                minDays={7}
                estimatedCount={logsCountData?.count}
                countLoading={logsCountLoading}
                actionLoading={actionLoading === "logs"}
                onDelete={handleBulkDeleteLogs}
                dialogTitle="Delete API Logs"
                dialogDescription={
                  <p>
                    This will soft-delete all API request logs older than{" "}
                    <strong>{logsDays} days</strong>.{" "}
                    {logsCountData?.count != null && (
                      <>
                        Approximately{" "}
                        <strong>
                          {logsCountData.count.toLocaleString()} records
                        </strong>{" "}
                        will be affected.
                      </>
                    )}{" "}
                    Records can be permanently purged later.
                  </p>
                }
              />
            </motion.div>

            {/* Community Reports */}
            <motion.div variants={fadeUp}>
              <CleanupCard
                title="Community Reports"
                description="Remove old community flood reports by age and status."
                icon={FileText}
                iconBg="bg-risk-alert/10 ring-risk-alert/20"
                iconColor="text-risk-alert"
                days={reportsDays}
                onDaysChange={setReportsDays}
                minDays={1}
                estimatedCount={reportsCountData?.count}
                countLoading={reportsCountLoading}
                actionLoading={actionLoading === "reports"}
                onDelete={handleBulkDeleteReports}
                dialogTitle="Delete Community Reports"
                dialogDescription={
                  <p>
                    This will soft-delete community reports older than{" "}
                    <strong>{reportsDays} days</strong>
                    {reportsStatus !== "all" && (
                      <>
                        {" "}
                        with status <strong>&quot;{reportsStatus}&quot;</strong>
                      </>
                    )}
                    .{" "}
                    {reportsCountData?.count != null && (
                      <>
                        Approximately{" "}
                        <strong>
                          {reportsCountData.count.toLocaleString()} records
                        </strong>{" "}
                        will be affected.
                      </>
                    )}{" "}
                    Records can be permanently purged later.
                  </p>
                }
                statusFilter={{
                  value: reportsStatus,
                  onChange: setReportsStatus,
                  options: [
                    { value: "all", label: "All Statuses" },
                    { value: "pending", label: "Pending" },
                    { value: "accepted", label: "Verified" },
                    { value: "rejected", label: "Flagged" },
                  ],
                }}
              />
            </motion.div>

            {/* Alert History */}
            <motion.div variants={fadeUp}>
              <CleanupCard
                title="Alert History"
                description="Clean up old alert delivery records by age and status."
                icon={ShieldAlert}
                iconBg="bg-risk-critical/10 ring-risk-critical/20"
                iconColor="text-risk-critical"
                days={alertsDays}
                onDaysChange={setAlertsDays}
                minDays={1}
                estimatedCount={alertsCountData?.count}
                countLoading={alertsCountLoading}
                actionLoading={actionLoading === "alerts"}
                onDelete={handleBulkDeleteAlerts}
                dialogTitle="Delete Alert History"
                dialogDescription={
                  <p>
                    This will soft-delete alert records older than{" "}
                    <strong>{alertsDays} days</strong>
                    {alertsStatus !== "all" && (
                      <>
                        {" "}
                        with status <strong>&quot;{alertsStatus}&quot;</strong>
                      </>
                    )}
                    .{" "}
                    {alertsCountData?.count != null && (
                      <>
                        Approximately{" "}
                        <strong>
                          {alertsCountData.count.toLocaleString()} records
                        </strong>{" "}
                        will be affected.
                      </>
                    )}{" "}
                    Records can be permanently purged later.
                  </p>
                }
                statusFilter={{
                  value: alertsStatus,
                  onChange: setAlertsStatus,
                  options: [
                    { value: "all", label: "All Statuses" },
                    { value: "delivered", label: "Delivered" },
                    { value: "failed", label: "Failed" },
                    { value: "pending", label: "Pending" },
                  ],
                }}
              />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Danger Zone - Permanent Purge ── */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6">
          <SectionHeading
            label="Danger Zone"
            title="Permanent Purge"
            subtitle="Permanently remove soft-deleted records from the database - this cannot be undone"
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={cleanupInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden border-destructive/30">
                <div className="h-1 w-full bg-linear-to-r from-risk-critical/60 via-risk-critical to-risk-critical/60" />
                <div className="pt-6 px-6 pb-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-risk-critical/10 ring-1 ring-risk-critical/20">
                      <AlertTriangle className="h-5 w-5 text-destructive" />
                    </div>
                    <div>
                      <p className="font-medium text-destructive">
                        Purge Soft-Deleted Records
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Permanently remove all soft-deleted rows. This frees
                        storage but cannot be reversed.
                      </p>
                    </div>
                  </div>

                  {storageLoading ? (
                    <Skeleton className="h-10 w-64" />
                  ) : totalDeleted === 0 ? (
                    <div className="rounded-lg border border-dashed p-4 text-center">
                      <p className="text-sm text-muted-foreground">
                        No soft-deleted records to purge. All data is active.
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="flex flex-wrap gap-2">
                        {purgableTables.map((table) => {
                          const meta = TABLE_META[table];
                          const count = tables?.[table]?.soft_deleted ?? 0;
                          return (
                            <Badge key={table} variant="outline">
                              {meta?.label ?? table}: {count.toLocaleString()}
                            </Badge>
                          );
                        })}
                        <Badge variant="destructive">
                          Total: {totalDeleted.toLocaleString()}
                        </Badge>
                      </div>

                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="destructive"
                            disabled={actionLoading !== null}
                          >
                            {actionLoading === "purge" ? (
                              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4 mr-1.5" />
                            )}
                            Purge All ({totalDeleted.toLocaleString()} records)
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle className="flex items-center gap-2 text-destructive">
                              <AlertTriangle className="h-5 w-5" />
                              Permanent Purge - No Undo
                            </AlertDialogTitle>
                            <AlertDialogDescription asChild>
                              <div className="space-y-3">
                                <p>
                                  This action is permanent and cannot be undone.{" "}
                                  <strong>
                                    {totalDeleted.toLocaleString()} soft-deleted
                                    records
                                  </strong>{" "}
                                  will be permanently removed across{" "}
                                  {purgableTables.length} table(s).
                                </p>
                                <div>
                                  <label
                                    htmlFor="purge-confirm"
                                    className="text-sm font-medium text-foreground"
                                  >
                                    Type{" "}
                                    <strong className="text-destructive">
                                      PURGE
                                    </strong>{" "}
                                    to confirm:
                                  </label>
                                  <Input
                                    id="purge-confirm"
                                    value={purgePhrase}
                                    onChange={(e) =>
                                      setPurgePhrase(e.target.value)
                                    }
                                    placeholder="PURGE"
                                    className="mt-1"
                                    autoComplete="off"
                                  />
                                </div>
                              </div>
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel
                              onClick={() => setPurgePhrase("")}
                            >
                              Cancel
                            </AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              disabled={purgePhrase !== "PURGE"}
                              onClick={handlePurgeDeleted}
                            >
                              Permanently Purge
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Cleanup History Log ── */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={historyRef}>
          <SectionHeading
            label="History"
            title="Cleanup Activity Log"
            subtitle="Recent cleanup and purge operations performed this session"
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={historyInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden">
                <div className="h-1 w-full bg-linear-to-r from-primary/40 via-primary/60 to-primary/40" />
                <div className="p-6">
                  {cleanupHistory.length === 0 ? (
                    <div className="rounded-lg border border-dashed p-8 text-center">
                      <Clock className="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">
                        No cleanup operations performed yet this session.
                      </p>
                      <p className="text-xs text-muted-foreground/60 mt-1">
                        Operations will appear here after you run a cleanup or
                        purge action.
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto rounded border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-xs">Timestamp</TableHead>
                            <TableHead className="text-xs">
                              Action Type
                            </TableHead>
                            <TableHead className="text-xs text-right">
                              Rows Affected
                            </TableHead>
                            <TableHead className="text-xs">Threshold</TableHead>
                            <TableHead className="text-xs">Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {cleanupHistory.map((entry) => (
                            <TableRow key={entry.id}>
                              <TableCell className="text-xs whitespace-nowrap">
                                {format(entry.timestamp, "yyyy-MM-dd HH:mm:ss")}
                              </TableCell>
                              <TableCell className="text-xs font-medium">
                                {entry.actionType}
                              </TableCell>
                              <TableCell className="text-xs text-right font-mono">
                                {entry.rowsAffected.toLocaleString()}
                              </TableCell>
                              <TableCell className="text-xs text-muted-foreground">
                                {entry.threshold}
                              </TableCell>
                              <TableCell>
                                {entry.status === "success" ? (
                                  <Badge
                                    variant="outline"
                                    className="text-[10px] bg-risk-safe/10 text-risk-safe border-risk-safe/30"
                                  >
                                    <CheckCircle className="h-3 w-3 mr-0.5" />
                                    Success
                                  </Badge>
                                ) : (
                                  <Badge
                                    variant="outline"
                                    className="text-[10px] bg-risk-critical/10 text-risk-critical border-risk-critical/30"
                                  >
                                    <AlertTriangle className="h-3 w-3 mr-0.5" />
                                    Failed
                                  </Badge>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
