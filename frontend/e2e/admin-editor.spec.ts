import { expect, test } from "./mock-reset";

test("expired session on edit pages redirects to admin login", async ({
  request,
}) => {
  const headers = {
    Cookie: "blog_session=admin-session; detail_expired=1",
  };

  const postResponse = await request.get("/admin/posts/1/edit", {
    maxRedirects: 0,
    headers,
  });
  expect(postResponse.status()).toBe(307);
  expect(postResponse.headers()["location"]).toContain("/admin/login");

  const momentResponse = await request.get("/admin/moments/5/edit", {
    maxRedirects: 0,
    headers,
  });
  expect(momentResponse.status()).toBe(307);
  expect(momentResponse.headers()["location"]).toContain("/admin/login");
});

test("admin can create, edit, preview, upload and delete a post", async ({
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
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/admin/posts/new");
  await expect(page.getByRole("heading", { name: "新建文章" })).toBeVisible();

  await page.getByLabel("标题", { exact: true }).fill("新的文章");
  await page.getByLabel("正文").fill("# 新文章\n\n正文");
  await page.getByRole("button", { name: "保存" }).click();
  await page.waitForURL("**/admin/posts");

  await page.goto("/admin/posts/100/edit");
  await expect(page.getByRole("heading", { name: "编辑文章" })).toBeVisible();
  await expect(page.getByLabel("标题", { exact: true })).toHaveValue("新的文章");

  await page.getByLabel("标题", { exact: true }).fill("更新后的文章");
  await page.getByRole("button", { name: "保存" }).click();
  await page.waitForURL("**/admin/posts");

  await page.goto("/admin/posts/100/edit");
  await expect(page.getByLabel("标题", { exact: true })).toHaveValue("更新后的文章");

  await page.getByRole("button", { name: "预览" }).click();
  await expect(page.locator(".admin-editor-preview")).toContainText(
    "Preview",
  );

  await page.locator('input[type="file"]').setInputFiles({
    name: "cover.png",
    mimeType: "image/png",
    buffer: Buffer.from("fake-image"),
  });
  await expect(page.getByLabel("正文")).toHaveValue(
    /\/static\/uploads\/mock\.webp/,
  );

  await page.getByRole("button", { name: "删除这篇文章" }).click();
  await page.waitForURL("**/admin/posts");
});
