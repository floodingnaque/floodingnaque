/**
 * LiveAlertsBanner Component
 *
 * Fixed position banner that shows when there are unread live alerts.
 * Displays count, latest alert preview, and provides quick actions.
 */

import { useState } from 'react';
import { X, Bell, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useLiveAlerts, useUnreadCount, useAlertActions } from '@/state/stores/alertStore';
import { AlertBadge } from './AlertBadge';
import { RISK_CONFIGS, type RiskLevel } from '@/types';

/**
 * LiveAlertsBanner component props
 */
interface LiveAlertsBannerProps {
  /** Callback when clicking to view all alerts */
  onViewAll?: () => void;
  /** Additional CSS classes */
  className?: string;
  /** Maximum alerts to show in expanded view */
  maxPreviewAlerts?: number;
}

/**
 * Get highest risk level from a list of alerts
 */
function getHighestRiskLevel(alerts: { risk_level: RiskLevel }[]): RiskLevel {
  return alerts.reduce(
    (max, alert) => (alert.risk_level > max ? alert.risk_level : max),
    0 as RiskLevel
  );
}

/**
 * Banner background color based on highest risk
 */
const BANNER_STYLES: Record<RiskLevel, string> = {
  0: 'bg-green-50 border-green-200',
  1: 'bg-amber-50 border-amber-200',
  2: 'bg-red-50 border-red-200',
};

/**
 * LiveAlertsBanner displays real-time alerts at the top of the page
 *
 * @example
 * <LiveAlertsBanner onViewAll={() => navigate('/alerts')} />
 */
export function LiveAlertsBanner({
  onViewAll,
  className,
  maxPreviewAlerts = 3,
}: LiveAlertsBannerProps) {
  const liveAlerts = useLiveAlerts();
  const unreadCount = useUnreadCount();
  const { markAllRead } = useAlertActions();

  const [isExpanded, setIsExpanded] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  // Don't render if no unread alerts or dismissed
  if (unreadCount === 0 || isDismissed) {
    return null;
  }

  const highestRisk = getHighestRiskLevel(liveAlerts);
  const riskConfig = RISK_CONFIGS[highestRisk];
  const latestAlert = liveAlerts[0];
  const previewAlerts = liveAlerts.slice(0, maxPreviewAlerts);

  const handleDismiss = () => {
    markAllRead();
    setIsDismissed(true);
    // Reset dismissed state after some time so future alerts can show
    setTimeout(() => setIsDismissed(false), 60000);
  };

  const handleViewAll = () => {
    markAllRead();
    onViewAll?.();
  };

  return (
    <div
      className={cn(
        'fixed top-0 left-0 right-0 z-50 border-b shadow-md',
        'animate-in slide-in-from-top duration-300',
        BANNER_STYLES[highestRisk],
        className
      )}
      role="alert"
      aria-live="polite"
    >
      <div className="container max-w-6xl mx-auto px-4 py-3">
        {/* Main Banner Content */}
        <div className="flex items-center gap-3">
          {/* Icon */}
          <div
            className={cn(
              'flex-shrink-0 flex items-center justify-center rounded-full h-10 w-10',
              highestRisk === 2
                ? 'bg-red-100'
                : highestRisk === 1
                  ? 'bg-amber-100'
                  : 'bg-green-100'
            )}
          >
            {highestRisk === 2 ? (
              <AlertTriangle className={cn('h-5 w-5', riskConfig.color)} />
            ) : (
              <Bell className={cn('h-5 w-5', riskConfig.color)} />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-foreground">
                {unreadCount} New Alert{unreadCount > 1 ? 's' : ''}
              </span>
              <AlertBadge riskLevel={highestRisk} size="sm" />
            </div>
            {latestAlert && !isExpanded && (
              <p className="text-sm text-muted-foreground truncate">
                {latestAlert.message}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex-shrink-0 flex items-center gap-2">
            {/* Expand/Collapse */}
            {liveAlerts.length > 1 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="h-8 px-2"
              >
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            )}

            {/* View All */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleViewAll}
              className="h-8"
            >
              View All
            </Button>

            {/* Dismiss */}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDismiss}
              className="h-8 w-8 p-0"
              aria-label="Dismiss alerts"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Expanded Alert Preview */}
        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-current/10 space-y-2 animate-in fade-in duration-200">
            {previewAlerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center gap-3 p-2 rounded-md bg-background/50"
              >
                <AlertBadge riskLevel={alert.risk_level} size="sm" />
                <p className="text-sm flex-1 truncate">{alert.message}</p>
                {alert.location && (
                  <span className="text-xs text-muted-foreground">
                    {alert.location}
                  </span>
                )}
              </div>
            ))}
            {liveAlerts.length > maxPreviewAlerts && (
              <p className="text-xs text-muted-foreground text-center pt-1">
                +{liveAlerts.length - maxPreviewAlerts} more alerts
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default LiveAlertsBanner;
