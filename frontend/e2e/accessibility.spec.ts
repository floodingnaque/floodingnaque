/**
 * Accessibility E2E Tests
 *
 * Automated a11y scanning using @axe-core/playwright.
 * Runs axe analysis on key pages to catch WCAG violations.
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Pages to scan for accessibility violations.
 * Each entry maps a human-readable name to a route.
 */
const pages = [
  { name: 'Landing', path: '/' },
  { name: 'Login', path: '/login' },
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Prediction', path: '/predict' },
  { name: 'Alerts', path: '/alerts' },
  { name: 'Reports', path: '/reports' },
  { name: 'Settings', path: '/settings' },
];

test.describe('Accessibility', () => {
  for (const { name, path } of pages) {
    test(`${name} page should have no critical a11y violations`, async ({ page }) => {
      await page.goto(path);

      // Wait for the page to settle (hydration, lazy loads, etc.)
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        // Only fail on serious / critical violations
        .options({ resultTypes: ['violations'] })
        .analyze();

      const serious = results.violations.filter(
        (v) => v.impact === 'critical' || v.impact === 'serious',
      );

      // Log all violations for debugging
      if (serious.length > 0) {
        console.log(
          `[${name}] a11y violations:\n`,
          JSON.stringify(serious, null, 2),
        );
      }

      expect(serious).toEqual([]);
    });
  }
});
