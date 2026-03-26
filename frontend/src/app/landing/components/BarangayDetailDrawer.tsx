/**
 * BarangayDetailDrawer
 *
 * Side sheet showing detailed information for a selected barangay.
 * Three tabs: Overview (risk + contributing factors), Profile
 * (demographics + historical floods), Evacuation (center + contacts).
 */

import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EMERGENCY_CONTACTS, type BarangayData } from "@/config/paranaque";
import { cn } from "@/lib/utils";
import type { PredictionResponse, RiskLevel } from "@/types";
import {
  AlertTriangle,
  CloudRain,
  Droplets,
  History,
  MapPin,
  Phone,
  Shield,
  Thermometer,
  Users,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const RISK_LABEL: Record<RiskLevel, { text: string; cls: string }> = {
  0: {
    text: "Safe",
    cls: "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
  },
  1: {
    text: "Alert",
    cls: "bg-risk-alert/15 text-risk-alert border-risk-alert/30",
  },
  2: {
    text: "Critical",
    cls: "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
  },
};

const STATIC_RISK_MAP: Record<BarangayData["floodRisk"], RiskLevel> = {
  low: 0,
  moderate: 1,
  high: 2,
};

function kelvinToCelsius(k: number) {
  return (k - 273.15).toFixed(1);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface BarangayDetailDrawerProps {
  barangay: BarangayData | null;
  prediction?: PredictionResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function BarangayDetailDrawer({
  barangay,
  prediction,
  open,
  onOpenChange,
}: BarangayDetailDrawerProps) {
  if (!barangay) return null;

  const riskLevel =
    prediction?.risk_level ?? STATIC_RISK_MAP[barangay.floodRisk];
  const riskMeta = RISK_LABEL[riskLevel];
  const weather = prediction?.weather_data;
  const factors = prediction?.smart_alert?.contributing_factors ?? [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="pb-4">
          <div className="flex items-center justify-between gap-2">
            <SheetTitle className="text-lg">{barangay.name}</SheetTitle>
            <Badge variant="outline" className={cn("text-xs", riskMeta.cls)}>
              {riskMeta.text}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {barangay.zone} zone &middot; {barangay.population.toLocaleString()}{" "}
            residents
          </p>
        </SheetHeader>

        <Tabs defaultValue="overview" className="mt-2">
          <TabsList className="w-full">
            <TabsTrigger value="overview" className="flex-1 text-xs">
              Overview
            </TabsTrigger>
            <TabsTrigger value="profile" className="flex-1 text-xs">
              Profile
            </TabsTrigger>
            <TabsTrigger value="evacuation" className="flex-1 text-xs">
              Evacuation
            </TabsTrigger>
          </TabsList>

          {/* ----------------------------------------------------------------
           * TAB 1: Overview - risk explanation + weather + factors
           * -------------------------------------------------------------- */}
          <TabsContent value="overview" className="space-y-5 mt-4">
            {/* Risk explanation */}
            <div className="rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm">Risk Assessment</span>
              </div>
              {prediction ? (
                <>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-muted-foreground text-xs">
                        Probability
                      </p>
                      <p className="font-semibold tabular-nums">
                        {(prediction.probability * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">
                        Confidence
                      </p>
                      <p className="font-semibold tabular-nums">
                        {(prediction.confidence * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">Model</p>
                      <p className="font-semibold text-xs">
                        {prediction.model_version}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">
                        Risk Label
                      </p>
                      <p className="font-semibold">{prediction.risk_label}</p>
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Based on historical data: {barangay.floodRisk} risk zone.
                </p>
              )}
            </div>

            {/* Weather snapshot */}
            {weather && (
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <CloudRain className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium text-sm">Current Weather</span>
                  {weather.simulated && (
                    <Badge variant="secondary" className="text-[10px] h-4">
                      Simulated
                    </Badge>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Thermometer className="h-3.5 w-3.5 text-muted-foreground" />
                    <div>
                      <p className="text-muted-foreground text-xs">
                        Temperature
                      </p>
                      <p className="font-semibold tabular-nums">
                        {kelvinToCelsius(weather.temperature)}°C
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Droplets className="h-3.5 w-3.5 text-muted-foreground" />
                    <div>
                      <p className="text-muted-foreground text-xs">Humidity</p>
                      <p className="font-semibold tabular-nums">
                        {weather.humidity}%
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <CloudRain className="h-3.5 w-3.5 text-muted-foreground" />
                    <div>
                      <p className="text-muted-foreground text-xs">
                        Precipitation
                      </p>
                      <p className="font-semibold tabular-nums">
                        {weather.precipitation.toFixed(1)} mm
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Source</p>
                    <p className="font-semibold text-xs capitalize">
                      {weather.source}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Contributing factors */}
            {factors.length > 0 && (
              <div className="rounded-lg border p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-risk-alert" />
                  <span className="font-medium text-sm">
                    Contributing Factors
                  </span>
                </div>
                <ul className="space-y-1">
                  {factors.map((f, i) => (
                    <li
                      key={i}
                      className="text-sm text-muted-foreground flex items-start gap-2"
                    >
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-risk-alert shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </TabsContent>

          {/* ----------------------------------------------------------------
           * TAB 2: Profile - demographics + historical
           * -------------------------------------------------------------- */}
          <TabsContent value="profile" className="space-y-5 mt-4">
            <div className="rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm">Demographics</span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground text-xs">Population</p>
                  <p className="font-semibold tabular-nums">
                    {barangay.population.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Zone</p>
                  <p className="font-semibold">{barangay.zone}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Area</p>
                  <p className="font-semibold tabular-nums">
                    {barangay.area} km²
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">
                    Historical Risk
                  </p>
                  <p className="font-semibold capitalize">
                    {barangay.floodRisk}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm">
                  Flood History (2022–2025)
                </span>
              </div>
              <div className="text-sm">
                <p className="text-muted-foreground text-xs">
                  Recorded Flood Events
                </p>
                <p className="text-2xl font-bold tabular-nums">
                  {barangay.floodEvents}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  From official DRRMO records
                </p>
              </div>
            </div>

            <div className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm">Coordinates</span>
              </div>
              <p className="text-sm text-muted-foreground tabular-nums">
                {barangay.lat.toFixed(4)}°N, {barangay.lon.toFixed(4)}°E
              </p>
            </div>
          </TabsContent>

          {/* ----------------------------------------------------------------
           * TAB 3: Evacuation - center + emergency contacts
           * -------------------------------------------------------------- */}
          <TabsContent value="evacuation" className="space-y-5 mt-4">
            <div className="rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-risk-safe" />
                <span className="font-medium text-sm">Evacuation Center</span>
              </div>
              <p className="text-sm font-semibold">
                {barangay.evacuationCenter}
              </p>
              <p className="text-xs text-muted-foreground">
                Designated evacuation facility for {barangay.name} residents.
              </p>
            </div>

            <div className="rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm">Emergency Contacts</span>
              </div>
              <div className="space-y-3">
                {Object.values(EMERGENCY_CONTACTS).map((contact) => (
                  <div
                    key={contact.phone}
                    className="flex items-start justify-between gap-2 text-sm"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-xs">{contact.name}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {contact.description}
                      </p>
                    </div>
                    <span className="shrink-0 font-mono text-xs text-primary tabular-nums">
                      {contact.phone}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}
