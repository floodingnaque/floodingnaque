/**
 * PredictionResult Component
 *
 * Displays the complete prediction result including risk level,
 * model details, and action buttons.
 *
 * Web 3.0 design — glassmorphism cards, gradient accent bars,
 * icon boxes, and risk-level colour theming.
 */

import {
  AlertTriangle,
  Clock,
  Cpu,
  Hash,
  History,
  Info,
  Layers,
  RefreshCw,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { Separator } from "@/components/ui/separator";

import type { PredictionResponse, RiskLevel } from "@/types";
import { ExplainabilityPanel } from "./ExplainabilityPanel";
import { RiskDisplay } from "./RiskDisplay";

// ---------------------------------------------------------------------------
// Risk-level gradient palettes (Tailwind v4 — bg-linear-to-*)
// ---------------------------------------------------------------------------

const GRADIENT_ACCENT: Record<RiskLevel, string> = {
  0: "bg-linear-to-r from-emerald-500 to-teal-400",
  1: "bg-linear-to-r from-amber-500 to-orange-400",
  2: "bg-linear-to-r from-red-500 to-rose-400",
};

const ICON_BOX: Record<RiskLevel, string> = {
  0: "bg-linear-to-br from-emerald-500/20 to-teal-500/20 ring-risk-safe/30 text-risk-safe",
  1: "bg-linear-to-br from-amber-500/20 to-orange-500/20 ring-risk-alert/30 text-risk-alert",
  2: "bg-linear-to-br from-red-500/20 to-rose-500/20 ring-risk-critical/30 text-risk-critical",
};

const STAT_BG: Record<RiskLevel, string> = {
  0: "bg-linear-to-br from-emerald-500/10 to-teal-500/10 ring-1 ring-risk-safe/20",
  1: "bg-linear-to-br from-amber-500/10 to-orange-500/10 ring-1 ring-risk-alert/20",
  2: "bg-linear-to-br from-red-500/10 to-rose-500/10 ring-1 ring-risk-critical/20",
};

const BADGE_VARIANT: Record<RiskLevel, string> = {
  0: "border-risk-safe/30 bg-risk-safe/10 text-risk-safe",
  1: "border-risk-alert/30 bg-risk-alert/10 text-risk-alert",
  2: "border-risk-critical/30 bg-risk-critical/10 text-risk-critical",
};

// ---------------------------------------------------------------------------
// Props & helpers
// ---------------------------------------------------------------------------

interface PredictionResultProps {
  /** Prediction response data */
  result: PredictionResponse;
  /** Callback to reset and make another prediction */
  onReset?: () => void;
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PredictionResult({ result, onReset }: PredictionResultProps) {
  const risk = result.risk_level;

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Risk Display — prominent hero */}
      <RiskDisplay
        riskLevel={risk}
        probability={result.probability}
        confidence={result.confidence}
      />

      {/* Dev-mode simulated weather notice */}
      {result.weather_data?.simulated && (
        <Alert className="border-risk-alert/30 bg-risk-alert/10">
          <AlertTriangle className="h-4 w-4 text-risk-alert" />
          <AlertDescription className="text-sm">
            <span className="font-medium">Development mode:</span> Weather data
            was simulated because <code className="text-xs">OWM_API_KEY</code>{" "}
            is not configured. Results are for testing only.
          </AlertDescription>
        </Alert>
      )}

      {/* Defaulted features warning — shown when model ran with incomplete data */}
      {result.feature_completeness &&
        result.feature_completeness.confidence_impact !== "none" && (
          <Alert
            className={
              result.feature_completeness.confidence_impact === "high"
                ? "border-risk-critical/30 bg-risk-critical/10"
                : "border-risk-alert/30 bg-risk-alert/10"
            }
          >
            <AlertTriangle
              className={`h-4 w-4 ${
                result.feature_completeness.confidence_impact === "high"
                  ? "text-risk-critical"
                  : "text-risk-alert"
              }`}
            />
            <AlertDescription className="text-sm">
              <span className="font-medium">Reduced confidence:</span> This
              prediction used {result.feature_completeness.features_available}/
              {result.feature_completeness.features_total} features.{" "}
              {result.feature_completeness.features_defaulted.length > 0 && (
                <>
                  Missing:{" "}
                  {result.feature_completeness.features_defaulted.join(", ")}.
                </>
              )}
            </AlertDescription>
          </Alert>
        )}

      {/* ── Explainability — XAI ── */}
      <ExplainabilityPanel
        explanation={result.explanation}
        riskLevel={risk}
        smartAlertFactors={result.smart_alert?.contributing_factors}
      />

      {/* ── Details Card ── */}
      <GlassCard intensity="heavy" className="relative overflow-hidden">
        {/* Gradient accent bar */}
        <div
          className={`absolute inset-x-0 top-0 h-1 ${GRADIENT_ACCENT[risk]}`}
        />

        <div className="p-6 space-y-5">
          {/* Header with icon box */}
          <div className="flex items-start gap-4">
            <div
              className={`shrink-0 flex items-center justify-center h-11 w-11 rounded-xl ring-1 ${ICON_BOX[risk]}`}
            >
              <Info className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold tracking-tight">
                Prediction Details
              </h3>
              <p className="text-sm text-muted-foreground">
                Technical information about this prediction
              </p>
            </div>
          </div>

          <Separator className="opacity-40" />

          {/* Model Version & Timestamp */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Model Version
              </p>
              <p className="font-mono text-sm">{result.model_version}</p>
            </div>
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Timestamp
              </p>
              <p className="text-sm">{formatTimestamp(result.timestamp)}</p>
            </div>
          </div>

          <Separator className="opacity-40" />

          {/* Features Used */}
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Features Used
            </p>
            <div className="flex flex-wrap gap-2">
              {result.features_used.map((feature) => (
                <Badge
                  key={feature}
                  variant="outline"
                  className={BADGE_VARIANT[risk]}
                >
                  {feature}
                </Badge>
              ))}
            </div>
          </div>

          <Separator className="opacity-40" />

          {/* Request ID */}
          <div className="space-y-1">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-1">
              <Hash className="h-3 w-3" />
              Request ID
            </p>
            <p className="font-mono text-xs text-muted-foreground/80">
              {result.request_id}
            </p>
          </div>

          {/* Stat tiles */}
          <div className="grid grid-cols-2 gap-4 pt-1">
            <div
              className={`relative overflow-hidden text-center p-4 rounded-xl ${STAT_BG[risk]}`}
            >
              <Cpu className="absolute -right-2 -top-2 h-14 w-14 opacity-[0.06]" />
              <p className="text-2xl font-bold tracking-tight">
                {Math.round(result.confidence * 100)}%
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">Confidence</p>
            </div>
            <div
              className={`relative overflow-hidden text-center p-4 rounded-xl ${STAT_BG[risk]}`}
            >
              <Layers className="absolute -right-2 -top-2 h-14 w-14 opacity-[0.06]" />
              <p className="text-2xl font-bold tracking-tight">
                {result.prediction === 1 ? "Flood" : "No Flood"}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Raw Prediction ({result.prediction})
              </p>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* ── Action Buttons ── */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          onClick={onReset}
          variant="default"
          size="lg"
          className="flex-1"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Make Another Prediction
        </Button>
        <Button asChild variant="outline" size="lg" className="flex-1">
          <Link to="/history?tab=predictions">
            <History className="mr-2 h-4 w-4" />
            View History
          </Link>
        </Button>
      </div>
    </div>
  );
}

export default PredictionResult;
