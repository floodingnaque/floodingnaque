/**
 * Query Provider
 *
 * React Query provider with default configuration for data fetching,
 * caching, and state management.
 */

import { PERSIST_MAX_AGE, queryPersister } from "@/lib/query-persister";
import { QueryClient } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { type ReactNode, useState } from "react";

/**
 * Default query client configuration
 */
const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        /** Data considered fresh for 5 minutes */
        staleTime: 5 * 60 * 1000,
        /** Garbage collection after 10 minutes */
        gcTime: 10 * 60 * 1000,
        /** Only retry failed requests once */
        retry: 1,
        /** Don't refetch on window focus by default */
        refetchOnWindowFocus: false,
        /** Don't refetch all queries on reconnect — SSE handles live updates */
        refetchOnReconnect: false,
      },
      mutations: {
        /** Retry mutations once on failure */
        retry: 1,
      },
    },
  });

/**
 * Props for QueryProvider
 */
interface QueryProviderProps {
  children: ReactNode;
}

/**
 * QueryProvider component
 *
 * Wraps the application with React Query's QueryClientProvider
 * and includes devtools in development mode.
 */
export function QueryProvider({ children }: QueryProviderProps) {
  // Create client in state to ensure it's only created once per component lifecycle
  const [queryClient] = useState(() => createQueryClient());

  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister: queryPersister,
        maxAge: PERSIST_MAX_AGE,
        dehydrateOptions: {
          shouldDehydrateQuery: (query) =>
            query.state.status === "success" &&
            (query.meta as Record<string, unknown> | undefined)?.persist ===
              true,
        },
      }}
    >
      {children}
      {import.meta.env.DEV && (
        <ReactQueryDevtools
          initialIsOpen={false}
          buttonPosition="bottom-left"
        />
      )}
    </PersistQueryClientProvider>
  );
}

export default QueryProvider;
