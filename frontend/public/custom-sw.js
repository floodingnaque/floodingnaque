/**
 * Custom Service Worker - Push Notification Handler
 *
 * This file is loaded by the Workbox-generated SW via importScripts.
 * Handles push events and notification click actions.
 */

// @ts-nocheck — runs in SW context, not module scope

self.addEventListener("push", function (event) {
  if (!event.data) return;

  let payload;
  try {
    payload = event.data.json();
  } catch {
    payload = { title: "Flood Alert", body: event.data.text() };
  }

  const riskLevel = payload.risk_level ?? 1;
  const isCritical = riskLevel === 2;

  const title = isCritical
    ? "CRITICAL FLOOD ALERT \u2014 Parañaque City"
    : "Flood Alert \u2014 Parañaque City";

  const options = {
    body:
      payload.body || payload.message || "A new flood alert has been issued.",
    icon: "/icons/icon-192x192.png",
    badge: "/icons/icon-72x72.png",
    tag: isCritical ? "critical-alert" : "alert-" + (payload.id || Date.now()),
    renotify: isCritical,
    requireInteraction: isCritical,
    vibrate: isCritical ? [200, 100, 200, 100, 200] : [200],
    data: {
      url: payload.url || "/alerts",
      id: payload.id,
    },
    actions: [
      { action: "view-map", title: "View Map" },
      { action: "dismiss", title: "Dismiss" },
    ],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();

  if (event.action === "dismiss") return;

  const url = event.notification.data?.url || "/alerts";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then(function (clientList) {
        // Focus existing tab if found
        for (var i = 0; i < clientList.length; i++) {
          var client = clientList[i];
          if (client.url.includes(self.location.origin) && "focus" in client) {
            client.navigate(url);
            return client.focus();
          }
        }
        // Open new tab
        return self.clients.openWindow(url);
      }),
  );
});
