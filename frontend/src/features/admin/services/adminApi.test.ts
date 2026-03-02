/**
 * Admin API Service Tests
 *
 * Tests for the admin API methods (health check endpoint).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { adminApi, type SystemHealth } from '@/features/admin/services/adminApi';

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  default: {
    get: vi.fn(),
  },
  initializeAuthStore: vi.fn(),
}));

import api from '@/lib/api-client';

describe('adminApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getHealth', () => {
    it('should call the correct endpoint', async () => {
      const mockResponse: SystemHealth = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        sla: {
          within_sla: true,
          response_time_ms: 50,
          threshold_ms: 500,
          message: 'OK',
        },
        checks: {
          database: { status: 'healthy', connected: true },
          redis: { status: 'healthy', connected: true },
          cache: { status: 'healthy' },
          model_available: true,
          scheduler_running: true,
          sentry_enabled: false,
        },
      };

      vi.mocked(api.get).mockResolvedValue(mockResponse);

      const result = await adminApi.getHealth();

      expect(api.get).toHaveBeenCalledWith('/api/v1/health');
      expect(result).toEqual(mockResponse);
    });

    it('should propagate errors from the API client', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Network error'));

      await expect(adminApi.getHealth()).rejects.toThrow('Network error');
    });
  });
});
