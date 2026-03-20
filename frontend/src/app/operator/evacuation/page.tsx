/**
 * Operator — Evacuation Centers Page
 */

import { Building, ChevronRight, MapPin, Search, Users } from "lucide-react";
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

// ─── Mock Data ───────────────────────────────────────────────────────────────

interface EvacCenter {
  id: string;
  name: string;
  barangay: string;
  capacity: number;
  occupancy: number;
  status: "open" | "standby" | "closed";
  address: string;
}

const MOCK_CENTERS: EvacCenter[] = [
  {
    id: "1",
    name: "Parañaque National High School",
    barangay: "San Antonio",
    capacity: 500,
    occupancy: 0,
    status: "standby",
    address: "San Antonio, Parañaque City",
  },
  {
    id: "2",
    name: "Barangay Hall - BF Homes",
    barangay: "BF Homes",
    capacity: 200,
    occupancy: 0,
    status: "standby",
    address: "BF Homes, Parañaque City",
  },
  {
    id: "3",
    name: "Dr. Arcadio Santos National High School",
    barangay: "La Huerta",
    capacity: 800,
    occupancy: 0,
    status: "standby",
    address: "La Huerta, Parañaque City",
  },
];

function statusColor(status: EvacCenter["status"]) {
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

  const filtered = MOCK_CENTERS.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.barangay.toLowerCase().includes(search.toLowerCase()),
  );

  const totalCapacity = MOCK_CENTERS.reduce((s, c) => s + c.capacity, 0);
  const totalOccupancy = MOCK_CENTERS.reduce((s, c) => s + c.occupancy, 0);

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{MOCK_CENTERS.length}</p>
            <p className="text-xs text-muted-foreground">Total Centers</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">
              {MOCK_CENTERS.filter((c) => c.status === "open").length}
            </p>
            <p className="text-xs text-muted-foreground">Open</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{totalOccupancy}</p>
            <p className="text-xs text-muted-foreground">Evacuees</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{totalCapacity}</p>
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
            {filtered.map((center) => {
              const pct =
                center.capacity > 0
                  ? Math.round((center.occupancy / center.capacity) * 100)
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
                      {center.address}
                    </p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {center.occupancy}/{center.capacity}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Badge
                      variant="outline"
                      className={statusColor(center.status)}
                    >
                      {center.status}
                    </Badge>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Users className="h-10 w-10 mb-2 opacity-30" />
                <p className="text-sm">No centers found</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
