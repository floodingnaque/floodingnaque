/**
 * Admin System Monitoring Page
 *
 * Industrial-grade observability dashboard with per-service health probes,
 * API response analytics, model prediction drift detection,
 * alert delivery confirmation monitoring, and anomaly detection.
 */

import { PageHeader } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useAlertDeliveryStats,
  useApiResponseStats,
  usePredictionDriftStats,
  useUptimeStats,
} from "@/features/admin/hooks/useAdmin";
import type { ServiceStatus } from "@/features/admin/services/adminApi";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { motion, useInView } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Bell,
  BellOff,
  CheckCircle,
  Clock,
  Gauge,
  HeartPulse,
  Hourglass,
  Radio,
  RefreshCw,
  Server,
  ShieldAlert,
  TrendingUp,
  XCircle,
  Zap,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";

// ── Helpers ──

function formatMs(ms: number): string {
  if (!Number.isFinite(ms)) return "—";
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const parts: string[] = [];
  if (d > 0) parts.push(`${d}d`);
  if (h > 0) parts.push(`${h}h`);
  parts.push(`${m}m`);
  return parts.join(" ");
}

/** Formats a decimal ratio (0-1) as a percentage string */
function formatPercent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function getUptimeColor(pct: number): string {
  if (pct >= 99.9) return "text-risk-safe";
  if (pct >= 99) return "text-risk-alert";
  return "text-risk-critical";
}

function getDriftColor(psi: number | null, threshold: number): string {
  if (psi === null) return "text-muted-foreground";
  if (psi < threshold * 0.5) return "text-risk-safe";
  if (psi < threshold) return "text-risk-alert";
  return "text-risk-critical";
}

function statusBadge(status: ServiceStatus["status"]) {
  const map: Record<
    string,
    { variant: string; icon: React.ElementType; label: string }
  > = {
    healthy: {
      variant: "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
      icon: CheckCircle,
      label: "Healthy",
    },
    degraded: {
      variant: "bg-risk-alert/15 text-risk-alert border-risk-alert/30",
      icon: AlertTriangle,
      label: "Degraded",
    },
    offline: {
      variant: "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
      icon: XCircle,
      label: "Offline",
    },
    unknown: {
      variant: "bg-muted text-muted-foreground border-border",
      icon: Clock,
      label: "Unknown",
    },
  };
  const cfg = map[status] ?? map.unknown;
  if (!cfg) return null;
  const Icon = cfg.icon;
  return (
    <Badge
      variant="outline"
      className={cn("text-[10px] px-1.5 py-0 gap-1", cfg.variant)}
    >
      <Icon className="h-3 w-3" />
      {cfg.label}
    </Badge>
  );
}

// ── Stat Card ──

const iconBoxStyles: Record<string, string> = {
  "text-primary": "bg-primary/10 ring-1 ring-primary/20",
  "text-risk-safe": "bg-risk-safe/10 ring-1 ring-risk-safe/20",
  "text-risk-alert": "bg-risk-alert/10 ring-1 ring-risk-alert/20",
  "text-risk-critical": "bg-risk-critical/10 ring-1 ring-risk-critical/20",
};

function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  color = "text-foreground",
  iconColor = "text-primary",
  accentGradient = "from-primary/60 via-primary to-primary/60",
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subValue?: string;
  color?: string;
  iconColor?: string;
  accentGradient?: string;
}) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div className={cn("h-1 w-full bg-linear-to-r", accentGradient)} />
      <CardContent className="pt-5 pb-4">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "h-9 w-9 rounded-xl flex items-center justify-center shrink-0",
              iconBoxStyles[iconColor] ?? "bg-muted/50 ring-1 ring-border/50",
            )}
          >
            <Icon className={cn("h-4.5 w-4.5", iconColor)} />
          </div>
          <div className="min-w-0">
            <p className={cn("text-xl font-bold leading-tight", color)}>
              {value}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
            {subValue && (
              <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                {subValue}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </GlassCard>
  );
}

// ── Distribution Bar ──

function DistributionBar({
  data,
  total,
  colors,
}: {
  data: Record<string, number>;
  total: number;
  colors: Record<string, string>;
}) {
  if (total === 0) return null;
  return (
    <div className="space-y-2">
      <div className="flex h-3 rounded-full overflow-hidden bg-muted/30">
        {Object.entries(data).map(([key, count]) => {
          const pct = (count / total) * 100;
          if (pct === 0) return null;
          return (
            <div
              key={key}
              className={cn("transition-all", colors[key] ?? "bg-gray-400")}
              style={{ width: `${pct}%` }}
              title={`${key}: ${count} (${pct.toFixed(1)}%)`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {Object.entries(data).map(([key, count]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs">
            <span
              className={cn(
                "h-2.5 w-2.5 rounded-full",
                colors[key] ?? "bg-gray-400",
              )}
            />
            <span className="text-muted-foreground capitalize">{key}</span>
            <span className="font-medium">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Skeleton ──

function MonitoringSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
      <Skeleton className="h-80 rounded-xl" />
    </div>
  );
}

// ── Page ──

export default function AdminMonitoringPage() {
  const sectionRef = useRef(null);
  const inView = useInView(sectionRef, { once: true, margin: "-80px" });

  const [liveMode, setLiveMode] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Queries — all auto-poll when liveMode is true
  const {
    data: uptimeResponse,
    isLoading: uptimeLoading,
    refetch: refetchUptime,
  } = useUptimeStats(liveMode);
  const {
    data: apiResponse,
    isLoading: apiLoading,
    refetch: refetchApi,
  } = useApiResponseStats();
  const {
    data: driftResponse,
    isLoading: driftLoading,
    refetch: refetchDrift,
  } = usePredictionDriftStats();
  const {
    data: alertResponse,
    isLoading: alertLoading,
    refetch: refetchAlert,
  } = useAlertDeliveryStats();

  const uptime = uptimeResponse?.data;
  const apiStats = apiResponse?.data;
  const drift = driftResponse?.data;
  const alertStats = alertResponse?.data;

  const handleRefresh = useCallback(() => {
    refetchUptime();
    refetchApi();
    refetchDrift();
    refetchAlert();
    setLastRefreshed(new Date());
  }, [refetchUptime, refetchApi, refetchDrift, refetchAlert]);

  // Derived: count degraded/offline services
  const services = uptime?.services ?? [];
  const degradedCount = services.filter(
    (s) => s.status === "degraded" || s.status === "offline",
  ).length;

  // Derived: anomaly signals
  const anomalies: string[] = [];
  if (apiStats && apiStats.error_rate > 0.1)
    anomalies.push(
      `Error rate ${formatPercent(apiStats.error_rate)} exceeds 10% threshold`,
    );
  if (drift?.drift_detected)
    anomalies.push(`Model drift detected — PSI ${drift.psi?.toFixed(4)}`);
  if (alertStats && alertStats.success_rate < 0.9)
    anomalies.push(
      `Alert delivery success rate ${formatPercent(alertStats.success_rate)} below 90%`,
    );
  if (degradedCount > 0)
    anomalies.push(
      `${degradedCount} service${degradedCount > 1 ? "s" : ""} degraded or offline`,
    );

  return (
    <div className="w-full space-y-0 pb-10">
      <PageHeader
        icon={Activity}
        title="System Monitoring"
        subtitle="Uptime, API performance, model drift, and alert delivery tracking"
        actions={
          <div className="flex items-center gap-3">
            {/* Last updated timestamp */}
            <span className="text-[11px] text-muted-foreground hidden sm:inline">
              Updated{" "}
              {lastRefreshed.toLocaleTimeString("en-PH", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
            {/* Live mode toggle */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">Live</span>
              <Switch
                checked={liveMode}
                onCheckedChange={setLiveMode}
                aria-label="Toggle live monitoring"
              />
            </div>
            {/* Manual refresh */}
            <Button
              variant="secondary"
              size="sm"
              onClick={handleRefresh}
              className="gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </Button>
          </div>
        }
      />

      {/* ── Anomaly / Degradation Banner ── */}
      {anomalies.length > 0 && (
        <div className="w-full px-6 pt-4">
          <GlassCard className="overflow-hidden border-risk-alert/30 bg-risk-alert/5">
            <div className="h-1 w-full bg-linear-to-r from-risk-alert/60 via-risk-alert to-risk-alert/60" />
            <CardContent className="py-3 flex items-start gap-3">
              <ShieldAlert className="h-5 w-5 text-risk-alert shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="text-sm font-semibold text-risk-alert">
                  {anomalies.length} anomal
                  {anomalies.length === 1 ? "y" : "ies"} detected
                </p>
                <ul className="text-xs text-muted-foreground space-y-0.5">
                  {anomalies.map((a, i) => (
                    <li key={i}>• {a}</li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </GlassCard>
        </div>
      )}

      {/* ── Tabbed Content ── */}
      <div ref={sectionRef} className="w-full px-6 pt-6">
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="overview" className="gap-1.5">
              <HeartPulse className="h-3.5 w-3.5" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="api" className="gap-1.5">
              <Zap className="h-3.5 w-3.5" />
              API Performance
            </TabsTrigger>
            <TabsTrigger value="drift" className="gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" />
              Model Drift
            </TabsTrigger>
            <TabsTrigger value="alerts" className="gap-1.5">
              <Bell className="h-3.5 w-3.5" />
              Alert Delivery
            </TabsTrigger>
          </TabsList>

          {/* ══════════════════════════════════════ */}
          {/*  TAB 1 — Overview & Service Health    */}
          {/* ══════════════════════════════════════ */}
          <TabsContent value="overview">
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate={inView ? "show" : "hidden"}
              className="space-y-6"
            >
              {uptimeLoading && !uptime ? (
                <MonitoringSkeleton />
              ) : (
                <>
                  {/* KPI strip */}
                  <motion.div variants={fadeUp}>
                    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
                      <StatCard
                        icon={HeartPulse}
                        label="Uptime"
                        value={
                          uptime
                            ? `${uptime.uptime_percentage.toFixed(2)}%`
                            : "—"
                        }
                        subValue={
                          uptime
                            ? formatUptime(uptime.uptime_seconds)
                            : undefined
                        }
                        color={getUptimeColor(uptime?.uptime_percentage ?? 0)}
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={Gauge}
                        label="Avg Health Check"
                        value={uptime ? formatMs(uptime.avg_response_ms) : "—"}
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={Radio}
                        label="Health Checks"
                        value={uptime?.health_check_count ?? 0}
                        subValue={`${uptime?.healthy_count ?? 0} healthy`}
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={Server}
                        label="Services"
                        value={`${services.filter((s) => s.status === "healthy").length}/${services.length}`}
                        subValue={
                          degradedCount > 0
                            ? `${degradedCount} degraded`
                            : "All healthy"
                        }
                        color={
                          degradedCount > 0
                            ? "text-risk-alert"
                            : "text-risk-safe"
                        }
                        iconColor={
                          degradedCount > 0
                            ? "text-risk-alert"
                            : "text-risk-safe"
                        }
                      />
                    </div>
                  </motion.div>

                  {/* Quick summary KPIs from all sections */}
                  <motion.div variants={fadeUp}>
                    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
                      <StatCard
                        icon={Zap}
                        label="Total Requests"
                        value={apiStats?.total_requests ?? 0}
                        subValue={`Last ${apiStats?.period_minutes ?? 60} min`}
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={AlertTriangle}
                        label="Error Rate"
                        value={
                          apiStats ? formatPercent(apiStats.error_rate) : "—"
                        }
                        color={
                          (apiStats?.error_rate ?? 0) > 0.05
                            ? "text-risk-critical"
                            : "text-risk-safe"
                        }
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={Activity}
                        label="Predictions"
                        value={drift?.total_predictions ?? 0}
                        subValue={
                          drift?.drift_detected ? "Drift detected" : "Stable"
                        }
                        color={
                          drift?.drift_detected
                            ? "text-risk-critical"
                            : "text-risk-safe"
                        }
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={Bell}
                        label="Alert Success"
                        value={
                          alertStats
                            ? formatPercent(alertStats.success_rate)
                            : "—"
                        }
                        color={
                          (alertStats?.success_rate ?? 1) >= 0.95
                            ? "text-risk-safe"
                            : "text-risk-critical"
                        }
                        iconColor="text-primary"
                      />
                    </div>
                  </motion.div>

                  {/* Service Health Table */}
                  {services.length > 0 && (
                    <motion.div variants={fadeUp}>
                      <GlassCard className="overflow-hidden">
                        <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                        <CardHeader className="pb-3">
                          <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <div className="h-6 w-6 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
                              <Server className="h-3.5 w-3.5 text-primary" />
                            </div>
                            Service Health Status
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Service</TableHead>
                                <TableHead className="w-28">Status</TableHead>
                                <TableHead className="w-24 text-right">
                                  Latency
                                </TableHead>
                                <TableHead className="w-28 text-right">
                                  Uptime (24h)
                                </TableHead>
                                <TableHead className="w-40">
                                  Last Checked
                                </TableHead>
                                <TableHead>Detail</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {services.map((svc) => (
                                <TableRow key={svc.service} className="text-xs">
                                  <TableCell className="font-medium">
                                    {svc.service}
                                  </TableCell>
                                  <TableCell>
                                    {statusBadge(svc.status)}
                                  </TableCell>
                                  <TableCell className="text-right font-mono">
                                    {formatMs(svc.latency_ms)}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {svc.uptime_pct_24h != null
                                      ? `${svc.uptime_pct_24h.toFixed(1)}%`
                                      : "—"}
                                  </TableCell>
                                  <TableCell className="text-muted-foreground font-mono text-[11px]">
                                    {svc.last_checked
                                      ? new Date(
                                          svc.last_checked,
                                        ).toLocaleTimeString("en-PH", {
                                          hour: "2-digit",
                                          minute: "2-digit",
                                          second: "2-digit",
                                        })
                                      : "—"}
                                  </TableCell>
                                  <TableCell className="text-muted-foreground truncate max-w-48">
                                    {svc.detail || "—"}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </CardContent>
                      </GlassCard>
                    </motion.div>
                  )}

                  {/* Overall Health Banner */}
                  {uptime?.last_check && (
                    <motion.div variants={fadeUp}>
                      <GlassCard
                        className={cn(
                          "overflow-hidden border transition-all duration-300",
                          uptime.last_check.healthy
                            ? "border-risk-safe/20 bg-risk-safe/5"
                            : "border-risk-critical/20 bg-risk-critical/5",
                        )}
                      >
                        <div
                          className={cn(
                            "h-1 w-full bg-linear-to-r",
                            uptime.last_check.healthy
                              ? "from-primary/60 via-primary to-primary/60"
                              : "from-risk-critical/60 via-risk-critical to-risk-critical/60",
                          )}
                        />
                        <CardContent className="pt-5 pb-4 flex items-center gap-4">
                          {uptime.last_check.healthy ? (
                            <CheckCircle className="h-8 w-8 text-risk-safe shrink-0" />
                          ) : (
                            <XCircle className="h-8 w-8 text-risk-critical shrink-0" />
                          )}
                          <div>
                            <p className="font-semibold">
                              System is{" "}
                              {uptime.last_check.healthy
                                ? "Healthy"
                                : "Experiencing Issues"}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Last health check responded in{" "}
                              {formatMs(uptime.last_check.response_ms)} at{" "}
                              {new Date(
                                uptime.last_check.timestamp,
                              ).toLocaleString("en-PH")}
                            </p>
                          </div>
                        </CardContent>
                      </GlassCard>
                    </motion.div>
                  )}
                </>
              )}
            </motion.div>
          </TabsContent>

          {/* ══════════════════════════════════════ */}
          {/*  TAB 2 — API Performance              */}
          {/* ══════════════════════════════════════ */}
          <TabsContent value="api">
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate={inView ? "show" : "hidden"}
              className="space-y-6"
            >
              {apiLoading && !apiStats ? (
                <MonitoringSkeleton />
              ) : (
                <>
                  {/* KPI row */}
                  <motion.div variants={fadeUp}>
                    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
                      <StatCard
                        icon={Zap}
                        label="Total Requests"
                        value={apiStats?.total_requests ?? 0}
                        subValue={`Last ${apiStats?.period_minutes ?? 60} min`}
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={Hourglass}
                        label="Avg Response"
                        value={
                          apiStats ? formatMs(apiStats.avg_response_ms) : "—"
                        }
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={TrendingUp}
                        label="P95 Latency"
                        value={
                          apiStats ? formatMs(apiStats.p95_response_ms) : "—"
                        }
                        subValue={
                          apiStats
                            ? `P99: ${formatMs(apiStats.p99_response_ms)}`
                            : undefined
                        }
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={AlertTriangle}
                        label="Error Rate"
                        value={
                          apiStats ? formatPercent(apiStats.error_rate) : "—"
                        }
                        color={
                          (apiStats?.error_rate ?? 0) > 0.05
                            ? "text-risk-critical"
                            : "text-risk-safe"
                        }
                        iconColor="text-primary"
                      />
                    </div>
                  </motion.div>

                  {/* HTTP Status Distribution */}
                  {apiStats?.status_breakdown && (
                    <motion.div variants={fadeUp}>
                      <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                        <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                        <CardHeader className="pb-3">
                          <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <div className="h-6 w-6 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
                              <Activity className="h-3.5 w-3.5 text-primary" />
                            </div>
                            HTTP Status Distribution
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <DistributionBar
                            data={apiStats.status_breakdown}
                            total={apiStats.total_requests}
                            colors={{
                              "2xx": "bg-risk-safe",
                              "3xx": "bg-blue-500",
                              "4xx": "bg-risk-alert",
                              "5xx": "bg-risk-critical",
                            }}
                          />
                        </CardContent>
                      </GlassCard>
                    </motion.div>
                  )}

                  {/* Slowest Endpoints (enhanced with p95/p99/errors/SLA) */}
                  {apiStats?.slowest_endpoints &&
                    apiStats.slowest_endpoints.length > 0 && (
                      <motion.div variants={fadeUp}>
                        <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                          <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                              <div className="h-6 w-6 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
                                <ArrowDown className="h-3.5 w-3.5 text-primary" />
                              </div>
                              Slowest Endpoints
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="p-0">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Endpoint</TableHead>
                                  <TableHead className="w-20 text-right">
                                    Avg
                                  </TableHead>
                                  <TableHead className="w-20 text-right">
                                    P95
                                  </TableHead>
                                  <TableHead className="w-20 text-right">
                                    P99
                                  </TableHead>
                                  <TableHead className="w-16 text-right">
                                    Calls
                                  </TableHead>
                                  <TableHead className="w-16 text-right">
                                    Errors
                                  </TableHead>
                                  <TableHead className="w-16 text-center">
                                    SLA
                                  </TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {apiStats.slowest_endpoints.map((ep) => (
                                  <TableRow
                                    key={ep.endpoint}
                                    className="text-xs"
                                  >
                                    <TableCell className="font-mono text-[11px]">
                                      {ep.endpoint}
                                    </TableCell>
                                    <TableCell className="text-right font-medium">
                                      {formatMs(ep.avg_ms)}
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground">
                                      {formatMs(ep.p95_ms)}
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground">
                                      {formatMs(ep.p99_ms)}
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground">
                                      {ep.count}
                                    </TableCell>
                                    <TableCell className="text-right">
                                      <span
                                        className={
                                          ep.error_count > 0
                                            ? "text-risk-critical font-medium"
                                            : "text-muted-foreground"
                                        }
                                      >
                                        {ep.error_count}
                                      </span>
                                    </TableCell>
                                    <TableCell className="text-center">
                                      {ep.sla_exceeded ? (
                                        <Badge
                                          variant="outline"
                                          className="text-[10px] px-1.5 py-0 bg-risk-critical/15 text-risk-critical border-risk-critical/30"
                                        >
                                          Breach
                                        </Badge>
                                      ) : (
                                        <Badge
                                          variant="outline"
                                          className="text-[10px] px-1.5 py-0 bg-risk-safe/15 text-risk-safe border-risk-safe/30"
                                        >
                                          OK
                                        </Badge>
                                      )}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </CardContent>
                        </GlassCard>
                      </motion.div>
                    )}
                </>
              )}
            </motion.div>
          </TabsContent>

          {/* ══════════════════════════════════════ */}
          {/*  TAB 3 — Model Prediction Drift       */}
          {/* ══════════════════════════════════════ */}
          <TabsContent value="drift">
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate={inView ? "show" : "hidden"}
              className="space-y-6"
            >
              {driftLoading && !drift ? (
                <MonitoringSkeleton />
              ) : (
                <>
                  {/* Drift KPI row */}
                  <motion.div variants={fadeUp}>
                    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
                      <StatCard
                        icon={Activity}
                        label="Total Predictions"
                        value={drift?.total_predictions ?? 0}
                        subValue={`Last ${drift?.window_minutes ?? 60} min`}
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={TrendingUp}
                        label="PSI Score"
                        value={
                          drift?.psi != null ? drift.psi.toFixed(4) : "N/A"
                        }
                        subValue={`Threshold: ${drift?.psi_threshold ?? 0.2}`}
                        color={getDriftColor(
                          drift?.psi ?? null,
                          drift?.psi_threshold ?? 0.2,
                        )}
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={Server}
                        label="Avg Confidence"
                        value={
                          drift && Number.isFinite(drift.avg_confidence)
                            ? `${(drift.avg_confidence * 100).toFixed(1)}%`
                            : "—"
                        }
                        subValue={
                          drift?.confidence_stats?.p50 != null &&
                          drift?.confidence_stats?.p95 != null
                            ? `P50: ${(drift.confidence_stats.p50 * 100).toFixed(0)}% | P95: ${(drift.confidence_stats.p95 * 100).toFixed(0)}%`
                            : "No data"
                        }
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={
                          drift?.drift_detected ? AlertTriangle : CheckCircle
                        }
                        label="Drift Status"
                        value={drift?.drift_detected ? "Detected" : "Stable"}
                        color={
                          drift?.drift_detected
                            ? "text-risk-critical"
                            : "text-risk-safe"
                        }
                        iconColor={
                          drift?.drift_detected
                            ? "text-risk-critical"
                            : "text-risk-safe"
                        }
                      />
                    </div>
                  </motion.div>

                  {/* Drift status banner */}
                  <motion.div variants={fadeUp}>
                    <GlassCard
                      className={cn(
                        "overflow-hidden border transition-all duration-300",
                        drift?.drift_detected
                          ? "border-risk-critical/20 bg-risk-critical/5"
                          : "border-risk-safe/20 bg-risk-safe/5",
                      )}
                    >
                      <div
                        className={cn(
                          "h-1 w-full bg-linear-to-r",
                          drift?.drift_detected
                            ? "from-risk-critical/60 via-risk-critical to-risk-critical/60"
                            : "from-primary/60 via-primary to-primary/60",
                        )}
                      />
                      <CardContent className="pt-5 pb-4 flex items-center gap-4">
                        {drift?.drift_detected ? (
                          <AlertTriangle className="h-8 w-8 text-risk-critical shrink-0" />
                        ) : (
                          <CheckCircle className="h-8 w-8 text-risk-safe shrink-0" />
                        )}
                        <div>
                          <p className="font-semibold">
                            {drift?.drift_detected
                              ? "Prediction Drift Detected"
                              : "Model Predictions Are Stable"}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {drift?.drift_detected
                              ? `PSI ${drift.psi?.toFixed(4)} exceeds threshold ${drift.psi_threshold}. Consider retraining the model.`
                              : drift?.total_predictions
                                ? `PSI ${drift?.psi?.toFixed(4) ?? "N/A"} is within threshold ${drift?.psi_threshold ?? 0.2}.`
                                : "No predictions recorded yet. Make some predictions to begin drift monitoring."}
                          </p>
                        </div>
                      </CardContent>
                    </GlassCard>
                  </motion.div>

                  {/* Prediction Distribution */}
                  {drift?.current_distribution &&
                    drift.total_predictions > 0 && (
                      <motion.div variants={fadeUp}>
                        <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                          <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                              <div className="h-6 w-6 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
                                <TrendingUp className="h-3.5 w-3.5 text-primary" />
                              </div>
                              Prediction Distribution
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-4">
                              <div>
                                <p className="text-xs text-muted-foreground mb-1.5 font-medium">
                                  Current
                                </p>
                                <DistributionBar
                                  data={drift.current_distribution}
                                  total={drift.total_predictions || 1}
                                  colors={{
                                    Safe: "bg-risk-safe",
                                    safe: "bg-risk-safe",
                                    low: "bg-risk-safe",
                                    "0": "bg-risk-safe",
                                    Alert: "bg-risk-alert",
                                    alert: "bg-risk-alert",
                                    "1": "bg-risk-alert",
                                    Critical: "bg-risk-critical",
                                    critical: "bg-risk-critical",
                                    high: "bg-risk-critical",
                                    "2": "bg-risk-critical",
                                  }}
                                />
                              </div>
                              {drift.baseline_distribution && (
                                <div>
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">
                                    Baseline
                                  </p>
                                  <DistributionBar
                                    data={drift.baseline_distribution}
                                    total={
                                      Object.values(
                                        drift.baseline_distribution,
                                      ).reduce((a, b) => a + b, 0) || 1
                                    }
                                    colors={{
                                      Safe: "bg-risk-safe",
                                      safe: "bg-risk-safe",
                                      low: "bg-risk-safe",
                                      "0": "bg-risk-safe",
                                      Alert: "bg-risk-alert",
                                      alert: "bg-risk-alert",
                                      "1": "bg-risk-alert",
                                      Critical: "bg-risk-critical",
                                      critical: "bg-risk-critical",
                                      high: "bg-risk-critical",
                                      "2": "bg-risk-critical",
                                    }}
                                  />
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </GlassCard>
                      </motion.div>
                    )}

                  {/* Confidence Stats */}
                  {drift?.confidence_stats &&
                    Object.keys(drift.confidence_stats).length > 0 && (
                      <motion.div variants={fadeUp}>
                        <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                          <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                              <div className="h-6 w-6 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
                                <Gauge className="h-3.5 w-3.5 text-primary" />
                              </div>
                              Confidence Distribution
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                              <div>
                                <p className="text-lg font-bold">
                                  {drift.confidence_stats.min != null
                                    ? `${(drift.confidence_stats.min * 100).toFixed(1)}%`
                                    : "—"}
                                </p>
                                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                                  <ArrowDown className="h-3 w-3 text-risk-critical" />
                                  Min
                                </p>
                              </div>
                              <div>
                                <p className="text-lg font-bold">
                                  {drift.confidence_stats.p50 != null
                                    ? `${(drift.confidence_stats.p50 * 100).toFixed(1)}%`
                                    : "—"}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  Median (P50)
                                </p>
                              </div>
                              <div>
                                <p className="text-lg font-bold">
                                  {drift.confidence_stats.p95 != null
                                    ? `${(drift.confidence_stats.p95 * 100).toFixed(1)}%`
                                    : "—"}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  P95
                                </p>
                              </div>
                              <div>
                                <p className="text-lg font-bold">
                                  {drift.confidence_stats.max != null
                                    ? `${(drift.confidence_stats.max * 100).toFixed(1)}%`
                                    : "—"}
                                </p>
                                <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                                  <ArrowUp className="h-3 w-3 text-risk-safe" />
                                  Max
                                </p>
                              </div>
                            </div>
                          </CardContent>
                        </GlassCard>
                      </motion.div>
                    )}
                </>
              )}
            </motion.div>
          </TabsContent>

          {/* ══════════════════════════════════════ */}
          {/*  TAB 4 — Alert Delivery               */}
          {/* ══════════════════════════════════════ */}
          <TabsContent value="alerts">
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate={inView ? "show" : "hidden"}
              className="space-y-6"
            >
              {alertLoading && !alertStats ? (
                <MonitoringSkeleton />
              ) : (
                <>
                  {/* Alert KPI row */}
                  <motion.div variants={fadeUp}>
                    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
                      <StatCard
                        icon={Bell}
                        label="Total Alerts"
                        value={alertStats?.total_alerts ?? 0}
                        subValue={`Last ${alertStats?.period_hours ?? 24}h`}
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={CheckCircle}
                        label="Success Rate"
                        value={
                          alertStats
                            ? formatPercent(alertStats.success_rate)
                            : "—"
                        }
                        color={
                          (alertStats?.success_rate ?? 1) >= 0.95
                            ? "text-risk-safe"
                            : "text-risk-critical"
                        }
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={Radio}
                        label="Channels"
                        value={
                          alertStats
                            ? Object.keys(alertStats.channel_breakdown).length
                            : 0
                        }
                        iconColor="text-primary"
                      />
                      <StatCard
                        icon={BellOff}
                        label="Failures"
                        value={alertStats?.recent_failures?.length ?? 0}
                        color={
                          (alertStats?.recent_failures?.length ?? 0) > 0
                            ? "text-risk-critical"
                            : "text-risk-safe"
                        }
                        iconColor="text-primary"
                      />
                    </div>
                  </motion.div>

                  {/* Delivery Status */}
                  {alertStats?.status_breakdown && (
                    <motion.div variants={fadeUp}>
                      <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                        <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                        <CardHeader className="pb-3">
                          <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <div className="h-6 w-6 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
                              <Bell className="h-3.5 w-3.5 text-primary" />
                            </div>
                            Delivery Status
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <DistributionBar
                            data={alertStats.status_breakdown}
                            total={alertStats.total_alerts || 1}
                            colors={{
                              delivered: "bg-risk-safe",
                              sent: "bg-risk-safe",
                              success: "bg-risk-safe",
                              pending: "bg-risk-alert",
                              queued: "bg-blue-500",
                              failed: "bg-risk-critical",
                              error: "bg-risk-critical",
                            }}
                          />
                        </CardContent>
                      </GlassCard>
                    </motion.div>
                  )}

                  {/* Channel Breakdown */}
                  {alertStats?.channel_breakdown && (
                    <motion.div variants={fadeUp}>
                      <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                        <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                        <CardHeader className="pb-3">
                          <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <div className="h-6 w-6 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
                              <Radio className="h-3.5 w-3.5 text-primary" />
                            </div>
                            Channel Distribution
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <DistributionBar
                            data={alertStats.channel_breakdown}
                            total={alertStats.total_alerts || 1}
                            colors={{
                              sms: "bg-blue-500",
                              email: "bg-indigo-500",
                              push: "bg-violet-500",
                              sse: "bg-risk-safe",
                              webhook: "bg-risk-alert",
                            }}
                          />
                        </CardContent>
                      </GlassCard>
                    </motion.div>
                  )}

                  {/* Recent Failures Table */}
                  {alertStats?.recent_failures &&
                    alertStats.recent_failures.length > 0 && (
                      <motion.div variants={fadeUp}>
                        <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                          <div className="h-1 w-full bg-linear-to-r from-risk-critical/60 via-risk-critical to-risk-critical/60" />
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                              <div className="h-6 w-6 rounded-xl bg-risk-critical/10 ring-1 ring-risk-critical/25 flex items-center justify-center">
                                <XCircle className="h-3.5 w-3.5 text-risk-critical" />
                              </div>
                              Recent Failures
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="p-0">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="w-15">ID</TableHead>
                                  <TableHead className="w-22.5">Risk</TableHead>
                                  <TableHead className="w-22.5">
                                    Channel
                                  </TableHead>
                                  <TableHead>Error</TableHead>
                                  <TableHead className="w-32.5">Time</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {alertStats.recent_failures.map((f) => (
                                  <TableRow key={f.id} className="text-xs">
                                    <TableCell className="font-mono">
                                      {f.id}
                                    </TableCell>
                                    <TableCell>
                                      <Badge
                                        variant="outline"
                                        className={cn(
                                          "text-[10px] px-1.5 py-0",
                                          f.risk_label === "Critical"
                                            ? "bg-risk-critical/15 text-risk-critical border-risk-critical/30"
                                            : f.risk_label === "Alert"
                                              ? "bg-risk-alert/15 text-risk-alert border-risk-alert/30"
                                              : "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
                                        )}
                                      >
                                        {f.risk_label}
                                      </Badge>
                                    </TableCell>
                                    <TableCell className="capitalize">
                                      {f.channel}
                                    </TableCell>
                                    <TableCell className="text-risk-critical truncate max-w-50">
                                      {f.error}
                                    </TableCell>
                                    <TableCell className="font-mono text-[11px] text-muted-foreground">
                                      {new Date(f.created_at).toLocaleString(
                                        "en-PH",
                                        {
                                          month: "short",
                                          day: "numeric",
                                          hour: "2-digit",
                                          minute: "2-digit",
                                        },
                                      )}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </CardContent>
                        </GlassCard>
                      </motion.div>
                    )}
                </>
              )}
            </motion.div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
