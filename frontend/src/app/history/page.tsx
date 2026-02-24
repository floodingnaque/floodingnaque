/**
 * History Page
 *
 * Tabbed page for viewing weather data and prediction history.
 * Weather tab: statistics, interactive charts, and sortable data tables.
 * Predictions tab: paginated list of past flood predictions.
 */

import { useState, useMemo, useCallback, lazy, Suspense } from 'react';
import {
  BarChart3,
  Table2,
  RefreshCw,
  CloudSun,
  Activity,
  AlertTriangle,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { useWeatherData, useWeatherStats } from '@/features/weather/hooks/useWeather';
import { WeatherStatsCards } from '@/features/weather/components/WeatherStatsCards';
import { DateRangeFilter, type DateRange } from '@/features/weather/components/DateRangeFilter';
import { usePredictionHistory } from '@/features/predictions/hooks/usePredictionHistory';
import type { WeatherDataParams, WeatherSource } from '@/types';
import { cn } from '@/lib/utils';

// Lazy-load heavy chart/table components
const WeatherChart = lazy(() =>
  import('@/features/weather/components/WeatherChart').then((m) => ({ default: m.WeatherChart }))
);
const WeatherTable = lazy(() =>
  import('@/features/weather/components/WeatherTable').then((m) => ({ default: m.WeatherTable }))
);

/** Fallback skeleton while chart/table loads */
function DataViewSkeleton() {
  return (
    <Card>
      <CardContent className="pt-6">
        <Skeleton className="h-[400px] w-full rounded-md" />
      </CardContent>
    </Card>
  );
}

/**
 * Default pagination settings
 */
const DEFAULT_LIMIT = 100;

/**
 * View mode options
 */
type ViewMode = 'chart' | 'table';

/**
 * Data category tabs
 */
type DataTab = 'weather' | 'predictions';

/**
 * Get risk label and color from numeric level
 */
function getRiskLabel(level: number): { label: string; className: string } {
  if (level === 0 || level <= 25) {
    return {
      label: 'Low',
      className: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    };
  }
  if (level === 1 || level <= 50) {
    return {
      label: 'Moderate',
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    };
  }
  return {
    label: 'High',
    className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  };
}

/**
 * HistoryPage component – Weather & Prediction history interface
 */
export default function HistoryPage() {
  // Top-level tab
  const [dataTab, setDataTab] = useState<DataTab>('weather');

  // Weather filter state
  const [page, setPage] = useState(1);
  const [dateRange, setDateRange] = useState<DateRange>({});
  const [source, setSource] = useState<WeatherSource | 'all'>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('chart');

  // Prediction filter state
  const [predPage, setPredPage] = useState(1);

  // Build weather query params
  const queryParams: WeatherDataParams = useMemo(
    () => ({
      page,
      limit: DEFAULT_LIMIT,
      source: source !== 'all' ? source : undefined,
      start_date: dateRange.start_date,
      end_date: dateRange.end_date,
      sort_by: 'recorded_at',
      order: 'desc',
    }),
    [page, source, dateRange]
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
  const {
    data: stats,
    isLoading: isLoadingStats,
  } = useWeatherStats({
    start_date: dateRange.start_date,
    end_date: dateRange.end_date,
  });

  // Fetch prediction history
  const {
    data: predData,
    isLoading: predLoading,
    isFetching: predFetching,
    refetch: predRefetch,
  } = usePredictionHistory({
    page: predPage,
    limit: 50,
    sort_by: 'created_at',
    order: 'desc',
  });

  // Handlers
  const handleSourceChange = useCallback((value: string) => {
    setSource(value as WeatherSource | 'all');
    setPage(1);
  }, []);

  const handleDateRangeChange = useCallback((range: DateRange) => {
    setDateRange(range);
    setPage(1);
  }, []);

  const handleRefresh = useCallback(() => {
    if (dataTab === 'weather') {
      refetch();
    } else {
      predRefetch();
    }
  }, [dataTab, refetch, predRefetch]);

  // Pagination
  const totalPages = weatherData?.pages || 1;
  const currentPage = weatherData?.page || 1;
  const predTotalPages = predData?.pages || 1;
  const predCurrentPage = predData?.page || 1;

  const isRefreshing = dataTab === 'weather' ? isFetching : predFetching;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <CloudSun className="h-8 w-8" />
            History
          </h1>
          <p className="text-muted-foreground mt-1">
            View and analyze historical weather and prediction data
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Data Category Tabs */}
      <Tabs value={dataTab} onValueChange={(v) => setDataTab(v as DataTab)}>
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
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Filters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <DateRangeFilter value={dateRange} onChange={handleDateRangeChange} />
              <div className="flex flex-wrap gap-4 items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Source:</span>
                  <Select value={source} onValueChange={handleSourceChange}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue placeholder="All Sources" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Sources</SelectItem>
                      <SelectItem value="OWM">OpenWeatherMap</SelectItem>
                      <SelectItem value="Meteostat">Meteostat</SelectItem>
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
            </CardContent>
          </Card>

          {/* Stats */}
          <WeatherStatsCards stats={stats} isLoading={isLoadingStats} />

          {/* Error */}
          {isError && (
            <Card className="border-destructive">
              <CardContent className="pt-6">
                <div className="text-center text-destructive">
                  <p className="font-medium">Error loading weather data</p>
                  <p className="text-sm mt-1">
                    {error?.message || 'An unexpected error occurred'}
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
              </CardContent>
            </Card>
          )}

          {/* Chart / Table */}
          <Suspense fallback={<DataViewSkeleton />}>
            {!isError && viewMode === 'chart' && (
              <WeatherChart
                data={weatherData?.data || []}
                isLoading={isLoadingData}
                title="Weather Trends Over Time"
              />
            )}

            {!isError && viewMode === 'table' && (
              <>
                <WeatherTable
                  data={weatherData?.data || []}
                  isLoading={isLoadingData}
                />
                {weatherData && totalPages > 1 && (
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                      Showing {weatherData.data.length} of {weatherData.total} records
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
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
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
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
          {/* Predictions Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Prediction History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {predLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : !predData?.data?.length ? (
                <div className="text-center py-8 text-muted-foreground">
                  <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No predictions found</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Risk Level</TableHead>
                      <TableHead>Flood Probability</TableHead>
                      <TableHead>Location</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {predData.data.map((pred) => {
                      const risk = getRiskLabel(pred.risk_level);
                      return (
                        <TableRow key={pred.id}>
                          <TableCell className="text-sm">
                            {new Date(pred.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="secondary"
                              className={cn('text-xs', risk.className)}
                            >
                              {risk.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-medium">
                            {typeof pred.flood_probability === 'number'
                              ? `${(pred.flood_probability * 100).toFixed(1)}%`
                              : '—'}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {pred.location || '—'}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Prediction Pagination */}
          {predData && predTotalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {predData.data.length} of {predData.total} predictions
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
                  onClick={() => setPredPage((p) => Math.min(predTotalPages, p + 1))}
                  disabled={predCurrentPage >= predTotalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
