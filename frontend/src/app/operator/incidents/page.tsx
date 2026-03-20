/**
 * Operator — Active Incidents Page
 *
 * Full-page incident management with Kanban pipeline,
 * searchable incident list, and new incident form.
 */

import {
  AlertTriangle,
  ChevronRight,
  Clock,
  Filter,
  Plus,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";

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
import { cn } from "@/lib/utils";

const PIPELINE_STAGES = [
  { key: "raised", label: "Alert Raised", color: "bg-red-500", count: 0 },
  { key: "confirmed", label: "LGU Confirmed", color: "bg-amber-500", count: 0 },
  { key: "broadcast", label: "Broadcast Sent", color: "bg-blue-500", count: 0 },
  { key: "resolved", label: "Resolved", color: "bg-emerald-500", count: 0 },
  { key: "closed", label: "Closed", color: "bg-gray-500", count: 0 },
];

export default function OperatorIncidentsPage() {
  const [search, setSearch] = useState("");

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Pipeline Overview */}
      <div className="flex flex-wrap items-center gap-2">
        {PIPELINE_STAGES.map((stage, i) => (
          <div key={stage.key} className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg border bg-card">
              <div className={cn("h-2.5 w-2.5 rounded-full", stage.color)} />
              <span className="text-sm font-medium">{stage.label}</span>
              <Badge variant="secondary" className="text-xs">
                {stage.count}
              </Badge>
            </div>
            {i < PIPELINE_STAGES.length - 1 && (
              <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
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
          <Button variant="outline" size="sm" className="gap-1">
            <Filter className="h-3.5 w-3.5" />
            Filters
          </Button>
          <Button size="sm" variant="destructive" className="gap-1">
            <Plus className="h-3.5 w-3.5" />
            Raise Incident
          </Button>
        </div>
      </div>

      {/* Incidents List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            All Incidents
          </CardTitle>
          <CardDescription>
            Manage and track all flood-related incidents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <ShieldCheck className="h-12 w-12 mb-3 text-emerald-500/50" />
            <p className="text-base font-medium">All Clear</p>
            <p className="text-sm mt-1">
              No active incidents — the city is currently safe.
            </p>
            <Button size="sm" variant="outline" className="mt-4 gap-1">
              <Clock className="h-3.5 w-3.5" />
              View Historical Incidents
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
