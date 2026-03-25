/**
 * Resident — Active Alerts Page
 *
 * Full alert feed with filters, mark-as-read, and bilingual support.
 */

import {
  AlertTriangle,
  Bell,
  BellOff,
  CheckCheck,
  ShieldCheck,
  Siren,
} from "lucide-react";
import { useMemo, useState } from "react";

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
import {
  useAcknowledgeAlert,
  useAcknowledgeAll,
  useAlerts,
} from "@/features/alerts/hooks/useAlerts";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import type { Alert } from "@/types";

type FilterTab = "active" | "all";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const LEVEL_STYLE: Record<
  number,
  { bg: string; icon: React.ElementType; label: string }
> = {
  0: {
    bg: "bg-green-500/5 border-green-500/20",
    icon: ShieldCheck,
    label: "Info",
  },
  1: {
    bg: "bg-amber-500/5 border-amber-500/20",
    icon: AlertTriangle,
    label: "Alert",
  },
  2: { bg: "bg-red-500/5 border-red-500/20", icon: Siren, label: "Critical" },
};

export default function ResidentAlertsPage() {
  const { data: alerts, isLoading } = useAlerts();
  const { data: prediction } = useLivePrediction();
  const ackMutation = useAcknowledgeAlert();
  const ackAllMutation = useAcknowledgeAll();
  const [filter, setFilter] = useState<FilterTab>("active");

  const smartAlert = prediction?.smart_alert;

  const alertList = useMemo(() => alerts?.data ?? [], [alerts]);

  const filtered = useMemo(() => {
    if (filter === "active")
      return alertList.filter((a: Alert) => !a.acknowledged);
    return alertList;
  }, [alertList, filter]);

  const unreadCount = useMemo(
    () => alertList.filter((a: Alert) => !a.acknowledged).length,
    [alertList],
  );

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      {/* ── Header + Actions ──────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Bell className="h-5 w-5 text-primary" />
            Mga Alerto / Alerts
          </h2>
          <p className="text-sm text-muted-foreground">
            Real-time flood warnings for Parañaque City
          </p>
        </div>
        {unreadCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="gap-2 self-start"
            onClick={() => ackAllMutation.mutate()}
            disabled={ackAllMutation.isPending}
          >
            <CheckCheck className="h-4 w-4" />
            Mark All as Read ({unreadCount})
          </Button>
        )}
      </div>

      {/* ── Filter Tabs ───────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <Button
          variant={filter === "active" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("active")}
        >
          Active
          {unreadCount > 0 && (
            <Badge variant="destructive" className="ml-1.5 h-5 min-w-5 px-1.5">
              {unreadCount}
            </Badge>
          )}
        </Button>
        <Button
          variant={filter === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("all")}
        >
          All History
        </Button>
      </div>

      {/* ── Smart Alert Banner ────────────────────────────────────── */}
      {smartAlert && !smartAlert.was_suppressed && (
        <div className="p-4 rounded-xl bg-amber-500/10 border-2 border-amber-500/30">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
                System Alert — {smartAlert.escalation_state}
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-400/80 mt-0.5">
                3-hour rainfall: {smartAlert.rainfall_3h} mm
              </p>
              {smartAlert.contributing_factors.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {smartAlert.contributing_factors.map((f, i) => (
                    <Badge
                      key={i}
                      variant="outline"
                      className="text-xs border-amber-500/30 text-amber-700 dark:text-amber-400"
                    >
                      {f}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Alert List ────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((alert: Alert) => {
            const style = (LEVEL_STYLE[alert.risk_level] ?? LEVEL_STYLE[1])!;
            const LevelIcon = style.icon;
            return (
              <div
                key={alert.id}
                className={`p-4 rounded-xl border transition-colors ${style.bg} ${
                  alert.acknowledged ? "opacity-60" : ""
                }`}
              >
                <div className="flex items-start gap-3">
                  <LevelIcon
                    className={`h-5 w-5 mt-0.5 shrink-0 ${
                      alert.risk_level === 2
                        ? "text-red-600"
                        : alert.risk_level === 1
                          ? "text-amber-600"
                          : "text-green-600"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium">{alert.message}</p>
                      <Badge
                        variant={
                          alert.risk_level === 2 ? "destructive" : "secondary"
                        }
                        className="text-[10px]"
                      >
                        {style.label}
                      </Badge>
                      {alert.acknowledged && (
                        <Badge variant="outline" className="text-[10px]">
                          Read
                        </Badge>
                      )}
                    </div>
                    {alert.location && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {alert.location}
                      </p>
                    )}
                    <div className="flex items-center justify-between mt-2">
                      <p className="text-xs text-muted-foreground">
                        {timeAgo(alert.triggered_at)}
                        {alert.escalation_state &&
                          ` · ${alert.escalation_state}`}
                      </p>
                      {!alert.acknowledged && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => ackMutation.mutate(alert.id)}
                          disabled={ackMutation.isPending}
                        >
                          Mark Read
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            {filter === "active" ? (
              <>
                <ShieldCheck className="h-12 w-12 mb-3 text-green-500 opacity-60" />
                <p className="text-sm font-medium">Ligtas — All Clear</p>
                <p className="text-xs mt-1">
                  No active flood alerts for your area
                </p>
              </>
            ) : (
              <>
                <BellOff className="h-12 w-12 mb-3 opacity-30" />
                <p className="text-sm font-medium">No alert history</p>
                <p className="text-xs mt-1">
                  Alerts will appear here when the system detects flood risk
                </p>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── What To Do ────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Kapag May Alerto / When You Get an Alert
          </CardTitle>
          <CardDescription>Follow these steps to stay safe</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            1. Stay calm and monitor updates from this app and official
            channels.
          </p>
          <p>2. Prepare your emergency go-bag if risk escalates.</p>
          <p>3. Follow evacuation instructions from your barangay or MDRRMO.</p>
          <p>4. Move to higher ground if flooding begins in your area.</p>
          <p>5. Call the emergency hotlines listed in Emergency Contacts.</p>
        </CardContent>
      </Card>
    </div>
  );
}
