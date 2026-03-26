/**
 * Operator - Evacuation Centers Page
 *
 * Displays real-time evacuation center data from the API.
 * Uses useEvacuationCenters() hook with auto-refetch.
 */

import {
  AlertTriangle,
  Building,
  ChevronRight,
  MapPin,
  Search,
  Users,
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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvacuationCenters } from "@/features/evacuation";
import type { EvacuationCenter } from "@/types";

function statusFromCenter(
  center: EvacuationCenter,
): "open" | "standby" | "closed" {
  if (!center.is_active) return "closed";
  if (center.capacity_current > 0) return "open";
  return "standby";
}

function statusColor(status: "open" | "standby" | "closed") {
  switch (status) {
    case "open":
      return "bg-green-500/10 text-green-700 border-green-500/30";
    case "standby":
      return "bg-amber-500/10 text-amber-700 border-amber-500/30";
    case "closed":
      return "bg-muted text-muted-foreground border-border";
  }
}

export default function OperatorEvacuationPage() {
  const [search, setSearch] = useState("");
  const {
    data: centers = [],
    isLoading,
    isError,
    refetch,
  } = useEvacuationCenters();

  const filtered = useMemo(
    () =>
      centers.filter(
        (c) =>
          c.name.toLowerCase().includes(search.toLowerCase()) ||
          c.barangay.toLowerCase().includes(search.toLowerCase()),
      ),
    [centers, search],
  );

  const totalCapacity = centers.reduce((s, c) => s + c.capacity_total, 0);
  const totalOccupancy = centers.reduce((s, c) => s + c.capacity_current, 0);

  if (isError) {
    return (
      <div className="p-4 sm:p-6">
        <Card>
          <CardContent className="pt-6 flex flex-col items-center gap-3 text-muted-foreground">
            <AlertTriangle className="h-8 w-8 opacity-50" />
            <p className="text-sm">Failed to load evacuation centers</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const openCount = centers.filter(
    (c) => statusFromCenter(c) === "open",
  ).length;

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            {isLoading ? (
              <Skeleton className="h-8 w-12 mx-auto" />
            ) : (
              <p className="text-2xl font-bold">{centers.length}</p>
            )}
            <p className="text-xs text-muted-foreground">Total Centers</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            {isLoading ? (
              <Skeleton className="h-8 w-12 mx-auto" />
            ) : (
              <p className="text-2xl font-bold">{openCount}</p>
            )}
            <p className="text-xs text-muted-foreground">Open</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            {isLoading ? (
              <Skeleton className="h-8 w-12 mx-auto" />
            ) : (
              <p className="text-2xl font-bold">{totalOccupancy}</p>
            )}
            <p className="text-xs text-muted-foreground">Evacuees</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            {isLoading ? (
              <Skeleton className="h-8 w-12 mx-auto" />
            ) : (
              <p className="text-2xl font-bold">{totalCapacity}</p>
            )}
            <p className="text-xs text-muted-foreground">Total Capacity</p>
          </CardContent>
        </Card>
      </div>

      {/* Overall Occupancy */}
      <Card>
        <CardContent className="pt-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Overall Occupancy</span>
            <span className="font-medium">
              {totalCapacity > 0
                ? Math.round((totalOccupancy / totalCapacity) * 100)
                : 0}
              %
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{
                width: `${totalCapacity > 0 ? (totalOccupancy / totalCapacity) * 100 : 0}%`,
              }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Center List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building className="h-4 w-4 text-primary" />
            Evacuation Centers
          </CardTitle>
          <CardDescription>
            Manage capacity, status, and logistics
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-10"
              placeholder="Search centers…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="space-y-3">
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full rounded-lg" />
              ))
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Users className="h-10 w-10 mb-2 opacity-30" />
                <p className="text-sm">No centers found</p>
              </div>
            ) : (
              filtered.map((center) => {
                const status = statusFromCenter(center);
                const pct =
                  center.capacity_total > 0
                    ? Math.round(
                        (center.capacity_current / center.capacity_total) * 100,
                      )
                    : 0;
                return (
                  <div
                    key={center.id}
                    className="flex items-center gap-4 p-4 rounded-lg border border-border/50 hover:bg-accent/50 transition-colors"
                  >
                    <div className="shrink-0 h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Building className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {center.name}
                      </p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {center.address ?? center.barangay}
                      </p>
                      <div className="mt-1.5 flex items-center gap-2">
                        <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {center.capacity_current}/{center.capacity_total}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <Badge variant="outline" className={statusColor(status)}>
                        {status}
                      </Badge>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
