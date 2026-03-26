/**
 * Resident - My Flood Risk Page
 *
 * Detailed risk breakdown with XAI factors, household risk profile,
 * and personalized recommendations.
 */

import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Brain,
  Droplets,
  Info,
  ShieldCheck,
  Siren,
  Thermometer,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";

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
import { useHouseholdProfile } from "@/features/resident";
import type { RiskLevel } from "@/types/api/prediction";

const RISK_BG: Record<RiskLevel, string> = {
  0: "bg-green-500/10 border-green-500/30",
  1: "bg-amber-500/10 border-amber-500/30",
  2: "bg-red-500/10 border-red-500/30",
};
const RISK_TEXT: Record<RiskLevel, string> = {
  0: "text-green-600 dark:text-green-400",
  1: "text-amber-600 dark:text-amber-400",
  2: "text-red-600 dark:text-red-400",
};
const RISK_LABEL: Record<RiskLevel, { en: string; fil: string }> = {
  0: { en: "SAFE", fil: "LIGTAS" },
  1: { en: "ALERT", fil: "ALERTO" },
  2: { en: "CRITICAL", fil: "KRITIKAL" },
};
const RISK_ICON: Record<RiskLevel, React.ElementType> = {
  0: ShieldCheck,
  1: AlertTriangle,
  2: Siren,
};

const RISK_ACTIONS: Record<RiskLevel, string[]> = {
  0: [
    "Continue normal activities",
    "Keep your go-bag ready and phone charged",
    "Check weather updates periodically",
  ],
  1: [
    "Prepare your emergency go-bag",
    "Charge devices and save emergency numbers",
    "Monitor weather updates frequently",
    "Know your evacuation route",
    "Alert household members - be ready to move",
  ],
  2: [
    "Evacuate immediately if instructed by MDRRMO",
    "Go to the nearest open evacuation center",
    "Bring your go-bag, documents, and medication",
    "Avoid walking through floodwater",
    "Call 911 if you are trapped",
  ],
};

export default function ResidentRiskPage() {
  const { data: prediction, isLoading } = useLivePrediction();
  const { data: household } = useHouseholdProfile();

  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;
  const Icon = RISK_ICON[riskLevel];
  const probability = prediction?.probability
    ? Math.round(prediction.probability * 100)
    : 0;
  const confidence = Math.round((prediction?.confidence ?? 0) * 100);
  const weather = prediction?.weather_data;

  const vulnerabilities: string[] = [];
  if (household) {
    if (household.is_senior_citizen || household.senior_count > 0)
      vulnerabilities.push("Senior citizen (60+)");
    if (household.children_count > 0) vulnerabilities.push("Children under 5");
    if (household.is_pwd || household.pwd_count > 0)
      vulnerabilities.push("Person with disability");
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      {/* ── Current Risk Level ─────────────────────────────────────── */}
      {isLoading ? (
        <Skeleton className="h-44 w-full rounded-2xl" />
      ) : (
        <div
          className={`rounded-2xl border-2 p-6 sm:p-8 text-center ${RISK_BG[riskLevel]}`}
          role="status"
          aria-live="polite"
        >
          <Icon className={`h-12 w-12 mx-auto mb-2 ${RISK_TEXT[riskLevel]}`} />
          <p className="text-sm text-muted-foreground">
            Current flood risk level
          </p>
          <p
            className={`text-4xl sm:text-5xl font-extrabold tracking-tight mt-1 ${RISK_TEXT[riskLevel]}`}
          >
            {RISK_LABEL[riskLevel].fil} / {RISK_LABEL[riskLevel].en}
          </p>
          <div className="flex items-center justify-center gap-4 mt-3 text-sm text-muted-foreground">
            <span>
              <span className="font-semibold">{probability}%</span> flood
              probability
            </span>
            <span className="text-border">|</span>
            <span>
              <span className="font-semibold">{confidence}%</span> model
              confidence
            </span>
          </div>
          <p className="text-xs text-muted-foreground/70 mt-2">
            Model: {prediction?.model_version ?? "-"}
            {prediction?.timestamp &&
              ` · Updated ${new Date(prediction.timestamp).toLocaleTimeString()}`}
          </p>
        </div>
      )}

      {/* ── Weather Contributing Factors ───────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-primary" />
            Current Conditions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-16" />
          ) : (
            <div className="grid grid-cols-3 gap-3">
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                <Droplets className="h-5 w-5 text-blue-500 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">
                    {weather?.precipitation != null
                      ? `${weather.precipitation} mm/h`
                      : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground">Rainfall</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                <Thermometer className="h-5 w-5 text-orange-500 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">
                    {weather?.temperature
                      ? `${Math.round(weather.temperature - 273.15)}°C`
                      : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground">Temp</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                <Droplets className="h-5 w-5 text-cyan-500 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">
                    {weather?.humidity != null ? `${weather.humidity}%` : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground">Humidity</p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── XAI Explanation ────────────────────────────────────────── */}
      {prediction?.explanation && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Brain className="h-4 w-4 text-primary" />
              Bakit Ito ang Risk Level? / Why This Risk Level?
            </CardTitle>
            <CardDescription>
              {prediction.explanation.why_alert.summary}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {prediction.explanation.why_alert.factors.map((f, i) => (
              <div
                key={i}
                className={`flex items-center gap-3 p-3 rounded-lg text-sm ${
                  f.severity === "high"
                    ? "bg-red-500/5 border border-red-500/20"
                    : f.severity === "medium"
                      ? "bg-amber-500/5 border border-amber-500/20"
                      : "bg-muted/50 border border-border/50"
                }`}
              >
                <span
                  className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                    f.severity === "high"
                      ? "bg-red-500"
                      : f.severity === "medium"
                        ? "bg-amber-500"
                        : "bg-muted-foreground"
                  }`}
                />
                <span className="flex-1">{f.text}</span>
                <Badge
                  variant="outline"
                  className={`text-[10px] uppercase ${
                    f.severity === "high"
                      ? "text-red-600 border-red-500/30"
                      : f.severity === "medium"
                        ? "text-amber-600 border-amber-500/30"
                        : ""
                  }`}
                >
                  {f.severity}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* ── Personalized Recommendations ───────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="h-4 w-4 text-primary" />
            Ano ang Dapat Gawin? / What Should You Do?
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {RISK_ACTIONS[riskLevel].map((action, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <ArrowRight className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <span>{action}</span>
            </div>
          ))}
          {riskLevel >= 1 && (
            <div className="flex gap-2 pt-3">
              <Button asChild size="sm">
                <Link to="/resident/evacuation">Find Evacuation Center</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link to="/resident/emergency">Emergency Contacts</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Household Vulnerability ────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            Household Risk Profile
          </CardTitle>
          <CardDescription>
            Vulnerabilities that affect your family&apos;s evacuation priority
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!household ? (
            <div className="flex flex-col items-center py-6 text-muted-foreground">
              <Users className="h-8 w-8 mb-2 opacity-40" />
              <p className="text-sm font-medium">No household profile yet</p>
              <p className="text-xs mt-1">
                Complete your household profile for personalized risk advice
              </p>
              <Button asChild variant="outline" size="sm" className="mt-3">
                <Link to="/resident/profile/household">Complete Profile</Link>
              </Button>
            </div>
          ) : vulnerabilities.length > 0 ? (
            <div className="space-y-2">
              {vulnerabilities.map((v) => (
                <div
                  key={v}
                  className="flex items-center gap-2 p-2 rounded-lg bg-amber-500/5 border border-amber-500/20 text-sm"
                >
                  <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                  {v}
                </div>
              ))}
              <p className="text-xs text-muted-foreground pt-1">
                Your household will be prioritized for evacuation assistance by
                MDRRMO.
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No special vulnerabilities registered. Your household follows
              standard evacuation procedures.
            </p>
          )}
        </CardContent>
      </Card>

      {/* ── Risk Level Reference ───────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Ano ang Ibig Sabihin? / What the Levels Mean
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div className="flex items-start gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
            <ShieldCheck className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-foreground">
                LIGTAS / Safe (Level 0)
              </p>
              <p>
                No flood risk detected. Normal conditions. Stay aware of weather
                changes.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-foreground">
                ALERTO / Alert (Level 1)
              </p>
              <p>
                Elevated flood risk. Monitor weather updates. Prepare to
                evacuate if conditions worsen.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/5 border border-red-500/20">
            <Siren className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-foreground">
                KRITIKAL / Critical (Level 2)
              </p>
              <p>
                Severe flood risk. Evacuate immediately if instructed. Follow
                MDRRMO guidance.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
