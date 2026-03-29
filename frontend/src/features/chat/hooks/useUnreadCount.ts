/**
 * useUnreadCount - lightweight unread counter for an inactive channel.
 *
 * Opens an SSE stream scoped to a single barangay and increments a
 * counter on each new_message event.  Counter resets when the
 * `barangayId` changes (e.g. when the user switches tabs).
 *
 * The caller should only pass the *inactive* channel ID so we don't
 * duplicate the full `useChat` SSE stream on the active channel.
 */

import { useEffect, useRef, useState } from "react";

import { API_CONFIG } from "@/config/api.config";
import { api } from "@/lib/api-client";

const MAX_RETRY_DELAY_MS = 30_000;
const BASE_RETRY_DELAY_MS = 1_000;
const MAX_RECONNECT_ATTEMPTS = 10;

export function useUnreadCount(barangayId: string | null): number {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!barangayId) return;

    let es: EventSource | null = null;
    let cancelled = false;
    const seenIds = new Set<string>();

    async function connect() {
      if (cancelled) return;

      try {
        const { ticket } = await api.post<{ ticket: string }>(
          `${API_CONFIG.endpoints.sse.chat}/ticket`,
        );
        if (cancelled) return;

        const baseUrl = API_CONFIG.sseUrl || API_CONFIG.baseUrl;
        const url = `${baseUrl}${API_CONFIG.endpoints.sse.chat}?channel=${encodeURIComponent(barangayId!)}&ticket=${encodeURIComponent(ticket)}`;

        es = new EventSource(url);

        es.addEventListener("connected", () => {
          retryCount.current = 0;
        });

        es.addEventListener("new_message", (event: MessageEvent) => {
          try {
            const data = JSON.parse(event.data);
            const id = data.message?.id as string | undefined;
            if (id && !seenIds.has(id)) {
              seenIds.add(id);
              setCounts((prev) => ({
                ...prev,
                [barangayId!]: (prev[barangayId!] ?? 0) + 1,
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
      setCounts((prev) => {
        const next = { ...prev };
        delete next[barangayId];
        return next;
      });
    };
  }, [barangayId]);

  return barangayId ? (counts[barangayId] ?? 0) : 0;
}
