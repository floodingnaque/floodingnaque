/**
 * Query Provider
 *
 * React Query provider with default configuration for data fetching,
 * caching, and state management.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { type ReactNode, useState } from 'react';

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
        /** Refetch on reconnect */
        refetchOnReconnect: true,
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
    <QueryClientProvider client={queryClient}>
      {children}
      {import.meta.env.DEV && (
        <ReactQueryDevtools
          initialIsOpen={false}
          buttonPosition="bottom-left"
        />
      )}
    </QueryClientProvider>
  );
}

export default QueryProvider;
