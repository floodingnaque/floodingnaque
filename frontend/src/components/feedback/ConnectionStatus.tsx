/**
 * ConnectionStatus Component (Feedback variant)
 *
 * Store-connected wrapper around the alerts ConnectionStatus.
 * Reads SSE state from useAlertStore so consumers don't need to pass props.
 */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useAlertStore } from '@/state/stores/alertStore';
import { Wifi, WifiOff, AlertTriangle } from 'lucide-react';

interface ConnectionStatusProps {
  /** Additional CSS classes */
  className?: string;
  /** Whether to show the text label */
  showLabel?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

const sizeConfig = {
  sm: {
    icon: 'h-3 w-3',
    badge: 'text-xs px-1.5 py-0.5',
    gap: 'gap-1',
  },
  md: {
    icon: 'h-4 w-4',
    badge: 'text-xs px-2 py-0.5',
    gap: 'gap-1.5',
  },
  lg: {
    icon: 'h-5 w-5',
    badge: 'text-sm px-2.5 py-1',
    gap: 'gap-2',
  },
};

/**
 * Displays SSE connection status with visual feedback.
 * Reads state directly from the alert store — no props needed.
 */
export function ConnectionStatus({
  className,
  showLabel = true,
  size = 'md',
}: ConnectionStatusProps) {
  const { isConnected, connectionError } = useAlertStore();
  const config = sizeConfig[size];

  const wrapperCls = cn(
    'inline-flex items-center transition-all duration-300',
    config.gap,
    className,
  );

  if (connectionError) {
    return (
      <div className={wrapperCls} role="status" aria-live="polite">
        <Badge
          variant="outline"
          className={cn(
            'border-amber-500 bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400 transition-colors',
            config.badge,
          )}
        >
          <AlertTriangle className={cn(config.icon, 'mr-1')} aria-hidden="true" />
          {showLabel && (
            <span className="truncate max-w-37.5">{connectionError}</span>
          )}
        </Badge>
      </div>
    );
  }

  if (isConnected) {
    return (
      <div className={wrapperCls} role="status" aria-live="polite">
        <Badge
          variant="outline"
          className={cn(
            'border-green-500 bg-green-50 text-green-700 dark:bg-green-950/30 dark:text-green-400 transition-colors',
            config.badge,
          )}
        >
          <Wifi className={cn(config.icon, 'mr-1')} aria-hidden="true" />
          {showLabel && <span>Connected</span>}
        </Badge>
      </div>
    );
  }

  return (
    <div className={wrapperCls} role="status" aria-live="polite">
      <Badge
        variant="outline"
        className={cn(
          'border-red-500 bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400 transition-colors',
          config.badge,
        )}
      >
        <WifiOff className={cn(config.icon, 'mr-1')} aria-hidden="true" />
        {showLabel && <span>Disconnected</span>}
      </Badge>
    </div>
  );
}

export default ConnectionStatus;
