import { expect, test } from "@playwright/test";

test("renders search results", async ({ page }) => {
  await page.goto("/search?q=FastAPI");
  await expect(page.getByRole("link", { name: "第一篇文章" })).toBeVisible();
});

test("shows prompt without query", async ({ page }) => {
  await page.goto("/search");
  await expect(page.getByText("输入关键词开始搜索")).toBeVisible();
});

test("rejects query longer than 100 chars", async ({ page }) => {
  await page.goto(`/search?q=${"a".repeat(101)}`);
  await expect(page.getByText("搜索词不能超过 100 个字符")).toBeVisible();
});

test("shows empty results", async ({ page }) => {
  await page.goto("/search?q=nothing");
  await expect(page.getByText("没有找到相关文章")).toBeVisible();
});
