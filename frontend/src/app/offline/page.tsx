import { MapPin, Phone, RefreshCw, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

interface EvacuationCenter {
  id: number;
  name: string;
  address: string;
}

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-center">
      <div className="mx-auto max-w-sm space-y-6">
        {/* Icon */}
        <div className="flex justify-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
            <WifiOff className="h-10 w-10 text-muted-foreground" />
          </div>
        </div>

        {/* Message */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">You're Offline</h1>
          <p className="text-muted-foreground">
            No internet connection. Some features are unavailable, but critical
            emergency information is still accessible.
          </p>
        </div>

        {/* Emergency contacts - always cached */}
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-left dark:border-red-800 dark:bg-red-950/30">
          <h2 className="mb-3 flex items-center gap-2 font-semibold text-red-700 dark:text-red-400">
            <Phone className="h-4 w-4" />
            Emergency Contacts
          </h2>
          <div className="space-y-2 text-sm">
            {[
              { label: "Parañaque DRRMO", number: "(02) 8776-8888" },
              { label: "Bureau of Fire", number: "(02) 8426-0246" },
              { label: "Philippine Red Cross", number: "143" },
              { label: "National Emergency", number: "911" },
            ].map(({ label, number }) => (
              <a
                key={label}
                href={`tel:${number.replace(/\D/g, "")}`}
                className="flex items-center justify-between rounded-lg p-2 transition-colors hover:bg-red-100 dark:hover:bg-red-900/30"
              >
                <span className="text-muted-foreground">{label}</span>
                <span className="font-semibold text-red-700 dark:text-red-400">
                  {number}
                </span>
              </a>
            ))}
          </div>
        </div>

        {/* Nearest evacuation centers - cached from last session */}
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-left dark:border-blue-800 dark:bg-blue-950/30">
          <h2 className="mb-2 flex items-center gap-2 font-semibold text-blue-700 dark:text-blue-400">
            <MapPin className="h-4 w-4" />
            Nearest Evacuation Centers
          </h2>
          <p className="text-xs text-muted-foreground">
            Showing centers cached from your last online session.
          </p>
          <EvacuationCenterOfflineList />
        </div>

        {/* Retry */}
        <Button
          onClick={() => window.location.reload()}
          className="w-full"
          variant="outline"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Try Again
        </Button>
      </div>
    </div>
  );
}

function EvacuationCenterOfflineList() {
  const [centers, setCenters] = useState<EvacuationCenter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [cacheError, setCacheError] = useState(false);

  useEffect(() => {
    if (typeof caches === "undefined") {
      setCacheError(true);
      setIsLoading(false);
      return;
    }

    caches
      .open("api-cache")
      .then((cache) => cache.match("/api/v1/evacuation/centers"))
      .then((res) => {
        if (res) {
          return res.json().then((data) => {
            const list = Array.isArray(data?.centers) ? data.centers : [];
            setCenters(list);
          });
        }
        return undefined;
      })
      .catch(() => {
        setCacheError(true);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return (
      <p className="mt-2 text-xs text-muted-foreground animate-pulse">
        Loading cached data…
      </p>
    );
  }

  if (cacheError) {
    return (
      <p className="mt-2 text-xs text-muted-foreground">
        Cache unavailable. Emergency contacts above are always accessible.
      </p>
    );
  }

  if (!centers.length) {
    return (
      <p className="mt-2 text-xs text-muted-foreground">
        No cached data. Visit the app online first.
      </p>
    );
  }

  return (
    <div className="mt-2 space-y-1">
      {centers.slice(0, 3).map((c) => (
        <div key={c.id} className="text-sm">
          <span className="font-medium">{c.name}</span>
          <span className="text-muted-foreground"> - {c.address}</span>
        </div>
      ))}
    </div>
  );
}
