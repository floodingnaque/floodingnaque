/**
 * Alerts Page
 *
 * Main page for viewing and managing flood alerts.
 * Features real-time SSE updates, filtering, and bulk actions.
 */

import { motion, useInView } from "framer-motion";
import { Calendar, CheckCheck, Filter, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { SectionHeading } from "@/components/layout/SectionHeading";
import { fadeUp, staggerContainer } from "@/lib/motion";

import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { AlertList } from "@/features/alerts/components/AlertList";
import { ConnectionStatus } from "@/features/alerts/components/ConnectionStatus";
import {
  useAcknowledgeAlert,
  useAcknowledgeAll,
  useAlerts,
} from "@/features/alerts/hooks/useAlerts";
import { useAlertStore } from "@/state/stores/alertStore";
import type { AlertParams, RiskLevel } from "@/types";

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
  const [acknowledged, setAcknowledged] = useState<boolean | undefined>(
    undefined,
  );
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // Build query params
  const queryParams: AlertParams = useMemo(
    () => ({
      page,
      limit: DEFAULT_LIMIT,
      risk_level: riskLevel,
      acknowledged,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      sort_by: "triggered_at",
      order: "desc",
    }),
    [page, riskLevel, acknowledged, startDate, endDate],
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
  const { mutate: acknowledgeAlert } = useAcknowledgeAlert({
    onSuccess: () => refetch(),
  });

  const { mutate: acknowledgeAll, isPending: isAcknowledgingAll } =
    useAcknowledgeAll({
      onSuccess: () => refetch(),
    });

  // Subscribe to live alerts from the layout's SSE connection.
  // Instead of opening a duplicate EventSource, we watch the store's
  // liveAlerts array and auto-refetch when a new alert arrives.
  // Use primitive selectors to avoid getSnapshot instability (infinite loops).
  const isConnected = useAlertStore((s) => s.connectionState === "CONNECTED");
  const liveAlerts = useAlertStore((s) => s.liveAlerts);
  const prevAlertsLenRef = useRef(liveAlerts.length);

  useEffect(() => {
    if (liveAlerts.length > prevAlertsLenRef.current) {
      // New alert pushed via SSE - refetch paginated list
      refetch();
    }
    prevAlertsLenRef.current = liveAlerts.length;
  }, [liveAlerts.length, refetch]);

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
    setStartDate("");
    setEndDate("");
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

  // refs for scroll-triggered sections
  const filtersRef = useRef<HTMLDivElement>(null);
  const filtersInView = useInView(filtersRef, { once: true, amount: 0.1 });
  const listRef = useRef<HTMLDivElement>(null);
  const listInView = useInView(listRef, { once: true, amount: 0.05 });

  return (
    <div className="min-h-screen bg-background">
      {/* Header Actions */}
      <div className="w-full px-6 pt-6">
        <div className="flex items-center justify-end gap-3">
          <ConnectionStatus
            isConnected={isConnected}
            showReconnectButton={false}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isFetching ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleAcknowledgeAll}
            disabled={isAcknowledgingAll || unacknowledgedCount === 0}
          >
            <CheckCheck className="h-4 w-4 mr-2" />
            {isAcknowledgingAll
              ? "Acknowledging..."
              : `Acknowledge All${unacknowledgedCount > 0 ? ` (${unacknowledgedCount})` : ""}`}
          </Button>
        </div>
      </div>

      {/* Filters Section */}
      <section className="py-8 bg-muted/30">
        <div className="w-full px-6" ref={filtersRef}>
          <SectionHeading
            label="Filter & Search"
            title="Narrow Down Alerts"
            subtitle="Use these filters to find specific alerts by risk level, status, or date range."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={filtersInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <div className="p-6 pb-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                        <Filter className="h-5 w-5 text-primary" />
                      </div>
                      <h3 className="text-lg font-semibold">Filters</h3>
                    </div>
                    {hasFilters && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleResetFilters}
                        className="hover:bg-primary/10 hover:text-primary"
                      >
                        Reset Filters
                      </Button>
                    )}
                  </div>
                </div>
                <div className="px-6 pb-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Risk Level Filter */}
                    <div className="space-y-2">
                      <Label htmlFor="risk-level">Risk Level</Label>
                      <Select
                        value={
                          riskLevel !== undefined ? String(riskLevel) : "all"
                        }
                        onValueChange={(value) => {
                          setPage(1);
                          setRiskLevel(
                            value === "all"
                              ? undefined
                              : (Number(value) as RiskLevel),
                          );
                        }}
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
                            ? "all"
                            : acknowledged
                              ? "acknowledged"
                              : "pending"
                        }
                        onValueChange={(value) => {
                          setPage(1);
                          setAcknowledged(
                            value === "all"
                              ? undefined
                              : value === "acknowledged",
                          );
                        }}
                      >
                        <SelectTrigger id="status">
                          <SelectValue placeholder="All Statuses" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Statuses</SelectItem>
                          <SelectItem value="pending">Pending</SelectItem>
                          <SelectItem value="acknowledged">
                            Acknowledged
                          </SelectItem>
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
                          onChange={(e) => {
                            setPage(1);
                            setStartDate(e.target.value);
                          }}
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
                          onChange={(e) => {
                            setPage(1);
                            setEndDate(e.target.value);
                          }}
                          className="pl-10"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Alert List Section */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={listRef}>
          <SectionHeading
            label="Alert Feed"
            title="Active & Historical Alerts"
            subtitle="View, acknowledge, and track all flood risk alerts across the system."
          />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={listInView ? "show" : undefined}
          >
            {/* Results Summary */}
            {alertsData && (
              <motion.div
                variants={fadeUp}
                className="flex items-center justify-between mb-4 text-sm text-muted-foreground"
              >
                <span>
                  Showing {alertsData.data.length} of {alertsData.total} alerts
                  {hasFilters && " (filtered)"}
                </span>
                <span>
                  Page {page} of {totalPages}
                </span>
              </motion.div>
            )}

            {/* Error State */}
            {isError && (
              <motion.div variants={fadeUp}>
                <GlassCard className="mb-6 border-destructive/40 overflow-hidden">
                  <div className="h-1 w-full bg-linear-to-r from-destructive/60 via-destructive to-destructive/60" />
                  <div className="py-6 px-6">
                    <div className="text-center">
                      <p className="text-destructive font-medium">
                        Failed to load alerts
                      </p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {error?.message || "An unknown error occurred"}
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
              </motion.div>
            )}

            {/* Alerts List */}
            <motion.div variants={fadeUp}>
              <AlertList
                alerts={alertsData?.data ?? []}
                isLoading={isLoading}
                onAcknowledge={handleAcknowledge}
                acknowledgingId={acknowledgingId}
                emptyMessage={
                  hasFilters
                    ? "No alerts match your current filters"
                    : "All clear - no flood alerts have been recorded"
                }
              />
            </motion.div>

            {/* Pagination */}
            {alertsData && totalPages > 1 && (
              <motion.div
                variants={fadeUp}
                className="flex items-center justify-center gap-2 mt-6"
              >
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1 || isFetching}
                  className="border-border/40 hover:bg-risk-safe/10 hover:border-risk-safe/30"
                >
                  Previous
                </Button>

                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
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
                        variant={page === pageNum ? "default" : "outline"}
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
                  className="border-border/40 hover:bg-risk-safe/10 hover:border-risk-safe/30"
                >
                  Next
                </Button>
              </motion.div>
            )}
          </motion.div>
        </div>
      </section>
    </div>
  );
}
