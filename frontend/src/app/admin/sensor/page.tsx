/**
 * Admin Sensor Data Input Page
 *
 * Manual weather data ingestion with form validation,
 * data source status overview, and recent reading charts.
 * Posts to POST /api/v1/data/data.
 */

import { EmptyState } from "@/components/feedback/EmptyState";
import { PageHeader, SectionHeading } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChartTooltip } from "@/components/ui/chart-tooltip";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PulsingDot } from "@/components/ui/pulsing-dot";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { SensorFormValues } from "@/features/sensor";
import { useRecentReadings, useSensorSubmit } from "@/features/sensor";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { motion, useInView } from "framer-motion";
import {
  Cloud,
  CloudRain,
  Database,
  Droplets,
  Gauge,
  Loader2,
  Radio,
  Satellite,
  Save,
  Thermometer,
  Wind,
} from "lucide-react";
import { useRef, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";

const SOURCES = ["Manual", "PAGASA", "IoT Sensor", "API", "Other"] as const;

const DATA_SOURCES = [
  {
    name: "PAGASA Station (NAIA)",
    icon: CloudRain,
    status: "online" as const,
    lastSync: "30s ago",
  },
  {
    name: "GPM IMERG Satellite",
    icon: Satellite,
    status: "online" as const,
    lastSync: "1m ago",
  },
  {
    name: "EFCOS River Gauge — San Juan",
    icon: Droplets,
    status: "online" as const,
    lastSync: "45s ago",
  },
  {
    name: "IoT Node — Baclaran",
    icon: Radio,
    status: "delayed" as const,
    lastSync: "12m ago",
  },
  {
    name: "OpenWeatherMap API",
    icon: Cloud,
    status: "online" as const,
    lastSync: "5m ago",
  },
  {
    name: "Meteostat Historical",
    icon: Database,
    status: "online" as const,
    lastSync: "10m ago",
  },
];

const STATUS_COLORS: Record<string, string> = {
  online: "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
  delayed: "bg-risk-alert/15 text-risk-alert border-risk-alert/30",
  offline: "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
};

const INITIAL_FORM: SensorFormValues = {
  date: "",
  time: "",
  rainfall: "",
  riverLevel: "",
  temperature: "",
  humidity: "",
  pressure: "",
  windSpeed: "",
  source: "Manual",
};

export default function AdminSensorPage() {
  const [form, setForm] = useState<SensorFormValues>(INITIAL_FORM);
  const submit = useSensorSubmit();
  const { data: hourlyData, isLoading: hourlyLoading } = useRecentReadings(1);

  const F =
    (key: keyof SensorFormValues) => (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  const canSave =
    form.date &&
    form.time &&
    (form.rainfall || form.temperature || form.humidity);

  function handleSubmit() {
    if (!canSave) return;

    const tempC = form.temperature ? parseFloat(form.temperature) : null;
    const tempK = tempC !== null ? tempC + 273.15 : null;

    const payload = {
      ...(tempK !== null && { temperature: tempK }),
      ...(form.humidity && { humidity: parseFloat(form.humidity) }),
      ...(form.rainfall && { precipitation: parseFloat(form.rainfall) }),
      ...(form.windSpeed && { wind_speed: parseFloat(form.windSpeed) }),
      ...(form.pressure && { pressure: parseFloat(form.pressure) }),
      source: form.source,
      timestamp: new Date(`${form.date}T${form.time}`).toISOString(),
    };

    submit.mutate(payload, {
      onSuccess: () => {
        toast.success("Weather observation saved");
        setForm((f) => ({
          ...f,
          rainfall: "",
          riverLevel: "",
          temperature: "",
          humidity: "",
          pressure: "",
          windSpeed: "",
        }));
      },
      onError: () => toast.error("Failed to save observation"),
    });
  }

  // Chart data from hourly readings
  const chartData = (hourlyData?.data ?? []).map((r) => ({
    time: new Date(r.timestamp).toLocaleTimeString("en-PH", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }),
    precipitation: r.precipitation,
    temperature: r.temperature ? +(r.temperature - 273.15).toFixed(1) : null,
  }));

  const formRef = useRef<HTMLDivElement>(null);
  const formInView = useInView(formRef, { once: true, amount: 0.1 });
  const chartsRef = useRef<HTMLDivElement>(null);
  const chartsInView = useInView(chartsRef, { once: true, amount: 0.1 });

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 pt-6">
        <PageHeader
          icon={Radio}
          title="Sensor Data Input"
          subtitle="Manually ingest weather observations or monitor data sources"
        />
      </div>

      {/* Input Form / Data Sources Tabs */}
      <section className="py-10 bg-muted/30">
        <div className="container mx-auto px-4" ref={formRef}>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={formInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <Tabs defaultValue="manual">
                <div className="flex items-center justify-between mb-6">
                  <SectionHeading
                    label="Input"
                    title="Weather Data"
                    subtitle="Submit manual readings or view active data sources"
                  />
                  <TabsList>
                    <TabsTrigger value="manual">Manual Entry</TabsTrigger>
                    <TabsTrigger value="sources">Data Sources</TabsTrigger>
                  </TabsList>
                </div>

                <TabsContent value="manual">
                  <GlassCard className="overflow-hidden">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                    <div className="pt-6 px-6 pb-6">
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                            Date <span className="text-destructive">*</span>
                          </Label>
                          <Input
                            type="date"
                            value={form.date}
                            onChange={F("date")}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                            Time <span className="text-destructive">*</span>
                          </Label>
                          <Input
                            type="time"
                            value={form.time}
                            onChange={F("time")}
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4 mb-4">
                        {[
                          {
                            label: "Rainfall",
                            key: "rainfall" as const,
                            suffix: "mm/hr",
                            icon: CloudRain,
                          },
                          {
                            label: "River Level",
                            key: "riverLevel" as const,
                            suffix: "m",
                            icon: Droplets,
                          },
                          {
                            label: "Temperature",
                            key: "temperature" as const,
                            suffix: "°C",
                            icon: Thermometer,
                          },
                          {
                            label: "Humidity",
                            key: "humidity" as const,
                            suffix: "%",
                            icon: Droplets,
                          },
                          {
                            label: "Pressure",
                            key: "pressure" as const,
                            suffix: "hPa",
                            icon: Gauge,
                          },
                          {
                            label: "Wind Speed",
                            key: "windSpeed" as const,
                            suffix: "m/s",
                            icon: Wind,
                          },
                        ].map(({ label, key, suffix, icon: Icon }) => (
                          <div key={key} className="space-y-2">
                            <Label className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                              <Icon className="h-3 w-3" /> {label}
                            </Label>
                            <div className="relative">
                              <Input
                                type="number"
                                step="any"
                                value={form[key]}
                                onChange={F(key)}
                                placeholder="0"
                                className="pr-14"
                              />
                              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                                {suffix}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                            Source
                          </Label>
                          <Select
                            value={form.source}
                            onValueChange={(v) =>
                              setForm((f) => ({ ...f, source: v }))
                            }
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {SOURCES.map((s) => (
                                <SelectItem key={s} value={s}>
                                  {s}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <Button
                        onClick={handleSubmit}
                        disabled={!canSave || submit.isPending}
                      >
                        {submit.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Save className="h-4 w-4 mr-2" />
                        )}
                        Save Reading
                      </Button>
                    </div>
                  </GlassCard>
                </TabsContent>

                <TabsContent value="sources">
                  <div className="space-y-3">
                    {DATA_SOURCES.map((src) => {
                      const Icon = src.icon;
                      return (
                        <GlassCard
                          key={src.name}
                          className="overflow-hidden hover:shadow-lg transition-all duration-300"
                        >
                          <div className="px-6 py-4 flex items-center gap-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted">
                              <Icon className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <div className="flex-1">
                              <p className="text-sm font-medium">{src.name}</p>
                              <p className="text-xs text-muted-foreground">
                                Last sync: {src.lastSync}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              {src.status === "online" && (
                                <PulsingDot
                                  size="sm"
                                  color="hsl(var(--risk-safe))"
                                />
                              )}
                              <Badge
                                variant="outline"
                                className={cn(
                                  "text-xs capitalize",
                                  STATUS_COLORS[src.status],
                                )}
                              >
                                {src.status}
                              </Badge>
                            </div>
                          </div>
                        </GlassCard>
                      );
                    })}
                  </div>
                </TabsContent>
              </Tabs>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Recent Readings Charts */}
      <section className="py-10 bg-background">
        <div className="container mx-auto px-4" ref={chartsRef}>
          <SectionHeading
            label="Readings"
            title="Recent 24h Observations"
            subtitle="Hourly precipitation and temperature from all data sources"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={chartsInView ? "show" : undefined}
            className="grid gap-4 md:grid-cols-2"
          >
            {[
              {
                title: "Precipitation",
                dataKey: "precipitation",
                color: "hsl(var(--primary))",
                unit: " mm",
              },
              {
                title: "Temperature",
                dataKey: "temperature",
                color: "hsl(142.1 76.2% 36.3%)",
                unit: " °C",
              },
            ].map(({ title, dataKey, color, unit }) => (
              <motion.div key={dataKey} variants={fadeUp}>
                <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                  <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                  <div className="pt-5 px-6 pb-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground mb-4">
                      {title}
                    </p>
                    {hourlyLoading ? (
                      <Skeleton className="h-35 w-full" />
                    ) : chartData.length === 0 ? (
                      <EmptyState
                        icon={CloudRain}
                        title="No data"
                        description="No hourly readings available"
                        size="sm"
                      />
                    ) : (
                      <ResponsiveContainer width="100%" height={140}>
                        <LineChart
                          data={chartData}
                          margin={{ top: 4, right: 4, bottom: 0, left: -16 }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            className="stroke-border"
                          />
                          <XAxis
                            dataKey="time"
                            tick={{ fontSize: 10 }}
                            className="fill-muted-foreground"
                          />
                          <YAxis
                            tick={{ fontSize: 10 }}
                            className="fill-muted-foreground"
                          />
                          <ChartTooltip unit={unit} />
                          <Line
                            type="monotone"
                            dataKey={dataKey}
                            stroke={color}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 3 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </GlassCard>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>
    </div>
  );
}
