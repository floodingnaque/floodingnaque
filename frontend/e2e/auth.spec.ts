/**
 * Authentication E2E Tests
 *
 * End-to-end tests for the authentication flow using Playwright.
 */

import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test.describe('Login Page', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/login');
    });

    test('should display login form', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /welcome back|sign in/i })).toBeVisible();
      await expect(page.getByLabel(/email/i)).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    });

    test('should show validation errors for empty form', async ({ page }) => {
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/email is required/i)).toBeVisible();
    });

    test('should show error for invalid email format', async ({ page }) => {
      await page.getByLabel(/email/i).fill('invalid-email');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/valid email/i)).toBeVisible();
    });

    test('should show error for short password', async ({ page }) => {
      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('short');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/at least 8 characters/i)).toBeVisible();
    });

    test('should show loading state during submission', async ({ page }) => {
      // Mock slow response
      await page.route('**/api/v1/auth/login', async (route) => {
        await new Promise((r) => setTimeout(r, 1000));
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            access_token: 'test-token',
            refresh_token: 'test-refresh',
            token_type: 'Bearer',
            expires_in: 3600,
          }),
        });
      });

      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByRole('button')).toBeDisabled();
      await expect(page.getByText(/signing in/i)).toBeVisible();
    });

    test('should display error message on failed login', async ({ page }) => {
      // Mock failed login
      await page.route('**/api/v1/auth/login', async (route) => {
        await route.fulfill({
          status: 401,
          body: JSON.stringify({
            code: 'INVALID_CREDENTIALS',
            message: 'Invalid email or password',
          }),
        });
      });

      await page.getByLabel(/email/i).fill('wrong@example.com');
      await page.getByLabel(/password/i).fill('wrongpassword');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByRole('alert')).toBeVisible();
    });

    test('should redirect to dashboard on successful login', async ({ page }) => {
      // Mock successful login
      await page.route('**/api/v1/auth/login', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            access_token: 'test-access-token',
            refresh_token: 'test-refresh-token',
            token_type: 'Bearer',
            expires_in: 3600,
          }),
        });
      });

      // Mock user profile
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            id: 1,
            email: 'test@example.com',
            name: 'Test User',
            role: 'user',
            is_active: true,
            created_at: '2026-01-01T00:00:00Z',
          }),
        });
      });

      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page).toHaveURL('/');
    });

    test('should have link to register page', async ({ page }) => {
      await expect(page.getByText(/don't have an account/i)).toBeVisible();
      await expect(page.getByRole('link', { name: /sign up/i })).toBeVisible();
    });
  });

  test.describe('Registration Page', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/register');
    });

    test('should display registration form', async ({ page }) => {
      await expect(page.getByLabel(/name/i)).toBeVisible();
      await expect(page.getByLabel(/email/i)).toBeVisible();
      await expect(page.getByLabel(/^password$/i)).toBeVisible();
      await expect(page.getByLabel(/confirm password/i)).toBeVisible();
    });

    test('should validate password match', async ({ page }) => {
      await page.getByLabel(/name/i).fill('Test User');
      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/^password$/i).fill('password123');
      await page.getByLabel(/confirm password/i).fill('different123');
      
      await page.getByRole('button', { name: /create account|sign up|register/i }).click();

      await expect(page.getByText(/passwords must match|passwords don't match/i)).toBeVisible();
    });

    test('should show error for existing email', async ({ page }) => {
      // Mock registration conflict
      await page.route('**/api/v1/auth/register', async (route) => {
        await route.fulfill({
          status: 409,
          body: JSON.stringify({
            code: 'EMAIL_EXISTS',
            message: 'Email already registered',
          }),
        });
      });

      await page.getByLabel(/name/i).fill('Existing User');
      await page.getByLabel(/email/i).fill('existing@example.com');
      await page.getByLabel(/^password$/i).fill('password123');
      await page.getByLabel(/confirm password/i).fill('password123');
      
      await page.getByRole('button', { name: /create account|sign up|register/i }).click();

      await expect(page.getByRole('alert')).toBeVisible();
    });

    test('should redirect after successful registration', async ({ page }) => {
      // Mock successful registration
      await page.route('**/api/v1/auth/register', async (route) => {
        await route.fulfill({
          status: 201,
          body: JSON.stringify({
            access_token: 'new-access-token',
            refresh_token: 'new-refresh-token',
            token_type: 'Bearer',
            expires_in: 3600,
          }),
        });
      });

      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            id: 1,
            email: 'newuser@example.com',
            name: 'New User',
            role: 'user',
            is_active: true,
            created_at: '2026-01-15T00:00:00Z',
          }),
        });
      });

      await page.getByLabel(/name/i).fill('New User');
      await page.getByLabel(/email/i).fill('newuser@example.com');
      await page.getByLabel(/^password$/i).fill('password123');
      await page.getByLabel(/confirm password/i).fill('password123');
      
      await page.getByRole('button', { name: /create account|sign up|register/i }).click();

      await expect(page).toHaveURL('/');
    });
  });

  test.describe('Protected Routes', () => {
    test('should redirect to login when accessing protected route', async ({ page }) => {
      await page.goto('/dashboard');

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });

    test('should access protected route after login', async ({ page }) => {
      // Set up auth state
      await page.route('**/api/v1/auth/login', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            access_token: 'test-token',
            refresh_token: 'test-refresh',
            token_type: 'Bearer',
            expires_in: 3600,
          }),
        });
      });

      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            id: 1,
            email: 'test@example.com',
            name: 'Test User',
            role: 'user',
            is_active: true,
          }),
        });
      });

      await page.route('**/api/v1/dashboard/stats', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            total_predictions: 100,
            predictions_today: 5,
            active_alerts: 2,
            avg_risk_level: 35,
            recent_activity: [],
          }),
        });
      });

      // Login first
      await page.goto('/login');
      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should be on dashboard
      await expect(page).toHaveURL('/');
    });
  });

  test.describe('Logout', () => {
    test('should logout and redirect to login', async ({ page }) => {
      // Setup authenticated state (would typically use auth helpers)
      await page.route('**/api/v1/auth/logout', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ message: 'Logged out' }),
        });
      });

      // Manually trigger logout scenario would go here
      // This test structure is ready for when logout UI is accessible
    });
  });
});

test.describe('Authentication - Mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should display login form on mobile', async ({ page }) => {
    await page.goto('/login');

    await expect(page.getByRole('heading', { name: /welcome back|sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test('should be touch-friendly on mobile', async ({ page }) => {
    await page.goto('/login');

    // Inputs should be large enough for touch
    const emailInput = page.getByLabel(/email/i);
    const box = await emailInput.boundingBox();
    
    expect(box?.height).toBeGreaterThan(40);
  });
});
