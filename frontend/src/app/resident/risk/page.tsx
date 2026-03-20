/**
 * Resident — My Flood Risk Page
 */

import { AlertTriangle, Info, ShieldCheck } from "lucide-react";

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
  0: "bg-green-500/10 border-green-500/30",
  1: "bg-amber-500/10 border-amber-500/30",
  2: "bg-red-500/10 border-red-500/30",
};
const RISK_TEXT: Record<RiskLevel, string> = {
  0: "text-green-600",
  1: "text-amber-600",
  2: "text-red-600",
};

export default function ResidentRiskPage() {
  const { data: prediction, isLoading } = useLivePrediction();

  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;
  const config = RISK_CONFIGS[riskLevel];

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto">
      {/* Risk level card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            My Flood Risk Assessment
          </CardTitle>
          <CardDescription>
            AI-powered risk level for your location
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <div
              className={`rounded-xl border p-6 text-center ${RISK_BG[riskLevel]}`}
            >
              <p className={`text-5xl font-bold ${RISK_TEXT[riskLevel]}`}>
                {config.label}
              </p>
              <p className="text-sm mt-2 text-muted-foreground">
                Model confidence:{" "}
                {Math.round((prediction?.confidence ?? 0) * 100)}%
              </p>
              <p className="text-xs mt-1 text-muted-foreground">
                Model version: {prediction?.model_version ?? "—"}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* What this means */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="h-4 w-4 text-primary" />
            What This Means
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div className="flex items-start gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
            <ShieldCheck className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-foreground">Safe (Level 0)</p>
              <p>
                No flood risk detected. Normal conditions. Stay aware of weather
                changes.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-foreground">Alert (Level 1)</p>
              <p>
                Elevated flood risk. Monitor weather updates. Prepare to
                evacuate if conditions worsen.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/5 border border-red-500/20">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-foreground">Critical (Level 2)</p>
              <p>
                Severe flood risk. Evacuate immediately if instructed. Follow
                MDRRMO guidance.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* XAI Explanation */}
      {prediction?.explanation && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Why This Risk Level?</CardTitle>
            <CardDescription>
              Key factors contributing to the prediction
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">
              {prediction.explanation.why_alert.summary}
            </p>
            {prediction.explanation.why_alert.factors.map((f, i) => (
              <div
                key={i}
                className={`flex items-center gap-2 p-2 rounded text-sm ${
                  f.severity === "high"
                    ? "bg-red-500/5 text-red-700"
                    : f.severity === "medium"
                      ? "bg-amber-500/5 text-amber-700"
                      : "bg-muted/50 text-muted-foreground"
                }`}
              >
                <span className="h-2 w-2 rounded-full bg-current shrink-0" />
                {f.text}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
