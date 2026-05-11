import { test, expect } from "@playwright/test";

const TOKEN = process.env.ADMIN_TOKEN ?? "test-token";

test.beforeEach(async ({ page }) => {
  // Set auth token in localStorage before each test
  await page.goto("/");
  await page.evaluate((t) => localStorage.setItem("admin_token", t), TOKEN);
});

test("Pipeline Stream: page loads and shows table", async ({ page }) => {
  await page.goto("/pipeline");
  await expect(page.getByRole("heading", { name: "Pipeline Stream" })).toBeVisible();
  await expect(page.locator("table")).toBeVisible();
});

test("Prompt Editor: save button triggers PUT request", async ({ page }) => {
  await page.goto("/prompt");
  await expect(page.locator("[data-testid='prompt-textarea']")).toBeVisible();

  const [req] = await Promise.all([
    page.waitForRequest((r) => r.method() === "PUT" && r.url().includes("/api/settings/prompt")),
    page.locator("[data-testid='save-prompt-btn']").click(),
  ]);
  expect(req.method()).toBe("PUT");
});

test("KB Settings: TTL input and save", async ({ page }) => {
  await page.goto("/kb");
  await expect(page.locator("[data-testid='kb-ttl-input']")).toBeVisible();
  await page.fill("[data-testid='kb-ttl-input']", "10");

  const [req] = await Promise.all([
    page.waitForRequest((r) => r.method() === "PUT" && r.url().includes("/api/settings/kb-ttl")),
    page.locator("[data-testid='save-kb-btn']").click(),
  ]);
  const body = JSON.parse(req.postData()!);
  expect(body.ttl_minutes).toBe(10);
});

test("Audit: page mount triggers auto query and Pause toggle works", async ({ page }) => {
  const reqs: string[] = [];
  page.on("request", (r) => { if (r.url().includes("/api/audit")) reqs.push(r.url()); });
  await page.goto("/audit");
  // wait for auto-query on mount
  await page.waitForRequest((r) => r.url().includes("/api/audit"));
  expect(reqs.length).toBeGreaterThanOrEqual(1);
  // pause toggle
  const toggle = page.locator("[data-testid='audit-tail-toggle']");
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(toggle).toContainText("Resume");
});
