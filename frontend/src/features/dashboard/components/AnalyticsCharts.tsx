/**
 * AnalyticsCharts Component (P2 - HIGH VALUE)
 *
 * Collection of Recharts visualizations for the Analytics page:
 * - 7-day rainfall trend (area chart)
 * - Risk distribution pie chart (from live prediction stats)
 * - Alert frequency bar chart (from alerts API)
 *
 * Data-driven from /api/data/weather, /api/v1/predictions/stats,
 * and /api/v1/alerts.
 */

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { API_ENDPOINTS } from "@/config/api.config";
import { alertsApi } from "@/features/alerts/services/alertsApi";
import { weatherApi } from "@/features/weather/services/weatherApi";
import api from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";
import { format, subDays } from "date-fns";
import {
  AlertTriangle,
  BarChart3,
  CloudRain,
  PieChart as PieIcon,
  RefreshCw,
} from "lucide-react";
import { memo, useMemo } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PRIMARY_HEX, RISK_HEX } from "@/lib/colors";

// ---------------------------------------------------------------------------
// Colors
// ---------------------------------------------------------------------------

const RISK_PIE_COLORS = [RISK_HEX.safe, RISK_HEX.alert, RISK_HEX.critical];

const AREA_MARGIN = { top: 5, right: 10, bottom: 5, left: -10 } as const;
const BAR_MARGIN = { top: 5, right: 10, bottom: 5, left: -10 } as const;

const TOOLTIP_STYLE = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: 12,
} as const;

// ---------------------------------------------------------------------------
// 7-Day Rainfall Trend
// ---------------------------------------------------------------------------

export const RainfallTrend = memo(function RainfallTrend({
  className,
}: {
  className?: string;
}) {
  const sevenDaysAgo = useMemo(
    () => format(subDays(new Date(), 7), "yyyy-MM-dd"),
    [],
  );
  const today = useMemo(() => format(new Date(), "yyyy-MM-dd"), []);

  const {
    data: raw,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["weather", "trend", sevenDaysAgo, today],
    queryFn: () =>
      weatherApi.getData({
        start_date: sevenDaysAgo,
        end_date: today,
        sort_by: "recorded_at",
        order: "asc",
        limit: 500,
      }),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 60 * 1000,
  });

  // Aggregate by day
  const chartData = useMemo(() => {
    if (!raw?.data?.length) return [];
    const byDay = new Map<string, { sum: number; count: number }>();
    for (const w of raw.data) {
      const day = format(new Date(w.recorded_at), "MMM dd");
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
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <CloudRain className="h-4 w-4" />
            7-Day Rainfall Trend
          </CardTitle>
          {dataUpdatedAt > 0 && (
            <span className="text-[10px] text-muted-foreground">
              Updated {format(new Date(dataUpdatedAt), "h:mm a")}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="flex flex-col items-center py-10 gap-2 text-muted-foreground">
            <AlertTriangle className="h-6 w-6 opacity-50" />
            <p className="text-sm">Failed to load rainfall data</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Retry
            </Button>
          </div>
        ) : chartData.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={AREA_MARGIN}>
              <defs>
                <linearGradient id="rainGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={PRIMARY_HEX} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={PRIMARY_HEX} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} unit=" mm" />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: string | number | undefined) => [
                  `${typeof v === "number" ? v.toFixed(1) : (v ?? "")} mm`,
                  "Precipitation",
                ]}
              />
              <Area
                type="monotone"
                dataKey="precipitation"
                stroke={PRIMARY_HEX}
                fill="url(#rainGradient)"
                strokeWidth={2}
                isAnimationActive={false}
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
// Risk Distribution Pie Chart (from live prediction stats)
// ---------------------------------------------------------------------------

interface PredictionStatsResponse {
  stats: {
    risk_distribution: Record<string, number>;
    total_predictions: number;
  };
}

export const RiskDistribution = memo(function RiskDistribution({
  className,
}: {
  className?: string;
}) {
  const {
    data: statsResp,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["predictions", "stats", "risk-dist"],
    queryFn: () =>
      api.get<PredictionStatsResponse>(
        `${API_ENDPOINTS.predictions.stats}?days=30`,
      ),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 60 * 1000,
  });

  const data = useMemo(() => {
    const dist = statsResp?.stats?.risk_distribution;
    if (!dist) return [];
    // Backend risk_distribution keys: "safe", "alert", "critical"
    return [
      { name: "Low", value: dist["safe"] ?? dist["0"] ?? dist["low"] ?? 0 },
      {
        name: "Moderate",
        value: dist["alert"] ?? dist["1"] ?? dist["moderate"] ?? 0,
      },
      {
        name: "High",
        value: dist["critical"] ?? dist["2"] ?? dist["high"] ?? 0,
      },
    ];
  }, [statsResp]);

  const totalPredictions = data.reduce((sum, d) => sum + d.value, 0);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Risk Distribution</CardTitle>
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
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <PieIcon className="h-4 w-4" />
            Risk Distribution (30 days)
          </CardTitle>
          {dataUpdatedAt > 0 && (
            <span className="text-[10px] text-muted-foreground">
              Updated {format(new Date(dataUpdatedAt), "h:mm a")}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="flex flex-col items-center py-10 gap-2 text-muted-foreground">
            <AlertTriangle className="h-6 w-6 opacity-50" />
            <p className="text-sm">Failed to load risk data</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Retry
            </Button>
          </div>
        ) : totalPredictions > 0 ? (
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
                isAnimationActive={false}
              >
                {data.map((_, idx) => (
                  <Cell key={idx} fill={RISK_PIE_COLORS[idx]} />
                ))}
              </Pie>
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend
                verticalAlign="bottom"
                height={30}
                formatter={(value: string) => (
                  <span className="text-xs text-muted-foreground">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-muted-foreground py-10 text-center">
            No prediction data available for the past 30 days
          </p>
        )}
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Alert Frequency Bar Chart (from alerts API)
// ---------------------------------------------------------------------------

export const AlertFrequency = memo(function AlertFrequency({
  className,
}: {
  className?: string;
}) {
  const weekStart = useMemo(
    () => format(subDays(new Date(), 7), "yyyy-MM-dd"),
    [],
  );
  const todayStr = useMemo(() => format(new Date(), "yyyy-MM-dd"), []);

  const {
    data: raw,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["alerts", "week-frequency", weekStart, todayStr],
    queryFn: () =>
      alertsApi.getAlerts({
        start_date: weekStart,
        end_date: todayStr,
        limit: 500,
        sort_by: "created_at",
        order: "asc",
      }),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 60 * 1000,
  });

  const chartData = useMemo(() => {
    const alerts = raw?.data;
    if (!alerts?.length) return [];
    const byDay = new Map<string, number>();
    for (const a of alerts) {
      const day = format(new Date(a.created_at), "EEE");
      byDay.set(day, (byDay.get(day) ?? 0) + 1);
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
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Alert Events This Week
          </CardTitle>
          {dataUpdatedAt > 0 && (
            <span className="text-[10px] text-muted-foreground">
              Updated {format(new Date(dataUpdatedAt), "h:mm a")}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="flex flex-col items-center py-10 gap-2 text-muted-foreground">
            <AlertTriangle className="h-6 w-6 opacity-50" />
            <p className="text-sm">Failed to load alert data</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Retry
            </Button>
          </div>
        ) : chartData.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={BAR_MARGIN}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar
                dataKey="alerts"
                fill={RISK_HEX.critical}
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-muted-foreground py-10 text-center">
            No alert events recorded this week
          </p>
        )}
      </CardContent>
    </Card>
  );
});
