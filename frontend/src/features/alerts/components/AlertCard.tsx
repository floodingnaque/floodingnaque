/**
 * AlertCard Component
 *
 * Card component for displaying a single alert with its details
 * and acknowledge action.
 */

import { formatDistanceToNow } from 'date-fns';
import { MapPin, Clock, Check, CheckCircle2 } from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { AlertBadge } from './AlertBadge';
import type { Alert } from '@/types';

/**
 * AlertCard component props
 */
interface AlertCardProps {
  /** Alert data to display */
  alert: Alert;
  /** Callback when acknowledge button is clicked */
  onAcknowledge?: (alertId: number) => void;
  /** Whether acknowledge action is in progress */
  isAcknowledging?: boolean;
  /** Compact variant for list view */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Format a date string to relative time
 */
function formatRelativeTime(dateString: string): string {
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true });
  } catch {
    return 'Unknown time';
  }
}

/**
 * AlertCard displays an individual alert with its details
 *
 * @example
 * <AlertCard
 *   alert={alert}
 *   onAcknowledge={(id) => handleAcknowledge(id)}
 * />
 */
export function AlertCard({
  alert,
  onAcknowledge,
  isAcknowledging = false,
  compact = false,
  className,
}: AlertCardProps) {
  const handleAcknowledge = () => {
    if (onAcknowledge && !alert.acknowledged) {
      onAcknowledge(alert.id);
    }
  };

  return (
    <Card
      className={cn(
        'transition-all duration-200',
        alert.acknowledged && 'opacity-60',
        !compact && 'hover:shadow-md',
        className
      )}
    >
      <CardContent className={cn('p-4', compact && 'p-3')}>
        <div className="flex items-start gap-3">
          {/* Risk Badge */}
          <div className="flex-shrink-0 pt-0.5">
            <AlertBadge
              riskLevel={alert.risk_level}
              size={compact ? 'sm' : 'md'}
            />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Message */}
            <p
              className={cn(
                'font-medium text-foreground',
                compact ? 'text-sm' : 'text-base',
                alert.acknowledged && 'text-muted-foreground'
              )}
            >
              {alert.message}
            </p>

            {/* Meta info */}
            <div
              className={cn(
                'flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-muted-foreground',
                compact ? 'text-xs' : 'text-sm'
              )}
            >
              {/* Location */}
              {alert.location && (
                <span className="flex items-center gap-1">
                  <MapPin className={cn('h-3 w-3', compact && 'h-2.5 w-2.5')} />
                  {alert.location}
                </span>
              )}

              {/* Triggered time */}
              <span className="flex items-center gap-1">
                <Clock className={cn('h-3 w-3', compact && 'h-2.5 w-2.5')} />
                {formatRelativeTime(alert.triggered_at)}
              </span>

              {/* Acknowledged status */}
              {alert.acknowledged && (
                <span className="flex items-center gap-1 text-green-600">
                  <CheckCircle2
                    className={cn('h-3 w-3', compact && 'h-2.5 w-2.5')}
                  />
                  Acknowledged
                </span>
              )}
            </div>
          </div>

          {/* Action */}
          <div className="flex-shrink-0">
            {alert.acknowledged ? (
              <div
                className={cn(
                  'flex items-center justify-center rounded-full bg-green-100',
                  compact ? 'h-7 w-7' : 'h-8 w-8'
                )}
              >
                <Check
                  className={cn(
                    'text-green-600',
                    compact ? 'h-3.5 w-3.5' : 'h-4 w-4'
                  )}
                />
              </div>
            ) : (
              <Button
                variant="outline"
                size={compact ? 'sm' : 'default'}
                onClick={handleAcknowledge}
                disabled={isAcknowledging}
                className="whitespace-nowrap"
              >
                {isAcknowledging ? 'Acknowledging...' : 'Acknowledge'}
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default AlertCard;
