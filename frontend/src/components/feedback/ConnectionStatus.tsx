/**
 * ConnectionStatus Component
 * 
 * Displays the current SSE connection status with visual indicators.
 * Shows connected/disconnected state with appropriate icons and colors.
 */

import { Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useAlertStore } from '@/state/stores/alertStore';

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
 * 
 * - Green Wifi icon with "Connected" badge when connected
 * - Red WifiOff icon with "Disconnected" badge when not connected
 * - Amber AlertTriangle with error message if there's a connection error
 * - CSS transition animation for smooth state changes
 */
export function ConnectionStatus({
  className,
  showLabel = true,
  size = 'md',
}: ConnectionStatusProps) {
  const { isConnected, connectionError } = useAlertStore();
  const config = sizeConfig[size];

  // Show error state if there's a connection error
  if (connectionError) {
    return (
      <div
        className={cn(
          'inline-flex items-center transition-all duration-300',
          config.gap,
          className
        )}
        role="status"
        aria-live="polite"
      >
        <Badge
          variant="outline"
          className={cn(
            'border-amber-500 bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400 transition-colors',
            config.badge
          )}
        >
          <AlertTriangle className={cn(config.icon, 'mr-1')} aria-hidden="true" />
          {showLabel && (
            <span className="truncate max-w-[150px]">
              {connectionError}
            </span>
          )}
        </Badge>
      </div>
    );
  }

  // Show connected state
  if (isConnected) {
    return (
      <div
        className={cn(
          'inline-flex items-center transition-all duration-300',
          config.gap,
          className
        )}
        role="status"
        aria-live="polite"
      >
        <Badge
          variant="outline"
          className={cn(
            'border-green-500 bg-green-50 text-green-700 dark:bg-green-950/30 dark:text-green-400 transition-colors',
            config.badge
          )}
        >
          <Wifi className={cn(config.icon, 'mr-1')} aria-hidden="true" />
          {showLabel && <span>Connected</span>}
        </Badge>
      </div>
    );
  }

  // Show disconnected state
  return (
    <div
      className={cn(
        'inline-flex items-center transition-all duration-300',
        config.gap,
        className
      )}
      role="status"
      aria-live="polite"
    >
      <Badge
        variant="outline"
        className={cn(
          'border-red-500 bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400 transition-colors',
          config.badge
        )}
      >
        <WifiOff className={cn(config.icon, 'mr-1')} aria-hidden="true" />
        {showLabel && <span>Disconnected</span>}
      </Badge>
    </div>
  );
}

export default ConnectionStatus;
