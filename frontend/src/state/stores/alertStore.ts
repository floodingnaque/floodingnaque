/**
 * Alert Store
 *
 * Zustand store for managing real-time alerts from SSE connection.
 * Implements:
 * - Connection state machine (IDLE → CONNECTING → CONNECTED → RECONNECTING → FAILED)
 * - Circular buffer with 200-alert hard cap (Critical alerts evicted last)
 * - SSE deduplication via time-windowed ID set (60s)
 * - Derived unreadCount (computed, not stored separately)
 */

import { postTabMessage } from "@/lib/tab-sync";
import type { Alert } from "@/types";
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { useShallow } from "zustand/react/shallow";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Hard cap on live alerts in memory */
const MAX_LIVE_ALERTS = 200;
/** Number of alerts persisted to localStorage for offline fallback */
const PERSIST_LIMIT = 50;
/** Deduplication window in milliseconds */
const DEDUP_WINDOW_MS = 60_000;
/** localStorage key for persisted alert subset */
const STORAGE_KEY = "floodingnaque_alerts_cache";

// ---------------------------------------------------------------------------
// Connection state machine
// ---------------------------------------------------------------------------

export type ConnectionState =
  | "IDLE"
  | "CONNECTING"
  | "CONNECTED"
  | "RECONNECTING"
  | "FAILED";

// ---------------------------------------------------------------------------
// Dedup key helper
// ---------------------------------------------------------------------------

function dedupKey(alert: Alert): string {
  return `${alert.id}:${alert.risk_level}:${alert.triggered_at}`;
}

// ---------------------------------------------------------------------------
// Circular buffer eviction:
// When at cap, remove the oldest non-Critical alert first.
// If all are Critical, remove the oldest overall.
// ---------------------------------------------------------------------------

function evictOne(alerts: Alert[]): Alert[] {
  // Find oldest non-critical
  for (let i = alerts.length - 1; i >= 0; i--) {
    if (alerts[i]!.risk_level !== 2) {
      return [...alerts.slice(0, i), ...alerts.slice(i + 1)];
    }
  }
  // All Critical - drop the oldest
  return alerts.slice(0, -1);
}

// ---------------------------------------------------------------------------
// localStorage helpers (best-effort, never throw)
// ---------------------------------------------------------------------------

function persistAlerts(alerts: Alert[]): void {
  try {
    const subset = alerts.slice(0, PERSIST_LIMIT);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(subset));
  } catch {
    // localStorage full or unavailable - silently ignore
  }
}

function loadPersistedAlerts(): Alert[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed as Alert[];
  } catch {
    // Corrupt data - clear it
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }
  return [];
}

// ---------------------------------------------------------------------------
// Store interfaces
// ---------------------------------------------------------------------------

interface AlertState {
  /** Live alerts, newest first - hard cap at MAX_LIVE_ALERTS */
  liveAlerts: Alert[];
  /** Set of acknowledged alert IDs (used to derive unreadCount) */
  acknowledgedIds: Set<number>;
  /** Connection state machine state */
  connectionState: ConnectionState;
  /** Connection error message if any */
  connectionError: string | null;
  /** Recent dedup keys with expiry timestamps */
  _recentKeys: Map<string, number>;
}

interface AlertActions {
  addAlert: (alert: Alert) => void;
  /** Add alert without broadcasting to other tabs (prevents loop) */
  addAlertSilent: (alert: Alert) => void;
  markAllRead: () => void;
  setConnectionState: (state: ConnectionState) => void;
  setConnectionError: (error: string | null) => void;
  clearAlerts: () => void;
  removeAlert: (alertId: number) => void;
  updateAlert: (alertId: number, updates: Partial<Alert>) => void;
  /** Prune expired dedup keys (called periodically) */
  pruneDedup: () => void;
}

type AlertStore = AlertState & AlertActions;

// ---------------------------------------------------------------------------
// Backward compat: mirror isConnected for consumers that read it
// ---------------------------------------------------------------------------

// We compute isConnected + unreadCount as derived selectors below.

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

const initialState: AlertState = {
  liveAlerts: loadPersistedAlerts(),
  acknowledgedIds: new Set<number>(),
  connectionState: "IDLE" as ConnectionState,
  connectionError: null,
  _recentKeys: new Map<string, number>(),
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAlertStore = create<AlertStore>()(
  devtools(
    (set, get) => {
      // Shared alert insertion logic (used by both addAlert and addAlertSilent)
      const insertAlert = (alert: Alert) => {
        set((state) => {
          const now = Date.now();
          const key = dedupKey(alert);

          // --- Dedup check ---
          const expiry = state._recentKeys.get(key);
          if (expiry !== undefined && expiry > now) {
            return state;
          }

          const newKeys = new Map(state._recentKeys);
          newKeys.set(key, now + DEDUP_WINDOW_MS);

          // --- Existing alert update ---
          const existsIdx = state.liveAlerts.findIndex(
            (a) => a.id === alert.id,
          );
          if (existsIdx !== -1) {
            const updated = [...state.liveAlerts];
            updated[existsIdx] = alert;
            return { liveAlerts: updated, _recentKeys: newKeys };
          }

          // --- New alert: prepend + enforce cap ---
          let updated = [alert, ...state.liveAlerts];
          while (updated.length > MAX_LIVE_ALERTS) {
            updated = evictOne(updated);
          }

          persistAlerts(updated);
          return { liveAlerts: updated, _recentKeys: newKeys };
        });
      };

      return {
        ...initialState,

        addAlert: (alert: Alert) => {
          insertAlert(alert);
          // Broadcast to other tabs
          postTabMessage({ type: "NEW_ALERT", payload: alert });
        },

        addAlertSilent: (alert: Alert) => {
          // Insert without broadcasting (called from tab-sync listener)
          insertAlert(alert);
        },

        markAllRead: () => {
          set((state) => {
            const ids = new Set(state.acknowledgedIds);
            for (const a of state.liveAlerts) {
              ids.add(a.id);
            }
            // Remove acknowledged alerts from the live list and localStorage
            // so they don't resurface after page refresh or SSE reconnection
            const remaining = state.liveAlerts.filter((a) => !ids.has(a.id));
            persistAlerts(remaining);
            return { acknowledgedIds: ids, liveAlerts: remaining };
          });
        },

        setConnectionState: (connectionState: ConnectionState) => {
          set({
            connectionState,
            connectionError:
              connectionState === "CONNECTED" ? null : get().connectionError,
          });
        },

        setConnectionError: (error: string | null) => {
          set({
            connectionError: error,
            connectionState: error ? "FAILED" : get().connectionState,
          });
        },

        clearAlerts: () => {
          set({
            liveAlerts: [],
            acknowledgedIds: new Set<number>(),
            _recentKeys: new Map<string, number>(),
          });
          persistAlerts([]);
        },

        removeAlert: (alertId: number) => {
          set((state) => ({
            liveAlerts: state.liveAlerts.filter((a) => a.id !== alertId),
          }));
        },

        updateAlert: (alertId: number, updates: Partial<Alert>) => {
          set((state) => ({
            liveAlerts: state.liveAlerts.map((a) =>
              a.id === alertId ? { ...a, ...updates } : a,
            ),
          }));
        },

        pruneDedup: () => {
          const now = Date.now();
          set((state) => {
            const pruned = new Map<string, number>();
            for (const [k, v] of state._recentKeys) {
              if (v > now) pruned.set(k, v);
            }
            return { _recentKeys: pruned };
          });
        },
      };
    },
    { name: "alert-store", enabled: import.meta.env.DEV },
  ),
);

// ---------------------------------------------------------------------------
// Selector hooks
// ---------------------------------------------------------------------------

export const useLiveAlerts = () => useAlertStore((state) => state.liveAlerts);

/** Derived unread count - never stored, always computed */
export const useUnreadCount = () =>
  useAlertStore(
    (state) =>
      state.liveAlerts.filter((a) => !state.acknowledgedIds.has(a.id)).length,
  );

/** Backward-compatible boolean derived from connection state machine */
export const useIsConnected = () =>
  useAlertStore((state) => state.connectionState === "CONNECTED");

export const useConnectionState = () =>
  useAlertStore((state) => state.connectionState);

export const useAlertConnectionStatus = () =>
  useAlertStore(
    useShallow((state) => ({
      isConnected: state.connectionState === "CONNECTED",
      connectionState: state.connectionState,
      connectionError: state.connectionError,
    })),
  );

// ---------------------------------------------------------------------------
// Action hooks (stable references)
// ---------------------------------------------------------------------------

export const useAlertActions = () => {
  const addAlert = useAlertStore((state) => state.addAlert);
  const markAllRead = useAlertStore((state) => state.markAllRead);
  const setConnectionState = useAlertStore((state) => state.setConnectionState);
  const setConnectionError = useAlertStore((state) => state.setConnectionError);
  const clearAlerts = useAlertStore((state) => state.clearAlerts);
  const removeAlert = useAlertStore((state) => state.removeAlert);
  const updateAlert = useAlertStore((state) => state.updateAlert);
  const pruneDedup = useAlertStore((state) => state.pruneDedup);

  return {
    addAlert,
    markAllRead,
    setConnectionState,
    setConnectionError,
    clearAlerts,
    removeAlert,
    updateAlert,
    pruneDedup,
  };
};

/** @deprecated Use setConnectionState instead */
export const useSetConnected = () => {
  const setConnectionState = useAlertStore((state) => state.setConnectionState);
  return (connected: boolean) =>
    setConnectionState(connected ? "CONNECTED" : "IDLE");
};

/**
 * Get alerts by risk level
 */
export const useAlertsByRiskLevel = (riskLevel: Alert["risk_level"]) =>
  useAlertStore((state) =>
    state.liveAlerts.filter((a) => a.risk_level === riskLevel),
  );

/**
 * Get high risk alerts count (risk_level >= 2)
 */
export const useHighRiskAlertsCount = () =>
  useAlertStore(
    (state) => state.liveAlerts.filter((a) => a.risk_level >= 2).length,
  );

export default useAlertStore;
