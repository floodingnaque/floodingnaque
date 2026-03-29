/**
 * useChannelOverview - operator sidebar showing all 16 barangay channels
 * with unread counts and alert indicators.
 *
 * Uses a single SSE connection with channel="all" so we don't open
 * 17 separate streams.
 *
 * Robustness:
 * - Deduplicates message IDs to prevent inflated unread counts on
 *   reconnection (bounded ring-buffer of 500 IDs).
 * - Reconnects with exponential backoff.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { API_CONFIG } from "@/config/api.config";
import { api } from "@/lib/api-client";
import type { ChatChannel, ChatMessage } from "@/types/api/chat";
import { useQuery } from "@tanstack/react-query";

/** Max number of recent message IDs to track for deduplication. */
const SEEN_BUFFER_SIZE = 500;
const MAX_RETRY_DELAY_MS = 30_000;
const BASE_RETRY_DELAY_MS = 1_000;
const MAX_RECONNECT_ATTEMPTS = 15;

export function useChannelOverview() {
  const [unreadCounts, setUnreadCounts] = useState<Record<string, number>>({});
  const [hasAlert, setHasAlert] = useState<Record<string, boolean>>({});

  /** Ring-buffer of recently seen message IDs to prevent double-counting. */
  const seenIds = useRef<Set<string>>(new Set());
  const seenQueue = useRef<string[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: channelsData } = useQuery({
    queryKey: ["chat", "channels"],
    queryFn: () =>
      api.get<{ channels: ChatChannel[] }>("/api/v1/chat/channels"),
    staleTime: Infinity,
  });

  const channels: ChatChannel[] = channelsData?.channels ?? [];

  // Single SSE stream watching all channels
  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;

    async function connect() {
      if (cancelled) return;

      try {
        const { ticket } = await api.post<{ ticket: string }>(
          `${API_CONFIG.endpoints.sse.chat}/ticket`,
        );
        if (cancelled) return;

        const baseUrl = API_CONFIG.sseUrl || API_CONFIG.baseUrl;
        const url = `${baseUrl}${API_CONFIG.endpoints.sse.chat}?channel=all&ticket=${encodeURIComponent(ticket)}`;

        es = new EventSource(url);
        eventSourceRef.current = es;

        es.addEventListener("connected", () => {
          retryCount.current = 0;
        });

        es.addEventListener("new_message", (event: MessageEvent) => {
          try {
            const data = JSON.parse(event.data);
            const msg: ChatMessage = data.message;
            if (!msg.id || !msg.barangay_id) return;

            // Deduplicate
            if (seenIds.current.has(msg.id)) return;
            seenIds.current.add(msg.id);
            seenQueue.current.push(msg.id);
            if (seenQueue.current.length > SEEN_BUFFER_SIZE) {
              const evicted = seenQueue.current.shift()!;
              seenIds.current.delete(evicted);
            }

            setUnreadCounts((prev) => ({
              ...prev,
              [msg.barangay_id]: (prev[msg.barangay_id] ?? 0) + 1,
            }));
            if (
              ["alert", "flood_report", "status_update"].includes(
                msg.message_type,
              )
            ) {
              setHasAlert((prev) => ({
                ...prev,
                [msg.barangay_id]: true,
              }));
            }
          } catch {
            // ignore
          }
        });

        es.onerror = () => {
          if (cancelled) return;
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
              if (!cancelled) connect();
            }, delay);
          }
        };
      } catch {
        if (cancelled) return;
        if (retryCount.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            BASE_RETRY_DELAY_MS * 2 ** retryCount.current,
            MAX_RETRY_DELAY_MS,
          );
          retryCount.current++;
          retryTimer.current = setTimeout(() => {
            if (!cancelled) connect();
          }, delay);
        }
      }
    }

    connect();

    return () => {
      cancelled = true;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      if (es) es.close();
      eventSourceRef.current = null;
    };
  }, []);

  const markRead = useCallback((barangayId: string) => {
    setUnreadCounts((prev) => ({ ...prev, [barangayId]: 0 }));
    setHasAlert((prev) => ({ ...prev, [barangayId]: false }));
  }, []);

  const totalUnread = Object.values(unreadCounts).reduce(
    (sum, n) => sum + n,
    0,
  );

  return {
    channels,
    unreadCounts,
    hasAlert,
    totalUnread,
    markRead,
  };
}
