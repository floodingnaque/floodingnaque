/**
 * RecentActivity Component
 *
 * Displays a list of recent predictions and alerts with
 * icons, descriptions, and relative timestamps.
 */

import { Link } from 'react-router-dom';
import { Activity, AlertTriangle, Clock, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatRelativeTime, cn } from '@/lib/utils';
import type { ActivityItem } from '../services/dashboardApi';

interface RecentActivityProps {
  /** Array of recent activity items */
  activities: ActivityItem[];
  /** Maximum number of items to display (default: 10) */
  maxItems?: number;
}

/**
 * Get icon and color for activity type
 */
function getActivityIcon(type: ActivityItem['type']) {
  if (type === 'alert') {
    return {
      icon: <AlertTriangle className="h-4 w-4" />,
      bgColor: 'bg-amber-100 dark:bg-amber-900/30',
      iconColor: 'text-amber-600',
    };
  }
  return {
    icon: <Activity className="h-4 w-4" />,
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    iconColor: 'text-blue-600',
  };
}

/**
 * Individual activity item row
 */
function ActivityRow({ activity }: { activity: ActivityItem }) {
  const { icon, bgColor, iconColor } = getActivityIcon(activity.type);

  return (
    <div className="flex items-start gap-3 py-3 border-b last:border-b-0">
      <div className={cn('p-2 rounded-full flex-shrink-0', bgColor)}>
        <div className={iconColor}>{icon}</div>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-tight">
          {activity.description}
        </p>
        <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>{formatRelativeTime(activity.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Empty state when no activities exist
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="p-3 rounded-full bg-muted mb-3">
        <Activity className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-sm font-medium">No recent activity</p>
      <p className="text-xs text-muted-foreground mt-1">
        Your predictions and alerts will appear here
      </p>
    </div>
  );
}

/**
 * RecentActivity displays a scrollable list of recent system activities
 */
export function RecentActivity({
  activities,
  maxItems = 10,
}: RecentActivityProps) {
  const safeActivities = Array.isArray(activities) ? activities : [];
  const displayActivities = safeActivities.slice(0, maxItems);
  const hasMore = safeActivities.length > maxItems;

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold">Recent Activity</CardTitle>
        {safeActivities.length > 0 && (
          <Link to="/history">
            <Button variant="ghost" size="sm" className="gap-1">
              View all
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
        )}
      </CardHeader>
      <CardContent>
        {displayActivities.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-0">
            {displayActivities.map((activity, index) => (
              <ActivityRow
                key={`${activity.timestamp}-${index}`}
                activity={activity}
              />
            ))}
            {hasMore && (
              <div className="pt-3 text-center">
                <Link to="/history">
                  <Button variant="link" size="sm">
                    View {safeActivities.length - maxItems} more activities
                  </Button>
                </Link>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton loading state for RecentActivity
 */
export function RecentActivitySkeleton() {
  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-8 w-20" />
      </CardHeader>
      <CardContent>
        <div className="space-y-0">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-start gap-3 py-3 border-b last:border-b-0">
              <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
              <div className="flex-1 space-y-2">
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

export default RecentActivity;
