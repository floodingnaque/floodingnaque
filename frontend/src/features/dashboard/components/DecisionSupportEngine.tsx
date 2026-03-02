/**
 * DecisionSupportEngine Component
 *
 * Provides intelligent, risk-level-aware action recommendations
 * for LGU/DRRMO operators. Shows a checklist of suggested actions
 * when flood risk is elevated, helping operators coordinate response.
 */

import { useState, useCallback, memo } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  ShieldCheck,
  Radio,
  Building2,
  Users,
  Truck,
  PhoneCall,
  Eye,
  CloudRain,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { RiskLevel } from '@/types';

// ---------------------------------------------------------------------------
// Action definitions per risk level
// ---------------------------------------------------------------------------

interface Action {
  id: string;
  icon: React.ElementType;
  label: string;
  description: string;
}

const HIGH_RISK_ACTIONS: Action[] = [
  {
    id: 'early-warning',
    icon: Radio,
    label: 'Activate Early Warning System',
    description: 'Trigger barangay-level sirens and SMS broadcast',
  },
  {
    id: 'evac-center',
    icon: Building2,
    label: 'Prepare Evacuation Centers',
    description: 'Open designated shelters, stage supplies',
  },
  {
    id: 'notify-officials',
    icon: PhoneCall,
    label: 'Notify Barangay Officials',
    description: 'Alert all 16 barangay captains and BDRRMC heads',
  },
  {
    id: 'rescue-team',
    icon: Truck,
    label: 'Deploy Rescue Teams',
    description: 'Pre-position rubber boats and rescue personnel',
  },
  {
    id: 'coordinate',
    icon: Users,
    label: 'Coordinate with NDRRMC',
    description: 'Escalate to regional and national disaster council',
  },
];

const MODERATE_RISK_ACTIONS: Action[] = [
  {
    id: 'monitor',
    icon: Eye,
    label: 'Intensified Monitoring',
    description: 'Increase sensor polling frequency to 5-minute intervals',
  },
  {
    id: 'standby',
    icon: Users,
    label: 'Place Teams on Standby',
    description: 'Alert rescue and evacuation teams for possible deployment',
  },
  {
    id: 'rainfall-watch',
    icon: CloudRain,
    label: 'Track Rainfall Trend',
    description: 'Monitor upstream precipitation and PAGASA bulletins',
  },
];

const RISK_CONFIG: Record<RiskLevel, {
  icon: React.ElementType;
  title: string;
  subtitle: string;
  badgeLabel: string;
  badgeClass: string;
  borderClass: string;
  actions: Action[];
}> = {
  2: {
    icon: ShieldAlert,
    title: 'High Risk Response Protocol',
    subtitle: 'Immediate action recommended - activate emergency procedures',
    badgeLabel: 'HIGH RISK',
    badgeClass: 'bg-risk-critical text-white',
    borderClass: 'border-risk-critical/30',
    actions: HIGH_RISK_ACTIONS,
  },
  1: {
    icon: AlertTriangle,
    title: 'Moderate Risk - Preparedness Mode',
    subtitle: 'Elevated monitoring and team readiness',
    badgeLabel: 'MODERATE',
    badgeClass: 'bg-risk-alert text-black',
    borderClass: 'border-risk-alert/30',
    actions: MODERATE_RISK_ACTIONS,
  },
  0: {
    icon: ShieldCheck,
    title: 'Normal Operations',
    subtitle: 'No elevated flood risk detected - routine monitoring active',
    badgeLabel: 'SAFE',
    badgeClass: 'bg-risk-safe text-white',
    borderClass: 'border-risk-safe/30',
    actions: [],
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface DecisionSupportEngineProps {
  riskLevel: RiskLevel;
  className?: string;
}

export const DecisionSupportEngine = memo(function DecisionSupportEngine({
  riskLevel,
  className,
}: DecisionSupportEngineProps) {
  const [checked, setChecked] = useState<Set<string>>(new Set());

  const toggle = useCallback((id: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const config = RISK_CONFIG[riskLevel];
  const RiskIcon = config.icon;
  const completedCount = checked.size;
  const totalActions = config.actions.length;

  return (
    <Card className={cn(config.borderClass, className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <RiskIcon className="h-5 w-5" />
            Decision Support
          </CardTitle>
          <Badge className={cn('text-[10px]', config.badgeClass)}>{config.badgeLabel}</Badge>
        </div>
        <CardDescription>{config.subtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        {totalActions > 0 ? (
          <div className="space-y-3">
            {/* Progress */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Response checklist</span>
              <span>{completedCount}/{totalActions} completed</span>
            </div>
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-300',
                  riskLevel === 2 ? 'bg-risk-critical' : 'bg-risk-alert',
                )}
                style={{ width: `${totalActions > 0 ? (completedCount / totalActions) * 100 : 0}%` }}
              />
            </div>

            {/* Actions */}
            <div className="space-y-2">
              {config.actions.map((action) => {
                const ActionIcon = action.icon;
                const isDone = checked.has(action.id);
                return (
                  <button
                    key={action.id}
                    onClick={() => toggle(action.id)}
                    className={cn(
                      'flex items-start gap-3 w-full text-left p-3 rounded-lg border transition-colors',
                      isDone
                        ? 'bg-muted/50 border-muted'
                        : 'hover:bg-muted/30 border-border',
                    )}
                  >
                    <Checkbox
                      checked={isDone}
                      className="mt-0.5"
                      aria-label={action.label}
                    />
                    <ActionIcon className={cn('h-4 w-4 mt-0.5 shrink-0', isDone ? 'text-muted-foreground' : 'text-primary')} />
                    <div className="min-w-0">
                      <p className={cn('text-sm font-medium', isDone && 'line-through text-muted-foreground')}>
                        {action.label}
                      </p>
                      <p className="text-xs text-muted-foreground">{action.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-4">
            {config.title} - standard monitoring is active.
          </p>
        )}
      </CardContent>
    </Card>
  );
});

export default DecisionSupportEngine;
