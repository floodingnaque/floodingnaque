/**
 * BarangayStatusSection
 *
 * Main orchestrator for the public "Live Barangay Status" section.
 *
 * Layout: two-column (3/5 map + 2/5 scrollable barangay cards) on desktop,
 * stacked on mobile. Composes all sub-components:
 *   StatusSectionHeader, CityWideSummary, BarangayCard grid,
 *   BarangayDetailDrawer, RecentPublicAlerts, DataTransparency,
 *   RegistrationCTA.
 *
 * Data: useAllBarangayPredictions() - batched live risk per barangay.
 */

import { BARANGAYS, type BarangayData } from "@/config/paranaque";
import { useAllBarangayPredictions } from "@/features/flooding/hooks/useAllBarangayPredictions";
import type { RiskLevel } from "@/types";
import { motion, useInView } from "framer-motion";
import { Loader2, MapPin } from "lucide-react";
import { Suspense, lazy, useCallback, useMemo, useRef, useState } from "react";

import { BarangayCard } from "./BarangayCard";
import { BarangayDetailDrawer } from "./BarangayDetailDrawer";
import { CityWideSummary } from "./CityWideSummary";
import { PublicReportsFeed } from "./PublicReportsFeed";
import { RecentPublicAlerts } from "./RecentPublicAlerts";
import { RegistrationCTA } from "./RegistrationCTA";
import { StatusSectionHeader } from "./StatusSectionHeader";

// Lazy-load heavy map (Leaflet)
const BarangayRiskMap = lazy(() =>
  import("@/features/dashboard/components/BarangayRiskMap").then((m) => ({
    default: m.BarangayRiskMap,
  })),
);

// ---------------------------------------------------------------------------
// Sort barangays: Critical first, then Alert, then Safe
// ---------------------------------------------------------------------------

const STATIC_RISK_MAP: Record<BarangayData["floodRisk"], RiskLevel> = {
  low: 0,
  moderate: 1,
  high: 2,
};

const RISK_LABEL: Record<string, { text: string; className: string }> = {
  high: { text: "High", className: "text-risk-critical font-semibold" },
  moderate: { text: "Moderate", className: "text-risk-alert font-semibold" },
  low: { text: "Low", className: "text-risk-safe font-semibold" },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BarangayStatusSection() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.05 });

  const { data: predictions, isLoading } = useAllBarangayPredictions(isInView);

  // Detail drawer state
  const [selectedBarangay, setSelectedBarangay] = useState<BarangayData | null>(
    null,
  );
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleViewDetails = useCallback((b: BarangayData) => {
    setSelectedBarangay(b);
    setDrawerOpen(true);
  }, []);

  // Build live predictions map for the BarangayRiskMap component
  const livePredictionsMap = useMemo(() => {
    if (!predictions) return undefined;
    const map = new Map<string, RiskLevel>();
    for (const [key, pred] of Object.entries(predictions)) {
      map.set(key, pred.risk_level);
    }
    return map;
  }, [predictions]);

  // Sort barangays by risk (Critical → Alert → Safe)
  const sortedBarangays = useMemo(() => {
    return [...BARANGAYS].sort((a, b) => {
      const riskA =
        predictions?.[a.key]?.risk_level ?? STATIC_RISK_MAP[a.floodRisk];
      const riskB =
        predictions?.[b.key]?.risk_level ?? STATIC_RISK_MAP[b.floodRisk];
      return riskB - riskA; // Higher risk first
    });
  }, [predictions]);

  return (
    <section
      id="barangay-status"
      className="py-16 sm:py-20 bg-background"
      ref={ref}
    >
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : undefined}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <StatusSectionHeader
            predictions={predictions}
            isLoading={isLoading}
          />

          {/* City-wide summary stats */}
          <CityWideSummary predictions={predictions} isLoading={isLoading} />

          {/* Two-column layout: Map + Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">
            {/* Map panel - 3/5 width on desktop */}
            <div className="lg:col-span-3">
              <Suspense
                fallback={
                  <div className="flex items-center justify-center h-125 bg-muted/30 rounded-xl border border-border/40">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                }
              >
                <BarangayRiskMap
                  height={500}
                  livePredictions={livePredictionsMap}
                />
              </Suspense>
            </div>

            {/* Barangay cards - 2/5 width, scrollable */}
            <div className="lg:col-span-2 max-h-130 overflow-y-auto pr-1 space-y-3 scrollbar-thin">
              {sortedBarangays.map((b) => (
                <BarangayCard
                  key={b.key}
                  barangay={b}
                  prediction={predictions?.[b.key]}
                  isLoading={isLoading}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          </div>

          {/* Bottom row: Reports Feed + Alerts (2-col) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <PublicReportsFeed />
            <RecentPublicAlerts />
          </div>

          {/* Barangay summary table (collapsed from former BarangayMapSection) */}
          <details className="mb-8 group">
            <summary className="cursor-pointer flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2">
              <MapPin className="h-4 w-4 text-primary" />
              View All 16 Barangays — Population &amp; Risk Summary
              <span className="ml-1 text-xs transition-transform group-open:rotate-90">
                ▶
              </span>
            </summary>
            <div className="mt-3 overflow-x-auto rounded-lg border border-border/40 bg-background">
              <table
                className="w-full text-sm"
                aria-label="Barangay flood risk summary"
              >
                <thead>
                  <tr className="bg-muted/50 text-left">
                    <th
                      scope="col"
                      className="px-4 py-2.5 font-medium text-muted-foreground"
                    >
                      Barangay
                    </th>
                    <th
                      scope="col"
                      className="px-4 py-2.5 font-medium text-muted-foreground text-right"
                    >
                      Population
                    </th>
                    <th
                      scope="col"
                      className="px-4 py-2.5 font-medium text-muted-foreground text-center"
                    >
                      Flood Risk
                    </th>
                    <th
                      scope="col"
                      className="px-4 py-2.5 font-medium text-muted-foreground"
                    >
                      Evacuation Centre
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {BARANGAYS.map((b) => {
                    const risk = (RISK_LABEL[b.floodRisk] ?? RISK_LABEL.low)!;
                    return (
                      <tr
                        key={b.key}
                        className="hover:bg-muted/20 transition-colors"
                      >
                        <td className="px-4 py-2 font-medium text-foreground">
                          {b.name}
                        </td>
                        <td className="px-4 py-2 text-right text-muted-foreground tabular-nums">
                          {b.population.toLocaleString()}
                        </td>
                        <td
                          className={`px-4 py-2 text-center ${risk.className}`}
                        >
                          {risk.text}
                        </td>
                        <td className="px-4 py-2 text-muted-foreground text-xs">
                          {b.evacuationCenter}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>

          {/* Registration CTA */}
          <RegistrationCTA predictions={predictions} />
        </motion.div>
      </div>

      {/* Detail drawer */}
      <BarangayDetailDrawer
        barangay={selectedBarangay}
        prediction={
          selectedBarangay ? predictions?.[selectedBarangay.key] : undefined
        }
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </section>
  );
}
