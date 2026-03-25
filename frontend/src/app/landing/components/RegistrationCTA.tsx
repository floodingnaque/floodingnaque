/**
 * RegistrationCTA
 *
 * Contextual call-to-action that nudges unauthenticated visitors
 * to register. Becomes more prominent when Alert or Critical
 * conditions are detected.
 */

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PredictionResponse } from "@/types";
import { Bell, ChevronRight } from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

interface RegistrationCTAProps {
  predictions?: Record<string, PredictionResponse>;
}

export function RegistrationCTA({ predictions }: RegistrationCTAProps) {
  const elevated = useMemo(() => {
    if (!predictions) return false;
    return Object.values(predictions).some((p) => p.risk_level >= 1);
  }, [predictions]);

  return (
    <div
      className={cn(
        "rounded-xl p-5 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-colors",
        elevated
          ? "bg-risk-alert/10 border border-risk-alert/30"
          : "bg-muted/40 border border-border/40",
      )}
    >
      <div className="flex items-start gap-3">
        <Bell
          className={cn(
            "h-5 w-5 mt-0.5 shrink-0",
            elevated ? "text-risk-alert" : "text-muted-foreground",
          )}
        />
        <div>
          <p className="font-semibold text-sm text-foreground">
            {elevated
              ? "Elevated flood risk detected — stay informed"
              : "Get personalized flood alerts for your barangay"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Create a free account to receive early-warning notifications, save
            your household profile, and access your personal risk dashboard.
          </p>
        </div>
      </div>
      <Button
        asChild
        size="sm"
        className={cn(
          "shrink-0",
          elevated
            ? "bg-risk-alert hover:bg-risk-alert/90 text-white"
            : "bg-primary hover:bg-primary/90 text-white",
        )}
      >
        <Link to="/register" className="inline-flex items-center gap-1.5">
          Register Free <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </Button>
    </div>
  );
}
