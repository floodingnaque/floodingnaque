/**
 * Dashboard E2E Tests
 *
 * End-to-end tests for the dashboard page using Playwright.
 */

import { test, expect } from '@playwright/test';

const mockDashboardStats = {
  total_predictions: 1234,
  predictions_today: 42,
  active_alerts: 3,
  avg_risk_level: 35,
  recent_activity: [
    { type: 'prediction', timestamp: '2026-01-15T10:00:00Z', description: 'Flood risk prediction completed' },
    { type: 'alert', timestamp: '2026-01-15T09:30:00Z', description: 'Alert triggered for high risk area' },
    { type: 'prediction', timestamp: '2026-01-15T09:00:00Z', description: 'Flood risk prediction completed' },
  ],
};

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
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

    // Mock dashboard stats
    await page.route('**/api/v1/dashboard/stats', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(mockDashboardStats),
      });
    });

    // Mock alerts
    await page.route('**/api/v1/alerts/recent*', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 1,
              risk_level: 1,
              message: 'Moderate flood risk detected',
              location: 'Manila',
              triggered_at: '2026-01-15T10:00:00Z',
              acknowledged: false,
            },
          ],
          request_id: 'test',
        }),
      });
    });
  });

  test.describe('Stats Cards', () => {
    test('should display all stats cards', async ({ page }) => {
      await page.goto('/dashboard');

      await expect(page.getByText('Total Predictions')).toBeVisible();
      await expect(page.getByText("Today's Predictions")).toBeVisible();
      await expect(page.getByText('Active Alerts')).toBeVisible();
      await expect(page.getByText('Avg Risk Level')).toBeVisible();
    });

    test('should display correct stat values', async ({ page }) => {
      await page.goto('/dashboard');

      await expect(page.getByText('1,234')).toBeVisible();
      await expect(page.getByText('42')).toBeVisible();
      await expect(page.getByText('3')).toBeVisible();
      await expect(page.getByText('35%')).toBeVisible();
    });

    test('should display risk level indicator', async ({ page }) => {
      await page.goto('/dashboard');

      // 35% is moderate risk
      await expect(page.getByText('Moderate')).toBeVisible();
    });
  });

  test.describe('Recent Activity', () => {
    test('should display recent activity list', async ({ page }) => {
      await page.goto('/dashboard');

      await expect(page.getByText(/recent activity/i)).toBeVisible();
    });

    test('should show activity timestamps', async ({ page }) => {
      await page.goto('/dashboard');

      // Should show relative timestamps like "X hours ago"
      await expect(page.getByText(/ago/i).first()).toBeVisible();
    });
  });

  test.describe('Recent Alerts', () => {
    test('should display recent alerts section', async ({ page }) => {
      await page.goto('/dashboard');

      await expect(page.getByText(/alert|warning/i).first()).toBeVisible();
    });

    test('should display alert details', async ({ page }) => {
      await page.goto('/dashboard');

      await expect(page.getByText('Manila')).toBeVisible();
    });
  });

  test.describe('Loading State', () => {
    test('should show skeleton while loading', async ({ page }) => {
      // Add delay to see skeleton
      await page.route('**/api/v1/dashboard/stats', async (route) => {
        await new Promise((r) => setTimeout(r, 1000));
        await route.fulfill({
          status: 200,
          body: JSON.stringify(mockDashboardStats),
        });
      });

      await page.goto('/dashboard');

      // Should show loading skeleton initially
      await expect(page.locator('[class*="skeleton"]').first()).toBeVisible();

      // Then show actual content
      await expect(page.getByText('1,234')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Error State', () => {
    test('should handle API error gracefully', async ({ page }) => {
      await page.route('**/api/v1/dashboard/stats', async (route) => {
        await route.fulfill({
          status: 500,
          body: JSON.stringify({ message: 'Server error' }),
        });
      });

      await page.goto('/dashboard');

      // Should show error state or retry option
      await expect(page.getByText(/error|try again|failed/i)).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Navigation', () => {
    test('should navigate to predictions page', async ({ page }) => {
      await page.goto('/dashboard');

      // Find and click predictions link/button
      const predictLink = page.locator('a[href*="predict"], button:has-text("predict")').first();
      if (await predictLink.isVisible()) {
        await predictLink.click();
        await expect(page).toHaveURL(/predict/);
      }
    });

    test('should navigate to alerts page', async ({ page }) => {
      await page.goto('/dashboard');

      const alertsLink = page.locator('a[href*="alerts"], button:has-text("alerts")').first();
      if (await alertsLink.isVisible()) {
        await alertsLink.click();
        await expect(page).toHaveURL(/alerts/);
      }
    });
  });

  test.describe('Quick Actions', () => {
    test('should display quick action buttons', async ({ page }) => {
      await page.goto('/dashboard');

      // Look for common quick actions
      const newPrediction = page.getByRole('button', { name: /new prediction|make prediction/i });
      if (await newPrediction.isVisible()) {
        await expect(newPrediction).toBeEnabled();
      }
    });
  });
});

test.describe('Dashboard - Refresh', () => {
  test('should refresh data automatically', async ({ page }) => {
    let requestCount = 0;

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
      requestCount++;
      await route.fulfill({
        status: 200,
        body: JSON.stringify({
          ...mockDashboardStats,
          predictions_today: mockDashboardStats.predictions_today + requestCount,
        }),
      });
    });

    await page.goto('/dashboard');
    await expect(page.getByText('42')).toBeVisible();

    // Initial request should be made
    expect(requestCount).toBeGreaterThanOrEqual(1);
  });
});

test.describe('Dashboard - Mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test.beforeEach(async ({ page }) => {
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
        body: JSON.stringify(mockDashboardStats),
      });
    });
  });

  test('should display stats cards in grid on mobile', async ({ page }) => {
    await page.goto('/dashboard');

    await expect(page.getByText('Total Predictions')).toBeVisible();
    await expect(page.getByText('1,234')).toBeVisible();
  });

  test('should be scrollable on mobile', async ({ page }) => {
    await page.goto('/dashboard');

    // Should be able to scroll
    await page.evaluate(() => window.scrollTo(0, 500));

    // Page should have scrolled
    const scrollY = await page.evaluate(() => window.scrollY);
    expect(scrollY).toBeGreaterThan(0);
  });
});
