/**
 * Weather History Page
 *
 * Main page for viewing weather data history with statistics,
 * interactive charts, and sortable data tables.
 */

import { useState, useMemo } from 'react';
import { BarChart3, Table2, RefreshCw, CloudSun } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { useWeatherData, useWeatherStats } from '@/features/weather/hooks/useWeather';
import { WeatherStatsCards } from '@/features/weather/components/WeatherStatsCards';
import { WeatherChart } from '@/features/weather/components/WeatherChart';
import { WeatherTable } from '@/features/weather/components/WeatherTable';
import { DateRangeFilter, type DateRange } from '@/features/weather/components/DateRangeFilter';
import type { WeatherDataParams, WeatherSource } from '@/types';

/**
 * Default pagination settings
 */
const DEFAULT_LIMIT = 100;

/**
 * View mode options
 */
type ViewMode = 'chart' | 'table';

/**
 * HistoryPage component - Weather data history interface
 */
export default function HistoryPage() {
  // Filter state
  const [page, setPage] = useState(1);
  const [dateRange, setDateRange] = useState<DateRange>({});
  const [source, setSource] = useState<WeatherSource | 'all'>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('chart');

  // Build query params
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

  // Handle source filter change
  const handleSourceChange = (value: string) => {
    setSource(value as WeatherSource | 'all');
    setPage(1);
  };

  // Handle date range change
  const handleDateRangeChange = (range: DateRange) => {
    setDateRange(range);
    setPage(1);
  };

  // Handle refresh
  const handleRefresh = () => {
    refetch();
  };

  // Pagination
  const totalPages = weatherData?.pages || 1;
  const currentPage = weatherData?.page || 1;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <CloudSun className="h-8 w-8" />
            Weather History
          </h1>
          <p className="text-muted-foreground mt-1">
            View and analyze historical weather data
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleRefresh}
          disabled={isFetching}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Filters Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Date Range Filter */}
          <DateRangeFilter value={dateRange} onChange={handleDateRangeChange} />

          {/* Source Filter and View Toggle */}
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

            {/* View Mode Toggle */}
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

      {/* Stats Cards */}
      <WeatherStatsCards stats={stats} isLoading={isLoadingStats} />

      {/* Error State */}
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
                onClick={handleRefresh}
                className="mt-4"
              >
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Data Display - Chart or Table */}
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

          {/* Pagination Controls */}
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
    </div>
  );
}
