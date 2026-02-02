/**
 * RiskDisplay Component
 *
 * Large, centered display showing flood risk level with visual feedback.
 * Color-coded background and icon based on risk level.
 */

import { CheckCircle, AlertTriangle, XCircle, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { RISK_CONFIGS, type RiskLevel } from '@/types';

/**
 * RiskDisplay component props
 */
interface RiskDisplayProps {
  /** Risk level (0 = Safe, 1 = Alert, 2 = Critical) */
  riskLevel: RiskLevel;
  /** Probability of flooding (0-1) */
  probability: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Map of risk level to icon components
 */
const RISK_ICONS: Record<RiskLevel, LucideIcon> = {
  0: CheckCircle,
  1: AlertTriangle,
  2: XCircle,
};

/**
 * Get confidence level text based on probability
 */
function getConfidenceLevel(probability: number): string {
  if (probability >= 0.9) return 'Very High Confidence';
  if (probability >= 0.75) return 'High Confidence';
  if (probability >= 0.5) return 'Moderate Confidence';
  if (probability >= 0.25) return 'Low Confidence';
  return 'Very Low Confidence';
}

/**
 * RiskDisplay renders a prominent risk level indicator
 */
export function RiskDisplay({
  riskLevel,
  probability,
  className,
}: RiskDisplayProps) {
  const config = RISK_CONFIGS[riskLevel];
  const Icon = RISK_ICONS[riskLevel];
  const percentProbability = Math.round(probability * 100);
  const confidenceLevel = getConfidenceLevel(probability);

  return (
    <div
      className={cn(
        'rounded-xl p-8 text-center animate-in fade-in duration-500',
        config.bgColor,
        className
      )}
    >
      {/* Icon */}
      <div className="flex justify-center mb-4">
        <Icon className={cn('h-20 w-20', config.color)} strokeWidth={1.5} />
      </div>

      {/* Risk Label */}
      <h2 className={cn('text-4xl font-bold mb-2', config.color)}>
        {config.label}
      </h2>

      {/* Risk Level Badge */}
      <p className="text-lg text-muted-foreground mb-4">
        Risk Level {riskLevel}
      </p>

      {/* Probability */}
      <div className="mb-4">
        <p className={cn('text-5xl font-bold', config.color)}>
          {percentProbability}%
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          Flood Probability
        </p>
      </div>

      {/* Confidence Indicator */}
      <div className="mt-6 pt-4 border-t border-current/10">
        <p className="text-sm font-medium text-muted-foreground">
          {confidenceLevel}
        </p>
        <div className="mt-2 h-2 bg-white/50 rounded-full overflow-hidden relative">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500 absolute inset-y-0 left-0',
              probability >= 0.9 ? 'w-[90%]' :
              probability >= 0.75 ? 'w-3/4' :
              probability >= 0.5 ? 'w-1/2' :
              probability >= 0.25 ? 'w-1/4' :
              probability >= 0.1 ? 'w-[10%]' : 'w-[5%]',
              {
                'bg-green-600': riskLevel === 0,
                'bg-amber-600': riskLevel === 1,
                'bg-red-600': riskLevel === 2,
              }
            )}
          />
        </div>
      </div>
    </div>
  );
}

export default RiskDisplay;
