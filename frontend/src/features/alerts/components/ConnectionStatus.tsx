/**
 * ConnectionStatus Component
 *
 * Displays the current SSE connection status with visual indicator.
 */

import { formatDistanceToNow } from "date-fns";
import { RefreshCw, Wifi, WifiOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
  /** Last heartbeat timestamp from SSE */
  lastHeartbeat?: Date | null;
}

/**
 * ConnectionStatus displays the SSE connection state
 *
 * @example
 * <ConnectionStatus
 *   isConnected={isConnected}
 *   onReconnect={reconnect}
 *   lastHeartbeat={lastHeartbeat}
 * />
 */
export function ConnectionStatus({
  isConnected,
  onReconnect,
  isReconnecting = false,
  className,
  showReconnectButton = true,
  lastHeartbeat,
}: ConnectionStatusProps) {
  const heartbeatLabel =
    lastHeartbeat && isConnected
      ? formatDistanceToNow(lastHeartbeat, { addSuffix: true })
      : null;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Status Indicator */}
      <div className="flex items-center gap-1.5">
        <div
          className={cn(
            "h-2 w-2 rounded-full",
            isConnected ? "bg-risk-safe" : "bg-risk-critical",
            isConnected && "animate-pulse",
          )}
        />
        {isConnected ? (
          <Wifi className="h-4 w-4 text-risk-safe" />
        ) : (
          <WifiOff className="h-4 w-4 text-risk-critical" />
        )}
        <span
          className={cn(
            "text-sm font-medium",
            isConnected ? "text-risk-safe" : "text-risk-critical",
          )}
        >
          {isConnected ? "Live" : "Disconnected"}
        </span>
        {heartbeatLabel && (
          <span className="text-[10px] text-muted-foreground hidden lg:inline">
            · {heartbeatLabel}
          </span>
        )}
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
            className={cn("h-3.5 w-3.5 mr-1", isReconnecting && "animate-spin")}
          />
          {isReconnecting ? "Reconnecting..." : "Reconnect"}
        </Button>
      )}
    </div>
  );
}

export default ConnectionStatus;
