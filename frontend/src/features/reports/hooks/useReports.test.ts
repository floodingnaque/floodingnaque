/**
 * useReports Hook Tests
 *
 * Tests for report generation and export mutation hooks.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/tests/mocks/server';
import { createWrapper } from '@/test/utils';
import { useExportPDF, useExportCSV, downloadBlob, reportsKeys } from '@/features/reports/hooks/useReports';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('reportsKeys', () => {
  it('should generate correct query keys', () => {
    expect(reportsKeys.all).toEqual(['reports']);
    expect(reportsKeys.exports()).toEqual(['reports', 'exports']);
  });
});

describe('downloadBlob', () => {
  let mockLink: HTMLAnchorElement;
  let mockCreateElement: ReturnType<typeof vi.spyOn>;
  let mockAppendChild: ReturnType<typeof vi.spyOn>;
  let mockRemoveChild: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    mockLink = {
      href: '',
      download: '',
      style: { display: '' },
      click: vi.fn(),
    } as unknown as HTMLAnchorElement;

    mockCreateElement = vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
    mockAppendChild = vi.spyOn(document.body, 'appendChild').mockReturnValue(mockLink);
    mockRemoveChild = vi.spyOn(document.body, 'removeChild').mockReturnValue(mockLink);
  });

  afterEach(() => {
    // Restore DOM mocks to prevent interference with other tests
    mockCreateElement.mockRestore();
    mockAppendChild.mockRestore();
    mockRemoveChild.mockRestore();
  });

  it('should create download link with correct attributes', () => {
    const blob = new Blob(['test'], { type: 'application/pdf' });
    downloadBlob(blob, 'test-report.pdf');

    expect(mockCreateElement).toHaveBeenCalledWith('a');
    expect(mockLink.download).toBe('test-report.pdf');
    expect(mockLink.click).toHaveBeenCalled();
    expect(mockRemoveChild).toHaveBeenCalled();
  });
});

describe('useExportPDF', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return initial state correctly', () => {
    const { result } = renderHook(() => useExportPDF(), { wrapper: createWrapper() });

    expect(result.current.mutate).toBeDefined();
    expect(result.current.isPending).toBe(false);
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it('should export PDF successfully', async () => {
    const { result } = renderHook(() => useExportPDF(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({
        report_type: 'predictions',
        start_date: '2026-01-01',
        end_date: '2026-01-31',
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Toast should have been called
    const { toast } = await import('sonner');
    expect(toast.success).toHaveBeenCalledWith(
      'PDF Report Downloaded',
      expect.objectContaining({
        description: expect.stringContaining('predictions'),
      })
    );
  });

  it('should handle PDF export error', async () => {
    server.use(
      http.post('*/api/v1/export/pdf', () => {
        return HttpResponse.json(
          { code: 'EXPORT_FAILED', message: 'Export failed' },
          { status: 500 }
        );
      })
    );

    const { result } = renderHook(() => useExportPDF(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ report_type: 'alerts' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    const { toast } = await import('sonner');
    expect(toast.error).toHaveBeenCalledWith(
      'Export Failed',
      expect.objectContaining({
        description: expect.any(String),
      })
    );
  });

  it('should show pending state during export', async () => {
    const { result } = renderHook(() => useExportPDF(), { wrapper: createWrapper() });

    // Initially not pending
    expect(result.current.isPending).toBe(false);

    act(() => {
      result.current.mutate({ report_type: 'predictions' });
    });

    // Wait for the mutation to complete - isPending goes from true to false
    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useExportCSV', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return initial state correctly', () => {
    const { result } = renderHook(() => useExportCSV(), { wrapper: createWrapper() });

    expect(result.current.mutate).toBeDefined();
    expect(result.current.isPending).toBe(false);
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it('should export CSV successfully', async () => {
    const { result } = renderHook(() => useExportCSV(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({
        report_type: 'weather',
        start_date: '2026-01-01',
        end_date: '2026-01-31',
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const { toast } = await import('sonner');
    expect(toast.success).toHaveBeenCalledWith(
      'CSV Report Downloaded',
      expect.objectContaining({
        description: expect.stringContaining('weather'),
      })
    );
  });

  it('should handle CSV export error', async () => {
    server.use(
      http.post('*/api/v1/export/csv', () => {
        return HttpResponse.json(
          { code: 'EXPORT_FAILED', message: 'Export failed' },
          { status: 500 }
        );
      })
    );

    const { result } = renderHook(() => useExportCSV(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ report_type: 'alerts' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it('should handle network error during export', async () => {
    server.use(
      http.post('*/api/v1/export/csv', () => {
        return HttpResponse.error();
      })
    );

    const { result } = renderHook(() => useExportCSV(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ report_type: 'predictions' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('Export with different report types', () => {
  const reportTypes = ['predictions', 'alerts', 'weather'] as const;

  reportTypes.forEach((reportType) => {
    it(`should export ${reportType} as PDF`, async () => {
      const { result } = renderHook(() => useExportPDF(), { wrapper: createWrapper() });

      act(() => {
        result.current.mutate({ report_type: reportType });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it(`should export ${reportType} as CSV`, async () => {
      const { result } = renderHook(() => useExportCSV(), { wrapper: createWrapper() });

      act(() => {
        result.current.mutate({ report_type: reportType });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });
});
