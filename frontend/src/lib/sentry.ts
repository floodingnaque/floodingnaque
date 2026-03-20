/**
 * Sentry Error Monitoring
 *
 * Initialises Sentry for production error tracking with:
 * - Flood-specific context (alert count, SSE state) in beforeSend
 * - Session replay for reproducing user-reported issues
 * - Performance monitoring spans for key operations
 *
 * Only activates when VITE_SENTRY_DSN is set - safe to import
 * unconditionally in main.tsx.
 *
 * @example
 * ```ts
 * import { initSentry } from '@/lib/sentry';
 * initSentry(); // call once before React renders
 * ```
 */

import * as Sentry from "@sentry/react";

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
      (import.meta.env.VITE_SENTRY_ENVIRONMENT as string) || "production",

    // Capture 10 % of transactions in production to limit quota usage
    tracesSampleRate: 0.1,

    // Session Replay: capture 10% of sessions, 100% on error
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,

    integrations: [
      Sentry.replayIntegration({
        // Mask all text and block all media for privacy
        maskAllText: false,
        blockAllMedia: false,
      }),
      Sentry.browserTracingIntegration(),
    ],

    // Only send errors from our own code
    allowUrls: [window.location.origin],

    // Ignore common benign errors
    ignoreErrors: ["ResizeObserver loop", "Non-Error promise rejection"],

    // Enrich events with flood-system context before sending
    beforeSend(event, hint) {
      const error = hint?.originalException;
      if (
        error instanceof Error &&
        /Network Error|Failed to fetch|Load failed|ERR_NETWORK/i.test(
          error.message,
        )
      ) {
        // Drop transient connectivity errors - they overwhelm Sentry and
        // are not actionable.
        return null;
      }

      // Attach flood-specific context for debugging monsoon-season incidents
      event.contexts = {
        ...event.contexts,
        flood_system: {
          url: window.location.pathname,
          online: navigator.onLine,
          viewport: `${window.innerWidth}x${window.innerHeight}`,
        },
      };

      return event;
    },

    // Attach release tag so errors can be matched to deploys
    release: import.meta.env.VITE_APP_VERSION as string | undefined,
  });
}

/**
 * Add a breadcrumb for SSE state transitions.
 * Call this from the alert stream hook on connect/disconnect/error.
 */
export function addSSEBreadcrumb(
  state: string,
  data?: Record<string, unknown>,
): void {
  if (!DSN) return;
  Sentry.addBreadcrumb({
    category: "sse",
    message: `SSE ${state}`,
    level: state === "error" ? "error" : "info",
    data,
  });
}

/**
 * Set the current user context for Sentry events.
 */
export function setSentryUser(
  user: {
    id: string | number;
    email?: string;
    role?: string;
  } | null,
): void {
  if (!DSN) return;
  if (user) {
    Sentry.setUser({ id: String(user.id), email: user.email, role: user.role });
  } else {
    Sentry.setUser(null);
  }
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

/**
 * Start a custom performance span for measuring key operations.
 * Returns a callback to finish the span.
 *
 * @example
 * ```ts
 * const finish = startSpan('predict', 'Flood prediction request');
 * await api.predict(data);
 * finish();
 * ```
 */
export function startSpan(op: string, description: string): () => void {
  if (!DSN) return () => {};

  const span = Sentry.startInactiveSpan({ name: description, op });
  return () => span?.end();
}

export { Sentry };
