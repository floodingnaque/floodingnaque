/**
 * Flood Prediction E2E Tests
 *
 * End-to-end tests for the flood risk prediction flow using Playwright.
 */

import { test, expect } from '@playwright/test';

// Mock data for predictions
const mockPredictionSafe = {
  prediction: 0,
  probability: 0.15,
  risk_level: 0,
  risk_label: 'Safe',
  confidence: 0.92,
  model_version: 'v1.0.0',
  features_used: ['temperature', 'humidity', 'precipitation', 'wind_speed'],
  timestamp: new Date().toISOString(),
  request_id: 'test-request-safe',
};

const mockPredictionAlert = {
  ...mockPredictionSafe,
  prediction: 1,
  probability: 0.65,
  risk_level: 1,
  risk_label: 'Alert',
  request_id: 'test-request-alert',
};

const mockPredictionCritical = {
  ...mockPredictionSafe,
  prediction: 1,
  probability: 0.92,
  risk_level: 2,
  risk_label: 'Critical',
  request_id: 'test-request-critical',
};

test.describe('Flood Prediction', () => {
  test.beforeEach(async ({ page }) => {
    // Mock auth for protected routes
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
  });

  test.describe('Prediction Form', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/predict');
    });

    test('should display prediction form', async ({ page }) => {
      await expect(page.getByText(/weather parameters/i)).toBeVisible();
      await expect(page.getByLabel(/temperature/i)).toBeVisible();
      await expect(page.getByLabel(/humidity/i)).toBeVisible();
      await expect(page.getByLabel(/precipitation/i)).toBeVisible();
      await expect(page.getByLabel(/wind speed/i)).toBeVisible();
      await expect(page.getByLabel(/pressure/i)).toBeVisible();
    });

    test('should show helper text for each field', async ({ page }) => {
      await expect(page.getByText(/temperature in degrees celsius/i)).toBeVisible();
      await expect(page.getByText(/relative humidity/i)).toBeVisible();
      await expect(page.getByText(/rainfall amount/i)).toBeVisible();
      await expect(page.getByText(/meters per second/i)).toBeVisible();
    });

    test('should validate required fields', async ({ page }) => {
      await page.getByRole('button', { name: /predict/i }).click();

      // Check for validation errors
      const errors = await page.locator('.text-destructive').count();
      expect(errors).toBeGreaterThan(0);
    });

    test('should validate temperature range', async ({ page }) => {
      await page.getByLabel(/temperature/i).fill('-60');
      await page.getByRole('button', { name: /predict/i }).click();

      await expect(page.getByText(/at least -50/i)).toBeVisible();
    });

    test('should validate humidity range', async ({ page }) => {
      await page.getByLabel(/humidity/i).fill('150');
      await page.getByRole('button', { name: /predict/i }).click();

      await expect(page.getByText(/at most 100/i)).toBeVisible();
    });

    test('should allow optional pressure field', async ({ page }) => {
      await page.route('**/api/v1/predict/predict', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify(mockPredictionSafe),
        });
      });

      await page.getByLabel(/temperature/i).fill('25');
      await page.getByLabel(/humidity/i).fill('60');
      await page.getByLabel(/precipitation/i).fill('10');
      await page.getByLabel(/wind speed/i).fill('12');
      // Don't fill pressure

      await page.getByRole('button', { name: /predict/i }).click();

      // Should not show validation error for pressure
      await expect(page.getByText(/pressure.*required/i)).not.toBeVisible();
    });
  });

  test.describe('Prediction Results', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/predict');
    });

    test('should display Safe result for low-risk conditions', async ({ page }) => {
      await page.route('**/api/v1/predict/predict', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify(mockPredictionSafe),
        });
      });

      await page.getByLabel(/temperature/i).fill('20');
      await page.getByLabel(/humidity/i).fill('50');
      await page.getByLabel(/precipitation/i).fill('5');
      await page.getByLabel(/wind speed/i).fill('8');

      await page.getByRole('button', { name: /predict/i }).click();

      await expect(page.getByText(/safe/i)).toBeVisible();
    });

    test('should display Alert result for moderate-risk conditions', async ({ page }) => {
      await page.route('**/api/v1/predict/predict', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify(mockPredictionAlert),
        });
      });

      await page.getByLabel(/temperature/i).fill('25');
      await page.getByLabel(/humidity/i).fill('80');
      await page.getByLabel(/precipitation/i).fill('30');
      await page.getByLabel(/wind speed/i).fill('20');

      await page.getByRole('button', { name: /predict/i }).click();

      await expect(page.getByText(/alert/i)).toBeVisible();
    });

    test('should display Critical result for high-risk conditions', async ({ page }) => {
      await page.route('**/api/v1/predict/predict', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify(mockPredictionCritical),
        });
      });

      await page.getByLabel(/temperature/i).fill('28');
      await page.getByLabel(/humidity/i).fill('95');
      await page.getByLabel(/precipitation/i).fill('75');
      await page.getByLabel(/wind speed/i).fill('30');

      await page.getByRole('button', { name: /predict/i }).click();

      await expect(page.getByText(/critical/i)).toBeVisible();
    });

    test('should display probability percentage', async ({ page }) => {
      await page.route('**/api/v1/predict/predict', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            ...mockPredictionAlert,
            probability: 0.72,
          }),
        });
      });

      await page.getByLabel(/temperature/i).fill('25');
      await page.getByLabel(/humidity/i).fill('80');
      await page.getByLabel(/precipitation/i).fill('30');
      await page.getByLabel(/wind speed/i).fill('20');

      await page.getByRole('button', { name: /predict/i }).click();

      // Should display 72% somewhere
      await expect(page.getByText(/72%/)).toBeVisible();
    });
  });

  test.describe('Loading State', () => {
    test('should show loading spinner during prediction', async ({ page }) => {
      await page.goto('/predict');

      await page.route('**/api/v1/predict/predict', async (route) => {
        await new Promise((r) => setTimeout(r, 1500));
        await route.fulfill({
          status: 200,
          body: JSON.stringify(mockPredictionSafe),
        });
      });

      await page.getByLabel(/temperature/i).fill('25');
      await page.getByLabel(/humidity/i).fill('75');
      await page.getByLabel(/precipitation/i).fill('10');
      await page.getByLabel(/wind speed/i).fill('12');

      await page.getByRole('button', { name: /predict/i }).click();

      // Button should show loading state
      await expect(page.getByText(/analyzing/i)).toBeVisible();
      await expect(page.getByRole('button')).toBeDisabled();
    });

    test('should disable form inputs during loading', async ({ page }) => {
      await page.goto('/predict');

      await page.route('**/api/v1/predict/predict', async (route) => {
        await new Promise((r) => setTimeout(r, 1500));
        await route.fulfill({
          status: 200,
          body: JSON.stringify(mockPredictionSafe),
        });
      });

      await page.getByLabel(/temperature/i).fill('25');
      await page.getByLabel(/humidity/i).fill('75');
      await page.getByLabel(/precipitation/i).fill('10');
      await page.getByLabel(/wind speed/i).fill('12');

      await page.getByRole('button', { name: /predict/i }).click();

      // Inputs should be disabled
      await expect(page.getByLabel(/temperature/i)).toBeDisabled();
      await expect(page.getByLabel(/humidity/i)).toBeDisabled();
    });
  });

  test.describe('Error Handling', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/predict');
    });

    test('should display error message on API failure', async ({ page }) => {
      await page.route('**/api/v1/predict/predict', async (route) => {
        await route.fulfill({
          status: 500,
          body: JSON.stringify({
            code: 'MODEL_ERROR',
            message: 'Prediction model is unavailable',
          }),
        });
      });

      await page.getByLabel(/temperature/i).fill('25');
      await page.getByLabel(/humidity/i).fill('75');
      await page.getByLabel(/precipitation/i).fill('10');
      await page.getByLabel(/wind speed/i).fill('12');

      await page.getByRole('button', { name: /predict/i }).click();

      await expect(page.getByRole('alert')).toBeVisible();
    });

    test('should handle network errors', async ({ page }) => {
      await page.route('**/api/v1/predict/predict', async (route) => {
        await route.abort('failed');
      });

      await page.getByLabel(/temperature/i).fill('25');
      await page.getByLabel(/humidity/i).fill('75');
      await page.getByLabel(/precipitation/i).fill('10');
      await page.getByLabel(/wind speed/i).fill('12');

      await page.getByRole('button', { name: /predict/i }).click();

      await expect(page.getByRole('alert')).toBeVisible();
    });

    test('should allow retry after error', async ({ page }) => {
      let requestCount = 0;
      await page.route('**/api/v1/predict/predict', async (route) => {
        requestCount++;
        if (requestCount === 1) {
          await route.fulfill({
            status: 500,
            body: JSON.stringify({ message: 'Server error' }),
          });
        } else {
          await route.fulfill({
            status: 200,
            body: JSON.stringify(mockPredictionSafe),
          });
        }
      });

      await page.getByLabel(/temperature/i).fill('25');
      await page.getByLabel(/humidity/i).fill('75');
      await page.getByLabel(/precipitation/i).fill('10');
      await page.getByLabel(/wind speed/i).fill('12');

      // First attempt fails
      await page.getByRole('button', { name: /predict/i }).click();
      await expect(page.getByRole('alert')).toBeVisible();

      // Second attempt succeeds
      await page.getByRole('button', { name: /predict/i }).click();
      await expect(page.getByText(/safe/i)).toBeVisible();
    });
  });

  test.describe('Multiple Predictions', () => {
    test('should allow making multiple predictions', async ({ page }) => {
      await page.goto('/predict');

      let predictionCount = 0;
      await page.route('**/api/v1/predict/predict', async (route) => {
        predictionCount++;
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            ...mockPredictionSafe,
            request_id: `prediction-${predictionCount}`,
          }),
        });
      });

      // First prediction
      await page.getByLabel(/temperature/i).fill('20');
      await page.getByLabel(/humidity/i).fill('50');
      await page.getByLabel(/precipitation/i).fill('5');
      await page.getByLabel(/wind speed/i).fill('8');
      await page.getByRole('button', { name: /predict/i }).click();

      await expect(page.getByText(/safe/i)).toBeVisible();

      // Clear and make second prediction
      await page.getByLabel(/temperature/i).clear();
      await page.getByLabel(/humidity/i).clear();
      await page.getByLabel(/precipitation/i).clear();
      await page.getByLabel(/wind speed/i).clear();

      await page.getByLabel(/temperature/i).fill('30');
      await page.getByLabel(/humidity/i).fill('90');
      await page.getByLabel(/precipitation/i).fill('60');
      await page.getByLabel(/wind speed/i).fill('25');
      await page.getByRole('button', { name: /predict/i }).click();

      expect(predictionCount).toBe(2);
    });
  });
});

test.describe('Prediction - Mobile', () => {
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
  });

  test('should display prediction form on mobile', async ({ page }) => {
    await page.goto('/predict');

    await expect(page.getByLabel(/temperature/i)).toBeVisible();
    await expect(page.getByLabel(/humidity/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /predict/i })).toBeVisible();
  });

  test('should use single column layout on mobile', async ({ page }) => {
    await page.goto('/predict');

    // Form should be stacked on mobile - check field visibility
    const tempInput = page.getByLabel(/temperature/i);
    const humidityInput = page.getByLabel(/humidity/i);

    const tempBox = await tempInput.boundingBox();
    const humidityBox = await humidityInput.boundingBox();

    // On mobile, fields should be stacked (same x position)
    expect(tempBox?.x).toBeCloseTo(humidityBox?.x || 0, 0);
  });

  test('should be scrollable when form is long', async ({ page }) => {
    await page.goto('/predict');

    // Should be able to scroll to submit button
    const button = page.getByRole('button', { name: /predict/i });
    await button.scrollIntoViewIfNeeded();
    await expect(button).toBeVisible();
  });
});

test.describe('Prediction - Accessibility', () => {
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
    await page.goto('/predict');
  });

  test('should have proper form labels', async ({ page }) => {
    const labels = ['temperature', 'humidity', 'precipitation', 'wind speed', 'pressure'];

    for (const label of labels) {
      const input = page.getByLabel(new RegExp(label, 'i'));
      await expect(input).toBeVisible();
    }
  });

  test('should support keyboard navigation', async ({ page }) => {
    // Tab through the form
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Should eventually reach the submit button
    const activeElement = page.locator(':focus');
    await expect(activeElement).toBeVisible();
  });

  test('should announce errors to screen readers', async ({ page }) => {
    await page.getByRole('button', { name: /predict/i }).click();

    // Error messages should have role=alert or be in aria-live region
    await expect(page.locator('.text-destructive')).toBeVisible();
  });
});
