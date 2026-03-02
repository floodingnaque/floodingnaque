/**
 * Landing Page E2E Tests
 *
 * Verifies all key sections of the public landing page render correctly,
 * anchor-scroll IDs are present, and CTA buttons link to the right routes.
 */

import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock prediction endpoint to avoid real API calls from LiveStatusRibbon
    await page.route('**/api/v1/predict*', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify({
          risk_level: 0,
          probability: 0.12,
          weather_data: {
            temperature: 28,
            humidity: 75,
            precipitation: 2.5,
            wind_speed: 8,
            cloud_cover: 60,
          },
        }),
      });
    });

    await page.goto('/');
  });

  test('should render the hero section with headline', async ({ page }) => {
    await expect(page.locator('#hero')).toBeVisible();
    await expect(page.getByRole('heading', { name: /Flood Detection/i })).toBeVisible();
  });

  test('should render the live status ribbon', async ({ page }) => {
    await expect(page.locator('#live-status')).toBeVisible();
    await expect(page.getByText('LIVE')).toBeVisible();
  });

  test('should render all anchor-scroll sections', async ({ page }) => {
    const sectionIds = [
      'hero',
      'live-status',
      'stats',
      'how-it-works',
      'features',
      'risk-levels',
      'barangay-map',
      'cta',
      'footer',
    ];

    for (const id of sectionIds) {
      await expect(page.locator(`#${id}`)).toBeAttached();
    }
  });

  test('should render the stats row with four stats', async ({ page }) => {
    await expect(page.getByText('Official Flood Records')).toBeVisible();
    await expect(page.getByText('Model Accuracy')).toBeVisible();
    await expect(page.getByText('Barangays Monitored')).toBeVisible();
    await expect(page.getByText('Training Samples')).toBeVisible();
  });

  test('should render the how-it-works section with three steps', async ({ page }) => {
    await expect(page.getByText('Collect Weather Data')).toBeVisible();
    await expect(page.getByText(/Predict with ML/)).toBeVisible();
    await expect(page.getByText('Alert in Real-Time')).toBeVisible();
  });

  test('should render feature cards', async ({ page }) => {
    await expect(page.getByText('Barangay Risk Map')).toBeVisible();
    await expect(page.getByText('AI-Powered Prediction')).toBeVisible();
  });

  test('should render risk level explainer', async ({ page }) => {
    await expect(page.locator('#risk-levels')).toBeAttached();
    await expect(page.getByText('SAFE').first()).toBeVisible();
    await expect(page.getByText('ALERT').first()).toBeVisible();
    await expect(page.getByText('CRITICAL').first()).toBeVisible();
  });

  test('should render dual CTA section', async ({ page }) => {
    await expect(page.getByText('For Residents')).toBeVisible();
    await expect(page.getByText(/For LGU/)).toBeVisible();
  });

  test('should have Sign In link pointing to /login', async ({ page }) => {
    const signIn = page.locator('nav a[href="/login"]').first();
    await expect(signIn).toBeVisible();
  });

  test('should render footer with team credits', async ({ page }) => {
    await expect(page.locator('#footer')).toBeAttached();
    await expect(page.getByText('Andam')).toBeVisible();
    await expect(page.getByText('Quiray')).toBeVisible();
  });

  test('CTA buttons should link to login', async ({ page }) => {
    const residentCTA = page.locator('#cta a[href="/login"]').first();
    await expect(residentCTA).toBeVisible();

    const lguCTA = page.locator('#cta a[href="/login?role=lgu"]').first();
    await expect(lguCTA).toBeVisible();
  });
});

test.describe('Landing Page - Mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should render hero and be scrollable', async ({ page }) => {
    await page.route('**/api/v1/predict*', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ risk_level: 0, probability: 0.1 }),
      });
    });

    await page.goto('/');

    await expect(page.locator('#hero')).toBeVisible();

    // Should be scrollable to footer
    await page.evaluate(() =>
      document.getElementById('footer')?.scrollIntoView({ behavior: 'instant' }),
    );
    const footer = page.locator('#footer');
    await expect(footer).toBeVisible();
  });
});
