/**
 * Custom Service Worker - Push Notification Handler
 *
 * This file is loaded by the Workbox-generated SW via importScripts.
 * Handles push events and notification click actions for flood alerts.
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
  const barangayId = payload.barangay_id;

  const title = payload.title
    ? payload.title
    : isCritical
      ? "\u{1F6A8} CRITICAL FLOOD RISK \u2014 Immediate Action Required"
      : "\u26A0\uFE0F Flood Alert \u2014 Monitor Conditions";

  const options = {
    body:
      payload.body || payload.message || "A new flood alert has been issued.",
    icon: "/icons/icon-192x192.png",
    badge: "/icons/icon-72x72.png",
    tag: "flood-alert-" + (barangayId || "citywide"),
    renotify: isCritical,
    requireInteraction: isCritical,
    vibrate: isCritical ? [200, 100, 200, 100, 200] : [200, 100, 200],
    data: {
      url: payload.url || "/dashboard",
      barangay_id: barangayId,
      risk_level: riskLevel,
    },
    actions: isCritical
      ? [
          { action: "evacuate", title: "\u{1F3C3} Find Evacuation Center" },
          { action: "dismiss", title: "Dismiss" },
        ]
      : [
          { action: "view", title: "View Status" },
          { action: "dismiss", title: "Dismiss" },
        ],
  };

  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
      // Clear cached API responses so the app fetches fresh data
      caches.open("api-cache").then(function (cache) {
        return cache.keys().then(function (keys) {
          return Promise.all(
            keys
              .filter(function (req) {
                return req.url.includes("/api/v1/");
              })
              .map(function (req) {
                return cache.delete(req);
              }),
          );
        });
      }),
    ]),
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();

  if (event.action === "dismiss") return;

  var url = event.notification.data?.url || "/dashboard";

  if (event.action === "evacuate") {
    url = "/resident/evacuation";
  } else if (event.action === "view") {
    url = "/dashboard";
  }

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
