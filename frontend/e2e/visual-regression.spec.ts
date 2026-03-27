/**
 * Visual Regression Tests
 *
 * Uses Playwright's built-in `toHaveScreenshot()` for pixel-level comparison.
 * Run with: npx playwright test e2e/visual-regression.spec.ts
 * Update snapshots: npx playwright test e2e/visual-regression.spec.ts --update-snapshots
 */

import { expect, test } from "@playwright/test";

test.describe("Visual Regression", () => {
  test.beforeEach(async ({ page }) => {
    // Disable animations for deterministic screenshots
    await page.addStyleTag({
      content: `
        *, *::before, *::after {
          animation-duration: 0s !important;
          animation-delay: 0s !important;
          transition-duration: 0s !important;
          transition-delay: 0s !important;
        }
      `,
    });
  });

  test("Login page", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("login-page.png", {
      fullPage: true,
    });
  });

  test("Register page", async ({ page }) => {
    await page.goto("/register");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("register-page.png", {
      fullPage: true,
    });
  });

  test("Landing page hero", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Capture just the viewport (above the fold)
    await expect(page).toHaveScreenshot("landing-hero.png");
  });

  test("History page - weather tab", async ({ page }) => {
    // Navigate with auth bypass if possible, else just check layout
    await page.goto("/history?tab=weather");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("history-weather-tab.png", {
      fullPage: true,
    });
  });

  test("History page - predictions tab", async ({ page }) => {
    await page.goto("/history?tab=predictions");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("history-predictions-tab.png", {
      fullPage: true,
    });
  });
});

test.describe("Component Visual Regression", () => {
  test.beforeEach(async ({ page }) => {
    await page.addStyleTag({
      content: `
        *, *::before, *::after {
          animation-duration: 0s !important;
          animation-delay: 0s !important;
          transition-duration: 0s !important;
          transition-delay: 0s !important;
        }
      `,
    });
  });

  test("Dark mode toggle", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    // Screenshot in light mode
    await expect(page).toHaveScreenshot("login-light-mode.png");

    // Toggle dark mode if theme switcher exists
    const themeToggle = page.locator(
      '[data-testid="theme-toggle"], [aria-label*="theme"], [aria-label*="dark"]',
    );
    if ((await themeToggle.count()) > 0) {
      await themeToggle.first().click();
      await page.waitForTimeout(200);
      await expect(page).toHaveScreenshot("login-dark-mode.png");
    }
  });

  test("Mobile responsive - login", async ({ page, browserName }) => {
    test.skip(
      browserName !== "chromium",
      "Mobile viewport test only on Chromium",
    );
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("login-mobile.png", {
      fullPage: true,
    });
  });
});
