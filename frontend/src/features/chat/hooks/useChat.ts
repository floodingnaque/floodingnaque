/**
 * useChat - core hook for a single barangay chat channel.
 *
 * Loads history from Flask, subscribes to a Flask SSE stream for
 * live delivery of new messages, deletions, pin toggles, and typing.
 *
 * Robustness features:
 * - Reconnection gap-fill: re-fetches recent messages after a connection
 *   drop so nothing is silently missed.
 * - Retry with exponential back-off (max 30 s).
 * - Idempotent inserts: duplicates (by ID) are ignored.
 * - Last-Event-ID replay on reconnection.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { API_CONFIG } from "@/config/api.config";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/state/stores/authStore";
import type {
  ChatMessage,
  PresenceUser,
  TypingPayload,
} from "@/types/api/chat";

const TYPING_TIMEOUT_MS = 2_500;
const MAX_RETRY_DELAY_MS = 30_000;
const BASE_RETRY_DELAY_MS = 1_000;
const MAX_RECONNECT_ATTEMPTS = 15;

export function useChat(barangayId: string | null) {
  const user = useAuthStore((s) => s.user);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [onlineUsers, setOnlineUsers] = useState<PresenceUser[]>([]);
  const [typingUsers, setTypingUsers] = useState<
    { name: string; role: string }[]
  >([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const typingTimerRef = useRef<Record<string, ReturnType<typeof setTimeout>>>(
    {},
  );
  const hadConnection = useRef(false);
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const subscriptionId = useRef(0);
  const lastEventIdRef = useRef<string | null>(null);
  /** Bumped to force the SSE effect to re-run from the reconnect button. */
  const [reconnectTrigger, setReconnectTrigger] = useState(0);

  // ── Load message history from Flask API ─────────────────────────
  const loadHistory = useCallback(
    async (opts?: { since?: string }) => {
      if (!barangayId) return;
      setIsLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ limit: "50" });
        if (opts?.since) params.set("after", opts.since);
        const data = await api.get<{
          messages: ChatMessage[];
          has_more: boolean;
        }>(`/api/v1/chat/${barangayId}/messages?${params}`);
        if (opts?.since) {
          setMessages((prev) => {
            const ids = new Set(prev.map((m) => m.id));
            const fresh = data.messages.filter((m) => !ids.has(m.id));
            return [...prev, ...fresh];
          });
        } else {
          setMessages(data.messages);
        }
        setHasMore(data.has_more);
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Failed to load messages";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [barangayId],
  );

  // ── Load older messages (pagination) ────────────────────────────
  const loadOlderMessages = useCallback(async () => {
    if (!barangayId || !hasMore) return;
    const oldest = messages[0]?.created_at;
    if (!oldest) return;
    try {
      const data = await api.get<{
        messages: ChatMessage[];
        has_more: boolean;
      }>(
        `/api/v1/chat/${barangayId}/messages?limit=50&before=${encodeURIComponent(oldest)}`,
      );
      setMessages((prev) => [...data.messages, ...prev]);
      setHasMore(data.has_more);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to load older messages";
      setError(msg);
    }
  }, [barangayId, messages, hasMore]);

  // ── SSE connection ───────────────────────────────────────────────
  useEffect(() => {
    if (!barangayId || !user) return;

    const thisSubId = ++subscriptionId.current;
    const isStale = () => thisSubId !== subscriptionId.current;

    setMessages([]);
    setTypingUsers([]);
    setIsConnected(false);
    hadConnection.current = false;
    retryCount.current = 0;
    lastEventIdRef.current = null;

    loadHistory();

    let es: EventSource | null = null;

    async function connect() {
      if (isStale()) return;

      try {
        // Get SSE ticket
        const { ticket } = await api.post<{ ticket: string }>(
          `${API_CONFIG.endpoints.sse.chat}/ticket`,
        );
        if (isStale()) return;

        const baseUrl = API_CONFIG.sseUrl || API_CONFIG.baseUrl;
        let url = `${baseUrl}${API_CONFIG.endpoints.sse.chat}?channel=${encodeURIComponent(barangayId!)}&ticket=${encodeURIComponent(ticket)}`;
        if (lastEventIdRef.current) {
          url += `&lastEventId=${encodeURIComponent(lastEventIdRef.current)}`;
        }

        es = new EventSource(url);
        eventSourceRef.current = es;

        // ── connected ──
        es.addEventListener("connected", (event: MessageEvent) => {
          if (isStale()) return;
          if (hadConnection.current) {
            // Gap-fill after reconnect
            setMessages((prev) => {
              const newest = prev[prev.length - 1]?.created_at;
              if (newest) loadHistory({ since: newest });
              return prev;
            });
          }
          hadConnection.current = true;
          retryCount.current = 0;
          setIsConnected(true);
          setError(null);
          // Extract initial presence from connected event
          try {
            const data = JSON.parse(event.data);
            if (data.presence?.users) {
              setOnlineUsers(data.presence.users);
            }
          } catch {
            // ignore
          }
        });

        // ── presence ──
        es.addEventListener("presence", (event: MessageEvent) => {
          if (isStale()) return;
          try {
            const data = JSON.parse(event.data);
            if (data.users) {
              setOnlineUsers(data.users);
            }
          } catch {
            // ignore
          }
        });

        // ── new_message ──
        es.addEventListener("new_message", (event: MessageEvent) => {
          if (isStale()) return;
          if (event.lastEventId) lastEventIdRef.current = event.lastEventId;
          try {
            const data = JSON.parse(event.data);
            const msg: ChatMessage = data.message;
            setMessages((prev) => {
              if (prev.some((m) => m.id === msg.id)) return prev;
              return [...prev, msg];
            });
          } catch {
            // ignore parse errors
          }
        });

        // ── delete_message ──
        es.addEventListener("delete_message", (event: MessageEvent) => {
          if (isStale()) return;
          if (event.lastEventId) lastEventIdRef.current = event.lastEventId;
          try {
            const data = JSON.parse(event.data);
            setMessages((prev) => prev.filter((m) => m.id !== data.message_id));
          } catch {
            // ignore
          }
        });

        // ── pin_message ──
        es.addEventListener("pin_message", (event: MessageEvent) => {
          if (isStale()) return;
          if (event.lastEventId) lastEventIdRef.current = event.lastEventId;
          try {
            const data = JSON.parse(event.data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === data.message_id
                  ? { ...m, is_pinned: data.is_pinned }
                  : m,
              ),
            );
          } catch {
            // ignore
          }
        });

        // ── typing ──
        es.addEventListener("typing", (event: MessageEvent) => {
          if (isStale()) return;
          try {
            const payload: TypingPayload = JSON.parse(event.data);
            if (payload.user_id === user!.id) return;

            const entry = {
              name: payload.user_name,
              role: payload.user_role ?? "user",
            };

            setTypingUsers((prev) => {
              if (payload.is_typing) {
                return prev.some((u) => u.name === payload.user_name)
                  ? prev
                  : [...prev, entry];
              }
              return prev.filter((u) => u.name !== payload.user_name);
            });

            if (payload.is_typing) {
              clearTimeout(typingTimerRef.current[payload.user_name]);
              typingTimerRef.current[payload.user_name] = setTimeout(() => {
                if (!isStale()) {
                  setTypingUsers((prev) =>
                    prev.filter((u) => u.name !== payload.user_name),
                  );
                }
              }, TYPING_TIMEOUT_MS);
            }
          } catch {
            // ignore
          }
        });

        // ── heartbeat ──
        es.addEventListener("heartbeat", (event: MessageEvent) => {
          if (event.lastEventId) lastEventIdRef.current = event.lastEventId;
        });

        // ── error → reconnect with backoff ──
        es.onerror = () => {
          if (isStale()) return;
          setIsConnected(false);

          es?.close();
          es = null;
          eventSourceRef.current = null;

          if (retryCount.current < MAX_RECONNECT_ATTEMPTS) {
            const delay = Math.min(
              BASE_RETRY_DELAY_MS * 2 ** retryCount.current,
              MAX_RETRY_DELAY_MS,
            );
            retryCount.current++;
            retryTimer.current = setTimeout(() => {
              if (!isStale()) connect();
            }, delay);
          } else {
            setError("Connection lost. Click reconnect to try again.");
          }
        };
      } catch {
        if (isStale()) return;
        // Ticket fetch failed → retry
        if (retryCount.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            BASE_RETRY_DELAY_MS * 2 ** retryCount.current,
            MAX_RETRY_DELAY_MS,
          );
          retryCount.current++;
          retryTimer.current = setTimeout(() => {
            if (!isStale()) connect();
          }, delay);
        }
      }
    }

    connect();

    const timers = typingTimerRef.current;
    return () => {
      subscriptionId.current++;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      Object.values(timers).forEach(clearTimeout);
      if (es) es.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [barangayId, user?.id, reconnectTrigger]);

  // ── Send a message via Flask API ─────────────────────────────────
  const sendMessage = useCallback(
    async (
      content: string,
      messageType: string = "text",
      reportId?: number,
    ) => {
      if (!barangayId || !content.trim()) return;
      await api.post(`/api/v1/chat/${barangayId}/messages`, {
        content: content.trim(),
        message_type: messageType,
        report_id: reportId ?? null,
      });
    },
    [barangayId],
  );

  // ── Send typing indicator via REST → SSE broadcast ───────────────
  const sendTyping = useCallback(
    async (isTyping: boolean) => {
      if (!barangayId || !user) return;
      try {
        await api.post("/api/v1/chat/stream/typing", {
          channel: barangayId,
          is_typing: isTyping,
        });
      } catch {
        // Typing is best-effort
      }
    },
    [barangayId, user],
  );

  // ── Delete a message ─────────────────────────────────────────────
  const deleteMessage = useCallback(
    async (messageId: string) => {
      if (!barangayId) return;
      await api.delete(`/api/v1/chat/${barangayId}/messages/${messageId}`);
    },
    [barangayId],
  );

  // ── Pin/unpin a message ──────────────────────────────────────────
  const togglePin = useCallback(
    async (messageId: string) => {
      if (!barangayId) return;
      await api.patch(`/api/v1/chat/${barangayId}/messages/${messageId}/pin`);
    },
    [barangayId],
  );

  // ── Manual reconnect (exposed for UI retry button) ───────────────
  const reconnect = useCallback(() => {
    if (isConnected) return;
    retryCount.current = 0;
    setReconnectTrigger((n) => n + 1);
  }, [isConnected]);

  const pinnedMessages = messages.filter((m) => m.is_pinned);

  return {
    messages,
    pinnedMessages,
    onlineUsers,
    typingUsers,
    isConnected,
    isLoading,
    hasMore,
    error,
    sendMessage,
    sendTyping,
    deleteMessage,
    togglePin,
    loadOlderMessages,
    reconnect,
  };
}
