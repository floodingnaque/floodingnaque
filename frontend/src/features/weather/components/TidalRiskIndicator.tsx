/**
 * TidalRiskIndicator Component (P3 - SHOULD HAVE)
 *
 * Standalone card showing current tide height, risk factor badge,
 * next high-tide time, and advisory message.  Gracefully handles
 * missing WorldTides API configuration (shows "not configured" state).
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { AlertTriangle, ArrowUp, Clock, Info, Waves } from "lucide-react";
import { memo } from "react";
import { useCurrentTide, useTidePrediction } from "../hooks/useTides";

// ---------------------------------------------------------------------------
// Risk-factor colour mapping
// ---------------------------------------------------------------------------

const RISK_COLORS: Record<string, { bg: string; text: string; label: string }> =
  {
    low: {
      bg: "bg-risk-safe text-white",
      text: "text-risk-safe",
      label: "Low",
    },
    moderate: {
      bg: "bg-risk-alert text-black",
      text: "text-risk-alert",
      label: "Moderate",
    },
    high: {
      bg: "bg-risk-critical text-white",
      text: "text-risk-critical",
      label: "High",
    },
  };

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

export function TidalRiskIndicatorSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Waves className="h-4 w-4" />
          Tidal Risk
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-10 w-28" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-3/4" />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface TidalRiskIndicatorProps {
  className?: string;
}

export const TidalRiskIndicator = memo(function TidalRiskIndicator({
  className,
}: TidalRiskIndicatorProps) {
  const {
    data: currentTide,
    isLoading: currentLoading,
    isError: currentError,
  } = useCurrentTide(true);

  const {
    data: prediction,
    isLoading: predLoading,
    isError: predError,
  } = useTidePrediction(true);

  const isLoading = currentLoading || predLoading;

  // Not configured / unreachable - show graceful fallback
  if (!isLoading && (currentError || predError)) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Waves className="h-4 w-4" />
            Tidal Risk
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-start gap-2 text-sm text-muted-foreground">
            <Info className="h-4 w-4 mt-0.5 shrink-0" />
            <p>
              Tide data unavailable. The WorldTides API may not be configured.
              Contact the system administrator.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) return <TidalRiskIndicatorSkeleton />;

  const height = currentTide?.height ?? prediction?.current_height ?? null;
  const riskFactor = prediction?.risk_factor ?? "low";
  const riskStyle = (RISK_COLORS[riskFactor] ?? RISK_COLORS.low)!;
  const message = prediction?.message;
  const nextHigh = prediction?.next_high_tide;

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Waves className="h-4 w-4" />
          Tidal Risk
          <Badge className={cn("ml-auto text-xs", riskStyle.bg)}>
            {riskStyle.label}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Current height */}
        {height != null && (
          <div className="flex items-baseline gap-2">
            <span className={cn("text-3xl font-bold", riskStyle.text)}>
              {height.toFixed(2)}
            </span>
            <span className="text-sm text-muted-foreground">m MSL</span>
          </div>
        )}

        {/* Next high tide */}
        {nextHigh && (
          <div className="flex items-center gap-2 text-sm">
            <ArrowUp className="h-4 w-4 text-muted-foreground" />
            <span>
              Next high tide:{" "}
              <strong>
                {typeof nextHigh.height === "number"
                  ? `${nextHigh.height.toFixed(2)} m`
                  : "-"}
              </strong>
            </span>
            {nextHigh.date && (
              <span className="flex items-center gap-1 text-muted-foreground ml-auto text-xs">
                <Clock className="h-3 w-3" />
                {new Date(nextHigh.date).toLocaleTimeString("en-PH", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>
        )}

        {/* Risk advisory */}
        {message && (
          <div
            className={cn(
              "flex items-start gap-2 rounded-lg px-3 py-2 text-xs",
              riskFactor === "high"
                ? "bg-risk-critical/10 text-risk-critical"
                : riskFactor === "moderate"
                  ? "bg-risk-alert/10 text-risk-alert"
                  : "bg-risk-safe/10 text-risk-safe",
            )}
          >
            <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <span>{message}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
});

export default TidalRiskIndicator;
