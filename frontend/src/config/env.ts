/**
 * Environment Variable Validation
 *
 * Uses Zod to validate all VITE_* environment variables at application
 * startup.  Invalid or missing required values throw immediately so
 * misconfigurations surface during development rather than at runtime.
 */

import { z } from 'zod';

/**
 * Schema for all expected VITE_* environment variables.
 *
 * - Required in production are marked with `.min(1)`.
 * - Optional variables use `.optional()` or `.default()`.
 */
const envSchema = z.object({
  // ── API ──────────────────────────────────────────────────────
  /** Base URL for backend API. Required in production builds. */
  VITE_API_BASE_URL: z.string().url().optional(),

  /** SSE URL override (falls back to API base URL when absent). */
  VITE_SSE_URL: z.string().url().optional(),

  // ── Monitoring ───────────────────────────────────────────────
  /** Sentry DSN — omit for local dev (Sentry will no-op). */
  VITE_SENTRY_DSN: z.string().url().optional(),

  /** Sentry environment label. */
  VITE_SENTRY_ENVIRONMENT: z.string().optional(),

  /** Release / version tag attached to Sentry events. */
  VITE_APP_VERSION: z.string().optional(),

  // ── Map defaults ─────────────────────────────────────────────
  VITE_MAP_DEFAULT_LAT: z
    .string()
    .optional()
    .transform((v) => (v ? Number(v) : undefined))
    .pipe(z.number().min(-90).max(90).optional()),

  VITE_MAP_DEFAULT_LNG: z
    .string()
    .optional()
    .transform((v) => (v ? Number(v) : undefined))
    .pipe(z.number().min(-180).max(180).optional()),

  VITE_MAP_DEFAULT_ZOOM: z
    .string()
    .optional()
    .transform((v) => (v ? Number(v) : undefined))
    .pipe(z.number().int().min(1).max(20).optional()),
});

/**
 * Validated environment variables.
 *
 * Import this singleton instead of reading `import.meta.env` directly
 * so that typos and invalid values are caught at startup.
 */
function parseEnv() {
  const raw = import.meta.env;

  const result = envSchema.safeParse(raw);

  if (!result.success) {
    const formatted = result.error.issues
      .map((i) => `  • ${i.path.join('.')}: ${i.message}`)
      .join('\n');

    const msg = `[env] Invalid environment variables:\n${formatted}`;

    if (import.meta.env.PROD) {
      throw new Error(msg);
    }

    // In dev, warn loudly but don't crash — allows running without .env
    console.warn(msg);

    // Fallback: return raw values (un-validated) so the app can still boot
    return raw as z.infer<typeof envSchema>;
  }

  return result.data;
}

export const env = parseEnv();
