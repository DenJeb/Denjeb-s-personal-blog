import { expect, test } from "@playwright/test";

test("lists posts and paginates", async ({ page }) => {
  await page.goto("/posts");
  await expect(page.getByRole("link", { name: "第一篇文章" })).toBeVisible();
  await expect(page.getByRole("link", { name: "下一页" })).toHaveAttribute(
    "href",
    "/posts?page=2",
  );
});

test("shows empty state for out-of-range page", async ({ page }) => {
  await page.goto("/posts?page=99");
  await expect(page.getByText("没有更多文章")).toBeVisible();
});
