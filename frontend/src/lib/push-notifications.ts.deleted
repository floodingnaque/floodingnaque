/**
 * Push Notifications Client
 *
 * Handles VAPID-based push subscription via the Push API.
 * Sends subscription to backend for server-side push delivery.
 *
 * Requires:
 * - VITE_VAPID_PUBLIC_KEY env var (base64url-encoded public key)
 * - Backend POST /api/v1/notifications/subscribe endpoint (separate task)
 */

import apiClient from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Convert a URL-safe base64 VAPID key to a Uint8Array for applicationServerKey.
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}

// ---------------------------------------------------------------------------
// Subscribe
// ---------------------------------------------------------------------------

/**
 * Subscribe to push notifications for a specific barangay.
 *
 * @param barangay - Barangay key for targeted alerts
 * @returns PushSubscription if successful, null if unsupported or denied
 */
export async function subscribeToPushNotifications(
  barangay: string,
): Promise<PushSubscription | null> {
  // Feature detection
  if (!("PushManager" in window) || !("serviceWorker" in navigator)) {
    return null;
  }

  const vapidKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
  if (!vapidKey) {
    console.warn("[Push] VITE_VAPID_PUBLIC_KEY not configured");
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.ready;

    // Check for existing subscription first
    let subscription = await registration.pushManager.getSubscription();

    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey) as BufferSource,
      });
    }

    // Send subscription to backend (404 handled gracefully if endpoint missing)
    try {
      await apiClient.post("/api/v1/notifications/subscribe", {
        subscription: subscription.toJSON(),
        barangay,
      });
    } catch {
      // Backend endpoint may not exist yet — subscription still valid locally
      console.warn("[Push] Failed to register subscription with backend");
    }

    return subscription;
  } catch (error) {
    if (error instanceof DOMException && error.name === "NotAllowedError") {
      return null; // Permission denied
    }
    console.error("[Push] Subscription failed:", error);
    return null;
  }
}

/**
 * Check if push notifications are supported and permission status.
 */
export function getPushPermissionStatus():
  | NotificationPermission
  | "unsupported" {
  if (!("Notification" in window)) return "unsupported";
  return Notification.permission;
}
