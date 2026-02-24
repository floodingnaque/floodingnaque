/**
 * RecentAlerts Component
 *
 * Displays the latest flood alerts in a compact card format.
 * Color-coded by risk level with links to the full alerts page.
 */

import { memo } from 'react';
import { Link } from 'react-router-dom';
import { Bell, ChevronRight, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatRelativeTime, truncate, cn } from '@/lib/utils';

/**
 * Alert data structure (placeholder until WS7 provides the actual type)
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
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  className: string;
} {
  if (level <= 25) {
    return {
      label: 'Low',
      variant: 'secondary',
      className: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border-green-200',
    };
  }
  if (level <= 50) {
    return {
      label: 'Moderate',
      variant: 'secondary',
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-200',
    };
  }
  if (level <= 75) {
    return {
      label: 'High',
      variant: 'secondary',
      className: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 border-orange-200',
    };
  }
  return {
    label: 'Critical',
    variant: 'destructive',
    className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border-red-200',
  };
}

/**
 * Individual alert row component
 */
function AlertRow({ alert }: { alert: AlertData }) {
  const riskInfo = getRiskLevelInfo(alert.risk_level);

  return (
    <Link
      to={`/alerts/${alert.id}`}
      className="block group"
    >
      <div className="flex items-start gap-3 py-3 px-2 -mx-2 rounded-md border-b last:border-b-0 hover:bg-muted/50 transition-colors">
        <div
          className={cn(
            'p-1.5 rounded-full flex-shrink-0 mt-0.5',
            riskInfo.className.replace('text-', 'bg-').split(' ')[0] + '/20'
          )}
        >
          <AlertTriangle
            className={cn(
              'h-3.5 w-3.5',
              riskInfo.className.includes('red')
                ? 'text-red-600'
                : riskInfo.className.includes('orange')
                ? 'text-orange-600'
                : riskInfo.className.includes('yellow')
                ? 'text-yellow-600'
                : 'text-green-600'
            )}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className={cn('text-xs', riskInfo.className)}>
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
        <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-1" />
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
      <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30 mb-3">
        <Bell className="h-5 w-5 text-green-600" />
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
            <div key={i} className="flex items-start gap-3 py-3 border-b last:border-b-0">
              <Skeleton className="h-6 w-6 rounded-full flex-shrink-0" />
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
