/**
 * Operator Overview Page - /operator/
 *
 * Real-time situational dashboard for MDRRMO staff.
 * Status banner, key metrics, live map, incidents, and weather.
 */

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Bell,
  Brain,
  CloudRain,
  Droplets,
  LifeBuoy,
  MapPin,
  Send,
  ShieldCheck,
  Thermometer,
  Users,
  Wind,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

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
import { BarangayRiskMap } from "@/features/dashboard";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { DecisionEngine } from "@/features/operator/components/DecisionEngine";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/types";

// ─── Risk Configuration ─────────────────────────────────────────────────────

const RISK_CFG: Record<
  RiskLevel,
  { label: string; color: string; bg: string; border: string }
> = {
  0: {
    label: "SAFE",
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
  },
  1: {
    label: "ALERT",
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
  },
  2: {
    label: "CRITICAL",
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
  },
};

// ─── Status Banner ──────────────────────────────────────────────────────────

function StatusBanner({
  riskLevel,
  confidence,
  weather,
  isLoading,
}: {
  riskLevel: RiskLevel;
  confidence: number;
  weather: {
    rainfall: number;
    temperature: number;
    humidity: number;
    wind_speed: number;
  } | null;
  isLoading: boolean;
}) {
  const navigate = useNavigate();
  const cfg = RISK_CFG[riskLevel];

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-9 w-32" />
            <Skeleton className="h-9 w-32" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("rounded-xl border-2 p-6", cfg.bg, cfg.border)}>
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className={cn("p-3 rounded-xl", cfg.bg, "ring-1", cfg.border)}>
            <ShieldCheck className={cn("h-8 w-8", cfg.color)} />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2
                className={cn("text-2xl font-bold tracking-tight", cfg.color)}
              >
                {cfg.label}
              </h2>
              <Badge
                variant="outline"
                className={cn("text-xs", cfg.color, cfg.border)}
              >
                {confidence}% confidence
              </Badge>
            </div>
            {weather && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-sm text-muted-foreground">
                <span className="flex items-center gap-1">
                  <CloudRain className="h-3.5 w-3.5" />
                  {weather.rainfall} mm/h
                </span>
                <span className="flex items-center gap-1">
                  <Thermometer className="h-3.5 w-3.5" />
                  {weather.temperature}°C
                </span>
                <span className="flex items-center gap-1">
                  <Droplets className="h-3.5 w-3.5" />
                  {weather.humidity}%
                </span>
                <span className="flex items-center gap-1">
                  <Wind className="h-3.5 w-3.5" />
                  {weather.wind_speed} m/s
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="destructive"
            className="gap-1"
            onClick={() => navigate("/operator/incidents")}
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            Raise Incident
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="gap-1 border-amber-500/30 text-amber-600 hover:bg-amber-500/10"
            onClick={() => navigate("/operator/broadcast")}
          >
            <Send className="h-3.5 w-3.5" />
            Send Broadcast
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="gap-1"
            onClick={() => navigate("/operator/evacuation")}
          >
            <LifeBuoy className="h-3.5 w-3.5" />
            Evacuation Centers
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Stat Card ──────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  description,
  urgent,
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  description?: string;
  urgent?: boolean;
  onClick?: () => void;
}) {
  return (
    <GlassCard
      className={cn(
        "cursor-pointer hover:shadow-lg transition-all duration-300",
        urgent && "ring-2 ring-red-500/30",
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              {label}
            </p>
            <p
              className={cn(
                "text-2xl font-bold",
                urgent && "text-red-600 dark:text-red-400",
              )}
            >
              {value}
            </p>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
          <div
            className={cn(
              "p-2 rounded-lg",
              urgent ? "bg-red-500/10" : "bg-primary/10",
            )}
          >
            <Icon
              className={cn(
                "h-5 w-5",
                urgent ? "text-red-500" : "text-primary",
              )}
            />
          </div>
        </div>
      </CardContent>
    </GlassCard>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function OperatorOverviewPage() {
  const navigate = useNavigate();
  const { data: prediction, isLoading } = useLivePrediction();

  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;
  const confidence = prediction?.confidence
    ? Math.round(prediction.confidence * 100)
    : 0;

  const weather = prediction?.weather_data
    ? {
        rainfall: prediction.weather_data.precipitation ?? 0,
        temperature: Math.round(
          (prediction.weather_data.temperature ?? 273) - 273.15,
        ),
        humidity: prediction.weather_data.humidity ?? 0,
        wind_speed: prediction.weather_data.wind_speed ?? 0,
      }
    : null;

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-screen-2xl mx-auto">
      {/* Status Banner */}
      <StatusBanner
        riskLevel={riskLevel}
        confidence={confidence}
        weather={weather}
        isLoading={isLoading}
      />

      {/* Key Metrics Strip */}
      <motion.div
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3"
        variants={staggerContainer}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={fadeUp}>
          <StatCard
            icon={AlertTriangle}
            label="Active Incidents"
            value={0}
            description="No active incidents"
            onClick={() => navigate("/operator/incidents")}
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <StatCard
            icon={Bell}
            label="Pending Alerts"
            value={0}
            description="All acknowledged"
            onClick={() => navigate("/operator/alerts")}
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <StatCard
            icon={LifeBuoy}
            label="Evacuation Centers"
            value="0 / 0"
            description="Open / Total"
            onClick={() => navigate("/operator/evacuation")}
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <StatCard
            icon={Users}
            label="Residents at Risk"
            value={0}
            description="High-risk barangays"
            onClick={() => navigate("/operator/residents")}
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <StatCard
            icon={MapPin}
            label="Community Reports"
            value={0}
            description="Pending review"
            onClick={() => navigate("/operator/reports")}
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <StatCard
            icon={Brain}
            label="Model Last Run"
            value={
              prediction?.timestamp
                ? new Date(prediction.timestamp).toLocaleTimeString()
                : "-"
            }
            description="RF v6"
            onClick={() => navigate("/operator/predict")}
          />
        </motion.div>
      </motion.div>

      {/* Main Content: Map + Panels */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Live Map */}
        <Card className="xl:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <MapPin className="h-4 w-4 text-primary" />
              Live Flood Risk Map
            </CardTitle>
            <CardDescription>
              Barangay boundaries color-coded by current risk level
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <BarangayRiskMap
              prediction={prediction}
              height={350}
              className="border-0 shadow-none"
            />
          </CardContent>
        </Card>

        {/* Side Panels */}
        <div className="space-y-6">
          {/* Decision Engine */}
          <DecisionEngine riskLevel={riskLevel} />

          {/* Active Incidents Panel */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  Active Incidents
                </CardTitle>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-xs"
                  onClick={() => navigate("/operator/incidents")}
                >
                  View All
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <ShieldCheck className="h-10 w-10 mb-2 text-emerald-500/50" />
                <p className="text-sm font-medium">All Clear</p>
                <p className="text-xs">No active incidents</p>
              </div>
            </CardContent>
          </Card>

          {/* Weather Panel */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <CloudRain className="h-4 w-4 text-blue-500" />
                Current Weather
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-8 w-full" />
                  ))}
                </div>
              ) : weather ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2 border-b border-border/30">
                    <span className="text-sm text-muted-foreground flex items-center gap-2">
                      <CloudRain className="h-4 w-4" /> Rainfall
                    </span>
                    <span className="text-sm font-medium">
                      {weather.rainfall} mm/h
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border/30">
                    <span className="text-sm text-muted-foreground flex items-center gap-2">
                      <Thermometer className="h-4 w-4" /> Temperature
                    </span>
                    <span className="text-sm font-medium">
                      {weather.temperature}°C
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border/30">
                    <span className="text-sm text-muted-foreground flex items-center gap-2">
                      <Droplets className="h-4 w-4" /> Humidity
                    </span>
                    <span className="text-sm font-medium">
                      {weather.humidity}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-muted-foreground flex items-center gap-2">
                      <Wind className="h-4 w-4" /> Wind
                    </span>
                    <span className="text-sm font-medium">
                      {weather.wind_speed} m/s
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Weather data unavailable
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
