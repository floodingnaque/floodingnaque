/**
 * Test Utilities
 *
 * Custom render function and utilities for testing React components
 * with all necessary providers (QueryClient, Router, etc.).
 */

import type { ReactElement, ReactNode } from 'react';
import { render } from '@testing-library/react';
import type { RenderOptions, RenderResult } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';

/**
 * Create a new QueryClient for testing with disabled retries
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * Props for the AllProviders wrapper component
 */
interface AllProvidersProps {
  children: ReactNode;
  initialEntries?: string[];
}

/**
 * Wrapper component providing all necessary context providers for testing
 */
export function AllProviders({ children, initialEntries = ['/'] }: AllProvidersProps) {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

/**
 * Custom render options
 */
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[];
  queryClient?: QueryClient;
}

/**
 * Custom render function that wraps components with all providers
 */
export function customRender(
  ui: ReactElement,
  options?: CustomRenderOptions
): RenderResult & { user: ReturnType<typeof userEvent.setup> } {
  const { initialEntries, queryClient, ...renderOptions } = options || {};

  const testQueryClient = queryClient || createTestQueryClient();

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={testQueryClient}>
      <MemoryRouter initialEntries={initialEntries || ['/']}>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  );

  const user = userEvent.setup();

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    user,
  };
}

/**
 * Render hook wrapper for testing custom hooks
 */
export function createWrapper(options?: { initialEntries?: string[] }) {
  const queryClient = createTestQueryClient();

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={options?.initialEntries || ['/']}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

/**
 * Wait for async operations to complete
 */
export function waitForAsync(ms: number = 0): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Create a deferred promise for testing async flows
 */
export function createDeferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
} {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;

  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

// Re-export testing library utilities
export * from '@testing-library/react';
export { userEvent };
export { customRender as render };
