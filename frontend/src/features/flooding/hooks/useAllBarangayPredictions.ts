/**
 * useAllBarangayPredictions Hook
 *
 * Fetches flood predictions for ALL 16 Parañaque barangays using a
 * single TanStack Query instance. Requests are staggered in small
 * batches (3 at a time, 1 s between batches) to avoid overwhelming
 * the backend / OWM weather API.
 *
 * Replaces the previous pattern of 16 individual useLivePrediction
 * hooks which caused a request storm on mount.
 */

import { BARANGAYS } from "@/config/paranaque";
import { predictionApi } from "@/features/flooding/services/predictionApi";
import type { PredictionResponse } from "@/types";
import { useQuery } from "@tanstack/react-query";

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes
const BATCH_SIZE = 3;
const BATCH_DELAY_MS = 1_000;

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });
}

async function fetchAllPredictions(
  signal?: AbortSignal,
): Promise<Record<string, PredictionResponse>> {
  const results: Record<string, PredictionResponse> = {};

  for (let i = 0; i < BARANGAYS.length; i += BATCH_SIZE) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");

    const batch = BARANGAYS.slice(i, i + BATCH_SIZE);
    const settled = await Promise.allSettled(
      batch.map((b) =>
        predictionApi
          .predictByLocation({ latitude: b.lat, longitude: b.lon }, { signal })
          .then((result) => ({ key: b.key, result })),
      ),
    );

    for (const outcome of settled) {
      if (outcome.status === "fulfilled") {
        results[outcome.value.key] = outcome.value.result;
      }
      // Silently skip failed individual predictions — partial data is OK
    }

    // Pause between batches (skip after the last one)
    if (i + BATCH_SIZE < BARANGAYS.length) {
      await delay(BATCH_DELAY_MS, signal);
    }
  }

  return results;
}

/**
 * Single query that fetches predictions for all 16 barangays in
 * staggered batches and refreshes every 5 minutes.
 */
export function useAllBarangayPredictions(enabled = true) {
  return useQuery<Record<string, PredictionResponse>>({
    queryKey: ["prediction", "live", "all-barangays"],
    queryFn: ({ signal }) => fetchAllPredictions(signal),
    enabled,
    staleTime: REFRESH_INTERVAL,
    refetchInterval: REFRESH_INTERVAL,
    retry: 1,
    refetchOnWindowFocus: true,
  });
}
