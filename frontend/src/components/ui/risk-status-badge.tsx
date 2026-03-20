import { Badge } from "@/components/ui/badge";
import { PulsingDot } from "@/components/ui/pulsing-dot";
import { RISK_HEX } from "@/lib/colors";
import { cn } from "@/lib/utils";
import type { RiskLabel } from "@/types";

const riskStyles: Record<RiskLabel, { bg: string; text: string; dot: string }> =
  {
    Safe: {
      bg: "bg-risk-safe/15 border-risk-safe/30",
      text: "text-risk-safe",
      dot: RISK_HEX.safe,
    },
    Alert: {
      bg: "bg-risk-alert/15 border-risk-alert/30",
      text: "text-risk-alert",
      dot: RISK_HEX.alert,
    },
    Critical: {
      bg: "bg-risk-critical/15 border-risk-critical/30",
      text: "text-risk-critical",
      dot: RISK_HEX.critical,
    },
  };

interface RiskStatusBadgeProps {
  risk: RiskLabel;
  className?: string;
}

export function RiskStatusBadge({ risk, className }: RiskStatusBadgeProps) {
  const style = riskStyles[risk];
  return (
    <Badge
      variant="outline"
      className={cn("gap-1.5 font-bold", style.bg, style.text, className)}
    >
      <PulsingDot color={style.dot} size="sm" />
      {risk}
    </Badge>
  );
}
