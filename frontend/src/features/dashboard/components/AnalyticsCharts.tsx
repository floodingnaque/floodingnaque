/**
 * AnalyticsCharts Component (P2 — HIGH VALUE)
 *
 * Collection of Recharts visualizations for the Analytics page:
 * - 7-day rainfall trend (area chart)
 * - Risk distribution pie chart
 * - Alert frequency bar chart
 *
 * Data-driven from /api/data/weather and /api/dashboard/stats.
 */

import { memo, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  CloudRain,
  PieChart as PieIcon,
  BarChart3,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { weatherApi } from '@/features/weather/services/weatherApi';
import { BARANGAYS } from '@/config/paranaque';

// ---------------------------------------------------------------------------
// Colors
// ---------------------------------------------------------------------------

const RISK_PIE_COLORS = ['#28A745', '#FFC107', '#DC3545'];

// ---------------------------------------------------------------------------
// 7-Day Rainfall Trend
// ---------------------------------------------------------------------------

export const RainfallTrend = memo(function RainfallTrend({
  className,
}: {
  className?: string;
}) {
  const sevenDaysAgo = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().split('T')[0];
  }, []);
  const today = useMemo(() => new Date().toISOString().split('T')[0], []);

  const { data: raw, isLoading } = useQuery({
    queryKey: ['weather', 'trend', sevenDaysAgo, today],
    queryFn: () =>
      weatherApi.getData({
        start_date: sevenDaysAgo,
        end_date: today,
        sort_by: 'recorded_at',
        order: 'asc',
        limit: 200,
      }),
    staleTime: 30 * 60 * 1000,
  });

  // Aggregate by day
  const chartData = useMemo(() => {
    if (!raw?.data?.length) return [];
    const byDay = new Map<string, { sum: number; count: number }>();
    for (const w of raw.data) {
      const day = new Date(w.recorded_at).toLocaleDateString('en-PH', {
        month: 'short',
        day: 'numeric',
      });
      const existing = byDay.get(day) ?? { sum: 0, count: 0 };
      existing.sum += w.precipitation;
      existing.count += 1;
      byDay.set(day, existing);
    }
    return Array.from(byDay.entries()).map(([day, { sum }]) => ({
      day,
      precipitation: +sum.toFixed(1),
    }));
  }, [raw]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">7-Day Rainfall Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-52 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <CloudRain className="h-4 w-4" />
          7-Day Rainfall Trend
        </CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <defs>
                <linearGradient id="rainGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1E3A5F" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1E3A5F" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} unit=" mm" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '0.5rem',
                  fontSize: 12,
                }}
              />
              <Area
                type="monotone"
                dataKey="precipitation"
                stroke="#1E3A5F"
                fill="url(#rainGradient)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-muted-foreground py-10 text-center">
            No rainfall data available for the past 7 days
          </p>
        )}
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Risk Distribution Pie Chart (based on barangay static + live risk)
// ---------------------------------------------------------------------------

export const RiskDistribution = memo(function RiskDistribution({
  className,
}: {
  className?: string;
}) {
  const data = useMemo(() => {
    let low = 0;
    let moderate = 0;
    let high = 0;
    for (const b of BARANGAYS) {
      if (b.floodRisk === 'low') low++;
      else if (b.floodRisk === 'moderate') moderate++;
      else high++;
    }
    return [
      { name: 'Low', value: low },
      { name: 'Moderate', value: moderate },
      { name: 'High', value: high },
    ];
  }, []);

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <PieIcon className="h-4 w-4" />
          Barangay Risk Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              dataKey="value"
              label={({ name, value }) => `${name} (${value})`}
              labelLine={false}
            >
              {data.map((_, idx) => (
                <Cell key={idx} fill={RISK_PIE_COLORS[idx]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
                fontSize: 12,
              }}
            />
            <Legend
              verticalAlign="bottom"
              height={30}
              formatter={(value: string) => (
                <span className="text-xs text-muted-foreground">{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Alert Frequency Bar Chart (placeholder — uses dashboard stats)
// ---------------------------------------------------------------------------

export const AlertFrequency = memo(function AlertFrequency({
  className,
}: {
  className?: string;
}) {
  // Generate mock week data based on current alerts count
  const { data: raw, isLoading } = useQuery({
    queryKey: ['weather', 'week-stats'],
    queryFn: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 7);
      return weatherApi.getData({
        start_date: start.toISOString().split('T')[0],
        end_date: end.toISOString().split('T')[0],
        sort_by: 'recorded_at',
        order: 'asc',
        limit: 200,
      });
    },
    staleTime: 30 * 60 * 1000,
  });

  const chartData = useMemo(() => {
    if (!raw?.data?.length) return [];
    const byDay = new Map<string, number>();
    for (const w of raw.data) {
      const day = new Date(w.recorded_at).toLocaleDateString('en-PH', {
        weekday: 'short',
      });
      // Count readings above alert threshold (>= 2.5mm precip) as "alert events"
      if (w.precipitation >= 2.5) {
        byDay.set(day, (byDay.get(day) ?? 0) + 1);
      }
    }
    return Array.from(byDay.entries()).map(([day, count]) => ({
      day,
      alerts: count,
    }));
  }, [raw]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Alert Events This Week</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-52 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Alert Events This Week
        </CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '0.5rem',
                  fontSize: 12,
                }}
              />
              <Bar dataKey="alerts" fill="#DC3545" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-muted-foreground py-10 text-center">
            No alert-level events recorded this week
          </p>
        )}
      </CardContent>
    </Card>
  );
});
