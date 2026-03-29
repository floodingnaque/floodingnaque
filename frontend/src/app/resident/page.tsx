/**
 * Resident - Home / Overview Page
 *
 * Primary screen answering "Am I safe right now?" within 3 seconds.
 * Full-width, mobile-first, bilingual (EN/FIL), real-time via SSE.
 */

import {
  AlertTriangle,
  Bell,
  BookOpen,
  Cloud,
  Droplets,
  ExternalLink,
  LifeBuoy,
  MapPin,
  Phone,
  RefreshCw,
  ShieldCheck,
  Siren,
  Thermometer,
  Wind,
} from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { useRecentAlerts } from "@/features/alerts/hooks/useAlerts";
import { ResidentDecisionPanel } from "@/features/flooding";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { useLanguage } from "@/state";
import { useUnreadCount } from "@/state/stores/alertStore";
import type { Alert as AlertData } from "@/types";
import type { RiskLevel } from "@/types/api/prediction";

/* ── Risk theme maps ──────────────────────────────────────────────────── */

function rainfallLabel(mm: number): string {
  if (mm <= 0) return "No Rain";
  if (mm < 2.5) return "Light Rain";
  if (mm < 7.5) return "Moderate Rain";
  if (mm < 15) return "Heavy Rain";
  return "Intense Rain";
}

/* ── Quick action tile data ───────────────────────────────────────────── */

const QUICK_ACTIONS = [
  {
    label: "Report Flood",
    labelFil: "Mag-ulat ng Baha",
    href: "/resident/report",
    icon: Siren,
    color: "text-red-600 dark:text-red-400",
    bgColor: "bg-red-500/10",
  },
  {
    label: "Evacuation Centers",
    labelFil: "Evacuation Center",
    href: "/resident/evacuation",
    icon: LifeBuoy,
    color: "text-blue-600 dark:text-blue-400",
    bgColor: "bg-blue-500/10",
  },
  {
    label: "Emergency Contacts",
    labelFil: "Mga Emergency Number",
    href: "/resident/emergency",
    icon: Phone,
    color: "text-amber-600 dark:text-amber-400",
    bgColor: "bg-amber-500/10",
  },
  {
    label: "Live Map",
    labelFil: "Live na Mapa",
    href: "/resident/map",
    icon: MapPin,
    color: "text-emerald-600 dark:text-emerald-400",
    bgColor: "bg-emerald-500/10",
  },
  {
    label: "Safety Guide",
    labelFil: "Gabay sa Kaligtasan",
    href: "/resident/guide",
    icon: BookOpen,
    color: "text-purple-600 dark:text-purple-400",
    bgColor: "bg-purple-500/10",
  },
  {
    label: "Evacuation Plan",
    labelFil: "Plano sa Paglikas",
    href: "/resident/plan",
    icon: ExternalLink,
    color: "text-teal-600 dark:text-teal-400",
    bgColor: "bg-teal-500/10",
  },
] as const;

/* ── Page component ───────────────────────────────────────────────────── */

export default function ResidentOverviewPage() {
  const {
    data: prediction,
    isLoading,
    isError: predictionError,
    refetch: refetchPrediction,
  } = useLivePrediction();
  const {
    data: recentAlerts,
    dataUpdatedAt: alertsUpdatedAt,
    isError: alertsError,
    refetch: refetchAlerts,
  } = useRecentAlerts(5, {
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
  const language = useLanguage();
  const unreadCount = useUnreadCount();

  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;
  const weather = prediction?.weather_data;
  const tempC = weather?.temperature
    ? Math.round(weather.temperature - 273.15)
    : null;

  const activeAlerts = useMemo(
    () => (recentAlerts ?? []).filter((a: AlertData) => !a.acknowledged),
    [recentAlerts],
  );

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      <Breadcrumb items={[{ label: "Home" }]} className="mb-4" />

      {/* ── Error feedback ─────────────────────────────────────── */}
      {(predictionError || alertsError) && (
        <Alert variant="destructive" className="border-red-500/30 bg-red-500/5">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>
              {predictionError && alertsError
                ? "Unable to load flood risk and alerts data."
                : predictionError
                  ? "Unable to load flood risk data."
                  : "Unable to load alerts."}{" "}
              Showing cached data if available.
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 ml-2 shrink-0"
              onClick={() => {
                if (predictionError) refetchPrediction();
                if (alertsError) refetchAlerts();
              }}
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* ── Personal Risk & Decision Panel (consolidated) ──────── */}
      <ResidentDecisionPanel prediction={prediction} userLocation={null} />

      {/* ── 3b. Current Weather Snapshot ───────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))
        ) : (
          <>
            <Card>
              <CardContent className="pt-4 flex items-center gap-3">
                <Cloud className="h-6 w-6 text-sky-500 shrink-0" />
                <div>
                  <p className="text-lg font-bold">
                    {weather?.precipitation != null
                      ? `${weather.precipitation} mm/h`
                      : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {weather?.precipitation != null
                      ? rainfallLabel(weather.precipitation)
                      : "Rainfall"}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 flex items-center gap-3">
                <Thermometer className="h-6 w-6 text-orange-500 shrink-0" />
                <div>
                  <p className="text-lg font-bold">
                    {tempC !== null ? `${tempC}°C` : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground">Temperature</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 flex items-center gap-3">
                <Droplets className="h-6 w-6 text-blue-500 shrink-0" />
                <div>
                  <p className="text-lg font-bold">
                    {weather?.humidity != null ? `${weather.humidity}%` : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground">Humidity</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 flex items-center gap-3">
                <Wind className="h-6 w-6 text-slate-500 shrink-0" />
                <div>
                  <p className="text-lg font-bold">
                    {weather?.wind_speed != null
                      ? `${weather.wind_speed} m/s`
                      : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground">Wind</p>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* ── 3d. Active Alerts for My Barangay ──────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4 text-primary" />
            Active Alerts
          </CardTitle>
          <CardDescription>Current warnings for your area</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {activeAlerts.length > 0 ? (
            <>
              {activeAlerts.slice(0, 3).map((alert: AlertData) => (
                <div
                  key={alert.id}
                  className="p-3 rounded-lg border bg-amber-500/5 border-amber-500/20"
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{alert.message}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(alert.triggered_at).toLocaleString()}
                        {alert.escalation_state &&
                          ` - ${alert.escalation_state}`}
                      </p>
                    </div>
                    <Badge
                      variant={
                        alert.risk_level === 2 ? "destructive" : "secondary"
                      }
                      className="shrink-0"
                    >
                      {alert.risk_level === 2 ? "Critical" : "Alert"}
                    </Badge>
                  </div>
                </div>
              ))}
              <Button asChild variant="ghost" size="sm" className="w-full">
                <Link to="/resident/alerts">View All Alerts</Link>
              </Button>
            </>
          ) : prediction?.smart_alert &&
            !prediction.smart_alert.was_suppressed ? (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
                Flood alert - {prediction.smart_alert.escalation_state}
              </p>
              {prediction.smart_alert.contributing_factors.length > 0 && (
                <p className="text-xs text-amber-600 dark:text-amber-400/80 mt-1">
                  {prediction.smart_alert.contributing_factors.join(", ")}
                </p>
              )}
            </div>
          ) : activeAlerts.length === 0 && unreadCount === 0 ? (
            <div className="flex flex-col items-center gap-2 py-6 text-muted-foreground">
              <ShieldCheck className="h-8 w-8 text-green-500" />
              <p className="text-sm font-medium">
                {language === "fil"
                  ? "Walang aktibong alerto - No active alerts. Your area is safe."
                  : "No active alerts. Your area is safe."}
              </p>
              {alertsUpdatedAt ? (
                <p className="text-xs text-muted-foreground/60">
                  Last checked: {new Date(alertsUpdatedAt).toLocaleString()}
                </p>
              ) : null}
              <Button asChild variant="outline" size="sm" className="mt-2">
                <Link to="/resident/report">Report a Flood</Link>
              </Button>
            </div>
          ) : activeAlerts.length === 0 && unreadCount > 0 ? (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
                  {unreadCount} unread {unreadCount === 1 ? "alert" : "alerts"}{" "}
                  — check your notifications
                </p>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* ── 3e. Quick Action Tiles ─────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {QUICK_ACTIONS.map((action) => {
          const ActionIcon = action.icon;
          const isEmphasis =
            riskLevel === 2 && action.href === "/resident/evacuation";
          return (
            <Link
              key={action.href}
              to={action.href}
              className={`flex flex-col items-center gap-2 p-4 sm:p-5 rounded-xl border transition-all hover:shadow-md active:scale-[0.98] min-h-22 ${
                isEmphasis
                  ? "border-red-500/50 bg-red-500/10 ring-2 ring-red-500/30"
                  : "border-border/50 hover:bg-accent/50"
              }`}
            >
              <div className={`p-2 rounded-lg ${action.bgColor}`}>
                <ActionIcon className={`h-6 w-6 ${action.color}`} />
              </div>
              <span className="text-sm font-medium text-center leading-tight">
                {action.label}
              </span>
              {language === "fil" && (
                <span className="text-[10px] text-muted-foreground text-center leading-tight">
                  {action.labelFil}
                </span>
              )}
            </Link>
          );
        })}
      </div>

      {/* ── 3f. Weather Source Attribution ──────────────────────────── */}
      {weather?.source && (
        <p className="text-[11px] text-muted-foreground text-center">
          Weather data: {weather.source}
          {weather.simulated && " (simulated)"}
        </p>
      )}
    </div>
  );
}
