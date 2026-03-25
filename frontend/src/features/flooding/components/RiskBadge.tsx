/**
 * RiskBadge Component
 *
 * Compact colored badge for flood risk levels.
 * Used across all role dashboards for consistent risk display.
 */

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";

const RISK_CONFIG = {
  0: { label: "Safe", cls: "bg-risk-safe text-white" },
  1: { label: "Alert", cls: "bg-risk-alert text-black" },
  2: { label: "Critical", cls: "bg-risk-critical text-white" },
} as const;

interface RiskBadgeProps {
  /** Risk level: 0 = Safe, 1 = Alert, 2 = Critical */
  level: number;
  className?: string;
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  const cfg = RISK_CONFIG[level as keyof typeof RISK_CONFIG] ?? RISK_CONFIG[0];
  return (
    <Badge className={cn("text-[10px] px-1.5", cfg.cls, className)}>
      {cfg.label}
    </Badge>
  );
}
