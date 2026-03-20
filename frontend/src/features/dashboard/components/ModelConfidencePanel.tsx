/**
 * ModelConfidencePanel Component
 *
 * Displays ML model confidence metrics:
 * - SVG confidence arc gauge (overall accuracy)
 * - Metric arcs row (precision, recall, F1)
 * - ROC-AUC & Ensemble agreement sub-cards
 * - Cross-validation fold bar visualization
 * - Calibration curve line chart
 *
 * Data sourced from useModelMetrics() hook.
 */

import { Activity, Award, FlaskConical, Target } from "lucide-react";
import { memo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useModelMetrics } from "../hooks/useAnalytics";

// ---------------------------------------------------------------------------
// ConfArc — SVG semi-circle gauge
// ---------------------------------------------------------------------------

function ConfArc({
  value,
  label,
  size = 120,
  className,
}: {
  value: number;
  label: string;
  size?: number;
  className?: string;
}) {
  const r = (size - 16) / 2;
  const circ = Math.PI * r; // half circle
  const offset = circ * (1 - value / 100);
  const color =
    value >= 90
      ? "text-risk-safe"
      : value >= 70
        ? "text-risk-alert"
        : "text-risk-critical";

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <svg
        width={size}
        height={size / 2 + 12}
        viewBox={`0 0 ${size} ${size / 2 + 12}`}
      >
        {/* Background arc */}
        <path
          d={`M 8,${size / 2 + 4} A ${r},${r} 0 0 1 ${size - 8},${size / 2 + 4}`}
          fill="none"
          className="stroke-muted"
          strokeWidth="6"
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={`M 8,${size / 2 + 4} A ${r},${r} 0 0 1 ${size - 8},${size / 2 + 4}`}
          fill="none"
          className={cn(
            "transition-all duration-700",
            color.replace("text-", "stroke-"),
          )}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
        />
        <text
          x={size / 2}
          y={size / 2 - 2}
          textAnchor="middle"
          className="fill-foreground text-xl font-mono font-bold"
          fontSize="20"
        >
          {value.toFixed(1)}%
        </text>
      </svg>
      <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider -mt-1">
        {label}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MiniMetric — small labeled stat block
// ---------------------------------------------------------------------------

function MiniMetric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof Target;
}) {
  return (
    <div className="rounded-lg bg-muted border border-border p-2.5 flex items-center gap-2.5">
      <div className="h-7 w-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
        <Icon className="h-3.5 w-3.5 text-primary" />
      </div>
      <div className="min-w-0">
        <p className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground">
          {label}
        </p>
        <p className="text-sm font-bold font-mono">{value}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recharts tooltip style
// ---------------------------------------------------------------------------

const tooltipStyle = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: 12,
};

// ---------------------------------------------------------------------------
// ModelConfidencePanel
// ---------------------------------------------------------------------------

export const ModelConfidencePanel = memo(function ModelConfidencePanel({
  className,
}: {
  className?: string;
}) {
  const { data, isLoading } = useModelMetrics();

  if (isLoading || !data) {
    return <ModelConfidencePanelSkeleton className={className} />;
  }

  const { metrics, cvFolds, calibration, modelVersion, modelName } = data;

  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-violet-500/60 via-purple-400 to-violet-500/60" />

      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b border-border">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-violet-500/10 flex items-center justify-center ring-4 ring-violet-500/20">
            <Target className="h-4 w-4 text-violet-500" />
          </div>
          Model Confidence
        </CardTitle>
        <span className="text-[10px] font-mono text-muted-foreground">
          {modelName} · {modelVersion}
        </span>
      </CardHeader>

      <CardContent className="pt-4 space-y-5">
        {/* Gauge + metric arcs */}
        <div className="flex flex-col items-center gap-3">
          <ConfArc
            value={metrics.overall}
            label="Overall Accuracy"
            size={140}
          />
          <div className="grid grid-cols-3 gap-2 w-full">
            <MiniMetric
              icon={Target}
              label="Precision"
              value={`${metrics.precision.toFixed(1)}%`}
            />
            <MiniMetric
              icon={Activity}
              label="Recall"
              value={`${metrics.recall.toFixed(1)}%`}
            />
            <MiniMetric
              icon={Award}
              label="F1 Score"
              value={`${metrics.f1.toFixed(1)}%`}
            />
          </div>
        </div>

        {/* ROC-AUC & Ensemble */}
        <div className="grid grid-cols-2 gap-2">
          <GlassCard intensity="light" className="p-3">
            <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-1">
              ROC-AUC
            </p>
            <p className="text-lg font-bold font-mono text-risk-safe">
              {(metrics.roc_auc / 100).toFixed(3)}
            </p>
          </GlassCard>
          <GlassCard intensity="light" className="p-3">
            <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-1">
              Ensemble Agreement
            </p>
            <p className="text-lg font-bold font-mono text-risk-safe">
              {metrics.ensemble_agreement.toFixed(1)}%
            </p>
          </GlassCard>
        </div>

        {/* Cross-validation folds */}
        <div>
          <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-2">
            Cross-Validation Folds (mean: {metrics.cv_mean.toFixed(1)}% ±{" "}
            {metrics.cv_std.toFixed(2)}%)
          </p>
          <div className="flex items-end gap-1 h-12">
            {cvFolds.map((v, i) => {
              const height = Math.max((v / Math.max(...cvFolds)) * 100, 8);
              return (
                <div
                  key={i}
                  className="flex-1 rounded-t-sm bg-primary/70 hover:bg-primary transition-colors relative group"
                  style={{ height: `${height}%` }}
                >
                  <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[8px] font-mono text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                    {v.toFixed(1)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Calibration curve */}
        <div>
          <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-2">
            Calibration Curve
          </p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart
              data={calibration}
              margin={{ top: 5, right: 10, bottom: 5, left: -10 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="prob"
                tick={{ fontSize: 10 }}
                label={{ value: "Predicted", position: "bottom", fontSize: 10 }}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                label={{
                  value: "Actual",
                  angle: -90,
                  position: "insideLeft",
                  fontSize: 10,
                }}
              />
              <Tooltip contentStyle={tooltipStyle} />
              {/* Perfect calibration line */}
              <ReferenceLine
                segment={[
                  { x: 0, y: 0 },
                  { x: 1, y: 1 },
                ]}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="4 4"
                strokeOpacity={0.5}
              />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={{ r: 3 }}
                name="Model Calibration"
              />
            </LineChart>
          </ResponsiveContainer>
          <p className="text-[9px] font-mono text-center text-muted-foreground mt-1">
            <FlaskConical className="h-3 w-3 inline-block mr-1" />
            Calibration: {metrics.calibration.toFixed(1)}%
          </p>
        </div>
      </CardContent>
    </GlassCard>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function ModelConfidencePanelSkeleton({
  className,
}: {
  className?: string;
}) {
  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-muted/60 via-muted to-muted/60" />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b border-border">
        <Skeleton className="h-5 w-36" />
        <Skeleton className="h-3 w-24" />
      </CardHeader>
      <CardContent className="pt-4 space-y-5">
        <div className="flex flex-col items-center gap-3">
          <Skeleton className="h-20 w-36 rounded-lg" />
          <div className="grid grid-cols-3 gap-2 w-full">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Skeleton className="h-16 rounded-lg" />
          <Skeleton className="h-16 rounded-lg" />
        </div>
        <Skeleton className="h-12 w-full rounded-lg" />
        <Skeleton className="h-44 w-full rounded-lg" />
      </CardContent>
    </GlassCard>
  );
}

export default ModelConfidencePanel;
