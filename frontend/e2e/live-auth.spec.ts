import { expect, test } from "@playwright/test";

test.skip(
  !process.env.LIVE_API || !process.env.E2E_POST_SLUG,
  "set LIVE_API=1 and E2E_POST_SLUG to run against the disposable Phase 2 DB",
);

const postSlug = process.env.E2E_POST_SLUG ?? "";

test("real FastAPI login, comments and guestbook", async ({ page }) => {
  await page.goto(`/login?next=/posts/${postSlug}`);
  await page.getByLabel("邮箱").fill("e2e@example.com");
  await page.getByLabel("密码").fill("E2ePass123!");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.waitForURL(`/posts/${postSlug}`);

  await expect(
    page.getByRole("link", { name: "e2e_user", exact: true }),
  ).toBeVisible();

  await page.goto(`/posts/${postSlug}#comments`);
  await page
    .getByPlaceholder("写下你的评论…")
    .fill("真实 E2E 文章评论");
  await page.getByRole("button", { name: "发表评论" }).click();
  await expect(page.getByRole("status")).toContainText("评论已提交");

  await page.goto("/guestbook");
  await page
    .getByPlaceholder("写下想说的话…")
    .fill("真实 E2E 留言");
  await page.getByRole("button", { name: "提交留言" }).click();
  await expect(page.getByRole("status")).toContainText("留言已提交");

  await page.goto("/moments");
  await page
    .getByPlaceholder("写下你的评论…")
    .first()
    .fill("真实 E2E 动态评论");
  await page.getByRole("button", { name: "发表评论" }).first().click();
  await expect(page.getByRole("status")).toContainText("评论已提交");

  await page.getByRole("button", { name: "退出" }).click();
  await expect(page.getByRole("link", { name: "登录" })).toBeVisible();
});
