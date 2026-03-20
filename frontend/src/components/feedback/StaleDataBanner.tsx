/**
 * StaleDataBanner
 *
 * A small alert bar shown at the top of a component when cached
 * (possibly stale) data is being displayed because the network is
 * unavailable.
 */

import { Alert, AlertDescription } from "@/components/ui/alert";
import { WifiOff } from "lucide-react";

interface StaleDataBannerProps {
  cachedAt?: string;
}

export function StaleDataBanner({ cachedAt }: StaleDataBannerProps) {
  const timeLabel = cachedAt
    ? new Date(cachedAt).toLocaleString("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "an earlier session";

  return (
    <Alert
      variant="destructive"
      className="mb-4 border-risk-alert bg-risk-alert/10 text-risk-alert"
    >
      <WifiOff className="h-4 w-4 text-risk-alert!" />
      <AlertDescription>
        You are offline. Showing cached data from {timeLabel}. Results may be
        outdated.
      </AlertDescription>
    </Alert>
  );
}

export default StaleDataBanner;
