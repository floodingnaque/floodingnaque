/**
 * SimulationPanel – What-if flood prediction interface.
 *
 * Range sliders for weather parameters, preset scenarios, debounced API calls,
 * and explainability output. Predictions are ephemeral (not stored in DB).
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import {
  AlertTriangle,
  Cloud,
  Droplets,
  Gauge,
  ShieldCheck,
  Thermometer,
  Wind,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSimulation } from "../hooks/useSimulation";
import type { SimulationParams, SimulationResult } from "../types";

// ── Defaults & Presets ──────────────────────────────────────────────────

const DEFAULTS: SimulationParams = {
  temperature: 301,
  humidity: 75,
  precipitation: 10,
  wind_speed: 3,
  pressure: 1010,
};

const PRESETS: Record<
  string,
  { label: string; params: Partial<SimulationParams> }
> = {
  normal: {
    label: "Normal Day",
    params: {
      temperature: 303,
      humidity: 70,
      precipitation: 5,
      wind_speed: 2,
      pressure: 1013,
    },
  },
  heavy_monsoon: {
    label: "Heavy Monsoon",
    params: {
      temperature: 299,
      humidity: 92,
      precipitation: 45,
      wind_speed: 8,
      pressure: 1005,
    },
  },
  typhoon: {
    label: "Typhoon",
    params: {
      temperature: 297,
      humidity: 95,
      precipitation: 80,
      wind_speed: 25,
      pressure: 980,
    },
  },
  high_tide_rain: {
    label: "High Tide + Rain",
    params: {
      temperature: 301,
      humidity: 85,
      precipitation: 30,
      wind_speed: 5,
      pressure: 1008,
    },
  },
};

const PARAM_CONFIG = [
  {
    key: "temperature" as const,
    label: "Temperature",
    unit: "K",
    min: 290,
    max: 315,
    step: 0.5,
    icon: Thermometer,
  },
  {
    key: "humidity" as const,
    label: "Humidity",
    unit: "%",
    min: 0,
    max: 100,
    step: 1,
    icon: Droplets,
  },
  {
    key: "precipitation" as const,
    label: "Precipitation",
    unit: "mm",
    min: 0,
    max: 150,
    step: 1,
    icon: Cloud,
  },
  {
    key: "wind_speed" as const,
    label: "Wind Speed",
    unit: "m/s",
    min: 0,
    max: 50,
    step: 0.5,
    icon: Wind,
  },
  {
    key: "pressure" as const,
    label: "Pressure",
    unit: "hPa",
    min: 950,
    max: 1050,
    step: 1,
    icon: Gauge,
  },
] as const;

const RISK_COLORS: Record<string, string> = {
  Safe: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  Alert: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  Critical: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
};

// ── Component ───────────────────────────────────────────────────────────

export function SimulationPanel() {
  const [params, setParams] = useState<SimulationParams>({ ...DEFAULTS });
  const [selectedPreset, setSelectedPreset] = useState<string>("custom");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const simulation = useSimulation();

  // Debounced auto-simulate on param change
  const runSimulation = useCallback(
    (p: SimulationParams) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        simulation.mutate(p);
      }, 400);
    },
    [simulation],
  );

  useEffect(() => {
    runSimulation(params);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [params]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePresetChange = (value: string) => {
    setSelectedPreset(value);
    if (value !== "custom" && PRESETS[value]) {
      setParams((prev) => ({
        ...prev,
        ...PRESETS[value].params,
        scenario: value as SimulationParams["scenario"],
      }));
    }
  };

  const handleParamChange = (key: keyof SimulationParams, value: number) => {
    setSelectedPreset("custom");
    setParams((prev) => ({ ...prev, [key]: value, scenario: undefined }));
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Left: Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cloud className="h-5 w-5" />
            Scenario Controls
          </CardTitle>
          <CardDescription>
            Adjust weather parameters or select a preset to see predicted flood
            risk in real time.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Preset selector */}
          <div>
            <span className="text-sm font-medium mb-2 block">
              Preset Scenario
            </span>
            <Select value={selectedPreset} onValueChange={handlePresetChange}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a scenario…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="custom">Custom</SelectItem>
                {Object.entries(PRESETS).map(([key, { label }]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Parameter sliders */}
          {PARAM_CONFIG.map(
            ({ key, label, unit, min, max, step, icon: Icon }) => (
              <div key={key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium flex items-center gap-1.5">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    {label}
                  </label>
                  <span className="text-sm font-mono tabular-nums">
                    {params[key] ?? 0} {unit}
                  </span>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={params[key] ?? 0}
                  onChange={(e) =>
                    handleParamChange(key, parseFloat(e.target.value))
                  }
                  className="w-full accent-primary h-2 rounded-lg cursor-pointer"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>
                    {min}
                    {unit}
                  </span>
                  <span>
                    {max}
                    {unit}
                  </span>
                </div>
              </div>
            ),
          )}
        </CardContent>
      </Card>

      {/* Right: Results */}
      <div className="space-y-6">
        <SimulationResultCard
          result={simulation.data}
          isPending={simulation.isPending}
        />
        {simulation.data?.explanation && (
          <ExplanationCard explanation={simulation.data.explanation} />
        )}
        {simulation.error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive text-sm">
                {simulation.error.message}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// ── Result Card ─────────────────────────────────────────────────────────

function SimulationResultCard({
  result,
  isPending,
}: {
  result?: SimulationResult;
  isPending: boolean;
}) {
  if (isPending && !result) {
    return <SimulationPanelSkeleton />;
  }

  if (!result) {
    return (
      <Card>
        <CardContent className="pt-6 text-center text-muted-foreground">
          <p>Adjust parameters to see prediction results.</p>
        </CardContent>
      </Card>
    );
  }

  const riskColor = RISK_COLORS[result.risk_label] ?? "";

  return (
    <Card className={cn(isPending && "opacity-60 transition-opacity")}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Prediction Result</span>
          <Badge variant="outline" className={cn("text-sm", riskColor)}>
            {result.risk_label === "Safe" && (
              <ShieldCheck className="mr-1 h-3.5 w-3.5" />
            )}
            {result.risk_label === "Alert" && (
              <AlertTriangle className="mr-1 h-3.5 w-3.5" />
            )}
            {result.risk_label === "Critical" && (
              <AlertTriangle className="mr-1 h-3.5 w-3.5" />
            )}
            {result.risk_label}
          </Badge>
        </CardTitle>
        <CardDescription>
          Scenario: {result.scenario} | Model: {result.model_version}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Stat
            label="Flood Probability"
            value={`${(result.probability * 100).toFixed(1)}%`}
          />
          <Stat
            label="Confidence"
            value={`${(result.confidence * 100).toFixed(1)}%`}
          />
          <Stat label="Risk Level" value={String(result.risk_level)} />
          <Stat
            label="Features Used"
            value={String(result.features_used?.length ?? 0)}
          />
        </div>

        {/* Probability bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Flood Probability</span>
            <span>{(result.probability * 100).toFixed(1)}%</span>
          </div>
          <div className="h-3 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                result.probability < 0.3
                  ? "bg-emerald-500"
                  : result.probability < 0.6
                    ? "bg-amber-500"
                    : "bg-red-500",
              )}
              style={{ width: `${Math.min(result.probability * 100, 100)}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

// ── Explanation Card ────────────────────────────────────────────────────

function ExplanationCard({
  explanation,
}: {
  explanation: NonNullable<SimulationResult["explanation"]>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Why This Risk Level?</CardTitle>
        <CardDescription>{explanation.why_alert.summary}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Contributing factors */}
        {explanation.why_alert.factors.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Key Factors</h4>
            <ul className="space-y-1.5">
              {explanation.why_alert.factors.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <Badge
                    variant="outline"
                    className={cn(
                      "shrink-0 mt-0.5 text-xs",
                      f.severity === "high" &&
                        "border-red-300 text-red-700 dark:text-red-400",
                      f.severity === "medium" &&
                        "border-amber-300 text-amber-700 dark:text-amber-400",
                      f.severity === "low" &&
                        "border-blue-300 text-blue-700 dark:text-blue-400",
                    )}
                  >
                    {f.severity}
                  </Badge>
                  <span>{f.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Top feature contributions */}
        {explanation.prediction_contributions.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Feature Contributions</h4>
            <div className="space-y-1.5">
              {explanation.prediction_contributions.slice(0, 5).map((c) => (
                <div
                  key={c.feature}
                  className="flex items-center gap-2 text-sm"
                >
                  <span className="w-32 truncate text-muted-foreground">
                    {c.label}
                  </span>
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        c.direction === "increases_risk"
                          ? "bg-red-400"
                          : "bg-emerald-400",
                      )}
                      style={{
                        width: `${Math.min(c.abs_contribution * 100, 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs font-mono w-12 text-right">
                    {c.direction === "increases_risk" ? "+" : "-"}
                    {(c.abs_contribution * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Skeleton ────────────────────────────────────────────────────────────

export function SimulationPanelSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-56 mt-1" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i}>
              <Skeleton className="h-3 w-20 mb-1" />
              <Skeleton className="h-6 w-16" />
            </div>
          ))}
        </div>
        <Skeleton className="h-3 w-full rounded-full" />
      </CardContent>
    </Card>
  );
}
