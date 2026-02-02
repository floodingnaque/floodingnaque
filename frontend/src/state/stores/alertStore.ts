/**
 * Alert Store
 * 
 * Zustand store for managing real-time alerts from SSE connection.
 * Not persisted - alerts are ephemeral and fetched fresh on connection.
 */

import { create } from 'zustand';
import type { Alert } from '@/types';

/**
 * Maximum number of live alerts to keep in memory
 */
const MAX_LIVE_ALERTS = 50;

/**
 * Alert store state interface
 */
interface AlertState {
  /** List of live alerts, newest first */
  liveAlerts: Alert[];
  /** Count of unread alerts */
  unreadCount: number;
  /** Whether SSE connection is active */
  isConnected: boolean;
  /** Connection error message if any */
  connectionError: string | null;
}

/**
 * Alert store actions interface
 */
interface AlertActions {
  /** Add a new alert to the list */
  addAlert: (alert: Alert) => void;
  /** Mark all alerts as read */
  markAllRead: () => void;
  /** Set connection status */
  setConnected: (connected: boolean) => void;
  /** Set connection error */
  setConnectionError: (error: string | null) => void;
  /** Clear all alerts */
  clearAlerts: () => void;
  /** Remove a specific alert by ID */
  removeAlert: (alertId: number) => void;
  /** Update an existing alert */
  updateAlert: (alertId: number, updates: Partial<Alert>) => void;
}

/**
 * Combined alert store type
 */
type AlertStore = AlertState & AlertActions;

/**
 * Initial state
 */
const initialState: AlertState = {
  liveAlerts: [],
  unreadCount: 0,
  isConnected: false,
  connectionError: null,
};

/**
 * Alert store (no persistence)
 */
export const useAlertStore = create<AlertStore>()((set, get) => ({
  ...initialState,

  addAlert: (alert: Alert) => {
    set((state) => {
      // Check if alert already exists (by ID)
      const exists = state.liveAlerts.some((a) => a.id === alert.id);
      if (exists) {
        // Update existing alert
        return {
          liveAlerts: state.liveAlerts.map((a) =>
            a.id === alert.id ? alert : a
          ),
        };
      }

      // Add new alert at the beginning, maintain max limit
      const updatedAlerts = [alert, ...state.liveAlerts].slice(0, MAX_LIVE_ALERTS);
      
      return {
        liveAlerts: updatedAlerts,
        unreadCount: state.unreadCount + 1,
      };
    });
  },

  markAllRead: () => {
    set({ unreadCount: 0 });
  },

  setConnected: (connected: boolean) => {
    set({ 
      isConnected: connected,
      // Clear error when successfully connected
      connectionError: connected ? null : get().connectionError,
    });
  },

  setConnectionError: (error: string | null) => {
    set({ 
      connectionError: error,
      isConnected: error ? false : get().isConnected,
    });
  },

  clearAlerts: () => {
    set({
      liveAlerts: [],
      unreadCount: 0,
    });
  },

  removeAlert: (alertId: number) => {
    set((state) => ({
      liveAlerts: state.liveAlerts.filter((a) => a.id !== alertId),
    }));
  },

  updateAlert: (alertId: number, updates: Partial<Alert>) => {
    set((state) => ({
      liveAlerts: state.liveAlerts.map((a) =>
        a.id === alertId ? { ...a, ...updates } : a
      ),
    }));
  },
}));

/**
 * Selector hooks for common alert state
 */
export const useLiveAlerts = () => useAlertStore((state) => state.liveAlerts);
export const useUnreadCount = () => useAlertStore((state) => state.unreadCount);
export const useAlertConnectionStatus = () =>
  useAlertStore((state) => ({
    isConnected: state.isConnected,
    connectionError: state.connectionError,
  }));

/**
 * Action hooks
 */
export const useAlertActions = () =>
  useAlertStore((state) => ({
    addAlert: state.addAlert,
    markAllRead: state.markAllRead,
    setConnected: state.setConnected,
    setConnectionError: state.setConnectionError,
    clearAlerts: state.clearAlerts,
    removeAlert: state.removeAlert,
    updateAlert: state.updateAlert,
  }));

/**
 * Get alerts by risk level
 */
export const useAlertsByRiskLevel = (riskLevel: Alert['risk_level']) =>
  useAlertStore((state) =>
    state.liveAlerts.filter((a) => a.risk_level === riskLevel)
  );

/**
 * Get high risk alerts count (risk_level >= 2)
 */
export const useHighRiskAlertsCount = () =>
  useAlertStore(
    (state) => state.liveAlerts.filter((a) => a.risk_level >= 2).length
  );

export default useAlertStore;
