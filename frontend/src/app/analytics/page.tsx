/**
 * Analytics Page
 *
 * Data visualization dashboard for LGU operators and admins.
 * Shows rainfall trends, risk distribution, alert frequency,
 * and model performance charts.
 */

import { BarChart3 } from 'lucide-react';
import {
  RainfallTrend,
  RiskDistribution,
  AlertFrequency,
} from '@/features/dashboard/components/AnalyticsCharts';
import {
  ModelSummaryCards,
  AccuracyProgressionChart,
} from '@/features/dashboard/components/ModelManagement';
import { ForecastPanel } from '@/features/dashboard/components/ForecastPanel';

export default function AnalyticsPage() {
  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <header className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <BarChart3 className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Weather trends, risk analysis, and model performance
          </p>
        </div>
      </header>

      {/* Model Summary */}
      <ModelSummaryCards />

      {/* Charts Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        <RainfallTrend />
        <ForecastPanel hours={12} />
        <RiskDistribution />
        <AlertFrequency />
        <AccuracyProgressionChart className="lg:col-span-2" />
      </div>
    </div>
  );
}
