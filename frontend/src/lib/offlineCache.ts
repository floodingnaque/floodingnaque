/**
 * Offline Prediction Cache
 *
 * Stores the last N prediction results in IndexedDB so the UI can
 * display them with a "stale data" indicator when the network is down.
 *
 * Uses the `idb` library for a promise-based IndexedDB API.
 */

import { openDB, type IDBPDatabase } from 'idb';
import type { PredictionResponse } from '@/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DB_NAME = 'floodingnaque-offline';
const DB_VERSION = 1;
const STORE_NAME = 'predictions';
/** Maximum number of cached prediction results */
const MAX_CACHED = 50;

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

interface CachedPrediction {
  /** Auto-incrementing key */
  id?: number;
  /** ISO-8601 timestamp when the entry was cached */
  cachedAt: string;
  /** The original prediction response */
  data: PredictionResponse;
}

// ---------------------------------------------------------------------------
// Database initialisation
// ---------------------------------------------------------------------------

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, {
            keyPath: 'id',
            autoIncrement: true,
          });
          store.createIndex('by-cached', 'cachedAt');
        }
      },
    });
  }
  return dbPromise;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Save a prediction result to the offline cache.
 *
 * Automatically evicts the oldest entries when `MAX_CACHED` is exceeded.
 */
export async function cachePrediction(
  prediction: PredictionResponse,
): Promise<void> {
  try {
    const db = await getDb();
    const entry: CachedPrediction = {
      cachedAt: new Date().toISOString(),
      data: prediction,
    };
    await db.add(STORE_NAME, entry);

    // Evict oldest if over limit
    const count = await db.count(STORE_NAME);
    if (count > MAX_CACHED) {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      let cursor = await store.openCursor();
      let toDelete = count - MAX_CACHED;
      while (cursor && toDelete > 0) {
        await cursor.delete();
        toDelete--;
        cursor = await cursor.continue();
      }
      await tx.done;
    }
  } catch (err) {
    // IndexedDB may be unavailable in some contexts (e.g. private browsing).
    // Fail silently - the cache is a best-effort enhancement.
    console.warn('[offlineCache] Failed to cache prediction:', err);
  }
}

/**
 * Retrieve the most recent `n` cached predictions, newest first.
 */
export async function getCachedPredictions(
  n: number = MAX_CACHED,
): Promise<CachedPrediction[]> {
  try {
    const db = await getDb();
    const all = await db.getAll(STORE_NAME);
    // Sort newest-first and take the requested amount
    return all
      .sort((a, b) => b.cachedAt.localeCompare(a.cachedAt))
      .slice(0, n);
  } catch {
    return [];
  }
}

/**
 * Remove all cached predictions.
 */
export async function clearCachedPredictions(): Promise<void> {
  try {
    const db = await getDb();
    await db.clear(STORE_NAME);
  } catch {
    // ignore
  }
}

export type { CachedPrediction };
