/**
 * SmsSimulationPanel Component (P4 - NICE TO HAVE)
 *
 * Allows LGU operators to send a simulated SMS alert.
 * Always runs in sandbox mode - no real messages are sent.
 * Displays the simulation result inline after submission.
 */

import { useState, useCallback } from 'react';
import {
  MessageSquare,
  Send,
  Loader2,
  CheckCircle2,
  Phone,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useSimulateSms } from '../hooks/useAlerts';
import type { SmsSimulationResponse } from '../services/alertsApi';

// ---------------------------------------------------------------------------
// Risk level options
// ---------------------------------------------------------------------------

const RISK_OPTIONS = [
  { value: 0, label: 'Safe', color: 'bg-risk-safe text-white' },
  { value: 1, label: 'Alert', color: 'bg-risk-alert text-black' },
  { value: 2, label: 'Critical', color: 'bg-risk-critical text-white' },
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SmsSimulationPanel({ className }: { className?: string }) {
  const [phone, setPhone] = useState('');
  const [riskLevel, setRiskLevel] = useState<number>(1);
  const [message, setMessage] = useState('');
  const [lastResult, setLastResult] = useState<SmsSimulationResponse | null>(null);

  const { mutate: simulate, isPending } = useSimulateSms({
    onSuccess: (data) => {
      setLastResult(data);
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!phone.trim()) return;
      setLastResult(null);
      simulate({
        phone: phone.trim(),
        riskLevel,
        message: message.trim() || undefined,
      });
    },
    [phone, riskLevel, message, simulate],
  );

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          SMS Alert Simulation
          <Badge variant="outline" className="ml-auto text-[10px]">
            Sandbox
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Phone number */}
          <div className="space-y-1.5">
            <label
              htmlFor="sim-phone"
              className="text-xs font-medium text-muted-foreground"
            >
              Recipient Phone (PH format)
            </label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                id="sim-phone"
                type="tel"
                placeholder="09171234567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className={cn(
                  'flex h-9 w-full rounded-md border border-input bg-transparent',
                  'pl-9 pr-3 py-1 text-sm shadow-sm transition-colors',
                  'placeholder:text-muted-foreground focus-visible:outline-none',
                  'focus-visible:ring-1 focus-visible:ring-ring',
                )}
                required
              />
            </div>
          </div>

          {/* Risk level selector */}
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              Risk Level
            </span>
            <div className="flex gap-2">
              {RISK_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setRiskLevel(opt.value)}
                  className={cn(
                    'px-3 py-1 rounded-md text-xs font-semibold transition-all',
                    riskLevel === opt.value
                      ? opt.color
                      : 'bg-muted text-muted-foreground hover:bg-muted/80',
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom message */}
          <div className="space-y-1.5">
            <label
              htmlFor="sim-message"
              className="text-xs font-medium text-muted-foreground"
            >
              Custom Message (optional)
            </label>
            <textarea
              id="sim-message"
              rows={2}
              placeholder="Leave blank for auto-generated message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className={cn(
                'flex w-full rounded-md border border-input bg-transparent',
                'px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground',
                'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                'resize-none',
              )}
            />
          </div>

          {/* Submit */}
          <Button
            type="submit"
            size="sm"
            className="w-full"
            disabled={isPending || !phone.trim()}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Send className="h-4 w-4 mr-2" />
            )}
            Send Simulation
          </Button>
        </form>

        {/* Result banner */}
        {lastResult && (
          <div className="mt-4 rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30 p-3 space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold text-risk-safe">
              <CheckCircle2 className="h-4 w-4" />
              Simulation Sent
            </div>
            <p className="text-xs text-muted-foreground">
              <strong>To:</strong> {lastResult.phone}
            </p>
            <p className="text-xs text-muted-foreground">
              <strong>Risk:</strong> {lastResult.risk_label} (level{' '}
              {lastResult.risk_level})
            </p>
            <p className="text-xs text-muted-foreground line-clamp-2">
              <strong>Message:</strong> {lastResult.message}
            </p>
            <p className="text-[10px] text-muted-foreground/70">
              {new Date(lastResult.simulated_at).toLocaleString('en-PH')}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default SmsSimulationPanel;
