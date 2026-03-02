/**
 * useAdmin Hook Tests
 *
 * Tests for the admin system health hook and query keys.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/tests/mocks/server';
import { createWrapper } from '@/test/utils';
import { useSystemHealth, adminQueryKeys } from '@/features/admin/hooks/useAdmin';

// ---------------------------------------------------------------------------
// Mock health response
// ---------------------------------------------------------------------------
function createMockHealthResponse() {
  return {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    sla: {
      within_sla: true,
      response_time_ms: 42,
      threshold_ms: 500,
      message: 'Response time within SLA',
    },
    checks: {
      database: { status: 'healthy', connected: true, latency_ms: 5 },
      redis: { status: 'healthy', connected: true },
      cache: { status: 'healthy' },
      model_available: true,
      scheduler_running: true,
      sentry_enabled: false,
    },
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('adminQueryKeys', () => {
  it('should generate correct base key', () => {
    expect(adminQueryKeys.all).toEqual(['admin']);
  });

  it('should generate correct health key', () => {
    expect(adminQueryKeys.health()).toEqual(['admin', 'health']);
  });
});

describe('useSystemHealth', () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it('should fetch system health successfully', async () => {
    const mock = createMockHealthResponse();

    server.use(
      http.get('*/api/v1/health', () => HttpResponse.json(mock)),
    );

    const { result } = renderHook(() => useSystemHealth(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.status).toBe('healthy');
    expect(result.current.data?.checks.database.connected).toBe(true);
    expect(result.current.data?.checks.model_available).toBe(true);
  });

  it('should handle disabled state', () => {
    const { result } = renderHook(() => useSystemHealth(false), {
      wrapper: createWrapper(),
    });

    // When disabled, the query should not be fetching
    expect(result.current.isFetching).toBe(false);
  });

  it('should handle server error gracefully', async () => {
    server.use(
      http.get('*/api/v1/health', () =>
        HttpResponse.json({ error: 'Internal Server Error' }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useSystemHealth(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it('should handle degraded status', async () => {
    const degraded = {
      ...createMockHealthResponse(),
      status: 'degraded',
      checks: {
        ...createMockHealthResponse().checks,
        database: { status: 'unhealthy', connected: false },
      },
    };

    server.use(
      http.get('*/api/v1/health', () => HttpResponse.json(degraded)),
    );

    const { result } = renderHook(() => useSystemHealth(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.status).toBe('degraded');
    expect(result.current.data?.checks.database.connected).toBe(false);
  });

  it('should handle network failure', async () => {
    server.use(
      http.get('*/api/v1/health', () => HttpResponse.error()),
    );

    const { result } = renderHook(() => useSystemHealth(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
