/**
 * ModelManagement Component (P2 - HIGH VALUE)
 *
 * Model version comparison table and feature importance chart
 * for the Admin dashboard. Data sourced from paranaque.ts constants.
 */

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import {
  Award,
  Cpu,
  Database,
  Layers,
  Loader2,
  TrendingUp,
} from "lucide-react";
import { memo, useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useModelHistory } from "../hooks/useAnalytics";

// ---------------------------------------------------------------------------
// Model Version Comparison Table
// ---------------------------------------------------------------------------

export const ModelVersionTable = memo(function ModelVersionTable({
  className,
}: {
  className?: string;
}) {
  const { data, isLoading } = useModelHistory();
  const models = useMemo(() => data?.models ?? [], [data?.models]);
  const latest = models.find((m) => m.is_active) ?? models[models.length - 1];

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="py-10 flex items-center justify-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading model history…
        </CardContent>
      </Card>
    );
  }

  if (!models.length) {
    return (
      <Card className={className}>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          No model version data available.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Model Version History
            </CardTitle>
            <CardDescription className="mt-1">
              Random Forest classifier progression from v1 → v{latest?.version}
            </CardDescription>
          </div>
          {latest && (
            <Badge className="bg-primary text-primary-foreground">
              Active: v{latest.version}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">Version</TableHead>
                <TableHead className="text-right">Accuracy</TableHead>
                <TableHead className="text-right">Precision</TableHead>
                <TableHead className="text-right">Recall</TableHead>
                <TableHead className="text-right">F1</TableHead>
                <TableHead className="text-right">Samples</TableHead>
                <TableHead className="text-right">Features</TableHead>
                <TableHead className="hidden md:table-cell">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {models.map((m) => {
                const isActive = m.is_active;
                return (
                  <TableRow
                    key={m.version}
                    className={cn(isActive && "bg-primary/5 font-medium")}
                  >
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        v{m.version}
                        {isActive && (
                          <Badge
                            variant="secondary"
                            className="text-[9px] px-1 py-0"
                          >
                            live
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(m.metrics.accuracy * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(m.metrics.precision * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(m.metrics.recall * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(m.metrics.f1_score * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right">
                      {m.training_data.total_records.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {m.training_data.num_features}
                    </TableCell>
                    <TableCell className="hidden md:table-cell text-xs text-muted-foreground max-w-50 truncate">
                      {m.description}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Accuracy Progression Chart
// ---------------------------------------------------------------------------

export const AccuracyProgressionChart = memo(function AccuracyProgressionChart({
  className,
}: {
  className?: string;
}) {
  const { data, isLoading } = useModelHistory();
  const models = useMemo(() => data?.models ?? [], [data?.models]);

  const chartData = useMemo(
    () =>
      models.map((m) => ({
        version: `v${m.version}`,
        accuracy: +(m.metrics.accuracy * 100).toFixed(2),
        f1: +(m.metrics.f1_score * 100).toFixed(2),
      })),
    [models],
  );

  if (isLoading || !chartData.length) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Accuracy Progression
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-55 text-sm text-muted-foreground">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "No data available"
          )}
        </CardContent>
      </Card>
    );
  }

  const minVal = Math.max(
    0,
    Math.min(...chartData.map((d) => Math.min(d.accuracy, d.f1))) - 10,
  );

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          Accuracy Progression
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={chartData}
            margin={{ top: 5, right: 10, bottom: 5, left: -10 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="version" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} domain={[minVal, 100]} unit="%" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.5rem",
                fontSize: 12,
              }}
              formatter={(v) => [`${v}%`]}
            />
            <Legend verticalAlign="bottom" height={30} />
            <Bar
              dataKey="accuracy"
              fill="hsl(var(--primary))"
              radius={[4, 4, 0, 0]}
              name="Accuracy"
            />
            <Bar
              dataKey="f1"
              fill="hsl(var(--risk-safe))"
              radius={[4, 4, 0, 0]}
              name="F1 Score"
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Model Summary Cards
// ---------------------------------------------------------------------------

export const ModelSummaryCards = memo(function ModelSummaryCards({
  className,
}: {
  className?: string;
}) {
  const { data, isLoading } = useModelHistory();
  const models = useMemo(() => data?.models ?? [], [data?.models]);
  const latest = models.find((m) => m.is_active) ?? models[models.length - 1];

  if (isLoading || !latest) {
    return (
      <div className={cn("grid gap-4 grid-cols-2 sm:grid-cols-4", className)}>
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="pt-5 pb-4 px-4">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const cards = [
    {
      icon: Award,
      label: "Accuracy",
      value: `${(latest.metrics.accuracy * 100).toFixed(2)}%`,
      color: "text-risk-safe",
    },
    {
      icon: TrendingUp,
      label: "F1 Score",
      value: `${(latest.metrics.f1_score * 100).toFixed(2)}%`,
      color: "text-primary",
    },
    {
      icon: Database,
      label: "Training Samples",
      value: latest.training_data.total_records.toLocaleString(),
      color: "text-muted-foreground",
    },
    {
      icon: Layers,
      label: "Features",
      value: latest.training_data.num_features.toString(),
      color: "text-muted-foreground",
    },
  ];

  return (
    <div className={cn("grid gap-4 grid-cols-2 sm:grid-cols-4", className)}>
      {cards.map((c) => (
        <Card key={c.label}>
          <CardContent className="pt-5 pb-4 px-4 flex items-center gap-3">
            <c.icon className={cn("h-5 w-5", c.color)} />
            <div>
              <p className="text-xs text-muted-foreground">{c.label}</p>
              <p className="text-lg font-bold">{c.value}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
});
