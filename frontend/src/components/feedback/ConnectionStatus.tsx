/**
 * ConnectionStatus Component (Feedback variant)
 *
 * Store-connected wrapper around the alerts ConnectionStatus.
 * Reads SSE state from useAlertStore so consumers don't need to pass props.
 */

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAlertStore } from "@/state/stores/alertStore";
import { AlertTriangle, Wifi, WifiOff } from "lucide-react";

interface ConnectionStatusProps {
  /** Additional CSS classes */
  className?: string;
  /** Whether to show the text label */
  showLabel?: boolean;
  /** Size variant */
  size?: "sm" | "md" | "lg";
}

const sizeConfig = {
  sm: {
    icon: "h-3 w-3",
    badge: "text-xs px-1.5 py-0.5",
    gap: "gap-1",
  },
  md: {
    icon: "h-4 w-4",
    badge: "text-xs px-2 py-0.5",
    gap: "gap-1.5",
  },
  lg: {
    icon: "h-5 w-5",
    badge: "text-sm px-2.5 py-1",
    gap: "gap-2",
  },
};

/**
 * Label and styling per connection state.
 */
const STATE_CONFIG: Record<
  string,
  {
    label: string;
    borderClass: string;
    Icon: typeof Wifi;
  }
> = {
  CONNECTED: {
    label: "Connected",
    borderClass: "border-risk-safe bg-risk-safe/10 text-risk-safe",
    Icon: Wifi,
  },
  CONNECTING: {
    label: "Connecting…",
    borderClass: "border-muted bg-muted/10 text-muted-foreground",
    Icon: Wifi,
  },
  RECONNECTING: {
    label: "Reconnecting…",
    borderClass: "border-risk-alert bg-risk-alert/10 text-risk-alert",
    Icon: AlertTriangle,
  },
  FAILED: {
    label: "Polling (SSE failed)",
    borderClass: "border-risk-critical bg-risk-critical/10 text-risk-critical",
    Icon: WifiOff,
  },
  IDLE: {
    label: "Disconnected",
    borderClass: "border-risk-critical bg-risk-critical/10 text-risk-critical",
    Icon: WifiOff,
  },
};

/**
 * Displays SSE connection status with visual feedback.
 * Reads state directly from the alert store - no props needed.
 */
export function ConnectionStatus({
  className,
  showLabel = true,
  size = "md",
}: ConnectionStatusProps) {
  const connectionState = useAlertStore((s) => s.connectionState);
  const connectionError = useAlertStore((s) => s.connectionError);
  const cfg = sizeConfig[size];

  const wrapperCls = cn(
    "inline-flex items-center transition-all duration-300",
    cfg.gap,
    className,
  );

  // Error state takes precedence
  if (connectionError) {
    return (
      <div className={wrapperCls} role="status" aria-live="polite">
        <Badge
          variant="outline"
          className={cn(
            "border-risk-alert bg-risk-alert/10 text-risk-alert transition-colors",
            cfg.badge,
          )}
        >
          <AlertTriangle className={cn(cfg.icon, "mr-1")} aria-hidden="true" />
          {showLabel && (
            <span className="truncate max-w-37.5">{connectionError}</span>
          )}
        </Badge>
      </div>
    );
  }

  const stateInfo = (STATE_CONFIG[connectionState] ?? STATE_CONFIG.IDLE)!;
  const { label, borderClass, Icon } = stateInfo;

  return (
    <div className={wrapperCls} role="status" aria-live="polite">
      <Badge
        variant="outline"
        className={cn(borderClass, "transition-colors", cfg.badge)}
      >
        <Icon className={cn(cfg.icon, "mr-1")} aria-hidden="true" />
        {showLabel && <span>{label}</span>}
      </Badge>
    </div>
  );
}

export default ConnectionStatus;
