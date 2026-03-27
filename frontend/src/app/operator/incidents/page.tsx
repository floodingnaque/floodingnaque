/**
 * Operator - Active Incidents Page
 *
 * Full-page incident management with Kanban pipeline,
 * searchable incident list, and new incident form.
 */

import {
  AlertTriangle,
  ArrowRight,
  ChevronRight,
  Clock,
  Loader2,
  MapPin,
  Plus,
  Search,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  useAdvanceIncident,
  useCreateIncident,
  useIncidents,
  useIncidentStats,
} from "@/features/operator";
import { cn } from "@/lib/utils";
import type { Incident, IncidentStatus, IncidentType } from "@/types/api/lgu";

const PARANAQUE_BARANGAYS = [
  "Baclaran",
  "BF Homes",
  "Don Bosco",
  "Don Galo",
  "La Huerta",
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
  "Sucat",
];

const PIPELINE_STAGES: {
  key: IncidentStatus;
  label: string;
  color: string;
  textColor: string;
}[] = [
  {
    key: "alert_raised",
    label: "Alert Raised",
    color: "bg-red-500",
    textColor: "text-red-700",
  },
  {
    key: "lgu_confirmed",
    label: "LGU Confirmed",
    color: "bg-amber-500",
    textColor: "text-amber-700",
  },
  {
    key: "broadcast_sent",
    label: "Broadcast Sent",
    color: "bg-blue-500",
    textColor: "text-blue-700",
  },
  {
    key: "resolved",
    label: "Resolved",
    color: "bg-emerald-500",
    textColor: "text-emerald-700",
  },
  {
    key: "closed",
    label: "Closed",
    color: "bg-gray-500",
    textColor: "text-gray-700",
  },
];

const STATUS_BADGE: Record<IncidentStatus, string> = {
  alert_raised: "bg-red-500/10 text-red-700 border-red-300",
  lgu_confirmed: "bg-amber-500/10 text-amber-700 border-amber-300",
  broadcast_sent: "bg-blue-500/10 text-blue-700 border-blue-300",
  resolved: "bg-emerald-500/10 text-emerald-700 border-emerald-300",
  closed: "bg-gray-500/10 text-gray-700 border-gray-300",
};

const NEXT_STATUS: Partial<Record<IncidentStatus, string>> = {
  alert_raised: "Confirm",
  lgu_confirmed: "Send Broadcast",
  broadcast_sent: "Resolve",
  resolved: "Close",
};

function IncidentCard({
  incident,
  onAdvance,
  isAdvancing,
}: {
  incident: Incident;
  onAdvance: (id: number) => void;
  isAdvancing: boolean;
}) {
  const nextAction = NEXT_STATUS[incident.status];
  return (
    <div className="flex items-start justify-between gap-4 p-4 border rounded-lg hover:bg-muted/30 transition-colors">
      <div className="space-y-1 min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm truncate">{incident.title}</span>
          <Badge
            variant="outline"
            className={cn("text-[10px] px-1.5", STATUS_BADGE[incident.status])}
          >
            {PIPELINE_STAGES.find((s) => s.key === incident.status)?.label}
          </Badge>
          <Badge variant="secondary" className="text-[10px]">
            {incident.incident_type.replace("_", " ")}
          </Badge>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {incident.barangay}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {new Date(incident.created_at).toLocaleDateString("en-PH", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          {incident.affected_families > 0 && (
            <span className="flex items-center gap-1">
              <Users className="h-3 w-3" />
              {incident.affected_families} families
            </span>
          )}
        </div>
      </div>
      {nextAction && (
        <Button
          size="sm"
          variant="outline"
          className="shrink-0 gap-1 text-xs"
          disabled={isAdvancing}
          onClick={() => onAdvance(incident.id)}
        >
          {isAdvancing ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <ArrowRight className="h-3 w-3" />
          )}
          {nextAction}
        </Button>
      )}
    </div>
  );
}

export default function OperatorIncidentsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [dialogOpen, setDialogOpen] = useState(false);

  // Form state
  const [title, setTitle] = useState("");
  const [incidentType, setIncidentType] = useState<IncidentType>("flood");
  const [barangay, setBarangay] = useState("");
  const [description, setDescription] = useState("");

  const { data: incidentsData, isLoading } = useIncidents();
  const { data: statsData } = useIncidentStats();
  const createIncident = useCreateIncident();
  const advanceIncident = useAdvanceIncident();

  const incidents = useMemo(() => {
    if (Array.isArray(incidentsData)) return incidentsData as Incident[];
    if (
      incidentsData &&
      typeof incidentsData === "object" &&
      "data" in incidentsData
    ) {
      return (incidentsData as { data: Incident[] }).data ?? [];
    }
    return [] as Incident[];
  }, [incidentsData]);

  const stageCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    if (
      statsData &&
      typeof statsData === "object" &&
      "by_status" in (statsData as unknown as Record<string, unknown>)
    ) {
      return (statsData as unknown as { by_status: Record<string, number> })
        .by_status;
    }
    for (const inc of incidents) {
      counts[inc.status] = (counts[inc.status] ?? 0) + 1;
    }
    return counts;
  }, [incidents, statsData]);

  const filtered = useMemo(() => {
    let result = incidents;
    if (statusFilter !== "all") {
      result = result.filter((i) => i.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (i) =>
          i.title.toLowerCase().includes(q) ||
          i.barangay.toLowerCase().includes(q) ||
          i.incident_type.toLowerCase().includes(q),
      );
    }
    return result;
  }, [incidents, statusFilter, search]);

  function handleCreate() {
    if (!title.trim() || !barangay) return;
    createIncident.mutate(
      {
        title: title.trim(),
        incident_type: incidentType,
        risk_level: 1,
        barangay,
        description: description.trim() || undefined,
      },
      {
        onSuccess: () => {
          setDialogOpen(false);
          setTitle("");
          setDescription("");
          setBarangay("");
          setIncidentType("flood");
        },
      },
    );
  }

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <Breadcrumb
        items={[
          { label: "Operations", href: "/operator" },
          { label: "Incidents" },
        ]}
        className="mb-4"
      />

      {/* Pipeline Overview */}
      <div className="flex flex-wrap items-center gap-2">
        {PIPELINE_STAGES.map((stage, i) => (
          <div key={stage.key} className="flex items-center gap-2">
            <button
              onClick={() =>
                setStatusFilter(statusFilter === stage.key ? "all" : stage.key)
              }
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg border bg-card transition-all",
                statusFilter === stage.key && "ring-2 ring-primary/50",
              )}
            >
              <div className={cn("h-2.5 w-2.5 rounded-full", stage.color)} />
              <span className="text-sm font-medium">{stage.label}</span>
              <Badge variant="secondary" className="text-xs">
                {stageCounts[stage.key] ?? 0}
              </Badge>
            </button>
            {i < PIPELINE_STAGES.length - 1 && (
              <ChevronRight className="h-4 w-4 text-muted-foreground/50 hidden sm:block" />
            )}
          </div>
        ))}
      </div>

      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search incidents..."
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          {statusFilter !== "all" && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setStatusFilter("all")}
            >
              Clear filter
            </Button>
          )}
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" variant="destructive" className="gap-1">
                <Plus className="h-3.5 w-3.5" />
                Raise Incident
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Raise New Incident</DialogTitle>
                <DialogDescription>
                  Create a new flood incident record for the MDRRMO pipeline.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-2">
                <div className="space-y-2">
                  <Label htmlFor="inc-title">Title</Label>
                  <Input
                    id="inc-title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Flooding in BF Homes Phase 3"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Incident Type</Label>
                    <Select
                      value={incidentType}
                      onValueChange={(v) => setIncidentType(v as IncidentType)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="flood">Flood</SelectItem>
                        <SelectItem value="flash_flood">Flash Flood</SelectItem>
                        <SelectItem value="storm_surge">Storm Surge</SelectItem>
                        <SelectItem value="landslide">Landslide</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Barangay</Label>
                    <Select value={barangay} onValueChange={setBarangay}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select…" />
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
                </div>
                <div className="space-y-2">
                  <Label htmlFor="inc-desc">Description (optional)</Label>
                  <Textarea
                    id="inc-desc"
                    value={description}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                      setDescription(e.target.value)
                    }
                    placeholder="Describe the situation…"
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleCreate}
                  disabled={
                    !title.trim() || !barangay || createIncident.isPending
                  }
                >
                  {createIncident.isPending && (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  )}
                  Raise Incident
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Incidents List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            {statusFilter !== "all"
              ? `${PIPELINE_STAGES.find((s) => s.key === statusFilter)?.label} Incidents`
              : "All Incidents"}
          </CardTitle>
          <CardDescription>
            Manage and track all flood-related incidents
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full rounded-lg" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <ShieldCheck className="h-12 w-12 mb-3 text-emerald-500/50" />
              <p className="text-base font-medium">All Clear</p>
              <p className="text-sm mt-1">
                {search || statusFilter !== "all"
                  ? "No incidents match your filters."
                  : "No active incidents - the city is currently safe."}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((inc) => (
                <IncidentCard
                  key={inc.id}
                  incident={inc}
                  onAdvance={(id) => advanceIncident.mutate(id)}
                  isAdvancing={advanceIncident.isPending}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
