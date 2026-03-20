/**
 * LiveStatusRibbon Component
 *
 * Horizontally scrollable bar showing current risk level for all
 * 16 Parañaque barangays.  Uses a single batched query that staggers
 * requests in groups of 3 to avoid overwhelming the backend / OWM API.
 */

import { Skeleton } from "@/components/ui/skeleton";
import { BARANGAYS } from "@/config/paranaque";
import { useAllBarangayPredictions } from "@/features/flooding/hooks/useAllBarangayPredictions";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/state/stores/authStore";
import type { PredictionResponse, RiskLevel } from "@/types";
import { motion } from "framer-motion";
import { Radio } from "lucide-react";
import { memo, useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Per-barangay pill (pure display — no data fetching)
// ---------------------------------------------------------------------------

const DOT: Record<RiskLevel, { cls: string; label: string }> = {
  0: { cls: "bg-risk-safe", label: "SAFE" },
  1: { cls: "bg-risk-alert", label: "ALERT" },
  2: { cls: "bg-risk-critical", label: "CRITICAL" },
};

function BarangayPill({
  name,
  data,
}: {
  name: string;
  data?: PredictionResponse;
}) {
  const dot = data ? DOT[data.risk_level] : null;

  return (
    <button
      onClick={() =>
        document
          .getElementById("barangay-map")
          ?.scrollIntoView({ behavior: "smooth" })
      }
      className="flex items-center gap-1.5 shrink-0 px-3 py-1 rounded-full bg-muted/50 hover:bg-muted transition-colors text-sm"
    >
      <span
        className={cn(
          "inline-block h-2.5 w-2.5 rounded-full",
          dot?.cls ?? "bg-muted-foreground/30",
        )}
      />
      <span className="font-medium whitespace-nowrap">{name}</span>
      {dot && (
        <span className="text-[10px] text-muted-foreground font-semibold">
          {dot.label}
        </span>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Memoized clock — 60s interval only re-renders this component, not the
// entire ribbon.
// ---------------------------------------------------------------------------

const TimeDisplay = memo(function TimeDisplay() {
  const [lastUpdated, setLastUpdated] = useState(() =>
    new Date().toLocaleTimeString("en-PH", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  );

  useEffect(() => {
    const id = setInterval(() => {
      setLastUpdated(
        new Date().toLocaleTimeString("en-PH", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      );
    }, 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <span className="shrink-0 text-xs text-muted-foreground whitespace-nowrap">
      Updated {lastUpdated}
    </span>
  );
});

// ---------------------------------------------------------------------------
// Ribbon
// ---------------------------------------------------------------------------

export function LiveStatusRibbon() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const { data: predictions, isLoading } =
    useAllBarangayPredictions(isAuthenticated);

  return (
    <section
      id="live-status"
      className="border-b border-border/50 bg-background/95 backdrop-blur-sm"
    >
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="flex items-center gap-3 py-3.5 overflow-x-auto scrollbar-none"
        >
          {/* Live indicator */}
          <div className="flex items-center gap-1.5 shrink-0 text-xs font-bold tracking-wide text-risk-critical uppercase">
            <Radio className="h-3.5 w-3.5 animate-pulse" />
            Live
          </div>

          <div className="w-px h-5 bg-border shrink-0" />

          {/* Barangay pills */}
          {isLoading
            ? BARANGAYS.map((b) => (
                <Skeleton
                  key={b.key}
                  className="h-7 w-32 rounded-full shrink-0"
                />
              ))
            : BARANGAYS.map((b) => (
                <BarangayPill
                  key={b.key}
                  name={b.name}
                  data={predictions?.[b.key]}
                />
              ))}

          <div className="w-px h-5 bg-border shrink-0" />

          {/* Timestamp */}
          <TimeDisplay />
        </motion.div>
      </div>
    </section>
  );
}

export default LiveStatusRibbon;
