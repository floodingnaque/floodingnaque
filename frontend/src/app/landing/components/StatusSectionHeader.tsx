/**
 * StatusSectionHeader
 *
 * Title bar for the Barangay Status section with live timestamp
 * and summary badges showing Safe / Alert / Critical counts.
 */

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { PredictionResponse } from "@/types";
import { Radio } from "lucide-react";
import { memo, useEffect, useState } from "react";

interface StatusSectionHeaderProps {
  predictions?: Record<string, PredictionResponse>;
  isLoading: boolean;
}

const TimeStamp = memo(function TimeStamp() {
  const [now, setNow] = useState(() =>
    new Date().toLocaleTimeString("en-PH", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  );

  useEffect(() => {
    const id = setInterval(
      () =>
        setNow(
          new Date().toLocaleTimeString("en-PH", {
            hour: "2-digit",
            minute: "2-digit",
          }),
        ),
      60_000,
    );
    return () => clearInterval(id);
  }, []);

  return (
    <span className="text-xs text-muted-foreground whitespace-nowrap">
      Updated {now}
    </span>
  );
});

export function StatusSectionHeader({
  predictions,
  isLoading,
}: StatusSectionHeaderProps) {
  const counts = { safe: 0, alert: 0, critical: 0 };

  if (predictions) {
    for (const p of Object.values(predictions)) {
      if (p.risk_level === 0) counts.safe++;
      else if (p.risk_level === 1) counts.alert++;
      else counts.critical++;
    }
  }

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Radio className="h-4 w-4 text-risk-critical animate-pulse" />
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Live Barangay Status
          </h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Real-time flood risk for all 16 Parañaque barangays
        </p>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {isLoading ? (
          <>
            <Skeleton className="h-6 w-20 rounded-full" />
            <Skeleton className="h-6 w-20 rounded-full" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </>
        ) : (
          <>
            <Badge
              variant="outline"
              className="bg-risk-safe/10 text-risk-safe border-risk-safe/30"
            >
              {counts.safe} Safe
            </Badge>
            <Badge
              variant="outline"
              className="bg-risk-alert/10 text-risk-alert border-risk-alert/30"
            >
              {counts.alert} Alert
            </Badge>
            <Badge
              variant="outline"
              className="bg-risk-critical/10 text-risk-critical border-risk-critical/30"
            >
              {counts.critical} Critical
            </Badge>
          </>
        )}
        <TimeStamp />
      </div>
    </div>
  );
}
