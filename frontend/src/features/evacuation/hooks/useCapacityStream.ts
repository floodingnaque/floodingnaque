/**
 * useCapacityStream Hook
 *
 * SSE hook for real-time evacuation center capacity updates.
 * Uses ticket-based auth matching the useAlertStream pattern.
 * Dispatches CustomEvents so map-layer components can react.
 */

import { API_CONFIG } from "@/config/api.config";
import api from "@/lib/api-client";
import { captureException } from "@/lib/sentry";
import type { CapacityUpdateEvent } from "@/types";
import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Options & Return Types
// ---------------------------------------------------------------------------

interface UseCapacityStreamOptions {
  /** Whether the SSE connection should be enabled (default: true) */
  enabled?: boolean;
  /** Callback when a capacity update arrives */
  onUpdate?: (event: CapacityUpdateEvent) => void;
  /** Reconnection delay in ms (default: 5 000) */
  reconnectDelay?: number;
  /** Max reconnection attempts (default: 10) */
  maxReconnectAttempts?: number;
}

interface UseCapacityStreamReturn {
  isConnected: boolean;
  reconnect: () => void;
  disconnect: () => void;
  reconnectAttempts: number;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useCapacityStream(
  options: UseCapacityStreamOptions = {},
): UseCapacityStreamReturn {
  const {
    enabled = true,
    onUpdate,
    reconnectDelay = 5_000,
    maxReconnectAttempts = 10,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const isReconnectingRef = useRef(false);
  const onUpdateRef = useRef(onUpdate);
  // Generation counter: incremented on each createConnection call and on
  // cleanup.  After an async gap (e.g. ticket POST) the counter is re-checked
  // — if it changed, a newer connection attempt (or cleanup) has started and
  // the stale call bails out.  This prevents orphaned EventSource connections
  // that can exhaust the browser's 6-connection HTTP/1.1 limit per origin.
  const connectionIdRef = useRef(0);

  useEffect(() => {
    onUpdateRef.current = onUpdate;
  }, [onUpdate]);

  // ---- SSE URL builder ----
  const getSseUrl = useCallback(async (): Promise<string> => {
    const baseUrl = API_CONFIG.sseUrl || API_CONFIG.baseUrl;
    const streamBase = `${baseUrl}${API_CONFIG.endpoints.evacuation.capacityStream}`;

    try {
      const { ticket } = await api.post<{ ticket: string }>(
        `${API_CONFIG.endpoints.evacuation.capacityStream}/ticket`,
      );
      return `${streamBase}?ticket=${encodeURIComponent(ticket)}`;
    } catch {
      // Fallback: no ticket (dev mode, public streams, etc.)
      return streamBase;
    }
  }, []);

  // ---- Cleanup ----
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
    setIsConnected(false);
    setReconnectAttempts(0);
  }, [cleanup]);

  // ---- Reconnect with exponential back-off + jitter ----
  const scheduleReconnect = useCallback(
    (attempt: number) => {
      if (attempt >= maxReconnectAttempts) {
        isReconnectingRef.current = false;
        return;
      }
      isReconnectingRef.current = true;
      const baseDelay = Math.min(reconnectDelay * 2 ** attempt, 60_000);
      const jitteredDelay = baseDelay * (0.5 + Math.random() * 0.5);

      reconnectTimeoutRef.current = setTimeout(() => {
        isReconnectingRef.current = false;
        createConnection();
      }, jitteredDelay);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [maxReconnectAttempts, reconnectDelay],
  );

  // ---- Create EventSource ----
  const createConnection = useCallback(async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (!enabled) return;

    // Claim a connection generation — checked after every async gap
    const myId = ++connectionIdRef.current;

    try {
      const url = await getSseUrl();

      // A newer createConnection or cleanup ran while we awaited — bail out
      if (myId !== connectionIdRef.current) return;

      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        setReconnectAttempts(0);
        isReconnectingRef.current = false;
      };

      // Named event: "capacity_update"
      es.addEventListener("capacity_update", (event: MessageEvent) => {
        try {
          const data: CapacityUpdateEvent = JSON.parse(event.data);
          onUpdateRef.current?.(data);

          // Broadcast a CustomEvent so map components can update in real-time
          window.dispatchEvent(
            new CustomEvent("evacuation_capacity", { detail: data }),
          );
        } catch (err) {
          captureException(err, { context: "SSE capacity_update parse" });
        }
      });

      // Heartbeat keep-alive
      es.addEventListener("heartbeat", () => {
        /* keep alive — no-op */
      });

      // Error → reconnect
      es.onerror = () => {
        setIsConnected(false);
        es.close();
        eventSourceRef.current = null;

        setReconnectAttempts((prev) => {
          const next = prev + 1;
          scheduleReconnect(next);
          return next;
        });
      };
    } catch (error) {
      if (myId !== connectionIdRef.current) return;
      captureException(error, { context: "SSE capacity stream creation" });
      setReconnectAttempts((prev) => {
        const next = prev + 1;
        scheduleReconnect(next);
        return next;
      });
    }
  }, [enabled, getSseUrl, scheduleReconnect]);

  const reconnect = useCallback(() => {
    cleanup();
    setReconnectAttempts(0);
    createConnection();
  }, [cleanup, createConnection]);

  // ---- Mount / unmount ----
  useEffect(() => {
    if (enabled && !isReconnectingRef.current) {
      createConnection();
    } else if (!enabled) {
      cleanup();
    }
    return () => cleanup();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return { isConnected, reconnect, disconnect, reconnectAttempts };
}

export default useCapacityStream;
