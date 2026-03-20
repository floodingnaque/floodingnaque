/**
 * TanStack Query IndexedDB Persister
 *
 * Persists selected query cache entries to IndexedDB via idb-keyval,
 * enabling offline-first dashboard loads. Only queries with
 * `meta: { persist: true }` are persisted.
 */

import {
  type PersistedClient,
  type Persister,
} from "@tanstack/react-query-persist-client";
import { del, get, set } from "idb-keyval";

const IDB_KEY = "floodingnaque-query-cache";

export const queryPersister: Persister = {
  persistClient: async (client: PersistedClient) => {
    await set(IDB_KEY, client);
  },
  restoreClient: async () => {
    return (await get<PersistedClient>(IDB_KEY)) ?? undefined;
  },
  removeClient: async () => {
    await del(IDB_KEY);
  },
};

/** 24-hour max age for persisted cache */
export const PERSIST_MAX_AGE = 1000 * 60 * 60 * 24;
