/**
 * ResidentDecisionPanel
 *
 * Location-aware decision engine for residents answering:
 * "What should I do right now?"
 *
 * Composes live prediction, nearby community reports, and nearest
 * evacuation center data into a tri-state recommendation:
 *   - "Evacuate Now"      → risk_level 2 OR ≥2 critical nearby reports
 *   - "Prepare to Evacuate" → risk_level 1
 *   - "Safe for Now"       → risk_level 0
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  LifeBuoy,
  MapPin,
  Navigation,
  Phone,
  ShieldAlert,
  ShieldCheck,
  Siren,
} from "lucide-react";
import { memo, useMemo } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useCommunityReports } from "@/features/community/hooks/useCommunityReports";
import { useNearestCenters } from "@/features/evacuation/hooks/useEvacuationCenters";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/state";
import type { PredictionResponse } from "@/types";
import type { CommunityReport } from "@/types/api/community";
import type { RiskLevel } from "@/types/api/prediction";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DRRMO_HOTLINE = "(02) 8820-0645";

type DecisionState = "evacuate" | "prepare" | "safe";

interface DecisionConfig {
  state: DecisionState;
  icon: React.ElementType;
  headline: string;
  headlineFil: string;
  message: string;
  messageFil: string;
  containerClass: string;
  iconClass: string;
  textClass: string;
}

const DECISION_MAP: Record<DecisionState, DecisionConfig> = {
  evacuate: {
    state: "evacuate",
    icon: Siren,
    headline: "Evacuate Now",
    headlineFil: "Lumikas na Agad",
    message:
      "Flooding is imminent or ongoing in your area. Head to the nearest evacuation center immediately.",
    messageFil:
      "Malapit na o nagbabaha na sa iyong lugar. Pumunta agad sa pinakamalapit na evacuation center.",
    containerClass:
      "border-red-500/40 bg-red-500/10 dark:bg-red-950/30 ring-2 ring-red-500/20",
    iconClass: "text-red-600 dark:text-red-400",
    textClass: "text-red-700 dark:text-red-300",
  },
  prepare: {
    state: "prepare",
    icon: ShieldAlert,
    headline: "Prepare to Evacuate",
    headlineFil: "Maghanda sa Paglikas",
    message:
      "Flood risk is elevated. Pack essentials and be ready to leave if conditions worsen.",
    messageFil:
      "Mataas ang panganib ng baha. Ihanda ang mga gamit at maging handa kung lumala ang sitwasyon.",
    containerClass:
      "border-amber-500/40 bg-amber-500/10 dark:bg-amber-950/30 ring-1 ring-amber-500/15",
    iconClass: "text-amber-600 dark:text-amber-400",
    textClass: "text-amber-700 dark:text-amber-300",
  },
  safe: {
    state: "safe",
    icon: ShieldCheck,
    headline: "Safe for Now",
    headlineFil: "Ligtas sa Ngayon",
    message:
      "No immediate flood threat detected. Stay informed and monitor weather updates.",
    messageFil:
      "Walang agarang banta ng baha. Manatiling updated sa mga balita tungkol sa panahon.",
    containerClass: "border-green-500/30 bg-green-500/5 dark:bg-green-950/20",
    iconClass: "text-green-600 dark:text-green-400",
    textClass: "text-green-700 dark:text-green-300",
  },
};

// ---------------------------------------------------------------------------
// Decision algorithm
// ---------------------------------------------------------------------------

function computeDecision(
  riskLevel: RiskLevel,
  nearbyReports: CommunityReport[],
): DecisionState {
  const criticalReports = nearbyReports.filter(
    (r) =>
      r.risk_label === "Critical" &&
      r.status !== "rejected" &&
      // Only count reports from the last 3 hours
      Date.now() - new Date(r.created_at).getTime() < 3 * 60 * 60 * 1000,
  );

  if (riskLevel === 2 || criticalReports.length >= 2) return "evacuate";
  if (riskLevel === 1) return "prepare";
  return "safe";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ResidentDecisionPanelProps {
  prediction: PredictionResponse | undefined;
  userLocation: [number, number] | null;
  className?: string;
}

export const ResidentDecisionPanel = memo(function ResidentDecisionPanel({
  prediction,
  userLocation,
  className,
}: ResidentDecisionPanelProps) {
  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;
  const language = useLanguage();

  // Nearby community reports (last 6 hours, auto-refreshing)
  const { data: reports } = useCommunityReports({
    hours: 6,
    limit: 50,
  });

  // Nearest evacuation center (requires user location)
  const { data: nearestCenters } = useNearestCenters(
    userLocation?.[0],
    userLocation?.[1],
    1,
  );

  const nearestCenter = nearestCenters?.[0];

  const decision = useMemo(
    () => computeDecision(riskLevel, reports?.reports ?? []),
    [riskLevel, reports],
  );

  const config = DECISION_MAP[decision];
  const Icon = config.icon;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={decision}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.3 }}
        className={cn(
          "rounded-xl border-2 p-5 space-y-4",
          config.containerClass,
          className,
        )}
        role="alert"
        aria-live="assertive"
        aria-label={`Decision: ${config.headline}`}
      >
        {/* Header */}
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "rounded-full p-2.5",
              decision === "evacuate" && "bg-red-500/15 animate-pulse",
              decision === "prepare" && "bg-amber-500/15",
              decision === "safe" && "bg-green-500/15",
            )}
          >
            <Icon className={cn("h-7 w-7", config.iconClass)} />
          </div>
          <div className="flex-1 min-w-0">
            <h3
              className={cn(
                "text-xl sm:text-2xl font-bold tracking-tight",
                config.textClass,
              )}
            >
              {config.headline}
            </h3>
            {language === "fil" && (
              <p className="text-xs text-muted-foreground">
                {config.headlineFil}
              </p>
            )}
          </div>
          <Badge
            variant="outline"
            className={cn("shrink-0 text-xs", config.textClass)}
          >
            {prediction
              ? `${Math.round((prediction.confidence ?? 0) * 100)}% confidence`
              : "Loading…"}
          </Badge>
        </div>

        {/* Message */}
        <p className="text-sm leading-relaxed text-foreground/80">
          {language === "fil" ? config.messageFil : config.message}
        </p>

        {/* Nearest evacuation center */}
        {nearestCenter && (
          <div className="flex items-start gap-3 rounded-lg border border-border/50 bg-background/50 p-3">
            <LifeBuoy className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {nearestCenter.center.name}
              </p>
              <p className="text-xs text-muted-foreground">
                {nearestCenter.distance_km < 1
                  ? `${Math.round(nearestCenter.distance_km * 1000)} m away`
                  : `${nearestCenter.distance_km.toFixed(1)} km away`}
                {nearestCenter.center.capacity_current <
                  nearestCenter.center.capacity_total && (
                  <>
                    {" · "}
                    <span className="text-green-600 dark:text-green-400">
                      {nearestCenter.available_slots} slots available
                    </span>
                  </>
                )}
              </p>
            </div>
            {nearestCenter.google_maps_url && (
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="shrink-0 h-8 px-2"
              >
                <a
                  href={nearestCenter.google_maps_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Navigation className="h-3.5 w-3.5 mr-1" />
                  Directions
                </a>
              </Button>
            )}
          </div>
        )}

        {/* Location hint when no user location */}
        {!userLocation && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            <span>
              Share your location for personalized evacuation guidance
            </span>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          {decision === "evacuate" && (
            <>
              <Button
                asChild
                size="sm"
                className="bg-red-600 text-white hover:bg-red-700"
              >
                <Link to="/resident/evacuation">
                  <LifeBuoy className="h-4 w-4 mr-1.5" />
                  Find Evacuation Centers
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <a href={`tel:${DRRMO_HOTLINE.replace(/[^0-9+]/g, "")}`}>
                  <Phone className="h-4 w-4 mr-1.5" />
                  Call DRRMO
                </a>
              </Button>
            </>
          )}
          {decision === "prepare" && (
            <>
              <Button
                asChild
                variant="outline"
                size="sm"
                className="border-amber-500/30 text-amber-700 dark:text-amber-400 hover:bg-amber-500/10"
              >
                <Link to="/resident/evacuation">
                  <LifeBuoy className="h-4 w-4 mr-1.5" />
                  View Evacuation Centers
                </Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link to="/resident/guide">
                  Preparation Checklist
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Link>
              </Button>
            </>
          )}
          {decision === "safe" && (
            <Button asChild variant="outline" size="sm">
              <Link to="/resident/guide">
                Safety Tips
                <ArrowRight className="h-3.5 w-3.5 ml-1" />
              </Link>
            </Button>
          )}
        </div>

        {/* DRRMO contact — always visible */}
        <div className="flex items-center gap-2 pt-1 border-t border-border/30">
          <Phone className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <span className="text-xs text-muted-foreground">
            Parañaque DRRMO:{" "}
            <a
              href={`tel:${DRRMO_HOTLINE.replace(/[^0-9+]/g, "")}`}
              className="font-medium text-foreground hover:underline"
            >
              {DRRMO_HOTLINE}
            </a>
          </span>
        </div>
      </motion.div>
    </AnimatePresence>
  );
});
