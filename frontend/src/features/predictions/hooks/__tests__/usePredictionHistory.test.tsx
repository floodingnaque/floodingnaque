/**
 * usePredictionHistory Hook Tests
 *
 * Basic tests for the prediction history hook.
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { usePredictionHistory, predictionQueryKeys } from '../usePredictionHistory';

// Mock the prediction API
vi.mock('../../services/predictionApi', () => ({
  predictionApi: {
    list: vi.fn().mockResolvedValue({ data: [], total: 0 }),
    stats: vi.fn().mockResolvedValue({}),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('usePredictionHistory', () => {
  it('returns query result with data', async () => {
    const { result } = renderHook(() => usePredictionHistory(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();
  });

  it('generates correct query keys', () => {
    expect(predictionQueryKeys.all).toEqual(['predictions']);
    expect(predictionQueryKeys.list()).toEqual(['predictions', 'list', undefined]);
    expect(predictionQueryKeys.stats()).toEqual(['predictions', 'stats']);
  });
});
