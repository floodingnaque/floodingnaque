/**
 * AlertCenterPanel Component
 *
 * Real-time alert center showing live flood alerts with filtering,
 * dismissal, toast notifications, and stats strip. Consumes data
 * from the Zustand alertStore (SSE-fed) and useRecentAlerts hook.
 */

import { formatDistanceToNow } from "date-fns";
import {
  AlertOctagon,
  AlertTriangle,
  Bell,
  CheckCircle2,
  MapPin,
  Shield,
  X,
} from "lucide-react";
import { memo, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRecentAlerts } from "@/features/alerts/hooks/useAlerts";
import { cn } from "@/lib/utils";
import { useAlertActions, useLiveAlerts } from "@/state/stores/alertStore";
import type { Alert, RiskLevel } from "@/types";

// ---------------------------------------------------------------------------
// Risk-level visual config
// ---------------------------------------------------------------------------

const RISK_STYLE: Record<
  RiskLevel,
  {
    border: string;
    bg: string;
    text: string;
    icon: typeof AlertOctagon;
    label: string;
  }
> = {
  2: {
    border: "border-risk-critical/50",
    bg: "bg-risk-critical/10",
    text: "text-risk-critical",
    icon: AlertOctagon,
    label: "Critical",
  },
  1: {
    border: "border-risk-alert/50",
    bg: "bg-risk-alert/10",
    text: "text-risk-alert",
    icon: AlertTriangle,
    label: "Alert",
  },
  0: {
    border: "border-risk-safe/50",
    bg: "bg-risk-safe/10",
    text: "text-risk-safe",
    icon: CheckCircle2,
    label: "Safe",
  },
};

type FilterValue = "all" | "Critical" | "Alert" | "Safe";

const FILTER_TO_LEVEL: Record<Exclude<FilterValue, "all">, RiskLevel> = {
  Critical: 2,
  Alert: 1,
  Safe: 0,
};

const FILTER_COLORS: Record<FilterValue, string> = {
  all: "",
  Critical: "bg-risk-critical text-white hover:bg-risk-critical/90",
  Alert: "bg-risk-alert text-black hover:bg-risk-alert/90",
  Safe: "bg-risk-safe text-white hover:bg-risk-safe/90",
};

// ---------------------------------------------------------------------------
// PulseRing — small animated status dot
// ---------------------------------------------------------------------------

function PulseRing({ className }: { className?: string }) {
  return (
    <span
      className={cn("relative inline-flex h-2.5 w-2.5 shrink-0", className)}
    >
      <span className="absolute inset-0 animate-ping rounded-full bg-current opacity-30" />
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-current" />
    </span>
  );
}

// ---------------------------------------------------------------------------
// AlertCenterPanel
// ---------------------------------------------------------------------------

export const AlertCenterPanel = memo(function AlertCenterPanel({
  className,
}: {
  className?: string;
}) {
  const liveAlerts = useLiveAlerts();
  const { removeAlert, markAllRead } = useAlertActions();
  const { data: recentAlerts, isLoading } = useRecentAlerts(20);

  const [filter, setFilter] = useState<FilterValue>("all");
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  // Merge live + recent, deduplicate by id, newest first
  const allAlerts = useMemo(() => {
    const map = new Map<number, Alert>();
    for (const a of liveAlerts) map.set(a.id, a);
    if (recentAlerts) {
      for (const a of recentAlerts) {
        if (!map.has(a.id)) map.set(a.id, a);
      }
    }
    return Array.from(map.values()).sort(
      (a, b) =>
        new Date(b.triggered_at ?? b.created_at).getTime() -
        new Date(a.triggered_at ?? a.created_at).getTime(),
    );
  }, [liveAlerts, recentAlerts]);

  const { visible, critCount, activeCount, warningCount } = useMemo(() => {
    const vis = allAlerts.filter((a) => {
      if (dismissed.has(a.id)) return false;
      if (filter === "all") return true;
      return a.risk_level === FILTER_TO_LEVEL[filter];
    });
    const crit = allAlerts.filter(
      (a) => a.risk_level === 2 && !dismissed.has(a.id),
    ).length;
    const active = vis.filter((a) => a.risk_level > 0).length;
    const warning = vis.filter((a) => a.risk_level === 1).length;
    return {
      visible: vis,
      critCount: crit,
      activeCount: active,
      warningCount: warning,
    };
  }, [allAlerts, dismissed, filter]);

  const dismiss = (id: number) => {
    setDismissed((prev) => new Set([...prev, id]));
    removeAlert(id);
  };

  const dismissAll = () => {
    setDismissed(new Set(allAlerts.map((a) => a.id)));
    markAllRead();
  };

  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-amber-500/60 via-red-500 to-amber-500/60" />

      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b border-border">
        <div className="flex items-center gap-3">
          <CardTitle className="text-base flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-risk-alert/10 flex items-center justify-center ring-4 ring-risk-alert/20">
              <Bell className="h-4 w-4 text-risk-alert" />
            </div>
            Alert Center
          </CardTitle>
          {critCount > 0 && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-risk-critical text-[10px] font-bold text-white font-mono">
              {critCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {(["all", "Critical", "Alert", "Safe"] as const).map((f) => (
            <Button
              key={f}
              variant={filter === f ? "default" : "ghost"}
              size="sm"
              onClick={() => setFilter(f)}
              className={cn(
                "h-6 px-2 text-[10px] font-mono uppercase tracking-wider",
                filter === f && f !== "all" && FILTER_COLORS[f],
                filter !== f && "text-muted-foreground",
              )}
            >
              {f}
            </Button>
          ))}
          {dismissed.size < allAlerts.length && allAlerts.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={dismissAll}
              className="h-6 px-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground"
            >
              Clear All
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Stats strip */}
        <div className="grid grid-cols-3 gap-2">
          {[
            {
              label: "Active Alerts",
              value: activeCount,
              cls: "text-risk-critical",
            },
            { label: "Critical", value: critCount, cls: "text-risk-critical" },
            { label: "Warnings", value: warningCount, cls: "text-risk-alert" },
          ].map(({ label, value, cls }) => (
            <div
              key={label}
              className="rounded-lg bg-muted border border-border p-2.5"
            >
              <p className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground mb-1">
                {label}
              </p>
              <p className={cn("text-xl font-bold font-mono", cls)}>{value}</p>
            </div>
          ))}
        </div>

        {/* Alert feed */}
        <div className="flex flex-col gap-2 max-h-105 overflow-y-auto pr-1">
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full rounded-lg" />
            ))
          ) : visible.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground font-mono text-sm">
              No alerts matching filter
            </div>
          ) : (
            visible.map((alert) => {
              const style = RISK_STYLE[alert.risk_level];
              return (
                <div
                  key={alert.id}
                  className={cn(
                    "rounded-lg border-l-4 p-3 animate-in fade-in slide-in-from-top-1 duration-300",
                    style.bg,
                    style.border,
                    "border border-l-4",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5">
                        <PulseRing className={style.text} />
                        <span
                          className={cn(
                            "text-xs font-bold font-mono",
                            style.text,
                          )}
                        >
                          {style.label}
                        </span>
                        {alert.location && (
                          <span className="flex items-center gap-1 text-xs text-muted-foreground">
                            <MapPin className="h-3 w-3" />
                            {alert.location}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-foreground/90 leading-relaxed">
                        {alert.message}
                      </p>
                      <p className="text-[10px] text-muted-foreground font-mono mt-1.5">
                        {formatDistanceToNow(
                          new Date(alert.triggered_at ?? alert.created_at),
                          {
                            addSuffix: true,
                          },
                        )}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => dismiss(alert.id)}
                      className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground shrink-0"
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>

                  {alert.risk_level === 2 && (
                    <div className="flex gap-2 mt-2">
                      <Button
                        size="sm"
                        variant="destructive"
                        className="h-7 text-[10px] font-mono"
                      >
                        <MapPin className="h-3 w-3 mr-1" />
                        View on Map
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[10px] font-mono"
                      >
                        <Shield className="h-3 w-3 mr-1" />
                        Find Evacuation Center
                      </Button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </GlassCard>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function AlertCenterPanelSkeleton({
  className,
}: {
  className?: string;
}) {
  return (
    <GlassCard className={cn("overflow-hidden", className)}>
      <div className="h-1 w-full bg-linear-to-r from-muted/60 via-muted to-muted/60" />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b border-border">
        <Skeleton className="h-5 w-32" />
        <div className="flex gap-1.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-12 rounded" />
          ))}
        </div>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        <div className="grid grid-cols-3 gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      </CardContent>
    </GlassCard>
  );
}

export default AlertCenterPanel;
