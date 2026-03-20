/**
 * PersonalizedRiskBanner
 *
 * Shows flood risk personalized to the user's detected barangay.
 * - idle: "Show risk for my location" button
 * - requesting: Spinner
 * - granted + detected: Barangay name + risk badge + description
 * - denied / unavailable / outside bounds: City-wide risk fallback
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { BarangayData } from "@/config/paranaque";
import { useUserLocation } from "@/hooks/useUserLocation";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  Loader2,
  MapPin,
  Navigation,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Risk display config
// ---------------------------------------------------------------------------

const RISK_DISPLAY: Record<
  BarangayData["floodRisk"],
  { label: string; icon: typeof ShieldCheck; className: string }
> = {
  low: {
    label: "Low Risk",
    icon: ShieldCheck,
    className: "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
  },
  moderate: {
    label: "Moderate Risk",
    icon: AlertTriangle,
    className: "bg-risk-alert/15 text-risk-alert border-risk-alert/30",
  },
  high: {
    label: "High Risk",
    icon: ShieldAlert,
    className: "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PersonalizedRiskBanner() {
  const { status, location, barangay, requestLocation } = useUserLocation();

  // Idle: prompt user to share location
  if (status === "idle") {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3">
        <Navigation className="size-5 text-muted-foreground shrink-0" />
        <span className="text-sm text-muted-foreground">
          Get personalized flood risk for your location
        </span>
        <Button
          variant="outline"
          size="sm"
          className="ml-auto shrink-0"
          onClick={requestLocation}
        >
          <MapPin className="size-4 mr-1.5" />
          Share Location
        </Button>
      </div>
    );
  }

  // Requesting: spinner
  if (status === "requesting") {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3">
        <Loader2 className="size-5 text-muted-foreground animate-spin shrink-0" />
        <span className="text-sm text-muted-foreground">
          Detecting your location…
        </span>
      </div>
    );
  }

  // Denied or unavailable
  if (status === "denied" || status === "unavailable") {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3">
        <MapPin className="size-5 text-muted-foreground shrink-0" />
        <span className="text-base font-medium text-muted-foreground">
          {status === "denied"
            ? "Location access denied. Showing city-wide risk data."
            : "Location unavailable. Showing city-wide risk data."}
        </span>
      </div>
    );
  }

  // Granted + detected barangay
  if (barangay) {
    const cfg = RISK_DISPLAY[barangay.floodRisk];
    const Icon = cfg.icon;

    return (
      <div
        className={cn(
          "flex items-center gap-3 rounded-lg border px-4 py-3",
          cfg.className,
        )}
      >
        <Icon className="size-5 shrink-0" />
        <div className="flex flex-col gap-0.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium">Brgy. {barangay.name}</span>
            <Badge variant="outline" className={cn("text-xs", cfg.className)}>
              {cfg.label}
            </Badge>
          </div>
          <span className="text-xs opacity-80">
            {barangay.floodEvents} flood events recorded • {barangay.zone} zone
            {barangay.evacuationCenter &&
              ` • Evacuation: ${barangay.evacuationCenter}`}
          </span>
        </div>
      </div>
    );
  }

  // Granted but outside all barangay polygons (city-level fallback)
  if (location && !location.isWithinBounds) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3">
        <MapPin className="size-5 text-muted-foreground shrink-0" />
        <span className="text-sm text-muted-foreground">
          You appear to be outside Parañaque. Showing city-wide risk data.
        </span>
      </div>
    );
  }

  // Granted, within bounds, but no polygon match
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3">
      <MapPin className="size-5 text-muted-foreground shrink-0" />
      <span className="text-sm text-muted-foreground">
        Location detected in Parañaque. Unable to determine specific barangay.
      </span>
    </div>
  );
}
