/**
 * useUserLocation Hook
 *
 * Enhanced geolocation hook that validates coordinates are within
 * Parañaque City bounds and detects the user's barangay via the
 * geo-worker (Turf.js point-in-polygon).
 *
 * Falls back to city center if the user is outside Parañaque bounds.
 */

import { BARANGAYS, type BarangayData } from "@/config/paranaque";
import { useCallback, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Parañaque City geographic bounds */
const PARANAQUE_BOUNDS = {
  minLat: 14.42,
  maxLat: 14.55,
  minLng: 120.97,
  maxLng: 121.07,
} as const;

/** City center fallback */
const PARANAQUE_CENTER = { lat: 14.4793, lng: 121.0198 } as const;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type LocationStatus =
  | "idle"
  | "requesting"
  | "granted"
  | "denied"
  | "unavailable";

export interface UserLocation {
  lat: number;
  lng: number;
  accuracy: number;
  isWithinBounds: boolean;
}

export interface UseUserLocationReturn {
  status: LocationStatus;
  location: UserLocation | null;
  barangay: BarangayData | null;
  requestLocation: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isWithinParanaque(lat: number, lng: number): boolean {
  return (
    lat >= PARANAQUE_BOUNDS.minLat &&
    lat <= PARANAQUE_BOUNDS.maxLat &&
    lng >= PARANAQUE_BOUNDS.minLng &&
    lng <= PARANAQUE_BOUNDS.maxLng
  );
}

/**
 * Simple point-in-polygon using ray casting algorithm.
 * Polygons in paranaque.ts are [lat, lon][] pairs.
 */
function pointInPolygon(
  lat: number,
  lng: number,
  polygon: [number, number][],
): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const pi = polygon[i]!;
    const pj = polygon[j]!;
    const [yi, xi] = pi;
    const [yj, xj] = pj;
    if (
      yi > lat !== yj > lat &&
      lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi
    ) {
      inside = !inside;
    }
  }
  return inside;
}

export function detectBarangay(lat: number, lng: number): BarangayData | null {
  for (const barangay of BARANGAYS) {
    if (pointInPolygon(lat, lng, barangay.polygon)) {
      return barangay;
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useUserLocation(): UseUserLocationReturn {
  const [status, setStatus] = useState<LocationStatus>("idle");
  const [location, setLocation] = useState<UserLocation | null>(null);
  const [barangay, setBarangay] = useState<BarangayData | null>(null);
  const requestedRef = useRef(false);

  const requestLocation = useCallback(() => {
    if (requestedRef.current) return;

    if (!("geolocation" in navigator)) {
      setStatus("unavailable");
      return;
    }

    setStatus("requesting");
    requestedRef.current = true;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude: lat, longitude: lng, accuracy } = position.coords;
        const inBounds = isWithinParanaque(lat, lng);

        if (inBounds) {
          setLocation({ lat, lng, accuracy, isWithinBounds: true });
          setBarangay(detectBarangay(lat, lng));
        } else {
          // Fallback to city center
          setLocation({
            lat: PARANAQUE_CENTER.lat,
            lng: PARANAQUE_CENTER.lng,
            accuracy: 0,
            isWithinBounds: false,
          });
          setBarangay(null);
        }

        setStatus("granted");
      },
      (error) => {
        requestedRef.current = false;
        if (error.code === error.PERMISSION_DENIED) {
          setStatus("denied");
        } else {
          setStatus("unavailable");
        }
      },
      {
        enableHighAccuracy: false,
        timeout: 5000,
        maximumAge: 300_000,
      },
    );
  }, []);

  return { status, location, barangay, requestLocation };
}
