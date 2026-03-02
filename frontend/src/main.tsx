/**
 * Application Entry Point
 *
 * Initializes the React application with routing, providers, and
 * production monitoring (Sentry).
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { initSentry } from '@/lib/sentry';
import { injectSpeedInsights } from '@vercel/speed-insights';
import { registerSW } from 'virtual:pwa-register';
import { Providers } from '@/providers';
import App from './App';

// Global styles
import './index.css';

// Initialize Sentry before rendering (no-op when DSN is empty)
initSentry();

// Initialize Vercel Speed Insights
injectSpeedInsights();

// Register PWA service worker (auto-update when new SW is available)
registerSW({ immediate: true });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Providers>
        <App />
      </Providers>
    </BrowserRouter>
  </StrictMode>
);
