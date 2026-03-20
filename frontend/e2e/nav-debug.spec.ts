/**
 * Deep Navigation Debug - captures screenshots + HTML + console output
 * for each page to diagnose why content doesn't render.
 */

import { test, type Page } from "@playwright/test";

const ADMIN_EMAIL = "floodingnaque@gmail.com";
const ADMIN_PASS = "Admin_floodingnaque_2025!";

async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  await page.getByRole("textbox", { name: /email/i }).fill(ADMIN_EMAIL);
  await page.getByRole("textbox", { name: /password/i }).fill(ADMIN_PASS);
  await page.getByRole("button", { name: /sign in/i }).click();

  await page.waitForURL("**/dashboard", { timeout: 15000 });
}

test.describe("Deep Nav Debug", () => {
  test.setTimeout(180_000);

  test("Capture every page state", async ({ page }) => {
    const consoleMessages: string[] = [];
    const apiErrors: string[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleMessages.push(`[ERROR] ${msg.text()}`);
      }
    });

    page.on("response", (response) => {
      const url = response.url();
      const status = response.status();
      if (url.includes("/api/") && status >= 400) {
        apiErrors.push(`${status} ${response.request().method()} ${url}`);
      }
    });

    // Login
    await loginAsAdmin(page);
    console.log("✅ Logged in successfully, now on dashboard");

    // Capture dashboard state
    await page.waitForTimeout(3000);

    // Get page text and structure
    const bodyHTML = await page.evaluate(() =>
      document.body.innerHTML.slice(0, 5000),
    );
    console.log("\n--- DASHBOARD HTML (first 5000 chars) ---");
    console.log(bodyHTML);

    // Check what headings we see on dashboard
    const allH1 = await page.locator("h1").allTextContents();
    const allH2 = await page.locator("h2").allTextContents();
    console.log("\n--- HEADINGS ---");
    console.log("H1:", JSON.stringify(allH1));
    console.log("H2:", JSON.stringify(allH2));

    // Check if the main content area is empty
    const mainContent = await page
      .locator("main")
      .innerHTML()
      .catch(() => "NO <main> TAG");
    console.log("\n--- MAIN CONTENT (first 2000 chars) ---");
    console.log(mainContent.slice(0, 2000));

    // Check for visible text
    const bodyText = await page.locator("body").textContent();
    console.log("\n--- BODY TEXT (first 1000 chars) ---");
    console.log((bodyText ?? "").slice(0, 1000));

    // Now try navigating to a few key pages via sidebar clicks
    const navPages = [
      { name: "Dashboard", path: "/dashboard" },
      { name: "Prediction", path: "/predict" },
      { name: "Admin Panel", path: "/admin" },
      { name: "User Management", path: "/admin/users" },
      { name: "System Logs", path: "/admin/logs" },
    ];

    for (const pg of navPages) {
      console.log(`\n${"=".repeat(60)}`);
      console.log(`  TESTING: ${pg.name} (${pg.path})`);
      console.log("=".repeat(60));

      await page.goto(pg.path);
      await page.waitForLoadState("networkidle", { timeout: 10000 });
      await page.waitForTimeout(2000);

      // Check URL
      console.log(`  URL: ${page.url()}`);

      // All headings
      const h1s = await page.locator("h1").allTextContents();
      const h2s = await page.locator("h2").allTextContents();
      console.log(`  H1: ${JSON.stringify(h1s)}`);
      console.log(`  H2: ${JSON.stringify(h2s)}`);

      // Check for error boundary
      const errorText = await page
        .locator("text=/something went wrong|error|crash/i")
        .allTextContents();
      if (errorText.length > 0) {
        console.log(`  ❌ ERROR TEXT FOUND: ${JSON.stringify(errorText)}`);
      }

      // Check for loading spinners still present
      const loaders = await page
        .locator(
          '[class*="animate-spin"], [class*="loader"], [class*="loading"]',
        )
        .count();
      console.log(`  Loading spinners visible: ${loaders}`);

      // Check main / outlet content
      const outlet = await page
        .locator("main")
        .innerHTML()
        .catch(() => "");
      const outletText = outlet
        .replace(/<[^>]*>/g, " ")
        .replace(/\s+/g, " ")
        .trim();
      console.log(`  Main content text: "${outletText.slice(0, 300)}"`);

      // Take screenshot
      await page.screenshot({
        path: `test-results/debug-${pg.name.replace(/\s/g, "-").toLowerCase()}.png`,
        fullPage: true,
      });
      console.log(`  Screenshot saved`);
    }

    // Report collected errors
    if (consoleMessages.length > 0) {
      console.log("\n--- CONSOLE ERRORS ---");
      for (const msg of consoleMessages) {
        console.log(`  ${msg.slice(0, 300)}`);
      }
    }

    if (apiErrors.length > 0) {
      console.log("\n--- API ERRORS ---");
      for (const err of apiErrors) {
        console.log(`  ${err}`);
      }
    }
  });
});
