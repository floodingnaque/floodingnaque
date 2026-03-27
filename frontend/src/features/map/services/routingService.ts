/**
 * OSRM Routing Service
 *
 * Fetches real road-following routes from the public OSRM demo server.
 * Used by SafeRouteLayer to render evacuation routes that follow
 * actual streets instead of straight lines.
 *
 * OSRM coordinate order: longitude, latitude (GeoJSON convention)
 * Leaflet coordinate order: latitude, longitude
 */

const OSRM_BASE = "https://router.project-osrm.org/route/v1/driving";

/** Request timeout — the public OSRM demo can be slow under load */
const OSRM_TIMEOUT_MS = 8_000;
/** Retry once on transient failures */
const OSRM_MAX_RETRIES = 1;

export interface OSRMRoute {
  /** Road-following coordinates in [lat, lon] order (Leaflet-ready) */
  coordinates: [number, number][];
  /** Route distance in meters */
  distance: number;
  /** Route duration in seconds */
  duration: number;
}

interface OSRMResponse {
  code: string;
  routes: {
    geometry: {
      type: string;
      coordinates: [number, number][]; // [lon, lat] from OSRM
    };
    distance: number;
    duration: number;
  }[];
}

/**
 * Fetch a driving route between two points via OSRM.
 * Includes timeout protection and a single retry on transient failures.
 *
 * @param originLat - Start latitude
 * @param originLon - Start longitude
 * @param destLat   - End latitude
 * @param destLon   - End longitude
 * @returns Route geometry + distance/duration, or null on failure
 */
export async function fetchOSRMRoute(
  originLat: number,
  originLon: number,
  destLat: number,
  destLon: number,
): Promise<OSRMRoute | null> {
  // OSRM uses lon,lat order
  const url = `${OSRM_BASE}/${originLon},${originLat};${destLon},${destLat}?overview=full&geometries=geojson`;

  for (let attempt = 0; attempt <= OSRM_MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), OSRM_TIMEOUT_MS);

    try {
      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (!response.ok) {
        if (attempt < OSRM_MAX_RETRIES) continue;
        return null;
      }

      const data: OSRMResponse = await response.json();
      if (data.code !== "Ok" || !data.routes.length) return null;

      const route = data.routes[0];
      if (!route) return null;

      // Convert from [lon, lat] (GeoJSON) → [lat, lon] (Leaflet)
      const coordinates: [number, number][] = route.geometry.coordinates.map(
        ([lon, lat]) => [lat, lon],
      );

      return {
        coordinates,
        distance: route.distance,
        duration: route.duration,
      };
    } catch {
      clearTimeout(timeoutId);
      if (attempt < OSRM_MAX_RETRIES) {
        // Brief pause before retry
        await new Promise((r) => setTimeout(r, 500));
        continue;
      }
      return null;
    }
  }

  return null;
}

/**
 * Fetch routes for multiple origin→destination pairs with staggered requests.
 * Adds a small delay between requests to be respectful to the free OSRM server.
 */
export async function fetchMultipleRoutes(
  pairs: {
    key: string;
    originLat: number;
    originLon: number;
    destLat: number;
    destLon: number;
  }[],
): Promise<Map<string, OSRMRoute>> {
  const results = new Map<string, OSRMRoute>();

  // Batch in groups of 4 with a small delay between batches
  const BATCH_SIZE = 4;
  for (let i = 0; i < pairs.length; i += BATCH_SIZE) {
    const batch = pairs.slice(i, i + BATCH_SIZE);
    const promises = batch.map(async (p) => {
      const route = await fetchOSRMRoute(
        p.originLat,
        p.originLon,
        p.destLat,
        p.destLon,
      );
      if (route) results.set(p.key, route);
    });
    await Promise.all(promises);

    // Small delay between batches to avoid hammering the free server
    if (i + BATCH_SIZE < pairs.length) {
      await new Promise((r) => setTimeout(r, 200));
    }
  }

  return results;
}
