/**
 * AlertCard Component
 *
 * Card component for displaying a single alert with its details
 * and acknowledge action. Includes smart alert metadata:
 * confidence score, 3h rainfall accumulation, escalation state,
 * and contributing factors.
 */

import { formatDistanceToNow } from "date-fns";
import {
  Check,
  CheckCircle2,
  Clock,
  CloudRain,
  MapPin,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { cn } from "@/lib/utils";
import type { Alert } from "@/types";
import { AlertBadge } from "./AlertBadge";

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
    return "Unknown time";
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
    <GlassCard
      intensity="light"
      className={cn(
        "overflow-hidden transition-all duration-300",
        alert.acknowledged && "opacity-60",
        !compact && "hover:shadow-lg",
        className,
      )}
    >
      <div
        className={cn(
          "h-1 w-full",
          alert.risk_level >= 2
            ? "bg-linear-to-r from-red-500/60 via-red-400 to-rose-500/60"
            : alert.risk_level >= 1
              ? "bg-linear-to-r from-amber-500/60 via-amber-400 to-yellow-500/60"
              : "bg-linear-to-r from-emerald-500/60 via-emerald-400 to-teal-500/60",
        )}
      />
      <div className={cn("p-4", compact && "p-3")}>
        <div className="flex items-start gap-3">
          {/* Risk Badge */}
          <div className="shrink-0 pt-0.5">
            <AlertBadge
              riskLevel={alert.risk_level}
              size={compact ? "sm" : "md"}
            />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Message */}
            <p
              className={cn(
                "font-medium text-foreground",
                compact ? "text-sm" : "text-base",
                alert.acknowledged && "text-muted-foreground",
              )}
            >
              {alert.message}
            </p>

            {/* Meta info */}
            <div
              className={cn(
                "flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-muted-foreground",
                compact ? "text-xs" : "text-sm",
              )}
            >
              {/* Location */}
              {alert.location && (
                <span className="flex items-center gap-1">
                  <MapPin className={cn("h-3 w-3", compact && "h-2.5 w-2.5")} />
                  {alert.location}
                </span>
              )}

              {/* Triggered time */}
              <span className="flex items-center gap-1">
                <Clock className={cn("h-3 w-3", compact && "h-2.5 w-2.5")} />
                {formatRelativeTime(alert.triggered_at)}
              </span>

              {/* Acknowledged status */}
              {alert.acknowledged && (
                <span className="flex items-center gap-1 text-risk-safe">
                  <CheckCircle2
                    className={cn("h-3 w-3", compact && "h-2.5 w-2.5")}
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
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                        alert.confidence_score >= 0.7
                          ? "bg-risk-safe/10 text-risk-safe"
                          : alert.confidence_score >= 0.45
                            ? "bg-risk-alert/10 text-risk-alert"
                            : "bg-risk-critical/10 text-risk-critical",
                      )}
                    >
                      <ShieldAlert className="w-3 h-3" />
                      {(alert.confidence_score * 100).toFixed(0)}% confidence
                    </span>
                  )}

                  {/* 3h rainfall accumulation */}
                  {alert.rainfall_3h != null && alert.rainfall_3h > 0 && (
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                        alert.rainfall_3h >= 80
                          ? "bg-risk-critical/10 text-risk-critical"
                          : alert.rainfall_3h >= 50
                            ? "bg-risk-alert/10 text-risk-alert"
                            : "bg-primary/10 text-primary",
                      )}
                    >
                      <CloudRain className="w-3 h-3" />
                      {alert.rainfall_3h.toFixed(1)} mm / 3h
                    </span>
                  )}

                  {/* Escalation state */}
                  {alert.escalation_state === "auto_escalated" && (
                    <span
                      className="inline-flex items-center gap-1 rounded-full bg-risk-critical/15 px-2 py-0.5 text-xs font-medium text-risk-critical"
                      title={
                        alert.escalation_reason
                          ? `Reason: ${alert.escalation_reason}`
                          : "Auto-escalated due to sustained risk"
                      }
                    >
                      <TrendingUp className="w-3 h-3" />
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
          <div className="shrink-0">
            {alert.acknowledged ? (
              <div
                className={cn(
                  "flex items-center justify-center rounded-full bg-risk-safe/15",
                  compact ? "h-7 w-7" : "h-8 w-8",
                )}
              >
                <Check
                  className={cn(
                    "text-risk-safe",
                    compact ? "h-3.5 w-3.5" : "h-4 w-4",
                  )}
                />
              </div>
            ) : (
              <Button
                variant="outline"
                size={compact ? "sm" : "default"}
                onClick={handleAcknowledge}
                disabled={isAcknowledging}
                className="whitespace-nowrap"
              >
                {isAcknowledging ? "Acknowledging..." : "Acknowledge"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

export default AlertCard;
