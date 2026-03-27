/**
 * LGUDashboard Component - Landing-Page-Inspired Overhaul
 *
 * Operational dashboard for LGU / MDRRMO operators, redesigned with
 * the same design language as the public landing page:
 *   • Dark "Command Center" hero banner with RainEffect + glass pills
 *   • Animated count-up KPI stat cards
 *   • Section headings with green uppercase label + bold title
 *   • Framer-motion stagger animations on every card group
 *   • Alternating section backgrounds (bg-background / bg-muted/30)
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────┐
 *   │  Dark Command Center Hero (risk + model + pills) │
 *   ├──────────────────────────────────────────────────┤
 *   │  Animated KPI Stats Row (5 cards)                │
 *   ├────────────────────────┬─────────────────────────┤
 *   │  FloodStatusHero       │  ForecastPanel          │
 *   ├────────────────────────┴─────────────────────────┤
 *   │  Live Analytics (Rainfall · Risk · Alerts 3-col) │
 *   ├────────────────────────┬─────────────────────────┤
 *   │  Feature Importances   │  Model Summary Cards    │
 *   ├────────────────────────┼─────────────────────────┤
 *   │  Decision Support Eng  │  Tidal + SMS Simulation │
 *   ├────────────────────────┴─────────────────────────┤
 *   │  Full-Width Barangay Risk Map                    │
 *   └──────────────────────────────────────────────────┘
 */

import { RainEffect } from "@/components/effects/RainEffect";
import {
  ConnectionStatus,
  DataUnavailable,
  ErrorBoundary,
} from "@/components/feedback";
import { FloodIcon } from "@/components/icons/FloodIcon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { motion, useInView } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Clock,
  CloudRain,
  Cpu,
  Droplets,
  Loader2,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Thermometer,
  TrendingUp,
  Waves,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { BARANGAYS } from "@/config/paranaque";
import { AlertChannelPanel } from "@/features/alerts/components/AlertChannelPanel";
import { SmsSimulationPanel } from "@/features/alerts/components/SmsSimulationPanel";
import { CommunityReportsPanel } from "@/features/community/components/CommunityReportsPanel";
import { useDashboardStats } from "@/features/dashboard/hooks/useDashboard";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { TidalRiskIndicator } from "@/features/weather/components/TidalRiskIndicator";
import { useCurrentTide } from "@/features/weather/hooks/useTides";
import type { PredictionResponse, RiskLevel } from "@/types";
import {
  useModelFeatureImportance,
  useModelHistory,
} from "../hooks/useAnalytics";
import { AlertCenterPanel } from "./AlertCenterPanel";
import {
  AlertFrequency,
  RainfallTrend,
  RiskDistribution,
} from "./AnalyticsCharts";
import { BarangayRiskMap } from "./BarangayRiskMap";
import { DecisionSupportEngine } from "./DecisionSupportEngine";
import { EmergencyCommandPanel } from "./EmergencyCommandPanel";
import { EnhancedPredictionCard } from "./EnhancedPredictionCard";
import { EvacuationStatusGrid } from "./EvacuationStatusGrid";
import { FloodPreparednessGuide } from "./FloodPreparednessGuide";
import { FloodRiskHeatmap } from "./FloodRiskHeatmap";
import { FloodTrendPanel } from "./FloodTrendPanel";
import { HistoricalFloodPanel } from "./HistoricalFloodPanel";
import { ModelConfidencePanel } from "./ModelConfidencePanel";
import { ModelSummaryCards } from "./ModelManagement";
import { RainfallMonitor } from "./RainfallMonitor";
import { RiverLevelMonitor } from "./RiverLevelMonitor";

// ═══════════════════════════════════════════════════════════════════════════
// Design Tokens
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
// Count-Up Hook
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
// Glass Metric Pill (hero overlay)
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
    <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-white/12 backdrop-blur-sm border border-white/20">
      <Icon className="h-4 w-4 text-white/80" />
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
// Dark Command Center Hero Banner
// ═══════════════════════════════════════════════════════════════════════════

function CommandCenterHero({
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
  const { data: historyData } = useModelHistory();
  const models = historyData?.models ?? [];
  const latest = models.find((m) => m.is_active) ?? models[models.length - 1];

  if (isLoading) {
    return (
      <div className="relative rounded-2xl bg-primary overflow-hidden p-8 sm:p-10">
        <div className="relative z-10 flex flex-col items-center gap-6">
          <Skeleton className="h-14 w-52 rounded-full bg-white/20" />
          <Skeleton className="h-6 w-72 bg-white/15" />
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
    <div className="relative rounded-2xl bg-primary overflow-hidden">
      <RainEffect />
      <div className="absolute inset-0 bg-linear-to-b from-black/10 via-transparent to-black/20" />

      <div className="relative z-10 px-6 py-8 sm:px-10 sm:py-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex flex-col items-center text-center space-y-5"
        >
          {/* Logo + Title */}
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center">
              <Shield className="h-6 w-6 text-white" />
            </div>
            <div className="text-left">
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                LGU Command Center
              </h1>
              <p className="text-xs text-white/60 font-medium">
                Parañaque MDRRMO &middot; Flood Monitoring & Response
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

          {/* Probability + Confidence + Model */}
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

          {/* Model trust line */}
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-white/50">
            <span>
              <Cpu className="inline h-3 w-3 mr-1" />
              Model{" "}
              <strong className="text-white/70">
                v{latest?.version ?? "?"}
              </strong>
              {" · "}
              <strong className="text-white/70">
                {latest ? (latest.metrics.accuracy * 100).toFixed(1) : "--"}%
              </strong>{" "}
              accuracy
              {" · "}
              <strong className="text-white/70">
                {latest?.training_data.total_records.toLocaleString() ?? "--"}
              </strong>{" "}
              samples
            </span>
          </div>

          {/* Timestamp + Refresh */}
          <div className="flex items-center gap-3 text-xs text-white/60">
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
// Animated KPI Stat Card
// ═══════════════════════════════════════════════════════════════════════════

function KPIStatCard({
  icon: Icon,
  target,
  suffix,
  label,
  subtitle,
  accentCls,
  barGradient,
  iconRing,
  isInView,
  decimals,
  staticValue,
}: {
  icon: React.ElementType;
  target: number;
  suffix?: string;
  label: string;
  subtitle?: string;
  accentCls?: string;
  barGradient?: string;
  iconRing?: string;
  isInView: boolean;
  decimals?: number;
  staticValue?: string;
}) {
  const count = useCountUp(target, 1800, isInView, decimals ?? 0);

  return (
    <motion.div variants={fadeUp}>
      <GlassCard className="h-full hover:shadow-lg transition-all duration-300 text-center overflow-hidden group">
        <div
          className={cn(
            "h-1 w-full",
            barGradient ?? "bg-linear-to-r from-primary to-primary/60",
          )}
        />
        <CardContent className="pt-5 pb-5 px-4 space-y-2">
          <div
            className={cn(
              "h-11 w-11 rounded-xl flex items-center justify-center mx-auto ring-4 shadow-lg",
              accentCls ?? "bg-linear-to-br from-primary to-primary/80",
              iconRing ?? "ring-primary/20",
            )}
          >
            <Icon className="h-5 w-5 text-white" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-foreground tabular-nums">
            {staticValue ?? (
              <>
                {decimals ? count.toFixed(decimals) : count.toLocaleString()}
                {suffix}
              </>
            )}
          </p>
          <p className="text-sm font-medium text-foreground">{label}</p>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </CardContent>
      </GlassCard>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Feature Importance Chart (styled)
// ═══════════════════════════════════════════════════════════════════════════

function FeatureImportanceChart({ className }: { className?: string }) {
  const { data: fiData } = useModelFeatureImportance();
  const featureImportances = useMemo(
    () => fiData?.features ?? [],
    [fiData?.features],
  );

  const chartData = useMemo(
    () =>
      featureImportances.slice(0, 8).map((f) => ({
        name: f.feature.replace(/_/g, " "),
        importance: +(f.importance * 100).toFixed(1),
      })),
    [featureImportances],
  );

  return (
    <GlassCard
      className={cn(
        "hover:shadow-lg transition-all duration-300 overflow-hidden",
        className,
      )}
    >
      <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-primary/10 flex items-center justify-center ring-4 ring-primary/20 shadow-lg">
            <BarChart3 className="h-4 w-4 text-primary" />
          </div>
          Feature Importances
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 0, right: 10, bottom: 0, left: 80 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              type="number"
              tick={{ fontSize: 11 }}
              unit="%"
              className="text-muted-foreground"
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11 }}
              width={80}
              className="text-muted-foreground"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.5rem",
                fontSize: 12,
              }}
              formatter={(v: string | number | undefined) => [
                `${v ?? 0}%`,
                "Importance",
              ]}
            />
            <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
              {chartData.map((_, idx) => (
                <Cell
                  key={idx}
                  fill={
                    idx === 0
                      ? "hsl(var(--primary))"
                      : idx < 3
                        ? "hsl(var(--primary) / 0.65)"
                        : "hsl(var(--primary) / 0.4)"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </GlassCard>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Main LGU Dashboard
// ═══════════════════════════════════════════════════════════════════════════

export function LGUDashboard() {
  const {
    data: prediction,
    isLoading: predLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useLivePrediction();

  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: currentTide } = useCurrentTide(true);

  /* scroll-triggered animation refs */
  const kpiRef = useRef<HTMLDivElement>(null);
  const kpiInView = useInView(kpiRef, { once: true, amount: 0.3 });

  const opsRef = useRef<HTMLDivElement>(null);
  const opsInView = useInView(opsRef, { once: true, amount: 0.1 });

  const analyticsRef = useRef<HTMLDivElement>(null);
  const analyticsInView = useInView(analyticsRef, { once: true, amount: 0.1 });

  const modelRef = useRef<HTMLDivElement>(null);
  const modelInView = useInView(modelRef, { once: true, amount: 0.1 });

  const dseRef = useRef<HTMLDivElement>(null);
  const dseInView = useInView(dseRef, { once: true, amount: 0.1 });

  const cmdRef = useRef<HTMLDivElement>(null);
  const cmdInView = useInView(cmdRef, { once: true, amount: 0.1 });

  const commRef = useRef<HTMLDivElement>(null);
  const commInView = useInView(commRef, { once: true, amount: 0.1 });

  const highRiskCount = useMemo(
    () => BARANGAYS.filter((b) => b.floodRisk === "high").length,
    [],
  );

  return (
    <div className="min-h-screen bg-background">
      {/* ── Top Bar ── */}
      <div className="container mx-auto px-4 pt-6 pb-2">
        <div className="flex items-center justify-end">
          <ConnectionStatus showLabel size="md" />
        </div>
      </div>

      {/* ── Section 1: Dark Command Center Hero ── */}
      <div className="container mx-auto px-4 pb-2">
        {isError && (
          <div className="mb-4">
            <DataUnavailable
              title="Prediction service unavailable"
              description={
                error instanceof Error
                  ? error.message
                  : "Live prediction stream is temporarily unavailable."
              }
              action={{
                label: isFetching ? "Retrying..." : "Retry now",
                onClick: () => void refetch(),
              }}
            />
          </div>
        )}
        <CommandCenterHero
          prediction={prediction}
          isLoading={predLoading}
          tideHeight={currentTide?.height}
          onRefresh={() => refetch()}
          isFetching={isFetching}
        />
      </div>

      {/* ── Section 2: Animated KPI Stats Row ── */}
      <section className="py-10 bg-muted/30">
        <div className="container mx-auto px-4" ref={kpiRef}>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={kpiInView ? "show" : undefined}
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-5"
          >
            <KPIStatCard
              icon={AlertTriangle}
              target={highRiskCount}
              label="Barangays at Risk"
              subtitle={`of ${BARANGAYS.length} total`}
              accentCls="bg-linear-to-br from-primary to-primary/80"
              barGradient="bg-linear-to-r from-primary to-primary/80"
              iconRing="ring-primary/20"
              isInView={kpiInView}
            />
            <KPIStatCard
              icon={CloudRain}
              target={prediction?.weather_data?.precipitation ?? 0}
              suffix=" mm"
              label="Max Precipitation"
              subtitle="Current reading"
              accentCls="bg-linear-to-br from-primary to-primary/80"
              barGradient="bg-linear-to-r from-primary to-primary/80"
              iconRing="ring-primary/20"
              decimals={1}
              isInView={kpiInView}
              staticValue={
                predLoading
                  ? "-"
                  : prediction?.weather_data
                    ? `${prediction.weather_data.precipitation.toFixed(1)} mm`
                    : "-"
              }
            />
            <KPIStatCard
              icon={Activity}
              target={stats?.active_alerts ?? 0}
              label="Active Alerts"
              subtitle="Unresolved"
              accentCls="bg-linear-to-br from-primary to-primary/80"
              barGradient="bg-linear-to-r from-primary to-primary/80"
              iconRing="ring-primary/20"
              isInView={kpiInView}
              staticValue={
                statsLoading ? "-" : String(stats?.active_alerts ?? 0)
              }
            />
            <KPIStatCard
              icon={TrendingUp}
              target={stats?.predictions_today ?? 0}
              label="Predictions Today"
              accentCls="bg-linear-to-br from-primary to-primary/80"
              barGradient="bg-linear-to-r from-primary to-primary/80"
              iconRing="ring-primary/20"
              isInView={kpiInView}
              staticValue={
                statsLoading ? "-" : String(stats?.predictions_today ?? 0)
              }
            />
            <KPIStatCard
              icon={FloodIcon}
              target={stats?.avg_risk_level ?? 0}
              label="Avg Risk Level"
              subtitle="0 = Safe, 2 = Critical"
              accentCls="bg-linear-to-br from-primary to-primary/80"
              barGradient="bg-linear-to-r from-primary to-primary/80"
              iconRing="ring-primary/20"
              decimals={2}
              isInView={kpiInView}
              staticValue={
                statsLoading
                  ? "-"
                  : stats?.avg_risk_level != null
                    ? stats.avg_risk_level.toFixed(2)
                    : "-"
              }
            />
          </motion.div>
        </div>
      </section>

      {/* ── Section 3: Operational Overview ── */}
      <section className="py-10 bg-background">
        <div className="container mx-auto px-4" ref={opsRef}>
          <SectionHeading
            label="Operational Overview"
            title="Flood Assessment & Monitoring"
            subtitle="Live prediction status, rainfall monitoring, river levels, and evacuation readiness."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={opsInView ? "show" : undefined}
            className="space-y-6"
          >
            {/* Row 1: Prediction + Rainfall */}
            <div className="grid gap-6 lg:grid-cols-12">
              <motion.div variants={fadeUp} className="lg:col-span-4">
                <EnhancedPredictionCard
                  prediction={prediction}
                  isLoading={predLoading}
                />
              </motion.div>
              <motion.div variants={fadeUp} className="lg:col-span-8">
                <RainfallMonitor />
              </motion.div>
            </div>

            {/* Row 2: River Level + Map */}
            <div className="grid gap-6 lg:grid-cols-12">
              <motion.div variants={fadeUp} className="lg:col-span-5">
                <RiverLevelMonitor />
              </motion.div>
              <motion.div variants={fadeUp} className="lg:col-span-7">
                <ErrorBoundary
                  fallback={
                    <div className="flex h-110 items-center justify-center rounded-xl border bg-muted/50 text-muted-foreground">
                      <p>Unable to load risk map. Please refresh the page.</p>
                    </div>
                  }
                >
                  <BarangayRiskMap prediction={prediction} height={440} />
                </ErrorBoundary>
              </motion.div>
            </div>

            {/* Row 3: Evacuation Status */}
            <motion.div variants={fadeUp}>
              <EvacuationStatusGrid />
            </motion.div>

            {/* Row 4: Alert Center */}
            <motion.div variants={fadeUp}>
              <AlertCenterPanel />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Section 4: Live Analytics ── */}
      <section className="py-10 bg-muted/30">
        <div className="container mx-auto px-4" ref={analyticsRef}>
          <SectionHeading
            label="Live Analytics"
            title="Rainfall, Risk & Alert Trends"
            subtitle="Visual insights into weather patterns, risk distribution and alert frequency."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={analyticsInView ? "show" : undefined}
            className="grid gap-6 md:grid-cols-3"
          >
            <motion.div variants={fadeUp}>
              <RainfallTrend />
            </motion.div>
            <motion.div variants={fadeUp}>
              <RiskDistribution />
            </motion.div>
            <motion.div variants={fadeUp}>
              <AlertFrequency />
            </motion.div>
          </motion.div>

          {/* Analytics Row 2: Historical + Trend */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={analyticsInView ? "show" : undefined}
            className="grid gap-6 md:grid-cols-2 mt-6"
          >
            <motion.div variants={fadeUp}>
              <HistoricalFloodPanel />
            </motion.div>
            <motion.div variants={fadeUp}>
              <FloodTrendPanel />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Section 5: Emergency Command & Community ── */}
      <section className="py-10 bg-background">
        <div className="container mx-auto px-4" ref={cmdRef}>
          <SectionHeading
            label="Emergency Operations"
            title="Command Board & Community Reports"
            subtitle="Real-time barangay status overview, incident timeline, evacuation capacity, and community flood reports."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={cmdInView ? "show" : undefined}
            className="space-y-6"
          >
            {/* Full-width emergency command board */}
            <motion.div variants={fadeUp}>
              <EmergencyCommandPanel />
            </motion.div>

            {/* Community Reports + Heatmap side-by-side */}
            <div className="grid gap-6 lg:grid-cols-12">
              <motion.div variants={fadeUp} className="lg:col-span-5">
                <CommunityReportsPanel />
              </motion.div>
              <motion.div variants={fadeUp} className="lg:col-span-7">
                <ErrorBoundary
                  fallback={
                    <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-lg border bg-muted/50 p-8 text-center">
                      <p className="text-sm text-muted-foreground">
                        Unable to load heatmap
                      </p>
                    </div>
                  }
                >
                  <FloodRiskHeatmap />
                </ErrorBoundary>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Section 6: Alert Channels & Preparedness ── */}
      <section className="py-10 bg-muted/30">
        <div className="container mx-auto px-4" ref={commRef}>
          <SectionHeading
            label="Communication & Preparedness"
            title="Alert Channels & Flood Safety Guide"
            subtitle="Multi-channel alert architecture, SMS delivery logs, and phase-based preparedness information."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={commInView ? "show" : undefined}
            className="grid gap-6 lg:grid-cols-2"
          >
            <motion.div variants={fadeUp}>
              <AlertChannelPanel />
            </motion.div>
            <motion.div variants={fadeUp}>
              <FloodPreparednessGuide />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Section 7: Model Intelligence ── */}
      <section className="py-10 bg-background">
        <div className="container mx-auto px-4" ref={modelRef}>
          <SectionHeading
            label="Model Intelligence"
            title="Feature Analysis & Model Health"
            subtitle="Understand which factors drive predictions and track model performance across versions."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={modelInView ? "show" : undefined}
            className="grid gap-6 lg:grid-cols-2"
          >
            <motion.div variants={fadeUp}>
              <FeatureImportanceChart />
            </motion.div>
            <motion.div variants={fadeUp}>
              <ModelSummaryCards />
            </motion.div>
            <motion.div variants={fadeUp} className="lg:col-span-2">
              <ModelConfidencePanel />
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Section 8: Decision Support ── */}
      <section className="py-10 bg-muted/30">
        <div className="container mx-auto px-4" ref={dseRef}>
          <SectionHeading
            label="Decision Support"
            title="Response Recommendations & Alerts"
            subtitle="AI-powered action recommendations, tidal conditions and SMS alert simulation."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={dseInView ? "show" : undefined}
            className="grid gap-6 lg:grid-cols-2"
          >
            <motion.div variants={fadeUp}>
              <DecisionSupportEngine
                riskLevel={(prediction?.risk_level ?? 0) as RiskLevel}
              />
            </motion.div>
            <motion.div variants={fadeUp} className="space-y-6">
              <TidalRiskIndicator />
              <SmsSimulationPanel />
            </motion.div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}

export default LGUDashboard;
