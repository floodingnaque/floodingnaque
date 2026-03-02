/**
 * ModelManagement Component (P2 — HIGH VALUE)
 *
 * Model version comparison table and feature importance chart
 * for the Admin dashboard. Data sourced from paranaque.ts constants.
 */

import { memo, useMemo } from 'react';
import { Cpu, TrendingUp, Award, Database, Layers } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { MODEL_VERSIONS } from '@/config/paranaque';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Model Version Comparison Table
// ---------------------------------------------------------------------------

export const ModelVersionTable = memo(function ModelVersionTable({
  className,
}: {
  className?: string;
}) {
  const latest = MODEL_VERSIONS[MODEL_VERSIONS.length - 1];

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
              Random Forest classifier progression from v1 → {latest.version}
            </CardDescription>
          </div>
          <Badge className="bg-primary text-primary-foreground">
            Active: {latest.version}
          </Badge>
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
              {MODEL_VERSIONS.map((m) => {
                const isLatest = m.version === latest.version;
                return (
                  <TableRow
                    key={m.version}
                    className={cn(isLatest && 'bg-primary/5 font-medium')}
                  >
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        {m.version}
                        {isLatest && (
                          <Badge variant="secondary" className="text-[9px] px-1 py-0">
                            live
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(m.accuracy * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(m.precision * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(m.recall * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(m.f1 * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right">
                      {m.samples.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">{m.features}</TableCell>
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
  const chartData = useMemo(
    () =>
      MODEL_VERSIONS.map((m) => ({
        version: m.version,
        accuracy: +(m.accuracy * 100).toFixed(2),
        f1: +(m.f1 * 100).toFixed(2),
      })),
    [],
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
          <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="version" tick={{ fontSize: 11 }} />
            <YAxis
              tick={{ fontSize: 11 }}
              domain={[80, 100]}
              unit="%"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
                fontSize: 12,
              }}
              formatter={(v) => [`${v}%`]}
            />
            <Legend verticalAlign="bottom" height={30} />
            <Bar dataKey="accuracy" fill="#1E3A5F" radius={[4, 4, 0, 0]} name="Accuracy" />
            <Bar dataKey="f1" fill="#28A745" radius={[4, 4, 0, 0]} name="F1 Score" />
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
  const latest = MODEL_VERSIONS[MODEL_VERSIONS.length - 1];

  const cards = [
    {
      icon: Award,
      label: 'Accuracy',
      value: `${(latest.accuracy * 100).toFixed(2)}%`,
      color: 'text-risk-safe',
    },
    {
      icon: TrendingUp,
      label: 'F1 Score',
      value: `${(latest.f1 * 100).toFixed(2)}%`,
      color: 'text-primary',
    },
    {
      icon: Database,
      label: 'Training Samples',
      value: latest.samples.toLocaleString(),
      color: 'text-muted-foreground',
    },
    {
      icon: Layers,
      label: 'Features',
      value: latest.features.toString(),
      color: 'text-muted-foreground',
    },
  ];

  return (
    <div className={cn('grid gap-4 grid-cols-2 sm:grid-cols-4', className)}>
      {cards.map((c) => (
        <Card key={c.label}>
          <CardContent className="pt-5 pb-4 px-4 flex items-center gap-3">
            <c.icon className={cn('h-5 w-5', c.color)} />
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
