import { expect, test } from "@playwright/test";

test("admin pages ask anonymous visitors to sign in", async ({ page }) => {
  const response = await page.goto("/admin");

  expect(response?.status()).toBe(200);
  const csp = response?.headers()["content-security-policy"] ?? "";
  expect(csp).toContain("script-src 'self' 'nonce-");
  await expect(
    page.getByRole("heading", { name: "需要管理员登录" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "去登录" })).toHaveAttribute(
    "href",
    "/admin/login",
  );
});

test("admin dashboard and post list load for a signed-in admin", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "blog_session",
      value: "admin-session",
      url: "http://127.0.0.1:3000",
    },
  ]);

  const dashboardResponse = await page.goto("/admin");

  expect(dashboardResponse?.status()).toBe(200);
  await expect(page.getByRole("heading", { name: "仪表盘" })).toBeVisible();
  await expect(page.getByText("博客当前的数据概览。")).toBeVisible();
  await expect(page.getByRole("heading", { name: "后台迁移" })).toBeVisible();

  await page.goto("/admin/posts");

  await expect(page.getByRole("heading", { name: "文章" })).toBeVisible();
  await expect(page.getByText("共 3 篇，包含草稿和未来文章。")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "第一篇文章" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "未发布草稿" })).toBeVisible();
  await expect(page.getByRole("link", { name: "未来文章" })).toBeVisible();
  await expect(page.getByText("草稿", { exact: true })).toBeVisible();
  await expect(page.getByText("未到日期", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "编辑" }).first()).toHaveAttribute(
    "href",
    "/admin/posts/1/edit",
  );
  await expect(
    page.getByRole("button", { name: "退出后台" }),
  ).toBeVisible();
});

test("admin can log out", async ({ page, context }) => {
  await context.addCookies([
    {
      name: "blog_session",
      value: "admin-session",
      url: "http://127.0.0.1:3100",
    },
  ]);

  await page.goto("/admin");
  await page.getByRole("button", { name: "退出后台" }).click();
  await page.waitForURL("**/admin/login");
});
