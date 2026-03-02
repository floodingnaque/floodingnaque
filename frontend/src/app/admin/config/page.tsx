/**
 * Admin System Configuration Page
 *
 * Feature flags management, risk threshold settings,
 * and system-wide configuration controls.
 */

import { useState, useCallback } from 'react';
import {
  SlidersHorizontal,
  Save,
  ToggleLeft,
  AlertTriangle,
  Gauge,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { useFeatureFlags, useUpdateFeatureFlag } from '@/features/admin/hooks/useAdmin';

const FLAG_LABELS: Record<string, { label: string; description: string }> = {
  sse_alerts: {
    label: 'SSE Live Alerts',
    description: 'Enable server-sent events for real-time alert streaming',
  },
  tidal_monitoring: {
    label: 'Tidal Monitoring',
    description: 'Include tidal data in risk assessments',
  },
  sms_simulation: {
    label: 'SMS Simulation',
    description: 'Enable SMS alert simulation panel for operators',
  },
  model_versioning: {
    label: 'Model Versioning',
    description: 'Enable multi-version model management',
  },
  csv_export: {
    label: 'CSV Export',
    description: 'Allow DRRMO CSV export for barangay data',
  },
  advanced_analytics: {
    label: 'Advanced Analytics',
    description: 'Enable extended analytics charts and trend analysis',
  },
  decision_support: {
    label: 'Decision Support Engine',
    description: 'Show risk-aware action recommendations for operators',
  },
  public_reports: {
    label: 'Public Reports',
    description: 'Allow residents to download monthly flood reports',
  },
};

interface ThresholdConfig {
  lowRisk: number;
  moderateRisk: number;
  highRisk: number;
  alertCooldownMinutes: number;
}

function loadThresholds(): ThresholdConfig {
  try {
    const raw = localStorage.getItem('risk_thresholds');
    if (raw) return JSON.parse(raw);
  } catch { /* use defaults */ }
  return {
    lowRisk: 30,
    moderateRisk: 60,
    highRisk: 80,
    alertCooldownMinutes: 15,
  };
}

function saveThresholds(config: ThresholdConfig) {
  localStorage.setItem('risk_thresholds', JSON.stringify(config));
}

export default function AdminConfigPage() {
  const { data: flagsResponse, isLoading: flagsLoading } = useFeatureFlags();
  const updateFlag = useUpdateFeatureFlag();

  const [thresholds, setThresholds] = useState<ThresholdConfig>(loadThresholds);
  const [thresholdsDirty, setThresholdsDirty] = useState(false);

  const flags = flagsResponse?.data ?? {};

  const handleFlagToggle = useCallback((flag: string, currentValue: boolean) => {
    updateFlag.mutate(
      { flag, enabled: !currentValue },
      {
        onSuccess: () => toast.success(`Feature flag "${flag}" updated`),
        onError: () => toast.error(`Failed to update "${flag}"`),
      },
    );
  }, [updateFlag]);

  const handleThresholdChange = useCallback((key: keyof ThresholdConfig, value: string) => {
    const num = Number(value);
    if (Number.isNaN(num)) return;
    setThresholds((prev) => ({ ...prev, [key]: num }));
    setThresholdsDirty(true);
  }, []);

  const handleSaveThresholds = useCallback(() => {
    if (thresholds.moderateRisk <= thresholds.lowRisk || thresholds.highRisk <= thresholds.moderateRisk) {
      toast.error('Risk thresholds must be in ascending order: Low < Moderate < High');
      return;
    }
    saveThresholds(thresholds);
    setThresholdsDirty(false);
    toast.success('Risk thresholds saved');
  }, [thresholds]);

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <header className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <SlidersHorizontal className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System Configuration</h1>
          <p className="text-sm text-muted-foreground">
            Feature flags, risk thresholds, and system-wide settings
          </p>
        </div>
      </header>

      {/* Feature Flags */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ToggleLeft className="h-4 w-4" />
            Feature Flags
          </CardTitle>
          <CardDescription>
            Toggle system capabilities on or off. Changes take effect immediately.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {flagsLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between">
                  <Skeleton className="h-5 w-48" />
                  <Skeleton className="h-6 w-11" />
                </div>
              ))}
            </div>
          ) : Object.keys(flags).length === 0 ? (
            <div className="space-y-4">
              {Object.entries(FLAG_LABELS).map(([key, { label, description }]) => (
                <div key={key} className="flex items-center justify-between py-2">
                  <div className="space-y-0.5">
                    <Label className="text-sm font-medium">{label}</Label>
                    <p className="text-xs text-muted-foreground">{description}</p>
                  </div>
                  <Switch
                    checked={true}
                    onCheckedChange={() => handleFlagToggle(key, true)}
                    disabled={updateFlag.isPending}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(flags).map(([key, enabled]) => {
                const meta = FLAG_LABELS[key] ?? { label: key, description: '' };
                return (
                  <div key={key} className="flex items-center justify-between py-2">
                    <div className="space-y-0.5">
                      <Label className="text-sm font-medium">{meta.label}</Label>
                      <p className="text-xs text-muted-foreground">{meta.description}</p>
                    </div>
                    <Switch
                      checked={!!enabled}
                      onCheckedChange={() => handleFlagToggle(key, !!enabled)}
                      disabled={updateFlag.isPending}
                    />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Risk Thresholds */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Gauge className="h-4 w-4" />
            Risk Thresholds
          </CardTitle>
          <CardDescription>
            Configure flood risk classification boundaries (percentage).
            These thresholds determine how prediction scores map to Low, Moderate, and High risk levels.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="lowRisk" className="text-sm">
                Low Risk Threshold
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="lowRisk"
                  type="number"
                  min={0}
                  max={100}
                  value={thresholds.lowRisk}
                  onChange={(e) => handleThresholdChange('lowRisk', e.target.value)}
                />
                <span className="text-sm text-muted-foreground">%</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Scores below this are considered safe
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="moderateRisk" className="text-sm">
                Moderate Risk Threshold
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="moderateRisk"
                  type="number"
                  min={0}
                  max={100}
                  value={thresholds.moderateRisk}
                  onChange={(e) => handleThresholdChange('moderateRisk', e.target.value)}
                />
                <span className="text-sm text-muted-foreground">%</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Scores between Low and this trigger caution
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="highRisk" className="text-sm">
                High Risk Threshold
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="highRisk"
                  type="number"
                  min={0}
                  max={100}
                  value={thresholds.highRisk}
                  onChange={(e) => handleThresholdChange('highRisk', e.target.value)}
                />
                <span className="text-sm text-muted-foreground">%</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Scores at or above this trigger emergency alerts
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="cooldown" className="text-sm">
                Alert Cooldown
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="cooldown"
                  type="number"
                  min={1}
                  max={120}
                  value={thresholds.alertCooldownMinutes}
                  onChange={(e) => handleThresholdChange('alertCooldownMinutes', e.target.value)}
                />
                <span className="text-sm text-muted-foreground">min</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Minimum interval between duplicate alerts
              </p>
            </div>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {thresholdsDirty && (
                <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-300">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Unsaved Changes
                </Badge>
              )}
            </div>
            <Button
              onClick={handleSaveThresholds}
              disabled={!thresholdsDirty}
            >
              <Save className="h-4 w-4 mr-2" />
              Save Thresholds
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
