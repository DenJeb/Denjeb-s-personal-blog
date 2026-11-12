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

test("admin moments can be created, edited and deleted", async ({
  page,
  context,
}) => {
  await signInAsAdmin(context);
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/admin/moments");
  await expect(page.getByRole("heading", { name: "动态管理" })).toBeVisible();
  await expect(page.getByText("今天写完了后台迁移。")).toBeVisible();

  await page.getByRole("link", { name: "发布动态" }).click();
  await expect(page.getByRole("heading", { name: "发布动态" })).toBeVisible();
  await page.getByLabel("内容").fill("新的动态内容");
  await page.getByRole("button", { name: "保存" }).click();
  await page.waitForURL("**/admin/moments");
  await expect(page.getByText("新的动态内容")).toBeVisible();

  const row = page.locator("article").filter({ hasText: "新的动态内容" });
  await row.getByRole("link", { name: "编辑" }).click();
  await expect(page.getByRole("heading", { name: "编辑动态" })).toBeVisible();
  await page.getByLabel("内容").fill("更新后的动态内容");
  await page.getByRole("button", { name: "保存" }).click();
  await page.waitForURL("**/admin/moments");
  await expect(page.getByText("更新后的动态内容")).toBeVisible();

  const updatedRow = page
    .locator("article")
    .filter({ hasText: "更新后的动态内容" });
  await updatedRow.getByRole("button", { name: "删除" }).click();
  await expect(page.getByText("更新后的动态内容")).toHaveCount(0);
});

test("admin messages can be deleted", async ({ page, context }) => {
  await signInAsAdmin(context);
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/admin/messages");
  await expect(page.getByRole("heading", { name: "留言管理" })).toBeVisible();
  await expect(page.getByText("留言内容一。")).toBeVisible();

  await page.getByRole("button", { name: "删除" }).click();
  await expect(page.getByText("还没有留言。")).toBeVisible();
});
