/**
 * Operator — Analytics & Trends Page
 *
 * Workflow metrics, incident frequency chart, and response-time stats
 * powered by the /api/v1/lgu/incidents/analytics endpoint.
 */

import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  FileCheck,
  TrendingUp,
} from "lucide-react";
import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useIncidentAnalytics } from "@/features/operator";
import type { WorkflowAnalytics } from "@/types";

const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function fmtMinutes(val: number | null): string {
  if (val == null) return "—";
  if (val < 60) return `${Math.round(val)}m`;
  return `${(val / 60).toFixed(1)}h`;
}

function pct(val: number | null): string {
  if (val == null) return "—";
  return `${(val * 100).toFixed(1)}%`;
}

export default function OperatorAnalyticsPage() {
  const { data: raw, isLoading } = useIncidentAnalytics();
  const analytics = raw as unknown as WorkflowAnalytics | undefined;

  const chartData = useMemo(() => {
    if (!analytics?.monthly_frequency) return [];
    return analytics.monthly_frequency.map((m) => ({
      name: `${MONTH_LABELS[m.month - 1]} ${m.year}`,
      count: m.count,
    }));
  }, [analytics]);

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 space-y-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-4">
                <Skeleton className="h-10 w-20 mx-auto" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardContent className="pt-6">
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="p-4 sm:p-6">
        <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
          <BarChart3 className="h-12 w-12 mb-3 opacity-30" />
          <p className="text-sm font-medium">No analytics data available</p>
          <p className="text-xs mt-1">
            Analytics will appear once incidents are logged
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center shrink-0">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
            </div>
            <div>
              <p className="text-xl font-bold">{analytics.total_incidents}</p>
              <p className="text-xs text-muted-foreground">Total Incidents</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center shrink-0">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            </div>
            <div>
              <p className="text-xl font-bold">
                {analytics.resolved_incidents}
              </p>
              <p className="text-xs text-muted-foreground">Resolved</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
              <Clock className="h-5 w-5 text-blue-500" />
            </div>
            <div>
              <p className="text-xl font-bold">
                {fmtMinutes(analytics.avg_resolve_minutes)}
              </p>
              <p className="text-xs text-muted-foreground">Avg Resolve Time</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center shrink-0">
              <FileCheck className="h-5 w-5 text-purple-500" />
            </div>
            <div>
              <p className="text-xl font-bold">
                {pct(analytics.aar_completion_rate)}
              </p>
              <p className="text-xs text-muted-foreground">AAR Completion</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Monthly Incident Trend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Incident Trends
          </CardTitle>
          <CardDescription>Monthly flood incidents over time</CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border/50 rounded-lg">
              <BarChart3 className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm font-medium">No monthly data yet</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  className="stroke-border"
                />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar
                  dataKey="count"
                  name="Incidents"
                  fill="hsl(var(--primary))"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Workflow Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Workflow Metrics
          </CardTitle>
          <CardDescription>
            Average pipeline stage durations and quality indicators
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="p-3 border rounded-lg">
              <p className="text-lg font-bold">
                {fmtMinutes(analytics.avg_confirm_minutes)}
              </p>
              <p className="text-xs text-muted-foreground">Avg Confirmation</p>
            </div>
            <div className="p-3 border rounded-lg">
              <p className="text-lg font-bold">
                {fmtMinutes(analytics.avg_broadcast_minutes)}
              </p>
              <p className="text-xs text-muted-foreground">Avg Broadcast</p>
            </div>
            <div className="p-3 border rounded-lg">
              <p className="text-lg font-bold">
                {fmtMinutes(analytics.avg_resolve_minutes)}
              </p>
              <p className="text-xs text-muted-foreground">Avg Resolution</p>
            </div>
            <div className="p-3 border rounded-lg">
              <p className="text-lg font-bold">{analytics.stalled_incidents}</p>
              <p className="text-xs text-muted-foreground">Stalled Incidents</p>
            </div>
            <div className="p-3 border rounded-lg">
              <p className="text-lg font-bold">
                {pct(analytics.false_alarm_rate)}
              </p>
              <p className="text-xs text-muted-foreground">False Alarm Rate</p>
            </div>
            <div className="p-3 border rounded-lg">
              <div className="flex items-center gap-2">
                <p className="text-lg font-bold">{analytics.total_aars}</p>
                <Badge variant="secondary" className="text-[10px]">
                  {analytics.approved_aars} approved
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                After-Action Reports
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
