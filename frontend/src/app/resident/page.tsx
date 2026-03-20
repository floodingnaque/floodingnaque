/**
 * Resident — Home / Overview Page
 */

import {
  AlertTriangle,
  Bell,
  Cloud,
  Droplets,
  MapPin,
  ShieldCheck,
  Thermometer,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
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
const RISK_ICON: Record<RiskLevel, React.ElementType> = {
  0: ShieldCheck,
  1: AlertTriangle,
  2: AlertTriangle,
};

export default function ResidentOverviewPage() {
  const { data: prediction, isLoading } = useLivePrediction();

  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;
  const config = RISK_CONFIGS[riskLevel];
  const Icon = RISK_ICON[riskLevel];
  const weather = prediction?.weather_data;
  const tempC = weather?.temperature
    ? Math.round(weather.temperature - 273.15)
    : null;

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto">
      {/* Risk Banner */}
      {isLoading ? (
        <Skeleton className="h-36 w-full rounded-xl" />
      ) : (
        <div
          className={`rounded-xl border p-6 text-center ${RISK_BG[riskLevel]}`}
        >
          <Icon className={`h-10 w-10 mx-auto mb-2 ${RISK_TEXT[riskLevel]}`} />
          <p className="text-sm text-muted-foreground">
            Your area&apos;s flood risk
          </p>
          <p className={`text-4xl font-bold mt-1 ${RISK_TEXT[riskLevel]}`}>
            {config.label}
          </p>
          <p className="text-sm mt-2 text-muted-foreground">
            Confidence: {Math.round((prediction?.confidence ?? 0) * 100)}%
          </p>
        </div>
      )}

      {/* Quick Info Cards */}
      <div className="grid grid-cols-2 gap-3">
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <Thermometer className="h-5 w-5 text-orange-500 shrink-0" />
            <div>
              <p className="text-lg font-bold">
                {tempC !== null ? `${tempC}°C` : "—"}
              </p>
              <p className="text-xs text-muted-foreground">Temperature</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <Droplets className="h-5 w-5 text-blue-500 shrink-0" />
            <div>
              <p className="text-lg font-bold">
                {weather?.humidity != null ? `${weather.humidity}%` : "—"}
              </p>
              <p className="text-xs text-muted-foreground">Humidity</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <Cloud className="h-5 w-5 text-sky-500 shrink-0" />
            <div>
              <p className="text-lg font-bold">
                {weather?.precipitation != null
                  ? `${weather.precipitation} mm`
                  : "—"}
              </p>
              <p className="text-xs text-muted-foreground">Rainfall</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <MapPin className="h-5 w-5 text-primary shrink-0" />
            <div>
              <p className="text-lg font-bold">Parañaque</p>
              <p className="text-xs text-muted-foreground">Your City</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Alerts */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4 text-primary" />
            Active Alerts
          </CardTitle>
          <CardDescription>Current warnings for your area</CardDescription>
        </CardHeader>
        <CardContent>
          {prediction?.smart_alert && !prediction.smart_alert.was_suppressed ? (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <p className="text-sm font-medium text-amber-700">
                Flood alert — {prediction.smart_alert.escalation_state}
              </p>
              {prediction.smart_alert.contributing_factors.length > 0 && (
                <p className="text-xs text-amber-600 mt-1">
                  {prediction.smart_alert.contributing_factors.join(", ")}
                </p>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 py-4 text-muted-foreground">
              <ShieldCheck className="h-5 w-5 text-green-500" />
              <p className="text-sm">No active alerts — stay safe!</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3">
            {[
              {
                label: "Report Flood",
                href: "/resident/report",
                color: "text-red-600",
              },
              {
                label: "Evacuation Centers",
                href: "/resident/evacuation",
                color: "text-blue-600",
              },
              {
                label: "Emergency Contacts",
                href: "/resident/emergency",
                color: "text-amber-600",
              },
              {
                label: "Safety Guide",
                href: "/resident/guide",
                color: "text-green-600",
              },
            ].map((action) => (
              <a
                key={action.href}
                href={action.href}
                className="flex items-center gap-2 p-3 rounded-lg border border-border/50 hover:bg-accent/50 transition-colors"
              >
                <Badge variant="outline" className={action.color}>
                  {action.label}
                </Badge>
              </a>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
