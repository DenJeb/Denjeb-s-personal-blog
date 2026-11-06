import { expect, test } from "@playwright/test";

test("shows a friendly error when the API fails", async ({ page }) => {
  const response = await page.goto("/posts");

  await expect(page.getByText("页面暂时无法加载")).toBeVisible();
  await expect(page.getByText("ECONNREFUSED")).toHaveCount(0);
  expect(response?.status()).toBe(500);
});
