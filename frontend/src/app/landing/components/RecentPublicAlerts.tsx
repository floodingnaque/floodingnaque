/**
 * RecentPublicAlerts
 *
 * Displays the 5 most recent flood alerts. Fetches from
 * the public /api/v1/alerts/recent endpoint (no auth required).
 * Auto-refreshes every 5 minutes.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { alertsApi } from "@/features/alerts/services/alertsApi";
import { cn } from "@/lib/utils";
import type { Alert, RiskLevel } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bell, CheckCircle, XCircle } from "lucide-react";

const RISK_BADGE: Record<
  RiskLevel,
  { icon: typeof Bell; cls: string; label: string }
> = {
  0: {
    icon: CheckCircle,
    cls: "bg-risk-safe/10 text-risk-safe border-risk-safe/30",
    label: "Safe",
  },
  1: {
    icon: AlertTriangle,
    cls: "bg-risk-alert/10 text-risk-alert border-risk-alert/30",
    label: "Alert",
  },
  2: {
    icon: XCircle,
    cls: "bg-risk-critical/10 text-risk-critical border-risk-critical/30",
    label: "Critical",
  },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function RecentPublicAlerts() {
  const { data: alerts, isLoading } = useQuery<Alert[]>({
    queryKey: ["alerts", "recent", "public", 5],
    queryFn: () => alertsApi.getRecentAlerts(5),
    staleTime: 5 * 60 * 1000,
    // Pause polling while in error state to avoid flooding the console
    refetchInterval: (query) =>
      query.state.status === "error" ? false : 5 * 60 * 1000,
    retry: 1,
  });

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Bell className="h-4 w-4 text-muted-foreground" />
          Recent Alerts
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-start gap-3 py-2">
              <Skeleton className="h-5 w-5 rounded-full shrink-0" />
              <div className="flex-1 space-y-1">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            </div>
          ))
        ) : !alerts?.length ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No recent alerts
          </p>
        ) : (
          alerts.map((alert) => {
            const meta = RISK_BADGE[alert.risk_level];
            const Icon = meta.icon;
            return (
              <div
                key={alert.id}
                className="flex items-start gap-3 py-2 border-b last:border-0 border-border/30"
              >
                <Icon
                  className={cn(
                    "h-4 w-4 mt-0.5 shrink-0",
                    alert.risk_level === 0
                      ? "text-risk-safe"
                      : alert.risk_level === 1
                        ? "text-risk-alert"
                        : "text-risk-critical",
                  )}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground line-clamp-2">
                    {alert.message}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge
                      variant="outline"
                      className={cn("text-[10px] h-4 px-1.5", meta.cls)}
                    >
                      {meta.label}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground">
                      {timeAgo(alert.triggered_at)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
