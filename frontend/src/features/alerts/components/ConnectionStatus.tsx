/**
 * ConnectionStatus Component
 *
 * Displays the current SSE connection status with visual indicator.
 */

import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/**
 * ConnectionStatus component props
 */
interface ConnectionStatusProps {
  /** Whether connected to SSE stream */
  isConnected: boolean;
  /** Manual reconnect function */
  onReconnect?: () => void;
  /** Whether reconnection is in progress */
  isReconnecting?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Show reconnect button */
  showReconnectButton?: boolean;
}

/**
 * ConnectionStatus displays the SSE connection state
 *
 * @example
 * <ConnectionStatus
 *   isConnected={isConnected}
 *   onReconnect={reconnect}
 * />
 */
export function ConnectionStatus({
  isConnected,
  onReconnect,
  isReconnecting = false,
  className,
  showReconnectButton = true,
}: ConnectionStatusProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Status Indicator */}
      <div className="flex items-center gap-1.5">
        <div
          className={cn(
            'h-2 w-2 rounded-full',
            isConnected ? 'bg-green-500' : 'bg-red-500',
            isConnected && 'animate-pulse'
          )}
        />
        {isConnected ? (
          <Wifi className="h-4 w-4 text-green-600" />
        ) : (
          <WifiOff className="h-4 w-4 text-red-600" />
        )}
        <span
          className={cn(
            'text-sm font-medium',
            isConnected ? 'text-green-600' : 'text-red-600'
          )}
        >
          {isConnected ? 'Live' : 'Disconnected'}
        </span>
      </div>

      {/* Reconnect Button */}
      {!isConnected && showReconnectButton && onReconnect && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onReconnect}
          disabled={isReconnecting}
          className="h-7 px-2"
        >
          <RefreshCw
            className={cn('h-3.5 w-3.5 mr-1', isReconnecting && 'animate-spin')}
          />
          {isReconnecting ? 'Reconnecting...' : 'Reconnect'}
        </Button>
      )}
    </div>
  );
}

export default ConnectionStatus;
