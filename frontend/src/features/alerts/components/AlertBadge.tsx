/**
 * AlertBadge Component
 *
 * Small badge displaying flood risk level with appropriate color coding.
 */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { RISK_CONFIGS, type RiskLevel } from '@/types';

/**
 * AlertBadge component props
 */
interface AlertBadgeProps {
  /** Risk level (0 = Safe, 1 = Alert, 2 = Critical) */
  riskLevel: RiskLevel;
  /** Additional CSS classes */
  className?: string;
  /** Badge size variant */
  size?: 'sm' | 'md' | 'lg';
}

/**
 * Risk level color mapping for badges
 */
const RISK_BADGE_STYLES: Record<RiskLevel, string> = {
  0: 'bg-green-100 text-green-700 border-green-200 hover:bg-green-100',
  1: 'bg-amber-100 text-amber-700 border-amber-200 hover:bg-amber-100',
  2: 'bg-red-100 text-red-700 border-red-200 hover:bg-red-100',
};

/**
 * Size variants for badge
 */
const SIZE_STYLES: Record<'sm' | 'md' | 'lg', string> = {
  sm: 'text-[10px] px-1.5 py-0',
  md: 'text-xs px-2 py-0.5',
  lg: 'text-sm px-2.5 py-1',
};

/**
 * AlertBadge renders a color-coded risk level indicator
 *
 * @example
 * <AlertBadge riskLevel={2} /> // Shows "Critical" in red
 * <AlertBadge riskLevel={0} size="sm" /> // Shows "Safe" in green, small
 */
export function AlertBadge({
  riskLevel,
  className,
  size = 'md',
}: AlertBadgeProps) {
  const config = RISK_CONFIGS[riskLevel];

  return (
    <Badge
      variant="outline"
      className={cn(
        RISK_BADGE_STYLES[riskLevel],
        SIZE_STYLES[size],
        'font-medium',
        className
      )}
    >
      {config.label}
    </Badge>
  );
}

export default AlertBadge;
