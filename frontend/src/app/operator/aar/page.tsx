/**
 * Operator - After-Action Reports Page
 *
 * List, search, and create after-action reports for resolved incidents.
 * Uses useAARs + useCreateAAR hooks from operator feature module.
 */

import {
  CheckCircle2,
  ClipboardCheck,
  Clock,
  FileText,
  Loader2,
  Plus,
  Search,
  Send,
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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useAARs, useCreateAAR, useIncidents } from "@/features/operator";
import { showToast } from "@/lib/toast";
import type { AARStatus, AfterActionReport } from "@/types";

const STATUS_CFG: Record<
  AARStatus,
  { label: string; cls: string; Icon: typeof FileText }
> = {
  draft: {
    label: "Draft",
    cls: "bg-muted text-muted-foreground",
    Icon: FileText,
  },
  submitted: {
    label: "Submitted",
    cls: "bg-blue-500/10 text-blue-600",
    Icon: Send,
  },
  reviewed: {
    label: "Reviewed",
    cls: "bg-yellow-500/10 text-yellow-700",
    Icon: Clock,
  },
  approved: {
    label: "Approved",
    cls: "bg-green-500/10 text-green-700",
    Icon: CheckCircle2,
  },
};

export default function OperatorAARPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<AARStatus | "all">("all");
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newSummary, setNewSummary] = useState("");
  const [selectedIncident, setSelectedIncident] = useState<number | "">("");

  const { data: raw, isLoading } = useAARs();
  const createAAR = useCreateAAR();
  const { data: incidentData } = useIncidents({ status: "resolved" });
  const aars = useMemo(() => {
    const items = (raw as unknown as { data: AfterActionReport[] })?.data ?? [];
    return items.filter((aar) => {
      if (statusFilter !== "all" && aar.status !== statusFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          aar.title.toLowerCase().includes(q) ||
          aar.summary?.toLowerCase().includes(q) ||
          aar.prepared_by?.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [raw, search, statusFilter]);

  // stat counts
  const counts = useMemo(() => {
    const all = (raw as unknown as { data: AfterActionReport[] })?.data ?? [];
    return {
      total: all.length,
      approved: all.filter((a) => a.status === "approved").length,
      pending: all.filter((a) => a.status !== "approved").length,
      compliant: all.filter((a) => a.ra10121_compliant).length,
    };
  }, [raw]);

  const resolvedIncidents = useMemo(() => {
    return incidentData?.data ?? [];
  }, [incidentData]);

  const handleCreateAAR = () => {
    if (!selectedIncident || !newTitle.trim() || !newSummary.trim()) return;
    createAAR.mutate(
      {
        incident_id: selectedIncident,
        title: newTitle.trim(),
        summary: newSummary.trim(),
      },
      {
        onSuccess: () => {
          showToast.success("After-action report created");
          setShowCreate(false);
          setNewTitle("");
          setNewSummary("");
          setSelectedIncident("");
        },
        onError: () => {
          showToast.error("Failed to create report");
        },
      },
    );
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <Breadcrumb
        items={[
          { label: "Operations", href: "/operator" },
          { label: "After-Action Reports" },
        ]}
        className="mb-4"
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">After-Action Reports</h2>
          <p className="text-sm text-muted-foreground">
            Post-incident analysis and RA 10121 compliance documentation
          </p>
        </div>
        <Button className="gap-2" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4" />
          New Report
        </Button>
      </div>

      {/* Create Dialog (inline) */}
      {showCreate && (
        <Card className="border-primary/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              Create After-Action Report
            </CardTitle>
            <CardDescription>
              Select a resolved incident and provide a summary
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Incident</p>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                value={selectedIncident}
                onChange={(e) =>
                  setSelectedIncident(
                    e.target.value ? Number(e.target.value) : "",
                  )
                }
              >
                <option value="">Select an incident…</option>
                {resolvedIncidents.map((inc) => (
                  <option key={inc.id} value={inc.id}>
                    #{inc.id} - {inc.title} ({inc.barangay})
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Title</p>
              <Input
                placeholder="AAR title…"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Summary</p>
              <textarea
                className="w-full rounded-md border px-3 py-2 text-sm bg-background min-h-20 resize-y"
                placeholder="Brief summary of the incident response…"
                value={newSummary}
                onChange={(e) => setNewSummary(e.target.value)}
              />
            </div>
            <div className="flex gap-3 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCreate(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={
                  !selectedIncident ||
                  !newTitle.trim() ||
                  !newSummary.trim() ||
                  createAAR.isPending
                }
                onClick={handleCreateAAR}
              >
                {createAAR.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                Create Report
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            {isLoading ? (
              <Skeleton className="h-8 w-12 mx-auto" />
            ) : (
              <p className="text-2xl font-bold">{counts.total}</p>
            )}
            <p className="text-xs text-muted-foreground">Total AARs</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            {isLoading ? (
              <Skeleton className="h-8 w-12 mx-auto" />
            ) : (
              <p className="text-2xl font-bold">{counts.approved}</p>
            )}
            <p className="text-xs text-muted-foreground">Approved</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            {isLoading ? (
              <Skeleton className="h-8 w-12 mx-auto" />
            ) : (
              <p className="text-2xl font-bold">{counts.pending}</p>
            )}
            <p className="text-xs text-muted-foreground">Pending Review</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            {isLoading ? (
              <Skeleton className="h-8 w-12 mx-auto" />
            ) : (
              <p className="text-2xl font-bold">{counts.compliant}</p>
            )}
            <p className="text-xs text-muted-foreground">RA 10121 Compliant</p>
          </CardContent>
        </Card>
      </div>

      {/* Search + Filter */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-10"
                placeholder="Search after-action reports…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              {(
                ["all", "draft", "submitted", "reviewed", "approved"] as const
              ).map((s) => (
                <Button
                  key={s}
                  size="sm"
                  variant={statusFilter === s ? "default" : "outline"}
                  onClick={() => setStatusFilter(s)}
                >
                  {s === "all" ? "All" : STATUS_CFG[s].label}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <ClipboardCheck className="h-4 w-4 text-primary" />
            Reports
          </CardTitle>
          <CardDescription>
            {aars.length} report{aars.length !== 1 ? "s" : ""} found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full rounded" />
              ))}
            </div>
          ) : aars.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <FileText className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm font-medium">No after-action reports yet</p>
              <p className="text-xs mt-1">
                Create your first report from a resolved incident
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {aars.map((aar) => {
                const cfg = STATUS_CFG[aar.status];
                const StatusIcon = cfg.Icon;
                return (
                  <div
                    key={aar.id}
                    className="flex items-start gap-4 p-4 border rounded-lg hover:bg-muted/30 transition-colors"
                  >
                    <div
                      className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${cfg.cls}`}
                    >
                      <StatusIcon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium truncate">
                          {aar.title}
                        </p>
                        <Badge variant="outline" className="text-[10px]">
                          {cfg.label}
                        </Badge>
                        {aar.ra10121_compliant && (
                          <Badge variant="secondary" className="text-[10px]">
                            RA 10121
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {aar.summary}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        {aar.prepared_by && <span>By: {aar.prepared_by}</span>}
                        {aar.response_time_minutes != null && (
                          <span>Response: {aar.response_time_minutes}min</span>
                        )}
                        {aar.prediction_accuracy != null && (
                          <span>
                            Accuracy:{" "}
                            {(aar.prediction_accuracy * 100).toFixed(0)}%
                          </span>
                        )}
                        <span>
                          {new Date(aar.created_at).toLocaleDateString("en-PH")}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      {aar.submitted_to_ndrrmc && (
                        <Badge variant="outline" className="text-[10px]">
                          NDRRMC
                        </Badge>
                      )}
                      {aar.submitted_to_dilg && (
                        <Badge variant="outline" className="text-[10px]">
                          DILG
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
