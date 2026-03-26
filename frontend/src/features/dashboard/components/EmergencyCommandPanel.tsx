/**
 * EmergencyCommandPanel
 *
 * Full-width emergency response command board for the LGU Dashboard.
 * Merges barangay status board, incident timeline, and evacuation
 * capacity chart. Wired to real APIs with demo-data fallback.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PulsingDot } from "@/components/ui/pulsing-dot";
import { RiskStatusBadge } from "@/components/ui/risk-status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BARANGAYS } from "@/config/paranaque";
import { useDashboardStats } from "@/features/dashboard/hooks/useDashboard";
import { useEvacuationCenters } from "@/features/evacuation";
import { cn } from "@/lib/utils";
import type { RiskLabel } from "@/types";
import { Building2 } from "lucide-react";
import { memo, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BarangayStatus, IncidentTimelineEntry } from "../types";

// ---------------------------------------------------------------------------
// Demo / fallback data - shown while APIs load or on error
// ---------------------------------------------------------------------------

const DEMO_BARANGAYS: BarangayStatus[] = [
  {
    name: "Baclaran",
    risk: "Critical",
    alerts: 4,
    evac_open: true,
    evac_cap: 500,
    evac_occ: 312,
    responders: 8,
    road: "Impassable",
  },
  {
    name: "San Dionisio",
    risk: "Critical",
    alerts: 3,
    evac_open: true,
    evac_cap: 350,
    evac_occ: 198,
    responders: 6,
    road: "Impassable",
  },
  {
    name: "Don Galo",
    risk: "Critical",
    alerts: 2,
    evac_open: false,
    evac_cap: 300,
    evac_occ: 300,
    responders: 4,
    road: "Passable (light)",
  },
  {
    name: "Marcelo Green",
    risk: "Critical",
    alerts: 2,
    evac_open: true,
    evac_cap: 400,
    evac_occ: 155,
    responders: 5,
    road: "Impassable",
  },
  {
    name: "Tambo",
    risk: "Alert",
    alerts: 1,
    evac_open: true,
    evac_cap: 400,
    evac_occ: 89,
    responders: 3,
    road: "Passable (light)",
  },
  {
    name: "San Antonio",
    risk: "Alert",
    alerts: 1,
    evac_open: true,
    evac_cap: 350,
    evac_occ: 44,
    responders: 2,
    road: "Passable (all)",
  },
  {
    name: "Moonwalk",
    risk: "Alert",
    alerts: 1,
    evac_open: true,
    evac_cap: 350,
    evac_occ: 28,
    responders: 2,
    road: "Passable (all)",
  },
  {
    name: "Sun Valley",
    risk: "Alert",
    alerts: 0,
    evac_open: false,
    evac_cap: 300,
    evac_occ: 0,
    responders: 1,
    road: "Passable (all)",
  },
  {
    name: "BF Homes",
    risk: "Safe",
    alerts: 0,
    evac_open: false,
    evac_cap: 800,
    evac_occ: 0,
    responders: 0,
    road: "Passable (all)",
  },
  {
    name: "La Huerta",
    risk: "Safe",
    alerts: 0,
    evac_open: false,
    evac_cap: 300,
    evac_occ: 0,
    responders: 0,
    road: "Passable (all)",
  },
];

const DEMO_TIMELINE: IncidentTimelineEntry[] = [
  {
    time: "06:15",
    event: "PAGASA issues ITCZ advisory for Metro Manila",
    level: "info",
  },
  {
    time: "06:40",
    event: "Rainfall exceeds 30 mm/hr in Baclaran - Alert triggered",
    level: "Alert",
  },
  {
    time: "07:12",
    event: "Community report: waist-deep flooding at Quirino Ave",
    level: "Critical",
  },
  {
    time: "07:18",
    event: "DRRMO deploys 4 response teams to Baclaran & Don Galo",
    level: "info",
  },
  {
    time: "07:35",
    event: "Evacuation center opened - Parañaque City Hall Gym",
    level: "info",
  },
  {
    time: "08:02",
    event: "ML model upgrades San Dionisio to Critical (prob: 89%)",
    level: "Critical",
  },
  {
    time: "08:20",
    event: "SMS blast sent to 12,440 registered residents",
    level: "info",
  },
  {
    time: "08:55",
    event: "MMDA advisory: Quirino Ave. closed to all vehicles",
    level: "Alert",
  },
];

// ---------------------------------------------------------------------------
// Sub: Stat KPI
// ---------------------------------------------------------------------------

const StatKPI = memo(function StatKPI({
  label,
  value,
  sub,
  colorClass,
}: {
  label: string;
  value: string | number;
  sub?: string;
  colorClass?: string;
}) {
  return (
    <div className="rounded-lg bg-muted border border-border p-3">
      <div className="text-[9px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-1">
        {label}
      </div>
      <div
        className={cn(
          "text-xl font-bold font-mono leading-none",
          colorClass ?? "text-foreground",
        )}
      >
        {value}
      </div>
      {sub && (
        <div className="text-[9px] text-muted-foreground font-mono mt-1">
          {sub}
        </div>
      )}
    </div>
  );
});

// ---------------------------------------------------------------------------
// Sub: Barangay Status Board
// ---------------------------------------------------------------------------

const BarangayStatusBoard = memo(function BarangayStatusBoard({
  barangays,
}: {
  barangays: BarangayStatus[];
}) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
        Barangay Status Board
      </div>
      <div className="flex flex-col gap-1 max-h-85 overflow-y-auto pr-1">
        {barangays.map((b) => {
          const isSelected = selected === b.name;
          const riskKey = b.risk as RiskLabel;
          return (
            <button
              key={b.name}
              type="button"
              onClick={() => setSelected(isSelected ? null : b.name)}
              className={cn(
                "w-full text-left rounded-md border p-2 pl-3 cursor-pointer transition-colors",
                "border-l-[3px]",
                isSelected
                  ? "bg-muted/80 border-l-current"
                  : "bg-muted border-border hover:bg-accent/50",
                riskKey === "Critical" && "border-l-risk-critical",
                riskKey === "Alert" && "border-l-risk-alert",
                riskKey === "Safe" && "border-l-risk-safe",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <PulsingDot
                    color={
                      riskKey === "Critical"
                        ? "hsl(var(--risk-critical))"
                        : riskKey === "Alert"
                          ? "hsl(var(--risk-alert))"
                          : "hsl(var(--risk-safe))"
                    }
                    size="sm"
                  />
                  <span className="text-xs font-semibold text-foreground font-mono truncate">
                    {b.name}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <RiskStatusBadge
                    risk={riskKey}
                    className="text-[9px] px-1.5 py-0"
                  />
                  {b.alerts > 0 && (
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1.5 py-0 border-risk-alert/40 text-risk-alert bg-risk-alert/10"
                    >
                      {b.alerts} alert{b.alerts > 1 ? "s" : ""}
                    </Badge>
                  )}
                </div>
              </div>
              {isSelected && (
                <div className="mt-2 grid grid-cols-2 gap-1">
                  <div className="rounded bg-background p-1.5">
                    <div className="text-[8px] uppercase tracking-wider text-muted-foreground font-mono">
                      Evacuation
                    </div>
                    <div
                      className={cn(
                        "text-[11px] font-mono font-semibold",
                        b.evac_open
                          ? "text-risk-safe"
                          : "text-muted-foreground",
                      )}
                    >
                      {b.evac_open
                        ? `Open (${b.evac_occ}/${b.evac_cap})`
                        : "Closed"}
                    </div>
                  </div>
                  <div className="rounded bg-background p-1.5">
                    <div className="text-[8px] uppercase tracking-wider text-muted-foreground font-mono">
                      Responders
                    </div>
                    <div className="text-[11px] font-mono font-semibold text-primary">
                      {b.responders} deployed
                    </div>
                  </div>
                  <div className="rounded bg-background p-1.5 col-span-2">
                    <div className="text-[8px] uppercase tracking-wider text-muted-foreground font-mono">
                      Road Status
                    </div>
                    <div
                      className={cn(
                        "text-[11px] font-mono font-semibold",
                        b.road === "Impassable"
                          ? "text-risk-critical"
                          : "text-risk-safe",
                      )}
                    >
                      {b.road}
                    </div>
                  </div>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
});

// ---------------------------------------------------------------------------
// Sub: Incident Timeline
// ---------------------------------------------------------------------------

const IncidentTimeline = memo(function IncidentTimeline({
  events,
}: {
  events: IncidentTimelineEntry[];
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
        Incident Timeline
      </div>
      <div className="relative max-h-85 overflow-y-auto pr-1">
        {/* Vertical connector */}
        <div className="absolute left-9 top-0 bottom-0 w-px bg-border" />

        {events.map((t, i) => {
          const isCrit = t.level === "Critical";
          const isAlert = t.level === "Alert";
          return (
            <div key={i} className="flex gap-2.5 mb-2.5 relative">
              <div className="w-8.5 shrink-0 pt-0.5 text-right">
                <span className="text-[9px] text-muted-foreground font-mono">
                  {t.time}
                </span>
              </div>
              {/* Dot */}
              <div className="shrink-0 z-1 mt-1">
                <div
                  className={cn(
                    "w-2 h-2 rounded-full border",
                    isCrit &&
                      "bg-risk-critical border-risk-critical shadow-[0_0_6px_rgba(220,53,69,0.4)]",
                    isAlert &&
                      "bg-risk-alert border-risk-alert shadow-[0_0_6px_rgba(255,193,7,0.4)]",
                    !isCrit &&
                      !isAlert &&
                      "bg-muted-foreground/40 border-muted-foreground/40",
                  )}
                />
              </div>
              <div
                className={cn(
                  "flex-1 rounded-md border p-1.5",
                  isCrit && "bg-risk-critical/5 border-risk-critical/30",
                  isAlert && "bg-risk-alert/5 border-risk-alert/30",
                  !isCrit && !isAlert && "bg-muted border-border",
                )}
              >
                <div
                  className={cn(
                    "text-[11px] font-mono leading-relaxed",
                    isCrit && "text-risk-critical",
                    isAlert && "text-risk-alert",
                    !isCrit && !isAlert && "text-muted-foreground",
                  )}
                >
                  {t.event}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

// ---------------------------------------------------------------------------
// Sub: Evacuation Capacity Chart
// ---------------------------------------------------------------------------

const EvacCapacityChart = memo(function EvacCapacityChart({
  barangays,
}: {
  barangays: BarangayStatus[];
}) {
  const openCenters = barangays.filter((b) => b.evac_open);
  if (openCenters.length === 0) return null;

  return (
    <div className="mt-4">
      <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
        Evacuation Center Occupancy by Barangay
      </div>
      <ResponsiveContainer width="100%" height={100}>
        <BarChart
          data={openCenters}
          margin={{ top: 0, right: 0, bottom: 0, left: -30 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="hsl(var(--border))"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 8 }}
            interval={0}
            angle={-15}
            dy={5}
          />
          <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 8 }} />
          <Tooltip
            formatter={(v, n) => [
              Number(v),
              n === "evac_occ" ? "Occupancy" : "Capacity",
            ]}
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              fontSize: 11,
              borderRadius: 6,
            }}
            labelStyle={{ color: "hsl(var(--foreground))" }}
          />
          <Bar
            dataKey="evac_cap"
            fill="hsl(var(--border))"
            radius={[2, 2, 0, 0]}
            name="Capacity"
          />
          <Bar dataKey="evac_occ" radius={[2, 2, 0, 0]} name="Occupancy">
            {openCenters.map((b, i) => {
              const ratio = b.evac_occ / b.evac_cap;
              const fill =
                ratio >= 0.9
                  ? "hsl(var(--risk-critical))"
                  : ratio >= 0.7
                    ? "hsl(var(--risk-alert))"
                    : "hsl(var(--risk-safe))";
              return <Cell key={i} fill={fill} />;
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
});

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const EmergencyCommandPanel = memo(function EmergencyCommandPanel() {
  const { data: evacData } = useEvacuationCenters();
  const { data: stats } = useDashboardStats();

  // Build barangay status from live evacuation data, fall back to demo
  const barangays: BarangayStatus[] = useMemo(() => {
    if (!evacData) return DEMO_BARANGAYS;

    const centers =
      "centers" in evacData
        ? (
            evacData as {
              centers: Array<{
                barangay: string;
                is_active: boolean;
                capacity_total: number;
                capacity_current: number;
              }>;
            }
          ).centers
        : Array.isArray(evacData)
          ? evacData
          : [];

    if (centers.length === 0) return DEMO_BARANGAYS;

    return BARANGAYS.map((brgy) => {
      const center = centers.find(
        (c) => c.barangay.toLowerCase() === brgy.name.toLowerCase(),
      );
      const risk: BarangayStatus["risk"] =
        brgy.floodRisk === "high"
          ? "Critical"
          : brgy.floodRisk === "moderate"
            ? "Alert"
            : "Safe";

      return {
        name: brgy.name,
        risk,
        alerts: 0,
        evac_open: center?.is_active ?? false,
        evac_cap: center?.capacity_total ?? 0,
        evac_occ: center?.capacity_current ?? 0,
        responders: 0,
        road: "Passable (all)" as const,
      };
    }).sort((a, b) => {
      const order = { Critical: 0, Alert: 1, Safe: 2 };
      return order[a.risk] - order[b.risk];
    });
  }, [evacData]);

  const timeline = DEMO_TIMELINE; // Timeline always demo (no backend endpoint yet)

  const criticalCount = barangays.filter((b) => b.risk === "Critical").length;
  const totalAlerts =
    barangays.reduce((s, b) => s + b.alerts, 0) || stats?.active_alerts || 0;
  const totalEvacOcc = barangays.reduce((s, b) => s + b.evac_occ, 0);
  const totalEvacCap = barangays.reduce((s, b) => s + b.evac_cap, 0);
  const totalResponders = barangays.reduce((s, b) => s + b.responders, 0);
  const roadsClosed = barangays.filter((b) => b.road === "Impassable").length;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <div className="flex items-center gap-3">
          <CardTitle className="flex items-center gap-2 text-sm font-bold font-mono tracking-wide">
            <Building2 className="h-4 w-4" />
            Emergency Response Command
          </CardTitle>
          <div className="flex items-center gap-1.5">
            <PulsingDot color="hsl(var(--risk-critical))" size="sm" />
            <span className="text-[9px] text-risk-critical font-mono uppercase tracking-wider">
              Active Incident
            </span>
          </div>
        </div>
        <span className="text-[10px] text-muted-foreground font-mono">
          {new Date().toLocaleString("en-PH", {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Command metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
          <StatKPI
            label="Critical Barangays"
            value={criticalCount}
            colorClass="text-risk-critical"
          />
          <StatKPI
            label="Active Alerts"
            value={totalAlerts}
            colorClass="text-risk-alert"
          />
          <StatKPI
            label="Evacuation Occ."
            value={totalEvacOcc.toLocaleString()}
            colorClass="text-primary"
            sub={
              totalEvacCap > 0
                ? `${Math.round((totalEvacOcc / totalEvacCap) * 100)}% of ${totalEvacCap.toLocaleString()} cap`
                : undefined
            }
          />
          <StatKPI
            label="Responders"
            value={totalResponders}
            colorClass="text-risk-safe"
            sub="deployed"
          />
          <StatKPI
            label="Roads Closed"
            value={roadsClosed}
            colorClass="text-risk-critical"
            sub="impassable"
          />
        </div>

        {/* Status board + Timeline */}
        <div className="grid gap-4 lg:grid-cols-2">
          <BarangayStatusBoard barangays={barangays} />
          <IncidentTimeline events={timeline} />
        </div>

        {/* Evacuation capacity chart */}
        <EvacCapacityChart barangays={barangays} />
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function EmergencyCommandPanelSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-64" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-5 gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
        <Skeleton className="h-24" />
      </CardContent>
    </Card>
  );
}
