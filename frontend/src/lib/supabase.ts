/**
 * Supabase Client
 *
 * Used exclusively for Realtime features (community chat presence,
 * typing indicators, and postgres_changes subscriptions).
 * All CRUD still goes through the Flask API via api-client.ts.
 *
 * Auth token sync: subscribes to authStore so that when the Flask JWT
 * changes (login / refresh / logout) the Realtime connection is
 * re-authenticated. This allows Supabase RLS policies to identify the
 * user and prevents silent message drops for any role.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

/** True when the required env vars are present. */
export const isRealtimeEnabled = Boolean(supabaseUrl && supabaseAnonKey);

if (!isRealtimeEnabled) {
  console.warn(
    "[supabase] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY not set — Realtime features disabled.",
  );
}

export const supabase = createClient(supabaseUrl ?? "", supabaseAnonKey ?? "", {
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
});

// ── Auth token sync ─────────────────────────────────────────────
// Lazily subscribes to the auth store once it's available so the
// Realtime connection uses the same JWT as the Flask API.
// This is called as a side-effect on module load (deferred).

let _authSyncInitialized = false;

/**
 * Bind Supabase Realtime auth to the Zustand auth store.
 * Safe to call multiple times — only subscribes once.
 */
export function initSupabaseAuth(
  subscribe: (cb: (token: string | null) => void) => () => void,
  getToken: () => string | null,
): void {
  if (_authSyncInitialized || !isRealtimeEnabled) return;
  _authSyncInitialized = true;

  // Set initial token
  const token = getToken();
  if (token) {
    supabase.realtime.setAuth(token);
  }

  // React to future changes (login, refresh, logout)
  subscribe((newToken) => {
    if (newToken) {
      supabase.realtime.setAuth(newToken);
    } else {
      // On logout, revert to the anon key so existing
      // subscriptions gracefully downgrade instead of erroring.
      supabase.realtime.setAuth(supabaseAnonKey ?? "");
    }
  });
}
