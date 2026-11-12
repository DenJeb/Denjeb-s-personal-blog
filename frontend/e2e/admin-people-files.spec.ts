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

test("admin users can be toggled and deleted", async ({ page, context }) => {
  await signInAsAdmin(context);
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "用户管理" })).toBeVisible();
  await expect(page.getByText("共 2 个注册用户")).toBeVisible();

  const readerRow = page
    .locator("article")
    .filter({ hasText: "reader@example.com" });
  await expect(readerRow.getByText("正常", { exact: true })).toBeVisible();

  await readerRow.getByRole("button", { name: "禁用" }).click();
  await expect(
    readerRow.getByText("已禁用", { exact: true }),
  ).toBeVisible();

  await readerRow.getByRole("button", { name: "启用" }).click();
  await expect(readerRow.getByText("正常", { exact: true })).toBeVisible();

  await readerRow.getByRole("button", { name: "删除" }).click();
  await expect(page.getByText("共 1 个注册用户")).toBeVisible();
  await expect(page.getByText("reader@example.com")).toHaveCount(0);
});

test("admin uploads show references and delete orphans", async ({
  page,
  context,
}) => {
  await signInAsAdmin(context);
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/admin/uploads");
  await expect(page.getByRole("heading", { name: "图片管理" })).toBeVisible();
  await expect(page.getByText("共 2 个文件")).toBeVisible();

  const usedRow = page.locator("article").filter({ hasText: "used.webp" });
  await expect(usedRow.getByText("已引用", { exact: true })).toBeVisible();
  await expect(usedRow.getByText("使用中", { exact: true })).toBeVisible();
  await expect(usedRow.getByRole("button", { name: "删除" })).toHaveCount(0);

  const orphanRow = page
    .locator("article")
    .filter({ hasText: "orphan.webp" });
  await expect(
    orphanRow.getByText("未引用", { exact: true }),
  ).toBeVisible();

  await orphanRow.getByRole("button", { name: "删除" }).click();
  await expect(page.getByText("共 1 个文件")).toBeVisible();
  await expect(page.getByText("orphan.webp")).toHaveCount(0);
});
