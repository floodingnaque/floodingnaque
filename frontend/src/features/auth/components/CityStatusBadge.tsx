/**
 * CityStatusBadge - Live flood risk status indicator
 *
 * Shows current city-wide flood risk level so even unauthenticated
 * users are immediately informed. Displayed on all auth pages.
 */

import { cn } from "@/lib/utils";
import { Shield } from "lucide-react";

type RiskLevel = "Safe" | "Alert" | "Critical";

const riskConfig: Record<
  RiskLevel,
  { bg: string; text: string; dot: string; label: string }
> = {
  Safe: {
    bg: "bg-risk-safe/15 border-risk-safe/30",
    text: "text-risk-safe",
    dot: "bg-risk-safe",
    label: "Safe",
  },
  Alert: {
    bg: "bg-risk-alert/15 border-risk-alert/30",
    text: "text-risk-alert",
    dot: "bg-risk-alert",
    label: "Alert",
  },
  Critical: {
    bg: "bg-risk-critical/15 border-risk-critical/30",
    text: "text-risk-critical",
    dot: "bg-risk-critical",
    label: "Critical",
  },
};

interface CityStatusBadgeProps {
  risk?: RiskLevel;
  className?: string;
}

export function CityStatusBadge({
  risk = "Safe",
  className,
}: CityStatusBadgeProps) {
  const config = riskConfig[risk];

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium backdrop-blur-sm",
        config.bg,
        config.text,
        className,
      )}
      role="status"
      aria-label={`City status: ${config.label}`}
    >
      <Shield className="h-3 w-3" aria-hidden="true" />
      <span className="relative flex h-2 w-2">
        <span
          className={cn(
            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
            config.dot,
          )}
        />
        <span
          className={cn(
            "relative inline-flex h-2 w-2 rounded-full",
            config.dot,
          )}
        />
      </span>
      City Status: {config.label}
    </div>
  );
}
