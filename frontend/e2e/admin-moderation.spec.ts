import { expect, test } from "./mock-reset";

async function signInAsAdmin(context: {
  addCookies: (cookies: {
    name: string;
    value: string;
    url: string;
  }[]) => Promise<void>;
}) {
  await context.addCookies([
    {
      name: "blog_session",
      value: "admin-session",
      url: "http://127.0.0.1:3000",
    },
  ]);
}

test("moderation pages ask anonymous visitors to sign in", async ({ page }) => {
  await page.goto("/admin/comments");
  await expect(
    page.getByRole("heading", { name: "需要管理员登录" }),
  ).toBeVisible();
});

test("expired admin session on a write sends the browser to login", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "blog_session",
      value: "admin-session",
      url: "http://127.0.0.1:3000",
    },
    {
      name: "write_expired",
      value: "1",
      url: "http://127.0.0.1:3000",
    },
  ]);

  await page.goto("/admin/comments");
  await page.getByRole("button", { name: "通过" }).click();
  await page.waitForURL("**/admin/login");
});

test("admin comments can be approved and deleted", async ({ page, context }) => {
  await signInAsAdmin(context);
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/admin/comments");

  await expect(page.getByRole("heading", { name: "评论管理" })).toBeVisible();
  await expect(page.getByText("共 2 条")).toBeVisible();
  await expect(page.getByText("这条评论待审核。")).toBeVisible();
  await expect(page.getByText("待审核", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "通过" }).click();
  await expect(
    page.getByRole("button", { name: "取消审核" }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("已通过", { exact: true }).first(),
  ).toBeVisible();

  await page.getByRole("button", { name: "删除" }).first().click();
  await expect(page.getByText("共 1 条")).toBeVisible();
  await expect(page.getByText("这条评论待审核。")).toHaveCount(0);
});

test("admin moment comments can be approved and deleted", async ({
  page,
  context,
}) => {
  await signInAsAdmin(context);
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/admin/moment-comments");

  await expect(
    page.getByRole("heading", { name: "动态评论管理" }),
  ).toBeVisible();
  await expect(page.getByText("动态评论待审核。")).toBeVisible();

  await page.getByRole("button", { name: "通过" }).click();
  await expect(
    page.getByRole("button", { name: "取消审核" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "删除" }).click();
  await expect(page.getByText("还没有动态评论。")).toBeVisible();
});
