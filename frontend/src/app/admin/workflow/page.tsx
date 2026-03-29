/**
 * Admin LGU Workflow & After-Action Reports Page
 *
 * Industrial-grade workflow management for the RA 10121-compliant
 * LGU incident pipeline:
 *   Alert → LGU Confirmation → Public Broadcast → Resolution → Closed (AAR)
 *
 * Tabs: Incidents | After-Action Reports | Analytics
 */

import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Clock,
  FileText,
  GitBranch,
  Loader2,
  Megaphone,
  Plus,
  Radio,
  RefreshCw,
  Send,
  Shield,
  ShieldCheck,
  Timer,
  TrendingUp,
  WifiOff,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChartTooltip } from "@/components/ui/chart-tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PRIMARY_HEX, RISK_HEX } from "@/lib/colors";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";

import type {
  AARStatus,
  AfterActionReport,
  Incident,
  IncidentStats,
  IncidentStatus,
  WorkflowAnalytics,
} from "@/types";
import { LGU_WORKFLOW_STEPS } from "@/types";

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<
  IncidentStatus,
  {
    label: string;
    className: string;
    color: string;
    headerClass: string;
    iconBgClass: string;
    iconTextClass: string;
    icon: typeof AlertTriangle;
  }
> = {
  alert_raised: {
    label: "Alert Raised",
    className: "border-risk-critical/30 bg-risk-critical/10 text-risk-critical",
    color: RISK_HEX.critical,
    headerClass:
      "bg-risk-critical/10 border-b-2 border-risk-critical/40 text-risk-critical",
    iconBgClass: "bg-risk-critical/10",
    iconTextClass: "text-risk-critical",
    icon: AlertTriangle,
  },
  lgu_confirmed: {
    label: "LGU Confirmed",
    className: "border-risk-alert/30 bg-risk-alert/10 text-risk-alert",
    color: RISK_HEX.alert,
    headerClass:
      "bg-risk-alert/10 border-b-2 border-risk-alert/40 text-risk-alert",
    iconBgClass: "bg-risk-alert/10",
    iconTextClass: "text-risk-alert",
    icon: ShieldCheck,
  },
  broadcast_sent: {
    label: "Broadcast Sent",
    className: "border-blue-500/30 bg-blue-500/10 text-blue-400",
    color: "#3B82F6",
    headerClass: "bg-blue-500/10 border-b-2 border-blue-500/40 text-blue-400",
    iconBgClass: "bg-blue-500/10",
    iconTextClass: "text-blue-400",
    icon: Megaphone,
  },
  resolved: {
    label: "Resolved",
    className: "border-risk-safe/30 bg-risk-safe/10 text-risk-safe",
    color: RISK_HEX.safe,
    headerClass:
      "bg-risk-safe/10 border-b-2 border-risk-safe/40 text-risk-safe",
    iconBgClass: "bg-risk-safe/10",
    iconTextClass: "text-risk-safe",
    icon: CheckCircle2,
  },
  closed: {
    label: "Closed",
    className: "border-slate-500/30 bg-slate-500/10 text-slate-400",
    color: "#64748b",
    headerClass:
      "bg-slate-500/10 border-b-2 border-slate-500/40 text-slate-400",
    iconBgClass: "bg-slate-500/10",
    iconTextClass: "text-slate-400",
    icon: FileText,
  },
};

const AAR_STATUS_CONFIG: Record<
  AARStatus,
  { label: string; className: string }
> = {
  draft: {
    label: "Draft",
    className: "border-slate-500/30 bg-slate-500/10 text-slate-400",
  },
  submitted: {
    label: "Submitted",
    className: "border-blue-500/30 bg-blue-500/10 text-blue-400",
  },
  reviewed: {
    label: "Reviewed",
    className: "border-risk-alert/30 bg-risk-alert/10 text-risk-alert",
  },
  approved: {
    label: "Approved",
    className: "border-risk-safe/30 bg-risk-safe/10 text-risk-safe",
  },
};

const NEXT_STATUS: Partial<Record<IncidentStatus, IncidentStatus>> = {
  alert_raised: "lgu_confirmed",
  lgu_confirmed: "broadcast_sent",
  broadcast_sent: "resolved",
  resolved: "closed",
};

const BROADCAST_CHANNELS = [
  { value: "sms", label: "SMS / Text Blast" },
  { value: "sirens", label: "Warning Sirens" },
  { value: "social_media", label: "Social Media" },
  { value: "radio", label: "Radio Broadcast" },
  { value: "pa_system", label: "PA System" },
  { value: "door_to_door", label: "Door-to-Door" },
];

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const CHART_MARGIN = { top: 5, right: 10, bottom: 5, left: -10 } as const;

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useIncidentsAdmin() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [stats, setStats] = useState<IncidentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [incRes, statsRes] = await Promise.all([
        api.get<{ data?: Incident[] }>(API_ENDPOINTS.lgu.incidents, {
          params: { limit: 100 },
        }),
        api.get<{ data?: IncidentStats | null }>(
          API_ENDPOINTS.lgu.incidentStats,
        ),
      ]);
      setIncidents(Array.isArray(incRes.data) ? incRes.data : []);
      setStats(statsRes.data ?? null);
      setLastUpdated(new Date());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { incidents, stats, loading, error, lastUpdated, refetch: fetch };
}

function useAARs(incidentId: number | null) {
  const [aars, setAars] = useState<AfterActionReport[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async () => {
    if (!incidentId) {
      setAars([]);
      return;
    }
    setLoading(true);
    try {
      const res = await api.get<{ data?: AfterActionReport[] }>(
        `${API_ENDPOINTS.lgu.incidents}/${incidentId}/aar`,
      );
      setAars(Array.isArray(res.data) ? res.data : []);
    } catch {
      setAars([]);
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { aars, loading, refetch: fetch };
}

function useWorkflowAnalytics() {
  const [analytics, setAnalytics] = useState<WorkflowAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<{ data?: WorkflowAnalytics | null }>(
        API_ENDPOINTS.lgu.incidentAnalytics,
      );
      setAnalytics(res.data ?? null);
    } catch {
      setAnalytics(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { analytics, loading, refetch: fetch };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function timeSince(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ${mins % 60}m`;
  const days = Math.floor(hrs / 24);
  return `${days}d ${hrs % 24}h`;
}

function isStalled(incident: Incident): boolean {
  if (incident.status !== "alert_raised" && incident.status !== "lgu_confirmed")
    return false;
  const elapsed = Date.now() - new Date(incident.created_at).getTime();
  return elapsed > 24 * 60 * 60 * 1000;
}

// ---------------------------------------------------------------------------
// Pipeline Stage Card (Kanban column)
// ---------------------------------------------------------------------------

function PipelineStage({
  status,
  incidents,
  onSelectIncident,
}: {
  status: IncidentStatus;
  incidents: Incident[];
  onSelectIncident: (id: number) => void;
}) {
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;
  const stalledCount = incidents.filter(isStalled).length;

  return (
    <div className="min-w-50 flex-1">
      {/* Column header */}
      <div
        className={cn(
          "rounded-t-lg px-3 py-2 flex items-center justify-between",
          cfg.headerClass,
        )}
      >
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" />
          <span className="text-xs font-semibold">{cfg.label}</span>
        </div>
        <Badge
          variant="outline"
          className={cn("text-[10px] min-w-5.5 justify-center", cfg.className)}
        >
          {incidents.length}
        </Badge>
      </div>

      {/* Incident cards */}
      <div className="space-y-2 p-2 min-h-20 rounded-b-lg bg-muted/20 border border-t-0 border-border/30">
        {incidents.length === 0 && (
          <p className="text-[11px] text-muted-foreground/50 text-center py-4">
            No incidents
          </p>
        )}
        {incidents.map((inc) => {
          const stalled = isStalled(inc);
          return (
            <button
              key={inc.id}
              onClick={() => onSelectIncident(inc.id)}
              className={cn(
                "w-full text-left rounded-md border p-2.5 transition-colors hover:bg-accent/50 cursor-pointer",
                stalled
                  ? "border-risk-alert/40 bg-risk-alert/5"
                  : "border-border/40 bg-card/60",
              )}
            >
              <p className="text-xs font-medium truncate">{inc.title}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <span className="text-[10px] text-muted-foreground">
                  {inc.barangay}
                </span>
                <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                  <Clock className="h-2.5 w-2.5" />
                  {timeSince(inc.created_at)}
                </span>
              </div>
              {stalled && (
                <div className="flex items-center gap-1 mt-1.5">
                  <AlertTriangle className="h-3 w-3 text-risk-alert" />
                  <span className="text-[10px] font-medium text-risk-alert">
                    Stalled &gt;24h
                  </span>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Stalled banner */}
      {stalledCount > 0 && (
        <div className="mt-1 rounded-md bg-risk-alert/10 border border-risk-alert/20 px-2 py-1 flex items-center gap-1.5">
          <AlertTriangle className="h-3 w-3 text-risk-alert" />
          <span className="text-[10px] font-medium text-risk-alert">
            {stalledCount} stalled
          </span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pipeline Flow Arrows
// ---------------------------------------------------------------------------

function FlowArrow() {
  return (
    <div className="flex items-center justify-center px-1 pt-8">
      <ChevronRight className="h-5 w-5 text-muted-foreground/30" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Kanban Pipeline Overview
// ---------------------------------------------------------------------------

function KanbanPipeline({
  incidents,
  stats,
  onSelectIncident,
}: {
  incidents: Incident[];
  stats: IncidentStats | null;
  onSelectIncident: (id: number) => void;
}) {
  const stages: IncidentStatus[] = [
    "alert_raised",
    "lgu_confirmed",
    "broadcast_sent",
    "resolved",
    "closed",
  ];

  const groupedIncidents = useMemo(() => {
    const groups: Record<IncidentStatus, Incident[]> = {
      alert_raised: [],
      lgu_confirmed: [],
      broadcast_sent: [],
      resolved: [],
      closed: [],
    };
    for (const inc of incidents) {
      if (groups[inc.status]) {
        groups[inc.status].push(inc);
      }
    }
    return groups;
  }, [incidents]);

  const totalStalled = incidents.filter(isStalled).length;

  return (
    <div className="space-y-4">
      {/* Summary stats bar */}
      <div className="flex flex-wrap gap-4">
        <div className="flex items-center gap-2 text-sm">
          <div className="h-2.5 w-2.5 rounded-full bg-primary" />
          <span className="text-muted-foreground">
            Active:{" "}
            <span className="font-semibold text-foreground">
              {stats?.total_active ?? 0}
            </span>
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <div className="h-2.5 w-2.5 rounded-full bg-risk-safe" />
          <span className="text-muted-foreground">
            Resolved:{" "}
            <span className="font-semibold text-foreground">
              {stats?.by_status?.resolved ?? 0}
            </span>
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <div className="h-2.5 w-2.5 rounded-full bg-slate-500" />
          <span className="text-muted-foreground">
            Closed:{" "}
            <span className="font-semibold text-foreground">
              {stats?.by_status?.closed ?? 0}
            </span>
          </span>
        </div>
        {totalStalled > 0 && (
          <div className="flex items-center gap-2 text-sm">
            <AlertTriangle className="h-3.5 w-3.5 text-risk-alert" />
            <span className="font-semibold text-risk-alert">
              {totalStalled} stalled incident{totalStalled > 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>

      {/* Kanban columns */}
      <div className="flex gap-0 overflow-x-auto pb-2">
        {stages.map((s, i) => (
          <div key={s} className="flex items-start">
            <PipelineStage
              status={s}
              incidents={groupedIncidents[s]}
              onSelectIncident={onSelectIncident}
            />
            {i < stages.length - 1 && <FlowArrow />}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Incident Row (list view)
// ---------------------------------------------------------------------------

function IncidentRow({
  incident,
  selected,
  onSelect,
  onAdvance,
  transitioning,
}: {
  incident: Incident;
  selected: boolean;
  onSelect: () => void;
  onAdvance: () => void;
  transitioning: number | null;
}) {
  const cfg = STATUS_CONFIG[incident.status];
  const next = NEXT_STATUS[incident.status];
  const stalled = isStalled(incident);

  return (
    <div
      role="button"
      tabIndex={0}
      className={cn(
        "group rounded-lg border p-4 transition-all cursor-pointer",
        selected
          ? "border-primary/40 bg-primary/5 ring-1 ring-primary/20"
          : stalled
            ? "border-risk-alert/30 bg-risk-alert/5 hover:border-risk-alert/50"
            : "border-border/40 bg-card/60 hover:border-primary/30 hover:bg-primary/5",
      )}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={cn(
              "h-9 w-9 rounded-lg flex items-center justify-center shrink-0",
              cfg.iconBgClass,
            )}
          >
            <cfg.icon className={cn("h-4 w-4", cfg.iconTextClass)} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold truncate">{incident.title}</p>
              {stalled && (
                <Badge
                  variant="outline"
                  className="border-risk-alert/30 bg-risk-alert/10 text-risk-alert text-[10px]"
                >
                  <AlertTriangle className="h-3 w-3 mr-0.5" />
                  Stalled
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-xs text-muted-foreground">
                {incident.barangay}
              </span>
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {timeSince(incident.created_at)}
              </span>
              <Badge
                variant="outline"
                className={cn("text-[10px]", cfg.className)}
              >
                {cfg.label}
              </Badge>
            </div>
          </div>
        </div>

        {next && (
          <Button
            variant="outline"
            size="sm"
            className="shrink-0 text-xs"
            onClick={(e) => {
              e.stopPropagation();
              onAdvance();
            }}
            disabled={transitioning === incident.id}
          >
            {transitioning === incident.id ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <>
                <ArrowRight className="h-3 w-3 mr-1" />
                {STATUS_CONFIG[next].label}
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Incident Detail Panel
// ---------------------------------------------------------------------------

function IncidentDetail({
  incident,
  onTransition,
  transitioning,
}: {
  incident: Incident;
  onTransition: () => void;
  transitioning: number | null;
}) {
  const cfg = STATUS_CONFIG[incident.status];
  const next = NEXT_STATUS[incident.status];

  return (
    <GlassCard intensity="medium" className="relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary/60 to-primary/20" />
      <div className="p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold">{incident.title}</h3>
            <p className="text-xs text-muted-foreground mt-1">
              {incident.barangay} · {incident.incident_type?.replace("_", " ")}{" "}
              · Created {new Date(incident.created_at).toLocaleString()}
            </p>
          </div>
          <Badge variant="outline" className={cn("text-xs", cfg.className)}>
            {cfg.label}
          </Badge>
        </div>

        {incident.description && (
          <p className="text-sm text-muted-foreground">
            {incident.description}
          </p>
        )}

        {/* Workflow stepper */}
        <div className="flex items-center gap-1 flex-wrap">
          {LGU_WORKFLOW_STEPS.map((step, i) => {
            const stepIdx = LGU_WORKFLOW_STEPS.findIndex(
              (s) => s.status === incident.status,
            );
            const isComplete = i < stepIdx;
            const isCurrent = i === stepIdx;
            return (
              <div key={step.status} className="flex items-center gap-1">
                <div
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium",
                    isComplete &&
                      "bg-risk-safe/15 text-risk-safe ring-1 ring-risk-safe/30",
                    isCurrent &&
                      "bg-primary/15 text-primary ring-1 ring-primary/40",
                    !isComplete &&
                      !isCurrent &&
                      "bg-muted/40 text-muted-foreground/50",
                  )}
                >
                  {isComplete && (
                    <CheckCircle2 className="h-3 w-3 inline mr-1" />
                  )}
                  {step.label}
                </div>
                {i < LGU_WORKFLOW_STEPS.length - 1 && (
                  <ChevronRight className="h-3 w-3 text-muted-foreground/40" />
                )}
              </div>
            );
          })}
        </div>

        <Separator className="opacity-30" />

        {/* Impact data */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Affected Families</p>
            <p className="font-semibold">{incident.affected_families}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Evacuated</p>
            <p className="font-semibold">{incident.evacuated_families}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Casualties</p>
            <p className="font-semibold">{incident.casualties}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Estimated Damage</p>
            <p className="font-semibold">
              {incident.estimated_damage
                ? `₱${incident.estimated_damage.toLocaleString()}`
                : "-"}
            </p>
          </div>
        </div>

        {/* Timestamps */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs text-muted-foreground">
          {incident.confirmed_by && (
            <span>
              Confirmed by:{" "}
              <span className="text-foreground">{incident.confirmed_by}</span>
            </span>
          )}
          {incident.confirmed_at && (
            <span>
              Confirmed: {new Date(incident.confirmed_at).toLocaleString()}
            </span>
          )}
          {incident.broadcast_sent_at && (
            <span>
              Broadcast: {new Date(incident.broadcast_sent_at).toLocaleString()}
            </span>
          )}
          {incident.broadcast_channels && (
            <span>
              Channels:{" "}
              <span className="text-foreground">
                {incident.broadcast_channels}
              </span>
            </span>
          )}
          {incident.resolved_at && (
            <span>
              Resolved: {new Date(incident.resolved_at).toLocaleString()}
            </span>
          )}
          {incident.resolved_by && (
            <span>
              Resolved by:{" "}
              <span className="text-foreground">{incident.resolved_by}</span>
            </span>
          )}
        </div>

        {/* Advance button */}
        {next && (
          <>
            <Separator className="opacity-30" />
            <div className="flex justify-end">
              <Button
                size="sm"
                className="bg-primary hover:bg-primary/90"
                onClick={onTransition}
                disabled={transitioning === incident.id}
              >
                {transitioning === incident.id ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <ArrowRight className="h-4 w-4 mr-2" />
                )}
                Advance to {STATUS_CONFIG[next].label}
              </Button>
            </div>
          </>
        )}
      </div>
    </GlassCard>
  );
}

// ---------------------------------------------------------------------------
// Transition Validation Dialog
// ---------------------------------------------------------------------------

interface TransitionData {
  actor: string;
  confirmation_notes?: string;
  broadcast_channels?: string;
  affected_families?: number;
  evacuated_families?: number;
  casualties?: number;
  estimated_damage?: number;
}

function TransitionDialog({
  open,
  onOpenChange,
  incident,
  onConfirm,
  submitting,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  incident: Incident;
  onConfirm: (data: TransitionData) => void;
  submitting: boolean;
}) {
  const [actor, setActor] = useState("");
  const [notes, setNotes] = useState("");
  const [channels, setChannels] = useState<string[]>([]);
  const [affectedFamilies, setAffectedFamilies] = useState(
    String(incident.affected_families || 0),
  );
  const [evacuatedFamilies, setEvacuatedFamilies] = useState(
    String(incident.evacuated_families || 0),
  );
  const [casualties, setCasualties] = useState(
    String(incident.casualties || 0),
  );
  const [estimatedDamage, setEstimatedDamage] = useState(
    String(incident.estimated_damage || ""),
  );
  const [confirmed, setConfirmed] = useState(false);

  const next = NEXT_STATUS[incident.status];
  if (!next) return null;

  const handleSubmit = () => {
    const data: TransitionData = { actor: actor.trim() || "admin" };

    if (next === "lgu_confirmed") {
      data.confirmation_notes = notes;
    } else if (next === "broadcast_sent") {
      data.broadcast_channels = channels.join(", ");
    } else if (next === "resolved") {
      data.affected_families = parseInt(affectedFamilies) || 0;
      data.evacuated_families = parseInt(evacuatedFamilies) || 0;
      data.casualties = parseInt(casualties) || 0;
      const dmg = parseFloat(estimatedDamage);
      if (!isNaN(dmg)) data.estimated_damage = dmg;
    }

    onConfirm(data);
  };

  const isValid = (): boolean => {
    if (!actor.trim()) return false;
    if (next === "broadcast_sent" && channels.length === 0) return false;
    if (next === "closed" && !confirmed) return false;
    return true;
  };

  const toggleChannel = (ch: string) => {
    setChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch],
    );
  };

  const nextCfg = STATUS_CONFIG[next];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowRight className="h-5 w-5 text-primary" />
            Transition to {nextCfg.label}
          </DialogTitle>
          <DialogDescription>
            Advancing "{incident.title}" from{" "}
            {STATUS_CONFIG[incident.status].label} → {nextCfg.label}. Fill out
            the required fields below.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Actor / Officer - always required */}
          <div className="space-y-2">
            <Label htmlFor="tx-actor">MDRRMO Officer *</Label>
            <Input
              id="tx-actor"
              placeholder="Full name of authorizing officer"
              value={actor}
              onChange={(e) => setActor(e.target.value)}
            />
          </div>

          {/* Stage-specific fields */}
          {next === "lgu_confirmed" && (
            <div className="space-y-2">
              <Label htmlFor="tx-notes">Confirmation Notes</Label>
              <textarea
                id="tx-notes"
                className="flex min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                placeholder="Basis for confirmation, field assessment notes..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          )}

          {next === "broadcast_sent" && (
            <div className="space-y-2">
              <Label>Broadcast Channels *</Label>
              <p className="text-xs text-muted-foreground">
                Select at least one channel for public dissemination.
              </p>
              <div className="grid grid-cols-2 gap-2">
                {BROADCAST_CHANNELS.map((ch) => (
                  <button
                    key={ch.value}
                    type="button"
                    onClick={() => toggleChannel(ch.value)}
                    className={cn(
                      "rounded-md border px-3 py-2 text-xs text-left transition-colors",
                      channels.includes(ch.value)
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-border/40 hover:border-primary/30",
                    )}
                  >
                    <Radio
                      className={cn(
                        "h-3 w-3 inline mr-1.5",
                        channels.includes(ch.value)
                          ? "text-primary"
                          : "text-muted-foreground/40",
                      )}
                    />
                    {ch.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {next === "resolved" && (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">
                Record final impact data before resolving.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="tx-affected" className="text-xs">
                    Affected Families
                  </Label>
                  <Input
                    id="tx-affected"
                    type="number"
                    min="0"
                    value={affectedFamilies}
                    onChange={(e) => setAffectedFamilies(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="tx-evacuated" className="text-xs">
                    Evacuated Families
                  </Label>
                  <Input
                    id="tx-evacuated"
                    type="number"
                    min="0"
                    value={evacuatedFamilies}
                    onChange={(e) => setEvacuatedFamilies(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="tx-casualties" className="text-xs">
                    Casualties
                  </Label>
                  <Input
                    id="tx-casualties"
                    type="number"
                    min="0"
                    value={casualties}
                    onChange={(e) => setCasualties(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="tx-damage" className="text-xs">
                    Est. Damage (₱)
                  </Label>
                  <Input
                    id="tx-damage"
                    type="number"
                    min="0"
                    placeholder="0"
                    value={estimatedDamage}
                    onChange={(e) => setEstimatedDamage(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          {next === "closed" && (
            <div className="space-y-3">
              <div className="rounded-lg border border-risk-alert/30 bg-risk-alert/5 p-3">
                <p className="text-xs text-risk-alert font-medium flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Closing this incident requires an After-Action Report per RA
                  10121.
                </p>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                  className="rounded border-border"
                />
                <span className="text-sm">
                  I confirm that an AAR has been filed or will be filed within
                  48 hours.
                </span>
              </label>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={submitting || !isValid()}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Confirm Transition
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// AAR Card
// ---------------------------------------------------------------------------

function AARCard({ aar }: { aar: AfterActionReport }) {
  const statusCfg = AAR_STATUS_CONFIG[aar.status];

  const [mountTime] = useState(Date.now);
  const is48hWarning =
    aar.status === "draft" &&
    mountTime - new Date(aar.created_at).getTime() > 48 * 60 * 60 * 1000;

  return (
    <GlassCard intensity="light" className="relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary/40 to-primary/10" />
      <div className="p-5 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-linear-to-br from-primary/15 to-primary/5 ring-1 ring-primary/20 flex items-center justify-center">
              <FileText className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold">{aar.title}</p>
                {is48hWarning && (
                  <Badge
                    variant="outline"
                    className="border-risk-alert/30 bg-risk-alert/10 text-risk-alert text-[10px]"
                  >
                    <Clock className="h-3 w-3 mr-0.5" />
                    &gt;48h Draft
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {new Date(aar.created_at).toLocaleDateString()}
                {aar.prepared_by && ` · By ${aar.prepared_by}`}
              </p>
            </div>
          </div>
          <Badge
            variant="outline"
            className={cn("text-[10px]", statusCfg.className)}
          >
            {statusCfg.label}
          </Badge>
        </div>

        <p className="text-sm text-muted-foreground line-clamp-2">
          {aar.summary}
        </p>

        {/* Compliance badges */}
        <div className="flex flex-wrap gap-2">
          <Badge
            variant="outline"
            className={cn(
              "text-[10px]",
              aar.ra10121_compliant
                ? "border-risk-safe/30 bg-risk-safe/10 text-risk-safe"
                : "border-slate-500/30 bg-slate-500/10 text-slate-400",
            )}
          >
            <Shield className="h-3 w-3 mr-1" />
            RA 10121
          </Badge>
          <Badge
            variant="outline"
            className={cn(
              "text-[10px]",
              aar.submitted_to_ndrrmc
                ? "border-risk-safe/30 bg-risk-safe/10 text-risk-safe"
                : "border-slate-500/30 bg-slate-500/10 text-slate-400",
            )}
          >
            <Send className="h-3 w-3 mr-1" />
            NDRRMC
          </Badge>
          <Badge
            variant="outline"
            className={cn(
              "text-[10px]",
              aar.submitted_to_dilg
                ? "border-risk-safe/30 bg-risk-safe/10 text-risk-safe"
                : "border-slate-500/30 bg-slate-500/10 text-slate-400",
            )}
          >
            <Send className="h-3 w-3 mr-1" />
            DILG
          </Badge>
        </div>

        {/* Metrics row */}
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
          {aar.response_time_minutes != null && (
            <span>
              Response:{" "}
              <span className="text-foreground font-medium">
                {aar.response_time_minutes} min
              </span>
            </span>
          )}
          {aar.evacuation_time_minutes != null && (
            <span>
              Evacuation:{" "}
              <span className="text-foreground font-medium">
                {aar.evacuation_time_minutes} min
              </span>
            </span>
          )}
          {aar.warning_lead_time_minutes != null && (
            <span>
              Lead time:{" "}
              <span className="text-foreground font-medium">
                {aar.warning_lead_time_minutes} min
              </span>
            </span>
          )}
          {aar.prediction_accuracy != null && (
            <span>
              Accuracy:{" "}
              <span className="text-foreground font-medium">
                {(aar.prediction_accuracy * 100).toFixed(0)}%
              </span>
            </span>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

// ---------------------------------------------------------------------------
// Create AAR Dialog (enhanced with more fields)
// ---------------------------------------------------------------------------

function CreateAARDialog({
  open,
  onOpenChange,
  incident,
  onSubmit,
  submitting,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  incident: Incident;
  onSubmit: (data: Record<string, unknown>) => void;
  submitting: boolean;
}) {
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [timeline, setTimeline] = useState("");
  const [responseActions, setResponseActions] = useState("");
  const [resourcesDeployed, setResourcesDeployed] = useState("");
  const [lessonsLearned, setLessonsLearned] = useState("");
  const [recommendations, setRecommendations] = useState("");
  const [preparedBy, setPreparedBy] = useState("");
  const [responseTime, setResponseTime] = useState("");
  const [evacuationTime, setEvacuationTime] = useState("");
  const [warningLeadTime, setWarningLeadTime] = useState("");

  const handleSubmit = () => {
    const data: Record<string, unknown> = {
      title: title.trim(),
      summary: summary.trim(),
      prepared_by: preparedBy.trim() || undefined,
    };
    if (timeline.trim()) data.timeline = timeline.trim();
    if (responseActions.trim()) data.response_actions = responseActions.trim();
    if (resourcesDeployed.trim())
      data.resources_deployed = resourcesDeployed.trim();
    if (lessonsLearned.trim()) data.lessons_learned = lessonsLearned.trim();
    if (recommendations.trim()) data.recommendations = recommendations.trim();
    const rt = parseInt(responseTime);
    if (!isNaN(rt)) data.response_time_minutes = rt;
    const et = parseInt(evacuationTime);
    if (!isNaN(et)) data.evacuation_time_minutes = et;
    const wlt = parseInt(warningLeadTime);
    if (!isNaN(wlt)) data.warning_lead_time_minutes = wlt;
    onSubmit(data);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create After-Action Report</DialogTitle>
          <DialogDescription>
            Create a new AAR for "{incident.title}". Comply with RA 10121
            requirements.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Required fields */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 space-y-2">
              <Label htmlFor="aar-title">Report Title *</Label>
              <Input
                id="aar-title"
                placeholder="e.g. After-Action Report - Flash Flood October 2024"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="col-span-2 space-y-2">
              <Label htmlFor="aar-summary">Summary *</Label>
              <textarea
                id="aar-summary"
                className="flex min-h-24 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                placeholder="Brief overview of the incident response, key actions taken, and outcomes..."
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
              />
            </div>
          </div>

          <Separator className="opacity-30" />

          {/* Timeline & Response */}
          <div className="space-y-2">
            <Label htmlFor="aar-timeline">Incident Timeline</Label>
            <textarea
              id="aar-timeline"
              className="flex min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Chronological account of events..."
              value={timeline}
              onChange={(e) => setTimeline(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="aar-actions">Response Actions Taken</Label>
            <textarea
              id="aar-actions"
              className="flex min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Describe the actions taken during response..."
              value={responseActions}
              onChange={(e) => setResponseActions(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="aar-resources">Resources Deployed</Label>
            <Input
              id="aar-resources"
              placeholder="e.g. 3 rescue boats, 50 volunteers, 2 evacuation vehicles"
              value={resourcesDeployed}
              onChange={(e) => setResourcesDeployed(e.target.value)}
            />
          </div>

          <Separator className="opacity-30" />

          {/* Metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="aar-rt" className="text-xs">
                Response Time (min)
              </Label>
              <Input
                id="aar-rt"
                type="number"
                min="0"
                placeholder="0"
                value={responseTime}
                onChange={(e) => setResponseTime(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="aar-et" className="text-xs">
                Evacuation Time (min)
              </Label>
              <Input
                id="aar-et"
                type="number"
                min="0"
                placeholder="0"
                value={evacuationTime}
                onChange={(e) => setEvacuationTime(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="aar-wlt" className="text-xs">
                Warning Lead Time (min)
              </Label>
              <Input
                id="aar-wlt"
                type="number"
                min="0"
                placeholder="0"
                value={warningLeadTime}
                onChange={(e) => setWarningLeadTime(e.target.value)}
              />
            </div>
          </div>

          <Separator className="opacity-30" />

          {/* Lessons & Recommendations */}
          <div className="space-y-2">
            <Label htmlFor="aar-lessons">Lessons Learned</Label>
            <textarea
              id="aar-lessons"
              className="flex min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Key learnings from this incident..."
              value={lessonsLearned}
              onChange={(e) => setLessonsLearned(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="aar-recs">Recommendations</Label>
            <textarea
              id="aar-recs"
              className="flex min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Recommended improvements for future response..."
              value={recommendations}
              onChange={(e) => setRecommendations(e.target.value)}
            />
          </div>

          {/* Prepared by */}
          <div className="space-y-2">
            <Label htmlFor="aar-prepared">Prepared By</Label>
            <Input
              id="aar-prepared"
              placeholder="Officer name"
              value={preparedBy}
              onChange={(e) => setPreparedBy(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !title.trim() || !summary.trim()}
          >
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Create Report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Analytics Charts
// ---------------------------------------------------------------------------

function MonthlyFrequencyChart({
  data,
}: {
  data: { year: number; month: number; count: number }[];
}) {
  const chartData = data.map((d) => ({
    name: `${MONTH_NAMES[d.month - 1]} ${d.year}`,
    count: d.count,
  }));

  if (chartData.length === 0) return null;

  return (
    <GlassCard intensity="light" className="p-5">
      <h4 className="text-sm font-semibold mb-4">Monthly Incident Frequency</h4>
      <div className="h-55">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={CHART_MARGIN}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="count" name="Incidents" radius={[4, 4, 0, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={PRIMARY_HEX} opacity={0.8} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
}

function StageDwellTimeChart({ analytics }: { analytics: WorkflowAnalytics }) {
  const data = [
    {
      name: "Confirmation",
      minutes: analytics.avg_confirm_minutes ?? 0,
      color: RISK_HEX.alert,
    },
    {
      name: "Broadcast",
      minutes: analytics.avg_broadcast_minutes ?? 0,
      color: "#3B82F6",
    },
    {
      name: "Resolution",
      minutes: analytics.avg_resolve_minutes ?? 0,
      color: RISK_HEX.safe,
    },
  ].filter((d) => d.minutes > 0);

  if (data.length === 0) return null;

  return (
    <GlassCard intensity="light" className="p-5">
      <h4 className="text-sm font-semibold mb-4">
        Average Stage Dwell Time (minutes)
      </h4>
      <div className="h-55">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ ...CHART_MARGIN, left: 60 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              opacity={0.15}
              horizontal={false}
            />
            <XAxis
              type="number"
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={70}
            />
            <Tooltip content={<ChartTooltip unit=" min" />} />
            <Bar dataKey="minutes" name="Avg Time" radius={[0, 4, 4, 0]}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.color} opacity={0.8} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
}

// ---------------------------------------------------------------------------
// Analytics Panel
// ---------------------------------------------------------------------------

function AnalyticsPanel({
  analytics,
  loading,
}: {
  analytics: WorkflowAnalytics | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!analytics) {
    return (
      <GlassCard intensity="medium" className="p-8 text-center">
        <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground/40 mb-3" />
        <p className="text-muted-foreground">
          Analytics data is unavailable. Check your connection and try again.
        </p>
      </GlassCard>
    );
  }

  const statCards = [
    {
      label: "Total Incidents",
      value: analytics.total_incidents,
      icon: ClipboardCheck,
      color: PRIMARY_HEX,
    },
    {
      label: "Avg Confirmation",
      value:
        analytics.avg_confirm_minutes != null
          ? `${analytics.avg_confirm_minutes} min`
          : "-",
      icon: Timer,
      color: RISK_HEX.alert,
    },
    {
      label: "Avg Resolution",
      value:
        analytics.avg_resolve_minutes != null
          ? `${analytics.avg_resolve_minutes} min`
          : "-",
      icon: Clock,
      color: RISK_HEX.safe,
    },
    {
      label: "False Alarm Rate",
      value: `${(analytics.false_alarm_rate * 100).toFixed(1)}%`,
      icon: XCircle,
      color: RISK_HEX.critical,
    },
    {
      label: "AAR Completion",
      value: `${(analytics.aar_completion_rate * 100).toFixed(0)}%`,
      icon: FileText,
      color: PRIMARY_HEX,
    },
    {
      label: "Stalled Incidents",
      value: analytics.stalled_incidents,
      icon: AlertTriangle,
      color: analytics.stalled_incidents > 0 ? RISK_HEX.alert : RISK_HEX.safe,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <GlassCard key={card.label} intensity="light" className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon className="h-4 w-4" style={{ color: card.color }} />
                <span className="text-[11px] text-muted-foreground">
                  {card.label}
                </span>
              </div>
              <p className="text-xl font-bold">{card.value}</p>
            </GlassCard>
          );
        })}
      </div>

      {/* Compliance summary */}
      <GlassCard intensity="light" className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-4 w-4 text-primary" />
          <h4 className="text-sm font-semibold">RA 10121 Compliance Summary</h4>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Total AARs</p>
            <p className="text-lg font-bold">{analytics.total_aars}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Approved</p>
            <p className="text-lg font-bold text-risk-safe">
              {analytics.approved_aars}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">RA 10121 Compliant</p>
            <p className="text-lg font-bold text-primary">
              {analytics.compliant_aars}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Completion Rate</p>
            <p className="text-lg font-bold">
              {(analytics.aar_completion_rate * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MonthlyFrequencyChart data={analytics.monthly_frequency} />
        <StageDwellTimeChart analytics={analytics} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function WorkflowPage() {
  const { incidents, stats, loading, error, lastUpdated, refetch } =
    useIncidentsAdmin();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [transitioning, setTransitioning] = useState<number | null>(null);
  const [transitionDialogOpen, setTransitionDialogOpen] = useState(false);
  const [transitionTarget, setTransitionTarget] = useState<Incident | null>(
    null,
  );
  const [aarDialogOpen, setAarDialogOpen] = useState(false);
  const [creatingAAR, setCreatingAAR] = useState(false);
  const [activeTab, setActiveTab] = useState("pipeline");

  const {
    aars,
    loading: aarsLoading,
    refetch: refetchAARs,
  } = useAARs(selectedId);

  const {
    analytics,
    loading: analyticsLoading,
    refetch: refetchAnalytics,
  } = useWorkflowAnalytics();

  // Open transition dialog
  const openTransitionDialog = (incident: Incident) => {
    setTransitionTarget(incident);
    setTransitionDialogOpen(true);
  };

  // Transition handler via dialog
  const handleTransition = async (data: TransitionData) => {
    if (!transitionTarget) return;
    const next = NEXT_STATUS[transitionTarget.status];
    if (!next) return;

    setTransitioning(transitionTarget.id);
    try {
      await api.post(
        `${API_ENDPOINTS.lgu.incidents}/${transitionTarget.id}/transition`,
        { next_status: next, ...data },
      );
      setTransitionDialogOpen(false);
      setTransitionTarget(null);
      refetch();
      refetchAnalytics();
    } catch {
      /* errors handled by API client interceptor */
    } finally {
      setTransitioning(null);
    }
  };

  // Create AAR handler
  const handleCreateAAR = async (data: Record<string, unknown>) => {
    if (!selectedId) return;
    setCreatingAAR(true);
    try {
      await api.post(`${API_ENDPOINTS.lgu.incidents}/${selectedId}/aar`, data);
      setAarDialogOpen(false);
      refetchAARs();
      refetchAnalytics();
    } catch {
      /* errors handled by API client interceptor */
    } finally {
      setCreatingAAR(false);
    }
  };

  const selectedIncident = incidents.find((i) => i.id === selectedId) ?? null;

  // Select incident from pipeline and switch to incidents tab
  const handlePipelineSelect = (id: number) => {
    setSelectedId(id);
    setActiveTab("pipeline");
  };

  // inView refs
  const pipeRef = useRef<HTMLDivElement>(null);
  const pipeInView = useInView(pipeRef, { once: true, amount: 0.1 });
  const mainRef = useRef<HTMLDivElement>(null);
  const mainInView = useInView(mainRef, { once: true, amount: 0.05 });

  return (
    <div className="w-full space-y-0">
      {/* ── Header ── */}
      <div className="px-4 sm:px-6 lg:px-8 pt-6 pb-2">
        <Breadcrumb
          items={[
            { label: "Admin", href: "/admin" },
            { label: "Incident Workflow" },
          ]}
          className="mb-4"
        />
        <div className="flex items-center justify-end gap-3">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetch();
              refetchAnalytics();
            }}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* ═══ Pipeline Overview ═══ */}
      <section ref={pipeRef} className="bg-muted/30 py-8 px-4 sm:px-6 lg:px-8">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={pipeInView ? "show" : "hidden"}
        >
          <SectionHeading
            label="Pipeline Overview"
            title="Kanban Pipeline"
            subtitle="Incident distribution across workflow stages. Click any incident to view details."
          />

          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {!loading && error && (
            <motion.div variants={fadeUp}>
              <GlassCard intensity="medium" className="p-8 text-center">
                <WifiOff className="h-12 w-12 mx-auto text-risk-critical/40 mb-3" />
                <p className="text-muted-foreground font-medium">
                  Failed to load workflow data.
                </p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  Check your connection and click Refresh.
                </p>
              </GlassCard>
            </motion.div>
          )}

          {!loading && !error && incidents.length === 0 && (
            <motion.div variants={fadeUp}>
              <GlassCard intensity="medium" className="p-8 text-center">
                <CheckCircle2 className="h-12 w-12 mx-auto text-risk-safe/40 mb-3" />
                <p className="text-lg font-semibold text-risk-safe">
                  All Clear
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  No active incidents. Parañaque City is currently safe.
                </p>
              </GlassCard>
            </motion.div>
          )}

          {!loading && !error && incidents.length > 0 && (
            <motion.div variants={fadeUp}>
              <KanbanPipeline
                incidents={incidents}
                stats={stats}
                onSelectIncident={handlePipelineSelect}
              />
            </motion.div>
          )}
        </motion.div>
      </section>

      {/* ═══ Main Content Tabs ═══ */}
      <section
        ref={mainRef}
        className="bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={mainInView ? "show" : "hidden"}
        >
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="space-y-6"
          >
            <TabsList className="bg-muted/50">
              <TabsTrigger
                value="pipeline"
                className="data-[state=active]:bg-primary/15 data-[state=active]:text-primary"
              >
                <GitBranch className="h-4 w-4 mr-2" />
                Incidents
              </TabsTrigger>
              <TabsTrigger
                value="aars"
                className="data-[state=active]:bg-primary/15 data-[state=active]:text-primary"
              >
                <FileText className="h-4 w-4 mr-2" />
                After-Action Reports
              </TabsTrigger>
              <TabsTrigger
                value="analytics"
                className="data-[state=active]:bg-primary/15 data-[state=active]:text-primary"
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                Analytics
              </TabsTrigger>
            </TabsList>

            {/* ─── Incidents Tab ─── */}
            <TabsContent value="pipeline" className="space-y-4">
              <SectionHeading
                label="All Incidents"
                title="Incident Management"
                subtitle="Click an incident to view details. Use the transition button to advance through the workflow."
              />

              {loading && (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              )}

              {!loading && error && (
                <GlassCard intensity="medium" className="p-8 text-center">
                  <WifiOff className="h-12 w-12 mx-auto text-risk-critical/40 mb-3" />
                  <p className="text-muted-foreground">
                    Failed to load incidents. Check your connection.
                  </p>
                </GlassCard>
              )}

              {!loading && !error && incidents.length === 0 && (
                <GlassCard intensity="medium" className="p-8 text-center">
                  <CheckCircle2 className="h-12 w-12 mx-auto text-risk-safe/40 mb-3" />
                  <p className="text-lg font-semibold text-risk-safe">
                    All Clear
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    No incidents in the system. The city is currently safe.
                  </p>
                </GlassCard>
              )}

              {!loading && !error && incidents.length > 0 && (
                <motion.div variants={fadeUp} className="space-y-2">
                  {incidents.map((inc) => (
                    <IncidentRow
                      key={inc.id}
                      incident={inc}
                      selected={selectedId === inc.id}
                      onSelect={() =>
                        setSelectedId(inc.id === selectedId ? null : inc.id)
                      }
                      onAdvance={() => openTransitionDialog(inc)}
                      transitioning={transitioning}
                    />
                  ))}
                </motion.div>
              )}

              {/* Selected incident detail */}
              {selectedIncident && (
                <motion.div variants={fadeUp}>
                  <IncidentDetail
                    incident={selectedIncident}
                    onTransition={() => openTransitionDialog(selectedIncident)}
                    transitioning={transitioning}
                  />
                </motion.div>
              )}
            </TabsContent>

            {/* ─── AARs Tab ─── */}
            <TabsContent value="aars" className="space-y-4">
              <div className="flex items-center justify-between">
                <SectionHeading
                  label="Post-Incident"
                  title="After-Action Reports"
                  subtitle={
                    selectedIncident
                      ? `Viewing AARs for "${selectedIncident.title}"`
                      : "Select an incident in the Incidents tab first."
                  }
                />
                {selectedIncident && (
                  <Button
                    size="sm"
                    className="bg-primary hover:bg-primary/90"
                    onClick={() => setAarDialogOpen(true)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    New AAR
                  </Button>
                )}
              </div>

              {/* AAR completion rate bar */}
              {analytics && analytics.total_aars > 0 && (
                <GlassCard intensity="light" className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-muted-foreground">
                      AAR Completion Rate
                    </span>
                    <span className="text-sm font-bold">
                      {(analytics.aar_completion_rate * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted/50 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{
                        width: `${Math.min(analytics.aar_completion_rate * 100, 100)}%`,
                      }}
                    />
                  </div>
                  <div className="flex justify-between mt-2 text-[11px] text-muted-foreground">
                    <span>{analytics.total_aars} total AARs</span>
                    <span>{analytics.approved_aars} approved</span>
                    <span>{analytics.compliant_aars} RA 10121 compliant</span>
                  </div>
                </GlassCard>
              )}

              {!selectedIncident && (
                <GlassCard intensity="medium" className="p-8 text-center">
                  <ClipboardCheck className="h-12 w-12 mx-auto text-muted-foreground/40 mb-3" />
                  <p className="text-muted-foreground">
                    Select an incident from the Incidents tab to view or create
                    after-action reports.
                  </p>
                </GlassCard>
              )}

              {selectedIncident && aarsLoading && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              )}

              {selectedIncident && !aarsLoading && aars.length === 0 && (
                <GlassCard intensity="medium" className="p-8 text-center">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground/40 mb-3" />
                  <p className="text-muted-foreground">
                    No after-action reports yet for this incident.
                  </p>
                  <p className="text-xs text-muted-foreground/60 mt-1">
                    RA 10121 requires an AAR within 48 hours of resolution.
                  </p>
                </GlassCard>
              )}

              {selectedIncident && !aarsLoading && aars.length > 0 && (
                <motion.div variants={fadeUp} className="space-y-4">
                  {aars.map((aar) => (
                    <AARCard key={aar.id} aar={aar} />
                  ))}
                </motion.div>
              )}
            </TabsContent>

            {/* ─── Analytics Tab ─── */}
            <TabsContent value="analytics" className="space-y-4">
              <SectionHeading
                label="Performance"
                title="Workflow Analytics"
                subtitle="Key performance metrics, stage dwell times, and compliance tracking."
              />
              <AnalyticsPanel
                analytics={analytics}
                loading={analyticsLoading}
              />
            </TabsContent>
          </Tabs>
        </motion.div>
      </section>

      {/* ── Transition Dialog ── */}
      {transitionTarget && (
        <TransitionDialog
          open={transitionDialogOpen}
          onOpenChange={(v) => {
            setTransitionDialogOpen(v);
            if (!v) setTransitionTarget(null);
          }}
          incident={transitionTarget}
          onConfirm={handleTransition}
          submitting={transitioning === transitionTarget.id}
        />
      )}

      {/* ── Create AAR Dialog ── */}
      {selectedIncident && (
        <CreateAARDialog
          open={aarDialogOpen}
          onOpenChange={setAarDialogOpen}
          incident={selectedIncident}
          onSubmit={handleCreateAAR}
          submitting={creatingAAR}
        />
      )}
    </div>
  );
}
