import { expect, test } from "@playwright/test";

test("renders terminal welcome", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("欢迎来到我的个人博客")).toBeVisible();
  await expect(page.getByRole("link", { name: "阅读文章" })).toHaveAttribute(
    "href",
    "/posts",
  );
});
