/**
 * Incidents Page - LGU Incident Logging & Workflow
 *
 * Displays all flood incidents, provides filtering, creation, and
 * workflow state transitions (Alert → LGU Confirmed → Broadcast → Resolved → Closed).
 * Accessible to operator and admin roles.
 */

import { formatDistanceToNow } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Clock,
  Filter,
  Loader2,
  MapPin,
  Plus,
  Radio,
  RefreshCw,
  Search,
  Shield,
  Siren,
  Users,
  WifiOff,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";

import type {
  Incident,
  IncidentSource,
  IncidentStats,
  IncidentStatus,
  IncidentType,
} from "@/types";
import { LGU_WORKFLOW_STEPS } from "@/types";

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PARANAQUE_BARANGAYS = [
  "Baclaran",
  "BF Homes",
  "Don Bosco",
  "Don Galo",
  "La Huerta",
  "Marcelo Green Village",
  "Merville",
  "Moonwalk",
  "San Antonio",
  "San Dionisio",
  "San Isidro",
  "San Martin de Porres",
  "Santo Niño",
  "Sun Valley",
  "Tambo",
  "Vitalez",
] as const;

const RISK_LABELS: Record<number, { label: string; className: string }> = {
  0: {
    label: "Safe",
    className: "border-risk-safe/30 bg-risk-safe/10 text-risk-safe",
  },
  1: {
    label: "Alert",
    className: "border-risk-alert/30 bg-risk-alert/10 text-risk-alert",
  },
  2: {
    label: "Critical",
    className: "border-risk-critical/30 bg-risk-critical/10 text-risk-critical",
  },
};

const STATUS_CONFIG: Record<
  IncidentStatus,
  { label: string; className: string; icon: React.ElementType }
> = {
  alert_raised: {
    label: "Alert Raised",
    className: "border-risk-alert/30 bg-risk-alert/10 text-risk-alert",
    icon: Siren,
  },
  lgu_confirmed: {
    label: "LGU Confirmed",
    className: "border-blue-500/30 bg-blue-500/10 text-blue-400",
    icon: Shield,
  },
  broadcast_sent: {
    label: "Broadcast Sent",
    className: "border-purple-500/30 bg-purple-500/10 text-purple-400",
    icon: Radio,
  },
  resolved: {
    label: "Resolved",
    className: "border-risk-safe/30 bg-risk-safe/10 text-risk-safe",
    icon: CheckCircle2,
  },
  closed: {
    label: "Closed",
    className: "border-slate-500/30 bg-slate-500/10 text-slate-400",
    icon: CheckCircle2,
  },
};

const NEXT_STATUS: Partial<Record<IncidentStatus, IncidentStatus>> = {
  alert_raised: "lgu_confirmed",
  lgu_confirmed: "broadcast_sent",
  broadcast_sent: "resolved",
  resolved: "closed",
};

const INCIDENT_TYPE_LABELS: Record<IncidentType, string> = {
  flood: "Flood",
  storm_surge: "Storm Surge",
  landslide: "Landslide",
  flash_flood: "Flash Flood",
};

/** Auto-refresh interval for incident data (30 seconds) */
const AUTO_REFRESH_MS = 30_000;

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

function useIncidents(params: {
  page: number;
  limit: number;
  status?: IncidentStatus;
  risk_level?: number;
  barangay?: string;
  search?: string;
}) {
  const [data, setData] = useState<{
    incidents: Incident[];
    total: number;
    pages: number;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchIncidents = useCallback(async () => {
    setIsLoading(true);
    setIsError(false);
    try {
      const query = new URLSearchParams();
      query.set("offset", String((params.page - 1) * params.limit));
      query.set("limit", String(params.limit));
      if (params.status) query.set("status", params.status);
      if (params.risk_level !== undefined)
        query.set("risk_level", String(params.risk_level));
      if (params.barangay) query.set("barangay", params.barangay);
      if (params.search) query.set("search", params.search);

      const res = await api.get<{
        data?: Incident[];
        pagination?: { total: number; limit: number; offset: number };
      }>(`${API_ENDPOINTS.lgu.incidents}?${query}`);
      const incidents = Array.isArray(res.data) ? res.data : [];
      const total = res.pagination?.total ?? incidents.length;
      setData({
        incidents,
        total,
        pages: Math.max(1, Math.ceil(total / params.limit)),
      });
      setLastUpdated(new Date());
    } catch {
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  }, [
    params.page,
    params.limit,
    params.status,
    params.risk_level,
    params.barangay,
    params.search,
  ]);

  // Fetch on mount and when params change
  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  // Auto-refresh
  useEffect(() => {
    const id = setInterval(fetchIncidents, AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, [fetchIncidents]);

  return { data, isLoading, isError, lastUpdated, refetch: fetchIncidents };
}

function useIncidentStats() {
  const [stats, setStats] = useState<IncidentStats | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get<{
        data?: IncidentStats;
      }>(API_ENDPOINTS.lgu.incidentStats);
      setStats(res.data ?? null);
      setLastUpdated(new Date());
    } catch {
      /* tolerate stats failure */
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch on mount is intentional
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    const id = setInterval(fetchStats, AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, [fetchStats]);

  return { stats, lastUpdated, refetch: fetchStats };
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Stats summary cards - color-coded by urgency */
function StatsRow({ stats }: { stats: IncidentStats | null }) {
  if (!stats) return null;

  const cards = [
    {
      label: "Active Incidents",
      value: stats.total_active,
      icon: Siren,
      accent: "text-risk-critical",
      barColor: "bg-linear-to-r from-risk-critical/60 to-risk-critical/20",
    },
    {
      label: "Alert Raised",
      value: stats.by_status?.alert_raised ?? 0,
      icon: Siren,
      accent: "text-risk-alert",
      barColor: "bg-linear-to-r from-risk-alert/60 to-risk-alert/20",
    },
    {
      label: "LGU Confirmed",
      value: stats.by_status?.lgu_confirmed ?? 0,
      icon: Shield,
      accent: "text-blue-400",
      barColor: "bg-linear-to-r from-blue-500/60 to-blue-500/20",
    },
    {
      label: "Resolved",
      value: stats.by_status?.resolved ?? 0,
      icon: CheckCircle2,
      accent: "text-risk-safe",
      barColor: "bg-linear-to-r from-risk-safe/60 to-risk-safe/20",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <GlassCard
          key={c.label}
          intensity="light"
          className="relative overflow-hidden"
        >
          <div className={cn("absolute inset-x-0 top-0 h-1", c.barColor)} />
          <div className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center shrink-0">
              <c.icon className={cn("h-5 w-5", c.accent)} />
            </div>
            <div>
              <p className="text-2xl font-bold">{c.value}</p>
              <p className="text-xs text-muted-foreground">{c.label}</p>
            </div>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}

/** Workflow pipeline visualization for a single incident */
function WorkflowPipeline({
  currentStatus,
}: {
  currentStatus: IncidentStatus;
}) {
  const currentIdx = LGU_WORKFLOW_STEPS.findIndex(
    (s) => s.status === currentStatus,
  );

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {LGU_WORKFLOW_STEPS.map((step, i) => {
        const isComplete = i < currentIdx;
        const isCurrent = i === currentIdx;
        return (
          <div key={step.status} className="flex items-center gap-1">
            <div
              className={cn(
                "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-medium transition-all",
                isComplete &&
                  "bg-risk-safe/15 text-risk-safe ring-1 ring-risk-safe/30",
                isCurrent &&
                  "bg-primary/15 text-primary ring-1 ring-primary/40",
                !isComplete &&
                  !isCurrent &&
                  "bg-muted/40 text-muted-foreground/50",
              )}
            >
              {isComplete && <CheckCircle2 className="h-3 w-3" />}
              {step.label}
            </div>
            {i < LGU_WORKFLOW_STEPS.length - 1 && (
              <ChevronRight className="h-3 w-3 text-muted-foreground/40 shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Single incident card with detail view link */
function IncidentCard({
  incident,
  onTransition,
  transitioning,
  onViewDetail,
}: {
  incident: Incident;
  onTransition: (id: number, next: IncidentStatus) => void;
  transitioning: number | null;
  onViewDetail: (incident: Incident) => void;
}) {
  const risk = (RISK_LABELS[incident.risk_level] ?? RISK_LABELS[0])!;
  const status = STATUS_CONFIG[incident.status]!;
  const next = NEXT_STATUS[incident.status];
  const StatusIcon = status.icon;

  return (
    <GlassCard intensity="medium" className="relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary/60 to-primary/20" />
      <div className="p-5 space-y-4">
        {/* Title row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-10 w-10 rounded-xl bg-linear-to-br from-primary/20 to-primary/10 ring-1 ring-primary/30 flex items-center justify-center shrink-0">
              <StatusIcon className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold tracking-tight truncate">
                {incident.title}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                <MapPin className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">
                  {incident.barangay}
                </span>
                <span className="text-xs text-muted-foreground/50">·</span>
                <span className="text-xs text-muted-foreground capitalize">
                  {INCIDENT_TYPE_LABELS[incident.incident_type]}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Badge
              variant="outline"
              className={cn("text-[10px]", risk.className)}
            >
              {risk.label}
            </Badge>
            <Badge
              variant="outline"
              className={cn("text-[10px]", status.className)}
            >
              {status.label}
            </Badge>
          </div>
        </div>

        {/* Description */}
        {incident.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {incident.description}
          </p>
        )}

        {/* Workflow pipeline */}
        <WorkflowPipeline currentStatus={incident.status} />

        {/* Impact stats row */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {incident.affected_families > 0 && (
            <span>
              Affected:{" "}
              <span className="text-foreground font-medium">
                {incident.affected_families}
              </span>{" "}
              families
            </span>
          )}
          {incident.evacuated_families > 0 && (
            <span>
              Evacuated:{" "}
              <span className="text-foreground font-medium">
                {incident.evacuated_families}
              </span>
            </span>
          )}
          {incident.estimated_damage != null &&
            incident.estimated_damage > 0 && (
              <span>
                Damage:{" "}
                <span className="text-foreground font-medium">
                  ₱{incident.estimated_damage.toLocaleString()}
                </span>
              </span>
            )}
        </div>

        {/* Footer - date + actions */}
        <div className="flex items-center justify-between pt-1">
          <span className="text-[10px] text-muted-foreground">
            {formatRelativeTime(incident.created_at)}
          </span>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs hover:bg-primary/10 hover:text-primary"
              onClick={() => onViewDetail(incident)}
            >
              Details
              <ChevronRight className="h-3 w-3 ml-1" />
            </Button>
            {next && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs border-primary/30 hover:bg-primary/10 hover:text-primary"
                onClick={() => onTransition(incident.id, next)}
                disabled={transitioning === incident.id}
              >
                {transitioning === incident.id ? (
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                ) : (
                  <ArrowRight className="h-3 w-3 mr-1" />
                )}
                {STATUS_CONFIG[next].label}
              </Button>
            )}
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

/** Incident detail side panel */
function IncidentDetailPanel({
  incident,
  open,
  onClose,
}: {
  incident: Incident | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!incident) return null;

  const risk = (RISK_LABELS[incident.risk_level] ?? RISK_LABELS[0])!;
  const status = STATUS_CONFIG[incident.status]!;

  const timelineEntries: {
    label: string;
    time: string | null;
    actor?: string | null;
  }[] = [
    {
      label: "Alert Raised",
      time: incident.created_at,
      actor: incident.created_by,
    },
    {
      label: "LGU Confirmed",
      time: incident.confirmed_at,
      actor: incident.confirmed_by,
    },
    { label: "Broadcast Sent", time: incident.broadcast_sent_at },
    {
      label: "Resolved",
      time: incident.resolved_at,
      actor: incident.resolved_by,
    },
  ];

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="pb-4">
          <SheetTitle>{incident.title}</SheetTitle>
          <SheetDescription>
            Incident #{incident.id} - {incident.barangay}
          </SheetDescription>
          <div className="flex items-center gap-2 pt-1">
            <Badge variant="outline" className={cn("text-xs", risk.className)}>
              {risk.label}
            </Badge>
            <Badge
              variant="outline"
              className={cn("text-xs", status.className)}
            >
              {status.label}
            </Badge>
            <Badge variant="outline" className="text-xs capitalize">
              {INCIDENT_TYPE_LABELS[incident.incident_type]}
            </Badge>
          </div>
        </SheetHeader>

        <Separator />

        <div className="space-y-6 py-4">
          {incident.description && (
            <div>
              <h4 className="text-sm font-semibold mb-1">Description</h4>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {incident.description}
              </p>
            </div>
          )}

          {/* Workflow Timeline */}
          <div>
            <h4 className="text-sm font-semibold mb-3">Workflow Timeline</h4>
            <div className="space-y-3">
              {timelineEntries.map((entry) => {
                const completed = !!entry.time;
                return (
                  <div key={entry.label} className="flex items-start gap-3">
                    <div
                      className={cn(
                        "mt-0.5 h-5 w-5 rounded-full flex items-center justify-center shrink-0",
                        completed
                          ? "bg-risk-safe/20 text-risk-safe"
                          : "bg-muted/40 text-muted-foreground/40",
                      )}
                    >
                      {completed ? (
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      ) : (
                        <Clock className="h-3 w-3" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p
                        className={cn(
                          "text-sm font-medium",
                          !completed && "text-muted-foreground/50",
                        )}
                      >
                        {entry.label}
                      </p>
                      {completed && entry.time && (
                        <p className="text-xs text-muted-foreground">
                          {new Date(entry.time).toLocaleString()}
                          {entry.actor && ` - by ${entry.actor}`}
                        </p>
                      )}
                      {!completed && (
                        <p className="text-xs text-muted-foreground/40">
                          Pending
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <Separator />

          {/* Impact Metrics */}
          <div>
            <h4 className="text-sm font-semibold mb-3">Impact Metrics</h4>
            <div className="grid grid-cols-2 gap-3">
              <MetricItem
                icon={Users}
                label="Affected Families"
                value={incident.affected_families}
              />
              <MetricItem
                icon={Users}
                label="Evacuated Families"
                value={incident.evacuated_families}
              />
              <MetricItem
                icon={Users}
                label="Casualties"
                value={incident.casualties}
              />
              {incident.estimated_damage != null && (
                <MetricItem
                  label="Estimated Damage"
                  value={`₱${incident.estimated_damage.toLocaleString()}`}
                />
              )}
            </div>
          </div>

          {incident.broadcast_channels && (
            <>
              <Separator />
              <div>
                <h4 className="text-sm font-semibold mb-1">
                  Broadcast Channels
                </h4>
                <p className="text-sm text-muted-foreground">
                  {incident.broadcast_channels}
                </p>
              </div>
            </>
          )}

          {incident.location_detail && (
            <>
              <Separator />
              <div>
                <h4 className="text-sm font-semibold mb-1">Location Detail</h4>
                <p className="text-sm text-muted-foreground">
                  {incident.location_detail}
                </p>
              </div>
            </>
          )}

          <Separator />
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Source</span>
            <Badge variant="outline" className="text-xs capitalize">
              {incident.source.replace("_", " ")}
            </Badge>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Created</span>
            <span className="text-xs">
              {new Date(incident.created_at).toLocaleString()}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Last Updated</span>
            <span className="text-xs">
              {new Date(incident.updated_at).toLocaleString()}
            </span>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function MetricItem({
  icon: Icon,
  label,
  value,
}: {
  icon?: React.ElementType;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg bg-muted/30 p-3">
      <div className="flex items-center gap-1.5 mb-1">
        {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

function formatRelativeTime(dateString: string): string {
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true });
  } catch {
    return "Unknown time";
  }
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function IncidentsPage() {
  // Filter state
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | undefined>(
    undefined,
  );
  const [riskFilter, setRiskFilter] = useState<number | undefined>(undefined);
  const [barangayFilter, setBarangayFilter] = useState<string | undefined>(
    undefined,
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [transitioning, setTransitioning] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  // Detail panel
  const [detailIncident, setDetailIncident] = useState<Incident | null>(null);

  // Create form state
  const [newTitle, setNewTitle] = useState("");
  const [newBarangay, setNewBarangay] = useState("");
  const [newType, setNewType] = useState<IncidentType>("flood");
  const [newRisk, setNewRisk] = useState<number>(1);
  const [newDescription, setNewDescription] = useState("");
  const [newAffectedFamilies, setNewAffectedFamilies] = useState("");
  const [newOfficer, setNewOfficer] = useState("");
  const [creating, setCreating] = useState(false);

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Data hooks
  const { data, isLoading, isError, lastUpdated, refetch } = useIncidents({
    page,
    limit: 20,
    status: statusFilter,
    risk_level: riskFilter,
    barangay: barangayFilter,
    search: debouncedSearch || undefined,
  });
  const { stats, refetch: refetchStats } = useIncidentStats();

  // Workflow transition handler
  const handleTransition = async (id: number, nextStatus: IncidentStatus) => {
    setTransitioning(id);
    try {
      await api.post(`${API_ENDPOINTS.lgu.incidents}/${id}/transition`, {
        next_status: nextStatus,
        actor: "operator",
      });
      refetch();
      refetchStats();
    } catch {
      /* toast error in prod */
    } finally {
      setTransitioning(null);
    }
  };

  // Create incident handler
  const handleCreate = async () => {
    if (!newTitle.trim() || !newBarangay) return;
    setCreating(true);
    try {
      await api.post(API_ENDPOINTS.lgu.incidents, {
        title: newTitle.trim(),
        barangay: newBarangay,
        incident_type: newType,
        risk_level: newRisk,
        description: newDescription.trim() || undefined,
        affected_families: newAffectedFamilies
          ? parseInt(newAffectedFamilies, 10)
          : 0,
        confirmed_by: newOfficer.trim() || undefined,
        source: "manual" as IncidentSource,
      });
      setCreateOpen(false);
      setNewTitle("");
      setNewBarangay("");
      setNewType("flood");
      setNewRisk(1);
      setNewDescription("");
      setNewAffectedFamilies("");
      setNewOfficer("");
      refetch();
      refetchStats();
    } catch {
      /* toast error in prod */
    } finally {
      setCreating(false);
    }
  };

  // Reset filters
  const resetFilters = () => {
    setStatusFilter(undefined);
    setRiskFilter(undefined);
    setBarangayFilter(undefined);
    setSearchQuery("");
    setPage(1);
  };

  const hasFilters =
    statusFilter || riskFilter !== undefined || barangayFilter || searchQuery;

  // inView refs
  const statsRef = useRef<HTMLDivElement>(null);
  const statsInView = useInView(statsRef, { once: true, amount: 0.1 });
  const filterRef = useRef<HTMLDivElement>(null);
  const filterInView = useInView(filterRef, { once: true, amount: 0.1 });
  const listRef = useRef<HTMLDivElement>(null);
  const listInView = useInView(listRef, { once: true, amount: 0.05 });

  // Manual refresh handler
  const handleManualRefresh = () => {
    refetch();
    refetchStats();
  };

  return (
    <div className="space-y-0">
      {/* ── Header ── */}
      <div className="w-full px-6 pt-6 pb-2">
        <PageHeader
          icon={ClipboardList}
          title="Incident Management"
          subtitle="Log, track, and manage flood incidents through the LGU workflow pipeline"
          actions={
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleManualRefresh}
                  className="border border-white/20 text-white hover:bg-white/10 hover:text-white"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
                {lastUpdated && (
                  <span className="text-[10px] text-white/50 hidden sm:inline">
                    Updated {formatRelativeTime(lastUpdated.toISOString())}
                  </span>
                )}
              </div>
              <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" className="bg-primary hover:bg-primary/90">
                    <Plus className="h-4 w-4 mr-2" />
                    New Incident
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-lg">
                  <DialogHeader>
                    <DialogTitle>Log New Incident</DialogTitle>
                    <DialogDescription>
                      Create a new flood incident record. It will start in
                      &ldquo;Alert Raised&rdquo; status.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-2">
                    <div className="space-y-2">
                      <Label htmlFor="inc-title">Title *</Label>
                      <Input
                        id="inc-title"
                        placeholder="e.g. Flash flood - Don Galo area"
                        value={newTitle}
                        onChange={(e) => setNewTitle(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="inc-desc">Description</Label>
                      <textarea
                        id="inc-desc"
                        rows={3}
                        placeholder="Describe the incident, affected areas, and any immediate observations…"
                        value={newDescription}
                        onChange={(e) => setNewDescription(e.target.value)}
                        className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="inc-barangay">Barangay *</Label>
                      <Select
                        value={newBarangay}
                        onValueChange={setNewBarangay}
                      >
                        <SelectTrigger id="inc-barangay">
                          <SelectValue placeholder="Select barangay" />
                        </SelectTrigger>
                        <SelectContent>
                          {PARANAQUE_BARANGAYS.map((b) => (
                            <SelectItem key={b} value={b}>
                              {b}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="inc-type">Type</Label>
                        <Select
                          value={newType}
                          onValueChange={(v) => setNewType(v as IncidentType)}
                        >
                          <SelectTrigger id="inc-type">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="flood">Flood</SelectItem>
                            <SelectItem value="storm_surge">
                              Storm Surge
                            </SelectItem>
                            <SelectItem value="landslide">Landslide</SelectItem>
                            <SelectItem value="flash_flood">
                              Flash Flood
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="inc-risk">Risk Level</Label>
                        <Select
                          value={String(newRisk)}
                          onValueChange={(v) => setNewRisk(Number(v))}
                        >
                          <SelectTrigger id="inc-risk">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="0">Safe</SelectItem>
                            <SelectItem value="1">Alert</SelectItem>
                            <SelectItem value="2">Critical</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="inc-families">Affected Families</Label>
                        <Input
                          id="inc-families"
                          type="number"
                          min="0"
                          placeholder="0"
                          value={newAffectedFamilies}
                          onChange={(e) =>
                            setNewAffectedFamilies(e.target.value)
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="inc-officer">Reporting Officer</Label>
                        <Input
                          id="inc-officer"
                          placeholder="Officer name"
                          value={newOfficer}
                          onChange={(e) => setNewOfficer(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setCreateOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleCreate}
                      disabled={creating || !newTitle.trim() || !newBarangay}
                    >
                      {creating && (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      )}
                      Create Incident
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          }
        />
      </div>

      {/* ═══ Stats Row ═══ */}
      <section ref={statsRef} className="bg-muted/30 py-8 w-full px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={statsInView ? "show" : "hidden"}
        >
          <motion.div variants={fadeUp}>
            <StatsRow stats={stats} />
          </motion.div>
        </motion.div>
      </section>

      {/* ═══ Filters ═══ */}
      <section ref={filterRef} className="bg-background py-8 w-full px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={filterInView ? "show" : "hidden"}
        >
          <SectionHeading
            label="Filter Incidents"
            title="Search & Filter"
            subtitle="Narrow down incidents by status, risk level, or barangay."
          />
          <motion.div variants={fadeUp}>
            <GlassCard intensity="medium" className="overflow-hidden">
              <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-xl bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
                      <Filter className="h-5 w-5 text-primary" />
                    </div>
                    <h3 className="text-lg font-semibold">Filters</h3>
                  </div>
                  {hasFilters && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={resetFilters}
                      className="hover:bg-primary/10 hover:text-primary"
                    >
                      Reset
                    </Button>
                  )}
                </div>

                {/* Search bar */}
                <div className="relative mb-4">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search incidents by title, barangay, or description…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {/* Status */}
                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select
                      value={statusFilter ?? "all"}
                      onValueChange={(v) => {
                        setStatusFilter(
                          v === "all" ? undefined : (v as IncidentStatus),
                        );
                        setPage(1);
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                        {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                          <SelectItem key={k} value={k}>
                            {v.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {/* Risk Level */}
                  <div className="space-y-2">
                    <Label>Risk Level</Label>
                    <Select
                      value={
                        riskFilter !== undefined ? String(riskFilter) : "all"
                      }
                      onValueChange={(v) => {
                        setRiskFilter(v === "all" ? undefined : Number(v));
                        setPage(1);
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Levels</SelectItem>
                        <SelectItem value="0">Safe</SelectItem>
                        <SelectItem value="1">Alert</SelectItem>
                        <SelectItem value="2">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {/* Barangay */}
                  <div className="space-y-2">
                    <Label>Barangay</Label>
                    <Select
                      value={barangayFilter ?? "all"}
                      onValueChange={(v) => {
                        setBarangayFilter(v === "all" ? undefined : v);
                        setPage(1);
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Barangays</SelectItem>
                        {PARANAQUE_BARANGAYS.map((b) => (
                          <SelectItem key={b} value={b}>
                            {b}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        </motion.div>
      </section>

      {/* ═══ Incident List ═══ */}
      <section ref={listRef} className="bg-muted/30 py-12 w-full px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={listInView ? "show" : "hidden"}
        >
          <SectionHeading
            label="Incident Log"
            title="All Incidents"
            subtitle={
              isLoading && !data
                ? "Loading…"
                : `${data?.total ?? 0} incident${(data?.total ?? 0) !== 1 ? "s" : ""} found`
            }
          />

          {isLoading && !data && (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {isError && (
            <GlassCard intensity="medium" className="p-8 text-center">
              <WifiOff className="h-12 w-12 mx-auto text-risk-critical/40 mb-3" />
              <p className="text-lg font-semibold mb-1">
                Failed to Load Incidents
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                The incident data could not be retrieved. This may be a server
                or network issue.
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </GlassCard>
          )}

          {!isLoading && !isError && data && (
            <div className="space-y-4">
              {data.incidents.length === 0 ? (
                <GlassCard intensity="medium" className="p-8 text-center">
                  {hasFilters ? (
                    <>
                      <Filter className="h-12 w-12 mx-auto text-muted-foreground/40 mb-3" />
                      <p className="text-lg font-semibold mb-1">
                        No Matching Incidents
                      </p>
                      <p className="text-sm text-muted-foreground mb-4">
                        No incidents match the current filters. Try broadening
                        your search criteria.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={resetFilters}
                      >
                        Clear Filters
                      </Button>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-12 w-12 mx-auto text-risk-safe/40 mb-3" />
                      <p className="text-lg font-semibold mb-1">
                        All Clear - No Active Incidents
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Parañaque City currently has no recorded flood
                        incidents. The system is monitoring continuously.
                      </p>
                    </>
                  )}
                </GlassCard>
              ) : (
                data.incidents.map((inc) => (
                  <motion.div key={inc.id} variants={fadeUp}>
                    <IncidentCard
                      incident={inc}
                      onTransition={handleTransition}
                      transitioning={transitioning}
                      onViewDetail={setDetailIncident}
                    />
                  </motion.div>
                ))
              )}

              {/* Pagination */}
              {(data.pages ?? 1) > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {data.pages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= (data.pages ?? 1)}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          )}
        </motion.div>
      </section>

      {/* ═══ Incident Detail Panel ═══ */}
      <IncidentDetailPanel
        incident={detailIncident}
        open={!!detailIncident}
        onClose={() => setDetailIncident(null)}
      />
    </div>
  );
}
