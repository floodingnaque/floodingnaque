/**
 * useAuth Hook Tests
 *
 * Tests for authentication React hooks including login, register,
 * logout, and profile management.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/tests/mocks/server';
import { createWrapper } from '@/test/utils';
import { useAuth, authQueryKeys } from '@/features/auth/hooks/useAuth';

// Mock the navigate function
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock auth store
vi.mock('@/state/stores/authStore', () => ({
  useAuthStore: vi.fn((selector) => {
    const state = {
      user: null,
      accessToken: null,
      isAuthenticated: false,
      setAuth: vi.fn(),
      clearAuth: vi.fn(),
    };
    return selector(state);
  }),
}));

describe('authQueryKeys', () => {
  it('should generate correct query keys', () => {
    expect(authQueryKeys.all).toEqual(['auth']);
    expect(authQueryKeys.profile()).toEqual(['auth', 'profile']);
  });
});

describe('useAuth', () => {
  const wrapper = createWrapper();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('login', () => {
    it('should return login function and state', () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.login).toBeDefined();
      expect(result.current.isLoggingIn).toBe(false);
      expect(result.current.loginError).toBeNull();
    });

    it('should handle successful login', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      act(() => {
        result.current.login({ email: 'test@example.com', password: 'password123' });
      });

      await waitFor(() => expect(result.current.isLoggingIn).toBe(false));
    });

    it('should handle login error with invalid credentials', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      act(() => {
        result.current.login({ email: 'wrong@example.com', password: 'wrongpassword' });
      });

      await waitFor(() => expect(result.current.loginError).not.toBeNull());
    });
  });

  describe('register', () => {
    it('should return register function and state', () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.register).toBeDefined();
      expect(result.current.isRegistering).toBe(false);
      expect(result.current.registerError).toBeNull();
    });

    it('should handle successful registration', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      act(() => {
        result.current.register({
          email: 'newuser@example.com',
          password: 'password123',
          name: 'New User',
        });
      });

      await waitFor(() => expect(result.current.isRegistering).toBe(false));
    });

    it('should handle registration error for existing email', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      act(() => {
        result.current.register({
          email: 'existing@example.com',
          password: 'password123',
          name: 'Existing User',
        });
      });

      await waitFor(() => expect(result.current.registerError).not.toBeNull());
    });
  });

  describe('logout', () => {
    it('should return logout function', () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.logout).toBeDefined();
      expect(result.current.isLoggingOut).toBe(false);
    });

    it('should handle logout', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      act(() => {
        result.current.logout();
      });

      await waitFor(() => expect(result.current.isLoggingOut).toBe(false));
    });
  });

  describe('state', () => {
    it('should expose user and authentication state', () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.user).toBeDefined();
      expect(typeof result.current.isAuthenticated).toBe('boolean');
    });
  });
});

describe('useAuth with server errors', () => {
  const wrapper = createWrapper();

  it('should handle server error on login', async () => {
    server.use(
      http.post('*/api/v1/auth/login', () => {
        return HttpResponse.json(
          { code: 'SERVER_ERROR', message: 'Internal server error' },
          { status: 500 }
        );
      })
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.login({ email: 'test@example.com', password: 'password123' });
    });

    await waitFor(() => expect(result.current.loginError).not.toBeNull());
  });

  it('should handle network error', async () => {
    server.use(
      http.post('*/api/v1/auth/login', () => {
        return HttpResponse.error();
      })
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.login({ email: 'test@example.com', password: 'password123' });
    });

    await waitFor(() => expect(result.current.loginError).not.toBeNull());
  });
});
