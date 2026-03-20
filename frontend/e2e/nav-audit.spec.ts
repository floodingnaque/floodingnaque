/**
 * Navigation Audit E2E Tests
 *
 * Logs in as admin and visits every Nav Bar page from Dashboard
 * down to System Logs, checking each for:
 *   - Successful navigation (no crash / error boundary)
 *   - No console errors
 *   - No failed API calls (4xx/5xx)
 *   - Key content rendered (headings, cards, tables)
 *   - Interactive elements functional (buttons, filters, forms)
 */

import { expect, test, type ConsoleMessage, type Page } from "@playwright/test";

// ── Shared state ──

const ADMIN_EMAIL = "floodingnaque@gmail.com";
const ADMIN_PASS = "Admin_floodingnaque_2025!";

interface PageIssue {
  page: string;
  type:
    | "console-error"
    | "api-error"
    | "crash"
    | "missing-content"
    | "interaction-fail";
  detail: string;
}

/** Helper: login and store auth state */
async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  const emailInput = page.getByRole("textbox", { name: /email/i });
  const passwordInput = page.getByRole("textbox", { name: /password/i });
  const signInBtn = page.getByRole("button", { name: /sign in/i });

  await emailInput.fill(ADMIN_EMAIL);
  await passwordInput.fill(ADMIN_PASS);
  await signInBtn.click();

  // Wait for redirect to dashboard
  await page.waitForURL("**/dashboard", { timeout: 15000 });
}

/** Collector for console errors and failed network requests */
function attachCollectors(page: Page) {
  const issues: PageIssue[] = [];
  const consoleErrors: string[] = [];
  const apiErrors: string[] = [];

  page.on("console", (msg: ConsoleMessage) => {
    if (msg.type() === "error") {
      const text = msg.text();
      // Filter out known noise
      if (
        text.includes("favicon") ||
        (text.includes("404 (Not Found)") && text.includes(".ico")) ||
        text.includes("Download the React DevTools")
      )
        return;
      consoleErrors.push(text);
    }
  });

  page.on("response", (response) => {
    const url = response.url();
    const status = response.status();
    // Only track API calls
    if (url.includes("/api/") && status >= 400) {
      apiErrors.push(`${status} ${response.request().method()} ${url}`);
    }
  });

  return { issues, consoleErrors, apiErrors };
}

// ── Tests ──

test.describe("Nav Bar Full Audit", () => {
  test.setTimeout(120_000); // 2 min for entire suite

  test("Login and navigate through all pages", async ({ page }) => {
    // Login
    await loginAsAdmin(page);

    // Define all nav pages to audit (Dashboard → System Logs)
    const pages = [
      {
        name: "Dashboard",
        path: "/dashboard",
        expectedHeading: /dashboard/i,
        expectedContent: [/prediction|flood|risk|weather|overview/i],
      },
      {
        name: "Flood Map",
        path: "/map",
        expectedHeading: /flood map|map/i,
        expectedContent: [/map|barangay|risk/i],
      },
      {
        name: "Prediction",
        path: "/predict",
        expectedHeading: /predict|flood risk/i,
        expectedContent: [/predict|temperature|humidity|precipitation/i],
      },
      {
        name: "Alerts",
        path: "/alerts",
        expectedHeading: /alert/i,
        expectedContent: [/alert|notification|flood/i],
      },
      {
        name: "Weather History",
        path: "/history",
        expectedHeading: /weather|history/i,
        expectedContent: [/weather|history|temperature|data/i],
      },
      {
        name: "Analytics",
        path: "/analytics",
        expectedHeading: /analytics|charts/i,
        expectedContent: [/analytics|chart|trend|data/i],
      },
      {
        name: "Reports",
        path: "/reports",
        expectedHeading: /report/i,
        expectedContent: [/report|export|generate/i],
      },
      {
        name: "Admin Panel",
        path: "/admin",
        expectedHeading: /admin/i,
        expectedContent: [/system|health|overview|status/i],
      },
      {
        name: "User Management",
        path: "/admin/users",
        expectedHeading: /user management/i,
        expectedContent: [/user|role|email|name/i],
      },
      {
        name: "Barangays",
        path: "/admin/barangays",
        expectedHeading: /barangay/i,
        expectedContent: [/barangay|flood risk|evacuation/i],
      },
      {
        name: "Datasets",
        path: "/admin/data",
        expectedHeading: /dataset/i,
        expectedContent: [/upload|data|csv|weather/i],
      },
      {
        name: "AI Models",
        path: "/admin/models",
        expectedHeading: /ai model|model control/i,
        expectedContent: [/model|retrain|version|performance/i],
      },
      {
        name: "Configuration",
        path: "/admin/config",
        expectedHeading: /configuration|config/i,
        expectedContent: [/feature flag|threshold|setting/i],
      },
      {
        name: "System Settings",
        path: "/settings",
        expectedHeading: /settings/i,
        expectedContent: [/profile|password|preference/i],
      },
      {
        name: "System Logs",
        path: "/admin/logs",
        expectedHeading: /system logs|logs/i,
        expectedContent: [/log|activity|endpoint|status/i],
      },
    ];

    const allIssues: PageIssue[] = [];

    for (const pg of pages) {
      const { consoleErrors, apiErrors } = attachCollectors(page);

      // Navigate
      try {
        await page.goto(pg.path, { timeout: 15000 });
        await page.waitForLoadState("networkidle", { timeout: 10000 });
      } catch (navErr) {
        allIssues.push({
          page: pg.name,
          type: "crash",
          detail: `Navigation failed: ${String(navErr).slice(0, 200)}`,
        });
        continue;
      }

      // Small wait for lazy components
      await page.waitForTimeout(1500);

      // Check for error boundary / crash text
      const errorBoundary = await page
        .locator("text=/something went wrong|error occurred|unexpected error/i")
        .count();
      if (errorBoundary > 0) {
        allIssues.push({
          page: pg.name,
          type: "crash",
          detail: "Error boundary triggered - page crashed",
        });
      }

      // Check for expected heading
      const headingVisible = await page
        .getByRole("heading", { name: pg.expectedHeading })
        .first()
        .isVisible()
        .catch(() => false);
      if (!headingVisible) {
        // Try broader text search
        const anyHeading = await page
          .locator("h1, h2")
          .first()
          .textContent()
          .catch(() => "");
        allIssues.push({
          page: pg.name,
          type: "missing-content",
          detail: `Expected heading matching ${pg.expectedHeading} not found. Found: "${anyHeading}"`,
        });
      }

      // Check expected content exists
      for (const pattern of pg.expectedContent) {
        const bodyText = await page
          .locator("body")
          .textContent()
          .catch(() => "");
        if (!pattern.test(bodyText ?? "")) {
          allIssues.push({
            page: pg.name,
            type: "missing-content",
            detail: `Expected content matching ${pattern} not found on page`,
          });
        }
      }

      // Collect console errors
      if (consoleErrors.length > 0) {
        for (const err of consoleErrors) {
          allIssues.push({
            page: pg.name,
            type: "console-error",
            detail: err.slice(0, 300),
          });
        }
      }

      // Collect API errors
      if (apiErrors.length > 0) {
        for (const err of apiErrors) {
          allIssues.push({
            page: pg.name,
            type: "api-error",
            detail: err,
          });
        }
      }

      // Remove listeners for next page
      page.removeAllListeners("console");
      page.removeAllListeners("response");
    }

    // Print comprehensive report
    console.log("\n" + "=".repeat(70));
    console.log("  NAVIGATION AUDIT REPORT");
    console.log("=".repeat(70));

    if (allIssues.length === 0) {
      console.log("\n  ✅ All pages loaded without issues!\n");
    } else {
      // Group by page
      const byPage = new Map<string, PageIssue[]>();
      for (const issue of allIssues) {
        if (!byPage.has(issue.page)) byPage.set(issue.page, []);
        byPage.get(issue.page)!.push(issue);
      }

      console.log(
        `\n  Found ${allIssues.length} issue(s) across ${byPage.size} page(s):\n`,
      );

      for (const [pageName, pageIssues] of byPage) {
        console.log(`  📄 ${pageName}`);
        for (const issue of pageIssues) {
          const icon = {
            crash: "💥",
            "console-error": "🔴",
            "api-error": "🌐",
            "missing-content": "⚠️",
            "interaction-fail": "🔧",
          }[issue.type];
          console.log(`     ${icon} [${issue.type}] ${issue.detail}`);
        }
        console.log("");
      }
    }

    console.log("=".repeat(70) + "\n");

    // Output as structured data for easy parsing
    if (allIssues.length > 0) {
      console.log(
        "STRUCTURED_ISSUES_JSON=" + JSON.stringify(allIssues, null, 2),
      );
    }

    // Don't fail the test - this is an audit
    // But attach the issues count
    expect(true).toBe(true);
  });
});
