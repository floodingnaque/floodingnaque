/**
 * GraphQL Client (urql)
 *
 * Lightweight GraphQL client for selective queries (health, weather_data).
 * Gated behind GRAPHQL_ENABLED feature flag — zero cost when disabled.
 *
 * REST remains the primary data transport. GraphQL is opt-in for
 * queries that benefit from selective field fetching.
 */

import { useAuthStore } from "@/state";
import { cacheExchange, createClient, fetchExchange } from "urql";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export const graphqlClient = createClient({
  url: `${API_BASE}/graphql`,
  exchanges: [cacheExchange, fetchExchange],
  fetchOptions: () => {
    const token = useAuthStore.getState().accessToken;
    return {
      headers: token
        ? { Authorization: `Bearer ${token}` }
        : ({} as Record<string, string>),
      credentials: "include" as RequestCredentials,
    };
  },
});
