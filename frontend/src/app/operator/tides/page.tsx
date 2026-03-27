/**
 * Operator - Tidal & River Level Monitoring Page
 *
 * Real-time tidal data, river level readings, and trend indicators
 * powered by WorldTides + PAGASA aggregation APIs.
 */

import { Info, Ruler, TrendingDown, TrendingUp, Waves } from "lucide-react";
import { useMemo } from "react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRiverLevel } from "@/features/dashboard";
import type { RiverReading } from "@/features/dashboard/types";
import {
  useCurrentTide,
  useTideExtremes,
  useTidePrediction,
  useTideStatus,
} from "@/features/weather/hooks/useTides";
import type { TideDataPoint } from "@/features/weather/services/tidesApi";

function fmtHeight(val: number | null | undefined): string {
  if (val == null) return "-";
  return `${val.toFixed(2)} m`;
}

function fmtTime(iso: string | undefined | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleTimeString("en-PH", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Resolve the time string from a TideDataPoint (backend uses `timestamp` or `date`) */
function tideTime(
  point: { date?: string; timestamp?: string } | null | undefined,
): string {
  return fmtTime(point?.date ?? point?.timestamp);
}

export default function OperatorTidesPage() {
  const {
    data: currentTide,
    isLoading: loadingCurrent,
    isError: errorCurrent,
  } = useCurrentTide();
  const {
    data: extremes,
    isLoading: loadingExtremes,
    isError: errorExtremes,
  } = useTideExtremes();
  const {
    data: prediction,
    isLoading: loadingPrediction,
    isError: errorPrediction,
  } = useTidePrediction();
  const { data: status } = useTideStatus();
  const { data: riverReadings, isLoading: loadingRiver } = useRiverLevel();

  // Derive whether tidal data is available at all
  const tidalUnavailable =
    !loadingCurrent &&
    !loadingExtremes &&
    !loadingPrediction &&
    errorCurrent &&
    errorPrediction;

  const nextHigh = useMemo(() => {
    if (!extremes?.extremes) return null;
    return (
      extremes.extremes.find(
        (e: TideDataPoint) => e.type === "High" || e.type === "high",
      ) ?? null
    );
  }, [extremes]);

  const nextLow = useMemo(() => {
    if (!extremes?.extremes) return null;
    return (
      extremes.extremes.find(
        (e: TideDataPoint) => e.type === "Low" || e.type === "low",
      ) ?? null
    );
  }, [extremes]);

  const riverData: RiverReading[] = useMemo(() => {
    if (!riverReadings) return [];
    return Array.isArray(riverReadings) ? riverReadings : [];
  }, [riverReadings]);

  const waterLevelStatus = (reading: RiverReading) => {
    if (reading.water_level >= reading.critical_level) return "critical";
    if (reading.water_level >= reading.alarm_level) return "warning";
    return "normal";
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <Breadcrumb
        items={[
          { label: "Operations", href: "/operator" },
          { label: "Tides & River Levels" },
        ]}
        className="mb-4"
      />

      {/* Tidal Data Unavailable Banner */}
      {tidalUnavailable && (
        <Card className="border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/30">
          <CardContent className="pt-4 flex items-start gap-3">
            <Info className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                Tidal data is currently unavailable
              </p>
              <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                The WorldTides API may be temporarily unreachable or the API key
                needs renewal. River level data below is unaffected.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current Levels */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
              <Waves className="h-5 w-5 text-blue-500" />
            </div>
            <div>
              {loadingCurrent ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                <p className="text-xl font-bold">
                  {fmtHeight(currentTide?.height)}
                </p>
              )}
              <p className="text-xs text-muted-foreground">Tidal Level</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-cyan-500/10 flex items-center justify-center shrink-0">
              <Ruler className="h-5 w-5 text-cyan-500" />
            </div>
            <div>
              {loadingRiver ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                <p className="text-xl font-bold">
                  {riverData.length > 0
                    ? fmtHeight(riverData[0]?.water_level)
                    : "-"}
                </p>
              )}
              <p className="text-xs text-muted-foreground">River Level</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center shrink-0">
              <TrendingDown className="h-5 w-5 text-green-500" />
            </div>
            <div>
              {loadingExtremes ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                <>
                  <p className="text-xl font-bold">
                    {fmtHeight(nextLow?.height)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Next Low {tideTime(nextLow)}
                  </p>
                </>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-red-500/10 flex items-center justify-center shrink-0">
              <TrendingUp className="h-5 w-5 text-red-500" />
            </div>
            <div>
              {loadingExtremes ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                <>
                  <p className="text-xl font-bold">
                    {fmtHeight(nextHigh?.height)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Next High {tideTime(nextHigh)}
                  </p>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Prediction Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Waves className="h-4 w-4 text-primary" />
            Tidal Prediction
          </CardTitle>
          <CardDescription>
            Current tidal risk assessment for Manila Bay / Parañaque coastline
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingPrediction ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full rounded" />
              <Skeleton className="h-10 w-3/4 rounded" />
            </div>
          ) : !prediction ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground border border-dashed border-border/50 rounded-lg">
              <Waves className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm font-medium">
                No tidal predictions available
              </p>
              <p className="text-xs mt-1">
                Tidal data from WorldTides API will appear once configured
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-4 flex-wrap">
                <div className="p-3 border rounded-lg flex-1 min-w-35">
                  <p className="text-lg font-bold">
                    {fmtHeight(prediction.current_height)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Current Height
                  </p>
                </div>
                <div className="p-3 border rounded-lg flex-1 min-w-35">
                  <Badge
                    variant={
                      prediction.risk_factor === "high"
                        ? "destructive"
                        : prediction.risk_factor === "moderate"
                          ? "secondary"
                          : "default"
                    }
                    className="text-xs"
                  >
                    {prediction.risk_factor} risk
                  </Badge>
                  <p className="text-xs text-muted-foreground mt-1">
                    Risk Factor
                  </p>
                </div>
                {prediction.next_high_tide && (
                  <div className="p-3 border rounded-lg flex-1 min-w-35">
                    <p className="text-lg font-bold">
                      {fmtHeight(prediction.next_high_tide.height)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Next High at {tideTime(prediction.next_high_tide)}
                    </p>
                  </div>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                {prediction.message}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tidal Extremes Table */}
      {extremes?.extremes && extremes.extremes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upcoming Tidal Extremes</CardTitle>
            <CardDescription>
              High and low tide schedule - Station: {extremes.station}, Datum:{" "}
              {extremes.datum}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="py-2 text-left font-medium">Type</th>
                    <th className="py-2 text-left font-medium">Time</th>
                    <th className="py-2 text-right font-medium">Height (m)</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {extremes.extremes.map((ext: TideDataPoint, i: number) => (
                    <tr key={i} className="hover:bg-muted/30">
                      <td className="py-2">
                        <Badge
                          variant={
                            ext.type === "High" || ext.type === "high"
                              ? "destructive"
                              : "default"
                          }
                          className="text-xs"
                        >
                          {ext.type}
                        </Badge>
                      </td>
                      <td className="py-2">{tideTime(ext)}</td>
                      <td className="py-2 text-right font-mono">
                        {fmtHeight(ext.height)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* River Monitoring */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Ruler className="h-4 w-4 text-primary" />
            River & Waterway Monitoring
          </CardTitle>
          <CardDescription>
            Water level readings from aggregation stations
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingRiver ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full rounded" />
              ))}
            </div>
          ) : riverData.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground border border-dashed border-border/50 rounded-lg">
              <Ruler className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm font-medium">No river readings available</p>
              <p className="text-xs mt-1">
                River/waterway stations will report here once data flows in
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {riverData.map((reading, i) => {
                const lvl = waterLevelStatus(reading);
                return (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium">
                        {reading.station_name ?? reading.station_id}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {fmtTime(reading.timestamp)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold">
                        {fmtHeight(reading.water_level)}
                      </p>
                      <Badge
                        variant={
                          lvl === "critical"
                            ? "destructive"
                            : lvl === "warning"
                              ? "secondary"
                              : "default"
                        }
                        className="text-[10px]"
                      >
                        {lvl}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* API Status */}
      {status && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Tidal API Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <Badge
                variant={
                  status.worldtides?.api_key_configured
                    ? "default"
                    : "secondary"
                }
                className="text-xs"
              >
                {status.active_provider !== "none" ? "Active" : "Disabled"}
              </Badge>
              <span>Provider: {status.active_provider}</span>
              {status.worldtides?.default_datum && (
                <span>Datum: {status.worldtides.default_datum}</span>
              )}
              {!status.worldtides?.api_key_configured && (
                <span className="text-yellow-600">API key not configured</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
