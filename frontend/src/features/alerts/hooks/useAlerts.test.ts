/**
 * useAlerts Hook Tests
 *
 * Tests for alerts-related React Query hooks.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/tests/mocks/server';
import { createWrapper } from '@/test/utils';
import {
  useAlerts,
  useRecentAlerts,
  useAlertHistory,
  useAcknowledgeAlert,
  alertKeys,
} from '@/features/alerts/hooks/useAlerts';

describe('alertKeys', () => {
  it('should generate correct query keys', () => {
    expect(alertKeys.all).toEqual(['alerts']);
    expect(alertKeys.lists()).toEqual(['alerts', 'list']);
    expect(alertKeys.list({ page: 1 })).toEqual(['alerts', 'list', { page: 1 }]);
    expect(alertKeys.recent(5)).toEqual(['alerts', 'recent', 5]);
    expect(alertKeys.history()).toEqual(['alerts', 'history']);
  });
});

describe('useAlerts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.resetHandlers();
  });

  it('should fetch paginated alerts successfully', async () => {
    const { result } = renderHook(() => useAlerts({ page: 1, limit: 10 }), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.data).toHaveLength(10);
    expect(result.current.data?.page).toBe(1);
    expect(result.current.data?.total).toBe(50);
  });

  it('should handle loading state', () => {
    // Use delay handler to ensure we can capture loading state
    server.use(
      http.get('*/api/v1/alerts', async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json({ data: [], page: 1, limit: 10, total: 0 });
      })
    );

    const { result } = renderHook(() => useAlerts(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('should handle error state', async () => {
    server.use(
      http.get('*/api/v1/alerts', () => {
        return HttpResponse.json(
          { code: 'SERVER_ERROR', message: 'Internal server error' },
          { status: 500 }
        );
      })
    );

    const { result } = renderHook(() => useAlerts(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeDefined();
  });

  it('should apply filter parameters', async () => {
    const params = { page: 2, limit: 5, risk_level: 2 as const };
    const { result } = renderHook(() => useAlerts(params), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.page).toBe(2);
    expect(result.current.data?.data).toHaveLength(5);
  });
});

describe('useRecentAlerts', () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it('should fetch recent alerts with default limit', async () => {
    const { result } = renderHook(() => useRecentAlerts(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
  });

  it('should fetch recent alerts with custom limit', async () => {
    const { result } = renderHook(() => useRecentAlerts(3), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.length).toBeLessThanOrEqual(3);
  });
});

describe('useAlertHistory', () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it('should fetch alert history with summary', async () => {
    const { result } = renderHook(() => useAlertHistory(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.alerts).toBeDefined();
    expect(result.current.data?.summary).toBeDefined();
    expect(result.current.data?.summary.total).toBe(100);
    expect(result.current.data?.summary.by_risk_level).toBeDefined();
  });
});

describe('useAcknowledgeAlert', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.resetHandlers();
  });

  it('should acknowledge an alert successfully', async () => {
    const onSuccess = vi.fn();

    const { result } = renderHook(
      () => useAcknowledgeAlert({ onSuccess }),
      { wrapper: createWrapper() }
    );

    result.current.mutate(123);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(onSuccess).toHaveBeenCalled();
  });

  it('should handle acknowledge error', async () => {
    server.use(
      http.patch('*/api/v1/alerts/:id/acknowledge', () => {
        return HttpResponse.json(
          { code: 'NOT_FOUND', message: 'Alert not found' },
          { status: 404 }
        );
      })
    );

    const onError = vi.fn();
    const { result } = renderHook(
      () => useAcknowledgeAlert({ onError }),
      { wrapper: createWrapper() }
    );

    result.current.mutate(999);

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(onError).toHaveBeenCalled();
  });
});
