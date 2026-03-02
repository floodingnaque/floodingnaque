/**
 * ResidentDashboard Component (P1 — MUST HAVE)
 *
 * The primary view for `user` role.
 * Layout:
 *   ┌────────────────────────────────────────────┐
 *   │  FloodStatusHero (full-width)              │
 *   ├───────────────────────┬────────────────────┤
 *   │  BarangayRiskMap      │  AlertFeed +       │
 *   │  (2/3)                │  EmergencyInfo     │
 *   │                       │  (1/3)             │
 *   └───────────────────────┴────────────────────┘
 */

import { Droplets, Bell, Download, FileText } from 'lucide-react';
import { ConnectionStatus, ErrorDisplay } from '@/components/feedback';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useLivePrediction } from '@/features/flooding/hooks/useLivePrediction';
import { useCurrentTide } from '@/features/weather/hooks/useTides';
import { TidalRiskIndicator } from '@/features/weather/components/TidalRiskIndicator';
import { useRecentAlerts } from '@/features/alerts';
import { useReportExport } from '@/features/reports/hooks/useReports';
import { RainfallTrend, AlertFrequency } from './AnalyticsCharts';
import { FloodStatusHero } from './FloodStatusHero';
import { BarangayRiskMap } from './BarangayRiskMap';
import { EmergencyInfoPanel } from './EmergencyInfoPanel';
import { cn } from '@/lib/utils';
import type { RiskLevel } from '@/types';

// ---------------------------------------------------------------------------
// Public Report Download widget
// ---------------------------------------------------------------------------

function PublicReportDownload() {
  const { exportReport, isExportingPDF, isExportingCSV } = useReportExport();

  const handleMonthlyReport = () => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    exportReport(
      {
        report_type: 'predictions',
        start_date: start.toISOString().split('T')[0],
        end_date: end.toISOString().split('T')[0],
      },
      'pdf',
    );
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Public Reports
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={handleMonthlyReport}
          disabled={isExportingPDF}
        >
          <Download className="h-3.5 w-3.5" />
          {isExportingPDF ? 'Generating...' : 'Monthly Flood Summary (PDF)'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={() => {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - 7);
            exportReport(
              {
                report_type: 'weather',
                start_date: start.toISOString().split('T')[0],
                end_date: end.toISOString().split('T')[0],
              },
              'csv',
            );
          }}
          disabled={isExportingCSV}
        >
          <Download className="h-3.5 w-3.5" />
          {isExportingCSV ? 'Generating...' : 'Weekly Weather Data (CSV)'}
        </Button>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Alert Feed sub-component (compact list for sidebar)
// ---------------------------------------------------------------------------

function AlertFeed() {
  const { data: alerts, isLoading } = useRecentAlerts(5);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Recent Alerts
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!alerts?.length) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Recent Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-4">
            No recent alerts
          </p>
        </CardContent>
      </Card>
    );
  }

  const riskBadge = (level: number) => {
    const cfg =
      level === 2
        ? { label: 'Critical', cls: 'bg-risk-critical text-white' }
        : level === 1
        ? { label: 'Alert', cls: 'bg-risk-alert text-black' }
        : { label: 'Safe', cls: 'bg-risk-safe text-white' };
    return <Badge className={cn('text-[10px] px-1.5', cfg.cls)}>{cfg.label}</Badge>;
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Bell className="h-4 w-4" />
          Recent Alerts
          <Badge variant="secondary" className="ml-auto text-xs">
            {alerts.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 max-h-64 overflow-y-auto">
        {alerts.map((a) => (
          <div
            key={a.id}
            className="flex items-start gap-2 p-2 rounded-lg border text-sm"
          >
            {riskBadge(a.risk_level)}
            <div className="flex-1 min-w-0">
              <p className="truncate">{a.message}</p>
              <p className="text-xs text-muted-foreground">
                {new Date(a.created_at).toLocaleString('en-PH', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
                {a.location && ` · ${a.location}`}
              </p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Resident Dashboard
// ---------------------------------------------------------------------------

export function ResidentDashboard() {
  const {
    data: prediction,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useLivePrediction();

  const { data: currentTide } = useCurrentTide(true);

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Droplets className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Flood Monitor
              </h1>
              <p className="text-sm text-muted-foreground">
                Parañaque City — Real-time flood risk assessment
              </p>
            </div>
          </div>
          <ConnectionStatus showLabel size="md" />
        </header>

        {/* Error */}
        {isError && (
          <ErrorDisplay
            error={error}
            retry={() => refetch()}
            title="Unable to fetch prediction"
          />
        )}

        {/* Hero Risk Card */}
        <FloodStatusHero
          prediction={prediction}
          isLoading={isLoading}
          tideHeight={currentTide?.height}
          onRefresh={() => refetch()}
          isFetching={isFetching}
        />

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left: Map (2/3) */}
          <div className="lg:col-span-2">
            <BarangayRiskMap
              prediction={prediction}
              height={420}
            />
          </div>

          {/* Right: Alerts + Tides + Emergency (1/3) */}
          <div className="space-y-6">
            <AlertFeed />
            <TidalRiskIndicator />
            <EmergencyInfoPanel riskLevel={prediction?.risk_level as RiskLevel | undefined} />
            <PublicReportDownload />
          </div>
        </div>

        {/* Trend Charts */}
        <div className="grid gap-6 md:grid-cols-2">
          <RainfallTrend />
          <AlertFrequency />
        </div>
      </div>
    </div>
  );
}

export default ResidentDashboard;
