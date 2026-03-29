/**
 * Evacuation Centers Page
 *
 * Full-width layout with real-time capacity stats, Leaflet map,
 * Find Nearest with barangay fallback, admin inline occupancy
 * updates, and SSE-driven live data.
 */

import { useQueryClient } from "@tanstack/react-query";
import { motion, useInView } from "framer-motion";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  AlertTriangle,
  Clock,
  LifeBuoy,
  Loader2,
  MapPin,
  Minus,
  Navigation,
  Phone,
  Plus,
  RefreshCw,
  Star,
  WifiOff,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, Tooltip } from "react-leaflet";
import { toast } from "sonner";

import { SectionHeading } from "@/components/layout/SectionHeading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BARANGAYS } from "@/config/paranaque";
import { useCapacityStream } from "@/features/evacuation/hooks/useCapacityStream";
import {
  evacuationKeys,
  useEvacuationCenters,
  useNearestCenters,
  useUpdateCapacity,
} from "@/features/evacuation/hooks/useEvacuationCenters";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { useUser } from "@/state";
import { useEvacuationActions } from "@/state/stores/evacuationStore";
import type { EvacuationCenter, NearestCenterResult } from "@/types";

// ---------------------------------------------------------------------------
// Leaflet icon fix
// ---------------------------------------------------------------------------

// @ts-expect-error leaflet private property workaround
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "/leaflet/marker-icon-2x.png",
  iconUrl: "/leaflet/marker-icon.png",
  shadowUrl: "/leaflet/marker-shadow.png",
});

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAP_CENTER: [number, number] = [14.4793, 121.0198];
const MAP_ZOOM = 13;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function occupancyColor(pct: number): string {
  if (pct >= 100) return "text-risk-critical";
  if (pct >= 81) return "text-orange-500";
  if (pct >= 51) return "text-risk-alert";
  return "text-risk-safe";
}

function occupancyBarColor(pct: number): string {
  if (pct >= 100) return "hsl(var(--risk-critical))";
  if (pct >= 81) return "#f97316"; // orange-500
  if (pct >= 51) return "hsl(var(--risk-alert))";
  return "hsl(var(--risk-safe))";
}

function occupancyBadge(
  pct: number,
): "default" | "secondary" | "destructive" | "outline" {
  if (pct >= 100) return "destructive";
  if (pct >= 81) return "secondary";
  if (pct >= 51) return "outline";
  return "default";
}

function occupancyLabel(pct: number): string {
  if (pct >= 100) return "Full";
  if (pct >= 81) return "Near Full";
  if (pct >= 51) return "Filling Up";
  return "Available";
}

function statusBadgeVariant(
  center: EvacuationCenter,
): "default" | "secondary" | "destructive" {
  if (!center.is_active) return "secondary";
  if (center.occupancy_pct >= 100) return "destructive";
  return "default";
}

function statusLabel(center: EvacuationCenter): string {
  if (!center.is_active) return "Closed";
  if (center.occupancy_pct >= 100) return "Full";
  return "Open";
}

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return "N/A";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function estimateTravelMins(distanceKm: number): number {
  // ~25 km/h average urban driving speed in Metro Manila
  return Math.max(1, Math.round((distanceKm / 25) * 60));
}

function createCenterIcon(pct: number): L.DivIcon {
  const fill =
    pct >= 100
      ? "#ef4444"
      : pct >= 81
        ? "#f97316"
        : pct >= 51
          ? "#eab308"
          : "#22c55e";
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="30" height="45">
      <path fill="${fill}" stroke="#fff" stroke-width="1.5"
        d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24C24 5.37 18.63 0 12 0z"/>
      <path fill="#fff" d="M12 6.5l-5.5 6.5h2.5v4h6v-4h2.5L12 6.5z"/>
    </svg>
  `;
  return L.divIcon({
    html: svg,
    className: "evac-center-marker",
    iconSize: [30, 45],
    iconAnchor: [15, 45],
    popupAnchor: [0, -45],
  });
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function EvacuationPage() {
  const queryClient = useQueryClient();
  const user = useUser();
  const isAdmin = user?.role === "admin";

  const {
    data: centers = [],
    isLoading,
    isError,
    refetch,
  } = useEvacuationCenters({ active_only: true });
  const { isConnected } = useCapacityStream({ enabled: true });
  const { setCachedCenters } = useEvacuationActions();
  const updateCapacity = useUpdateCapacity();

  // Cache centers for offline use whenever they load
  useEffect(() => {
    if (centers.length > 0) {
      setCachedCenters(centers);
    }
  }, [centers, setCachedCenters]);

  // ---- SSE → query cache bridge ----
  const paramsRef = useRef({ active_only: true });
  useEffect(() => {
    const handler = (e: Event) => {
      const { detail } = e as CustomEvent<{
        center_id: number;
        capacity_current: number;
        capacity_total: number;
      }>;
      queryClient.setQueryData<EvacuationCenter[]>(
        evacuationKeys.centers(paramsRef.current),
        (old) => {
          if (!old) return old;
          return old.map((c) =>
            c.id === detail.center_id
              ? {
                  ...c,
                  capacity_current: detail.capacity_current,
                  capacity_total: detail.capacity_total,
                  occupancy_pct: Math.round(
                    (detail.capacity_current / detail.capacity_total) * 100,
                  ),
                  available_slots:
                    detail.capacity_total - detail.capacity_current,
                }
              : c,
          );
        },
      );
    };
    window.addEventListener("evacuation_capacity", handler);
    return () => window.removeEventListener("evacuation_capacity", handler);
  }, [queryClient]);

  // ---- Find Nearest (geolocation + barangay fallback) ----
  const [userLocation, setUserLocation] = useState<{
    lat: number;
    lon: number;
  } | null>(null);
  const [geoError, setGeoError] = useState(false);
  const [fallbackBarangay, setFallbackBarangay] = useState<string>("");

  const { data: nearestResults, isFetching: findingNearest } =
    useNearestCenters(userLocation?.lat, userLocation?.lon, 3);

  const handleFindNearest = useCallback(() => {
    if (!navigator.geolocation) {
      toast.error("Geolocation not supported by your browser");
      setGeoError(true);
      return;
    }
    setGeoError(false);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        });
        setGeoError(false);
      },
      () => {
        toast.error("Unable to get your location - select a barangay instead");
        setGeoError(true);
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }, []);

  const handleBarangayFallback = useCallback((key: string) => {
    setFallbackBarangay(key);
    const brgy = BARANGAYS.find((b) => b.key === key);
    if (brgy) {
      setUserLocation({ lat: brgy.lat, lon: brgy.lon });
      setGeoError(false);
    }
  }, []);

  // ---- Highlighted nearest IDs for map ----
  const nearestIds = useMemo(
    () =>
      new Set(
        nearestResults?.map((r: NearestCenterResult) => r.center.id) ?? [],
      ),
    [nearestResults],
  );

  // ---- Stats ----
  const stats = useMemo(() => {
    const total = centers.length;
    const totalCapacity = centers.reduce((sum, c) => sum + c.capacity_total, 0);
    const totalOccupied = centers.reduce(
      (sum, c) => sum + c.capacity_current,
      0,
    );
    const avgOccupancy = totalCapacity
      ? Math.round((totalOccupied / totalCapacity) * 100)
      : 0;
    const available = centers.filter((c) => c.occupancy_pct < 100).length;
    const totalSlots = totalCapacity - totalOccupied;
    return { total, available, avgOccupancy, totalSlots };
  }, [centers]);

  // ---- Leaflet icons (memoized) ----
  const iconMap = useMemo(() => {
    const map = new Map<number, L.DivIcon>();
    for (const c of centers) {
      map.set(c.id, createCenterIcon(c.occupancy_pct));
    }
    return map;
  }, [centers]);

  // ---- Admin inline capacity update ----
  const handleCapacityChange = useCallback(
    (centerId: number, currentVal: number, delta: number, max: number) => {
      const next = Math.max(0, Math.min(max, currentVal + delta));
      if (next === currentVal) return;
      updateCapacity.mutate({ center_id: centerId, capacity_current: next });
    },
    [updateCapacity],
  );

  const sectionRef = useRef<HTMLDivElement>(null);
  const inView = useInView(sectionRef, { once: true, amount: 0.1 });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <div className="flex items-center justify-end gap-3">
          {/* Live indicator */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {isConnected ? (
              <>
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
                </span>
                <span className="text-green-600 dark:text-green-400 font-medium">
                  Live
                </span>
              </>
            ) : (
              <>
                <WifiOff className="h-3.5 w-3.5 text-risk-alert" />
                <span className="text-risk-alert font-medium">Offline</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Offline banner */}
      {!isConnected && (
        <div className="w-full px-6 mt-4">
          <div className="flex items-center gap-2 rounded-lg bg-risk-alert/10 dark:bg-risk-alert/15 px-4 py-2 text-xs text-risk-alert">
            <WifiOff className="h-4 w-4 shrink-0" />
            Live capacity updates unavailable - data may not be current.
          </div>
        </div>
      )}

      {/* Main content */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={sectionRef}>
          <SectionHeading
            label="Capacity Dashboard"
            title="Evacuation Center Status"
            subtitle="Monitor real-time occupancy and find the nearest available center."
          />

          {/* Error state */}
          {isError && !isLoading && (
            <div className="flex flex-col items-center justify-center py-16 text-center space-y-4">
              <AlertTriangle className="h-12 w-12 text-risk-critical" />
              <p className="text-lg font-semibold text-foreground">
                Failed to load evacuation centers
              </p>
              <p className="text-sm text-muted-foreground max-w-md">
                We couldn't fetch the latest center data. Please check your
                connection and try again.
              </p>
              <Button onClick={() => refetch()} variant="outline" size="sm">
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !isError && centers.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
              <LifeBuoy className="h-12 w-12 text-muted-foreground/50" />
              <p className="text-lg font-semibold text-foreground">
                No Active Centers
              </p>
              <p className="text-sm text-muted-foreground max-w-md">
                There are currently no active evacuation centers registered in
                the system. Centers will appear here once activated.
              </p>
            </div>
          )}

          {/* Main content when data is present */}
          {(isLoading || centers.length > 0) && !isError && (
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate={inView ? "show" : undefined}
              className="space-y-6"
            >
              {/* Stats Row */}
              <motion.div
                variants={fadeUp}
                className="grid grid-cols-2 md:grid-cols-4 gap-4"
              >
                <GlassCard className="p-4 text-center">
                  <p className="text-2xl font-bold text-primary">
                    {stats.total}
                  </p>
                  <p className="text-xs text-muted-foreground">Total Centers</p>
                </GlassCard>
                <GlassCard className="p-4 text-center">
                  <p className="text-2xl font-bold text-risk-safe">
                    {stats.available}
                  </p>
                  <p className="text-xs text-muted-foreground">Available</p>
                </GlassCard>
                <GlassCard className="p-4 text-center">
                  <p
                    className={`text-2xl font-bold ${occupancyColor(stats.avgOccupancy)}`}
                  >
                    {stats.avgOccupancy}%
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Avg. Occupancy
                  </p>
                </GlassCard>
                <GlassCard className="p-4 text-center">
                  <p className="text-2xl font-bold text-blue-600">
                    {stats.totalSlots.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Slots Available
                  </p>
                </GlassCard>
              </motion.div>

              {/* Find Nearest */}
              <motion.div variants={fadeUp}>
                <GlassCard className="p-4">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold">
                        Find Nearest Center
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        Uses your current location to find the closest available
                        evacuation center.
                      </p>
                    </div>
                    <Button
                      onClick={handleFindNearest}
                      disabled={findingNearest}
                      size="sm"
                    >
                      {findingNearest ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <Navigation className="h-4 w-4 mr-2" />
                      )}
                      Find Nearest
                    </Button>
                  </div>

                  {/* Barangay fallback when geolocation fails */}
                  {geoError && (
                    <div className="mt-3 flex flex-col sm:flex-row items-start sm:items-center gap-3">
                      <p className="text-xs text-muted-foreground shrink-0">
                        Or select your barangay:
                      </p>
                      <Select
                        value={fallbackBarangay}
                        onValueChange={handleBarangayFallback}
                      >
                        <SelectTrigger className="h-8 w-full sm:w-64 text-xs">
                          <SelectValue placeholder="Choose a barangay..." />
                        </SelectTrigger>
                        <SelectContent>
                          {BARANGAYS.map((b) => (
                            <SelectItem key={b.key} value={b.key}>
                              {b.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {/* Nearest results */}
                  {nearestResults && nearestResults.length > 0 && (
                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      {nearestResults.map((r: NearestCenterResult) => (
                        <div
                          key={`nearest-${r.center.id}`}
                          className="rounded-lg border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-950/20 p-3 space-y-1.5"
                        >
                          <p className="text-sm font-medium">{r.center.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {r.distance_km.toFixed(1)} km
                            away&nbsp;&middot;&nbsp; ~
                            {estimateTravelMins(r.distance_km)} min drive
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {r.available_slots} slots&nbsp;&middot;&nbsp;
                            <span className={occupancyColor(r.occupancy_pct)}>
                              {r.occupancy_pct}% full
                            </span>
                          </p>
                          <a
                            href={r.google_maps_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full h-7 text-xs mt-1"
                            >
                              Directions in Google Maps
                            </Button>
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                </GlassCard>
              </motion.div>

              {/* Leaflet Map */}
              <motion.div variants={fadeUp}>
                <GlassCard className="p-0 overflow-hidden">
                  <div
                    className="h-87.5 sm:h-105"
                    role="region"
                    aria-label="Evacuation centers map"
                  >
                    <MapContainer
                      center={MAP_CENTER}
                      zoom={MAP_ZOOM}
                      scrollWheelZoom={true}
                      className="h-full w-full z-0"
                      attributionControl={false}
                    >
                      <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        maxZoom={19}
                      />
                      {centers.map((c) => (
                        <Marker
                          key={`evac-marker-${c.id}`}
                          position={[c.latitude, c.longitude]}
                          icon={iconMap.get(c.id)!}
                        >
                          <Tooltip direction="top" offset={[0, -47]}>
                            <strong>{c.name}</strong>
                            {nearestIds.has(c.id) && (
                              <>
                                {" "}
                                <Star className="h-3 w-3 inline" /> Nearest
                              </>
                            )}
                          </Tooltip>
                          <Popup maxWidth={280}>
                            <div className="min-w-48 space-y-2 text-sm">
                              <p className="font-semibold text-gray-900 dark:text-gray-100">
                                {c.name}
                              </p>
                              <div className="space-y-1">
                                <div className="flex justify-between text-xs text-gray-500">
                                  <span>
                                    {c.capacity_current} / {c.capacity_total}
                                  </span>
                                  <span
                                    style={{
                                      color: occupancyBarColor(c.occupancy_pct),
                                    }}
                                  >
                                    {c.occupancy_pct}%
                                  </span>
                                </div>
                                <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                                  <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{
                                      width: `${Math.min(c.occupancy_pct, 100)}%`,
                                      backgroundColor: occupancyBarColor(
                                        c.occupancy_pct,
                                      ),
                                    }}
                                  />
                                </div>
                              </div>
                              <div className="text-xs text-gray-500 space-y-0.5">
                                <p>{c.barangay}</p>
                                {c.contact_number && (
                                  <p>Contact: {c.contact_number}</p>
                                )}
                              </div>
                            </div>
                          </Popup>
                        </Marker>
                      ))}
                    </MapContainer>
                  </div>
                </GlassCard>
              </motion.div>

              {/* Center Cards */}
              <motion.div variants={fadeUp}>
                {isLoading ? (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <GlassCard
                        key={`skeleton-${i}`}
                        className="p-4 h-44 animate-pulse"
                      />
                    ))}
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {centers.map((c: EvacuationCenter) => (
                      <GlassCard
                        key={c.id}
                        className={`p-4 space-y-3 hover:shadow-lg transition-shadow ${nearestIds.has(c.id) ? "ring-2 ring-indigo-400 dark:ring-indigo-600" : ""}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <MapPin className="h-3.5 w-3.5 text-risk-safe shrink-0" />
                            <span className="text-sm font-medium leading-tight truncate">
                              {c.name}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Badge variant={statusBadgeVariant(c)}>
                              {statusLabel(c)}
                            </Badge>
                            <Badge variant={occupancyBadge(c.occupancy_pct)}>
                              {occupancyLabel(c.occupancy_pct)}
                            </Badge>
                          </div>
                        </div>

                        {/* Capacity bar */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>
                              {c.capacity_current} / {c.capacity_total}
                            </span>
                            <span
                              className={`font-medium ${occupancyColor(c.occupancy_pct)}`}
                            >
                              {c.occupancy_pct}%
                            </span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{
                                width: `${Math.min(c.occupancy_pct, 100)}%`,
                                backgroundColor: occupancyBarColor(
                                  c.occupancy_pct,
                                ),
                              }}
                            />
                          </div>
                        </div>

                        <div className="text-xs text-muted-foreground space-y-0.5">
                          <p>{c.barangay}</p>
                          {c.address && <p>{c.address}</p>}
                          {c.contact_number && (
                            <p className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {c.contact_number}
                            </p>
                          )}
                          <p className="flex items-center gap-1 pt-0.5 text-muted-foreground/70">
                            <Clock className="h-3 w-3" />
                            Updated {relativeTime(c.updated_at)}
                          </p>
                        </div>

                        {/* Admin inline capacity update */}
                        {isAdmin && (
                          <div className="flex items-center gap-2 pt-1 border-t border-border">
                            <span className="text-xs text-muted-foreground">
                              Occupancy:
                            </span>
                            <Button
                              variant="outline"
                              size="icon"
                              className="h-6 w-6"
                              disabled={
                                updateCapacity.isPending ||
                                c.capacity_current <= 0
                              }
                              onClick={() =>
                                handleCapacityChange(
                                  c.id,
                                  c.capacity_current,
                                  -1,
                                  c.capacity_total,
                                )
                              }
                            >
                              <Minus className="h-3 w-3" />
                            </Button>
                            <span className="text-xs font-medium w-8 text-center">
                              {c.capacity_current}
                            </span>
                            <Button
                              variant="outline"
                              size="icon"
                              className="h-6 w-6"
                              disabled={
                                updateCapacity.isPending ||
                                c.capacity_current >= c.capacity_total
                              }
                              onClick={() =>
                                handleCapacityChange(
                                  c.id,
                                  c.capacity_current,
                                  1,
                                  c.capacity_total,
                                )
                              }
                            >
                              <Plus className="h-3 w-3" />
                            </Button>
                          </div>
                        )}
                      </GlassCard>
                    ))}
                  </div>
                )}
              </motion.div>
            </motion.div>
          )}
        </div>
      </section>
    </div>
  );
}
