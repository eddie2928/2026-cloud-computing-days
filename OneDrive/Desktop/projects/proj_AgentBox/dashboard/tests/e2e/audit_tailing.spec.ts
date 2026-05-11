import { test, expect } from "@playwright/test";

const TOKEN = process.env.ADMIN_TOKEN ?? "test-token";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((t) => localStorage.setItem("admin_token", t), TOKEN);
});

test("Audit: auto-query on mount, then polling every 3s", async ({ page }) => {
  let count = 0;
  page.on("request", (r) => { if (r.url().includes("/api/audit?")) count += 1; });
  await page.goto("/audit");
  await page.waitForTimeout(7000); // ≥ 2 polls + initial
  expect(count).toBeGreaterThanOrEqual(2);
});

test("Audit: Pause stops polling, Resume restarts", async ({ page }) => {
  await page.goto("/audit");
  await page.waitForRequest((r) => r.url().includes("/api/audit?"));
  await page.locator("[data-testid='audit-tail-toggle']").click(); // Pause
  let countAfterPause = 0;
  page.on("request", (r) => { if (r.url().includes("/api/audit?")) countAfterPause += 1; });
  await page.waitForTimeout(7000);
  expect(countAfterPause).toBe(0);
  await page.locator("[data-testid='audit-tail-toggle']").click(); // Resume
  await page.waitForRequest((r) => r.url().includes("/api/audit?"), { timeout: 5000 });
});
