/**
 * ResidentDashboard Component - Landing-Page-Inspired Overhaul
 *
 * Design language from the public landing page applied to the
 * authenticated resident dashboard:
 *   • Dark hero banner with live risk badge + glass metric pills
 *   • Animated count-up stat cards
 *   • Section headings with green uppercase label + bold title
 *   • Framer-motion stagger animations on cards
 *   • Alternating section backgrounds (bg-background / bg-muted/30)
 *
 * Layout:
 *   ┌────────────────────────────────────────────┐
 *   │  Dark Hero Banner (risk status + metrics)  │
 *   ├────────────────────────────────────────────┤
 *   │  Animated Stats Row (4 KPIs)               │
 *   ├───────────────────────┬────────────────────┤
 *   │  BarangayRiskMap      │  AlertFeed +       │
 *   │  (2/3)                │  TidalRisk +       │
 *   │                       │  Reports (1/3)     │
 *   ├───────────────────────┴────────────────────┤
 *   │  Trend Charts (2-col)                      │
 *   ├────────────────────────────────────────────┤
 *   │  Emergency Info                            │
 *   └────────────────────────────────────────────┘
 */

import { RainEffect } from "@/components/effects/RainEffect";
import {
  ChartErrorBoundary,
  ConnectionStatus,
  ErrorDisplay,
  MapErrorBoundary,
} from "@/components/feedback";
import { FloodIcon } from "@/components/icons/FloodIcon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { BARANGAYS } from "@/config/paranaque";
import {
  EmailSubscriptionToggle,
  SmsSubscriptionToggle,
  useRecentAlerts,
} from "@/features/alerts";
import { PushPermissionPrompt } from "@/features/alerts/components/PushPermissionPrompt";
import { useModelHistory } from "@/features/dashboard/hooks/useAnalytics";
import { useDashboardStats } from "@/features/dashboard/hooks/useDashboard";
import { EvacuationCapacityCard } from "@/features/evacuation";
import { PersonalizedRiskBanner } from "@/features/flooding/components/PersonalizedRiskBanner";
import { RiskBadge } from "@/features/flooding/components/RiskBadge";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { useReportExport } from "@/features/reports/hooks/useReports";
import { TidalRiskIndicator } from "@/features/weather/components/TidalRiskIndicator";
import { useCurrentTide } from "@/features/weather/hooks/useTides";
import { cn } from "@/lib/utils";
import type { PredictionResponse, RiskLevel } from "@/types";
import { motion, useInView } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Clock,
  CloudRain,
  Download,
  Droplets,
  FileText,
  Loader2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ShieldPlus,
  Thermometer,
  Waves,
} from "lucide-react";
import { memo, useEffect, useRef, useState } from "react";
import { AlertCenterPanel } from "./AlertCenterPanel";
import { AlertFrequency, RainfallTrend } from "./AnalyticsCharts";
import { BarangayRiskMap } from "./BarangayRiskMap";
import { EmergencyInfoPanel } from "./EmergencyInfoPanel";
import { EvacuationStatusGrid } from "./EvacuationStatusGrid";
import { HistoricalFloodPanel } from "./HistoricalFloodPanel";
import { RainfallMonitor } from "./RainfallMonitor";

// ═══════════════════════════════════════════════════════════════════════════
// Design Tokens (mirrors landing page HeroSection + RiskExplainer)
// ═══════════════════════════════════════════════════════════════════════════

const RISK_CFG: Record<
  RiskLevel,
  { label: string; bg: string; icon: typeof ShieldCheck; textCls: string }
> = {
  0: {
    label: "SAFE",
    bg: "bg-risk-safe",
    icon: ShieldCheck,
    textCls: "text-risk-safe",
  },
  1: {
    label: "ALERT",
    bg: "bg-risk-alert",
    icon: AlertTriangle,
    textCls: "text-risk-alert",
  },
  2: {
    label: "CRITICAL",
    bg: "bg-risk-critical",
    icon: ShieldAlert,
    textCls: "text-risk-critical",
  },
};

// ═══════════════════════════════════════════════════════════════════════════
// Framer-motion variants
// ═══════════════════════════════════════════════════════════════════════════

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45 } },
};

const staggerContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1, delayChildren: 0.05 } },
};

// ═══════════════════════════════════════════════════════════════════════════
// Count-Up Hook (from landing page StatsRow)
// ═══════════════════════════════════════════════════════════════════════════

function useCountUp(
  target: number,
  duration = 1800,
  isInView: boolean,
  decimals = 0,
) {
  const [value, setValue] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (!isInView || started.current) return;
    started.current = true;
    const start = performance.now();
    const step = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(+(eased * target).toFixed(decimals));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [isInView, target, duration, decimals]);

  return value;
}

// ═══════════════════════════════════════════════════════════════════════════
// Section Heading (landing page pattern)
// ═══════════════════════════════════════════════════════════════════════════

function SectionHeading({
  label,
  title,
  subtitle,
}: {
  label: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-8">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-2">
        {label}
      </p>
      <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
        {title}
      </h2>
      {subtitle && (
        <p className="mt-2 text-muted-foreground max-w-xl leading-relaxed text-sm">
          {subtitle}
        </p>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Glass Metric Pill (landing page hero style)
// ═══════════════════════════════════════════════════════════════════════════

function GlassPill({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-linear-to-br from-white/12 to-risk-safe/12 backdrop-blur-sm border border-white/20 hover:border-risk-safe/40 transition-all duration-300 hover:shadow-md hover:shadow-risk-safe/5">
      <Icon className="h-4 w-4 text-risk-safe" />
      <div className="flex flex-col">
        <span className="text-[10px] text-white/60 uppercase tracking-wide font-medium">
          {label}
        </span>
        <span className="text-sm font-semibold text-white">{value}</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Dark Hero Banner
// ═══════════════════════════════════════════════════════════════════════════

function HeroBanner({
  prediction,
  isLoading,
  tideHeight,
  onRefresh,
  isFetching,
}: {
  prediction: PredictionResponse | null | undefined;
  isLoading: boolean;
  tideHeight?: number | null;
  onRefresh: () => void;
  isFetching: boolean;
}) {
  if (isLoading) {
    return (
      <div className="relative rounded-2xl bg-linear-to-br from-primary via-primary/95 to-primary/80 overflow-hidden ring-1 ring-white/10 shadow-2xl p-8 sm:p-10">
        <div className="relative z-10 flex flex-col items-center gap-6">
          <Skeleton className="h-14 w-48 rounded-full bg-white/20" />
          <Skeleton className="h-6 w-64 bg-white/15" />
          <div className="flex gap-3">
            <Skeleton className="h-12 w-32 rounded-xl bg-white/10" />
            <Skeleton className="h-12 w-32 rounded-xl bg-white/10" />
            <Skeleton className="h-12 w-32 rounded-xl bg-white/10" />
          </div>
        </div>
      </div>
    );
  }

  const risk = prediction ? RISK_CFG[prediction.risk_level] : null;
  const RiskIcon = risk?.icon ?? ShieldCheck;
  const rainfall = prediction?.weather_data?.precipitation ?? 0;
  const temp = prediction?.weather_data?.temperature
    ? `${Math.round(prediction.weather_data.temperature - 273.15)}°C`
    : "--";
  const humidity = prediction?.weather_data?.humidity
    ? `${Math.round(prediction.weather_data.humidity)}%`
    : "--";
  const confidence = prediction
    ? `${Math.round(prediction.confidence * 100)}%`
    : "--";
  const lastUpdated = prediction
    ? new Date(prediction.timestamp).toLocaleTimeString("en-PH", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "--";

  return (
    <div className="relative rounded-2xl bg-linear-to-br from-primary via-primary/95 to-primary/80 overflow-hidden ring-1 ring-white/10 shadow-2xl">
      <RainEffect />
      <div className="absolute inset-0 bg-linear-to-b from-black/10 via-transparent to-black/30" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.05),transparent)]" />

      <div className="relative z-10 px-6 py-8 sm:px-10 sm:py-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex flex-col items-center text-center space-y-6"
        >
          {/* Logo + Title */}
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center">
              <FloodIcon className="h-6 w-6 text-white" />
            </div>
            <div className="text-left">
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Flood Monitor
              </h1>
              <p className="text-xs text-white/50 font-medium">
                Parañaque City &middot; Real-time Assessment
              </p>
            </div>
          </div>

          {/* Risk Badge */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.4, type: "spring" }}
          >
            {risk ? (
              <Badge
                className={cn(
                  "text-xl sm:text-2xl px-8 py-3 font-bold gap-2.5 shadow-lg",
                  risk.bg,
                  prediction?.risk_level === 1 ? "text-black" : "text-white",
                )}
              >
                <RiskIcon className="h-6 w-6" />
                {risk.label}
              </Badge>
            ) : (
              <Badge className="text-lg px-6 py-2.5 font-bold bg-white/20 text-white">
                Connecting to sensors…
              </Badge>
            )}
          </motion.div>

          {/* Probability + Confidence */}
          {prediction && (
            <p className="text-sm text-white/80">
              Flood probability:{" "}
              <span className="font-bold text-white text-base">
                {Math.round(prediction.probability * 100)}%
              </span>
              {" · "}Confidence:{" "}
              <span className="font-bold text-white text-base">
                {confidence}
              </span>
              {" · "}Model {prediction.model_version}
            </p>
          )}

          {/* Glass Metric Pills */}
          <div className="flex flex-wrap gap-3 justify-center">
            <GlassPill
              icon={CloudRain}
              label="Rainfall"
              value={`${rainfall.toFixed(1)} mm`}
            />
            <GlassPill icon={Thermometer} label="Temperature" value={temp} />
            <GlassPill icon={Droplets} label="Humidity" value={humidity} />
            {tideHeight != null && (
              <GlassPill
                icon={Waves}
                label="Tide (MSL)"
                value={`${tideHeight.toFixed(2)} m`}
              />
            )}
          </div>

          {/* Trust line */}
          <p className="text-xs text-white/50">
            Real-time prediction refreshes every 60 seconds
          </p>

          {/* Timestamp + Live indicator */}
          <div className="flex items-center gap-3 text-xs text-white/60">
            <span className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-risk-safe opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-risk-safe" />
              </span>
              <span className="text-risk-safe font-semibold">LIVE</span>
            </span>
            <Clock className="h-3 w-3" />
            <span>Updated {lastUpdated}</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs text-white/60 hover:text-white hover:bg-white/10"
              onClick={onRefresh}
              disabled={isFetching}
            >
              {isFetching ? (
                <Loader2 className="h-3 w-3 animate-spin mr-1" />
              ) : (
                <RefreshCw className="h-3 w-3 mr-1" />
              )}
              Refresh
            </Button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Animated Stat Card
// ═══════════════════════════════════════════════════════════════════════════

function StatCard({
  icon: Icon,
  target,
  suffix,
  label,
  source,
  decimals,
  isInView,
}: {
  icon: React.ElementType;
  target: number;
  suffix?: string;
  label: string;
  source: string;
  decimals?: number;
  isInView: boolean;
}) {
  const count = useCountUp(target, 1800, isInView, decimals ?? 0);

  return (
    <motion.div variants={fadeUp}>
      <GlassCard className="h-full hover:shadow-lg hover:scale-[1.02] transition-all duration-300 text-center overflow-hidden">
        <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
        <CardContent className="pt-6 pb-5 px-4 space-y-2">
          <div className="h-10 w-10 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center mx-auto">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-foreground tabular-nums">
            {decimals ? count.toFixed(decimals) : count.toLocaleString()}
            {suffix}
          </p>
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">{source}</p>
        </CardContent>
      </GlassCard>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Alert Feed
// ═══════════════════════════════════════════════════════════════════════════

const AlertFeed = memo(function AlertFeed() {
  const { data: alerts, isLoading } = useRecentAlerts(5);

  if (isLoading) {
    return (
      <GlassCard className="overflow-hidden">
        <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <div className="h-7 w-7 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
              <Bell className="h-3.5 w-3.5 text-primary" />
            </div>
            Recent Alerts
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </CardContent>
      </GlassCard>
    );
  }

  if (!alerts?.length) {
    return (
      <GlassCard className="overflow-hidden">
        <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <div className="h-7 w-7 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
              <Bell className="h-3.5 w-3.5 text-primary" />
            </div>
            Recent Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-6">
            No recent alerts - all clear
          </p>
        </CardContent>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="hover:shadow-lg transition-all duration-300 overflow-hidden">
      <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="h-7 w-7 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center shrink-0">
            <Bell className="h-3.5 w-3.5 text-primary" />
          </div>
          Recent Alerts
          <Badge variant="secondary" className="ml-auto text-xs">
            {alerts.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 max-h-64 overflow-y-auto">
        {alerts.map((a) => (
          <div
            key={a.id}
            className="flex items-start gap-2 p-2.5 rounded-lg border border-border/50 text-sm hover:bg-accent/50 transition-colors"
          >
            <RiskBadge level={a.risk_level} />
            <div className="flex-1 min-w-0">
              <p className="truncate font-medium">{a.message}</p>
              <p className="text-xs text-muted-foreground">
                {new Date(a.created_at).toLocaleString("en-PH", {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
                {a.location && ` · ${a.location}`}
              </p>
            </div>
          </div>
        ))}
      </CardContent>
    </GlassCard>
  );
});

// ═══════════════════════════════════════════════════════════════════════════
// Public Report Download
// ═══════════════════════════════════════════════════════════════════════════

const PublicReportDownload = memo(function PublicReportDownload() {
  const { exportReport, isExportingPDF, isExportingCSV } = useReportExport();

  const handleMonthlyReport = () => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    exportReport(
      {
        report_type: "predictions",
        start_date: start.toISOString().split("T")[0],
        end_date: end.toISOString().split("T")[0],
      },
      "pdf",
    );
  };

  return (
    <GlassCard className="hover:shadow-lg transition-all duration-300 overflow-hidden">
      <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="h-7 w-7 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
            <FileText className="h-3.5 w-3.5 text-primary" />
          </div>
          Public Reports
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={handleMonthlyReport}
          disabled={isExportingPDF}
        >
          <Download className="h-3.5 w-3.5" />
          {isExportingPDF ? "Generating…" : "Monthly Flood Summary (PDF)"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={() => {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - 7);
            exportReport(
              {
                report_type: "weather",
                start_date: start.toISOString().split("T")[0],
                end_date: end.toISOString().split("T")[0],
              },
              "csv",
            );
          }}
          disabled={isExportingCSV}
        >
          <Download className="h-3.5 w-3.5" />
          {isExportingCSV ? "Generating…" : "Weekly Weather Data (CSV)"}
        </Button>
      </CardContent>
    </GlassCard>
  );
});

// ═══════════════════════════════════════════════════════════════════════════
// Main Resident Dashboard
// ═══════════════════════════════════════════════════════════════════════════

export function ResidentDashboard() {
  const {
    data: prediction,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useLivePrediction();

  const { data: currentTide } = useCurrentTide(true);
  const { data: dashboardStats } = useDashboardStats();
  const { data: modelHistory } = useModelHistory();

  // Intersection refs for scroll-triggered animations
  const statsRef = useRef<HTMLDivElement>(null);
  const statsInView = useInView(statsRef, { once: true, amount: 0.3 });

  const monitorRef = useRef<HTMLDivElement>(null);
  const monitorInView = useInView(monitorRef, { once: true, amount: 0.1 });

  const analyticsRef = useRef<HTMLDivElement>(null);
  const analyticsInView = useInView(analyticsRef, { once: true, amount: 0.1 });

  const highRiskCount = BARANGAYS.filter((b) => b.floodRisk === "high").length;

  // Derive live stats from API data
  const activeModel = modelHistory?.models?.find((m) => m.is_active);
  const totalRecords =
    activeModel?.training_data?.total_records ??
    dashboardStats?.total_predictions ??
    1182;
  const modelAccuracy =
    activeModel?.metrics?.accuracy != null
      ? activeModel.metrics.accuracy * 100
      : 96.75;
  const modelName = activeModel
    ? `Random Forest v${activeModel.version}`
    : "Random Forest v6";

  return (
    <div className="min-h-screen bg-background">
      {/* ── Header ── */}
      <div className="container mx-auto px-4 pt-6 pb-2">
        <div className="flex items-center justify-end">
          <ConnectionStatus showLabel size="md" />
        </div>
      </div>

      {/* ── Section 1: Dark Hero Banner ── */}
      <div className="container mx-auto px-4 pb-2">
        {isError && (
          <div className="mb-4">
            <ErrorDisplay
              error={error}
              retry={() => refetch()}
              title="Unable to fetch prediction"
            />
          </div>
        )}
        <HeroBanner
          prediction={prediction}
          isLoading={isLoading}
          tideHeight={currentTide?.height}
          onRefresh={() => refetch()}
          isFetching={isFetching}
        />
      </div>

      {/* ── Personalized Location Risk ── */}
      <div className="container mx-auto px-4 py-2">
        <PersonalizedRiskBanner />
      </div>

      {/* ── Push Permission Prompt (shown after Critical alert) ── */}
      <div className="container mx-auto px-4 py-2">
        <PushPermissionPrompt />
      </div>

      {/* ── Section 2: Animated Stats Row ── */}
      <section className="py-10 bg-linear-to-b from-muted/30 via-risk-safe/5 to-muted/30 dark:from-muted/30 dark:via-risk-safe/10 dark:to-muted/30">
        <div className="container mx-auto px-4" ref={statsRef}>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={statsInView ? "show" : undefined}
            className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6"
          >
            <StatCard
              icon={FloodIcon}
              target={totalRecords}
              label="Official Flood Records"
              source="Parañaque DRRMO 2022–2025"
              isInView={statsInView}
            />
            <StatCard
              icon={Activity}
              target={modelAccuracy}
              suffix="%"
              label="Model Accuracy"
              source={modelName}
              decimals={2}
              isInView={statsInView}
            />
            <StatCard
              icon={BarChart3}
              target={16}
              label="Barangays Monitored"
              source="All barangays of Parañaque"
              isInView={statsInView}
            />
            <StatCard
              icon={ShieldPlus}
              target={highRiskCount}
              label="High-Risk Barangays"
              source={`of ${BARANGAYS.length} total monitored`}
              isInView={statsInView}
            />
          </motion.div>
        </div>
      </section>

      {/* ── Section 2b: Alert Center ── */}
      <section className="py-6 bg-background">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.1 }}
            transition={{ duration: 0.5 }}
          >
            <AlertCenterPanel />
          </motion.div>
        </div>
      </section>

      {/* ── Section 3: Live Monitoring ── */}
      <section className="py-10 bg-background">
        <div className="container mx-auto px-4" ref={monitorRef}>
          <SectionHeading
            label="Live Monitoring"
            title="Barangay Risk Map & Alerts"
            subtitle="Real-time flood risk visualization for all 16 barangays of Parañaque City."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={monitorInView ? "show" : undefined}
            className="grid gap-6 lg:grid-cols-3"
          >
            <motion.div variants={fadeUp} className="lg:col-span-2">
              <MapErrorBoundary>
                <BarangayRiskMap prediction={prediction} height={440} />
              </MapErrorBoundary>
            </motion.div>

            <motion.div variants={fadeUp} className="space-y-6">
              <RainfallMonitor />
              <AlertFeed />
              <SmsSubscriptionToggle />
              <EmailSubscriptionToggle />
              <EvacuationCapacityCard />
              <TidalRiskIndicator />
              <PublicReportDownload />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Section 4: Trends & Analytics ── */}
      <section className="py-10 bg-linear-to-b from-muted/30 via-blue-50/5 to-muted/30 dark:from-muted/30 dark:via-blue-950/10 dark:to-muted/30">
        <div className="container mx-auto px-4" ref={analyticsRef}>
          <SectionHeading
            label="Trends & Analytics"
            title="Rainfall & Alert Patterns"
            subtitle="7-day precipitation trend and alert frequency to help you stay prepared."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={analyticsInView ? "show" : undefined}
            className="grid gap-6 md:grid-cols-2"
          >
            <motion.div variants={fadeUp}>
              <ChartErrorBoundary>
                <RainfallTrend />
              </ChartErrorBoundary>
            </motion.div>
            <motion.div variants={fadeUp}>
              <ChartErrorBoundary>
                <AlertFrequency />
              </ChartErrorBoundary>
            </motion.div>
          </motion.div>

          {/* Historical flood data */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.1 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="mt-6"
          >
            <HistoricalFloodPanel />
          </motion.div>
        </div>
      </section>

      {/* ── Section 5: Emergency Preparedness ── */}
      <section className="py-10 bg-background">
        <div className="container mx-auto px-4">
          <SectionHeading
            label="Emergency Preparedness"
            title="Hotlines & Evacuation Centers"
            subtitle="Always keep these emergency contacts accessible - especially during heavy rainfall."
          />

          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.1 }}
              transition={{ duration: 0.5 }}
            >
              <EvacuationStatusGrid />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.1 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <EmergencyInfoPanel
                riskLevel={prediction?.risk_level as RiskLevel | undefined}
              />
            </motion.div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default ResidentDashboard;
