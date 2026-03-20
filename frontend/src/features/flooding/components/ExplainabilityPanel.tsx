/**
 * ExplainabilityPanel — XAI Visualization
 *
 * Renders Explainable AI output for a single prediction:
 *  1. Why-Alert summary — natural language explanation + factor badges
 *  2. Feature Importance — horizontal bar chart (global model importances)
 *  3. Prediction Contributions — waterfall chart (per-prediction SHAP-like values)
 *
 * Design: glassmorphism cards, risk-level colour theming, Recharts 3, Tailwind v4.
 */

import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  BarChart3,
  Brain,
  CheckCircle,
  FlaskConical,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { GlassCard } from "@/components/ui/glass-card";
import { Separator } from "@/components/ui/separator";
import { RISK_HEX } from "@/lib/colors";
import { cn } from "@/lib/utils";
import type {
  FeatureImportance,
  PredictionContribution,
  RiskLevel,
  WhyAlertFactor,
  XAIExplanation,
} from "@/types";

// ---------------------------------------------------------------------------
// Risk-level palettes (Tailwind v4)
// ---------------------------------------------------------------------------

const ACCENT_GRADIENT: Record<RiskLevel, string> = {
  0: "bg-linear-to-r from-emerald-500 to-teal-400",
  1: "bg-linear-to-r from-amber-500 to-orange-400",
  2: "bg-linear-to-r from-red-500 to-rose-400",
};

const ICON_BOX: Record<RiskLevel, string> = {
  0: "bg-linear-to-br from-emerald-500/20 to-teal-500/20 ring-risk-safe/30 text-risk-safe",
  1: "bg-linear-to-br from-amber-500/20 to-orange-500/20 ring-risk-alert/30 text-risk-alert",
  2: "bg-linear-to-br from-red-500/20 to-rose-500/20 ring-risk-critical/30 text-risk-critical",
};

const SEVERITY_STYLE: Record<string, string> = {
  high: "border-risk-critical/40 bg-risk-critical/15 text-risk-critical",
  medium: "border-risk-alert/40 bg-risk-alert/15 text-risk-alert",
  low: "border-slate-500/40 bg-slate-500/15 text-slate-300",
};

const SEVERITY_ICON: Record<string, React.ReactNode> = {
  high: <XCircle className="h-3.5 w-3.5 shrink-0 text-risk-critical" />,
  medium: <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-risk-alert" />,
  low: <CheckCircle className="h-3.5 w-3.5 shrink-0 text-slate-400" />,
};

const BAR_COLORS: Record<RiskLevel, { positive: string; negative: string }> = {
  0: { positive: RISK_HEX.safe, negative: "#6ee7b7" },
  1: { positive: RISK_HEX.alert, negative: "#fcd34d" },
  2: { positive: RISK_HEX.critical, negative: "#fca5a5" },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function WhyAlertCard({
  summary,
  factors,
  riskLevel,
}: {
  summary: string;
  factors: WhyAlertFactor[];
  riskLevel: RiskLevel;
}) {
  const RiskIcon =
    riskLevel === 2
      ? ShieldAlert
      : riskLevel === 1
        ? AlertTriangle
        : CheckCircle;

  return (
    <GlassCard intensity="heavy" className="relative overflow-hidden">
      <div
        className={`absolute inset-x-0 top-0 h-1 ${ACCENT_GRADIENT[riskLevel]}`}
      />

      <div className="p-6 space-y-4">
        {/* Section header */}
        <div className="flex items-start gap-4">
          <div
            className={cn(
              "shrink-0 flex items-center justify-center h-11 w-11 rounded-xl ring-1",
              ICON_BOX[riskLevel],
            )}
          >
            <Brain className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h3 className="text-lg font-semibold tracking-tight">
              Why This Classification?
            </h3>
            <p className="text-sm text-muted-foreground">
              AI-generated explanation of the risk assessment
            </p>
          </div>
        </div>

        <Separator className="opacity-40" />

        {/* Natural-language summary */}
        <div className="flex items-start gap-3 p-4 rounded-xl bg-muted/30">
          <RiskIcon className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
          <p className="text-sm leading-relaxed">{summary}</p>
        </div>

        {/* Factor badges */}
        {factors.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium tracking-wider uppercase text-muted-foreground">
              Contributing Factors
            </p>
            <div className="flex flex-wrap gap-2">
              {factors.map((f, i) => (
                <span
                  key={i}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
                    SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.low,
                  )}
                >
                  {SEVERITY_ICON[f.severity] ?? SEVERITY_ICON.low}
                  {f.text}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </GlassCard>
  );
}

// ---------------------------------------------------------------------------
// Custom Recharts Tooltip
// ---------------------------------------------------------------------------

interface TooltipPayloadItem {
  value: number;
  payload: { label: string; importance?: number; contribution?: number };
}

function ImportanceTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0]!;
  return (
    <div className="px-3 py-2 text-xs border rounded-lg shadow-lg border-border/40 bg-card/90 backdrop-blur-md">
      <p className="font-medium">{d.payload.label}</p>
      <p className="text-muted-foreground">
        Importance: <strong>{(d.value * 100).toFixed(1)}%</strong>
      </p>
    </div>
  );
}

function ContributionTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0]!;
  const val = d.value;
  const direction = val > 0 ? "Increases risk" : "Decreases risk";
  return (
    <div className="px-3 py-2 text-xs border rounded-lg shadow-lg border-border/40 bg-card/90 backdrop-blur-md">
      <p className="font-medium">{d.payload.label}</p>
      <p className="text-muted-foreground">
        {direction}: <strong>{(Math.abs(val) * 100).toFixed(1)}%</strong>
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Feature Importance Chart
// ---------------------------------------------------------------------------

function FeatureImportanceChart({
  data,
  riskLevel,
}: {
  data: FeatureImportance[];
  riskLevel: RiskLevel;
}) {
  // Take top 10
  const chartData = useMemo(
    () => data.slice(0, 10).map((d) => ({ ...d, value: d.importance })),
    [data],
  );

  if (!chartData.length) return null;
  const barColor = BAR_COLORS[riskLevel].positive;

  return (
    <GlassCard intensity="heavy" className="relative overflow-hidden">
      <div
        className={`absolute inset-x-0 top-0 h-1 ${ACCENT_GRADIENT[riskLevel]}`}
      />

      <div className="p-6 space-y-4">
        <div className="flex items-start gap-4">
          <div
            className={cn(
              "shrink-0 flex items-center justify-center h-11 w-11 rounded-xl ring-1",
              ICON_BOX[riskLevel],
            )}
          >
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold tracking-tight">
              Feature Importance
            </h3>
            <p className="text-sm text-muted-foreground">
              How much each feature influences the model overall
            </p>
          </div>
        </div>

        <Separator className="opacity-40" />

        <div className="w-full h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 4, right: 24, bottom: 4, left: 4 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                opacity={0.2}
                horizontal={false}
              />
              <XAxis
                type="number"
                domain={[0, "auto"]}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                axisLine={{ stroke: "hsl(var(--border))", opacity: 0.3 }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={140}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                content={<ImportanceTooltip />}
                cursor={{ fill: "hsl(var(--muted))", opacity: 0.15 }}
              />
              <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={18}>
                {chartData.map((_entry, idx) => (
                  <Cell
                    key={idx}
                    fill={barColor}
                    fillOpacity={1 - idx * 0.06}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </GlassCard>
  );
}

// ---------------------------------------------------------------------------
// Prediction Contributions Waterfall Chart
// ---------------------------------------------------------------------------

function ContributionChart({
  data,
  riskLevel,
}: {
  data: PredictionContribution[];
  riskLevel: RiskLevel;
}) {
  const chartData = useMemo(
    () =>
      data.slice(0, 10).map((d) => ({
        ...d,
        value: d.contribution,
      })),
    [data],
  );

  if (!chartData.length) return null;

  const { positive: posColor, negative: negColor } = BAR_COLORS[riskLevel];

  return (
    <GlassCard intensity="heavy" className="relative overflow-hidden">
      <div
        className={`absolute inset-x-0 top-0 h-1 ${ACCENT_GRADIENT[riskLevel]}`}
      />

      <div className="p-6 space-y-4">
        <div className="flex items-start gap-4">
          <div
            className={cn(
              "shrink-0 flex items-center justify-center h-11 w-11 rounded-xl ring-1",
              ICON_BOX[riskLevel],
            )}
          >
            <FlaskConical className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold tracking-tight">
              Prediction Contributions
            </h3>
            <p className="text-sm text-muted-foreground">
              How each feature pushed the risk score for this specific
              prediction
            </p>
          </div>
        </div>

        <Separator className="opacity-40" />

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <ArrowUp className="h-3.5 w-3.5" style={{ color: posColor }} />
            Increases risk
          </span>
          <span className="inline-flex items-center gap-1">
            <ArrowDown className="h-3.5 w-3.5" style={{ color: negColor }} />
            Decreases risk
          </span>
        </div>

        <div className="w-full h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 4, right: 24, bottom: 4, left: 4 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                opacity={0.2}
                horizontal={false}
              />
              <XAxis
                type="number"
                tickFormatter={(v: number) =>
                  `${v > 0 ? "+" : ""}${(v * 100).toFixed(0)}%`
                }
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                axisLine={{ stroke: "hsl(var(--border))", opacity: 0.3 }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={140}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                content={<ContributionTooltip />}
                cursor={{ fill: "hsl(var(--muted))", opacity: 0.15 }}
              />
              <ReferenceLine
                x={0}
                stroke="hsl(var(--border))"
                strokeOpacity={0.5}
              />
              <Bar dataKey="value" radius={[6, 6, 6, 6]} barSize={18}>
                {chartData.map((entry, idx) => (
                  <Cell
                    key={idx}
                    fill={entry.value > 0 ? posColor : negColor}
                    fillOpacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </GlassCard>
  );
}

// ---------------------------------------------------------------------------
// Smart Alert Contributing Factors (from backend smart_alert)
// ---------------------------------------------------------------------------

function SmartAlertFactors({
  factors,
  riskLevel,
}: {
  factors: string[];
  riskLevel: RiskLevel;
}) {
  if (!factors.length) return null;

  return (
    <GlassCard intensity="heavy" className="relative overflow-hidden">
      <div
        className={`absolute inset-x-0 top-0 h-1 ${ACCENT_GRADIENT[riskLevel]}`}
      />

      <div className="p-6 space-y-4">
        <div className="flex items-start gap-4">
          <div
            className={cn(
              "shrink-0 flex items-center justify-center h-11 w-11 rounded-xl ring-1",
              ICON_BOX[riskLevel],
            )}
          >
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold tracking-tight">
              Smart Alert Factors
            </h3>
            <p className="text-sm text-muted-foreground">
              Weather conditions detected by the alert evaluation engine
            </p>
          </div>
        </div>

        <Separator className="opacity-40" />

        <ul className="space-y-2">
          {factors.map((factor, i) => (
            <li
              key={i}
              className="flex items-center gap-3 rounded-lg bg-muted/20 px-4 py-2.5 text-sm"
            >
              <Sparkles className="w-4 h-4 shrink-0 text-muted-foreground" />
              {factor}
            </li>
          ))}
        </ul>
      </div>
    </GlassCard>
  );
}

// ---------------------------------------------------------------------------
// Public ExplainabilityPanel
// ---------------------------------------------------------------------------

export interface ExplainabilityPanelProps {
  explanation?: XAIExplanation | null;
  riskLevel: RiskLevel;
  smartAlertFactors?: string[];
}

export function ExplainabilityPanel({
  explanation,
  riskLevel,
  smartAlertFactors,
}: ExplainabilityPanelProps) {
  if (!explanation && !smartAlertFactors?.length) return null;

  return (
    <div className="space-y-6">
      {/* 1. Why-alert natural-language explanation */}
      {explanation?.why_alert && (
        <WhyAlertCard
          summary={explanation.why_alert.summary}
          factors={explanation.why_alert.factors}
          riskLevel={riskLevel}
        />
      )}

      {/* 2. Per-prediction contributions (SHAP-like waterfall) */}
      {explanation?.prediction_contributions &&
        explanation.prediction_contributions.length > 0 && (
          <ContributionChart
            data={explanation.prediction_contributions}
            riskLevel={riskLevel}
          />
        )}

      {/* 3. Global feature importance */}
      {explanation?.global_feature_importances &&
        explanation.global_feature_importances.length > 0 && (
          <FeatureImportanceChart
            data={explanation.global_feature_importances}
            riskLevel={riskLevel}
          />
        )}

      {/* 4. Smart alert contributing factors */}
      {smartAlertFactors && smartAlertFactors.length > 0 && (
        <SmartAlertFactors factors={smartAlertFactors} riskLevel={riskLevel} />
      )}
    </div>
  );
}

export default ExplainabilityPanel;
