/**
 * Evacuation Store
 *
 * Zustand store with localStorage persistence for evacuation data.
 * Caches center data for offline fallback and provides a client-side
 * Haversine nearest-center calculator when the server is unreachable.
 */

import type { EvacuationCenter } from "@/types";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { useShallow } from "zustand/react/shallow";

// ---------------------------------------------------------------------------
// Haversine distance (km) - client-side fallback
// ---------------------------------------------------------------------------

function haversineKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ---------------------------------------------------------------------------
// State & Actions
// ---------------------------------------------------------------------------

interface EvacuationState {
  /** Cached centers for offline use */
  cachedCenters: EvacuationCenter[];
  /** Timestamp of last cache update */
  cachedAt: number | null;
  /** Whether the user is currently considered offline */
  isOffline: boolean;
}

interface EvacuationActions {
  /** Update the center cache (call after a successful API fetch) */
  setCachedCenters: (centers: EvacuationCenter[]) => void;
  /** Mark online/offline status */
  setOffline: (offline: boolean) => void;
  /**
   * Client-side nearest-center lookup using Haversine distance.
   * Returns the `limit` closest centers sorted by distance (ascending).
   */
  findNearestOffline: (
    lat: number,
    lon: number,
    limit?: number,
  ) => Array<{ center: EvacuationCenter; distance_km: number }>;
  /** Clear the offline cache */
  clearCache: () => void;
}

type EvacuationStore = EvacuationState & EvacuationActions;

const initialState: EvacuationState = {
  cachedCenters: [],
  cachedAt: null,
  isOffline: false,
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useEvacuationStore = create<EvacuationStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setCachedCenters: (centers) =>
        set({ cachedCenters: centers, cachedAt: Date.now() }),

      setOffline: (offline) => set({ isOffline: offline }),

      findNearestOffline: (lat, lon, limit = 3) => {
        const { cachedCenters } = get();
        return cachedCenters
          .filter((c) => c.is_active)
          .map((c) => ({
            center: c,
            distance_km: haversineKm(lat, lon, c.latitude, c.longitude),
          }))
          .sort((a, b) => a.distance_km - b.distance_km)
          .slice(0, limit);
      },

      clearCache: () => set(initialState),
    }),
    {
      name: "floodingnaque-evacuation",
      partialize: (state) => ({
        cachedCenters: state.cachedCenters,
        cachedAt: state.cachedAt,
      }),
    },
  ),
);

// ---------------------------------------------------------------------------
// Granular selector hooks
// ---------------------------------------------------------------------------

export const useCachedCenters = () =>
  useEvacuationStore((s) => s.cachedCenters);

export const useIsOffline = () => useEvacuationStore((s) => s.isOffline);

export const useEvacuationActions = () =>
  useEvacuationStore(
    useShallow((s) => ({
      setCachedCenters: s.setCachedCenters,
      setOffline: s.setOffline,
      findNearestOffline: s.findNearestOffline,
      clearCache: s.clearCache,
    })),
  );
