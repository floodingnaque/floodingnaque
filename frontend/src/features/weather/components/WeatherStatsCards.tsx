/**
 * WeatherStatsCards Component
 *
 * Displays aggregated weather statistics in a responsive grid of metric cards.
 * Shows temperature, humidity, precipitation, wind speed, and record count.
 * Flags records excluded for being outside realistic Parañaque thresholds.
 * Web 3.0 glassmorphism design with gradient accent bars and icon boxes.
 */

import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTemperature } from "@/features/flooding/utils/temperature";
import type { WeatherStats } from "@/types";
import {
  AlertTriangle,
  CloudRain,
  Database,
  Droplets,
  Thermometer,
  Wind,
} from "lucide-react";

interface WeatherStatsCardsProps {
  /** Weather statistics data */
  stats?: WeatherStats;
  /** Loading state */
  isLoading?: boolean;
}

/**
 * Individual stat card configuration
 */
interface StatCardConfig {
  title: string;
  icon: React.ElementType;
  getValue: (stats: WeatherStats) => string;
  /** Gradient class for the top accent bar */
  accentGradient: string;
  /** Gradient class for the icon box background */
  iconBoxGradient: string;
  /** Ring color class for the icon box */
  iconBoxRing: string;
  /** Icon color inside the box */
  iconColor: string;
}

/**
 * Configuration for all stat cards
 */
const statCards: StatCardConfig[] = [
  {
    title: "Avg Temperature",
    icon: Thermometer,
    getValue: (stats) => formatTemperature(stats.avg_temperature, "C"),
    accentGradient: "bg-linear-to-r from-primary to-primary/80",
    iconBoxGradient: "bg-primary/10",
    iconBoxRing: "ring-primary/20",
    iconColor: "text-primary",
  },
  {
    title: "Avg Humidity",
    icon: Droplets,
    getValue: (stats) => `${(stats.avg_humidity ?? 0).toFixed(1)}%`,
    accentGradient: "bg-linear-to-r from-primary to-primary/80",
    iconBoxGradient: "bg-primary/10",
    iconBoxRing: "ring-primary/20",
    iconColor: "text-primary",
  },
  {
    title: "Total Precipitation",
    icon: CloudRain,
    getValue: (stats) => `${(stats.total_precipitation ?? 0).toFixed(2)} mm`,
    accentGradient: "bg-linear-to-r from-primary to-primary/80",
    iconBoxGradient: "bg-primary/10",
    iconBoxRing: "ring-primary/20",
    iconColor: "text-primary",
  },
  {
    title: "Avg Wind Speed",
    icon: Wind,
    getValue: (stats) => `${(stats.avg_wind_speed ?? 0).toFixed(1)} m/s`,
    accentGradient: "bg-linear-to-r from-primary to-primary/80",
    iconBoxGradient: "bg-primary/10",
    iconBoxRing: "ring-primary/20",
    iconColor: "text-primary",
  },
  {
    title: "Record Count",
    icon: Database,
    getValue: (stats) => (stats.record_count ?? 0).toLocaleString(),
    accentGradient: "bg-linear-to-r from-primary to-primary/80",
    iconBoxGradient: "bg-primary/10",
    iconBoxRing: "ring-primary/20",
    iconColor: "text-primary",
  },
];

/**
 * Skeleton loading card component with glassmorphism styling
 */
function StatCardSkeleton() {
  return (
    <GlassCard className="overflow-hidden">
      <div className="h-1 w-full bg-muted/40" />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-9 w-9 rounded-xl" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-20" />
      </CardContent>
    </GlassCard>
  );
}

/**
 * WeatherStatsCards component
 *
 * @example
 * <WeatherStatsCards stats={weatherStats} isLoading={isLoadingStats} />
 */
export function WeatherStatsCards({
  stats,
  isLoading,
}: WeatherStatsCardsProps) {
  // Show skeleton cards while loading
  if (isLoading) {
    return (
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
        {statCards.map((_, index) => (
          <StatCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  // Show placeholder when no stats available
  if (!stats) {
    return (
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
        {statCards.map((config, index) => {
          const Icon = config.icon;
          return (
            <GlassCard key={index} className="overflow-hidden">
              {/* Gradient accent bar */}
              <div
                className={`h-1 w-full ${config.accentGradient} opacity-60`}
              />
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {config.title}
                </CardTitle>
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-xl ${config.iconBoxGradient} ring-1 ${config.iconBoxRing}`}
                >
                  <Icon className={`h-4 w-4 ${config.iconColor} opacity-60`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-muted-foreground">
                  --
                </div>
              </CardContent>
            </GlassCard>
          );
        })}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
        {statCards.map((config, index) => {
          const Icon = config.icon;
          return (
            <GlassCard
              key={index}
              className="overflow-hidden transition-shadow hover:shadow-lg hover:shadow-black/5"
            >
              {/* Gradient accent bar */}
              <div className={`h-1 w-full ${config.accentGradient}`} />
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {config.title}
                </CardTitle>
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-xl ${config.iconBoxGradient} ring-1 ${config.iconBoxRing}`}
                >
                  <Icon className={`h-4 w-4 ${config.iconColor}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {config.getValue(stats)}
                </div>
              </CardContent>
            </GlassCard>
          );
        })}
      </div>
      {(stats.flagged_count ?? 0) > 0 && (
        <div className="flex items-center gap-2 rounded-lg bg-risk-alert/10 px-3 py-2 text-xs text-risk-alert">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          {stats.flagged_count} record{stats.flagged_count! > 1 ? "s" : ""}{" "}
          excluded from stats — values outside realistic Parañaque thresholds
          (20–45 °C, 0–100% RH, ≥0 mm).
        </div>
      )}
    </div>
  );
}

export default WeatherStatsCards;
