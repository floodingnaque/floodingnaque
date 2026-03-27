/**
 * Operator - Weather Monitor Page
 */

import { Cloud, Droplets, RefreshCw, Thermometer, Wind } from "lucide-react";

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ForecastPanel } from "@/features/dashboard";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";

export default function OperatorWeatherPage() {
  const { data: prediction, isLoading, refetch } = useLivePrediction();

  const weather = prediction?.weather_data;
  const tempC = weather?.temperature
    ? Math.round(weather.temperature - 273.15)
    : null;

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <Breadcrumb
        items={[
          { label: "Operations", href: "/operator" },
          { label: "Weather Monitor" },
        ]}
        className="mb-4"
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Weather Monitor</h2>
          <p className="text-sm text-muted-foreground">
            Real-time conditions for Parañaque City
          </p>
        </div>
        <div className="flex items-center gap-2">
          {weather?.source && (
            <Badge variant="outline" className="text-xs">
              Source: {weather.source}
            </Badge>
          )}
          {weather?.simulated && (
            <Badge
              variant="outline"
              className="bg-amber-500/10 text-amber-700 border-amber-500/30 text-xs"
            >
              Simulated
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => refetch()}
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Current Conditions */}
      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : weather ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center shrink-0">
                <Thermometer className="h-5 w-5 text-orange-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {tempC !== null ? `${tempC}°C` : "-"}
                </p>
                <p className="text-xs text-muted-foreground">Temperature</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
                <Droplets className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {weather.humidity != null ? `${weather.humidity}%` : "-"}
                </p>
                <p className="text-xs text-muted-foreground">Humidity</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-sky-500/10 flex items-center justify-center shrink-0">
                <Cloud className="h-5 w-5 text-sky-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {weather.precipitation != null
                    ? `${weather.precipitation} mm`
                    : "-"}
                </p>
                <p className="text-xs text-muted-foreground">Precipitation</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-teal-500/10 flex items-center justify-center shrink-0">
                <Wind className="h-5 w-5 text-teal-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {weather.wind_speed != null
                    ? `${weather.wind_speed} m/s`
                    : "-"}
                </p>
                <p className="text-xs text-muted-foreground">Wind Speed</p>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Cloud className="h-10 w-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">Weather data unavailable</p>
          </CardContent>
        </Card>
      )}

      {/* Forecast Chart */}
      <ForecastPanel hours={12} />
    </div>
  );
}
