/**
 * Admin Barangay Management Page
 *
 * Configures flood risk and evacuation data for all 16 Parañaque
 * barangays. Pulls live hazard classifications from the GIS backend,
 * evacuation center capacity, and merges with static config data.
 * Features: color-coded stats, risk distribution bar, sortable table,
 * multi-filter search, detail side-panel, and auto-refresh.
 */

import { PageHeader, SectionHeading } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BARANGAYS,
  type BarangayData,
  type BarangayZone,
} from "@/config/paranaque";
import {
  barangayQueryKeys,
  useBarangayDetail,
  useEvacuationCenters,
  useHazardMap,
} from "@/features/admin/hooks/useBarangay";
import type {
  EvacuationCenterData,
  HazardFeatureProperties,
} from "@/features/admin/services/barangayApi";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  ArrowUpDown,
  CheckCircle,
  Clock,
  CloudRain,
  Edit2,
  Eye,
  Landmark,
  MapPin,
  RefreshCw,
  Save,
  Search,
  Shield,
  Users,
  X,
  XCircle,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

// ── Constants ──

type FloodRisk = "low" | "moderate" | "high";

const RISK_STYLES: Record<FloodRisk, string> = {
  high: "bg-risk-critical/10 text-risk-critical border-risk-critical/30",
  moderate: "bg-risk-alert/10 text-risk-alert border-risk-alert/30",
  low: "bg-risk-safe/10 text-risk-safe border-risk-safe/30",
};

const RISK_ICONS: Record<FloodRisk, React.ElementType> = {
  high: AlertTriangle,
  moderate: Shield,
  low: CheckCircle,
};

const ZONE_STYLES: Record<BarangayZone, string> = {
  Coastal:
    "bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-700",
  "Low-lying":
    "bg-purple-50 text-purple-700 border-purple-300 dark:bg-purple-950 dark:text-purple-300 dark:border-purple-700",
  Inland:
    "bg-slate-50 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-600",
};

type AccentLevel = "good" | "warn" | "critical" | "neutral";

function accentGradient(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "from-risk-safe/60 via-risk-safe to-risk-safe/60";
    case "warn":
      return "from-risk-alert/60 via-risk-alert to-risk-alert/60";
    case "critical":
      return "from-risk-critical/60 via-risk-critical to-risk-critical/60";
    default:
      return "from-primary/40 via-primary/60 to-primary/40";
  }
}

function statTextColor(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "text-risk-safe";
    case "warn":
      return "text-risk-alert";
    case "critical":
      return "text-risk-critical";
    default:
      return "";
  }
}

function iconRing(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "bg-risk-safe/10 ring-risk-safe/20";
    case "warn":
      return "bg-risk-alert/10 ring-risk-alert/20";
    case "critical":
      return "bg-risk-critical/10 ring-risk-critical/20";
    default:
      return "bg-primary/10 ring-primary/20";
  }
}

type SortField =
  | "name"
  | "population"
  | "area"
  | "floodEvents"
  | "hazard_score";
type SortDir = "asc" | "desc";

// ── Merged Barangay Row ──

interface MergedBarangay extends BarangayData {
  /** Live hazard score from GIS (0–1) */
  hazard_score: number;
  /** Live risk classification */
  liveRisk: FloodRisk;
  /** Population density (pop / km²) */
  density: number;
  /** Evacuation center status for this barangay */
  evacStatus: "Open" | "Full" | "Closed" | "Unknown";
  /** Evacuation center capacity */
  evacCapacity: number;
  /** Evacuation center current occupancy */
  evacCurrent: number;
  /** Whether this barangay has a data gap */
  hasDataGap: boolean;
}

// ── Override persistence (localStorage) ──

interface BarangayOverride {
  evacuationCenter?: string;
  floodRisk?: FloodRisk;
  zone?: BarangayZone;
}

function loadOverrides(): Record<string, BarangayOverride> {
  try {
    const raw = localStorage.getItem("barangay_overrides");
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveOverrides(overrides: Record<string, BarangayOverride>) {
  localStorage.setItem("barangay_overrides", JSON.stringify(overrides));
}

// ── Stat Card ──

function StatCard({
  icon: Icon,
  label,
  value,
  isLoading,
  health = "neutral",
  description,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  isLoading?: boolean;
  health?: AccentLevel;
  description?: string;
}) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div
        className={cn("h-1 w-full bg-linear-to-r", accentGradient(health))}
      />
      <div className="pt-4 pb-3 px-6 flex items-center gap-3">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl ring-1",
            iconRing(health),
          )}
        >
          <Icon
            className={cn(
              "h-5 w-5",
              health === "neutral" ? "text-primary" : statTextColor(health),
            )}
          />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          {isLoading ? (
            <Skeleton className="h-7 w-16 mt-0.5" />
          ) : (
            <p className={cn("text-2xl font-bold", statTextColor(health))}>
              {value}
            </p>
          )}
          {description && (
            <p className="text-[10px] text-muted-foreground/70">
              {description}
            </p>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

// ── Risk Distribution Bar ──

function RiskDistributionBar({
  high,
  moderate,
  low,
  total,
}: {
  high: number;
  moderate: number;
  low: number;
  total: number;
}) {
  if (total === 0) return null;
  const pctH = (high / total) * 100;
  const pctM = (moderate / total) * 100;
  const pctL = (low / total) * 100;
  return (
    <div className="mt-4">
      <div className="flex items-center gap-4 text-xs text-muted-foreground mb-2">
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-risk-critical" /> High:{" "}
          {high}
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-risk-alert" /> Moderate:{" "}
          {moderate}
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-risk-safe" /> Low: {low}
        </span>
      </div>
      <div className="h-3 w-full rounded-full overflow-hidden flex bg-muted">
        {pctH > 0 && (
          <div
            className="bg-risk-critical h-full transition-all"
            style={{ width: `${pctH}%` }}
          />
        )}
        {pctM > 0 && (
          <div
            className="bg-risk-alert h-full transition-all"
            style={{ width: `${pctM}%` }}
          />
        )}
        {pctL > 0 && (
          <div
            className="bg-risk-safe h-full transition-all"
            style={{ width: `${pctL}%` }}
          />
        )}
      </div>
    </div>
  );
}

// ── Barangay Detail Panel ──

function BarangayDetailPanel({
  barangay,
  open,
  onClose,
  evacCenters,
}: {
  barangay: MergedBarangay | null;
  open: boolean;
  onClose: () => void;
  evacCenters: EvacuationCenterData[];
}) {
  const { data: detail, isLoading } = useBarangayDetail(
    open ? (barangay?.key ?? null) : null,
  );

  if (!barangay) return null;

  const bEvacCenters = evacCenters.filter(
    (c) => c.barangay.toLowerCase() === barangay.name.toLowerCase(),
  );
  const detailData = detail?.data;
  const RiskIcon = RISK_ICONS[barangay.liveRisk];

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-primary" />
            {barangay.name}
          </SheetTitle>
          <SheetDescription>
            {barangay.zone} zone &mdash; {barangay.area} km²
          </SheetDescription>
        </SheetHeader>

        <Tabs defaultValue="overview" className="mt-4">
          <TabsList className="w-full">
            <TabsTrigger value="overview" className="flex-1">
              Overview
            </TabsTrigger>
            <TabsTrigger value="risk" className="flex-1">
              Flood Risk
            </TabsTrigger>
            <TabsTrigger value="evacuation" className="flex-1">
              Evacuation
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Population</p>
                <p className="text-lg font-bold">
                  {barangay.population.toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Density</p>
                <p className="text-lg font-bold">
                  {barangay.density.toLocaleString()}/km²
                </p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Area</p>
                <p className="text-lg font-bold">{barangay.area} km²</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Zone</p>
                <Badge
                  variant="outline"
                  className={cn("text-xs mt-1", ZONE_STYLES[barangay.zone])}
                >
                  {barangay.zone}
                </Badge>
              </div>
            </div>
            <div className="rounded-lg border p-3">
              <p className="text-xs text-muted-foreground mb-1">
                Coordinates (Center)
              </p>
              <p className="font-mono text-sm">
                {barangay.lat.toFixed(4)}°N, {barangay.lon.toFixed(4)}°E
              </p>
            </div>
            {barangay.hasDataGap && (
              <div className="rounded-lg border border-risk-alert/30 bg-risk-alert/5 p-3 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-risk-alert mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-risk-alert">
                    Data Gap Detected
                  </p>
                  <p className="text-xs text-muted-foreground">
                    This barangay has 0 recorded flood events despite its risk
                    classification. Verify against DRRMO records.
                  </p>
                </div>
              </div>
            )}
          </TabsContent>

          {/* Flood Risk Tab */}
          <TabsContent value="risk" className="space-y-4 mt-4">
            <div className="rounded-lg border p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-medium">Current Risk Level</p>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs capitalize",
                    RISK_STYLES[barangay.liveRisk],
                  )}
                >
                  <RiskIcon className="h-3 w-3 mr-1" />
                  {barangay.liveRisk}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 flex-1 rounded-full bg-muted overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      barangay.liveRisk === "high"
                        ? "bg-risk-critical"
                        : barangay.liveRisk === "moderate"
                          ? "bg-risk-alert"
                          : "bg-risk-safe",
                    )}
                    style={{
                      width: `${(barangay.hazard_score * 100).toFixed(0)}%`,
                    }}
                  />
                </div>
                <span className="text-xs font-mono text-muted-foreground">
                  {(barangay.hazard_score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <p className="text-sm font-medium mb-2">Flood History</p>
              <p className="text-2xl font-bold">{barangay.floodEvents}</p>
              <p className="text-xs text-muted-foreground">
                DRRMO events (2022–2025)
              </p>
            </div>

            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : detailData?.hazard?.factors ? (
              <div className="rounded-lg border p-4">
                <p className="text-sm font-medium mb-3">
                  Vulnerability Factors
                </p>
                <div className="space-y-2">
                  {Object.entries(detailData.hazard.factors).map(
                    ([label, value]) => (
                      <div key={label} className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground capitalize w-28">
                          {label}
                        </span>
                        <div className="h-2 flex-1 rounded-full bg-muted overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full",
                              Number(value) >= 0.65
                                ? "bg-risk-critical"
                                : Number(value) >= 0.4
                                  ? "bg-risk-alert"
                                  : "bg-risk-safe",
                            )}
                            style={{
                              width: `${(Number(value) * 100).toFixed(0)}%`,
                            }}
                          />
                        </div>
                        <span className="text-xs font-mono w-10 text-right">
                          {(Number(value) * 100).toFixed(0)}%
                        </span>
                      </div>
                    ),
                  )}
                </div>
              </div>
            ) : null}

            {detailData?.elevation && (
              <div className="rounded-lg border p-4">
                <p className="text-sm font-medium mb-2">Elevation & Terrain</p>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <p className="text-lg font-bold">
                      {detailData.elevation.mean_elevation_m ?? "—"}m
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      Mean Elev.
                    </p>
                  </div>
                  <div>
                    <p className="text-lg font-bold">
                      {detailData.elevation.min_elevation_m ?? "—"}m
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      Min Elev.
                    </p>
                  </div>
                  <div>
                    <p className="text-lg font-bold">
                      {detailData.elevation.slope_pct ?? "—"}%
                    </p>
                    <p className="text-[10px] text-muted-foreground">Slope</p>
                  </div>
                </div>
              </div>
            )}

            {detailData?.drainage && (
              <div className="rounded-lg border p-4">
                <p className="text-sm font-medium mb-2">Drainage</p>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Nearest Waterway
                    </span>
                    <span>
                      {String(
                        detailData.drainage.nearest_waterway ?? "Unknown",
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Distance to Waterway
                    </span>
                    <span>
                      {String(
                        detailData.drainage.distance_to_waterway_m ?? "—",
                      )}
                      m
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Drainage Capacity
                    </span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-xs capitalize",
                        detailData.drainage.drainage_capacity === "poor"
                          ? "text-risk-critical"
                          : detailData.drainage.drainage_capacity === "moderate"
                            ? "text-risk-alert"
                            : "text-risk-safe",
                      )}
                    >
                      {String(
                        detailData.drainage.drainage_capacity ?? "unknown",
                      )}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Impervious Surface
                    </span>
                    <span>
                      {String(
                        detailData.drainage.impervious_surface_pct ?? "—",
                      )}
                      %
                    </span>
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          {/* Evacuation Tab */}
          <TabsContent value="evacuation" className="space-y-4 mt-4">
            {bEvacCenters.length > 0 ? (
              bEvacCenters.map((c) => {
                const occPct =
                  c.capacity_total > 0
                    ? Math.round((c.capacity_current / c.capacity_total) * 100)
                    : 0;
                const status = !c.is_active
                  ? "Closed"
                  : occPct >= 100
                    ? "Full"
                    : "Open";
                return (
                  <div key={c.id} className="rounded-lg border p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-sm font-medium">{c.name}</p>
                        {c.address && (
                          <p className="text-xs text-muted-foreground">
                            {c.address}
                          </p>
                        )}
                      </div>
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-xs",
                          status === "Open"
                            ? "text-risk-safe border-risk-safe/30"
                            : status === "Full"
                              ? "text-risk-alert border-risk-alert/30"
                              : "text-risk-critical border-risk-critical/30",
                        )}
                      >
                        {status}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center mt-3">
                      <div>
                        <p className="text-lg font-bold">{c.capacity_total}</p>
                        <p className="text-[10px] text-muted-foreground">
                          Capacity
                        </p>
                      </div>
                      <div>
                        <p className="text-lg font-bold">
                          {c.capacity_current}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          Occupancy
                        </p>
                      </div>
                      <div>
                        <p className="text-lg font-bold">{occPct}%</p>
                        <p className="text-[10px] text-muted-foreground">
                          Full
                        </p>
                      </div>
                    </div>
                    {c.contact_number && (
                      <p className="text-xs text-muted-foreground mt-2">
                        Contact: {c.contact_number}
                      </p>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="rounded-lg border p-4">
                <p className="text-sm font-medium">
                  {barangay.evacuationCenter}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  No live capacity data available. Evacuation center from
                  configuration records.
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}

// ── Main Page ──

function SortableHead({
  label,
  field,
  sortField,
  toggleSort,
  className,
}: {
  label: string;
  field: SortField;
  sortField: SortField;
  toggleSort: (f: SortField) => void;
  className?: string;
}) {
  const active = sortField === field;
  return (
    <TableHead className={className}>
      <button
        className="flex items-center gap-1 hover:text-foreground transition-colors"
        onClick={() => toggleSort(field)}
      >
        {label}
        <ArrowUpDown
          className={cn(
            "h-3 w-3",
            active ? "text-primary" : "text-muted-foreground/40",
          )}
        />
      </button>
    </TableHead>
  );
}

export default function AdminBarangaysPage() {
  // ── State ──
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [zoneFilter, setZoneFilter] = useState<string>("all");
  const [evacFilter, setEvacFilter] = useState<string>("all");
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [rowsPerPage, setRowsPerPage] = useState<number>(16);
  const [page, setPage] = useState(1);
  const [overrides, setOverrides] =
    useState<Record<string, BarangayOverride>>(loadOverrides);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editEvac, setEditEvac] = useState("");
  const [editRisk, setEditRisk] = useState<FloodRisk>("low");
  const [editZone, setEditZone] = useState<BarangayZone>("Inland");
  const [detailKey, setDetailKey] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // ── Queries ──
  const queryClient = useQueryClient();
  const {
    data: hazardData,
    isLoading: hazardLoading,
    isError: hazardError,
    dataUpdatedAt,
    refetch,
  } = useHazardMap();
  const { data: evacData } = useEvacuationCenters();

  const hazardMap = useMemo(() => {
    const map = new Map<string, HazardFeatureProperties>();
    if (hazardData?.data?.features) {
      for (const f of hazardData.data.features) {
        map.set(f.properties.key, f.properties);
      }
    }
    return map;
  }, [hazardData]);

  const evacCentersByBarangay = useMemo(() => {
    const map = new Map<string, EvacuationCenterData[]>();
    if (evacData?.centers) {
      for (const c of evacData.centers) {
        const key = c.barangay.toLowerCase();
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(c);
      }
    }
    return map;
  }, [evacData]);

  // ── Merge static + live data ──
  const barangays: MergedBarangay[] = useMemo(() => {
    return BARANGAYS.map((b) => {
      const hazard = hazardMap.get(b.key);
      const override = overrides[b.key];
      const centers = evacCentersByBarangay.get(b.name.toLowerCase()) ?? [];
      const anyOpen = centers.some((c) => c.is_active);
      const anyFull = centers.some(
        (c) => c.is_active && c.capacity_current >= c.capacity_total,
      );
      const totalCap = centers.reduce((s, c) => s + c.capacity_total, 0);
      const totalCur = centers.reduce((s, c) => s + c.capacity_current, 0);

      let evacStatus: MergedBarangay["evacStatus"] = "Unknown";
      if (centers.length > 0) {
        if (!anyOpen) evacStatus = "Closed";
        else if (anyFull && totalCur >= totalCap) evacStatus = "Full";
        else evacStatus = "Open";
      }

      const liveRisk = hazard
        ? (hazard.hazard_classification as FloodRisk)
        : (override?.floodRisk ?? b.floodRisk);

      const density = b.area > 0 ? Math.round(b.population / b.area) : 0;
      const hasDataGap = b.floodEvents === 0 && liveRisk === "high";

      return {
        ...b,
        evacuationCenter: override?.evacuationCenter ?? b.evacuationCenter,
        floodRisk: override?.floodRisk ?? b.floodRisk,
        zone: override?.zone ?? b.zone,
        hazard_score: hazard?.hazard_score ?? 0,
        liveRisk,
        density,
        evacStatus,
        evacCapacity: totalCap,
        evacCurrent: totalCur,
        hasDataGap,
      };
    });
  }, [overrides, hazardMap, evacCentersByBarangay]);

  // ── Filtering ──
  const filtered = useMemo(() => {
    return barangays.filter((b) => {
      const matchSearch =
        !search || b.name.toLowerCase().includes(search.toLowerCase());
      const matchRisk = riskFilter === "all" || b.liveRisk === riskFilter;
      const matchZone = zoneFilter === "all" || b.zone === zoneFilter;
      const matchEvac = evacFilter === "all" || b.evacStatus === evacFilter;
      return matchSearch && matchRisk && matchZone && matchEvac;
    });
  }, [barangays, search, riskFilter, zoneFilter, evacFilter]);

  // ── Sorting ──
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "name":
          cmp = a.name.localeCompare(b.name);
          break;
        case "population":
          cmp = a.population - b.population;
          break;
        case "area":
          cmp = a.area - b.area;
          break;
        case "floodEvents":
          cmp = a.floodEvents - b.floodEvents;
          break;
        case "hazard_score":
          cmp = a.hazard_score - b.hazard_score;
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortField, sortDir]);

  // ── Pagination ──
  const totalPages =
    rowsPerPage === 0 ? 1 : Math.ceil(sorted.length / rowsPerPage);
  const paged =
    rowsPerPage === 0
      ? sorted
      : sorted.slice((page - 1) * rowsPerPage, page * rowsPerPage);

  // ── Risk counts (from live data) ──
  const riskCounts = useMemo(() => {
    const counts = { high: 0, moderate: 0, low: 0 };
    barangays.forEach((b) => counts[b.liveRisk]++);
    return counts;
  }, [barangays]);

  // ── Aggregate stats ──
  const totalPop = useMemo(
    () => barangays.reduce((s, b) => s + b.population, 0),
    [barangays],
  );
  const totalEvents = useMemo(
    () => barangays.reduce((s, b) => s + b.floodEvents, 0),
    [barangays],
  );

  // ── Derived ──
  const hasActiveFilters =
    search !== "" ||
    riskFilter !== "all" ||
    zoneFilter !== "all" ||
    evacFilter !== "all";

  const displayUpdatedAt =
    lastRefreshed ?? (dataUpdatedAt ? new Date(dataUpdatedAt) : null);
  const detailBarangay = barangays.find((b) => b.key === detailKey) ?? null;

  // ── Handlers ──
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await queryClient.invalidateQueries({
      queryKey: barangayQueryKeys.all,
    });
    setLastRefreshed(new Date());
    setIsRefreshing(false);
  }, [queryClient]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const clearFilters = () => {
    setSearch("");
    setRiskFilter("all");
    setZoneFilter("all");
    setEvacFilter("all");
    setPage(1);
  };

  function startEdit(b: MergedBarangay) {
    setEditingKey(b.key);
    setEditEvac(b.evacuationCenter);
    setEditRisk(b.floodRisk);
    setEditZone(b.zone);
  }

  function cancelEdit() {
    setEditingKey(null);
  }

  function saveEdit(key: string) {
    const next = { ...overrides };
    const original = BARANGAYS.find((b) => b.key === key);
    if (!original) return;

    const override: BarangayOverride = {};
    if (editEvac !== original.evacuationCenter)
      override.evacuationCenter = editEvac;
    if (editRisk !== original.floodRisk) override.floodRisk = editRisk;
    if (editZone !== original.zone) override.zone = editZone;

    if (Object.keys(override).length > 0) {
      next[key] = override;
    } else {
      delete next[key];
    }

    setOverrides(next);
    saveOverrides(next);
    setEditingKey(null);
    toast.success("Barangay configuration updated");
  }

  // ── Sortable header helper ──
  // Extracted to module scope (SortableHead below) to satisfy react-hooks/static-components

  // ── Refs for animations ──
  const riskRef = useRef<HTMLDivElement>(null);
  const riskInView = useInView(riskRef, { once: true, amount: 0.1 });
  const tableRef = useRef<HTMLDivElement>(null);
  const tableInView = useInView(tableRef, { once: true, amount: 0.1 });
  const statsRef = useRef<HTMLDivElement>(null);
  const statsInView = useInView(statsRef, { once: true, amount: 0.1 });

  // ── Stats config ──
  const STATS: {
    label: string;
    value: string | number;
    icon: React.ElementType;
    health: AccentLevel;
    description?: string;
  }[] = [
    {
      label: "Total Barangays",
      value: BARANGAYS.length,
      icon: Landmark,
      health: "neutral",
    },
    {
      label: "Total Population",
      value: totalPop.toLocaleString(),
      icon: Users,
      health: "neutral",
      description: "PSA 2020 Census",
    },
    {
      label: "High-Risk Areas",
      value: riskCounts.high,
      icon: AlertTriangle,
      health: "critical",
      description: "Live model classification",
    },
    {
      label: "Flood Events",
      value: totalEvents,
      icon: CloudRain,
      health: "warn",
      description: "DRRMO 2022–2025",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <div className="flex items-start justify-between">
          <PageHeader
            icon={MapPin}
            title="Barangay Management"
            subtitle={`Configure flood risk and evacuation data for all ${BARANGAYS.length} barangays`}
          />
          <div className="flex items-center gap-3 pt-1">
            {displayUpdatedAt && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated{" "}
                {formatDistanceToNow(displayUpdatedAt, { addSuffix: true })}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn("h-4 w-4 mr-1.5", isRefreshing && "animate-spin")}
              />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Stats Strip */}
      <section className="py-6 bg-background">
        <div className="w-full px-6" ref={statsRef}>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={statsInView ? "show" : undefined}
            className="grid gap-4 grid-cols-2 lg:grid-cols-4"
          >
            {STATS.map(({ label, value, icon, health, description }) => (
              <motion.div key={label} variants={fadeUp}>
                <StatCard
                  icon={icon}
                  label={label}
                  value={value}
                  isLoading={hazardLoading}
                  health={health}
                  description={description}
                />
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Risk Overview */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={riskRef}>
          <SectionHeading
            label="Summary"
            title="Risk Overview"
            subtitle="Current flood risk distribution across barangays"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={riskInView ? "show" : undefined}
          >
            {/* Risk Summary Cards */}
            <motion.div variants={fadeUp} className="grid gap-4 sm:grid-cols-3">
              {(["high", "moderate", "low"] as const).map((level) => {
                const Icon = RISK_ICONS[level];
                const health: AccentLevel =
                  level === "high"
                    ? "critical"
                    : level === "moderate"
                      ? "warn"
                      : "good";
                return (
                  <GlassCard
                    key={level}
                    className="overflow-hidden hover:shadow-lg transition-all duration-300"
                  >
                    <div
                      className={cn(
                        "h-1 w-full bg-linear-to-r",
                        accentGradient(health),
                      )}
                    />
                    <div className="pt-4 pb-3 px-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div
                            className={cn(
                              "flex h-7 w-7 items-center justify-center rounded-lg ring-1",
                              iconRing(health),
                            )}
                          >
                            <Icon
                              className={cn("h-4 w-4", statTextColor(health))}
                            />
                          </div>
                          <span className="text-sm font-medium capitalize">
                            {level} Risk
                          </span>
                        </div>
                        <span
                          className={cn(
                            "text-2xl font-bold",
                            statTextColor(health),
                          )}
                        >
                          {hazardLoading ? (
                            <Skeleton className="h-7 w-8" />
                          ) : (
                            riskCounts[level]
                          )}
                        </span>
                      </div>
                    </div>
                  </GlassCard>
                );
              })}
            </motion.div>

            {/* Distribution Bar */}
            <motion.div variants={fadeUp}>
              <RiskDistributionBar
                high={riskCounts.high}
                moderate={riskCounts.moderate}
                low={riskCounts.low}
                total={BARANGAYS.length}
              />
            </motion.div>

            {/* Filters */}
            <motion.div variants={fadeUp} className="flex flex-wrap gap-3 mt-6">
              <div className="relative flex-1 min-w-50 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search barangay..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="pl-9"
                />
              </div>
              <Select
                value={riskFilter}
                onValueChange={(v) => {
                  setRiskFilter(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Risk Level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Risk Levels</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="moderate">Moderate</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={zoneFilter}
                onValueChange={(v) => {
                  setZoneFilter(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-36">
                  <SelectValue placeholder="Zone Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Zones</SelectItem>
                  <SelectItem value="Coastal">Coastal</SelectItem>
                  <SelectItem value="Inland">Inland</SelectItem>
                  <SelectItem value="Low-lying">Low-lying</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={evacFilter}
                onValueChange={(v) => {
                  setEvacFilter(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Evac Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Centers</SelectItem>
                  <SelectItem value="Open">Open</SelectItem>
                  <SelectItem value="Full">Full</SelectItem>
                  <SelectItem value="Closed">Closed</SelectItem>
                </SelectContent>
              </Select>
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="text-muted-foreground"
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Clear
                </Button>
              )}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Barangay Directory */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={tableRef}>
          <SectionHeading
            label="Directory"
            title="Barangay Directory"
            subtitle={`Showing ${filtered.length} of ${BARANGAYS.length} barangays`}
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={tableInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <div className="pt-6 px-6 pb-6">
                  {/* Error State */}
                  {hazardError && !hazardLoading ? (
                    <div className="text-center py-16">
                      <XCircle className="h-12 w-12 mx-auto text-risk-critical/40 mb-4" />
                      <p className="text-muted-foreground mb-4">
                        Failed to load hazard data. Showing cached
                        configuration.
                      </p>
                      <Button variant="outline" onClick={() => refetch()}>
                        <RefreshCw className="h-4 w-4 mr-1.5" />
                        Retry
                      </Button>
                    </div>
                  ) : hazardLoading ? (
                    <div className="space-y-3">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Skeleton key={i} className="h-12 w-full" />
                      ))}
                    </div>
                  ) : filtered.length === 0 ? (
                    <div className="text-center py-16">
                      <MapPin className="h-12 w-12 mx-auto text-muted-foreground/30 mb-4" />
                      <p className="text-muted-foreground mb-1">
                        No barangays match the current filters
                      </p>
                      {hasActiveFilters && (
                        <Button
                          variant="link"
                          size="sm"
                          onClick={clearFilters}
                          className="text-primary"
                        >
                          Clear all filters
                        </Button>
                      )}
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <SortableHead label="Barangay" field="name" sortField={sortField} toggleSort={toggleSort} />
                            <SortableHead
                              label="Population"
                              field="population"
                              sortField={sortField}
                              toggleSort={toggleSort}
                            />
                            <SortableHead label="Area" field="area" sortField={sortField} toggleSort={toggleSort} />
                            <TableHead>Zone</TableHead>
                            <SortableHead
                              label="Flood Risk"
                              field="hazard_score"
                              sortField={sortField}
                              toggleSort={toggleSort}
                            />
                            <SortableHead label="Floods" field="floodEvents" sortField={sortField} toggleSort={toggleSort} />
                            <TableHead>Evac. Center</TableHead>
                            <TableHead>Evac. Status</TableHead>
                            <TableHead className="text-right">
                              Actions
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paged.map((b) => {
                            const isEditing = editingKey === b.key;
                            const RiskIcon = RISK_ICONS[b.liveRisk];
                            return (
                              <TableRow
                                key={b.key}
                                className="hover:bg-muted/40 transition-colors"
                              >
                                <TableCell className="font-medium">
                                  <div className="flex items-center gap-1.5">
                                    {b.name}
                                    {b.hasDataGap && (
                                      <AlertTriangle className="h-3.5 w-3.5 text-risk-alert shrink-0" />
                                    )}
                                  </div>
                                </TableCell>
                                <TableCell className="text-muted-foreground">
                                  {b.population.toLocaleString()}
                                  <span className="text-[10px] text-muted-foreground/60 ml-1">
                                    ({b.density.toLocaleString()}/km²)
                                  </span>
                                </TableCell>
                                <TableCell className="text-muted-foreground font-mono text-xs">
                                  {b.area} km²
                                </TableCell>
                                <TableCell>
                                  {isEditing ? (
                                    <Select
                                      value={editZone}
                                      onValueChange={(v) =>
                                        setEditZone(v as BarangayZone)
                                      }
                                    >
                                      <SelectTrigger className="w-28 h-8">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="Coastal">
                                          Coastal
                                        </SelectItem>
                                        <SelectItem value="Low-lying">
                                          Low-lying
                                        </SelectItem>
                                        <SelectItem value="Inland">
                                          Inland
                                        </SelectItem>
                                      </SelectContent>
                                    </Select>
                                  ) : (
                                    <Badge
                                      variant="outline"
                                      className={cn(
                                        "text-xs",
                                        ZONE_STYLES[b.zone],
                                      )}
                                    >
                                      {b.zone}
                                    </Badge>
                                  )}
                                </TableCell>
                                <TableCell>
                                  {isEditing ? (
                                    <Select
                                      value={editRisk}
                                      onValueChange={(v) =>
                                        setEditRisk(v as FloodRisk)
                                      }
                                    >
                                      <SelectTrigger className="w-30 h-8">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="high">
                                          High
                                        </SelectItem>
                                        <SelectItem value="moderate">
                                          Moderate
                                        </SelectItem>
                                        <SelectItem value="low">Low</SelectItem>
                                      </SelectContent>
                                    </Select>
                                  ) : (
                                    <Badge
                                      variant="outline"
                                      className={cn(
                                        "text-xs capitalize",
                                        RISK_STYLES[b.liveRisk],
                                      )}
                                    >
                                      <RiskIcon className="h-3 w-3 mr-1" />
                                      {b.liveRisk}
                                      <span className="ml-1 text-[10px] font-mono opacity-70">
                                        {(b.hazard_score * 100).toFixed(0)}%
                                      </span>
                                    </Badge>
                                  )}
                                </TableCell>
                                <TableCell className="text-muted-foreground font-mono text-sm">
                                  {b.floodEvents}
                                </TableCell>
                                <TableCell>
                                  {isEditing ? (
                                    <Input
                                      value={editEvac}
                                      onChange={(e) =>
                                        setEditEvac(e.target.value)
                                      }
                                      className="h-8 text-sm"
                                    />
                                  ) : (
                                    <span
                                      className="text-sm text-muted-foreground max-w-45 truncate block"
                                      title={b.evacuationCenter}
                                    >
                                      {b.evacuationCenter}
                                    </span>
                                  )}
                                </TableCell>
                                <TableCell>
                                  <Badge
                                    variant="outline"
                                    className={cn(
                                      "text-xs",
                                      b.evacStatus === "Open"
                                        ? "text-risk-safe border-risk-safe/30"
                                        : b.evacStatus === "Full"
                                          ? "text-risk-alert border-risk-alert/30"
                                          : b.evacStatus === "Closed"
                                            ? "text-risk-critical border-risk-critical/30"
                                            : "text-muted-foreground",
                                    )}
                                  >
                                    {b.evacStatus}
                                  </Badge>
                                </TableCell>
                                <TableCell className="text-right">
                                  {isEditing ? (
                                    <div className="flex justify-end gap-1">
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8"
                                        onClick={() => saveEdit(b.key)}
                                        aria-label="Save changes"
                                      >
                                        <Save className="h-4 w-4 text-risk-safe" />
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8"
                                        onClick={cancelEdit}
                                        aria-label="Cancel editing"
                                      >
                                        <X className="h-4 w-4 text-muted-foreground" />
                                      </Button>
                                    </div>
                                  ) : (
                                    <div className="flex justify-end gap-1">
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8"
                                        onClick={() => setDetailKey(b.key)}
                                        aria-label={`View details for ${b.name}`}
                                      >
                                        <Eye className="h-4 w-4" />
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8"
                                        onClick={() => startEdit(b)}
                                        aria-label={`Edit ${b.name}`}
                                      >
                                        <Edit2 className="h-4 w-4" />
                                      </Button>
                                    </div>
                                  )}
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  {/* Pagination */}
                  {!hazardError && sorted.length > 0 && (
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <div className="flex items-center gap-3">
                        <p className="text-sm text-muted-foreground">
                          Showing{" "}
                          {rowsPerPage === 0
                            ? sorted.length
                            : Math.min(
                                (page - 1) * rowsPerPage + 1,
                                sorted.length,
                              )}
                          –
                          {rowsPerPage === 0
                            ? sorted.length
                            : Math.min(page * rowsPerPage, sorted.length)}{" "}
                          of {sorted.length}
                        </p>
                        <Select
                          value={String(rowsPerPage)}
                          onValueChange={(v) => {
                            setRowsPerPage(Number(v));
                            setPage(1);
                          }}
                        >
                          <SelectTrigger className="w-24 h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="8">8 rows</SelectItem>
                            <SelectItem value="16">16 rows</SelectItem>
                            <SelectItem value="0">All</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      {totalPages > 1 && (
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={page <= 1}
                            onClick={() => setPage((p) => p - 1)}
                          >
                            Previous
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={page >= totalPages}
                            onClick={() => setPage((p) => p + 1)}
                          >
                            Next
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Detail Panel */}
      <BarangayDetailPanel
        barangay={detailBarangay}
        open={!!detailKey}
        onClose={() => setDetailKey(null)}
        evacCenters={evacData?.centers ?? []}
      />
    </div>
  );
}
