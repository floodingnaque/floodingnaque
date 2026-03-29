/**
 * History Page
 *
 * Tabbed page for viewing weather data and prediction history.
 * Weather tab: statistics, interactive charts, and sortable data tables.
 * Predictions tab: paginated list of past flood predictions.
 */

import { format } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CloudSun,
  Download,
  RefreshCw,
  Table2,
} from "lucide-react";
import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useSearchParams } from "react-router-dom";

import { SectionHeading } from "@/components/layout/SectionHeading";
import { fadeUp, staggerContainer } from "@/lib/motion";

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

import { StaleDataBanner } from "@/components/feedback/StaleDataBanner";
import type { TimelineItem } from "@/features/predictions/components/TimelineScrubber";
import { TimelineScrubber } from "@/features/predictions/components/TimelineScrubber";
import {
  useOfflinePredictions,
  usePredictionHistory,
} from "@/features/predictions/hooks/usePredictionHistory";
import {
  DateRangeFilter,
  type DateRange,
} from "@/features/weather/components/DateRangeFilter";
import { WeatherStatsCards } from "@/features/weather/components/WeatherStatsCards";
import {
  useWeatherData,
  useWeatherStats,
} from "@/features/weather/hooks/useWeather";
import { cn } from "@/lib/utils";
import type { WeatherDataParams, WeatherSource } from "@/types";

// Lazy-load heavy chart/table components
const WeatherChart = lazy(() =>
  import("@/features/weather/components/WeatherChart").then((m) => ({
    default: m.WeatherChart,
  })),
);
const WeatherTable = lazy(() =>
  import("@/features/weather/components/WeatherTable").then((m) => ({
    default: m.WeatherTable,
  })),
);

/** Fallback skeleton while chart/table loads */
function DataViewSkeleton() {
  return (
    <GlassCard className="overflow-hidden">
      <div className="pt-6 px-6 pb-6">
        <Skeleton className="h-100 w-full rounded-md" />
      </div>
    </GlassCard>
  );
}

/**
 * Default pagination settings
 */
const DEFAULT_LIMIT = 100;

/**
 * View mode options
 */
type ViewMode = "chart" | "table";

/**
 * Data category tabs
 */
type DataTab = "weather" | "predictions";

/**
 * Get risk label and color from numeric level
 */
function getRiskLabel(level: number): { label: string; className: string } {
  if (level === 0 || level <= 25) {
    return {
      label: "Low",
      className: "bg-risk-safe/15 text-risk-safe",
    };
  }
  if (level === 1 || level <= 50) {
    return {
      label: "Moderate",
      className: "bg-risk-alert/15 text-risk-alert",
    };
  }
  return {
    label: "High",
    className: "bg-risk-critical/15 text-risk-critical",
  };
}

/**
 * HistoryPage component – Weather & Prediction history interface
 */
export default function HistoryPage() {
  const [searchParams] = useSearchParams();
  const initialTab =
    searchParams.get("tab") === "predictions" ? "predictions" : "weather";

  // Top-level tab
  const [dataTab, setDataTab] = useState<DataTab>(initialTab);

  // Weather filter state (persisted across tab switches)
  const [page, setPage] = useState(1);
  const [dateRange, setDateRange] = useState<DateRange>({});
  const [source, setSource] = useState<WeatherSource | "all">("all");
  const [viewMode, setViewMode] = useState<ViewMode>("chart");

  // Prediction filter state (persisted across tab switches)
  const [predPage, setPredPage] = useState(1);
  const [predDateRange, setPredDateRange] = useState<DateRange>({});

  // Timeline scrubber state
  const [timelineIndex, setTimelineIndex] = useState(0);

  // Last updated
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Build weather query params
  const queryParams: WeatherDataParams = useMemo(
    () => ({
      page,
      limit: DEFAULT_LIMIT,
      source: source !== "all" ? source : undefined,
      start_date: dateRange.start_date,
      end_date: dateRange.end_date,
      sort_by: "recorded_at",
      order: "desc",
    }),
    [page, source, dateRange],
  );

  // Fetch weather data
  const {
    data: weatherData,
    isLoading: isLoadingData,
    isError,
    error,
    refetch,
    isFetching,
  } = useWeatherData(queryParams);

  // Fetch weather stats
  const { data: stats, isLoading: isLoadingStats } = useWeatherStats({
    start_date: dateRange.start_date,
    end_date: dateRange.end_date,
  });

  // Fetch prediction history (with date range filters)
  const {
    data: predData,
    isLoading: predLoading,
    isFetching: predFetching,
    refetch: predRefetch,
  } = usePredictionHistory({
    page: predPage,
    limit: 50,
    sort_by: "created_at",
    order: "desc",
    start_date: predDateRange.start_date,
    end_date: predDateRange.end_date,
  });

  // Offline fallback for predictions
  const {
    data: offlinePredData,
    cachedAt,
    isOffline,
  } = useOfflinePredictions(50);

  // Use offline data when online data is unavailable and user is offline
  const effectivePredData = predData ?? (isOffline ? offlinePredData : null);

  // Build timeline items from prediction data (oldest → newest for scrubber)
  const timelineItems: TimelineItem[] = useMemo(() => {
    const rows = effectivePredData?.data;
    if (!rows?.length) return [];
    return [...rows].reverse().map((pred) => ({
      timestamp: pred.created_at,
      risk_label: pred.risk_label ?? getRiskLabel(pred.risk_level).label,
    }));
  }, [effectivePredData]);

  // Reset timeline index when data changes
  useEffect(() => {
    setTimelineIndex(0);
  }, [timelineItems.length]);

  // Handlers
  const handleSourceChange = useCallback((value: string) => {
    setSource(value as WeatherSource | "all");
    setPage(1);
  }, []);

  const handleDateRangeChange = useCallback((range: DateRange) => {
    setDateRange(range);
    setPage(1);
  }, []);

  const handlePredDateRangeChange = useCallback((range: DateRange) => {
    setPredDateRange(range);
    setPredPage(1);
  }, []);

  const handleRefresh = useCallback(() => {
    if (dataTab === "weather") {
      refetch().then(() => setLastUpdated(new Date()));
    } else {
      predRefetch().then(() => setLastUpdated(new Date()));
    }
  }, [dataTab, refetch, predRefetch]);

  // Prediction CSV export
  const handleExportPredictionsCsv = useCallback(() => {
    const rows = effectivePredData?.data;
    if (!rows?.length) return;
    const header =
      "Date,Risk Level,Risk Label,Flood Probability (%),Confidence (%),Model Version,Model,Temperature (°C),Humidity (%),Precipitation (mm)";
    const csvRows = rows.map((pred) => {
      const inputs = pred.input_data as
        | Record<string, number | undefined>
        | undefined;
      return [
        format(new Date(pred.created_at), "yyyy-MM-dd HH:mm"),
        pred.risk_level,
        pred.risk_label ?? getRiskLabel(pred.risk_level).label,
        (pred.flood_probability * 100).toFixed(1),
        (pred.flood_probability * 100).toFixed(1),
        pred.model_version ?? "",
        pred.model_name ?? "",
        inputs?.temperature != null
          ? (Number(inputs.temperature) - 273.15).toFixed(1)
          : "",
        inputs?.humidity != null ? Number(inputs.humidity).toFixed(1) : "",
        inputs?.precipitation != null
          ? Number(inputs.precipitation).toFixed(2)
          : "",
      ].join(",");
    });
    const csv = [header, ...csvRows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `predictions_${format(new Date(), "yyyyMMdd_HHmmss")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [effectivePredData]);

  // Pagination
  const totalPages = weatherData?.pages || 1;
  const currentPage = weatherData?.page || 1;
  const predTotalPages = predData?.pages || 1;
  const predCurrentPage = predData?.page || 1;

  const isRefreshing = dataTab === "weather" ? isFetching : predFetching;

  const contentRef = useRef<HTMLDivElement>(null);
  const contentInView = useInView(contentRef, { once: true, amount: 0.05 });

  return (
    <div className="min-h-screen bg-background">
      {/* Header Actions */}
      <div className="w-full px-6 pt-6">
        <div className="flex items-center justify-end gap-3">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              Updated {format(lastUpdated, "h:mm:ss a")}
            </span>
          )}
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Tabbed Content */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={contentRef}>
          <SectionHeading
            label="Data Explorer"
            title="Weather & Predictions"
            subtitle="Switch between weather observations and historical predictions to analyze past data"
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={contentInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <Tabs
                value={dataTab}
                onValueChange={(v) => setDataTab(v as DataTab)}
              >
                <TabsList>
                  <TabsTrigger value="weather" className="gap-2">
                    <CloudSun className="h-4 w-4" />
                    Weather Data
                  </TabsTrigger>
                  <TabsTrigger value="predictions" className="gap-2">
                    <Activity className="h-4 w-4" />
                    Predictions
                  </TabsTrigger>
                </TabsList>

                {/* ======== Weather Tab ======== */}
                <TabsContent value="weather" className="space-y-6 mt-6">
                  {/* Filters */}
                  <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                    <div className="p-6 pb-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                          <BarChart3 className="h-5 w-5 text-primary" />
                        </div>
                        <h3 className="text-lg font-semibold">Filters</h3>
                      </div>
                    </div>
                    <div className="px-6 pb-6 space-y-4">
                      <DateRangeFilter
                        value={dateRange}
                        onChange={handleDateRangeChange}
                      />
                      <div className="flex flex-wrap gap-4 items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">Source:</span>
                          <Select
                            value={source}
                            onValueChange={handleSourceChange}
                          >
                            <SelectTrigger className="w-37.5">
                              <SelectValue placeholder="All Sources" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="all">All Sources</SelectItem>
                              <SelectItem value="OWM">
                                OpenWeatherMap
                              </SelectItem>
                              <SelectItem value="Meteostat">
                                Meteostat
                              </SelectItem>
                              <SelectItem value="Google">Google</SelectItem>
                              <SelectItem value="Manual">Manual</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <Tabs
                          value={viewMode}
                          onValueChange={(v) => setViewMode(v as ViewMode)}
                        >
                          <TabsList>
                            <TabsTrigger value="chart" className="gap-2">
                              <BarChart3 className="h-4 w-4" />
                              Chart
                            </TabsTrigger>
                            <TabsTrigger value="table" className="gap-2">
                              <Table2 className="h-4 w-4" />
                              Table
                            </TabsTrigger>
                          </TabsList>
                        </Tabs>
                      </div>
                    </div>
                  </GlassCard>

                  {/* Stats */}
                  <WeatherStatsCards stats={stats} isLoading={isLoadingStats} />

                  {/* Error */}
                  {isError && (
                    <GlassCard className="border-destructive/40 overflow-hidden">
                      <div className="h-1 w-full bg-linear-to-r from-destructive/60 via-destructive to-destructive/60" />
                      <div className="pt-6 px-6 pb-6">
                        <div className="text-center text-destructive">
                          <p className="font-medium">
                            Error loading weather data
                          </p>
                          <p className="text-sm mt-1">
                            {error?.message || "An unexpected error occurred"}
                          </p>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => refetch()}
                            className="mt-4"
                          >
                            Try Again
                          </Button>
                        </div>
                      </div>
                    </GlassCard>
                  )}

                  {/* Chart / Table */}
                  <Suspense fallback={<DataViewSkeleton />}>
                    {!isError && viewMode === "chart" && (
                      <WeatherChart
                        data={weatherData?.data || []}
                        isLoading={isLoadingData}
                        title="Weather Trends Over Time"
                      />
                    )}

                    {!isError && viewMode === "table" && (
                      <>
                        <WeatherTable
                          data={weatherData?.data || []}
                          isLoading={isLoadingData}
                        />
                        {weatherData && totalPages > 1 && (
                          <div className="flex items-center justify-between">
                            <p className="text-sm text-muted-foreground">
                              Showing {weatherData.data.length} of{" "}
                              {weatherData.total} records
                            </p>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  setPage((p) => Math.max(1, p - 1))
                                }
                                disabled={currentPage <= 1}
                              >
                                Previous
                              </Button>
                              <span className="text-sm">
                                Page {currentPage} of {totalPages}
                              </span>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  setPage((p) => Math.min(totalPages, p + 1))
                                }
                                disabled={currentPage >= totalPages}
                              >
                                Next
                              </Button>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </Suspense>
                </TabsContent>

                {/* ======== Predictions Tab ======== */}
                <TabsContent value="predictions" className="space-y-6 mt-6">
                  {/* Offline banner */}
                  {isOffline && effectivePredData && (
                    <StaleDataBanner cachedAt={cachedAt ?? undefined} />
                  )}

                  {/* Prediction Filters */}
                  <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                    <div className="p-6 pb-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                          <BarChart3 className="h-5 w-5 text-primary" />
                        </div>
                        <h3 className="text-lg font-semibold">Filters</h3>
                      </div>
                    </div>
                    <div className="px-6 pb-6">
                      <DateRangeFilter
                        value={predDateRange}
                        onChange={handlePredDateRangeChange}
                      />
                    </div>
                  </GlassCard>

                  {/* Timeline Scrubber */}
                  {timelineItems.length > 1 && (
                    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                      <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                      <div className="p-6">
                        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                          <Activity className="h-4 w-4 text-primary" />
                          Timeline Replay
                        </h3>
                        <TimelineScrubber
                          items={timelineItems}
                          index={timelineIndex}
                          onIndexChange={setTimelineIndex}
                          speed={600}
                        />
                      </div>
                    </GlassCard>
                  )}

                  {/* Predictions Table */}
                  <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                    <div className="p-6 pb-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                          <Activity className="h-5 w-5 text-primary" />
                        </div>
                        <h3 className="text-lg font-semibold">
                          Prediction History
                        </h3>
                      </div>
                      {effectivePredData?.data?.length ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleExportPredictionsCsv}
                          className="gap-2"
                        >
                          <Download className="h-4 w-4" />
                          Export CSV
                        </Button>
                      ) : null}
                    </div>
                    <div className="px-6 pb-6">
                      {predLoading && !isOffline ? (
                        <div className="space-y-3">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Skeleton key={i} className="h-12 w-full" />
                          ))}
                        </div>
                      ) : !effectivePredData?.data?.length ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          <p>No predictions found</p>
                        </div>
                      ) : (
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Date</TableHead>
                                <TableHead>Risk Level</TableHead>
                                <TableHead>Flood Probability</TableHead>
                                <TableHead>Confidence</TableHead>
                                <TableHead>Model</TableHead>
                                <TableHead>Inputs</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {effectivePredData.data.map((pred, rowIdx) => {
                                const risk = getRiskLabel(pred.risk_level);
                                const inputs = pred.input_data as
                                  | Record<string, number | undefined>
                                  | undefined;
                                // Highlight active timeline row (timeline is reversed relative to table)
                                const isTimelineActive =
                                  timelineItems.length > 1 &&
                                  rowIdx ===
                                    timelineItems.length - 1 - timelineIndex;
                                return (
                                  <TableRow
                                    key={pred.id}
                                    className={cn(
                                      isTimelineActive &&
                                        "bg-primary/10 ring-1 ring-primary/30",
                                    )}
                                  >
                                    <TableCell className="text-sm whitespace-nowrap">
                                      {format(
                                        new Date(pred.created_at),
                                        "MMM dd, yyyy HH:mm",
                                      )}
                                    </TableCell>
                                    <TableCell>
                                      <Badge
                                        variant="secondary"
                                        className={cn(
                                          "text-xs",
                                          risk.className,
                                        )}
                                      >
                                        {pred.risk_label ?? risk.label}
                                      </Badge>
                                    </TableCell>
                                    <TableCell className="font-medium">
                                      {typeof pred.flood_probability ===
                                      "number"
                                        ? `${(pred.flood_probability * 100).toFixed(1)}%`
                                        : "-"}
                                    </TableCell>
                                    <TableCell className="text-sm">
                                      {typeof pred.flood_probability ===
                                      "number"
                                        ? `${(pred.flood_probability * 100).toFixed(1)}%`
                                        : "-"}
                                    </TableCell>
                                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                                      {pred.model_version
                                        ? `v${pred.model_version}`
                                        : "-"}
                                      {pred.model_name
                                        ? ` (${pred.model_name})`
                                        : ""}
                                    </TableCell>
                                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                                      {inputs
                                        ? [
                                            inputs.temperature != null &&
                                              `${Math.round(Number(inputs.temperature) - 273.15)}°C`,
                                            inputs.humidity != null &&
                                              `${Number(inputs.humidity).toFixed(0)}% RH`,
                                            inputs.precipitation != null &&
                                              `${Number(inputs.precipitation).toFixed(1)} mm`,
                                          ]
                                            .filter(Boolean)
                                            .join(" · ") || "-"
                                        : "-"}
                                    </TableCell>
                                  </TableRow>
                                );
                              })}
                            </TableBody>
                          </Table>
                        </div>
                      )}
                    </div>
                  </GlassCard>

                  {/* Prediction Pagination */}
                  {predData && predTotalPages > 1 && (
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">
                        Showing {predData.data.length} of {predData.total}{" "}
                        predictions
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPredPage((p) => Math.max(1, p - 1))}
                          disabled={predCurrentPage <= 1}
                        >
                          Previous
                        </Button>
                        <span className="text-sm">
                          Page {predCurrentPage} of {predTotalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            setPredPage((p) => Math.min(predTotalPages, p + 1))
                          }
                          disabled={predCurrentPage >= predTotalPages}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </motion.div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
