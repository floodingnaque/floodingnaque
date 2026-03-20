/**
 * FloodStatusHero Component (P1 - MUST HAVE)
 *
 * The single most prominent element on the Resident dashboard.
 * Shows current flood risk badge, confidence gauge, rainfall,
 * tide status, and last-updated timestamp - all driven by /predict.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { PredictionResponse, RiskLevel } from "@/types";
import {
  AlertTriangle,
  Clock,
  CloudRain,
  Loader2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Waves,
} from "lucide-react";
import { memo } from "react";

// ---------------------------------------------------------------------------
// Design tokens
// ---------------------------------------------------------------------------

const RISK_THEME: Record<
  RiskLevel,
  {
    label: string;
    bg: string;
    text: string;
    border: string;
    badgeBg: string;
    icon: typeof ShieldCheck;
  }
> = {
  0: {
    label: "SAFE",
    bg: "bg-gradient-to-br from-risk-safe/10 to-risk-safe/15 dark:from-risk-safe/10 dark:to-risk-safe/5",
    text: "text-risk-safe",
    border: "border-risk-safe/30",
    badgeBg: "bg-risk-safe text-white",
    icon: ShieldCheck,
  },
  1: {
    label: "ALERT",
    bg: "bg-gradient-to-br from-risk-alert/10 to-risk-alert/15 dark:from-risk-alert/10 dark:to-risk-alert/5",
    text: "text-risk-alert",
    border: "border-risk-alert/30",
    badgeBg: "bg-risk-alert text-black",
    icon: AlertTriangle,
  },
  2: {
    label: "CRITICAL",
    bg: "bg-gradient-to-br from-risk-critical/10 to-risk-critical/15 dark:from-risk-critical/10 dark:to-risk-critical/5",
    text: "text-risk-critical",
    border: "border-risk-critical/30",
    badgeBg: "bg-risk-critical text-white",
    icon: ShieldAlert,
  },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConfidenceGauge({ value }: { value: number }) {
  const percent = Math.round(value * 100);

  // SVG speedometer - 270° arc, radius 54, centre (60,60)
  const cx = 60;
  const cy = 60;
  const radius = 54;
  const startAngle = 135; // deg - gauge starts bottom-left
  const sweep = 270; // deg - total arc
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * (sweep / 360);
  const dashOffset = arcLength - (arcLength * percent) / 100;

  // Helper: angle → SVG point on circle
  const polarToXY = (angleDeg: number, r: number) => {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  // Tick marks at 0%, 25%, 50%, 75%, 100%
  const ticks = [0, 25, 50, 75, 100].map((t) => {
    const angle = startAngle + (sweep * t) / 100;
    const outer = polarToXY(angle, radius + 4);
    const inner = polarToXY(angle, radius - 6);
    return { t, outer, inner, angle };
  });

  // Needle rotation: maps percent → angle in same coordinate space
  const needleAngle = startAngle + (sweep * percent) / 100;
  const needleTip = polarToXY(needleAngle, radius - 14);
  const needleBaseL = polarToXY(needleAngle + 90, 3);
  const needleBaseR = polarToXY(needleAngle - 90, 3);

  // Gradient zone arcs (Critical 0-50, Alert 50-75, Safe 75-100)
  const zoneArc = (fromPct: number, toPct: number) => {
    const len = arcLength * ((toPct - fromPct) / 100);
    const offset = arcLength - (arcLength * toPct) / 100;
    return { len, offset };
  };
  const zones = [
    {
      ...zoneArc(0, 50),
      color: "var(--color-risk-critical, #DC3545)",
      opacity: 0.18,
    },
    {
      ...zoneArc(50, 75),
      color: "var(--color-risk-alert, #FFC107)",
      opacity: 0.18,
    },
    {
      ...zoneArc(75, 100),
      color: "var(--color-risk-safe, #28A745)",
      opacity: 0.18,
    },
  ];

  return (
    <div className="relative inline-flex items-center justify-center w-40 h-40">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-135">
        {/* Coloured zone arcs (behind track) */}
        {zones.map((z, i) => (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke={z.color}
            strokeWidth="14"
            strokeDasharray={`${z.len} ${circumference}`}
            strokeDashoffset={z.offset}
            opacity={z.opacity}
          />
        ))}

        {/* Background track */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${circumference}`}
          className="text-muted/40"
        />

        {/* Filled arc */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={dashOffset}
          className={cn(
            "transition-all duration-700",
            percent >= 75
              ? "text-risk-safe"
              : percent >= 50
                ? "text-risk-alert"
                : "text-risk-critical",
          )}
        />

        {/* Tick marks */}
        {ticks.map((tk) => (
          <line
            key={tk.t}
            x1={tk.inner.x}
            y1={tk.inner.y}
            x2={tk.outer.x}
            y2={tk.outer.y}
            stroke="currentColor"
            strokeWidth={tk.t === 0 || tk.t === 100 ? 2 : 1.2}
            className="text-muted-foreground/60"
          />
        ))}
      </svg>

      {/* Needle (drawn un-rotated so CSS transition works) */}
      <svg viewBox="0 0 120 120" className="absolute inset-0 w-full h-full">
        <polygon
          points={`${needleTip.x},${needleTip.y} ${needleBaseL.x},${needleBaseL.y} ${needleBaseR.x},${needleBaseR.y}`}
          className={cn(
            "transition-all duration-700",
            percent >= 75
              ? "fill-risk-safe"
              : percent >= 50
                ? "fill-risk-alert"
                : "fill-risk-critical",
          )}
        />
        <circle cx={cx} cy={cy} r="4" className="fill-muted-foreground" />
      </svg>

      {/* Centre label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-4">
        <span className="text-3xl font-bold">{percent}%</span>
        <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
          Confidence
        </span>
      </div>
    </div>
  );
}

function MetricPill({
  icon: Icon,
  label,
  value,
  className,
}: {
  icon: typeof CloudRain;
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg bg-background/60",
        className,
      )}
    >
      <Icon className="h-4 w-4 text-muted-foreground" />
      <div className="flex flex-col">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
          {label}
        </span>
        <span className="text-sm font-semibold">{value}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

export function FloodStatusHeroSkeleton() {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row items-center gap-6">
          <Skeleton className="h-40 w-40 rounded-full" />
          <div className="flex-1 space-y-4 text-center sm:text-left">
            <Skeleton className="h-10 w-40 mx-auto sm:mx-0" />
            <Skeleton className="h-5 w-60 mx-auto sm:mx-0" />
            <div className="flex flex-wrap gap-3 justify-center sm:justify-start">
              <Skeleton className="h-10 w-36" />
              <Skeleton className="h-10 w-36" />
              <Skeleton className="h-10 w-36" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface FloodStatusHeroProps {
  prediction: PredictionResponse | null | undefined;
  isLoading: boolean;
  /** Current tide height in meters MSL (optional) */
  tideHeight?: number | null;
  onRefresh?: () => void;
  isFetching?: boolean;
}

export const FloodStatusHero = memo(function FloodStatusHero({
  prediction,
  isLoading,
  tideHeight,
  onRefresh,
  isFetching,
}: FloodStatusHeroProps) {
  if (isLoading) return <FloodStatusHeroSkeleton />;
  if (!prediction) return null;

  const theme = RISK_THEME[prediction.risk_level];
  const Icon = theme.icon;
  const rainfall = prediction.weather_data?.precipitation ?? 0;
  const temp = prediction.weather_data?.temperature
    ? `${Math.round(prediction.weather_data.temperature - 273.15)}°C`
    : "-";
  const humidity = prediction.weather_data?.humidity
    ? `${Math.round(prediction.weather_data.humidity)}%`
    : "-";
  const lastUpdated = new Date(prediction.timestamp).toLocaleTimeString(
    "en-PH",
    {
      hour: "2-digit",
      minute: "2-digit",
    },
  );

  return (
    <Card className={cn("overflow-hidden border-2", theme.border)}>
      <CardContent className={cn("p-6 sm:p-8", theme.bg)}>
        <div className="flex flex-col sm:flex-row items-center gap-6">
          {/* Confidence Gauge */}
          <ConfidenceGauge value={prediction.confidence} />

          {/* Main Status */}
          <div className="flex-1 text-center sm:text-left space-y-3">
            <div className="flex items-center gap-3 justify-center sm:justify-start">
              <Icon className={cn("h-8 w-8", theme.text)} />
              <Badge
                className={cn("text-lg px-4 py-1 font-bold", theme.badgeBg)}
              >
                {theme.label}
              </Badge>
            </div>

            <p className="text-sm text-muted-foreground">
              Flood probability:{" "}
              <span className={cn("font-bold text-base", theme.text)}>
                {Math.round(prediction.probability * 100)}%
              </span>
              {" · "}Model {prediction.model_version}
            </p>

            {/* Metric pills */}
            <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
              <MetricPill
                icon={CloudRain}
                label="Rainfall"
                value={`${rainfall.toFixed(1)} mm`}
              />
              <MetricPill icon={CloudRain} label="Temperature" value={temp} />
              <MetricPill icon={CloudRain} label="Humidity" value={humidity} />
              {tideHeight != null && (
                <MetricPill
                  icon={Waves}
                  label="Tide (MSL)"
                  value={`${tideHeight.toFixed(2)} m`}
                />
              )}
            </div>

            {/* Footer: timestamp + refresh */}
            <div className="flex items-center gap-3 text-xs text-muted-foreground justify-center sm:justify-start pt-1">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" /> Last updated {lastUpdated}
              </span>
              {onRefresh && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
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
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
});
