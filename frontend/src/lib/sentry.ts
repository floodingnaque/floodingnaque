/**
 * Sentry Error Monitoring
 *
 * Initialises Sentry for production error tracking.
 * Only activates when VITE_SENTRY_DSN is set — safe to import
 * unconditionally in main.tsx.
 *
 * @example
 * ```ts
 * import { initSentry } from '@/lib/sentry';
 * initSentry(); // call once before React renders
 * ```
 */

import * as Sentry from '@sentry/react';

const DSN = import.meta.env.VITE_SENTRY_DSN as string | undefined;

/**
 * Initialise Sentry.  No-ops when the DSN env var is empty/missing
 * so the app works identically in development without Sentry installed.
 */
export function initSentry(): void {
  if (!DSN) {
    return;
  }

  Sentry.init({
    dsn: DSN,
    environment:
      (import.meta.env.VITE_SENTRY_ENVIRONMENT as string) || 'production',

    // Capture 10 % of transactions in production to limit quota usage
    tracesSampleRate: 0.1,

    // Only send errors from our own code
    allowUrls: [window.location.origin],

    // Ignore common benign errors
    ignoreErrors: [
      'ResizeObserver loop',
      'Non-Error promise rejection',
      'Network Error',
    ],

    // Attach release tag so errors can be matched to deploys
    release: import.meta.env.VITE_APP_VERSION as string | undefined,
  });
}

/**
 * Manually capture an exception (e.g. inside an ErrorBoundary).
 * Safe to call even when Sentry is not initialised.
 */
export function captureException(
  error: unknown,
  context?: Record<string, unknown>,
): void {
  if (!DSN) {
    return;
  }

  Sentry.captureException(error, {
    extra: context,
  });
}

export { Sentry };
