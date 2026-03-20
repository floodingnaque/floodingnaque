/**
 * Admin System Configuration Page
 *
 * Feature flags management (grouped by category with live toggles),
 * risk threshold configuration with visual band diagram,
 * scheduled tasks overview, and configuration export.
 */

import { PageHeader, SectionHeading } from "@/components/layout";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import type { FeatureFlagDetail } from "@/features/admin/services/adminApi";
import {
  useFeatureFlags,
  useUpdateFeatureFlag,
} from "@/features/admin/hooks/useAdmin";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  Bell,
  Brain,
  Calendar,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Database,
  Download,
  Gauge,
  LayoutGrid,
  Save,
  Shield,
  SlidersHorizontal,
  ToggleRight,
  XCircle,
  Zap,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

// -- Flag Metadata --

const FLAG_META: Record<
  string,
  { label: string; description: string; category: string; critical?: boolean }
> = {
  // Notifications
  realtime_alerts: {
    label: "Real-Time SSE Alerts",
    description:
      "Enable live Server-Sent Events alert delivery to connected clients",
    category: "notifications",
  },
  sse_alerts: {
    label: "SSE Alert Streaming",
    description:
      "Enable server-sent events for real-time alert streaming to dashboards",
    category: "notifications",
  },
  sms_alerts: {
    label: "SMS Alert Delivery",
    description: "Enable SMS broadcast to registered disaster response contacts",
    category: "notifications",
  },
  sms_simulation: {
    label: "SMS Simulation Panel",
    description:
      "Enable SMS alert simulation for operators \u2014 no actual SMS sent",
    category: "notifications",
  },
  webhook_notifications: {
    label: "Webhook Notifications",
    description: "Enable webhook delivery to configured callback URLs",
    category: "notifications",
  },
  // Data Sources
  satellite_data_integration: {
    label: "Satellite Data (GEE)",
    description:
      "Enable Google Earth Engine satellite precipitation data ingestion",
    category: "data_sources",
  },
  earth_engine_integration: {
    label: "Earth Engine Integration",
    description: "Enable Google Earth Engine data pipeline",
    category: "data_sources",
  },
  tidal_monitoring: {
    label: "Tidal Monitoring",
    description: "Include WorldTides tidal data in flood risk assessments",
    category: "data_sources",
  },
  bypass_openweathermap: {
    label: "Bypass OpenWeatherMap",
    description:
      "Emergency bypass \u2014 skip OWM API calls and use cached/fallback data",
    category: "data_sources",
    critical: true,
  },
  bypass_weatherstack: {
    label: "Bypass Weatherstack",
    description: "Emergency bypass \u2014 skip Weatherstack API calls",
    category: "data_sources",
    critical: true,
  },
  bypass_worldtides: {
    label: "Bypass WorldTides",
    description: "Emergency bypass \u2014 skip WorldTides tidal API calls",
    category: "data_sources",
    critical: true,
  },
  bypass_all_external_apis: {
    label: "Bypass All External APIs",
    description:
      "Emergency kill switch \u2014 disable all external API calls system-wide",
    category: "data_sources",
    critical: true,
  },
  // AI / ML
  model_v2_rollout: {
    label: "Model v2 Rollout",
    description: "Gradual percentage-based rollout of prediction model v2",
    category: "ai_ml",
  },
  model_v2_full_release: {
    label: "Model v2 Full Release",
    description:
      "Full release of prediction model v2 (overrides rollout percentage)",
    category: "ai_ml",
  },
  enhanced_predictions: {
    label: "Enhanced Predictions",
    description:
      "Enable enhanced prediction features with confidence intervals",
    category: "ai_ml",
    critical: true,
  },
  alert_threshold_experiment: {
    label: "Alert Threshold A/B Test",
    description: "A/B test for new alert threshold configurations",
    category: "ai_ml",
  },
  model_versioning: {
    label: "Model Versioning",
    description: "Enable multi-version model management and comparison",
    category: "ai_ml",
  },
  decision_support: {
    label: "Decision Support Engine",
    description: "Show risk-aware action recommendations for operators",
    category: "ai_ml",
  },
  mlflow_tracking: {
    label: "MLflow Tracking",
    description: "Enable MLflow experiment tracking for model training runs",
    category: "ai_ml",
  },
  // Features
  csv_export: {
    label: "CSV Export",
    description: "Allow DRRMO CSV export for barangay flood data",
    category: "features",
  },
  advanced_analytics: {
    label: "Advanced Analytics",
    description: "Enable extended analytics charts and trend analysis",
    category: "features",
  },
  public_reports: {
    label: "Public Reports",
    description: "Allow residents to download monthly flood reports",
    category: "features",
  },
  // System
  rate_limit_internal_bypass: {
    label: "Rate Limit Internal Bypass",
    description: "Bypass rate limiting for internal service accounts and admin",
    category: "system",
  },
  api_rate_limiting: {
    label: "API Rate Limiting",
    description: "Enable API rate limiting protection across all endpoints",
    category: "system",
  },
  api_auth_bypass: {
    label: "Auth Bypass (Dev Only)",
    description:
      "\u26A0\uFE0F Bypass authentication \u2014 development environments only. Never enable in production.",
    category: "system",
    critical: true,
  },
};

const CATEGORIES: {
  key: string;
  label: string;
  icon: React.ElementType;
  description: string;
}[] = [
  {
    key: "notifications",
    label: "Notifications",
    icon: Bell,
    description: "Alert delivery channels and notification systems",
  },
  {
    key: "data_sources",
    label: "Data Sources",
    icon: Database,
    description: "Weather data providers and external API integrations",
  },
  {
    key: "ai_ml",
    label: "AI / Machine Learning",
    icon: Brain,
    description: "Prediction models, experiments, and ML pipeline features",
  },
  {
    key: "features",
    label: "Features",
    icon: LayoutGrid,
    description: "User-facing feature toggles and exports",
  },
  {
    key: "system",
    label: "System",
    icon: Shield,
    description: "Infrastructure, security, and internal system controls",
  },
];

// -- Scheduled Tasks (static reference) --

const SCHEDULED_TASKS = [
  {
    id: "weather_ingest",
    name: "Weather Data Ingestion",
    description:
      "Fetch weather data from PAGASA \u2192 OWM \u2192 Meteostat fallback chain",
    interval: "60 min",
    envVar: "DATA_INGEST_INTERVAL_MINUTES",
  },
  {
    id: "smart_alert_check",
    name: "Smart Alert Evaluation",
    description:
      "Run ML prediction on latest weather data and evaluate through alert pipeline",
    interval: "5 min",
    envVar: "SMART_ALERT_CHECK_INTERVAL_MINUTES",
  },
  {
    id: "auto_retrain",
    name: "Auto Model Retraining",
    description:
      "Check retraining triggers (data freshness, drift, schedule) and conditionally retrain",
    interval: "30 days",
    envVar: "AUTO_RETRAIN_INTERVAL_DAYS",
  },
  {
    id: "drift_check",
    name: "Model Drift Monitoring",
    description:
      "Compute PSI per feature, export to Prometheus gauges, log warnings",
    interval: "6 hours",
    envVar: "DRIFT_CHECK_INTERVAL_HOURS",
  },
  {
    id: "purge_expired_ips",
    name: "Purge Expired Login IPs",
    description:
      "GDPR / Data Privacy Act \u2014 purge login IP addresses past 90-day retention",
    interval: "24 hours",
    envVar: "",
  },
];

// -- Threshold Types --

interface ThresholdConfig {
  alertThreshold: number;
  criticalThreshold: number;
  alertCooldownMinutes: number;
}

function loadThresholds(): ThresholdConfig {
  try {
    const raw = localStorage.getItem("risk_thresholds_v2");
    if (raw) return JSON.parse(raw);
  } catch {
    /* use defaults */
  }
  return { alertThreshold: 30, criticalThreshold: 60, alertCooldownMinutes: 15 };
}

function saveThresholds(config: ThresholdConfig) {
  localStorage.setItem("risk_thresholds_v2", JSON.stringify(config));
}

// -- Component --

export default function AdminConfigPage() {
  const { data: flagsResponse, isLoading: flagsLoading } = useFeatureFlags();
  const updateFlag = useUpdateFeatureFlag();

  const [thresholds, setThresholds] = useState<ThresholdConfig>(loadThresholds);
  const [thresholdsDirty, setThresholdsDirty] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{
    type: "flag" | "threshold";
    title: string;
    description: string;
    onConfirm: () => void;
  } | null>(null);
  const [collapsedCategories, setCollapsedCategories] = useState<
    Record<string, boolean>
  >({});

  // All flag detail objects from the API
  const allFlags: FeatureFlagDetail[] = useMemo(
    () => flagsResponse?.flags ?? [],
    [flagsResponse?.flags],
  );

  // Group flags by category
  const groupedFlags = useMemo(() => {
    const groups: Record<string, FeatureFlagDetail[]> = {};
    for (const cat of CATEGORIES) {
      groups[cat.key] = [];
    }
    groups["other"] = [];

    for (const flag of allFlags) {
      const meta = FLAG_META[flag.name];
      const cat = meta?.category ?? "other";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(flag);
    }

    return groups;
  }, [allFlags]);

  // Count critical flags that are in a concerning state
  const criticalFlags = useMemo(() => {
    const issues: string[] = [];
    for (const flag of allFlags) {
      const meta = FLAG_META[flag.name];
      if (!meta?.critical) continue;
      if (flag.name.startsWith("bypass_") && flag.enabled) {
        issues.push(meta.label + " is active");
      }
      if (flag.name === "api_auth_bypass" && flag.enabled) {
        issues.push(meta.label + " is active");
      }
    }
    return issues;
  }, [allFlags]);

  // -- Handlers --

  const toggleCategory = useCallback((cat: string) => {
    setCollapsedCategories((prev) => ({ ...prev, [cat]: !prev[cat] }));
  }, []);

  const handleFlagToggle = useCallback(
    (flag: FeatureFlagDetail) => {
      const meta = FLAG_META[flag.name];
      const friendlyName = meta?.label ?? flag.name;
      const isCritical = meta?.critical;
      const newEnabled = !flag.enabled;

      const doToggle = () => {
        updateFlag.mutate(
          { flag: flag.name, enabled: newEnabled },
          {
            onSuccess: () =>
              toast.success(
                friendlyName + " " + (newEnabled ? "enabled" : "disabled"),
              ),
            onError: () => toast.error("Failed to update " + friendlyName),
          },
        );
      };

      if (isCritical) {
        setConfirmDialog({
          type: "flag",
          title: (newEnabled ? "Enable" : "Disable") + " " + friendlyName + "?",
          description:
            "This is a critical system flag. " +
            (newEnabled ? "Enabling" : "Disabling") +
            ' "' +
            friendlyName +
            '" will take effect immediately and may impact live flood predictions or system security.',
          onConfirm: () => {
            doToggle();
            setConfirmDialog(null);
          },
        });
      } else {
        doToggle();
      }
    },
    [updateFlag],
  );

  const handleThresholdChange = useCallback(
    (key: keyof ThresholdConfig, value: string) => {
      const num = Number(value);
      if (Number.isNaN(num)) return;
      setThresholds((prev) => ({ ...prev, [key]: num }));
      setThresholdsDirty(true);
    },
    [],
  );

  const thresholdErrors = useMemo(() => {
    const errs: string[] = [];
    if (thresholds.criticalThreshold <= thresholds.alertThreshold)
      errs.push("Critical threshold must be greater than Alert threshold");
    if (thresholds.alertThreshold < 5 || thresholds.alertThreshold > 95)
      errs.push("Alert threshold must be between 5% and 95%");
    if (thresholds.criticalThreshold < 5 || thresholds.criticalThreshold > 95)
      errs.push("Critical threshold must be between 5% and 95%");
    if (thresholds.alertCooldownMinutes < 5)
      errs.push("Minimum cooldown is 5 minutes to prevent alert flooding");
    return errs;
  }, [thresholds]);

  const handleSaveThresholds = useCallback(() => {
    if (thresholdErrors.length > 0) {
      toast.error(thresholdErrors[0]);
      return;
    }
    setConfirmDialog({
      type: "threshold",
      title: "Save Risk Thresholds?",
      description:
        "Changing risk thresholds will immediately affect how flood probability scores are classified. This may trigger or suppress active alerts.",
      onConfirm: () => {
        saveThresholds(thresholds);
        setThresholdsDirty(false);
        toast.success("Risk thresholds saved");
        setConfirmDialog(null);
      },
    });
  }, [thresholds, thresholdErrors]);

  const handleExportConfig = useCallback(() => {
    const configData = {
      exported_at: new Date().toISOString(),
      version: "1.0.0",
      feature_flags: Object.fromEntries(
        allFlags.map((f) => [
          f.name,
          {
            enabled: f.enabled,
            flag_type: f.flag_type,
            rollout_percentage: f.rollout_percentage,
            description: f.description,
          },
        ]),
      ),
      risk_thresholds: thresholds,
    };
    const blob = new Blob([JSON.stringify(configData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download =
      "floodingnaque-config-" +
      new Date().toISOString().slice(0, 10) +
      ".json";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Configuration exported");
  }, [allFlags, thresholds]);

  // -- Animation refs --
  const flagsRef = useRef<HTMLDivElement>(null);
  const flagsInView = useInView(flagsRef, { once: true, amount: 0.1 });
  const thresholdsRef = useRef<HTMLDivElement>(null);
  const thresholdsInView = useInView(thresholdsRef, {
    once: true,
    amount: 0.1,
  });
  const schedulerRef = useRef<HTMLDivElement>(null);
  const schedulerInView = useInView(schedulerRef, {
    once: true,
    amount: 0.1,
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <div className="flex items-start justify-between">
          <PageHeader
            icon={SlidersHorizontal}
            title="System Configuration"
            subtitle="Feature flags, risk thresholds, and system-wide settings"
          />
          <div className="flex items-center gap-2 pt-1">
            <Button variant="outline" size="sm" onClick={handleExportConfig}>
              <Download className="h-4 w-4 mr-1.5" />
              Export Config
            </Button>
          </div>
        </div>
      </div>

      {/* Critical Flags Banner */}
      {criticalFlags.length > 0 && (
        <div className="w-full px-6 mt-4">
          <div className="rounded-lg border border-risk-critical/40 bg-risk-critical/5 px-4 py-3 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-risk-critical shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-risk-critical">
                Critical System Flags Active
              </p>
              <ul className="text-xs text-muted-foreground mt-1 list-disc list-inside space-y-0.5">
                {criticalFlags.map((msg) => (
                  <li key={msg}>{msg}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* -- Feature Flags -- */}
      <section className="py-6 bg-muted/30">
        <div className="w-full px-6" ref={flagsRef}>
          <SectionHeading
            label="Toggles"
            title="Feature Flags"
            subtitle="Toggle system capabilities on or off \u2014 changes take effect immediately"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={flagsInView ? "show" : undefined}
            className="space-y-4"
          >
            {flagsLoading ? (
              <motion.div variants={fadeUp}>
                <GlassCard className="overflow-hidden">
                  <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                  <CardContent className="pt-6 space-y-4">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div
                        key={"fl-skel-" + i}
                        className="flex items-center justify-between"
                      >
                        <div className="space-y-1">
                          <Skeleton className="h-4 w-40" />
                          <Skeleton className="h-3 w-64" />
                        </div>
                        <Skeleton className="h-6 w-11 rounded-full" />
                      </div>
                    ))}
                  </CardContent>
                </GlassCard>
              </motion.div>
            ) : allFlags.length === 0 ? (
              <motion.div variants={fadeUp}>
                <GlassCard className="overflow-hidden">
                  <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                  <CardContent className="py-12 text-center">
                    <ToggleRight className="h-10 w-10 mx-auto text-muted-foreground/40 mb-3" />
                    <p className="text-sm text-muted-foreground">
                      No feature flags returned from the server
                    </p>
                    <p className="text-xs text-muted-foreground/70 mt-1">
                      Verify the backend FeatureFlagService is initialized.
                    </p>
                  </CardContent>
                </GlassCard>
              </motion.div>
            ) : (
              CATEGORIES.map((cat) => {
                const flags = groupedFlags[cat.key] ?? [];
                if (flags.length === 0) return null;
                const isCollapsed = collapsedCategories[cat.key] ?? false;
                const enabledCount = flags.filter((f) => f.enabled).length;
                const CatIcon = cat.icon;

                return (
                  <motion.div key={cat.key} variants={fadeUp}>
                    <FlagCategoryCard
                      icon={CatIcon}
                      label={cat.label}
                      description={cat.description}
                      enabledCount={enabledCount}
                      totalCount={flags.length}
                      isCollapsed={isCollapsed}
                      onToggleCollapse={() => toggleCategory(cat.key)}
                    >
                      {flags.map((flag) => (
                        <FlagRow
                          key={flag.name}
                          flag={flag}
                          isPending={updateFlag.isPending}
                          onToggle={() => handleFlagToggle(flag)}
                        />
                      ))}
                    </FlagCategoryCard>
                  </motion.div>
                );
              })
            )}
            {/* Uncategorised flags */}
            {(groupedFlags["other"]?.length ?? 0) > 0 && (
              <motion.div variants={fadeUp}>
                <FlagCategoryCard
                  icon={ToggleRight}
                  label="Other"
                  description="Flags not in a known category"
                  enabledCount={
                    groupedFlags["other"]!.filter((f) => f.enabled).length
                  }
                  totalCount={groupedFlags["other"]!.length}
                  isCollapsed={collapsedCategories["other"] ?? false}
                  onToggleCollapse={() => toggleCategory("other")}
                >
                  {groupedFlags["other"]!.map((flag) => (
                    <FlagRow
                      key={flag.name}
                      flag={flag}
                      isPending={updateFlag.isPending}
                      onToggle={() => handleFlagToggle(flag)}
                    />
                  ))}
                </FlagCategoryCard>
              </motion.div>
            )}
          </motion.div>
        </div>
      </section>

      {/* -- Risk Thresholds -- */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={thresholdsRef}>
          <SectionHeading
            label="Thresholds"
            title="Risk Classification"
            subtitle="Configure how flood probability maps to risk levels \u2014 affects the entire alert pipeline"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={thresholdsInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                      <Gauge className="h-4 w-4 text-primary" />
                    </div>
                    Risk Thresholds
                  </CardTitle>
                  <CardDescription>
                    Two thresholds define three continuous risk bands \u2014 no
                    gap in coverage
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Threshold band visualization */}
                  <ThresholdBand
                    alertAt={thresholds.alertThreshold}
                    criticalAt={thresholds.criticalThreshold}
                  />

                  <Separator />

                  {/* Threshold Inputs */}
                  <div className="grid gap-5 sm:grid-cols-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="alertThreshold" className="text-sm">
                        Safe \u2192 Alert boundary (%)
                      </Label>
                      <Input
                        id="alertThreshold"
                        type="number"
                        min={5}
                        max={95}
                        value={thresholds.alertThreshold}
                        onChange={(e) =>
                          handleThresholdChange(
                            "alertThreshold",
                            e.target.value,
                          )
                        }
                      />
                      <p className="text-[10px] text-muted-foreground">
                        Scores below this are classified as Safe
                      </p>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="criticalThreshold" className="text-sm">
                        Alert \u2192 Critical boundary (%)
                      </Label>
                      <Input
                        id="criticalThreshold"
                        type="number"
                        min={5}
                        max={95}
                        value={thresholds.criticalThreshold}
                        onChange={(e) =>
                          handleThresholdChange(
                            "criticalThreshold",
                            e.target.value,
                          )
                        }
                      />
                      <p className="text-[10px] text-muted-foreground">
                        Scores at or above this are Critical
                      </p>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="cooldown" className="text-sm">
                        Alert cooldown (min)
                      </Label>
                      <Input
                        id="cooldown"
                        type="number"
                        min={5}
                        max={120}
                        value={thresholds.alertCooldownMinutes}
                        onChange={(e) =>
                          handleThresholdChange(
                            "alertCooldownMinutes",
                            e.target.value,
                          )
                        }
                      />
                      <p className="text-[10px] text-muted-foreground">
                        Minimum 5 min between alerts of the same level
                      </p>
                    </div>
                  </div>

                  {/* Validation errors */}
                  {thresholdErrors.map((err) => (
                    <p
                      key={err}
                      className="text-xs text-risk-critical flex items-center gap-1"
                    >
                      <AlertTriangle className="h-3 w-3 shrink-0" />
                      {err}
                    </p>
                  ))}

                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">
                      {thresholdsDirty
                        ? "You have unsaved changes"
                        : "All changes saved"}
                    </p>
                    <Button
                      onClick={handleSaveThresholds}
                      disabled={
                        !thresholdsDirty || thresholdErrors.length > 0
                      }
                    >
                      <Save className="h-4 w-4 mr-2" />
                      Save Thresholds
                    </Button>
                  </div>
                </CardContent>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* -- Scheduled Tasks -- */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={schedulerRef}>
          <SectionHeading
            label="Scheduler"
            title="Scheduled Tasks"
            subtitle="Background jobs managed by APScheduler \u2014 configure via environment variables"
          />
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={schedulerInView ? "show" : undefined}
          >
            <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
              <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                    <Calendar className="h-4 w-4 text-primary" />
                  </div>
                  Background Jobs
                </CardTitle>
                <CardDescription>
                  Jobs run via APScheduler with distributed locking \u2014 one
                  Gunicorn worker owns the scheduler
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {SCHEDULED_TASKS.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                          <Clock className="h-4 w-4 text-primary" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{task.name}</p>
                          <p className="text-xs text-muted-foreground line-clamp-1">
                            {task.description}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 ml-4">
                        <Badge variant="outline" className="text-xs">
                          <Zap className="h-3 w-3 mr-1" />
                          {task.interval}
                        </Badge>
                        {task.envVar && (
                          <Badge
                            variant="secondary"
                            className="text-[10px] font-mono hidden lg:flex"
                          >
                            {task.envVar}
                          </Badge>
                        )}
                        <Badge
                          variant="outline"
                          className="text-xs bg-risk-safe/10 text-risk-safe border-risk-safe/30"
                        >
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Active
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </GlassCard>
          </motion.div>
        </div>
      </section>

      {/* -- Confirmation Dialog -- */}
      <AlertDialog
        open={confirmDialog !== null}
        onOpenChange={(open) => !open && setConfirmDialog(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              {confirmDialog?.type === "flag" ? (
                <AlertTriangle className="h-5 w-5 text-risk-alert" />
              ) : (
                <Gauge className="h-5 w-5 text-primary" />
              )}
              {confirmDialog?.title}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmDialog?.description}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDialog?.onConfirm}
              className={cn(
                confirmDialog?.type === "flag" &&
                  "bg-risk-alert hover:bg-risk-alert/90",
              )}
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// -- Flag Category Card --

function FlagCategoryCard({
  icon: Icon,
  label,
  description,
  enabledCount,
  totalCount,
  isCollapsed,
  onToggleCollapse,
  children,
}: {
  icon: React.ElementType;
  label: string;
  description: string;
  enabledCount: number;
  totalCount: number;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  children: React.ReactNode;
}) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
      <button
        type="button"
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-muted/20 transition-colors"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">{label}</h3>
              <Badge variant="outline" className="text-[10px]">
                {enabledCount}/{totalCount} enabled
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>
        {isCollapsed ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
      </button>
      {!isCollapsed && (
        <CardContent className="pt-0 pb-4 space-y-1">{children}</CardContent>
      )}
    </GlassCard>
  );
}

// -- Flag Row --

function FlagRow({
  flag,
  isPending,
  onToggle,
}: {
  flag: FeatureFlagDetail;
  isPending: boolean;
  onToggle: () => void;
}) {
  const meta = FLAG_META[flag.name];
  const label = meta?.label ?? flag.name.replace(/_/g, " ");
  const description = meta?.description ?? flag.description;
  const isCritical = meta?.critical ?? false;

  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-lg px-4 py-3",
        isCritical &&
          flag.enabled &&
          "bg-risk-alert/5 ring-1 ring-risk-alert/15",
        !isCritical && "hover:bg-muted/30",
      )}
    >
      <div className="space-y-0.5 min-w-0 mr-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{label}</span>
          {isCritical && (
            <Badge
              variant="outline"
              className="text-[10px] bg-risk-alert/10 text-risk-alert border-risk-alert/30"
            >
              Critical
            </Badge>
          )}
          {flag.flag_type !== "boolean" && (
            <Badge variant="secondary" className="text-[10px]">
              {flag.flag_type}
            </Badge>
          )}
          {flag.force_value !== null && (
            <Badge
              variant="outline"
              className="text-[10px] bg-risk-critical/10 text-risk-critical border-risk-critical/30"
            >
              Override
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground line-clamp-1">
          {description}
        </p>
        <p className="text-[10px] text-muted-foreground/60 font-mono">
          {flag.name}
          {flag.updated_at &&
            " \u00B7 updated " +
              new Date(flag.updated_at).toLocaleDateString("en-PH")}
        </p>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <Badge
          variant="outline"
          className={cn(
            "text-[10px] min-w-16 justify-center",
            flag.enabled
              ? "bg-risk-safe/10 text-risk-safe border-risk-safe/30"
              : "bg-muted text-muted-foreground",
          )}
        >
          {flag.enabled ? (
            <>
              <CheckCircle className="h-3 w-3 mr-1" />
              On
            </>
          ) : (
            <>
              <XCircle className="h-3 w-3 mr-1" />
              Off
            </>
          )}
        </Badge>
        <Switch
          checked={flag.enabled}
          onCheckedChange={onToggle}
          disabled={isPending}
        />
      </div>
    </div>
  );
}

// -- Threshold Band Visualization --

function ThresholdBand({
  alertAt,
  criticalAt,
}: {
  alertAt: number;
  criticalAt: number;
}) {
  const safeWidth = Math.max(alertAt, 0);
  const alertWidth = Math.max(criticalAt - alertAt, 0);
  const criticalWidth = Math.max(100 - criticalAt, 0);

  return (
    <div className="space-y-2">
      <div className="flex h-10 rounded-lg overflow-hidden text-xs font-medium">
        {safeWidth > 0 && (
          <div
            className="flex items-center justify-center bg-risk-safe/25 text-risk-safe border-r border-background/50 transition-all duration-300"
            style={{ width: safeWidth + "%" }}
          >
            {safeWidth >= 12 && <span>Safe 0\u2013{alertAt}%</span>}
          </div>
        )}
        {alertWidth > 0 && (
          <div
            className="flex items-center justify-center bg-risk-alert/25 text-risk-alert border-r border-background/50 transition-all duration-300"
            style={{ width: alertWidth + "%" }}
          >
            {alertWidth >= 12 && (
              <span>
                Alert {alertAt}\u2013{criticalAt}%
              </span>
            )}
          </div>
        )}
        {criticalWidth > 0 && (
          <div
            className="flex items-center justify-center bg-risk-critical/25 text-risk-critical transition-all duration-300"
            style={{ width: criticalWidth + "%" }}
          >
            {criticalWidth >= 12 && (
              <span>Critical {criticalAt}\u2013100%</span>
            )}
          </div>
        )}
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground/70 px-1">
        <span>0%</span>
        <span>50%</span>
        <span>100%</span>
      </div>
    </div>
  );
}
