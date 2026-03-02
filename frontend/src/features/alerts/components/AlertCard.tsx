/**
 * AlertCard Component
 *
 * Card component for displaying a single alert with its details
 * and acknowledge action. Includes smart alert metadata:
 * confidence score, 3h rainfall accumulation, escalation state,
 * and contributing factors.
 */

import { formatDistanceToNow } from 'date-fns';
import {
  MapPin,
  Clock,
  Check,
  CheckCircle2,
  CloudRain,
  ShieldAlert,
  TrendingUp,
} from 'lucide-react';

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

            {/* Smart Alert Metadata */}
            {!compact && (
              <div className="mt-2 flex flex-col gap-1.5">
                {/* Confidence + Rainfall row */}
                <div className="flex flex-wrap items-center gap-2">
                  {/* Confidence score */}
                  {alert.confidence_score != null && (
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                        alert.confidence_score >= 0.7
                          ? 'bg-green-50 text-green-700'
                          : alert.confidence_score >= 0.45
                            ? 'bg-amber-50 text-amber-700'
                            : 'bg-red-50 text-red-700'
                      )}
                    >
                      <ShieldAlert className="h-3 w-3" />
                      {(alert.confidence_score * 100).toFixed(0)}% confidence
                    </span>
                  )}

                  {/* 3h rainfall accumulation */}
                  {alert.rainfall_3h != null && alert.rainfall_3h > 0 && (
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                        alert.rainfall_3h >= 80
                          ? 'bg-red-50 text-red-700'
                          : alert.rainfall_3h >= 50
                            ? 'bg-amber-50 text-amber-700'
                            : 'bg-blue-50 text-blue-700'
                      )}
                    >
                      <CloudRain className="h-3 w-3" />
                      {alert.rainfall_3h.toFixed(1)} mm / 3h
                    </span>
                  )}

                  {/* Escalation state */}
                  {alert.escalation_state === 'auto_escalated' && (
                    <span
                      className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800"
                      title={
                        alert.escalation_reason
                          ? `Reason: ${alert.escalation_reason}`
                          : 'Auto-escalated due to sustained risk'
                      }
                    >
                      <TrendingUp className="h-3 w-3" />
                      Escalated
                    </span>
                  )}
                </div>

                {/* Contributing factors */}
                {alert.contributing_factors &&
                  alert.contributing_factors.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {alert.contributing_factors.map((factor, idx) => (
                        <span
                          key={idx}
                          className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600"
                        >
                          {factor}
                        </span>
                      ))}
                    </div>
                  )}
              </div>
            )}
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
