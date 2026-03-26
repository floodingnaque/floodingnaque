/**
 * useUnreadCount - lightweight unread counter for an inactive channel.
 *
 * Subscribes to Supabase Realtime INSERT events on a single barangay and
 * increments a counter.  Counter resets automatically when the
 * `barangayId` changes (e.g. when the user switches tabs).
 *
 * The caller should only pass the *inactive* channel ID so we don't
 * duplicate the full `useChat` subscription on the active channel.
 */

import { useEffect, useState } from "react";

import { isRealtimeEnabled, supabase } from "@/lib/supabase";

export function useUnreadCount(barangayId: string | null): number {
  // Keyed counts - each barangay gets its own counter so we never
  // need a synchronous reset inside the effect body.
  const [counts, setCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!barangayId || !isRealtimeEnabled) return;

    const seenIds = new Set<string>();

    const channel = supabase
      .channel(`unread:${barangayId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "chat_messages",
          filter: `barangay_id=eq.${barangayId}`,
        },
        (payload) => {
          const id = (payload.new as { id?: string }).id;
          if (id && !seenIds.has(id)) {
            seenIds.add(id);
            setCounts((prev) => ({
              ...prev,
              [barangayId]: (prev[barangayId] ?? 0) + 1,
            }));
          }
        },
      )
      .subscribe();

    return () => {
      channel.unsubscribe();
      // Clear this channel's count on cleanup
      setCounts((prev) => {
        const next = { ...prev };
        delete next[barangayId];
        return next;
      });
    };
  }, [barangayId]);

  return barangayId ? (counts[barangayId] ?? 0) : 0;
}
