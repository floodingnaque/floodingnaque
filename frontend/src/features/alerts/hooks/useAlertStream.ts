/**
 * useAlertStream Hook
 *
 * SSE (Server-Sent Events) hook for real-time alert updates.
 * Manages EventSource connection with automatic reconnection.
 *
 * Authentication: Because the browser's EventSource API does not
 * support custom headers, we fetch a short-lived ticket from the
 * server and pass it as a query parameter over HTTPS.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useAlertStore } from '@/state/stores/alertStore';
import { API_CONFIG } from '@/config/api.config';
import api from '@/lib/api-client';
import { captureException } from '@/lib/sentry';
import type { Alert, SSEAlertEvent, SSEAlertData } from '@/types';

/**
 * Options for the useAlertStream hook
 */
interface UseAlertStreamOptions {
  /** Whether the SSE connection should be enabled (default: true) */
  enabled?: boolean;
  /** Callback when a new alert is received */
  onAlert?: (alert: Alert) => void;
  /** Callback when a connection error occurs */
  onError?: (error: Event) => void;
  /** Callback when connection is established */
  onConnect?: () => void;
  /** Callback when connection is lost */
  onDisconnect?: () => void;
  /** Reconnection delay in milliseconds (default: 5000) */
  reconnectDelay?: number;
  /** Maximum reconnection attempts (default: 10) */
  maxReconnectAttempts?: number;
}

/**
 * Return type for the useAlertStream hook
 */
interface UseAlertStreamReturn {
  /** Whether the SSE connection is currently active */
  isConnected: boolean;
  /** Manual reconnect function */
  reconnect: () => void;
  /** Manual disconnect function */
  disconnect: () => void;
  /** Last heartbeat timestamp */
  lastHeartbeat: Date | null;
  /** Number of reconnection attempts */
  reconnectAttempts: number;
}

/**
 * useAlertStream hook for real-time alert updates via SSE
 *
 * @param options - Configuration options for the SSE connection
 * @returns Connection state and control functions
 *
 * @example
 * const { isConnected, reconnect } = useAlertStream({
 *   enabled: true,
 *   onAlert: (alert) => console.log('New alert:', alert),
 * });
 */
export function useAlertStream(
  options: UseAlertStreamOptions = {}
): UseAlertStreamReturn {
  const {
    enabled = true,
    onAlert,
    onError,
    onConnect,
    onDisconnect,
    reconnectDelay = 5000,
    maxReconnectAttempts = 10,
  } = options;

  // Store actions
  const addAlert = useAlertStore((state) => state.addAlert);
  const setConnected = useAlertStore((state) => state.setConnected);
  const setConnectionError = useAlertStore((state) => state.setConnectionError);
  const isConnected = useAlertStore((state) => state.isConnected);

  // Local state
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [shouldReconnect, setShouldReconnect] = useState(false);

  // Refs for managing connection
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * Fetch a short-lived SSE ticket from the server and build the
   * SSE endpoint URL with the ticket as a query parameter.
   *
   * The ticket is a single-use, time-limited token that the SSE
   * endpoint validates in lieu of an Authorization header.
   */
  const getSseUrl = useCallback(async (): Promise<string> => {
    const baseUrl = API_CONFIG.sseUrl || API_CONFIG.baseUrl;
    const sseBase = `${baseUrl}${API_CONFIG.endpoints.sse.alerts}`;

    // Obtain a short-lived ticket (authenticated via httpOnly cookie)
    const { ticket } = await api.post<{ ticket: string }>(
      `${API_CONFIG.endpoints.sse.alerts}/ticket`,
    );
    return `${sseBase}?ticket=${encodeURIComponent(ticket)}`;
  }, []);

  /**
   * Clean up the EventSource connection
   */
  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  /**
   * Disconnect from SSE stream
   */
  const disconnect = useCallback(() => {
    cleanup();
    setConnected(false);
    setReconnectAttempts(0);
    setShouldReconnect(false);
    onDisconnect?.();
  }, [cleanup, setConnected, onDisconnect]);

  /**
   * Create and configure EventSource connection
   */
  const createConnection = useCallback(async () => {
    // Clean up any existing connection
    cleanup();

    if (!enabled) {
      return;
    }

    try {
      const url = await getSseUrl();
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      // Connection opened
      eventSource.onopen = () => {
        setConnected(true);
        setConnectionError(null);
        setReconnectAttempts(0);
        setShouldReconnect(false);
        onConnect?.();
      };

      // Handle alert events
      eventSource.addEventListener('alert', (event: MessageEvent) => {
        try {
          const data: SSEAlertData = JSON.parse(event.data);
          addAlert(data.alert);
          onAlert?.(data.alert);
        } catch (parseError) {
          captureException(parseError, { context: 'SSE alert event parse' });
        }
      });

      // Handle heartbeat events
      eventSource.addEventListener('heartbeat', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          setLastHeartbeat(new Date(data.timestamp));
        } catch {
          setLastHeartbeat(new Date());
        }
      });

      // Handle connection events
      eventSource.addEventListener('connection', (event: MessageEvent) => {
        try {
          const data: SSEAlertEvent['data'] = JSON.parse(event.data);
          if ('status' in data) {
            if (data.status === 'connected') {
              setConnected(true);
            } else if (data.status === 'disconnected') {
              setConnected(false);
            }
          }
        } catch (parseError) {
          captureException(parseError, { context: 'SSE connection event parse' });
        }
      });

      // Handle generic messages (fallback)
      eventSource.onmessage = (event: MessageEvent) => {
        try {
          const eventData: SSEAlertEvent = JSON.parse(event.data);

          if (eventData.type === 'alert' && 'alert' in eventData.data) {
            addAlert(eventData.data.alert);
            onAlert?.(eventData.data.alert);
          } else if (eventData.type === 'heartbeat') {
            setLastHeartbeat(new Date());
          }
        } catch {
          // Ignore parse errors for unknown message formats
        }
      };

      // Handle errors and reconnection
      eventSource.onerror = (error: Event) => {
        setConnected(false);
        setConnectionError('SSE connection error');
        onError?.(error);
        onDisconnect?.();

        // Close the errored connection
        eventSource.close();
        eventSourceRef.current = null;

        // Signal that we should reconnect
        setReconnectAttempts((prev) => {
          const newAttempts = prev + 1;
          if (newAttempts < maxReconnectAttempts && enabled) {
            setShouldReconnect(true);
          } else if (newAttempts >= maxReconnectAttempts) {
            setConnectionError(
              `Max reconnection attempts (${maxReconnectAttempts}) reached`
            );
          }
          return newAttempts;
        });
      };
    } catch (error) {
      captureException(error, { context: 'SSE EventSource creation' });
      setConnectionError('Failed to establish SSE connection');
    }
  }, [
    enabled,
    getSseUrl,
    cleanup,
    addAlert,
    setConnected,
    setConnectionError,
    onAlert,
    onError,
    onConnect,
    onDisconnect,
    maxReconnectAttempts,
  ]);

  /**
   * Manual reconnect function
   */
  const reconnect = useCallback(() => {
    setReconnectAttempts(0);
    setShouldReconnect(false);
    createConnection();
  }, [createConnection]);

  // Handle initial connection and enabled changes
  useEffect(() => {
    if (enabled) {
      createConnection();
    } else {
      // Clean up without calling disconnect to avoid setState warnings
      cleanup();
    }

    return () => {
      cleanup();
    };
  }, [enabled, createConnection, cleanup]);

  // Handle reconnection with delay
  useEffect(() => {
    if (shouldReconnect && reconnectAttempts > 0 && enabled) {
      reconnectTimeoutRef.current = setTimeout(() => {
        setShouldReconnect(false);
        createConnection();
      }, reconnectDelay);

      return () => {
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
      };
    }
  }, [shouldReconnect, reconnectAttempts, enabled, reconnectDelay, createConnection]);

  return {
    isConnected,
    reconnect,
    disconnect,
    lastHeartbeat,
    reconnectAttempts,
  };
}

export default useAlertStream;
