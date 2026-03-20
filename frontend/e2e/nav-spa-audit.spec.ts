/**
 * SPA Navigation Audit - uses sidebar clicks to navigate
 * (preserves auth state via SPA routing instead of full page reloads)
 */

import { test, type Page } from "@playwright/test";

const ADMIN_EMAIL = "floodingnaque@gmail.com";
const ADMIN_PASS = "Admin_floodingnaque_2025!";

interface PageIssue {
  page: string;
  type:
    | "console-error"
    | "api-error"
    | "crash"
    | "missing-content"
    | "render-fail";
  detail: string;
}

async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox", { name: /email/i }).fill(ADMIN_EMAIL);
  await page.getByRole("textbox", { name: /password/i }).fill(ADMIN_PASS);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL("**/dashboard", { timeout: 15000 });
}

test.describe("SPA Nav Audit", () => {
  test.setTimeout(180_000);

  test("Click each sidebar link and audit page content", async ({ page }) => {
    const allIssues: PageIssue[] = [];
    const allConsoleErrors: string[] = [];
    const allApiErrors: string[] = [];

    // Capture console errors globally
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        const text = msg.text();
        if (text.includes("favicon") || text.includes("React DevTools")) return;
        allConsoleErrors.push(text);
      }
    });

    // Capture API errors globally
    page.on("response", (response) => {
      const url = response.url();
      const status = response.status();
      if (url.includes("/api/") && status >= 400) {
        allApiErrors.push(`${status} ${response.request().method()} ${url}`);
      }
    });

    // Login
    await loginAsAdmin(page);
    console.log("✅ Logged in, on dashboard");
    await page.waitForTimeout(2000);

    // Verify dashboard works first
    const dashH1 = await page.locator("h1").allTextContents();
    console.log(`Dashboard headings: ${JSON.stringify(dashH1)}`);

    // Pages to test via sidebar nav
    const navPages = [
      {
        sidebarLabel: "Dashboard",
        path: "/dashboard",
        checks: {
          heading: /flood monitor|dashboard/i,
          content: [/risk|flood|barangay|weather/i],
        },
      },
      {
        sidebarLabel: "Flood Map",
        path: "/map",
        checks: {
          heading: /flood map|map/i,
          content: [/map|barangay|risk|leaflet/i],
        },
      },
      {
        sidebarLabel: "Prediction",
        path: "/predict",
        checks: {
          heading: /predict|flood risk/i,
          content: [/predict|temperature|humidity|precipitation|barangay/i],
        },
      },
      {
        sidebarLabel: "Alerts",
        path: "/alerts",
        checks: {
          heading: /alert/i,
          content: [/alert|notification|flood|active/i],
        },
      },
      {
        sidebarLabel: "Weather History",
        path: "/history",
        checks: {
          heading: /weather|history/i,
          content: [/weather|history|temperature|data|record/i],
        },
      },
      {
        sidebarLabel: "Analytics",
        path: "/analytics",
        checks: {
          heading: /analytics|chart/i,
          content: [/analytics|chart|trend|data|performance/i],
        },
      },
      {
        sidebarLabel: "Reports",
        path: "/reports",
        checks: {
          heading: /report/i,
          content: [/report|export|generate|download/i],
        },
      },
      {
        sidebarLabel: "Admin",
        path: "/admin",
        checks: {
          heading: /admin/i,
          content: [/system|health|overview|status|panel/i],
        },
      },
      {
        sidebarLabel: "User Management",
        path: "/admin/users",
        checks: {
          heading: /user management/i,
          content: [/user|role|email|account/i],
        },
      },
      {
        sidebarLabel: "Barangays",
        path: "/admin/barangays",
        checks: {
          heading: /barangay/i,
          content: [/barangay|flood risk|evacuation|population/i],
        },
      },
      {
        sidebarLabel: "Datasets",
        path: "/admin/data",
        checks: {
          heading: /dataset/i,
          content: [/upload|data|csv|weather|file/i],
        },
      },
      {
        sidebarLabel: "AI Models",
        path: "/admin/models",
        checks: {
          heading: /ai model|model control/i,
          content: [/model|retrain|version|performance|loaded/i],
        },
      },
      {
        sidebarLabel: "Configuration",
        path: "/admin/config",
        checks: {
          heading: /configuration|config/i,
          content: [/feature flag|threshold|setting/i],
        },
      },
      {
        sidebarLabel: "System Settings",
        path: "/settings",
        checks: {
          heading: /settings/i,
          content: [/profile|password|preference|theme/i],
        },
      },
      {
        sidebarLabel: "System Logs",
        path: "/admin/logs",
        checks: {
          heading: /system logs|logs/i,
          content: [/log|activity|endpoint|status/i],
        },
      },
    ];

    for (const pg of navPages) {
      console.log(`\n--- Testing: ${pg.sidebarLabel} (${pg.path}) ---`);

      // Reset error collectors for this page
      const preConsoleCount = allConsoleErrors.length;
      const preApiCount = allApiErrors.length;

      // Click sidebar link
      try {
        const sidebarLink = page
          .locator(`nav[aria-label="Main navigation"] a`)
          .filter({ hasText: pg.sidebarLabel })
          .first();
        const isVisible = await sidebarLink
          .isVisible({ timeout: 3000 })
          .catch(() => false);

        if (!isVisible) {
          allIssues.push({
            page: pg.sidebarLabel,
            type: "render-fail",
            detail: `Sidebar link "${pg.sidebarLabel}" not visible`,
          });
          console.log(`  ❌ Sidebar link not visible`);
          continue;
        }

        await sidebarLink.click();
        await page.waitForTimeout(2500); // Wait for lazy-load + API calls
        await page
          .waitForLoadState("networkidle", { timeout: 8000 })
          .catch(() => {});
      } catch (navErr) {
        allIssues.push({
          page: pg.sidebarLabel,
          type: "crash",
          detail: `Navigation click failed: ${String(navErr).slice(0, 200)}`,
        });
        console.log(`  ❌ Click failed: ${String(navErr).slice(0, 100)}`);
        continue;
      }

      // Check URL
      const currentUrl = page.url();
      const urlOk = currentUrl.includes(pg.path);
      console.log(`  URL: ${currentUrl} (${urlOk ? "✅" : "⚠️ unexpected"})`);
      if (!urlOk) {
        allIssues.push({
          page: pg.sidebarLabel,
          type: "render-fail",
          detail: `Expected URL containing ${pg.path}, got ${currentUrl}`,
        });
      }

      // Check for error boundary / crash text (match the EXACT route-error
      // fallback title "Something went wrong", not generic ErrorDisplay text)
      const errorBoundary = await page
        .locator("text=/Something went wrong/")
        .count();
      if (errorBoundary > 0) {
        allIssues.push({
          page: pg.sidebarLabel,
          type: "crash",
          detail: "Error boundary triggered - page crashed",
        });
        console.log("  💥 Error boundary triggered!");
      }

      // Get main content text
      const mainEl = page.locator("main");
      const mainExists = (await mainEl.count()) > 0;
      const mainText = mainExists
        ? ((await mainEl.textContent().catch(() => "")) ?? "")
        : ((await page
            .locator("body")
            .textContent()
            .catch(() => "")) ?? "");

      // Check heading
      const allH1 = await page
        .locator("main h1, main h2, .container h1")
        .allTextContents()
        .catch(() => [] as string[]);
      const headingMatch = allH1.some((h) => pg.checks.heading.test(h));
      if (!headingMatch) {
        allIssues.push({
          page: pg.sidebarLabel,
          type: "missing-content",
          detail: `Expected heading matching ${pg.checks.heading}. Found H1/H2: ${JSON.stringify(allH1)}`,
        });
        console.log(`  ⚠️ Heading: found ${JSON.stringify(allH1)}`);
      } else {
        console.log(`  ✅ Heading OK: ${JSON.stringify(allH1)}`);
      }

      // Check expected content
      for (const pattern of pg.checks.content) {
        if (!pattern.test(mainText)) {
          allIssues.push({
            page: pg.sidebarLabel,
            type: "missing-content",
            detail: `Expected content matching ${pattern} not found in main area`,
          });
          console.log(`  ⚠️ Missing content: ${pattern}`);
        }
      }

      // Check for console errors that appeared on this page
      const newConsoleErrors = allConsoleErrors.slice(preConsoleCount);
      for (const err of newConsoleErrors) {
        allIssues.push({
          page: pg.sidebarLabel,
          type: "console-error",
          detail: err.slice(0, 400),
        });
        console.log(`  🔴 Console error: ${err.slice(0, 150)}`);
      }

      // Check for API errors that appeared on this page
      const newApiErrors = allApiErrors.slice(preApiCount);
      for (const err of newApiErrors) {
        allIssues.push({
          page: pg.sidebarLabel,
          type: "api-error",
          detail: err,
        });
        console.log(`  🌐 API error: ${err}`);
      }

      // Check if page appears empty (just loading or no content)
      if (mainText.trim().length < 20) {
        allIssues.push({
          page: pg.sidebarLabel,
          type: "render-fail",
          detail: `Main area appears empty (${mainText.trim().length} chars)`,
        });
        console.log(`  ⚠️ Page content appears empty`);
      }

      // Screenshot
      await page
        .screenshot({
          path: `test-results/spa-${pg.sidebarLabel.replace(/\s/g, "-").toLowerCase()}.png`,
          fullPage: true,
        })
        .catch(() => {});
    }

    // ── Final Report ──
    console.log("\n\n" + "=".repeat(70));
    console.log("  FULL NAVIGATION AUDIT REPORT");
    console.log("=".repeat(70));

    if (allIssues.length === 0) {
      console.log("\n  ✅ All 15 pages loaded without issues!\n");
    } else {
      const byPage = new Map<string, PageIssue[]>();
      for (const issue of allIssues) {
        if (!byPage.has(issue.page)) byPage.set(issue.page, []);
        byPage.get(issue.page)!.push(issue);
      }

      const pagesWithIssues = byPage.size;
      const pagesOk = navPages.length - pagesWithIssues;

      console.log(
        `\n  ${allIssues.length} issue(s) across ${pagesWithIssues} page(s), ${pagesOk} page(s) clean\n`,
      );

      for (const [pageName, pageIssues] of byPage) {
        console.log(`  📄 ${pageName}`);
        for (const issue of pageIssues) {
          const icon: Record<string, string> = {
            crash: "💥",
            "console-error": "🔴",
            "api-error": "🌐",
            "missing-content": "⚠️",
            "render-fail": "🔧",
          };
          console.log(
            `     ${icon[issue.type] ?? "❓"} [${issue.type}] ${issue.detail}`,
          );
        }
        console.log("");
      }
    }

    console.log("=".repeat(70) + "\n");
  });
});
