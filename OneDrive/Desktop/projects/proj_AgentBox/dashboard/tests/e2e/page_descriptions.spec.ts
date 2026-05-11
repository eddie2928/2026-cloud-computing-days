import { test, expect } from "@playwright/test";

const TOKEN = process.env.ADMIN_TOKEN ?? "test-token";
const PAGES = [
  { path: "/pipeline", keyword: "mitmproxy" },
  { path: "/audit", keyword: "DynamoDB" },
  { path: "/prompt", keyword: "Bedrock Agent" },
  { path: "/kb", keyword: "KB Staging" },
];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((t) => localStorage.setItem("admin_token", t), TOKEN);
});

for (const { path, keyword } of PAGES) {
  test(`Page ${path} shows description containing "${keyword}"`, async ({ page }) => {
    await page.goto(path);
    const desc = page.locator("p").filter({ hasText: keyword }).first();
    await expect(desc).toBeVisible();
    await expect(desc).toContainText(keyword);
  });
}

test("Login page shows description containing Admin Token", async ({ page }) => {
  await page.evaluate(() => localStorage.removeItem("admin_token"));
  await page.goto("/login");
  const desc = page.locator("p").filter({ hasText: "Admin Token" }).first();
  await expect(desc).toBeVisible();
  await expect(desc).toContainText("Admin Token");
});
