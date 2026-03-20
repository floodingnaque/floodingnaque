/**
 * Application Entry Point
 *
 * Initializes the React application with routing, providers, and
 * production monitoring (Sentry).
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { initSentry } from "@/lib/sentry";
import { initLeaderElection } from "@/lib/tab-leader";
import { initTabSync } from "@/lib/tab-sync";
import { Providers } from "@/providers";
import { useAlertStore } from "@/state/stores/alertStore";
import { useAuthStore } from "@/state/stores/authStore";
import { inject as injectAnalytics } from "@vercel/analytics";
import { injectSpeedInsights } from "@vercel/speed-insights";
import { registerSW } from "virtual:pwa-register";
import App from "./App";

// Global styles
import "./index.css";

// Initialize Sentry before rendering (no-op when DSN is empty)
initSentry();

// Initialize Vercel Speed Insights + Analytics
injectSpeedInsights();
injectAnalytics();

// Register PWA service worker (auto-update when new SW is available)
registerSW({ immediate: true });

// Initialize cross-tab sync and leader election
initTabSync({
  addAlertSilent: (alert) => useAlertStore.getState().addAlertSilent(alert),
  clearAuthSilent: () => useAuthStore.getState().clearAuthSilent(),
  setAccessTokenSilent: (token) =>
    useAuthStore.getState().setAccessTokenSilent(token),
});
initLeaderElection();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Providers>
        <App />
      </Providers>
    </BrowserRouter>
  </StrictMode>,
);
