/**
 * PushPermissionPrompt
 *
 * Contextual prompt to enable push notifications after the user has
 * experienced a Critical alert in-app. Only shown when:
 *   1. Notification.permission === 'default' (not yet asked)
 *   2. At least 1 Critical alert has been seen
 *   3. Not dismissed this session
 */

import { Button } from "@/components/ui/button";
import { subscribeToPushNotifications } from "@/lib/push-notifications";
import { useAlertStore } from "@/state";
import type { Alert } from "@/types";
import { Bell, X } from "lucide-react";
import { useState } from "react";

export function PushPermissionPrompt() {
  const [isDismissed, setIsDismissed] = useState(false);
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const liveAlerts = useAlertStore((s) => s.liveAlerts);

  // Only show if permission not yet asked
  if (
    typeof Notification === "undefined" ||
    Notification.permission !== "default"
  ) {
    return null;
  }

  // Only show after user has seen a Critical alert
  const hasCritical = liveAlerts.some((a: Alert) => a.risk_level === 2);
  if (!hasCritical) return null;

  if (isDismissed || isSubscribed) return null;

  const handleEnable = async () => {
    setIsSubscribing(true);
    const sub = await subscribeToPushNotifications("city-wide");
    setIsSubscribing(false);
    if (sub) {
      setIsSubscribed(true);
    }
  };

  return (
    <div className="relative rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
      <button
        onClick={() => setIsDismissed(true)}
        className="absolute top-2 right-2 p-1 rounded-md hover:bg-muted transition-colors"
        aria-label="Dismiss"
      >
        <X className="size-4 text-muted-foreground" />
      </button>

      <div className="flex items-start gap-3 pr-6">
        <Bell className="size-5 text-destructive shrink-0 mt-0.5" />
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">
            Get notified of Critical alerts even when this tab is closed
          </p>
          <p className="text-xs text-muted-foreground">
            We'll only send notifications for Critical flood alerts in Parañaque
            City.
          </p>
          <div className="flex gap-2 mt-1">
            <Button
              size="sm"
              variant="destructive"
              onClick={handleEnable}
              disabled={isSubscribing}
            >
              {isSubscribing ? "Enabling…" : "Enable Notifications"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsDismissed(true)}
            >
              Not Now
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
