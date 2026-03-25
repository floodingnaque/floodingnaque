/**
 * BarangayCard
 *
 * Compact card showing a single barangay's live risk level,
 * probability bar, weather snapshot, zone badge, and action buttons.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { BarangayData } from "@/config/paranaque";
import { cn } from "@/lib/utils";
import type { PredictionResponse, RiskLevel } from "@/types";
import { CloudRain, Droplets, Info, MapPin, Thermometer } from "lucide-react";

// ---------------------------------------------------------------------------
// Risk display config
// ---------------------------------------------------------------------------

const RISK_META: Record<
  RiskLevel,
  { label: string; color: string; border: string; bg: string }
> = {
  0: {
    label: "Safe",
    color: "text-risk-safe",
    border: "border-risk-safe/40",
    bg: "bg-risk-safe/5",
  },
  1: {
    label: "Alert",
    color: "text-risk-alert",
    border: "border-risk-alert/40",
    bg: "bg-risk-alert/5",
  },
  2: {
    label: "Critical",
    color: "text-risk-critical",
    border: "border-risk-critical/40",
    bg: "bg-risk-critical/5",
  },
};

const STATIC_RISK_MAP: Record<BarangayData["floodRisk"], RiskLevel> = {
  low: 0,
  moderate: 1,
  high: 2,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface BarangayCardProps {
  barangay: BarangayData;
  prediction?: PredictionResponse;
  isLoading: boolean;
  onViewDetails: (barangay: BarangayData) => void;
}

export function BarangayCard({
  barangay,
  prediction,
  isLoading,
  onViewDetails,
}: BarangayCardProps) {
  if (isLoading) {
    return (
      <Card className="p-4">
        <Skeleton className="h-5 w-32 mb-3" />
        <Skeleton className="h-3 w-full mb-2" />
        <Skeleton className="h-3 w-2/3 mb-2" />
        <Skeleton className="h-8 w-full mt-3" />
      </Card>
    );
  }

  const riskLevel =
    prediction?.risk_level ?? STATIC_RISK_MAP[barangay.floodRisk];
  const meta = RISK_META[riskLevel];
  const probability = prediction?.probability ?? 0;
  const weather = prediction?.weather_data;

  return (
    <Card
      className={cn("transition-shadow hover:shadow-md", meta.border, meta.bg)}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-foreground text-sm truncate">
              {barangay.name}
            </h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 h-5 font-normal"
              >
                {barangay.zone}
              </Badge>
              <span className="text-[10px] text-muted-foreground">
                {barangay.population.toLocaleString()} pop.
              </span>
            </div>
          </div>
          <Badge
            className={cn("shrink-0 text-xs", meta.color, meta.bg, meta.border)}
          >
            {meta.label}
          </Badge>
        </div>

        {/* Probability bar */}
        <div>
          <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
            <span>Flood Probability</span>
            <span className="font-medium tabular-nums">
              {(probability * 100).toFixed(0)}%
            </span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                riskLevel === 0
                  ? "bg-risk-safe"
                  : riskLevel === 1
                    ? "bg-risk-alert"
                    : "bg-risk-critical",
              )}
              style={{ width: `${Math.min(probability * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Weather snapshot */}
        {weather && (
          <div className="grid grid-cols-3 gap-2 text-[10px] text-muted-foreground">
            <div className="flex items-center gap-1">
              <CloudRain className="h-3 w-3" />
              <span className="tabular-nums">
                {weather.precipitation.toFixed(1)} mm
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Thermometer className="h-3 w-3" />
              <span className="tabular-nums">
                {(weather.temperature - 273.15).toFixed(0)}°C
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Droplets className="h-3 w-3" />
              <span className="tabular-nums">{weather.humidity}%</span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 h-7 text-xs"
            onClick={() => onViewDetails(barangay)}
          >
            <Info className="h-3 w-3 mr-1" />
            Details
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs px-2"
            onClick={() =>
              document
                .getElementById("barangay-map")
                ?.scrollIntoView({ behavior: "smooth" })
            }
          >
            <MapPin className="h-3 w-3" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
