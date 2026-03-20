/**
 * StatsCards Component
 *
 * Displays dashboard statistics in a responsive grid of cards.
 * Each card shows a metric with an icon, value, and optional trend indicator.
 */

import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { Activity, AlertTriangle, Shield, TrendingUp } from "lucide-react";
import { memo } from "react";
import type { DashboardStats } from "../services/dashboardApi";

interface StatsCardsProps {
  /** Dashboard statistics data */
  stats: DashboardStats;
}

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  iconColor: string;
  bgColor: string;
  change?: {
    value: number;
    isPositive: boolean;
  };
  subtitle?: string;
}

/**
 * Individual stat card component
 */
function StatCard({
  title,
  value,
  icon,
  iconColor,
  bgColor,
  change,
  subtitle,
}: StatCardProps) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className={cn("p-2 rounded-xl ring-1 ring-border/20", bgColor)}>
          <div className={iconColor}>{icon}</div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {(change || subtitle) && (
          <div className="flex items-center mt-1">
            {change && (
              <span
                className={cn(
                  "text-xs font-medium",
                  change.isPositive ? "text-risk-safe" : "text-risk-critical",
                )}
              >
                {change.isPositive ? "+" : ""}
                {change.value}%
              </span>
            )}
            {subtitle && (
              <span className="text-xs text-muted-foreground ml-1">
                {subtitle}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </GlassCard>
  );
}

/**
 * Get risk level label and color based on numeric value
 */
function getRiskLevelInfo(level: number): {
  label: string;
  colorClass: string;
  bgClass: string;
} {
  if (level <= 25) {
    return {
      label: "Low",
      colorClass: "text-risk-safe",
      bgClass: "bg-risk-safe/15",
    };
  }
  if (level <= 50) {
    return {
      label: "Moderate",
      colorClass: "text-risk-alert",
      bgClass: "bg-risk-alert/15",
    };
  }
  if (level <= 75) {
    return {
      label: "High",
      colorClass: "text-orange-600",
      bgClass: "bg-orange-100 dark:bg-orange-900/30",
    };
  }
  return {
    label: "Critical",
    colorClass: "text-risk-critical",
    bgClass: "bg-risk-critical/15",
  };
}

/**
 * Get alert indicator color based on count
 */
function getAlertColorInfo(count: number): {
  colorClass: string;
  bgClass: string;
} {
  if (count === 0) {
    return {
      colorClass: "text-risk-safe",
      bgClass: "bg-risk-safe/15",
    };
  }
  if (count <= 3) {
    return {
      colorClass: "text-risk-alert",
      bgClass: "bg-risk-alert/15",
    };
  }
  return {
    colorClass: "text-risk-critical",
    bgClass: "bg-risk-critical/15",
  };
}

/**
 * StatsCards displays a responsive grid of dashboard statistics
 */
export const StatsCards = memo(function StatsCards({ stats }: StatsCardsProps) {
  // Guard against incomplete or undefined stats to avoid runtime errors
  const safeTotalPredictions =
    typeof stats?.total_predictions === "number" ? stats.total_predictions : 0;
  const safePredictionsToday =
    typeof stats?.predictions_today === "number" ? stats.predictions_today : 0;
  const safeActiveAlerts =
    typeof stats?.active_alerts === "number" ? stats.active_alerts : 0;
  const safeAvgRiskLevel =
    typeof stats?.avg_risk_level === "number" ? stats.avg_risk_level : 0;

  const riskInfo = getRiskLevelInfo(safeAvgRiskLevel);
  const alertInfo = getAlertColorInfo(safeActiveAlerts);

  return (
    <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Predictions"
        value={safeTotalPredictions.toLocaleString()}
        icon={<Activity className="h-4 w-4" />}
        iconColor="text-foreground"
        bgColor="bg-muted"
        subtitle="all time"
      />

      <StatCard
        title="Today's Predictions"
        value={safePredictionsToday}
        icon={<TrendingUp className="h-4 w-4" />}
        iconColor="text-foreground"
        bgColor="bg-muted"
        subtitle="since midnight"
      />

      <StatCard
        title="Active Alerts"
        value={safeActiveAlerts}
        icon={<AlertTriangle className="h-4 w-4" />}
        iconColor={alertInfo.colorClass}
        bgColor={alertInfo.bgClass}
        subtitle={safeActiveAlerts === 0 ? "All clear" : "Requires attention"}
      />

      <StatCard
        title="Avg Risk Level"
        value={`${Math.round(safeAvgRiskLevel)}%`}
        icon={<Shield className="h-4 w-4" />}
        iconColor={riskInfo.colorClass}
        bgColor={riskInfo.bgClass}
        subtitle={riskInfo.label}
      />
    </div>
  );
});

/**
 * Skeleton loading state for StatsCards
 */
export function StatsCardsSkeleton() {
  return (
    <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <GlassCard key={i} className="overflow-hidden">
          <div className="h-1 w-full bg-linear-to-r from-muted/60 via-muted to-muted/60" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-8 rounded-xl" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-8 w-20 mb-2" />
            <Skeleton className="h-3 w-32" />
          </CardContent>
        </GlassCard>
      ))}
    </div>
  );
}

export default StatsCards;
