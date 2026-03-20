/**
 * AlertList Component
 *
 * Renders a virtualized list of alert cards with loading and empty states,
 * and optional filtering controls. Uses @tanstack/react-virtual to avoid
 * DOM thrashing during monsoon-season alert surges.
 */

import { useVirtualizer } from "@tanstack/react-virtual";
import { AlertCircle, Filter } from "lucide-react";
import { useRef, useState } from "react";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import type { Alert, RiskLevel } from "@/types";
import { AlertCard } from "./AlertCard";

/**
 * AlertList component props
 */
interface AlertListProps {
  /** Array of alerts to display */
  alerts: Alert[];
  /** Whether alerts are loading */
  isLoading?: boolean;
  /** Callback when an alert is acknowledged */
  onAcknowledge?: (alertId: number) => void;
  /** ID of the alert currently being acknowledged */
  acknowledgingId?: number | null;
  /** Show filter controls */
  showFilters?: boolean;
  /** Use compact card variant */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Empty state message */
  emptyMessage?: string;
}

/**
 * Loading skeleton for alerts
 */
function AlertListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="border rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Skeleton className="h-5 w-16 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <div className="flex gap-4">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-20" />
              </div>
            </div>
            <Skeleton className="h-9 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Empty state component
 */
function EmptyState({
  message,
  isFiltered,
}: {
  message: string;
  isFiltered: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <AlertCircle className="h-12 w-12 text-muted-foreground/50 mb-4" />
      <p className="text-lg font-medium text-muted-foreground">{message}</p>
      <p className="text-sm text-muted-foreground/75 mt-1">
        {isFiltered
          ? "Try adjusting your filters to see more results"
          : "New alerts will appear here when triggered"}
      </p>
    </div>
  );
}

/**
 * AlertList renders a filterable list of alert cards
 *
 * @example
 * <AlertList
 *   alerts={alerts}
 *   isLoading={isLoading}
 *   onAcknowledge={handleAcknowledge}
 *   showFilters
 * />
 */
/** Threshold above which we enable virtual scrolling */
const VIRTUALIZE_THRESHOLD = 30;
/** Estimated height (px) of a single AlertCard row */
const ESTIMATED_ROW_HEIGHT = 80;
/** Height of a compact AlertCard row */
const ESTIMATED_ROW_HEIGHT_COMPACT = 60;

export function AlertList({
  alerts,
  isLoading = false,
  onAcknowledge,
  acknowledgingId,
  showFilters = false,
  compact = false,
  className,
  emptyMessage = "No alerts",
}: AlertListProps) {
  // Local filter state
  const [riskLevelFilter, setRiskLevelFilter] = useState<RiskLevel | "all">(
    "all",
  );
  const [showAcknowledged, setShowAcknowledged] = useState(true);

  // Scroll container ref for virtualization
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Filter alerts
  const filteredAlerts = alerts.filter((alert) => {
    // Risk level filter
    if (riskLevelFilter !== "all" && alert.risk_level !== riskLevelFilter) {
      return false;
    }
    // Acknowledged filter
    if (!showAcknowledged && alert.acknowledged) {
      return false;
    }
    return true;
  });

  const shouldVirtualize = filteredAlerts.length > VIRTUALIZE_THRESHOLD;

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual is compatible
  const virtualizer = useVirtualizer({
    count: filteredAlerts.length,
    getScrollElement: () => scrollContainerRef.current,
    estimateSize: () =>
      compact ? ESTIMATED_ROW_HEIGHT_COMPACT : ESTIMATED_ROW_HEIGHT,
    overscan: 5,
    enabled: shouldVirtualize,
  });

  // Loading state
  if (isLoading) {
    return (
      <div className={className}>
        {showFilters && (
          <div className="mb-4">
            <Skeleton className="h-10 w-full max-w-md" />
          </div>
        )}
        <AlertListSkeleton count={compact ? 5 : 3} />
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Filter Controls */}
      {showFilters && (
        <div className="flex flex-wrap items-center gap-4 mb-4 pb-4 border-b">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Filters:</span>
          </div>

          {/* Risk Level Filter */}
          <Select
            value={riskLevelFilter === "all" ? "all" : String(riskLevelFilter)}
            onValueChange={(value) =>
              setRiskLevelFilter(
                value === "all" ? "all" : (Number(value) as RiskLevel),
              )
            }
          >
            <SelectTrigger className="w-32 h-9">
              <SelectValue placeholder="Risk Level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Levels</SelectItem>
              <SelectItem value="0">Safe</SelectItem>
              <SelectItem value="1">Alert</SelectItem>
              <SelectItem value="2">Critical</SelectItem>
            </SelectContent>
          </Select>

          {/* Acknowledged Toggle */}
          <div className="flex items-center gap-2">
            <Switch
              id="show-acknowledged"
              checked={showAcknowledged}
              onCheckedChange={setShowAcknowledged}
            />
            <Label htmlFor="show-acknowledged" className="text-sm">
              Show acknowledged
            </Label>
          </div>

          {/* Results count */}
          <span className="text-sm text-muted-foreground ml-auto">
            {filteredAlerts.length} of {alerts.length} alerts
          </span>
        </div>
      )}

      {/* Alert List */}
      {filteredAlerts.length === 0 ? (
        <EmptyState
          message={
            alerts.length > 0 ? "No alerts match your filters" : emptyMessage
          }
          isFiltered={
            alerts.length > 0 || riskLevelFilter !== "all" || !showAcknowledged
          }
        />
      ) : shouldVirtualize ? (
        /* Virtualized rendering for large alert lists (>30 items) */
        <div
          ref={scrollContainerRef}
          className="max-h-[70vh] overflow-auto"
          role="list"
          aria-label="Alert list"
        >
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              width: "100%",
              position: "relative",
            }}
          >
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const alert = filteredAlerts[virtualRow.index];
              if (!alert) return null;
              return (
                <div
                  key={alert.id}
                  role="listitem"
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                  ref={virtualizer.measureElement}
                  data-index={virtualRow.index}
                >
                  <div className={compact ? "pb-2" : "pb-3"}>
                    <AlertCard
                      alert={alert}
                      onAcknowledge={onAcknowledge}
                      isAcknowledging={acknowledgingId === alert.id}
                      compact={compact}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* Standard rendering for small alert lists */
        <div className={cn("space-y-3", compact && "space-y-2")}>
          {filteredAlerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onAcknowledge={onAcknowledge}
              isAcknowledging={acknowledgingId === alert.id}
              compact={compact}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default AlertList;
