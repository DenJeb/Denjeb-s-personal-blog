import { expect, test } from "@playwright/test";

test("renders guestbook", async ({ page }) => {
  await page.goto("/guestbook");
  await expect(page.getByText("欢迎来到我的博客")).toBeVisible();
});

test("renders about page", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByText("DenJeb").first()).toBeVisible();
  await expect(
    page.getByRole("link", { name: /github.com\/DenJeb/ }),
  ).toBeVisible();
});
