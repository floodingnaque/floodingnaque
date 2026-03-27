/**
 * Resident - Evacuation Centers Page
 *
 * Real API data, capacity bars, GPS-nearest sorting,
 * directions link, and evacuation reminders.
 */

import {
  Building,
  Filter,
  Loader2,
  MapPin,
  Navigation,
  RefreshCw,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvacuationCenters } from "@/features/evacuation/hooks/useEvacuationCenters";
import type { EvacuationCenter } from "@/types";

function statusColor(isActive: boolean, occupancyPct: number) {
  if (!isActive) return "bg-muted text-muted-foreground border-border";
  if (occupancyPct >= 90) return "bg-red-500/10 text-red-700 border-red-500/30";
  if (occupancyPct >= 70)
    return "bg-amber-500/10 text-amber-700 border-amber-500/30";
  return "bg-green-500/10 text-green-700 border-green-500/30";
}

function statusLabel(isActive: boolean, occupancyPct: number) {
  if (!isActive) return "Closed";
  if (occupancyPct >= 95) return "Full";
  if (occupancyPct >= 70) return "Filling Up";
  return "Open";
}

function capacityBarColor(pct: number) {
  if (pct >= 90) return "bg-red-500";
  if (pct >= 70) return "bg-amber-500";
  return "bg-green-500";
}

export default function ResidentEvacuationPage() {
  const { data: centers, isLoading, refetch } = useEvacuationCenters();
  const [search, setSearch] = useState("");
  const [gpsLoading, setGpsLoading] = useState(false);
  const [userLocation, setUserLocation] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  const handleFindNearest = () => {
    if (!navigator.geolocation) return;
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        });
        setGpsLoading(false);
      },
      () => setGpsLoading(false),
      { timeout: 10000 },
    );
  };

  const filtered = useMemo(() => {
    if (!centers) return [];
    let list = [...centers];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (c: EvacuationCenter) =>
          c.name.toLowerCase().includes(q) ||
          c.barangay?.toLowerCase().includes(q) ||
          c.address?.toLowerCase().includes(q),
      );
    }
    if (userLocation) {
      list.sort((a: EvacuationCenter, b: EvacuationCenter) => {
        const distA = Math.hypot(
          (a.latitude ?? 0) - userLocation.lat,
          (a.longitude ?? 0) - userLocation.lng,
        );
        const distB = Math.hypot(
          (b.latitude ?? 0) - userLocation.lat,
          (b.longitude ?? 0) - userLocation.lng,
        );
        return distA - distB;
      });
    }
    return list;
  }, [centers, search, userLocation]);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      <Breadcrumb
        items={[{ label: "Home", href: "/resident" }, { label: "Evacuation" }]}
        className="mb-4"
      />

      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Building className="h-5 w-5 text-primary" />
            Mga Evacuation Center / Centers
          </h2>
          <p className="text-sm text-muted-foreground">
            Go to the nearest open center if instructed to evacuate
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => refetch()}
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </Button>
          <Button
            size="sm"
            className="gap-2"
            onClick={handleFindNearest}
            disabled={gpsLoading}
          >
            {gpsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Navigation className="h-4 w-4" />
            )}
            Find Nearest
          </Button>
        </div>
      </div>

      {/* ── Search ────────────────────────────────────────────────── */}
      <div className="relative">
        <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-10"
          placeholder="Search by name or barangay…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* ── Center List ───────────────────────────────────────────── */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-xl" />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((center: EvacuationCenter) => {
            const occupancy = center.occupancy_pct ?? 0;
            const available = center.available_slots ?? center.capacity_total;

            return (
              <Card key={center.id}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <div className="h-11 w-11 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Building className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium">{center.name}</p>
                        <Badge
                          variant="outline"
                          className={statusColor(center.is_active, occupancy)}
                        >
                          {statusLabel(center.is_active, occupancy)}
                        </Badge>
                      </div>
                      {center.address && (
                        <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {center.address}
                        </p>
                      )}

                      {/* Capacity bar */}
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {center.capacity_current ?? 0} /{" "}
                            {center.capacity_total} occupants
                          </span>
                          <span>{Math.round(occupancy)}% full</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${capacityBarColor(occupancy)}`}
                            style={{ width: `${Math.min(occupancy, 100)}%` }}
                          />
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {available} slots available
                          {center.contact_number &&
                            ` · ${center.contact_number}`}
                        </p>
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2 mt-3">
                        {center.latitude && center.longitude && (
                          <a
                            href={`https://www.google.com/maps/dir/?api=1&destination=${center.latitude},${center.longitude}`}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Button
                              variant="outline"
                              size="sm"
                              className="gap-1 h-7 text-xs"
                            >
                              <Navigation className="h-3 w-3" />
                              Directions
                            </Button>
                          </a>
                        )}
                        {center.contact_number && (
                          <a
                            href={`tel:${center.contact_number.replace(/[^0-9+]/g, "")}`}
                          >
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs"
                            >
                              Call
                            </Button>
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Building className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm font-medium">
              {search
                ? "No matching centers"
                : "No evacuation centers available"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* ── Reminders ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Paalala sa Paglikas / Evacuation Reminders
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            1. Bring your emergency go-bag (documents, medicine, water,
            clothes).
          </p>
          <p>2. Turn off electricity and gas before leaving your home.</p>
          <p>
            3. Avoid walking through floodwaters - they may be deeper than they
            appear.
          </p>
          <p>4. Register at the evacuation center upon arrival.</p>
          <p>5. Stay at the center until officials say it is safe to return.</p>
        </CardContent>
      </Card>
    </div>
  );
}
