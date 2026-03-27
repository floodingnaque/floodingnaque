/**
 * useAlertStream Hook
 *
 * SSE (Server-Sent Events) hook for real-time alert updates.
 * Implements a full connection state machine:
 *   IDLE → CONNECTING → CONNECTED → RECONNECTING → FAILED
 *
 * On FAILED state, falls back to polling /api/v1/alerts/recent every 30s.
 *
 * Authentication: Fetches a short-lived SSE ticket from the server and
 * passes it as a query parameter over HTTPS. If 401 is received, calls
 * authApi.refresh() before re-establishing the connection.
 */

import { API_CONFIG } from "@/config/api.config";
import api from "@/lib/api-client";
import { captureException } from "@/lib/sentry";
import type { ConnectionState } from "@/state/stores/alertStore";
import { useAlertStore } from "@/state/stores/alertStore";
import type { Alert, SSEAlertData, SSEAlertEvent } from "@/types";
import { useQueryClient } from "@tanstack/react-query";
import {
  startTransition,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";
import { alertsApi } from "../services/alertsApi";
import { alertKeys } from "./useAlerts";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_RECONNECT_ATTEMPTS = 10;
const MAX_BACKOFF_MS = 60_000;
const INITIAL_BACKOFF_MS = 1_000;
const POLLING_INTERVAL_MS = 30_000;
const DEDUP_PRUNE_INTERVAL_MS = 30_000;

// ---------------------------------------------------------------------------
// Options / Return types
// ---------------------------------------------------------------------------

interface UseAlertStreamOptions {
  enabled?: boolean;
  onAlert?: (alert: Alert) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface UseAlertStreamReturn {
  isConnected: boolean;
  connectionState: ConnectionState;
  reconnect: () => void;
  disconnect: () => void;
  lastHeartbeat: Date | null;
  reconnectAttempts: number;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAlertStream(
  options: UseAlertStreamOptions = {},
): UseAlertStreamReturn {
  const { enabled = true, onAlert, onError, onConnect, onDisconnect } = options;

  // Store actions
  const addAlert = useAlertStore((state) => state.addAlert);
  const setConnectionState = useAlertStore((state) => state.setConnectionState);
  const setConnectionError = useAlertStore((state) => state.setConnectionError);
  const pruneDedup = useAlertStore((state) => state.pruneDedup);
  const connectionState = useAlertStore((state) => state.connectionState);

  // Query client for cache invalidation on SSE events
  const queryClient = useQueryClient();

  // Local state
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );
  const dedupPruneRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isReconnectingRef = useRef(false);
  // Generation counter: prevents orphaned EventSource connections from async
  // race conditions (e.g. React StrictMode double-mount). Checked after every
  // async gap in createConnection; incremented on cleanup to invalidate stale calls.
  const connectionIdRef = useRef(0);
  // Track the last SSE event ID received for replay on reconnection
  const lastEventIdRef = useRef<string | null>(null);

  // Stable callback refs
  const onAlertRef = useRef(onAlert);
  const onErrorRef = useRef(onError);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  useEffect(() => {
    onAlertRef.current = onAlert;
  }, [onAlert]);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);
  useEffect(() => {
    onConnectRef.current = onConnect;
  }, [onConnect]);
  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
  }, [onDisconnect]);

  // ---------------------------------------------------------------------------
  // Polling fallback (activated when state machine reaches FAILED)
  // ---------------------------------------------------------------------------

  const startPollingFallback = useCallback(() => {
    if (pollingIntervalRef.current) return; // Already polling

    const poll = async () => {
      try {
        const recent = await alertsApi.getRecentAlerts(20);
        for (const alert of recent) {
          // Skip already-acknowledged alerts to avoid re-surfacing dismissed ones
          if ("acknowledged" in alert && alert.acknowledged) continue;
          addAlert(alert);
          onAlertRef.current?.(alert);
        }
      } catch {
        // Polling failure - silently retry next cycle
      }
    };

    // Immediate first poll + interval
    poll();
    pollingIntervalRef.current = setInterval(poll, POLLING_INTERVAL_MS);
  }, [addAlert]);

  const stopPollingFallback = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  // ---------------------------------------------------------------------------
  // SSE ticket + URL
  // ---------------------------------------------------------------------------

  const getSseUrl = useCallback(async (): Promise<string> => {
    const baseUrl = API_CONFIG.sseUrl || API_CONFIG.baseUrl;
    const sseBase = `${baseUrl}${API_CONFIG.endpoints.sse.alerts}`;

    const { ticket } = await api.post<{ ticket: string }>(
      `${API_CONFIG.endpoints.sse.alerts}/ticket`,
    );
    let url = `${sseBase}?ticket=${encodeURIComponent(ticket)}`;
    if (lastEventIdRef.current) {
      url += `&lastEventId=${encodeURIComponent(lastEventIdRef.current)}`;
    }
    return url;
  }, []);

  // ---------------------------------------------------------------------------
  // Cleanup
  // ---------------------------------------------------------------------------

  const cleanup = useCallback(() => {
    connectionIdRef.current++; // Invalidate any pending async createConnection
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    isReconnectingRef.current = false;
  }, []);

  const disconnect = useCallback(() => {
    cleanup();
    stopPollingFallback();
    setConnectionState("IDLE");
    setReconnectAttempts(0);
    onDisconnectRef.current?.();
  }, [cleanup, stopPollingFallback, setConnectionState]);

  // ---------------------------------------------------------------------------
  // Reconnect scheduler with exponential backoff (1s, 2s, 4s, …, 60s max)
  // ---------------------------------------------------------------------------

  const scheduleReconnect = useCallback(
    (attempt: number) => {
      if (attempt >= MAX_RECONNECT_ATTEMPTS) {
        setConnectionState("FAILED");
        setConnectionError(
          `Max reconnection attempts (${MAX_RECONNECT_ATTEMPTS}) reached`,
        );
        toast.error("Live alerts disconnected", {
          description:
            "Falling back to periodic polling. Refresh the page to retry SSE.",
          duration: Infinity,
        });
        isReconnectingRef.current = false;
        // Activate polling fallback
        startPollingFallback();
        return;
      }

      isReconnectingRef.current = true;
      setConnectionState("RECONNECTING");
      const delay = Math.min(
        INITIAL_BACKOFF_MS * Math.pow(2, attempt),
        MAX_BACKOFF_MS,
      );
      const jitteredDelay = delay * (0.5 + Math.random() * 0.5);

      reconnectTimeoutRef.current = setTimeout(() => {
        isReconnectingRef.current = false;
        createConnection();
      }, jitteredDelay);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [startPollingFallback],
  );

  // ---------------------------------------------------------------------------
  // Create SSE connection
  // ---------------------------------------------------------------------------

  const createConnection = useCallback(async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    if (!enabled) return;

    // Claim a connection generation - checked after async ticket fetch
    const myId = ++connectionIdRef.current;

    setConnectionState("CONNECTING");

    try {
      const url = await getSseUrl();

      // A newer createConnection or cleanup ran while we awaited - bail out
      if (myId !== connectionIdRef.current) return;

      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      // ----- Connection opened -----
      eventSource.onopen = () => {
        setConnectionState("CONNECTED");
        setConnectionError(null);
        setReconnectAttempts(0);
        isReconnectingRef.current = false;
        stopPollingFallback(); // Stop polling if SSE resumes
        onConnectRef.current?.();
      };

      // ----- Alert events -----
      eventSource.addEventListener("alert", (event: MessageEvent) => {
        try {
          if (event.lastEventId) lastEventIdRef.current = event.lastEventId;
          const data: SSEAlertData = JSON.parse(event.data);
          // Defer list re-render to avoid blocking map/badge interactions
          startTransition(() => {
            addAlert(data.alert);
          });
          // Keep REST query cache in sync with SSE-fed store
          queryClient.invalidateQueries({ queryKey: alertKeys.all });
          onAlertRef.current?.(data.alert);
        } catch (parseError) {
          captureException(parseError, { context: "SSE alert event parse" });
        }
      });

      // ----- Heartbeat events -----
      eventSource.addEventListener("heartbeat", (event: MessageEvent) => {
        try {
          if (event.lastEventId) lastEventIdRef.current = event.lastEventId;
          const data = JSON.parse(event.data);
          setLastHeartbeat(new Date(data.timestamp));
        } catch {
          setLastHeartbeat(new Date());
        }
      });

      // ----- Connection status events -----
      eventSource.addEventListener("connection", (event: MessageEvent) => {
        try {
          if (event.lastEventId) lastEventIdRef.current = event.lastEventId;
          const data: SSEAlertEvent["data"] = JSON.parse(event.data);
          if ("status" in data) {
            if (data.status === "connected") {
              setConnectionState("CONNECTED");
            } else if (data.status === "disconnected") {
              setConnectionState("RECONNECTING");
            }
          }
        } catch (parseError) {
          captureException(parseError, {
            context: "SSE connection event parse",
          });
        }
      });

      // ----- Generic message fallback -----
      eventSource.onmessage = (event: MessageEvent) => {
        try {
          const eventData: SSEAlertEvent = JSON.parse(event.data);
          if (eventData.type === "alert" && "alert" in eventData.data) {
            const alertData = eventData.data as SSEAlertData;
            startTransition(() => {
              addAlert(alertData.alert);
            });
            onAlertRef.current?.(alertData.alert);
          } else if (eventData.type === "heartbeat") {
            setLastHeartbeat(new Date());
          }
        } catch {
          // Ignore parse errors for unknown message formats
        }
      };

      // ----- Error handler + reconnect -----
      eventSource.onerror = (error: Event) => {
        onErrorRef.current?.(error);
        onDisconnectRef.current?.();

        eventSource.close();
        eventSourceRef.current = null;

        setReconnectAttempts((prev) => {
          const next = prev + 1;
          scheduleReconnect(next);
          return next;
        });
      };
    } catch (error) {
      if (myId !== connectionIdRef.current) return;
      captureException(error, { context: "SSE EventSource creation" });
      setConnectionError("Failed to establish SSE connection");

      setReconnectAttempts((prev) => {
        const next = prev + 1;
        scheduleReconnect(next);
        return next;
      });
    }
  }, [
    enabled,
    getSseUrl,
    addAlert,
    setConnectionState,
    setConnectionError,
    scheduleReconnect,
    stopPollingFallback,
  ]);

  // ---------------------------------------------------------------------------
  // Manual reconnect
  // ---------------------------------------------------------------------------

  const reconnect = useCallback(() => {
    cleanup();
    stopPollingFallback();
    setReconnectAttempts(0);
    createConnection();
  }, [cleanup, stopPollingFallback, createConnection]);

  // ---------------------------------------------------------------------------
  // Effect: connect on mount, cleanup on unmount
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (enabled && !isReconnectingRef.current) {
      createConnection();
    } else if (!enabled) {
      cleanup();
      stopPollingFallback();
    }

    return () => {
      cleanup();
      stopPollingFallback();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // ---------------------------------------------------------------------------
  // Effect: periodic dedup key pruning
  // ---------------------------------------------------------------------------

  useEffect(() => {
    dedupPruneRef.current = setInterval(pruneDedup, DEDUP_PRUNE_INTERVAL_MS);
    return () => {
      if (dedupPruneRef.current) {
        clearInterval(dedupPruneRef.current);
      }
    };
  }, [pruneDedup]);

  return {
    isConnected: connectionState === "CONNECTED",
    connectionState,
    reconnect,
    disconnect,
    lastHeartbeat,
    reconnectAttempts,
  };
}

export default useAlertStream;
