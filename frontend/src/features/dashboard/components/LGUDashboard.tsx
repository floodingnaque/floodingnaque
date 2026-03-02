/**
 * LGUDashboard Component (P1 - MUST HAVE)
 *
 * Operational dashboard for LGU / MDRRMO operators.
 *
 * Layout:
 *   ┌─────────── KPI Row (5 stat cards) ────────────┐
 *   ├───────────────────┬───────────────────────────┤
 *   │ Prediction Panel  │  Precipitation Forecast    │
 *   │ + Confidence      │  (Recharts bar chart)      │
 *   ├───────────────────┼───────────────────────────┤
 *   │ Barangay Risk Map │  Feature Importances       │
 *   │ (Leaflet)         │  (horizontal bar chart)    │
 *   └───────────────────┴───────────────────────────┘
 */

import { useMemo } from 'react';
import {
  Shield,
  Activity,
  AlertTriangle,
  CloudRain,
  Cpu,
  BarChart3,
  TrendingUp,
} from 'lucide-react';
import { FloodIcon } from '@/components/icons/FloodIcon';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ConnectionStatus, ErrorDisplay } from '@/components/feedback';
import { cn } from '@/lib/utils';

import { useLivePrediction } from '@/features/flooding/hooks/useLivePrediction';
import { useDashboardStats } from '@/features/dashboard/hooks/useDashboard';
import { useCurrentTide } from '@/features/weather/hooks/useTides';
import { TidalRiskIndicator } from '@/features/weather/components/TidalRiskIndicator';
import { SmsSimulationPanel } from '@/features/alerts/components/SmsSimulationPanel';
import { BARANGAYS, FEATURE_IMPORTANCES, MODEL_VERSIONS } from '@/config/paranaque';
import { RainfallTrend, RiskDistribution, AlertFrequency } from './AnalyticsCharts';
import { ModelSummaryCards } from './ModelManagement';
import { DecisionSupportEngine } from './DecisionSupportEngine';
import { FloodStatusHero } from './FloodStatusHero';
import { BarangayRiskMap } from './BarangayRiskMap';
import { ForecastPanel } from './ForecastPanel';
import type { RiskLevel } from '@/types';

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------

function KPICard({
  icon: Icon,
  label,
  value,
  subtitle,
  accent,
  isLoading,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subtitle?: string;
  accent?: string;
  isLoading?: boolean;
}) {
  return (
    <Card>
      <CardContent className="pt-5 pb-4 px-4">
        <div className="flex items-start gap-3">
          <div className={cn('p-2 rounded-lg', accent ?? 'bg-primary/10')}>
            <Icon className={cn('h-4 w-4', accent ? 'text-white' : 'text-primary')} />
          </div>
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground truncate">{label}</p>
            {isLoading ? (
              <Skeleton className="h-7 w-14 mt-0.5" />
            ) : (
              <p className="text-xl font-bold">{value}</p>
            )}
            {subtitle && (
              <p className="text-[10px] text-muted-foreground mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Feature Importance Chart
// ---------------------------------------------------------------------------

function FeatureImportanceChart({ className }: { className?: string }) {
  const chartData = useMemo(
    () =>
      FEATURE_IMPORTANCES.slice(0, 8).map((f) => ({
        name: f.feature.replace(/_/g, ' '),
        importance: +(f.importance * 100).toFixed(1),
      })),
    [],
  );

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Feature Importances
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 0, right: 10, bottom: 0, left: 80 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              type="number"
              tick={{ fontSize: 11 }}
              unit="%"
              className="text-muted-foreground"
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11 }}
              width={80}
              className="text-muted-foreground"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
                fontSize: 12,
              }}
              formatter={(v) => [`${v}%`, 'Importance']}
            />
            <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
              {chartData.map((_, idx) => (
                <Cell
                  key={idx}
                  fill={idx === 0 ? '#1E3A5F' : idx < 3 ? '#3B6FA0' : '#8BAFCC'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Model Version Badge
// ---------------------------------------------------------------------------

function ModelVersionBadge() {
  const latest = MODEL_VERSIONS[MODEL_VERSIONS.length - 1];
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <Cpu className="h-3.5 w-3.5" />
      <span>
        Model <strong>{latest.version}</strong> · {(latest.accuracy * 100).toFixed(1)}% acc ·{' '}
        {latest.samples.toLocaleString()} samples
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main LGU Dashboard
// ---------------------------------------------------------------------------

export function LGUDashboard() {
  const {
    data: prediction,
    isLoading: predLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useLivePrediction();

  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: currentTide } = useCurrentTide(true);

  // Count high-risk barangays
  const highRiskCount = useMemo(
    () => BARANGAYS.filter((b) => b.floodRisk === 'high').length,
    [],
  );

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                LGU Operations Center
              </h1>
              <p className="text-sm text-muted-foreground">
                Parañaque MDRRMO - Flood Monitoring & Prediction
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ModelVersionBadge />
            <ConnectionStatus showLabel size="md" />
          </div>
        </header>

        {/* Error */}
        {isError && (
          <ErrorDisplay
            error={error}
            retry={() => refetch()}
            title="Prediction service unavailable"
          />
        )}

        {/* KPI Row */}
        <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
          <KPICard
            icon={AlertTriangle}
            label="Barangays at Risk"
            value={highRiskCount}
            subtitle={`of ${BARANGAYS.length} total`}
            accent="bg-risk-critical"
            isLoading={false}
          />
          <KPICard
            icon={CloudRain}
            label="Max Precipitation"
            value={
              prediction?.weather_data
                ? `${prediction.weather_data.precipitation.toFixed(1)} mm`
                : '-'
            }
            subtitle="Current reading"
            isLoading={predLoading}
          />
          <KPICard
            icon={Activity}
            label="Active Alerts"
            value={stats?.active_alerts ?? 0}
            subtitle="Unresolved"
            isLoading={statsLoading}
          />
          <KPICard
            icon={TrendingUp}
            label="Predictions Today"
            value={stats?.predictions_today ?? 0}
            isLoading={statsLoading}
          />
          <KPICard
            icon={FloodIcon}
            label="Avg Risk Level"
            value={
              stats?.avg_risk_level != null
                ? stats.avg_risk_level.toFixed(2)
                : '-'
            }
            subtitle="0 = Safe, 2 = Critical"
            isLoading={statsLoading}
          />
        </div>

        {/* Prediction Hero */}
        <FloodStatusHero
          prediction={prediction}
          isLoading={predLoading}
          tideHeight={currentTide?.height}
          onRefresh={() => refetch()}
          isFetching={isFetching}
        />

        {/* Main Grid */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Forecast */}
          <ForecastPanel hours={12} />

          {/* Feature Importance */}
          <FeatureImportanceChart />
        </div>

        {/* Live Analytics Section */}
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            Live Analytics
          </h2>
          <div className="grid gap-6 md:grid-cols-3">
            <RainfallTrend />
            <RiskDistribution />
            <AlertFrequency />
          </div>
        </div>

        {/* Decision Support + SMS Simulation */}
        <div className="grid gap-6 lg:grid-cols-2">
          <DecisionSupportEngine riskLevel={(prediction?.risk_level ?? 0) as RiskLevel} />
          <div className="space-y-6">
            <TidalRiskIndicator />
            <SmsSimulationPanel />
          </div>
        </div>

        {/* AI Model Health */}
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Cpu className="h-5 w-5 text-primary" />
            AI Model Health
          </h2>
          <ModelSummaryCards />
        </div>

        {/* Map (full-width) */}
        <BarangayRiskMap
          prediction={prediction}
          height={500}
        />
      </div>
    </div>
  );
}

export default LGUDashboard;
