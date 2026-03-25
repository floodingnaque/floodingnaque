import { useCallback, useEffect, useState } from "react";

import { API_ENDPOINTS } from "@/config/api.config";
import { api } from "@/lib/api-client";

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

export function usePushNotifications() {
  const [permission, setPermission] = useState<NotificationPermission>(() =>
    typeof window !== "undefined" && "Notification" in window
      ? Notification.permission
      : "default",
  );
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isSubscribing, setIsSubscribing] = useState(false);

  const isSupported =
    typeof window !== "undefined" &&
    "Notification" in window &&
    "serviceWorker" in navigator &&
    "PushManager" in window;

  useEffect(() => {
    if (!isSupported) return;

    navigator.serviceWorker.ready
      .then((reg) => reg.pushManager.getSubscription())
      .then((sub) => setIsSubscribed(!!sub))
      .catch(() => {});
  }, [isSupported]);

  const subscribe = useCallback(async () => {
    if (!isSupported) return false;

    setIsSubscribing(true);
    try {
      const perm = await Notification.requestPermission();
      setPermission(perm);
      if (perm !== "granted") return false;

      const { public_key } = await api.get<{ public_key: string }>(
        API_ENDPOINTS.push.vapidPublicKey,
      );

      const reg = await navigator.serviceWorker.ready;
      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      });

      await api.post(API_ENDPOINTS.push.subscribe, {
        subscription: subscription.toJSON(),
      });

      setIsSubscribed(true);
      return true;
    } catch (error) {
      console.error("Push subscription failed:", error);
      return false;
    } finally {
      setIsSubscribing(false);
    }
  }, [isSupported]);

  const unsubscribe = useCallback(async () => {
    setIsSubscribing(true);
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await api.delete(API_ENDPOINTS.push.unsubscribe, {
          data: { endpoint: sub.endpoint },
        });
        await sub.unsubscribe();
        setIsSubscribed(false);
      }
    } catch (error) {
      console.error("Push unsubscribe failed:", error);
    } finally {
      setIsSubscribing(false);
    }
  }, []);

  return {
    isSupported,
    isSubscribed,
    isSubscribing,
    permission,
    subscribe,
    unsubscribe,
  };
}
