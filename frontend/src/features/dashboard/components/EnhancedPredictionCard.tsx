/**
 * EnhancedPredictionCard - AI Flood Prediction Display
 *
 * Shows risk level, probability donut, confidence/horizon/updated pills,
 * feature contribution bars, and data source tags.
 */

import { Badge } from "@/components/ui/badge";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { RiskStatusBadge } from "@/components/ui/risk-status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { PredictionResponse, RiskLabel } from "@/types";
import { Brain, Clock, Database, ShieldCheck } from "lucide-react";
import { memo, useMemo } from "react";
import { useModelFeatureImportance } from "../hooks/useAnalytics";
import type { FeatureContribution } from "../types";

// ─── Probability Donut (SVG) ────────────────────────────────────────────────

function ProbabilityDonut({
  probability,
  riskLabel,
}: {
  probability: number;
  riskLabel: RiskLabel;
}) {
  const pct = Math.round(probability * 100);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - probability);

  const strokeColor =
    riskLabel === "Critical"
      ? "hsl(var(--risk-critical))"
      : riskLabel === "Alert"
        ? "hsl(var(--risk-alert))"
        : "hsl(var(--risk-safe))";

  return (
    <div className="relative flex items-center justify-center">
      <svg width={100} height={100} viewBox="0 0 100 100">
        <circle
          cx={50}
          cy={50}
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={8}
        />
        <circle
          cx={50}
          cy={50}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={8}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          className="transition-all duration-700 ease-out"
        />
        <text
          x={50}
          y={46}
          textAnchor="middle"
          className="fill-foreground font-bold"
          style={{ fontSize: 20 }}
        >
          {pct}%
        </text>
        <text
          x={50}
          y={62}
          textAnchor="middle"
          className="fill-muted-foreground"
          style={{ fontSize: 10 }}
        >
          probability
        </text>
      </svg>
    </div>
  );
}

// ─── Feature Bar ────────────────────────────────────────────────────────────

function FeatureBar({ name, label, percentage }: FeatureContribution) {
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs">
        <span
          className="text-muted-foreground truncate max-w-[70%]"
          title={name}
        >
          {label}
        </span>
        <span className="font-mono font-semibold text-foreground">
          {percentage.toFixed(1)}%
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500"
          style={{ width: `${Math.min(100, percentage)}%` }}
        />
      </div>
    </div>
  );
}

// ─── Info Pill ──────────────────────────────────────────────────────────────

function InfoPill({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-1.5 rounded-md bg-muted/50 px-2.5 py-1.5 text-xs">
      <Icon className="h-3 w-3 text-muted-foreground" />
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-semibold text-foreground">{value}</span>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export const EnhancedPredictionCard = memo(function EnhancedPredictionCard({
  prediction,
  isLoading,
  className,
}: {
  prediction?: PredictionResponse | null;
  isLoading?: boolean;
  className?: string;
}) {
  const { data: fiData } = useModelFeatureImportance();
  const featureImportances = useMemo(
    () => fiData?.features ?? [],
    [fiData?.features],
  );

  const contributions = useMemo<FeatureContribution[]>(() => {
    if (!prediction) return [];

    // Use XAI explanation if available, otherwise fall back to global feature importances
    if (prediction.explanation?.prediction_contributions?.length) {
      const total = prediction.explanation.prediction_contributions.reduce(
        (s, c) => s + c.abs_contribution,
        0,
      );
      return prediction.explanation.prediction_contributions
        .slice(0, 6)
        .map((c) => ({
          name: c.feature,
          label: c.label,
          percentage: total > 0 ? (c.abs_contribution / total) * 100 : 0,
        }));
    }

    // Fallback: real feature importances from model
    if (!featureImportances.length) return [];
    const top = featureImportances.slice(0, 6);
    const total = top.reduce(
      (s: number, f: { importance: number }) => s + f.importance,
      0,
    );
    return top.map((f: { feature: string; importance: number }) => ({
      name: f.feature,
      label: f.feature.replace(/_/g, " "),
      percentage: total > 0 ? (f.importance / total) * 100 : 0,
    }));
  }, [prediction, featureImportances]);

  if (isLoading || !prediction)
    return <EnhancedPredictionCardSkeleton className={className} />;

  const riskLabel = prediction.risk_label;
  const updatedAt = new Date(prediction.timestamp).toLocaleTimeString("en-PH", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const sources: string[] = [];
  if (prediction.weather_data?.source)
    sources.push(prediction.weather_data.source);
  if (prediction.model_version)
    sources.push(`Model ${prediction.model_version}`);

  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div
        className={cn(
          "h-1 w-full",
          riskLabel === "Critical"
            ? "bg-risk-critical"
            : riskLabel === "Alert"
              ? "bg-risk-alert"
              : "bg-risk-safe",
        )}
      />
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Brain className="h-4 w-4 text-primary" />
          AI Prediction
          <RiskStatusBadge risk={riskLabel} className="ml-auto" />
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Probability donut + Info pills */}
        <div className="flex items-center gap-4">
          <ProbabilityDonut
            probability={prediction.probability}
            riskLabel={riskLabel}
          />
          <div className="flex-1 space-y-2">
            <InfoPill
              icon={ShieldCheck}
              label="Confidence"
              value={`${Math.round(prediction.confidence * 100)}%`}
            />
            <InfoPill icon={Clock} label="Updated" value={updatedAt} />
            <InfoPill
              icon={Database}
              label="Model"
              value={prediction.model_version}
            />
          </div>
        </div>

        {/* Feature contributions */}
        <div>
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium mb-2">
            Top Contributing Factors
          </p>
          <div className="space-y-2">
            {contributions.map((c) => (
              <FeatureBar key={c.name} {...c} />
            ))}
          </div>
        </div>

        {/* Data sources */}
        {sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {sources.map((src) => (
              <Badge key={src} variant="secondary" className="text-[10px]">
                {src}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </GlassCard>
  );
});

// ─── Skeleton ───────────────────────────────────────────────────────────────

export function EnhancedPredictionCardSkeleton({
  className,
}: {
  className?: string;
}) {
  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-muted" />
      <CardHeader className="pb-2">
        <Skeleton className="h-5 w-36" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <Skeleton className="h-25 w-25 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-7 w-full rounded-md" />
            <Skeleton className="h-7 w-full rounded-md" />
            <Skeleton className="h-7 w-full rounded-md" />
          </div>
        </div>
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-full" />
          ))}
        </div>
      </CardContent>
    </GlassCard>
  );
}
