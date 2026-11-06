import { expect, test } from "@playwright/test";

test("renders moments and comments", async ({ page }) => {
  await page.goto("/moments");
  await expect(page.getByText("今天写了一下午代码")).toBeVisible();
  await expect(page.getByText("加油")).toBeVisible();
});
