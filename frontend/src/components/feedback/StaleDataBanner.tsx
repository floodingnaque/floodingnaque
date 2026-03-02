/**
 * StaleDataBanner
 *
 * A small alert bar shown at the top of a component when cached
 * (possibly stale) data is being displayed because the network is
 * unavailable.
 */

import { WifiOff } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface StaleDataBannerProps {
  cachedAt?: string;
}

export function StaleDataBanner({ cachedAt }: StaleDataBannerProps) {
  const timeLabel = cachedAt
    ? new Date(cachedAt).toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    : 'an earlier session';

  return (
    <Alert variant="destructive" className="mb-4 border-amber-500 bg-amber-50 text-amber-900 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-700">
      <WifiOff className="h-4 w-4 text-amber-600! dark:text-amber-400!" />
      <AlertDescription>
        You are offline. Showing cached data from {timeLabel}. Results may be outdated.
      </AlertDescription>
    </Alert>
  );
}

export default StaleDataBanner;
