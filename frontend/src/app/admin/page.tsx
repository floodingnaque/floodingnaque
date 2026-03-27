/**
 * Admin Page
 *
 * Admin dashboard with real-time system health monitoring and
 * dashboard statistics. Restricted to users with admin role.
 */

import { useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Cpu,
  Database,
  FileText,
  Loader2,
  Radio,
  RefreshCw,
  Server,
  Shield,
  Users,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { fadeUp, staggerContainer } from "@/lib/motion";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  adminQueryKeys,
  useSystemHealth,
} from "@/features/admin/hooks/useAdmin";
import { BarangayRiskMap } from "@/features/dashboard";
import {
  dashboardQueryKeys,
  useDashboardStats,
} from "@/features/dashboard/hooks/useDashboard";
import { cn } from "@/lib/utils";
import { useUser } from "@/state";

/** Friendly labels for model performance metric keys */
const METRIC_LABELS: Record<string, string> = {
  accuracy: "Accuracy",
  f1_score: "F1 Score",
  f2_score: "F2 Score",
  precision: "Precision",
  recall: "Recall",
  cross_val_mean: "CV Mean",
  cross_val_std: "CV Std",
  roc_auc: "ROC AUC",
  log_loss: "Log Loss",
  mcc: "MCC",
  cohen_kappa: "Cohen Kappa",
};

const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  operator: "LGU Operator",
  user: "Resident",
};

/** Format infrastructure status strings for display */
function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Determine color class for a health status badge */
function statusColor(ok: boolean | undefined, degraded?: boolean): string {
  if (ok === undefined) return "bg-muted text-muted-foreground hover:bg-muted";
  if (degraded)
    return "bg-risk-alert/15 text-risk-alert hover:bg-risk-alert/15";
  return ok
    ? "bg-risk-safe/15 text-risk-safe hover:bg-risk-safe/15"
    : "bg-risk-critical/15 text-risk-critical hover:bg-risk-critical/15";
}

/** Color for a stat card accent bar based on health */
type HealthLevel = "good" | "warn" | "critical" | "neutral";

function accentGradient(level: HealthLevel): string {
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

function statTextColor(level: HealthLevel): string {
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

/**
 * Color-coded stat card component
 */
function StatCard({
  icon: Icon,
  label,
  value,
  description,
  isLoading,
  health = "neutral",
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  description?: string;
  isLoading?: boolean;
  health?: HealthLevel;
}) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div
        className={cn("h-1 w-full bg-linear-to-r", accentGradient(health))}
      />
      <div className="pt-6 px-6 pb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "p-2 rounded-xl ring-1",
                health === "neutral"
                  ? "bg-primary/10 ring-primary/20"
                  : health === "good"
                    ? "bg-risk-safe/10 ring-risk-safe/20"
                    : health === "warn"
                      ? "bg-risk-alert/10 ring-risk-alert/20"
                      : "bg-risk-critical/10 ring-risk-critical/20",
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
              <p className="text-sm text-muted-foreground">{label}</p>
              {isLoading ? (
                <Skeleton className="h-8 w-16 mt-1" />
              ) : (
                <p className={cn("text-2xl font-bold", statTextColor(health))}>
                  {value}
                </p>
              )}
            </div>
          </div>
        </div>
        {description && (
          <p className="text-xs text-muted-foreground mt-2">{description}</p>
        )}
      </div>
    </GlassCard>
  );
}

/**
 * Service health row for the infrastructure grid
 */
function ServiceRow({
  label,
  status,
  ok,
  degraded,
  latency,
  detail,
  isLoading,
}: {
  label: string;
  status: string;
  ok?: boolean;
  degraded?: boolean;
  latency?: number | null;
  detail?: string;
  isLoading?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-between py-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-5 w-16" />
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        {latency != null && (
          <span
            className={cn(
              "text-xs font-medium",
              latency > 500
                ? "text-risk-critical"
                : latency > 200
                  ? "text-risk-alert"
                  : "text-muted-foreground",
            )}
          >
            {Math.round(latency)}ms
          </span>
        )}
        <Badge className={cn("text-xs", statusColor(ok, degraded))}>
          {ok === true && <CheckCircle className="h-3 w-3 mr-1" />}
          {ok === false && <XCircle className="h-3 w-3 mr-1" />}
          {ok === undefined && <Clock className="h-3 w-3 mr-1" />}
          {status}
        </Badge>
        {detail && (
          <span className="text-xs text-muted-foreground">{detail}</span>
        )}
      </div>
    </div>
  );
}

/**
 * Admin Page Component
 */
export default function AdminPage() {
  const navigate = useNavigate();
  const user = useUser();
  const queryClient = useQueryClient();

  // Redirect non-admin users to dashboard
  useEffect(() => {
    if (user && user.role !== "admin") {
      navigate("/dashboard", { replace: true });
    }
  }, [user, navigate]);

  // Fetch real data
  const {
    data: health,
    isLoading: healthLoading,
    isFetching: healthFetching,
    dataUpdatedAt: healthUpdatedAt,
  } = useSystemHealth(!!user && user.role === "admin");

  const {
    data: dashStats,
    isLoading: statsLoading,
    dataUpdatedAt: statsUpdatedAt,
  } = useDashboardStats();

  // Last updated timestamp
  const lastUpdated = Math.max(healthUpdatedAt || 0, statsUpdatedAt || 0);
  const [, setTick] = useState(0);

  // Force re-render every 15s to keep relative timestamps fresh
  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 15_000);
    return () => clearInterval(interval);
  }, []);

  // Refresh all admin queries
  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: adminQueryKeys.health() });
    queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stats() });
  }, [queryClient]);

  // Hooks must be called before any early returns
  const statsRef = useRef<HTMLDivElement>(null);
  const statsInView = useInView(statsRef, { once: true, amount: 0.1 });
  const infraRef = useRef<HTMLDivElement>(null);
  const infraInView = useInView(infraRef, { once: true, amount: 0.1 });
  const metricsRef = useRef<HTMLDivElement>(null);
  const metricsInView = useInView(metricsRef, { once: true, amount: 0.1 });

  // Show nothing while checking permissions
  if (!user || user.role !== "admin") {
    return null;
  }

  // Derived health state
  const isHealthy = health?.status === "healthy";
  const dbConnected = health?.checks?.database?.connected ?? false;
  const dbLatency = health?.checks?.database?.latency_ms;
  const modelLoaded = health?.checks?.model_available ?? false;
  const slaResponseMs = health?.sla?.response_time_ms;
  const slaWithin = health?.sla?.within_sla ?? true;
  const slaThreshold = health?.sla?.threshold_ms ?? 1000;
  const schedulerRunning = health?.checks?.scheduler_running ?? false;
  const sentryEnabled = health?.checks?.sentry_enabled ?? false;
  const redisStatus = health?.checks?.redis?.status ?? "unknown";
  const cacheStatus = health?.checks?.cache?.status ?? "unknown";
  const poolSize = health?.checks?.database_pool?.size;

  // Stat card health levels
  const predictionsHealth: HealthLevel =
    (dashStats?.total_predictions ?? 0) > 0 ? "good" : "neutral";

  const alertsHealth: HealthLevel =
    dashStats?.active_alerts == null
      ? "neutral"
      : dashStats.active_alerts === 0
        ? "good"
        : dashStats.active_alerts > 5
          ? "critical"
          : "warn";

  const apiHealth: HealthLevel =
    slaResponseMs == null
      ? "neutral"
      : slaWithin
        ? slaResponseMs > slaThreshold * 0.8
          ? "warn"
          : "good"
        : "critical";

  const riskHealth: HealthLevel =
    dashStats?.avg_risk_level == null
      ? "neutral"
      : dashStats.avg_risk_level < 0.5
        ? "good"
        : dashStats.avg_risk_level < 1.2
          ? "warn"
          : "critical";

  // Degraded service detection for warning banner
  const degradedServices: string[] = [];
  if (!healthLoading && health) {
    if (!dbConnected) degradedServices.push("Database");
    if (!modelLoaded) degradedServices.push("ML Model");
    if (!schedulerRunning) degradedServices.push("Scheduler");
    if (redisStatus === "unhealthy") degradedServices.push("Redis");
    if (cacheStatus === "error") degradedServices.push("Cache");
    if (!slaWithin) degradedServices.push("API SLA");
    if (dbLatency != null && dbLatency > 500)
      degradedServices.push("DB Latency");
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <Breadcrumb
          items={[{ label: "Admin", href: "/admin" }, { label: "Dashboard" }]}
          className="mb-4"
        />
        <PageHeader
          icon={Shield}
          title="Admin Panel"
          subtitle="System health monitoring and statistics"
          actions={
            <div className="flex items-center gap-3">
              {lastUpdated > 0 && (
                <span className="text-xs text-white/60">
                  Updated{" "}
                  {formatDistanceToNow(new Date(lastUpdated), {
                    addSuffix: true,
                  })}
                </span>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={healthFetching}
                className="border border-white/20 text-white hover:bg-white/10 hover:text-white"
              >
                {healthFetching ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Refresh
              </Button>
            </div>
          }
        />
      </div>

      {/* SLA / Degraded Service Warning Banner */}
      {degradedServices.length > 0 ? (
        <div className="w-full px-6 mt-4">
          <div className="rounded-xl border border-risk-critical/30 bg-risk-critical/5 px-4 py-3 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-risk-critical shrink-0" />
            <div className="text-sm">
              <span className="font-semibold text-risk-critical">
                Service Degradation Detected
              </span>
              <span className="text-muted-foreground">
                {" - "}
                {degradedServices.join(", ")}{" "}
                {degradedServices.length === 1 ? "requires" : "require"}{" "}
                attention.
              </span>
            </div>
          </div>
        </div>
      ) : !healthLoading && health ? (
        <div className="w-full px-6 mt-4">
          <div className="rounded-xl border border-risk-safe/30 bg-risk-safe/5 px-4 py-3 flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-risk-safe shrink-0" />
            <span className="text-sm font-medium text-risk-safe">
              All Systems Operational
            </span>
          </div>
        </div>
      ) : null}

      {/* Quick Actions */}
      <div className="w-full px-6 mt-4">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => navigate("/admin/alerts")}
          >
            <Radio className="h-3.5 w-3.5" />
            Broadcast Alert
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => navigate("/admin/users")}
          >
            <Users className="h-3.5 w-3.5" />
            Manage Users
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => navigate("/admin/logs")}
          >
            <FileText className="h-3.5 w-3.5" />
            View Logs
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => navigate("/admin/config")}
          >
            <Server className="h-3.5 w-3.5" />
            System Config
          </Button>
        </div>
      </div>

      {/* System Stats Section */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={statsRef}>
          <SectionHeading
            label="Overview"
            title="System Statistics"
            subtitle="Key metrics and performance indicators for the flood prediction system"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={statsInView ? "show" : undefined}
            className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
          >
            <motion.div variants={fadeUp}>
              <StatCard
                icon={Activity}
                label="Total Predictions"
                value={dashStats?.total_predictions?.toLocaleString() ?? "N/A"}
                description={`${dashStats?.predictions_today ?? 0} today`}
                isLoading={statsLoading}
                health={predictionsHealth}
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={AlertTriangle}
                label="Active Alerts"
                value={dashStats?.active_alerts ?? "N/A"}
                description={
                  dashStats?.active_alerts == null
                    ? undefined
                    : dashStats.active_alerts === 0
                      ? "All clear"
                      : "Requires attention"
                }
                isLoading={statsLoading}
                health={alertsHealth}
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={Server}
                label="API Response"
                value={
                  slaResponseMs != null
                    ? `${Math.round(slaResponseMs)}ms`
                    : "N/A"
                }
                description={
                  health?.sla == null
                    ? undefined
                    : slaWithin
                      ? `Within ${slaThreshold}ms SLA`
                      : `Exceeds ${slaThreshold}ms SLA`
                }
                isLoading={healthLoading}
                health={apiHealth}
              />
            </motion.div>
            <motion.div variants={fadeUp}>
              <StatCard
                icon={Shield}
                label="Avg Risk Level"
                value={
                  dashStats?.avg_risk_level != null
                    ? `${(dashStats.avg_risk_level * 50).toFixed(0)}%`
                    : "N/A"
                }
                description={
                  dashStats?.avg_risk_level == null
                    ? undefined
                    : dashStats.avg_risk_level < 0.5
                      ? "Low risk"
                      : dashStats.avg_risk_level < 1.2
                        ? "Moderate risk"
                        : "High risk"
                }
                isLoading={statsLoading}
                health={riskHealth}
              />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Barangay Flood Risk Map */}
      <section className="py-10 bg-background">
        <div className="w-full px-6">
          <SectionHeading
            label="Situational Awareness"
            title="Barangay Flood Risk Map"
            subtitle="City-wide overview of current flood risk levels per barangay"
          />
          <BarangayRiskMap height={500} />
        </div>
      </section>

      {/* Infrastructure Section */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={infraRef}>
          <SectionHeading
            label="Infrastructure"
            title="Service Health"
            subtitle="Real-time status of all system dependencies"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={infraInView ? "show" : undefined}
            className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
          >
            {/* Database & Pool */}
            <motion.div variants={fadeUp}>
              <Card className="hover:shadow-md transition-all duration-300 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
                      <Database className="h-4 w-4 text-primary" />
                    </div>
                    Database
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 divide-y divide-border/30">
                  <ServiceRow
                    label="Connection"
                    status={dbConnected ? "Connected" : "Disconnected"}
                    ok={dbConnected}
                    latency={dbLatency}
                    isLoading={healthLoading}
                  />
                  <ServiceRow
                    label="Pool Size"
                    status={poolSize != null ? String(poolSize) : "N/A"}
                    ok={poolSize != null ? poolSize > 0 : undefined}
                    detail={
                      health?.checks?.database_pool?.checked_out != null
                        ? `${health.checks.database_pool.checked_out} in use`
                        : undefined
                    }
                    isLoading={healthLoading}
                  />
                  {dbLatency != null && dbLatency > 500 && (
                    <p className="text-xs text-risk-alert pt-2">
                      <AlertTriangle className="h-3 w-3 inline" /> Database
                      latency exceeds 500ms threshold
                    </p>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Server & Scheduler */}
            <motion.div variants={fadeUp}>
              <Card className="hover:shadow-md transition-all duration-300 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
                      <Server className="h-4 w-4 text-primary" />
                    </div>
                    Server
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 divide-y divide-border/30">
                  <ServiceRow
                    label="Health"
                    status={isHealthy ? "Healthy" : "Degraded"}
                    ok={isHealthy}
                    degraded={!isHealthy && health != null}
                    isLoading={healthLoading}
                  />
                  <ServiceRow
                    label="Scheduler"
                    status={schedulerRunning ? "Running" : "Stopped"}
                    ok={schedulerRunning}
                    isLoading={healthLoading}
                  />
                  <ServiceRow
                    label="Sentry"
                    status={sentryEnabled ? "Enabled" : "Disabled"}
                    ok={sentryEnabled ? true : undefined}
                    isLoading={healthLoading}
                  />
                </CardContent>
              </Card>
            </motion.div>

            {/* Services: ML Model, Redis, Cache */}
            <motion.div variants={fadeUp}>
              <Card className="hover:shadow-md transition-all duration-300 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
                      <Cpu className="h-4 w-4 text-primary" />
                    </div>
                    Services
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 divide-y divide-border/30">
                  <ServiceRow
                    label="ML Model"
                    status={modelLoaded ? "Loaded" : "Not Available"}
                    ok={modelLoaded}
                    detail={health?.model?.version ?? undefined}
                    isLoading={healthLoading}
                  />
                  <ServiceRow
                    label="Redis"
                    status={formatStatus(redisStatus)}
                    ok={
                      redisStatus === "healthy"
                        ? true
                        : redisStatus === "not_configured"
                          ? undefined
                          : false
                    }
                    latency={
                      health?.checks?.redis?.connected ? undefined : null
                    }
                    isLoading={healthLoading}
                  />
                  <ServiceRow
                    label="Cache"
                    status={formatStatus(cacheStatus)}
                    ok={
                      cacheStatus === "healthy"
                        ? true
                        : cacheStatus === "not_available" ||
                            cacheStatus === "unknown"
                          ? undefined
                          : false
                    }
                    isLoading={healthLoading}
                  />
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>

          {/* Last checked timestamp */}
          {health?.timestamp && (
            <p className="text-xs text-muted-foreground mt-4 text-right">
              Last health check:{" "}
              {new Date(health.timestamp).toLocaleString("en-PH", {
                dateStyle: "medium",
                timeStyle: "medium",
              })}
            </p>
          )}
        </div>
      </section>

      {/* Model Metrics & System Info Section */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={metricsRef}>
          <SectionHeading
            label="Performance"
            title="Model & System Details"
            subtitle="ML model performance metrics and server configuration"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={metricsInView ? "show" : undefined}
            className="space-y-6"
          >
            {/* Model Metrics */}
            {health?.model?.metrics &&
              Object.keys(health.model.metrics).length > 0 && (
                <motion.div variants={fadeUp}>
                  <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                          <Activity className="h-5 w-5 text-primary" />
                        </div>
                        Model Performance Metrics
                        {health.model.version && (
                          <Badge
                            variant="outline"
                            className="ml-2 text-xs font-normal"
                          >
                            {health.model.version}
                          </Badge>
                        )}
                      </CardTitle>
                      <CardDescription>
                        Current ML model accuracy and performance scores
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
                        {Object.entries(health.model.metrics).map(
                          ([key, value]) => {
                            const isPercentage =
                              typeof value === "number" && value <= 1;
                            const displayVal = isPercentage
                              ? `${(value * 100).toFixed(1)}%`
                              : typeof value === "number"
                                ? value.toFixed(2)
                                : String(value);

                            // Flag CV Std if unusually high
                            const isHighStd =
                              key === "cross_val_std" &&
                              typeof value === "number" &&
                              value > 0.05;

                            return (
                              <div key={key} className="space-y-1">
                                <p className="text-sm text-muted-foreground">
                                  {METRIC_LABELS[key] ?? formatStatus(key)}
                                </p>
                                <p
                                  className={cn(
                                    "text-xl font-bold",
                                    isHighStd && "text-risk-alert",
                                  )}
                                >
                                  {displayVal}
                                </p>
                                {isHighStd && (
                                  <p className="text-xs text-risk-alert">
                                    <AlertTriangle className="h-3 w-3 inline" />{" "}
                                    High variance
                                  </p>
                                )}
                              </div>
                            );
                          },
                        )}
                      </div>
                    </CardContent>
                  </GlassCard>
                </motion.div>
              )}

            {/* System Info */}
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                      <Server className="h-5 w-5 text-primary" />
                    </div>
                    System Information
                  </CardTitle>
                  <CardDescription>
                    Server environment and configuration details
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">
                        Python Version
                      </p>
                      <p className="font-medium">
                        {health?.system?.python_version ?? "N/A"}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">
                        Model Type
                      </p>
                      <p className="font-medium">
                        {health?.model?.type ?? "N/A"}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">
                        Feature Count
                      </p>
                      <p className="font-medium">
                        {health?.model?.features_count ?? "N/A"}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">
                        Last Health Check
                      </p>
                      <p className="font-medium">
                        {health?.timestamp
                          ? new Date(health.timestamp).toLocaleString("en-PH", {
                              dateStyle: "medium",
                              timeStyle: "short",
                            })
                          : "N/A"}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">
                        SLA Threshold
                      </p>
                      <p className="font-medium">
                        {health?.sla?.threshold_ms
                          ? `${health.sla.threshold_ms}ms`
                          : "N/A"}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">
                        Logged in as
                      </p>
                      <p className="font-medium">
                        {user.name || user.email} (
                        {ROLE_LABELS[user.role] ?? user.role})
                      </p>
                    </div>
                  </div>
                </CardContent>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
