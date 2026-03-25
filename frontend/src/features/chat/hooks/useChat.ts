/**
 * useChat — core hook for a single barangay chat channel.
 *
 * Loads history from Flask, subscribes to Supabase Realtime for
 * live INSERT/UPDATE delivery, presence tracking, and typing indicators.
 *
 * Robustness features:
 * - Reconnection gap-fill: re-fetches recent messages after a connection
 *   drop so nothing is silently missed.
 * - Retry with back-off: on CHANNEL_ERROR or TIMED_OUT, unsubscribes and
 *   re-subscribes with exponential delay (max 30 s).
 * - Idempotent inserts: duplicates (by ID) are ignored.
 * - Graceful degradation: if Supabase Realtime is unavailable the hook
 *   still provides REST-based history and send/delete/pin.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api-client";
import { isRealtimeEnabled, supabase } from "@/lib/supabase";
import { useAuthStore } from "@/state/stores/authStore";
import type {
  ChatMessage,
  PresenceUser,
  TypingPayload,
} from "@/types/api/chat";

const TYPING_TIMEOUT_MS = 2_500;
const MAX_RETRY_DELAY_MS = 30_000;
const BASE_RETRY_DELAY_MS = 1_000;

type ChannelType = ReturnType<typeof supabase.channel>;

export function useChat(barangayId: string | null) {
  const user = useAuthStore((s) => s.user);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [onlineUsers, setOnlineUsers] = useState<PresenceUser[]>([]);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  const channelRef = useRef<ChannelType | null>(null);
  const typingTimerRef = useRef<Record<string, ReturnType<typeof setTimeout>>>(
    {},
  );
  /** Tracks whether we already had a successful subscription once. */
  const hadConnection = useRef(false);
  /** Retry attempt counter for exponential back-off. */
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Guard against double-cleanup races during rapid channel switches. */
  const subscriptionId = useRef(0);

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
          // Gap-fill: merge without duplicates
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

  // ── Subscribe to Supabase Realtime ───────────────────────────────
  useEffect(() => {
    if (!barangayId || !user) return;

    // Increment subscription ID so stale callbacks from a
    // previous channel are silently ignored.
    const thisSubId = ++subscriptionId.current;
    const isStale = () => thisSubId !== subscriptionId.current;

    // Reset state for the new channel
    setMessages([]);
    setOnlineUsers([]);
    setTypingUsers([]);
    setIsConnected(false);
    hadConnection.current = false;
    retryCount.current = 0;

    loadHistory();

    if (!isRealtimeEnabled) return;

    // ── Build & subscribe channel ──────────────────────────────

    function createChannel(): ChannelType {
      const channel = supabase.channel(`chat:${barangayId}`, {
        config: {
          presence: { key: String(user!.id) },
        },
      });

      channel
        .on(
          "postgres_changes",
          {
            event: "INSERT",
            schema: "public",
            table: "chat_messages",
            filter: `barangay_id=eq.${barangayId}`,
          },
          (payload) => {
            if (isStale()) return;
            const msg = payload.new as ChatMessage;
            setMessages((prev) => {
              if (prev.some((m) => m.id === msg.id)) return prev;
              return [...prev, msg];
            });
          },
        )
        .on(
          "postgres_changes",
          {
            event: "UPDATE",
            schema: "public",
            table: "chat_messages",
            filter: `barangay_id=eq.${barangayId}`,
          },
          (payload) => {
            if (isStale()) return;
            const updated = payload.new as ChatMessage & {
              is_deleted: boolean;
            };
            if (updated.is_deleted) {
              setMessages((prev) => prev.filter((m) => m.id !== updated.id));
            } else {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === updated.id
                    ? { ...m, is_pinned: updated.is_pinned }
                    : m,
                ),
              );
            }
          },
        )
        .on(
          "broadcast",
          { event: "typing" },
          ({ payload }: { payload: TypingPayload }) => {
            if (isStale() || payload.user_id === user!.id) return;

            setTypingUsers((prev) => {
              if (payload.is_typing) {
                return prev.includes(payload.user_name)
                  ? prev
                  : [...prev, payload.user_name];
              }
              return prev.filter((n) => n !== payload.user_name);
            });

            if (payload.is_typing) {
              clearTimeout(typingTimerRef.current[payload.user_name]);
              typingTimerRef.current[payload.user_name] = setTimeout(() => {
                if (!isStale()) {
                  setTypingUsers((prev) =>
                    prev.filter((n) => n !== payload.user_name),
                  );
                }
              }, TYPING_TIMEOUT_MS);
            }
          },
        )
        .on("presence", { event: "sync" }, () => {
          if (isStale()) return;
          const state = channel.presenceState<PresenceUser>();
          const online = Object.values(state)
            .flat()
            .map((p) => {
              const raw = p as unknown as Record<string, unknown>;
              return {
                user_id: raw.user_id as number,
                user_name: raw.user_name as string,
                user_role: raw.user_role as string,
                online_at: raw.online_at as string,
              };
            });
          setOnlineUsers(online);
        })
        .subscribe(async (status) => {
          if (isStale()) return;

          if (status === "SUBSCRIBED") {
            // If we're reconnecting after a drop, fill the gap
            if (hadConnection.current) {
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
            await channel.track({
              user_id: user!.id,
              user_name: user!.name,
              user_role: user!.role,
              online_at: new Date().toISOString(),
            });
          } else if (
            status === "CLOSED" ||
            status === "CHANNEL_ERROR" ||
            status === "TIMED_OUT"
          ) {
            setIsConnected(false);
            // Retry with exponential back-off
            if (!isStale()) {
              const delay = Math.min(
                BASE_RETRY_DELAY_MS * 2 ** retryCount.current,
                MAX_RETRY_DELAY_MS,
              );
              retryCount.current++;
              retryTimer.current = setTimeout(() => {
                if (isStale()) return;
                channel.unsubscribe().then(() => {
                  if (isStale()) return;
                  const next = createChannel();
                  channelRef.current = next;
                });
              }, delay);
            }
          }
        });

      return channel;
    }

    const channel = createChannel();
    channelRef.current = channel;

    // ── Cleanup ──────────────────────────────────────────────────
    const timers = typingTimerRef.current;
    return () => {
      // Invalidate this subscription so stale callbacks are no-ops
      subscriptionId.current++;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      Object.values(timers).forEach(clearTimeout);
      channel.unsubscribe();
      channelRef.current = null;
      setIsConnected(false);
    };
    // loadHistory is stable via useCallback(barangayId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [barangayId, user?.id]);

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

  // ── Send typing indicator (ephemeral broadcast) ──────────────────
  const sendTyping = useCallback(
    async (isTyping: boolean) => {
      if (!channelRef.current || !user) return;
      try {
        await channelRef.current.send({
          type: "broadcast",
          event: "typing",
          payload: {
            user_id: user.id,
            user_name: user.name,
            is_typing: isTyping,
          } satisfies TypingPayload,
        });
      } catch {
        // Typing is best-effort — swallow send failures
      }
    },
    [user],
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
    if (!channelRef.current || isConnected) return;
    retryCount.current = 0;
    channelRef.current
      .unsubscribe()
      .then(() => channelRef.current?.subscribe());
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
