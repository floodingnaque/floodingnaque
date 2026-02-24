/**
 * Alerts Page
 *
 * Main page for viewing and managing flood alerts.
 * Features real-time SSE updates, filtering, and bulk actions.
 */

import { useState, useMemo } from 'react';
import { Bell, CheckCheck, RefreshCw, Calendar, Filter } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import {
  useAlerts,
  useAcknowledgeAlert,
  useAcknowledgeAll,
} from '@/features/alerts/hooks/useAlerts';
import { useAlertStream } from '@/features/alerts/hooks/useAlertStream';
import { AlertList } from '@/features/alerts/components/AlertList';
import { ConnectionStatus } from '@/features/alerts/components/ConnectionStatus';
import type { AlertParams, RiskLevel } from '@/types';

/**
 * Default pagination settings
 */
const DEFAULT_LIMIT = 20;

/**
 * AlertsPage component - Main alerts management interface
 */
export default function AlertsPage() {
  // Filter state
  const [page, setPage] = useState(1);
  const [riskLevel, setRiskLevel] = useState<RiskLevel | undefined>(undefined);
  const [acknowledged, setAcknowledged] = useState<boolean | undefined>(undefined);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // Build query params
  const queryParams: AlertParams = useMemo(
    () => ({
      page,
      limit: DEFAULT_LIMIT,
      risk_level: riskLevel,
      acknowledged,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      sort_by: 'triggered_at',
      order: 'desc',
    }),
    [page, riskLevel, acknowledged, startDate, endDate]
  );

  // Fetch alerts
  const {
    data: alertsData,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useAlerts(queryParams);

  // Mutations
  const { mutate: acknowledgeAlert } =
    useAcknowledgeAlert({
      onSuccess: () => refetch(),
    });

  const { mutate: acknowledgeAll, isPending: isAcknowledgingAll } =
    useAcknowledgeAll({
      onSuccess: () => refetch(),
    });

  // SSE Stream
  const { isConnected, reconnect, reconnectAttempts } = useAlertStream({
    enabled: true,
    onAlert: () => {
      // Refetch to include new alert in paginated view
      refetch();
    },
  });

  // Currently acknowledging alert ID
  const [acknowledgingId, setAcknowledgingId] = useState<number | null>(null);

  const handleAcknowledge = (alertId: number) => {
    setAcknowledgingId(alertId);
    acknowledgeAlert(alertId, {
      onSettled: () => setAcknowledgingId(null),
    });
  };

  const handleAcknowledgeAll = () => {
    acknowledgeAll();
  };

  // Reset filters
  const handleResetFilters = () => {
    setPage(1);
    setRiskLevel(undefined);
    setAcknowledged(undefined);
    setStartDate('');
    setEndDate('');
  };

  // Pagination
  const totalPages = alertsData?.pages ?? 1;
  const hasFilters =
    riskLevel !== undefined ||
    acknowledged !== undefined ||
    startDate ||
    endDate;

  // Calculate unacknowledged count
  const unacknowledgedCount =
    alertsData?.data?.filter((a) => !a.acknowledged).length ?? 0;

  return (
    <div className="container max-w-6xl py-8 px-4">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <Bell className="h-8 w-8 text-foreground" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Alerts</h1>
            <p className="text-muted-foreground">
              Monitor and manage flood risk alerts
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Connection Status */}
          <ConnectionStatus
            isConnected={isConnected}
            onReconnect={reconnect}
            isReconnecting={reconnectAttempts > 0 && !isConnected}
          />

          {/* Refresh Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>

          {/* Acknowledge All */}
          <Button
            variant="default"
            size="sm"
            onClick={handleAcknowledgeAll}
            disabled={isAcknowledgingAll || unacknowledgedCount === 0}
          >
            <CheckCheck className="h-4 w-4 mr-2" />
            {isAcknowledgingAll
              ? 'Acknowledging...'
              : `Acknowledge All${unacknowledgedCount > 0 ? ` (${unacknowledgedCount})` : ''}`}
          </Button>
        </div>
      </div>

      {/* Filters Card */}
      <Card className="mb-6">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filters
            </CardTitle>
            {hasFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResetFilters}
              >
                Reset Filters
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Risk Level Filter */}
            <div className="space-y-2">
              <Label htmlFor="risk-level">Risk Level</Label>
              <Select
                value={riskLevel !== undefined ? String(riskLevel) : 'all'}
                onValueChange={(value) =>
                  setRiskLevel(value === 'all' ? undefined : (Number(value) as RiskLevel))
                }
              >
                <SelectTrigger id="risk-level">
                  <SelectValue placeholder="All Levels" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Levels</SelectItem>
                  <SelectItem value="0">Safe</SelectItem>
                  <SelectItem value="1">Alert</SelectItem>
                  <SelectItem value="2">Critical</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Status Filter */}
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select
                value={
                  acknowledged === undefined
                    ? 'all'
                    : acknowledged
                      ? 'acknowledged'
                      : 'pending'
                }
                onValueChange={(value) =>
                  setAcknowledged(
                    value === 'all'
                      ? undefined
                      : value === 'acknowledged'
                  )
                }
              >
                <SelectTrigger id="status">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="acknowledged">Acknowledged</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Start Date */}
            <div className="space-y-2">
              <Label htmlFor="start-date">From Date</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* End Date */}
            <div className="space-y-2">
              <Label htmlFor="end-date">To Date</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="end-date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Summary */}
      {alertsData && (
        <div className="flex items-center justify-between mb-4 text-sm text-muted-foreground">
          <span>
            Showing {alertsData.data.length} of {alertsData.total} alerts
            {hasFilters && ' (filtered)'}
          </span>
          <span>
            Page {page} of {totalPages}
          </span>
        </div>
      )}

      {/* Error State */}
      {isError && (
        <Card className="mb-6 border-destructive">
          <CardContent className="py-6">
            <div className="text-center">
              <p className="text-destructive font-medium">
                Failed to load alerts
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {error?.message || 'An unknown error occurred'}
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

      {/* Alerts List */}
      <AlertList
        alerts={alertsData?.data ?? []}
        isLoading={isLoading}
        onAcknowledge={handleAcknowledge}
        acknowledgingId={acknowledgingId}
        emptyMessage="No alerts found"
      />

      {/* Pagination */}
      {alertsData && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || isFetching}
          >
            Previous
          </Button>

          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              // Calculate page number to show
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (page <= 3) {
                pageNum = i + 1;
              } else if (page >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = page - 2 + i;
              }

              return (
                <Button
                  key={pageNum}
                  variant={page === pageNum ? 'default' : 'outline'}
                  size="sm"
                  className="w-9"
                  onClick={() => setPage(pageNum)}
                  disabled={isFetching}
                >
                  {pageNum}
                </Button>
              );
            })}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || isFetching}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
