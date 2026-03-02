/**
 * EmergencyInfoPanel Component (P1 - MUST HAVE)
 *
 * Static emergency contact information and nearest evacuation centers
 * drawn from the centralized paranaque.ts data.
 * Always visible on the Resident dashboard for quick reference.
 *
 * When a riskLevel prop is provided, the panel displays dynamic
 * advisory messages based on the current flood risk.
 */

import { memo } from 'react';
import { Phone, MapPin, ShieldCheck, ExternalLink, AlertTriangle, ShieldAlert, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { EMERGENCY_CONTACTS, BARANGAYS } from '@/config/paranaque';
import { cn } from '@/lib/utils';
import type { RiskLevel } from '@/types';

// ---------------------------------------------------------------------------
// Risk-based advisory messages
// ---------------------------------------------------------------------------

const RISK_ADVISORIES: Record<RiskLevel, { icon: React.ElementType; title: string; items: string[]; variant: 'default' | 'destructive' }> = {
  2: {
    icon: ShieldAlert,
    title: 'High Risk Advisory',
    items: [
      'Prepare go-bag with essentials',
      'Monitor official DRRMO announcements',
      'Possible evacuation activation - stay alert',
      'Avoid low-lying areas and waterways',
    ],
    variant: 'destructive',
  },
  1: {
    icon: AlertTriangle,
    title: 'Moderate Risk Advisory',
    items: [
      'Stay alert and monitor updates',
      'Track rainfall trend closely',
      'Review evacuation routes as precaution',
    ],
    variant: 'default',
  },
  0: {
    icon: Info,
    title: 'Current Advisory',
    items: ['No immediate flooding risk detected'],
    variant: 'default',
  },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ContactRow({
  name,
  phone,
  highlight,
}: {
  name: string;
  phone: string;
  highlight?: boolean;
}) {
  return (
    <a
      href={`tel:${phone.replace(/[^+\d]/g, '')}`}
      className={cn(
        'flex items-center justify-between px-3 py-2 rounded-lg transition-colors',
        highlight
          ? 'bg-risk-critical/10 hover:bg-risk-critical/20'
          : 'hover:bg-muted',
      )}
    >
      <div className="flex items-center gap-2">
        <Phone className={cn('h-4 w-4 shrink-0', highlight ? 'text-risk-critical' : 'text-muted-foreground')} />
        <span className={cn('text-sm font-medium', highlight && 'text-risk-critical')}>{name}</span>
      </div>
      <span className="text-sm font-mono text-muted-foreground">{phone}</span>
    </a>
  );
}

function EvacuationCenterRow({ name, barangay }: { name: string; barangay: string }) {
  return (
    <div className="flex items-start gap-2 px-3 py-1.5">
      <MapPin className="h-3.5 w-3.5 mt-0.5 text-risk-safe shrink-0" />
      <div>
        <span className="text-sm">{name}</span>
        <span className="text-xs text-muted-foreground ml-1">({barangay})</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface EmergencyInfoPanelProps {
  className?: string;
  /** If provided, only show evacuation centers for high-risk barangays */
  filterHighRisk?: boolean;
  /** Current risk level - when provided, shows dynamic advisory messages */
  riskLevel?: RiskLevel;
}

export const EmergencyInfoPanel = memo(function EmergencyInfoPanel({
  className,
  filterHighRisk = true,
  riskLevel,
}: EmergencyInfoPanelProps) {
  const evacBarangays = filterHighRisk
    ? BARANGAYS.filter((b) => b.floodRisk === 'high')
    : BARANGAYS;

  const advisory = riskLevel != null ? RISK_ADVISORIES[riskLevel] : null;
  const AdvisoryIcon = advisory?.icon ?? Info;

  return (
    <Card className={cn('', className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-5 w-5 text-risk-safe" />
          Emergency Information
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Dynamic Advisory */}
        {advisory && (
          <Alert variant={advisory.variant} className="py-3">
            <AdvisoryIcon className="h-4 w-4" />
            <AlertDescription>
              <p className="font-semibold text-sm mb-1">{advisory.title}</p>
              <ul className="space-y-0.5">
                {advisory.items.map((item) => (
                  <li key={item} className="text-xs flex items-start gap-1.5">
                    <span className="mt-1 h-1 w-1 rounded-full bg-current shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}
        {/* Hotlines */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Emergency Hotlines
          </h4>
          <div className="space-y-1">
            {Object.values(EMERGENCY_CONTACTS).map((c) => (
              <ContactRow
                key={c.name}
                name={c.name}
                phone={c.phone}
                highlight={c.name.includes('MDRRMO')}
              />
            ))}
          </div>
        </div>

        {/* Evacuation Centers */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Evacuation Centers {filterHighRisk && '(High-Risk Areas)'}
          </h4>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {evacBarangays.map((b) => (
              <EvacuationCenterRow
                key={b.key}
                name={b.evacuationCenter}
                barangay={b.name}
              />
            ))}
          </div>
        </div>

        {/* NDRRMC link */}
        <a
          href="https://ndrrmc.gov.ph"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-primary hover:underline"
        >
          <ExternalLink className="h-3 w-3" />
          NDRRMC Official Updates
        </a>
      </CardContent>
    </Card>
  );
});
