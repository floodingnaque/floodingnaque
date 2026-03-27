/**
 * Operator - Flood Prediction Tool Page
 */

import { Cloud, Droplets, MapPin, Thermometer, Zap } from "lucide-react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { RISK_CONFIGS, type RiskLevel } from "@/types/api/prediction";

const RISK_BG: Record<RiskLevel, string> = {
  0: "bg-green-500/10 border border-green-500/30",
  1: "bg-amber-500/10 border border-amber-500/30",
  2: "bg-red-500/10 border border-red-500/30",
};
const RISK_TEXT: Record<RiskLevel, string> = {
  0: "text-green-600 dark:text-green-400",
  1: "text-amber-600 dark:text-amber-400",
  2: "text-red-600 dark:text-red-400",
};

export default function OperatorPredictPage() {
  const { data: prediction, isLoading } = useLivePrediction();

  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;
  const riskConfig = RISK_CONFIGS[riskLevel];

  const weather = prediction?.weather_data;
  const tempC = weather?.temperature
    ? Math.round(weather.temperature - 273.15)
    : null;

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <Breadcrumb
        items={[
          { label: "Operations", href: "/operator" },
          { label: "Flood Prediction" },
        ]}
        className="mb-4"
      />

      {/* Current Prediction */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            Live Flood Prediction
          </CardTitle>
          <CardDescription>
            Real-time model inference for Parañaque City
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : prediction ? (
            <div className="space-y-6">
              {/* Risk level banner */}
              <div
                className={`p-4 rounded-lg text-center ${RISK_BG[riskLevel]}`}
              >
                <p className="text-sm text-muted-foreground">
                  Current Risk Level
                </p>
                <p
                  className={`text-3xl font-bold mt-1 ${RISK_TEXT[riskLevel]}`}
                >
                  {riskConfig.label}
                </p>
                <p className="text-sm mt-1">
                  Confidence:{" "}
                  <Badge variant="outline">
                    {Math.round((prediction.confidence ?? 0) * 100)}%
                  </Badge>
                </p>
              </div>

              {/* Weather inputs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="flex items-center gap-2 p-3 rounded-lg border border-border/50">
                  <Thermometer className="h-4 w-4 text-orange-500" />
                  <div>
                    <p className="text-xs text-muted-foreground">Temperature</p>
                    <p className="text-sm font-medium">
                      {tempC !== null ? `${tempC}°C` : "-"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-3 rounded-lg border border-border/50">
                  <Droplets className="h-4 w-4 text-blue-500" />
                  <div>
                    <p className="text-xs text-muted-foreground">Humidity</p>
                    <p className="text-sm font-medium">
                      {weather?.humidity != null ? `${weather.humidity}%` : "-"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-3 rounded-lg border border-border/50">
                  <Cloud className="h-4 w-4 text-sky-500" />
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Precipitation
                    </p>
                    <p className="text-sm font-medium">
                      {weather?.precipitation != null
                        ? `${weather.precipitation} mm`
                        : "-"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-3 rounded-lg border border-border/50">
                  <MapPin className="h-4 w-4 text-primary" />
                  <div>
                    <p className="text-xs text-muted-foreground">Location</p>
                    <p className="text-sm font-medium">Parañaque</p>
                  </div>
                </div>
              </div>

              {/* Explanation */}
              {prediction.explanation && (
                <div className="p-3 rounded-lg bg-muted/50 text-sm text-muted-foreground">
                  {prediction.explanation.why_alert.summary}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Zap className="h-10 w-10 mb-2 opacity-30" />
              <p className="text-sm">Unable to fetch prediction</p>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2"
                onClick={() => window.location.reload()}
              >
                Retry
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Smart Alert Status */}
      {prediction?.smart_alert && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Smart Alert Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-sm">
              <p className="font-medium text-amber-700">
                Escalation: {prediction.smart_alert.escalation_state}
                {prediction.smart_alert.was_suppressed && " (suppressed)"}
              </p>
              {prediction.smart_alert.contributing_factors.length > 0 && (
                <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                  Factors:{" "}
                  {prediction.smart_alert.contributing_factors.join(", ")}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
