import { expect, test } from "./mock-reset";

test("admin can enable and disable TOTP", async ({ page, context }) => {
  await context.addCookies([
    {
      name: "blog_session",
      value: "admin-session",
      url: "http://127.0.0.1:3000",
    },
  ]);

  await page.goto("/admin/security");

  await expect(page.getByRole("heading", { name: "安全设置" })).toBeVisible();
  await expect(
    page.getByText("未启用。建议开启，避免密码泄露后直接进入后台。"),
  ).toBeVisible();

  await page.getByRole("button", { name: "开始设置" }).click();
  await expect(page.getByText("TESTSECRET", { exact: true })).toBeVisible();
  await expect(page.getByText(/otpauth:\/\/totp/)).toBeVisible();

  await page.getByLabel("验证码").fill("123456");
  await page.getByRole("button", { name: "启用两步验证" }).click();
  await expect(
    page.getByText(
      "已启用。每次登录除了密码，还需要输入认证器中的 6 位验证码。",
    ),
  ).toBeVisible();

  await page
    .locator("summary")
    .filter({ hasText: "关闭两步验证" })
    .click();
  await page.getByLabel("当前密码").fill("PytestPass123!");
  await page.getByLabel("认证器验证码").fill("123456");
  await page.getByRole("button", { name: "关闭两步验证" }).click();
  await expect(
    page.getByText("未启用。建议开启，避免密码泄露后直接进入后台。"),
  ).toBeVisible();
});
