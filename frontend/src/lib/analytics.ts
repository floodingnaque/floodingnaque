import { track } from "@vercel/analytics";

/**
 * Track a flood-specific analytics event with environment context.
 */
export function trackFloodEvent(event: string, data?: Record<string, unknown>) {
  track(event, {
    ...data,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT ?? "development",
  });
}
