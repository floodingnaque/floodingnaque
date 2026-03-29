/**
 * useNotificationAutoPrompt
 *
 * Auto-requests Notification permission and subscribes to Web Push
 * shortly after the user logs in. Runs once per session (tracked via
 * sessionStorage) so it doesn't nag on every navigation.
 *
 * Falls back gracefully: if SW is not ready or VAPID is unconfigured,
 * it still requests bare Notification permission so the Browser
 * Notification API fallback in useAlertStream works.
 */

import { useEffect, useRef } from "react";

import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";
import { useAuthStore } from "@/state/stores/authStore";

const SESSION_KEY = "floodingnaque_push_prompted";

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray.buffer as ArrayBuffer;
}

export function useNotificationAutoPrompt() {
  const prompted = useRef(false);
  const isAuthenticated = useAuthStore((s) => !!s.accessToken);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (prompted.current) return;
    if (typeof window === "undefined" || !("Notification" in window)) return;

    // Only prompt once per browser session
    if (sessionStorage.getItem(SESSION_KEY)) return;

    // Small delay so the UI settles first
    const timer = setTimeout(async () => {
      prompted.current = true;
      sessionStorage.setItem(SESSION_KEY, "1");

      // Already granted — try to subscribe to push silently
      if (Notification.permission === "granted") {
        await tryPushSubscribe();
        return;
      }

      // Already denied — nothing we can do
      if (Notification.permission === "denied") return;

      // "default" — ask the user
      try {
        const perm = await Notification.requestPermission();
        if (perm === "granted") {
          await tryPushSubscribe();
        }
      } catch {
        // Permission request failed (e.g., insecure context)
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [isAuthenticated]);
}

async function tryPushSubscribe(): Promise<void> {
  try {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;

    const reg = await navigator.serviceWorker.ready;
    const existing = await reg.pushManager.getSubscription();
    if (existing) return; // Already subscribed

    const { public_key } = await api.get<{ public_key: string }>(
      API_ENDPOINTS.push.vapidPublicKey,
    );
    if (!public_key) return;

    const subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(public_key),
    });

    await api.post(API_ENDPOINTS.push.subscribe, {
      subscription: subscription.toJSON(),
    });
  } catch (err) {
    // Push subscribe failed — not critical, we still have SSE + Browser Notifications
    console.warn("[push] Auto-subscribe failed:", err);
  }
}
