import { expect, test } from "@playwright/test";

async function loginWithMock(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill("user@example.com");
  await page.getByLabel("密码").fill("password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.waitForURL("/");
}

test("invalid login shows an error", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill("user@example.com");
  await page.getByLabel("密码").fill("wrong-password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.locator(".form-error")).toContainText("邮箱或密码错误");
});

test("login and logout update the header", async ({ page }) => {
  await loginWithMock(page);
  await expect(
    page.getByRole("link", { name: "DenJeb", exact: true }),
  ).toBeVisible();

  await page.getByRole("button", { name: "退出" }).click();
  await expect(page.getByRole("link", { name: "登录" })).toBeVisible();
});

test("guest is invited to login before commenting", async ({ page }) => {
  await page.goto("/posts/hello-world#comments");
  await expect(page.getByRole("link", { name: "登录后评论" })).toBeVisible();
});

test("logged-in user can submit a comment", async ({ page, context }) => {
  await context.addCookies([
    {
      name: "blog_session",
      value: "test-session",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);

  await page.goto("/posts/hello-world#comments");
  await page
    .getByPlaceholder("写下你的评论…")
    .fill("这是一条 Phase 2 测试评论");
  await page.getByRole("button", { name: "发表评论" }).click();
  await expect(page.getByRole("status")).toContainText("评论已提交");
});

test("logged-in user can submit a guestbook message", async ({
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

  await page.goto("/guestbook");
  await page
    .getByPlaceholder("写下想说的话…")
    .fill("这是一条 Phase 2 测试留言");
  await page.getByRole("button", { name: "提交留言" }).click();
  await expect(page.getByRole("status")).toContainText("留言已提交");
});

test("logged-in user can comment on a moment", async ({ page, context }) => {
  await context.addCookies([
    {
      name: "blog_session",
      value: "test-session",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);

  await page.goto("/moments");
  await page
    .getByPlaceholder("写下你的评论…")
    .first()
    .fill("这是一条 Phase 2 动态评论");
  await page.getByRole("button", { name: "发表评论" }).first().click();
  await expect(page.getByRole("status")).toContainText("评论已提交");
});
