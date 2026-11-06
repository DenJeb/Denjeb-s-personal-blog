import { expect, test } from "@playwright/test";

test("lists tags and filters by tag", async ({ page }) => {
  await page.goto("/tags");
  await expect(page.getByRole("link", { name: /FastAPI/ })).toBeVisible();

  await page.goto("/tags?tag=FastAPI");
  await expect(page.getByRole("link", { name: "第一篇文章" })).toBeVisible();
});

test("renders archive", async ({ page }) => {
  await page.goto("/archive");
  await expect(page.getByRole("heading", { name: "2026" })).toBeVisible();
});
