/**
 * CityWideSummary
 *
 * Six stat cards in a row: Safe / Alert / Critical barangay counts
 * (each listing the barangay names) and Avg Rainfall / Temperature / Humidity
 * computed from prediction weather data.
 */

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BARANGAYS, type BarangayData } from "@/config/paranaque";
import { cn } from "@/lib/utils";
import type { PredictionResponse, RiskLevel } from "@/types";
import {
  AlertTriangle,
  CloudRain,
  Droplets,
  ShieldCheck,
  Thermometer,
  XCircle,
} from "lucide-react";
import { useMemo } from "react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATIC_RISK_MAP: Record<BarangayData["floodRisk"], RiskLevel> = {
  low: 0,
  moderate: 1,
  high: 2,
};

interface SummaryData {
  safe: string[];
  alert: string[];
  critical: string[];
  avgRainfall: number | null;
  avgTemp: number | null;
  avgHumidity: number | null;
}

function computeSummary(
  predictions?: Record<string, PredictionResponse>,
): SummaryData {
  const safe: string[] = [];
  const alert: string[] = [];
  const critical: string[] = [];
  let rainSum = 0;
  let tempSum = 0;
  let humSum = 0;
  let weatherCount = 0;

  for (const b of BARANGAYS) {
    const pred = predictions?.[b.key];
    const level = pred?.risk_level ?? STATIC_RISK_MAP[b.floodRisk];
    if (level === 0) safe.push(b.name);
    else if (level === 1) alert.push(b.name);
    else critical.push(b.name);

    if (pred?.weather_data) {
      rainSum += pred.weather_data.precipitation;
      tempSum += pred.weather_data.temperature - 273.15;
      humSum += pred.weather_data.humidity;
      weatherCount++;
    }
  }

  return {
    safe,
    alert,
    critical,
    avgRainfall: weatherCount ? rainSum / weatherCount : null,
    avgTemp: weatherCount ? tempSum / weatherCount : null,
    avgHumidity: weatherCount ? humSum / weatherCount : null,
  };
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  className?: string;
}

function StatCard({ icon, label, value, sub, className }: StatCardProps) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardContent className="p-4 flex items-start gap-3">
        <div className="mt-0.5">{icon}</div>
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-bold tabular-nums leading-tight">
            {value}
          </p>
          {sub && (
            <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
              {sub}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface CityWideSummaryProps {
  predictions?: Record<string, PredictionResponse>;
  isLoading: boolean;
}

export function CityWideSummary({
  predictions,
  isLoading,
}: CityWideSummaryProps) {
  const summary = useMemo(() => computeSummary(predictions), [predictions]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="p-4">
            <Skeleton className="h-4 w-16 mb-2" />
            <Skeleton className="h-7 w-10" />
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
      <StatCard
        icon={<ShieldCheck className="h-5 w-5 text-risk-safe" />}
        label="Safe"
        value={String(summary.safe.length)}
        sub={summary.safe.slice(0, 3).join(", ") || "-"}
        className="border-risk-safe/20"
      />
      <StatCard
        icon={<AlertTriangle className="h-5 w-5 text-risk-alert" />}
        label="Alert"
        value={String(summary.alert.length)}
        sub={summary.alert.slice(0, 3).join(", ") || "-"}
        className="border-risk-alert/20"
      />
      <StatCard
        icon={<XCircle className="h-5 w-5 text-risk-critical" />}
        label="Critical"
        value={String(summary.critical.length)}
        sub={summary.critical.slice(0, 3).join(", ") || "-"}
        className="border-risk-critical/20"
      />
      <StatCard
        icon={<CloudRain className="h-5 w-5 text-blue-500" />}
        label="Avg Rainfall"
        value={
          summary.avgRainfall !== null
            ? `${summary.avgRainfall.toFixed(1)} mm`
            : "-"
        }
      />
      <StatCard
        icon={<Thermometer className="h-5 w-5 text-orange-500" />}
        label="Avg Temp"
        value={
          summary.avgTemp !== null ? `${summary.avgTemp.toFixed(1)}°C` : "-"
        }
      />
      <StatCard
        icon={<Droplets className="h-5 w-5 text-cyan-500" />}
        label="Avg Humidity"
        value={
          summary.avgHumidity !== null
            ? `${summary.avgHumidity.toFixed(0)}%`
            : "-"
        }
      />
    </div>
  );
}
