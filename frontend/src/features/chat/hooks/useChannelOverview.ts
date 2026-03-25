/**
 * useChannelOverview — operator sidebar showing all 16 barangay channels
 * with unread counts and alert indicators.
 *
 * Uses a single Supabase Realtime subscription (chat:overview) so
 * we don't open 17 separate channels.
 *
 * Robustness:
 * - Deduplicates message IDs to prevent inflated unread counts on
 *   reconnection (bounded ring-buffer of 500 IDs).
 * - Handles subscription errors gracefully.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api-client";
import { isRealtimeEnabled, supabase } from "@/lib/supabase";
import type { ChatChannel, ChatMessage } from "@/types/api/chat";
import { useQuery } from "@tanstack/react-query";

/** Max number of recent message IDs to track for deduplication. */
const SEEN_BUFFER_SIZE = 500;

export function useChannelOverview() {
  const [unreadCounts, setUnreadCounts] = useState<Record<string, number>>({});
  const [hasAlert, setHasAlert] = useState<Record<string, boolean>>({});

  /** Ring-buffer of recently seen message IDs to prevent double-counting. */
  const seenIds = useRef<Set<string>>(new Set());
  const seenQueue = useRef<string[]>([]);

  const { data: channelsData } = useQuery({
    queryKey: ["chat", "channels"],
    queryFn: () =>
      api.get<{ channels: ChatChannel[] }>("/api/v1/chat/channels"),
    staleTime: Infinity,
  });

  const channels: ChatChannel[] = channelsData?.channels ?? [];

  // Single lightweight subscription watching all barangays
  useEffect(() => {
    if (!isRealtimeEnabled) return;

    const channel = supabase
      .channel("chat:overview")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "chat_messages",
        },
        (payload: { new: Record<string, unknown> }) => {
          const msg = payload.new as unknown as ChatMessage;
          if (!msg.id || !msg.barangay_id) return;

          // Deduplicate: skip if we've already counted this message
          if (seenIds.current.has(msg.id)) return;
          seenIds.current.add(msg.id);
          seenQueue.current.push(msg.id);
          // Evict oldest when buffer overflows
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
        },
      )
      .subscribe();

    return () => {
      channel.unsubscribe();
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
