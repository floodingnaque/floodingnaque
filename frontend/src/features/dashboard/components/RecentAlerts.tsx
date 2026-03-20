/**
 * RecentAlerts Component
 *
 * Displays the latest flood alerts in a compact card format.
 * Color-coded by risk level with links to the full alerts page.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatRelativeTime, truncate } from "@/lib/utils";
import { AlertTriangle, Bell, ChevronRight } from "lucide-react";
import { memo } from "react";
import { Link } from "react-router-dom";

/**
 * Alert data structure for flood risk notifications.
 *
 * Matches the backend AlertHistory schema (see backend/app/models/).
 * Fields: id, message, risk_level (0=safe, 1=alert, 2=critical),
 * created_at (ISO 8601), and optional location string.
 */
export interface AlertData {
  id: string | number;
  message: string;
  risk_level: number;
  created_at: string;
  location?: string;
}

interface RecentAlertsProps {
  /** Array of alert data */
  alerts: AlertData[];
  /** Maximum number of alerts to display (default: 5) */
  maxAlerts?: number;
  /** Whether data is loading */
  isLoading?: boolean;
}

/**
 * Get risk level label and styling based on numeric value
 */
function getRiskLevelInfo(level: number): {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
  className: string;
} {
  if (level <= 25) {
    return {
      label: "Low",
      variant: "secondary",
      className: "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
    };
  }
  if (level <= 50) {
    return {
      label: "Moderate",
      variant: "secondary",
      className: "bg-risk-alert/15 text-risk-alert border-risk-alert/30",
    };
  }
  if (level <= 75) {
    return {
      label: "High",
      variant: "secondary",
      className: "bg-risk-alert/25 text-risk-alert border-risk-alert/40",
    };
  }
  return {
    label: "Critical",
    variant: "destructive",
    className: "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
  };
}

/**
 * Individual alert row component
 */
function AlertRow({ alert }: { alert: AlertData }) {
  const riskInfo = getRiskLevelInfo(alert.risk_level);

  return (
    <Link to="/alerts" className="block group">
      <div className="flex items-start gap-3 py-3 px-2 -mx-2 rounded-md border-b last:border-b-0 hover:bg-muted/50 transition-colors">
        <div
          className={cn(
            "p-1.5 rounded-full shrink-0 mt-0.5",
            riskInfo.className.replace("text-", "bg-").split(" ")[0] + "/20",
          )}
        >
          <AlertTriangle
            className={cn(
              "h-3.5 w-3.5",
              riskInfo.className.includes("critical")
                ? "text-risk-critical"
                : riskInfo.className.includes("alert")
                  ? "text-risk-alert"
                  : "text-risk-safe",
            )}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge
              variant="outline"
              className={cn("text-xs", riskInfo.className)}
            >
              {riskInfo.label}
            </Badge>
            {alert.location && (
              <span className="text-xs text-muted-foreground truncate">
                {alert.location}
              </span>
            )}
          </div>
          <p className="text-sm leading-tight group-hover:text-primary transition-colors">
            {truncate(alert.message, 80)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {formatRelativeTime(alert.created_at)}
          </p>
        </div>
        <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-1" />
      </div>
    </Link>
  );
}

/**
 * Empty state when no alerts exist
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-6 text-center">
      <div className="p-3 rounded-full bg-risk-safe/15 dark:bg-risk-safe/20 mb-3">
        <Bell className="h-5 w-5 text-risk-safe" />
      </div>
      <p className="text-sm font-medium">No active alerts</p>
      <p className="text-xs text-muted-foreground mt-1">
        All systems are operating normally
      </p>
    </div>
  );
}

/**
 * RecentAlerts displays the latest flood alerts in a compact format
 */
export const RecentAlerts = memo(function RecentAlerts({
  alerts,
  maxAlerts = 5,
  isLoading = false,
}: RecentAlertsProps) {
  if (isLoading) {
    return <RecentAlertsSkeleton />;
  }

  const displayAlerts = alerts.slice(0, maxAlerts);
  const hasMore = alerts.length > maxAlerts;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Recent Alerts
        </CardTitle>
        {alerts.length > 0 && (
          <Link to="/alerts">
            <Button variant="ghost" size="sm" className="gap-1">
              View all
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
        )}
      </CardHeader>
      <CardContent className="pt-0">
        {displayAlerts.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <div className="space-y-0">
              {displayAlerts.map((alert) => (
                <AlertRow key={alert.id} alert={alert} />
              ))}
            </div>
            {hasMore && (
              <div className="pt-3 text-center border-t mt-2">
                <Link to="/alerts">
                  <Button variant="link" size="sm">
                    View {alerts.length - maxAlerts} more alerts
                  </Button>
                </Link>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
});

/**
 * Skeleton loading state for RecentAlerts
 */
export function RecentAlertsSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-8 w-20" />
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-0">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="flex items-start gap-3 py-3 border-b last:border-b-0"
            >
              <Skeleton className="h-6 w-6 rounded-full shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-5 w-16" />
                  <Skeleton className="h-4 w-20" />
                </div>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default RecentAlerts;
