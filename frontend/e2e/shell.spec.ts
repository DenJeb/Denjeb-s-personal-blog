import { expect, test } from "@playwright/test";

test("renders site shell and login link", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "登录" })).toBeVisible();
  await expect(page.getByRole("link", { name: "搜索" })).toBeVisible();
  await expect(page.getByText("Denjeb 的个人博客").first()).toBeVisible();
});

test("renders 404 page", async ({ page }) => {
  const response = await page.goto("/does-not-exist");
  expect(response?.status()).toBe(404);
  await expect(page.getByText("页面不存在")).toBeVisible();
});

test("shows the logged-in user from the session cookie", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "blog_session",
      value: "test-session",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);

  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "DenJeb", exact: true }),
  ).toBeVisible();
});
