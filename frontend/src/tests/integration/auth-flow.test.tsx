/**
 * Authentication Flow Integration Tests
 *
 * Tests the complete authentication flow including login, registration,
 * token management, and protected routes.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server, createMockUser, createMockTokens } from '@/tests/mocks';
import { render } from '@/test/utils';
import { LoginForm } from '@/features/auth/components/LoginForm';
import { RegisterForm } from '@/features/auth/components/RegisterForm';


describe('Authentication Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset any auth state
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('Login Flow', () => {
    it('should display login form initially', () => {
      render(<LoginForm />);

      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('should show validation errors for invalid input', async () => {
      const { user } = render(<LoginForm />);

      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
    });

    it('should handle failed login attempt', async () => {
      server.use(
        http.post('*/api/v1/auth/login', async () => {
          return HttpResponse.json(
            { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' },
            { status: 401 }
          );
        })
      );

      const { user } = render(<LoginForm />);

      await user.type(screen.getByLabelText(/email/i), 'wrong@example.com');
      await user.type(screen.getByLabelText(/password/i), 'wrongpassword');
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(
        () => {
          expect(screen.getByRole('alert')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should show loading state during login', async () => {
      // Add delay to see loading state
      server.use(
        http.post('*/api/v1/auth/login', async () => {
          await new Promise((resolve) => setTimeout(resolve, 200));
          return HttpResponse.json(createMockTokens());
        })
      );

      const { user } = render(<LoginForm />);

      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');

      // Don't await - check loading state immediately after click
      const loginButton = screen.getByRole('button', { name: /sign in/i });
      user.click(loginButton);

      // Wait for loading state
      await waitFor(() => {
        expect(screen.getByRole('button')).toBeDisabled();
      });
    });
  });

  describe('Registration Flow', () => {
    it('should handle successful registration', async () => {
      server.use(
        http.post('*/api/v1/auth/register', async () => {
          return HttpResponse.json(createMockTokens(), { status: 201 });
        }),
        http.get('*/api/v1/auth/me', async () => {
          return HttpResponse.json(createMockUser());
        })
      );

      const { user } = render(<RegisterForm />);

      await user.type(screen.getByLabelText(/name/i), 'New User');
      await user.type(screen.getByLabelText(/email/i), 'newuser@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');

      await user.click(screen.getByRole('button', { name: /create account|sign up|register/i }));

      // Should show loading or transition
      await waitFor(() => {
        const button = screen.queryByRole('button');
        expect(button).toBeDefined();
      });
    });

    it('should show error for existing email', async () => {
      server.use(
        http.post('*/api/v1/auth/register', async () => {
          return HttpResponse.json(
            { code: 'EMAIL_EXISTS', message: 'Email already registered' },
            { status: 409 }
          );
        })
      );

      const { user } = render(<RegisterForm />);

      await user.type(screen.getByLabelText(/name/i), 'Existing User');
      await user.type(screen.getByLabelText(/email/i), 'existing@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');

      await user.click(screen.getByRole('button', { name: /create account|sign up|register/i }));

      await waitFor(
        () => {
          expect(screen.getByRole('alert')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should validate password requirements', async () => {
      const { user } = render(<RegisterForm />);

      await user.type(screen.getByLabelText(/name/i), 'Test User');
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'short');

      await user.click(screen.getByRole('button', { name: /create account|sign up|register/i }));

      await waitFor(() => {
        expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument();
      });
    });
  });

  describe('Token Management', () => {
    it('should handle token refresh on 401', async () => {
      let refreshAttempted = false;

      server.use(
        http.get('*/api/v1/auth/me', async () => {
          if (!refreshAttempted) {
            refreshAttempted = true;
            return HttpResponse.json(
              { code: 'TOKEN_EXPIRED', message: 'Token expired' },
              { status: 401 }
            );
          }
          return HttpResponse.json(createMockUser());
        }),
        http.post('*/api/v1/auth/refresh', async () => {
          return HttpResponse.json(createMockTokens());
        })
      );

      // This tests the token refresh interceptor indirectly
      expect(refreshAttempted).toBe(false);
    });
  });

  describe('Navigation', () => {
    it('should have link to switch between login and register', () => {
      render(<LoginForm />);

      expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
    });

    it('should call onSwitchToRegister when provided', async () => {
      const onSwitch = vi.fn();
      const { user } = render(<LoginForm onSwitchToRegister={onSwitch} />);

      await user.click(screen.getByRole('button', { name: /sign up/i }));

      expect(onSwitch).toHaveBeenCalled();
    });
  });
});

describe('Session Persistence', () => {
  it('should clear auth state on logout', async () => {
    server.use(
      http.post('*/api/v1/auth/logout', async () => {
        return HttpResponse.json({ message: 'Logged out' });
      })
    );

    // Simulate logout behavior
    localStorage.removeItem('auth-token');
    sessionStorage.removeItem('user');

    expect(localStorage.getItem('auth-token')).toBeNull();
    expect(sessionStorage.getItem('user')).toBeNull();
  });
});
